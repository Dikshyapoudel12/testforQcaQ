import pytest
import allure
from playwright.sync_api import expect

BASE_URL = "https://qcaq-dev.tai.com.np"
SIGNIN_URL = f"{BASE_URL}/signin"
PASSWORD = "Aman1234"

def test_login_fails_with_empty_email_address(page):
    """
    Test Case: Login fails with empty email address
    Preconditions: User is on the signin page at https://qcaq-dev.tai.com.np/signin.
    Steps:
      1. Leave email empty
      2. Fill password with Aman1234
      3. Click Signin
    Expected Result:
      Validation error indicating that email address is required is displayed.
    """
    for p in page:
        with allure.step("Navigate to signin page"):
            p.goto(SIGNIN_URL)
            p.wait_for_load_state("networkidle")

        with allure.step("Locate email input field"):
            email_selector = None
            selectors_to_try = [
                'input[name="email"]',
                'input[type="email"]',
                'input[placeholder*="email"]',
            ]
            for sel in selectors_to_try:
                try:
                    p.wait_for_selector(sel, timeout=5000)
                    email_selector = sel
                    break
                except Exception:
                    pass
            if email_selector is None:
                try:
                    form = p.query_selector('form')
                    if form:
                        input_el = form.query_selector('input[type=text]')
                        if input_el:
                            email_selector = 'form input[type=text]'
                except Exception:
                    pass
            assert email_selector is not None, "Failed to locate email input field"

        with allure.step("Locate password input field"):
            password_selector = None
            selectors_to_try_pw = [
                'input[name="password"]',
                'input[type="password"]',
                'input[placeholder*="password"]',
            ]
            for sel in selectors_to_try_pw:
                try:
                    p.wait_for_selector(sel, timeout=5000)
                    password_selector = sel
                    break
                except Exception:
                    pass
            assert password_selector is not None, "Failed to locate password input field"

        with allure.step("Fill password and leave email empty"):
            p.fill(email_selector, "")
            p.fill(password_selector, PASSWORD)

        with allure.step("Check if form is valid before submit"):
            form_valid = p.evaluate("() => { const form = document.querySelector('form'); return form ? form.checkValidity() : false; }")
            assert not form_valid, "Form validation passed unexpectedly with empty email"

        with allure.step("Try to click Signin button"):
            signin_button = p.locator('button[type="submit"]')
            # Check if button disabled
            disabled = signin_button.is_disabled()
            # It is acceptable if button is disabled or click prevented
            if not disabled:
                signin_button.click()

        with allure.step("Verify we remain on signin page"):
            expect(p).to_have_url(SIGNIN_URL, timeout=3000)
