import os
import pytest
import allure
from playwright.sync_api import expect


@allure.feature("User Login")
@allure.story("Successful login with valid admin credentials")
def test_successful_login_with_valid_admin_credentials(page):
    base_login_url = "https://ai-samurai.tai.com.np/admin/login"
    expected_post_login_url_suffix = "/admin"

    admin_username = os.environ.get("ADMIN_USERNAME")
    admin_password = os.environ.get("ADMIN_PASSWORD")

    for p in page:
        with allure.step("Navigate to the login page"):
            p.goto(base_login_url)

        with allure.step("Fill email with admin username"):
            p.fill('input[name="email"]', admin_username)

        with allure.step("Fill password with admin password"):
            p.fill('input[name="password"]', admin_password)

        with allure.step("Click Login button"):
            p.click("button:has-text('Login')")

        with allure.step("Verify redirection to admin dashboard after login"):
            p.wait_for_load_state("networkidle", timeout=10000)
            current_url = p.url
            assert current_url.endswith(expected_post_login_url_suffix), f"Expected URL to end with {expected_post_login_url_suffix} but got {current_url}"
