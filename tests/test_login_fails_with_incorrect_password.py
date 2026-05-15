import pytest
import allure
from playwright.sync_api import expect


@allure.title("Login fails with incorrect password")
def test_login_fails_with_incorrect_password(page):
    base_url = "https://qcaq-dev.tai.com.np"
    signin_url = f"{base_url}/signin"
    valid_email = "aman@tai.com"
    invalid_password = "WrongPassword123"
    
    for p in page:
        with allure.step("Navigate to signin page"):
            p.goto(signin_url)
        
        with allure.step("Fill email and incorrect password"):
            p.fill('input[placeholder="Email address"]', valid_email)
            p.fill('input[placeholder="Password"]', invalid_password)
        
        with allure.step("Click Sign In button"):
            p.click('button[type="submit"]')

        with allure.step("Wait for sign in button to be visible again"):
            sign_in_button = p.locator('button[type="submit"]')
            sign_in_button.wait_for(state="visible", timeout=5000)
        
        with allure.step("Verify URL did NOT change to /dashboard"):
            assert not p.url.startswith(f"{base_url}/dashboard"), "Unexpected redirect to dashboard on failed login"
        
        with allure.step("Verify page shows some authentication error keyword"):
            content = p.content().lower()
            error_keywords = ["invalid", "incorrect", "email", "password", "failed"]
            assert any(keyword in content for keyword in error_keywords), "No authentication error message displayed"
