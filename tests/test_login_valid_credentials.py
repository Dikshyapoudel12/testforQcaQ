import pytest
import allure
from playwright.sync_api import expect


BASE_URL = "https://ai-samurai.tai.com.np"
LOGIN_URL = f"{BASE_URL}/admin/login"
DASHBOARD_URL = f"{BASE_URL}/admin"
ADMIN_EMAIL = "admin@tai.com.np"
ADMIN_PASSWORD = "admin123"


@allure.title("Successful login with valid credentials")
@allure.description("Verify user can login with valid admin credentials and is redirected to admin dashboard")
@allure.severity(allure.severity_level.CRITICAL)
def test_successful_login_with_valid_credentials(page):
    for p in page:
        with allure.step("Navigate to login page"):
            p.goto(LOGIN_URL)

        with allure.step("Fill login form with valid credentials"):
            p.fill('input[name="email"]', ADMIN_EMAIL)
            p.fill('input[name="password"]', ADMIN_PASSWORD)

        with allure.step("Click the Login button"):
            # Assuming button text or type submit
            p.click('button:has-text("Login")')

        with allure.step("Verify redirection to admin dashboard"):
            expect(p).to_have_url(DASHBOARD_URL, timeout=10000)
