import pytest
import allure
from playwright.sync_api import expect

BASE_URL = "https://qcaq-dev.tai.com.np"
SIGNIN_URL = f"{BASE_URL}/signin"
DASHBOARD_URL = f"{BASE_URL}/dashboard"
VALID_EMAIL = "aman@tai.com"
VALID_PASSWORD = "Aman1234"
WELCOME_TEXT = "Welcome back! Here's an overview of your test automation."

def fill_first_visible(p, selectors, value):
    for selector in selectors:
        locator = p.locator(selector)
        if locator.count() > 0 and locator.is_visible():
            locator.fill(value)
            return True
    raise RuntimeError(f"None of the selectors matched visible element for value {value}: {selectors}")

def test_successful_login_with_valid_credentials(page):
    for p in page:
        with allure.step("Navigate to signin page"):
            p.goto(SIGNIN_URL)
            p.wait_for_load_state("networkidle", timeout=10000)

        with allure.step("Fill in email and password, then click Signin"):
            fill_first_visible(p, ['#email', 'input[name="email"]', 'input[type="email"]'], VALID_EMAIL)
            fill_first_visible(p, ['#password', 'input[name="password"]', 'input[type="password"]'], VALID_PASSWORD)

            btn = p.locator('button[type="submit"]')
            if btn.count() == 0:
                btn = p.locator('button').first
            btn.click()

        with allure.step("Verify redirected to dashboard and welcome text is visible"):
            expect(p).to_have_url(DASHBOARD_URL, timeout=10000)
            expect(p.locator(f"text={WELCOME_TEXT}")).to_be_visible()
