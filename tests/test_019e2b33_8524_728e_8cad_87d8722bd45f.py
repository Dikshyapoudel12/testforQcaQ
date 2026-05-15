import pytest
import allure
from playwright.sync_api import expect

BASE_URL = "https://qcaq-dev.tai.com.np/signin"
INVALID_EMAIL = "invalid-email-format"
PASSWORD = "Aman1234"

def test_login_fails_with_invalid_email_format(page):
    for p in page:
        with allure.step(f"Navigate to signin page {BASE_URL}"):
            p.goto(BASE_URL)
            p.wait_for_load_state("networkidle")

        with allure.step("Fill email with invalid format"):
            email_input = p.locator('input[placeholder="Email address"]')
            email_input.fill(INVALID_EMAIL)

        with allure.step("Fill password correctly"):
            password_input = p.locator('input[placeholder="Password"]')
            password_input.fill(PASSWORD)

        with allure.step("Click Sign In button"):
            p.click('button:has-text("Sign In")')

        with allure.step("Assert page did not navigate away from signin"):
            expect(p).to_have_url(BASE_URL, timeout=3000)

        with allure.step("Assert email input is invalid"):
            # Check validity via JS eval
            is_valid = email_input.evaluate("(el) => el.checkValidity()")
            assert not is_valid, "Email input is valid, expected invalid due to wrong format"
