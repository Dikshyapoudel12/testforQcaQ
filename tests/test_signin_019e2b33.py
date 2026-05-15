import pytest
import allure
from playwright.sync_api import expect

BASE_URL = "https://qcaq-dev.tai.com.np"
SIGNIN_URL = f"{BASE_URL}/signin"
TEST_EMAIL = "aman@tai.com"


def test_login_fails_with_empty_password(page):
    """
    Test Case ID: 019e2b33-81b5-72c3-ba42-f9b802664b3a
    Title: Login fails with empty password
    Preconditions: User is on the signin page.
    Steps:
        1. Fill email with aman@tai.com
        2. Leave password empty
        3. Click Sign In
    Expected Result:
        Validation error indicating that password is required is displayed.
    """
    for p in page:
        with allure.step("Navigate to signin page"):
            p.goto(SIGNIN_URL)

        with allure.step("Fill email and leave password empty"):
            p.fill('input[placeholder="Email address"]', TEST_EMAIL)
            p.fill('input[placeholder="Password"]', "")

        with allure.step("Click Sign In button"):
            # Click triggers browser native validation
            p.click('button[type="submit"]:has-text("Sign In")')

        with allure.step("Check native validation message of password input"):
            validation_message = p.eval_on_selector(
                'input[placeholder="Password"]', "el => el.validationMessage"
            )
            assert validation_message != "", f"Expected validation message but got empty"
            assert "fill" in validation_message.lower() or "required" in validation_message.lower(), \
                f"Unexpected validation message: {validation_message}"
