import os
import pytest
import allure
from playwright.sync_api import expect

def test_verify_login_button_is_clickable(page):
    """
    Test Case: Verify login button is clickable
    Preconditions: User is on the login page.
    Steps:
      - Fill `email` with ${ADMIN_USERNAME}
      - Fill `password` with ${ADMIN_PASSWORD}
      - Click `Login`
    Expected Result:
      - User is redirected to ${BASE_URL}/admin
    """
    login_url = os.environ.get("LOGIN_URL")
    base_url = os.environ.get("BASE_URL", "").rstrip("/")
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")

    for p in page:
        with allure.step("Navigate to login page"):
            p.goto(login_url)

        with allure.step("Fill email and password fields"):
            p.fill('input[name="email"]', username)
            p.fill('input[name="password"]', password)

        with allure.step("Click Login button"):
            p.click('button:has-text("Login")')

        with allure.step("Verify redirect to admin URL"):
            expect(p).to_have_url(f"{base_url}/admin", timeout=10000)
