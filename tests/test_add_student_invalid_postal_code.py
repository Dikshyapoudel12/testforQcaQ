import pytest
import allure
import uuid
import random
from playwright.sync_api import expect

BASE_URL = "https://ai-samurai.tai.com.np"
ADMIN_EMAIL = "admin@tai.com.np"
ADMIN_PASSWORD = "admin123"

@allure.title("Fail to add student with invalid postal code format")
def test_fail_add_student_invalid_postal_code(page):
    # Generate valid unique data for mandatory fields
    unique_suffix = uuid.uuid4().hex[:8]
    student_name = f"Test Student {unique_suffix}"
    student_email = f"student_{unique_suffix}@example.com"
    student_phone = f"98{random.randint(10000000, 99999999)}"
    invalid_postal_code = "1234-AB"  # includes dash and letters, invalid format

    for p in page:
        with allure.step("Login as admin"):
            p.goto(f"{BASE_URL}/admin/login")
            p.fill('input[name="email"]', ADMIN_EMAIL)
            p.fill('input[name="password"]', ADMIN_PASSWORD)
            p.click('button[type="submit"]')

            expect(p).to_have_url(f"{BASE_URL}/admin", timeout=10000)

        with allure.step("Navigate to Add Student page"):
            p.goto(f"{BASE_URL}/admin/students/add-student")
            expect(p).to_have_url(f"{BASE_URL}/admin/students/add-student", timeout=10000)

        with allure.step("Wait for student name input to be visible"):
            if p.locator('input[name="name"]').count() > 0:
                name_input = p.locator('input[name="name"]')
            elif p.locator('input[placeholder*="Name"]').count() > 0:
                name_input = p.locator('input[placeholder*="Name"]')
            else:
                name_input = p.locator('form input').first
            expect(name_input).to_be_visible(timeout=10000)

        with allure.step("Fill student form with invalid postal code"):
            name_input.fill(student_name)

            if p.locator('input[name="email"]').count() > 0:
                p.fill('input[name="email"]', student_email)
            else:
                p.fill('input[placeholder*="Email"]', student_email)

            if p.locator('input[name="phone"]').count() > 0:
                p.fill('input[name="phone"]', student_phone)
            else:
                p.fill('input[placeholder*="Phone"]', student_phone)

            if p.locator('input[name="postal_code"]').count() > 0:
                p.fill('input[name="postal_code"]', invalid_postal_code)
            else:
                p.fill('input[placeholder*="Postal"]', invalid_postal_code)

        with allure.step("Find and click submit button"):
            submit_btn = None
            candidates = [
                'button:has-text("Register Now")',
                'button:has-text("Register")',
                'button:has-text("Submit")',
                'button[type="submit"]',
                'input[type="submit"]',
                '[role="button"]:has-text("Register")',
                '[role="button"]:has-text("Submit")',
                'text=/Register/i'
            ]
            for selector in candidates:
                if p.locator(selector).count() > 0:
                    btn = p.locator(selector).first
                    if btn.is_visible():
                        submit_btn = btn
                        break
            assert submit_btn is not None, "Submit button not found on Add Student page"
            submit_btn.click()

        with allure.step("Assert validation error for postal code"):
            error_locator = p.locator('text=/postal/i')
            if not error_locator.count() or not error_locator.is_visible():
                error_locator = p.locator('text=/invalid/i')
            expect(error_locator).to_be_visible(timeout=7000)
