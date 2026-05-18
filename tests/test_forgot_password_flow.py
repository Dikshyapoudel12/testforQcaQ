import pytest
import allure
from playwright.sync_api import expect


@allure.feature("Forgot Password Flow")
@allure.title("Send reset link with valid email address")
def test_send_reset_link_with_valid_email(page):
    base_url = "https://qcaq-dev.tai.com.np/signin"
    test_email = "deekshyap@gmail.com"

    for p in page:
        with allure.step("Navigate to signin page"):
            p.goto(base_url)

        with allure.step("Click 'Forgot Password?' button"):
            # Click button or link labeled 'Forgot Password?'
            # Trying by text selector first
            p.click("text=Forgot Password?")

        with allure.step("Fill email field with valid email"):
            p.fill('input[name="email"]', test_email)

        with allure.step("Click 'Send Reset Link' button"):
            # Assuming the button has text 'Send Reset Link'
            p.click("text=Send Reset Link")

        with allure.step("Wait for confirmation message 'Email sent successfully'"):
            confirmation = p.locator("text=Email sent successfully")
            expect(confirmation).to_be_visible(timeout=10000)  # 10 seconds timeout

        # Optionally, assert final URL or other states here if needed

        # Test ends here
