import pytest
import allure
from playwright.sync_api import expect

BASE_URL = "https://ai-samurai.tai.com.np/admin/login"
PASSWORD = "admin123"


def test_login_fails_with_empty_email(page):
    """
    Test Case: Login fails with empty email
    Preconditions:
        - User is on the login page.
    Steps:
        1. Leave `email` empty
        2. Fill `password` with `admin123`
        3. Click `Login`
    Expected Result:
        - Validation error indicating email is required.
    """
    for p in page:
        with allure.step("Navigate to login page"):
            p.goto(BASE_URL)

        with allure.step("Leave email empty and fill password"):
            p.fill('input[name="email"]', "")
            p.fill('input[name="password"]', PASSWORD)

        with allure.step("Click Login button"):
            p.click('button[type="submit"]')

        with allure.step("Check for validation error about missing email"):
            error_locator = p.locator('#email-helper-text')
            error_locator.wait_for(state="visible", timeout=5000)
            error_text = error_locator.inner_text().lower()
            assert "email" in error_text and "required" in error_text, \
                f"Expected validation error about email required, got: {error_text}"
