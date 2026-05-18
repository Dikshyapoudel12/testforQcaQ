import uuid
import pytest
import allure
from playwright.sync_api import expect

SIGNUP_URL = "https://qcaq-dev.tai.com.np/signup"
FIRST_NAME = "TestUser"
PASSWORD = "Hiup@123"

@allure.title("Successful signup with valid data")
def test_successful_signup_with_valid_data(page):
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"

    for p in page:
        with allure.step("Navigate to the signup page"):
            p.goto(SIGNUP_URL)
            if "/signin" in p.url:
                pytest.skip("Signup page redirects to signin page, cannot test signup flow.")

        with allure.step("Fill First Name"):
            first_name_selector_candidates = [
                'input[name="firstName"]',
                'input[name="first_name"]',
                'input[type="text"]:nth-of-type(1)',
                'input:visible >> nth=0',
            ]
            filled = False
            for selector in first_name_selector_candidates:
                try:
                    p.fill(selector, FIRST_NAME)
                    filled = True
                    break
                except Exception:
                    continue
            if not filled:
                raise Exception("Failed to fill the First Name field")

        with allure.step("Fill Email Address with unique email using get_by_placeholder"):
            p.get_by_placeholder("Email Address").fill(unique_email)

        with allure.step("Fill Create Password"):
            p.fill('input[name="password"]', PASSWORD)

        with allure.step("Fill Confirm Password"):
            p.fill('input[name="confirmPassword"]', PASSWORD)

        with allure.step("Click Sign Up button"):
            p.click('button:has-text("Sign Up")')

        with allure.step("Wait for heading 'Verify your email' to be visible"):
            expect(p.locator("text=Verify your email")).to_be_visible(timeout=10000)
