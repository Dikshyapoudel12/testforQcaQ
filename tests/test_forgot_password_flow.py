import pytest
import allure
from playwright.sync_api import expect

def test_send_reset_link_with_valid_email_address(page):
    base_url = "https://qcaq-dev.tai.com.np/signin"
    test_email = "deekshyap@gmail.com"
    confirmation_text = "Email sent successfully"

    for p in page:
        with allure.step("Navigate to signin page"):
            p.goto(base_url)

        with allure.step("Click the 'Forgot Password?' button on signin page"):
            # The locator :has-text('Forgot Password?') matches many elements including container divs.
            # Use the button role with name for stricter match.
            forgot_password_button = p.get_by_role("button", name="Forgot password?")
            forgot_password_button.wait_for(state='visible', timeout=5000)
            forgot_password_button.click()

        with allure.step("Fill the 'email' field with valid email"):
            p.fill('input[name="email"]', test_email)

        with allure.step("Click the 'Send Reset Link' button"):
            send_reset_link_btn = p.locator("button:has-text('Send Reset Link')")
            send_reset_link_btn.wait_for(state='visible', timeout=5000)
            send_reset_link_btn.click()

        with allure.step("Verify confirmation message 'Email sent successfully' is visible"):
            expect(p.locator(f"text={confirmation_text}")).to_be_visible(timeout=10000)
