import asyncio
import email
import email.message
import email.utils
import imaplib
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import allure
import httpx
import pytest
from allure_commons.types import AttachmentType
from playwright.sync_api import sync_playwright

DEFAULT_TIMEOUT = 20_000  # 20 seconds
QCAQ_TEST_CASE_ID_LABEL = "qcaq_test_case_id"
QCAQ_TEST_SUITE_ID_LABEL = "qcaq_test_group_id"


# -------------------------------
# Email Test Fixtures
# -------------------------------


@dataclass
class EmailResult:
    """Represents a fetched email message."""

    id: str
    from_address: str
    subject: str
    body: str
    to: list[str]
    received_at: datetime


class EmailTestProvider:
    """Abstract interface for email test providers."""

    async def get_latest_from_sender(
        self, sender: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email from a specific sender."""
        raise NotImplementedError

    async def get_latest_to_recipient(
        self, recipient: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email sent to a specific recipient."""
        raise NotImplementedError

    async def wait_for_email(
        self,
        sender: str | None = None,
        recipient: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 1.0,
    ) -> EmailResult:
        """Wait for an email matching criteria, ignoring emails older than call time."""
        deadline = time.time() + timeout
        # Record start time so we only return emails that arrive after this call.
        since = datetime.now(timezone.utc)

        while time.time() < deadline:
            result: EmailResult | None = None

            if sender:
                result = await self.get_latest_from_sender(sender, since=since)
            elif recipient:
                result = await self.get_latest_to_recipient(recipient, since=since)
            else:
                msg = "Must specify either sender or recipient"
                raise ValueError(msg)

            if result is not None:
                return result

            # FIX #2: use asyncio.sleep instead of time.sleep inside async method
            await asyncio.sleep(poll_interval)

        raise TimeoutError(
            f"Email {'from ' + sender if sender else 'to ' + (recipient or '')} "
            f"not found within {timeout}s"
        )


class ImapProvider(EmailTestProvider):
    """IMAP-based email provider for Gmail and similar services."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        use_ssl: bool | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl if use_ssl is not None else port == 993

    def _connect(self) -> imaplib.IMAP4 | imaplib.IMAP4_SSL:
        """Create IMAP connection."""
        if self.use_ssl:
            return imaplib.IMAP4_SSL(self.host, self.port)
        return imaplib.IMAP4(self.host, self.port)

    def _search_emails(self, criteria: str, limit: int = 10) -> list[EmailResult]:
        """Search emails with given IMAP criteria."""
        mail = self._connect()
        try:
            if self.username:
                mail.login(self.username, self.password or "")
            mail.select("INBOX")

            status, data = mail.search(None, criteria)
            if status != "OK" or not data[0]:
                return []

            email_ids = data[0].split()[-limit:]
            results = []

            for msg_id in reversed(email_ids):
                msg_id_str = (
                    msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                )
                status, msg_data = mail.fetch(msg_id_str, "(RFC822)")

                if status == "OK" and msg_data[0]:
                    # FIX #1 (same pattern): use clean index access, no walrus operator
                    raw_email = (
                        msg_data[0][1]
                        if isinstance(msg_data[0], tuple)
                        else msg_data[0]
                    )
                    if isinstance(raw_email, bytes):
                        msg = email.message_from_bytes(raw_email)
                    else:
                        msg = email.message_from_string(raw_email)

                    body = self._extract_body(msg)
                    from_addr = msg.get("From", "")
                    subject = msg.get("Subject", "")
                    to_addrs = msg.get("To", "").split(", ")
                    date_str = msg.get("Date", "")

                    try:
                        received_at = email.utils.parsedate_to_datetime(date_str)
                    except (ValueError, TypeError):
                        received_at = datetime.now(timezone.utc)

                    results.append(
                        EmailResult(
                            id=msg_id_str,
                            from_address=from_addr,
                            subject=subject,
                            body=body,
                            to=to_addrs,
                            received_at=received_at,
                        )
                    )

            return results
        finally:
            mail.logout()

    def _extract_body(self, msg: email.message.Message) -> str:
        """Extract text body from email message."""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        decoded = payload.decode(
                            part.get_content_charset() or "utf-8",
                            errors="replace",
                        ).strip()
                        if decoded:
                            return decoded
                if content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        decoded = payload.decode(
                            part.get_content_charset() or "utf-8",
                            errors="replace",
                        ).strip()
                        if decoded:
                            return decoded
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(
                    msg.get_content_charset() or "utf-8",
                    errors="replace",
                ).strip()
        return ""

    async def get_latest_from_sender(
        self, sender: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email from a specific sender via IMAP."""
        criteria = f'FROM "{sender}"'
        results = self._search_emails(criteria)
        # FIX #6: apply since filter so polling does not return stale emails
        if since:
            results = [r for r in results if r.received_at >= since]
        return results[0] if results else None

    async def get_latest_to_recipient(
        self, recipient: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email to a specific recipient via IMAP."""
        criteria = f'TO "{recipient}"'
        results = self._search_emails(criteria)
        if since:
            results = [r for r in results if r.received_at >= since]
        return results[0] if results else None


class MailpitProvider(EmailTestProvider):
    """Mailpit HTTP API provider."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["X-Api-Key"] = self.api_key
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def get_latest_from_sender(
        self, sender: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email from a specific sender via Mailpit API."""
        client = await self._get_client()
        try:
            response = await client.get(
                "/api/v1/messages",
                params={"limit": 10, "search": f"from:{sender}"},
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])

            # FIX #4: parse ISO string before comparing to since timestamp
            if since:
                since_ts = since.timestamp()
                messages = [
                    m
                    for m in messages
                    if _parse_mailpit_timestamp(m.get("Created", "")) >= since_ts
                ]

            if not messages:
                return None

            latest = messages[0]
            return await self._get_email_details(client, latest["ID"])
        except httpx.HTTPError:
            return None

    async def get_latest_to_recipient(
        self, recipient: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email to a specific recipient via Mailpit API."""
        client = await self._get_client()
        try:
            response = await client.get(
                "/api/v1/messages",
                params={"limit": 5, "search": f"to:{recipient}"},
            )
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])

            # FIX #4: parse ISO string before comparing to since timestamp
            if since:
                since_ts = since.timestamp()
                messages = [
                    m
                    for m in messages
                    if _parse_mailpit_timestamp(m.get("Created", "")) >= since_ts
                ]

            if not messages:
                return None

            latest = messages[0]
            return await self._get_email_details(client, latest["ID"])
        except httpx.HTTPError:
            return None

    async def _get_email_details(
        self, client: httpx.AsyncClient, message_id: str
    ) -> EmailResult | None:
        """Get full email details by ID."""
        try:
            response = await client.get(f"/api/v1/message/{message_id}")
            response.raise_for_status()
            data = response.json()

            raw_text = data.get("Text", "")
            raw_html = data.get("HTML", "")
            body = raw_text or raw_html

            try:
                received_at = datetime.fromisoformat(
                    data["Created"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError, KeyError):
                received_at = datetime.now(timezone.utc)

            # FIX #3: Mailpit returns To as a list of {"Address": ..., "Name": ...}
            # objects, not a plain string — extract the Address field from each entry.
            to_raw = data.get("To", [])
            if isinstance(to_raw, list):
                to_addrs = [entry.get("Address", "") for entry in to_raw]
            else:
                # Fallback: plain string (unexpected, but safe)
                to_addrs = [to_raw] if to_raw else []

            return EmailResult(
                id=str(message_id),
                from_address=data.get("From", {}).get("Address", "")
                if isinstance(data.get("From"), dict)
                else data.get("From", ""),
                subject=data.get("Subject", ""),
                body=body,
                to=to_addrs,
                received_at=received_at,
            )
        except httpx.HTTPError:
            return None


def _parse_mailpit_timestamp(value: str) -> float:
    """Parse a Mailpit ISO 8601 timestamp string to a Unix timestamp float.

    Returns 0.0 on any parse failure so the message is excluded from
    since-filtered result sets rather than raising an exception.
    """
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return 0.0


class MailhogProvider(EmailTestProvider):
    """Mailhog HTTP API provider."""

    def __init__(
        self,
        api_url: str,
        timeout: float = 30.0,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.api_url,
                timeout=self.timeout,
            )
        return self._client

    async def get_latest_from_sender(
        self, sender: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email from a specific sender via Mailhog API."""
        client = await self._get_client()
        try:
            response = await client.get("/api/v2/messages")
            response.raise_for_status()
            data = response.json()

            messages = data.get("items", [])
            filtered = [
                m for m in messages if sender.lower() in m.get("From", "").lower()
            ]

            # FIX #6: apply since filter so polling does not return stale emails
            if since:
                since_ts = since.timestamp()
                filtered = [m for m in filtered if m.get("Created", 0) >= since_ts]

            if not filtered:
                return None

            return self._parse_email(filtered[0])
        except httpx.HTTPError:
            return None

    async def get_latest_to_recipient(
        self, recipient: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email to a specific recipient via Mailhog API."""
        client = await self._get_client()
        try:
            response = await client.get("/api/v2/messages")
            response.raise_for_status()
            data = response.json()

            messages = data.get("items", [])
            filtered = [
                m for m in messages if recipient.lower() in m.get("To", "").lower()
            ]

            if since:
                since_ts = since.timestamp()
                filtered = [m for m in filtered if m.get("Created", 0) >= since_ts]

            if not filtered:
                return None

            return self._parse_email(filtered[0])
        except httpx.HTTPError:
            return None

    def _parse_email(self, data: dict) -> EmailResult:
        """Parse Mailhog email format."""
        content = data.get("Content", {})
        headers = content.get("Headers", {})

        try:
            received_at = datetime.fromisoformat(
                data.get("Created", "").replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            received_at = datetime.now(timezone.utc)

        body = content.get("Body", "")
        if not body:
            mime = content.get("MIME", {})
            parts = mime.get("Parts", [])
            for part in parts:
                if part.get("MimeType") == "text/plain":
                    body = part.get("Body", "")
                    break

        return EmailResult(
            id=data.get("ID", ""),
            from_address=data.get("From", ""),
            subject=(headers.get("Subject", [""])[0] if headers.get("Subject") else ""),
            body=body,
            to=headers.get("To", []) if headers.get("To") else [],
            received_at=received_at,
        )


class PapercutProvider(EmailTestProvider):
    """Papercut HTTP provider."""

    def __init__(
        self,
        base_url: str,
        username: str | None = None,
        password: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            auth = None
            if self.username and self.password:
                auth = (self.username, self.password)
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=auth,
                timeout=self.timeout,
            )
        return self._client

    async def get_latest_from_sender(
        self, sender: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email from a specific sender via Papercut."""
        client = await self._get_client()
        try:
            response = await client.get("/api/messages")
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            filtered = [
                m
                for m in messages
                if sender.lower() in m.get("from_address", "").lower()
            ]

            # FIX #6: apply since filter so polling does not return stale emails
            if since:
                since_ts = since.timestamp()
                filtered = [m for m in filtered if m.get("timestamp", 0) >= since_ts]

            if not filtered:
                return None

            return await self._get_email_details(client, filtered[0]["id"])
        except httpx.HTTPError:
            return None

    async def get_latest_to_recipient(
        self, recipient: str, since: datetime | None = None
    ) -> EmailResult | None:
        """Get the latest email to a specific recipient via Papercut."""
        client = await self._get_client()
        try:
            response = await client.get("/api/messages")
            response.raise_for_status()
            data = response.json()

            messages = data.get("messages", [])
            filtered = [
                m
                for m in messages
                if recipient.lower() in m.get("recipient", "").lower()
            ]

            if since:
                since_ts = since.timestamp()
                filtered = [m for m in filtered if m.get("timestamp", 0) >= since_ts]

            if not filtered:
                return None

            return await self._get_email_details(client, filtered[0]["id"])
        except httpx.HTTPError:
            return None

    async def _get_email_details(
        self, client: httpx.AsyncClient, message_id: str
    ) -> EmailResult | None:
        """Get full email details by ID."""
        try:
            response = await client.get(f"/api/messages/{message_id}")
            response.raise_for_status()
            data = response.json()

            try:
                received_at = datetime.fromtimestamp(
                    data.get("timestamp", 0), tz=timezone.utc
                )
            except (ValueError, TypeError):
                received_at = datetime.now(timezone.utc)

            return EmailResult(
                id=str(message_id),
                from_address=data.get("from_address", ""),
                subject=data.get("subject", ""),
                body=data.get("body", ""),
                to=[data.get("recipient", "")],
                received_at=received_at,
            )
        except httpx.HTTPError:
            return None


class NoOpProvider(EmailTestProvider):
    """No-op provider for when no email service is configured."""

    async def get_latest_from_sender(
        self, sender: str, since: datetime | None = None
    ) -> EmailResult | None:
        return None

    async def get_latest_to_recipient(
        self, recipient: str, since: datetime | None = None
    ) -> EmailResult | None:
        return None


def create_email_provider() -> EmailTestProvider:
    """Create an email provider based on environment variables.

    Supports:
    - IMAP (EMAIL_PROVIDER=imap or IMAP_HOST set)
    - Mailpit (EMAIL_PROVIDER=mailpit or MAILPIT_URL set)
    - Mailhog (EMAIL_PROVIDER=mailhog or MAILHOG_API_URL set)
    - Papercut (EMAIL_PROVIDER=papercut or PAPERCUT_URL set)
    """
    provider_type = os.environ.get("EMAIL_PROVIDER", "").lower()

    if not provider_type:
        if os.environ.get("IMAP_HOST"):
            provider_type = "imap"
        elif os.environ.get("MAILPIT_URL"):
            provider_type = "mailpit"
        elif os.environ.get("MAILHOG_API_URL"):
            provider_type = "mailhog"
        elif os.environ.get("PAPERCUT_URL"):
            provider_type = "papercut"
        else:
            return NoOpProvider()

    match provider_type:
        case "imap":
            return ImapProvider(
                host=os.environ["IMAP_HOST"],
                port=int(os.environ.get("IMAP_PORT", "993")),
                username=os.environ.get("IMAP_USER"),
                password=os.environ.get("IMAP_PASSWORD"),
            )
        case "mailpit":
            return MailpitProvider(
                base_url=os.environ["MAILPIT_URL"],
                api_key=os.environ.get("MAILPIT_API_KEY"),
            )
        case "mailhog":
            return MailhogProvider(
                api_url=os.environ["MAILHOG_API_URL"],
            )
        case "papercut":
            return PapercutProvider(
                base_url=os.environ["PAPERCUT_URL"],
                username=os.environ.get("PAPERCUT_USER"),
                password=os.environ.get("PAPERCUT_PASSWORD"),
            )
        case _:
            return NoOpProvider()


@pytest.fixture(scope="session")
def email_provider() -> EmailTestProvider:
    """Create an email provider based on environment configuration.

    Environment variables:
    - EMAIL_PROVIDER: "imap" | "mailpit" | "mailhog" | "papercut"
    - IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASSWORD: IMAP connection
    - MAILPIT_URL, MAILPIT_API_KEY: Mailpit API
    - MAILHOG_API_URL: Mailhog API
    - PAPERCUT_URL, PAPERCUT_USER, PAPERCUT_PASSWORD: Papercut

    Usage:
        async def test_email_received(email_provider):
            email = await email_provider.get_latest_from_sender("noreply@example.com")
            assert email is not None
            assert "verification" in email.subject.lower()
    """
    return create_email_provider()


@pytest.fixture
def email_fetcher(email_provider: EmailTestProvider) -> "EmailFetcher":
    """Async fixture providing email fetching capabilities.

    Usage:
        async def test_verify_email(email_fetcher):
            email = await email_fetcher.get_latest_from_sender("noreply@example.com")
            assert email is not None

            # Extract tuple: (id, from_address, subject, body)
            email_id, from_addr, subject, body = EmailFetcher.extract_tuple(email)
            assert "verify" in subject.lower()

        async def test_wait_for_invite(email_fetcher):
            result = await email_fetcher.wait_for_latest(
                sender="team@example.com",
                timeout=60
            )
            assert "invitation" in result.subject.lower()
    """
    return EmailFetcher(email_provider)


class EmailFetcher:
    """High-level email fetching interface for tests."""

    def __init__(self, provider: EmailTestProvider) -> None:
        self._provider = provider

    async def get_latest_from_sender(self, sender: str) -> EmailResult | None:
        """Get latest email from a sender."""
        return await self._provider.get_latest_from_sender(sender)

    async def get_latest_to_recipient(
        self, recipient: str, since_minutes: int = 10
    ) -> EmailResult | None:
        """Get latest email to a recipient within time window."""
        since = datetime.now(timezone.utc) - timedelta(minutes=since_minutes)
        return await self._provider.get_latest_to_recipient(recipient, since)

    async def wait_for_latest(
        self,
        sender: str | None = None,
        recipient: str | None = None,
        timeout: float = 30.0,
        poll_interval: float = 1.0,
    ) -> EmailResult:
        """Wait for an email matching criteria."""
        return await self._provider.wait_for_email(
            sender=sender,
            recipient=recipient,
            timeout=timeout,
            poll_interval=poll_interval,
        )

    @staticmethod
    def extract_tuple(result: EmailResult | None) -> tuple[str, str, str, str] | None:
        """Extract standardized tuple from EmailResult.

        Returns:
            Tuple of (id, from_address, subject, body) or None.
        """
        if result is None:
            return None
        return (result.id, result.from_address, result.subject, result.body)

    @staticmethod
    def extract_otp(body: str, pattern: str = r"\b(\d{4,8})\b") -> str | None:
        """Extract OTP code from email body.

        Args:
            body: Email body text.
            pattern: Regex pattern with single capture group.

        Returns:
            OTP string or None.
        """
        match = re.search(pattern, body)
        return match.group(1) if match else None

    @staticmethod
    def extract_link(
        body: str, url_pattern: str = r"https?://[^\s<>\"']+"
    ) -> str | None:
        """Extract first URL from email body.

        Args:
            body: Email body text.
            url_pattern: Regex pattern for URL matching.

        Returns:
            URL string or None.
        """
        match = re.search(url_pattern, body)
        return match.group(0) if match else None


def pytest_addoption(parser):
    pass


# -------------------------------
# Environment Variable Loading
# -------------------------------
@pytest.fixture(scope="session", autouse=True)
def load_qcaq_environment():
    """
    Load QCAQ environment configuration.

    Environment variables and secrets are injected by the executor
    pipeline as container environment variables.

    Required variables (must be configured in QCAQ project settings):
    - BASE_URL: Application base URL

    Optional variables (configured per project):
    - API_KEY, AUTH_TOKEN, DB_PASSWORD, etc.: Project-specific secrets
    - ADMIN_USERNAME, ADMIN_PASSWORD: Test credentials
    - Any other variables defined in project environment settings
    """
    required_vars = ["BASE_URL"]
    missing = [var for var in required_vars if var not in os.environ]

    if missing:
        pass

    yield


# -------------------------------
# Playwright Startup
# -------------------------------
@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


# -------------------------------
# Browser Fixture
# -------------------------------
@pytest.fixture(scope="session")
def browsers(playwright_instance, pytestconfig):
    browser_names = pytestconfig.getoption("--browser") or ["chromium"]
    slowmo = pytestconfig.getoption("--slowmo")
    launch_options = {
        "headless": False,
        "slow_mo": slowmo,
    }
    browser_map = {
        "chromium": playwright_instance.chromium,
        "firefox": playwright_instance.firefox,
        "webkit": playwright_instance.webkit,
    }
    launched = []
    for name in browser_names:
        if name not in browser_map:
            raise ValueError(
                f"Unknown browser: {name}. Use chromium, firefox, or webkit."
            )
        b = browser_map[name].launch(**launch_options)
        launched.append((name, b))
    yield launched
    for _, b in launched:
        b.close()


# -------------------------------
# Browser Contexts
# -------------------------------
@pytest.fixture(scope="function")
def contexts(browsers, request, tmp_path):
    contexts = []
    video_dirs = []
    base_video_dir = tmp_path / "videos"

    for name, browser in browsers:
        browser_video_dir = base_video_dir / name
        browser_video_dir.mkdir(parents=True, exist_ok=True)
        video_dirs.append(browser_video_dir)

        ctx = browser.new_context(record_video_dir=browser_video_dir)
        ctx.set_default_timeout(DEFAULT_TIMEOUT)
        contexts.append((name, ctx))

    setattr(request.node, "_qcaq_video_dirs", video_dirs)
    yield contexts

    for _, ctx in contexts:
        ctx.close()


# -------------------------------
# Pages
# -------------------------------
@pytest.fixture(scope="function")
def pages(contexts):
    pages = []
    for name, ctx in contexts:
        page = ctx.new_page()
        pages.append((name, page))

    yield pages

    for _, page in pages:
        page.close()


def _extract_uuid_path_parts(node_path: Path) -> tuple[str | None, str | None]:
    """Extract suite and test case UUIDs from the generated test file path."""
    parts = node_path.parts
    for index in range(len(parts) - 1):
        suite_candidate = parts[index]
        test_case_candidate = parts[index + 1]
        try:
            suite_id = str(UUID(suite_candidate))
            test_case_id = str(UUID(test_case_candidate))
        except ValueError:
            continue
        return suite_id, test_case_id

    return None, None


@pytest.fixture(autouse=True)
def inject_qcaq_allure_labels(request):
    """Attach stable QCAQ IDs to Allure results for downstream report mapping."""
    suite_id, test_case_id = _extract_uuid_path_parts(Path(str(request.node.fspath)))
    if suite_id:
        allure.dynamic.label(QCAQ_TEST_SUITE_ID_LABEL, suite_id)
    if test_case_id:
        allure.dynamic.label(QCAQ_TEST_CASE_ID_LABEL, test_case_id)


# -------------------------------
# Allure Step Wrapper (Screenshots per Step)
# -------------------------------
@pytest.fixture(autouse=True)
def multi_browser_step_screenshots(pages):
    original_step = allure.step

    def wrapped_step(title: str):
        step_ctx = original_step(title)
        step_ctx.__enter__()

        class StepWrapper:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                for browser_name, page in pages:
                    try:
                        allure.attach(
                            page.screenshot(),
                            name=f"{title} - {browser_name}",
                            attachment_type=AttachmentType.PNG,
                        )
                    except Exception as err:
                        print(f"Error due to exception in screenshot due to: {err}")
                        pass
                step_ctx.__exit__(exc_type, exc_val, exc_tb)

        return StepWrapper()

    allure.step = wrapped_step
    yield
    allure.step = original_step


# -------------------------------
# Allure Screenshot on Test Failure
# -------------------------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        pages = item.funcargs.get("pages")
        if not pages:
            return

        nodeid = item.nodeid
        for browser_name, page in pages:
            try:
                allure.attach(
                    page.screenshot(),
                    name=f"FAILURE - {browser_name}",
                    attachment_type=AttachmentType.PNG,
                )
            except Exception as err:
                print(f"Error due to exception in screenshot due to: {err}")
                pass

            try:
                diagnostic = {
                    "browser": browser_name,
                    "url": page.url,
                    "title": page.title(),
                    "elements": page.evaluate("""() => {
                        const elements = document.querySelectorAll(
                            'input, textarea, select, button, a[href]'
                        );
                        return Array.from(elements).map(el => {
                            const rect = el.getBoundingClientRect();
                            return {
                                tag: el.tagName.toLowerCase(),
                                id: el.id || null,
                                name: el.getAttribute('name') || null,
                                type: el.getAttribute('type') || null,
                                placeholder: el.placeholder || null,
                                text: (el.textContent || '').trim().slice(0, 200),
                                value: el.value || null,
                                aria_label: el.getAttribute('aria-label') || null,
                                class: Array.from(el.classList).slice(0, 3),
                                href: el.href || null,
                                role: el.getAttribute('role') || null,
                                data_testid: el.getAttribute('data-testid') || null,
                                visible: rect.width > 0 && rect.height > 0,
                            };
                        });
                    }"""),
                }

                diag_dir = Path("./diagnostics")
                diag_dir.mkdir(parents=True, exist_ok=True)
                safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", nodeid)
                diag_path = diag_dir / f"{safe_name}_dom.json"
                diag_path.write_text(json.dumps(diagnostic, indent=2))
            except Exception as diag_err:
                try:
                    diag_dir = Path("./diagnostics")
                    diag_dir.mkdir(parents=True, exist_ok=True)
                    safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", nodeid)
                    diag_path = diag_dir / f"{safe_name}_dom.json"
                    diag_path.write_text(json.dumps({"error": str(diag_err)}))
                except Exception:
                    pass


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    yield

    video_dirs = getattr(item, "_qcaq_video_dirs", [])
    for video_dir in video_dirs:
        if not video_dir.exists():
            continue

        for video_file in sorted(video_dir.glob("*.webm")):
            try:
                allure.attach.file(
                    str(video_file),
                    name=f"Test Video - {video_file.stem}",
                    attachment_type=AttachmentType.WEBM,
                )
            except Exception as err:
                print(f"Error due to exception in video attachment due to: {err}")
                pass


@pytest.fixture(scope="function")
def page(pages):
    return [p for _, p in pages]


# -------------------------------
# Helper: page by browser name
# -------------------------------
@pytest.fixture
def page_by_browser(pages):
    return {name: page for name, page in pages}


# -------------------------------
# Helper: Fetch OTP from Email via IMAP
# -------------------------------
def fetch_otp_from_email(
    recipient_email: str,
    subject_contains: str = "",
    timeout: int = 60,
    poll_interval: int = 5,
) -> str:
    """Fetch an OTP code from an email received via IMAP.

    Connects to the IMAP server specified by environment variables and polls
    for an unseen email sent to the given recipient. Extracts a 4-6 digit
    numeric OTP from the email body.

    Args:
        recipient_email: The email address that should appear in the TO field.
        subject_contains: Optional substring to match in the email subject.
        timeout: Maximum seconds to wait for the email.
        poll_interval: Seconds between each poll attempt.

    Returns:
        The OTP string (4-6 digits).

    Raises:
        TimeoutError: If no matching email arrives within the timeout.
        ValueError: If required IMAP environment variables are missing.
    """
    host = os.environ.get("IMAP_HOST")
    port_str = os.environ.get("IMAP_PORT")
    user = os.environ.get("IMAP_USER")
    password = os.environ.get("IMAP_PASSWORD")

    if not host or not port_str:
        raise ValueError(
            "IMAP_HOST and IMAP_PORT environment variables are required. "
            "Configure them in your QCAQ project environment settings."
        )

    port = int(port_str)
    use_ssl = port == 993
    otp_pattern = re.compile(r"\b(\d{4,6})\b")

    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            if use_ssl:
                mail = imaplib.IMAP4_SSL(host, port)
            else:
                mail = imaplib.IMAP4(host, port)

            if user:
                mail.login(user, password or "")

            mail.select("INBOX")

            search_criteria = f'(TO "{recipient_email}" UNSEEN)'
            if subject_contains:
                search_criteria = (
                    f'(TO "{recipient_email}" UNSEEN SUBJECT "{subject_contains}")'
                )

            status, data = mail.search(None, search_criteria)

            if status == "OK" and data[0]:
                msg_num = data[0].split()[-1]
                status, msg_data = mail.fetch(msg_num, "(RFC822)")

                if status == "OK" and msg_data[0]:
                    # FIX #1: replace broken walrus operator with clean index access
                    raw_email = (
                        msg_data[0][1]
                        if isinstance(msg_data[0], tuple)
                        else msg_data[0]
                    )
                    if isinstance(raw_email, bytes):
                        msg = email.message_from_bytes(raw_email)
                    else:
                        msg = email.message_from_string(raw_email)

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(
                                        part.get_content_charset() or "utf-8",
                                        errors="replace",
                                    )
                                    break
                            elif content_type == "text/html" and not body:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(
                                        part.get_content_charset() or "utf-8",
                                        errors="replace",
                                    )
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode(
                                msg.get_content_charset() or "utf-8",
                                errors="replace",
                            )

                    match = otp_pattern.search(body)
                    if match:
                        mail.store(msg_num, "+FLAGS", "\\Seen")
                        mail.logout()
                        return match.group(1)

                mail.store(msg_num, "+FLAGS", "\\Seen")

            mail.logout()
        except Exception:
            pass

        time.sleep(poll_interval)

    raise TimeoutError(
        f"No OTP email found for {recipient_email} within {timeout} seconds."
    )
