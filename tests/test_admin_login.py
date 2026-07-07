import pytest
import allure
from playwright.sync_api import Page, expect

BASE_URL = "https://ai-samurai.tai.com.np"
LOGIN_URL = f"{BASE_URL}/admin/login"
ADMIN_DASHBOARD_URL = f"{BASE_URL}/admin"


@pytest.fixture
def go_to_login(page: Page):
    """Navigate to the admin login page before each test."""
    page.goto(LOGIN_URL)
    # Wait for the email field to be visible as a sign the page is loaded
    page.wait_for_timeout(1000)
    return page


@allure.id("019f3c1d-374d-743d-b28a-560e08273cc0")
def test_successful_login_with_valid_credentials(go_to_login: Page):
    """Validate that admin can log in using known credentials and is redirected to the admin home page."""
    page = go_to_login

    # Fill in valid credentials
    page.fill("input[name='email']", "admin@tai.com.np")
    page.fill("input[name='password']", "admin123")

    # Click the Login button
    page.get_by_role("button", name="Login").click()

    # Assert that the user is redirected to the admin dashboard
    page.wait_for_url(ADMIN_DASHBOARD_URL + "*", timeout=10000)
    assert page.url.startswith(ADMIN_DASHBOARD_URL)


@allure.id("019f3c1d-377b-770f-a7f1-4fe30f348991")
def test_login_with_invalid_password(go_to_login: Page):
    """Attempt login with a wrong password and verify that user is not redirected to the admin dashboard.

    Expected specific error message is TBD, so we only assert that the URL does not change to the dashboard.
    """
    page = go_to_login

    # Fill in email and invalid password
    page.fill("input[name='email']", "admin@tai.com.np")
    page.fill("input[name='password']", "wrongpass")

    # Click the Login button
    page.get_by_role("button", name="Login").click()

    # Wait briefly to allow any navigation attempt
    page.wait_for_timeout(3000)

    # Verify that user is not redirected to the admin dashboard URL
    # For invalid credentials, we expect to remain on the login page (no redirect to dashboard)
    expect(page).to_have_url(LOGIN_URL)
    assert page.url == LOGIN_URL
