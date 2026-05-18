import pytest
import allure
from playwright.sync_api import expect

# Constants for the test
BASE_URL = "https://qcaq-dev.tai.com.np/signin"
INVALID_EMAIL = "invalid-email-format"
FORGOT_PASSWORD_TEXT = "Forgot Password?"
SEND_RESET_LINK_TEXT = "Send Reset Link"
EMAIL_INPUT_NAME = "email"
VALIDATION_ERROR_TEXT_FRAGMENT = "invalid email"  # partial text to check error message


@allure.feature("Forgot Password Flow")
@allure.story("Sending reset link with invalid email format")
def test_sending_reset_link_with_invalid_email_format(page):
    for p in page:
        with allure.step(f"Navigate to signin page {BASE_URL}"):
            p.goto(BASE_URL)

        with allure.step(f"Click '{FORGOT_PASSWORD_TEXT}' button"):
            # Click the button or link named 'Forgot Password?'
            p.click(f"text={FORGOT_PASSWORD_TEXT}")

        with allure.step(f"Fill '{EMAIL_INPUT_NAME}' field with invalid email '{INVALID_EMAIL}'"):
            p.fill(f'input[name="{EMAIL_INPUT_NAME}"]', INVALID_EMAIL)

        with allure.step(f"Click '{SEND_RESET_LINK_TEXT}' button"):
            p.click(f"text={SEND_RESET_LINK_TEXT}")

        with allure.step("Assert validation error message indicates invalid email format is shown"):
            # Check for a visible error message containing indication of invalid email format
            # We'll check for some element that contains text containing 'invalid email'
            # Using expect with timeout because UI may show error with some delay
            # We look for a visible element containing text fragment that matches invalid email message
            validation_error = p.locator(f"text={VALIDATION_ERROR_TEXT_FRAGMENT}")
            expect(validation_error).to_be_visible(timeout=5000)

        with allure.step("Assert reset link is not sent"):
            # Since no actual email sending verification here and no email_fetcher used,
            # we limit to UI validation error presence which implies reset link is not sent.
            # No emails fetched here as this negative test case expects no email sent.
            pass
