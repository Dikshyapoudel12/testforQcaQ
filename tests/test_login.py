import pytest
import allure
from playwright.sync_api import expect


BASE_URL = "https://ai-samurai.tai.com.np"
LOGIN_URL = f"{BASE_URL}/admin/login"
DASHBOARD_URL = f"{BASE_URL}/admin"
ADMIN_EMAIL = "admin@tai.com.np"
ADMIN_PASSWORD = "admin123"


def test_successful_login_with_valid_credentials(page):
    """
    Test Case: Successful login with valid credentials
    Preconditions: User is on the login page.
    Steps:
        1. Fill `email` with `admin@tai.com.np`
        2. Fill `password` with `admin123`
        3. Click `Login`
    Expected Result:
        Page redirects to https://ai-samurai.tai.com.np/admin after login success.
    """
    for p in page:
        with allure.step("Navigate to the login page"):
            p.goto(LOGIN_URL)

        with allure.step("Fill in the email"):
            p.fill('input[name="email"]', ADMIN_EMAIL)

        with allure.step("Fill in the password"):
            p.fill('input[name="password"]', ADMIN_PASSWORD)

        with allure.step("Click the Login button"):
            # Assuming the login button is either a button with text 'Login' or input[type=submit]
            # Use text selector to be more robust
            p.click('button:has-text("Login")')

        with allure.step("Verify successful login by URL redirection"):
            expect(p).to_have_url(DASHBOARD_URL, timeout=10000)
