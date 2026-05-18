import pytest
import allure
from playwright.sync_api import expect


@allure.feature("Forgot Password Flow")
@allure.story("Sending reset link without email address")
def test_sending_reset_link_without_email_address(page):
    base_url = "https://qcaq-dev.tai.com.np/signin"

    for p in page:
        with allure.step("Go to signin page"):
            p.goto(base_url)

        with allure.step("Click 'Forgot Password?' button"):
            # Assuming the button/link text is exactly 'Forgot Password?'
            p.click("text=Forgot Password?")

        with allure.step("Leave email field empty and click 'Send Reset Link' button"):
            # Ensure the email input is empty
            p.fill('input[name="email"]', '')
            # Click Send Reset Link button - assuming button text
            p.click("text=Send Reset Link")

        with allure.step("Verify validation error message for required email"):
            # Wait for validation error message to appear
            # The exact message text to assert or selector to wait for is not specified.
            # We will wait for an element containing text 'email is required' or similar.
            # This can be adjusted according to actual UI messages.
            expect(p.locator("text=email is required")).to_be_visible(timeout=5000)
