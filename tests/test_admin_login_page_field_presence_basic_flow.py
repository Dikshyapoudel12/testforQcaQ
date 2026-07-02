import pytest
import allure
from playwright.sync_api import Page, expect


BASE_URL = "https://ai-samurai.tai.com.np"
ADMIN_LOGIN_URL = f"{BASE_URL}/admin/login"
ADMIN_DASHBOARD_URL = f"{BASE_URL}/admin"


@pytest.fixture
def admin_login_page(page: Page) -> Page:
    """Navigate to the admin login page and return the page object."""
    page.goto(ADMIN_LOGIN_URL)
    expect(page).to_have_url(ADMIN_LOGIN_URL)
    return page


def fill_login_form(page: Page, email: str | None = None, password: str | None = None) -> None:
    """Helper to fill the admin login form with given credentials (if provided)."""
    if email is not None:
        page.get_by_label("Email").fill(email)
    if password is not None:
        page.get_by_label("Password").fill(password)


@allure.id("019f21b3-5682-77fa-b3f2-f7f0811cfa78")
def test_successful_admin_login_with_valid_credentials(admin_login_page: Page) -> None:
    """Positive happy path login using provided admin credentials."""
    page = admin_login_page

    fill_login_form(page, email="admin@tai.com.np", password="admin123")

    # Click Login button
    page.get_by_role("button", name="Login").click()

    # Expect redirect to admin dashboard
    expect(page).to_have_url(ADMIN_DASHBOARD_URL, timeout=15000)


@allure.id("019f21b3-5699-7697-b881-163a1f2b6c18")
def test_login_attempt_with_empty_email_field(admin_login_page: Page) -> None:
    """Negative test: empty email field on login attempt.

    Expected behavior is TBD in the requirements, so we validate generic, stable behavior:
    - User should NOT be redirected to the admin dashboard
    - Login page should remain visible
    """
    page = admin_login_page

    # Only fill password, leave email empty
    fill_login_form(page, password="admin123")

    page.get_by_role("button", name="Login").click()

    # The user should remain on the login page (no redirect to dashboard)
    expect(page).not_to_have_url(ADMIN_DASHBOARD_URL)
    expect(page).to_have_url(ADMIN_LOGIN_URL)


@allure.id("019f21b3-56a5-7346-a6c3-9b9524097f79")
def test_login_attempt_with_empty_password_field(admin_login_page: Page) -> None:
    """Negative test: empty password field on login attempt.

    Expected behavior is TBD; we assert that login does not succeed and no redirect occurs.
    """
    page = admin_login_page

    # Only fill email, leave password empty
    fill_login_form(page, email="admin@tai.com.np")

    page.get_by_role("button", name="Login").click()

    # The user should remain on the login page (no redirect to dashboard)
    expect(page).not_to_have_url(ADMIN_DASHBOARD_URL)
    expect(page).to_have_url(ADMIN_LOGIN_URL)


@allure.id("019f21b3-56b1-7794-a82f-1fd30935dd40")
def test_login_attempt_with_invalid_email_and_or_password(admin_login_page: Page) -> None:
    """Negative test for invalid credentials using wrong password.

    We assert that:
    - User is not redirected to the admin dashboard
    - An error message is displayed to the user (generic assertion based on visible text)
    """
    page = admin_login_page

    # Use a clearly invalid password
    fill_login_form(page, email="admin@tai.com.np", password="wrongpassword123!")

    page.get_by_role("button", name="Login").click()

    # Assert no redirect to dashboard
    expect(page).not_to_have_url(ADMIN_DASHBOARD_URL)

    # Try to assert a generic error feedback; if the exact text changes, this may need updating
    possible_error_locators = [
        page.get_by_text("Invalid", exact=False),
        page.get_by_text("incorrect", exact=False),
        page.get_by_text("error", exact=False),
    ]

    # At least one of the generic error indicators should become visible
    any_visible = False
    for locator in possible_error_locators:
        try:
            locator.wait_for(timeout=3000, state="visible")
            any_visible = True
            break
        except Exception:
            continue

    assert any_visible, "Expected some error indication for invalid credentials, but none was found."
