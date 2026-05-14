import pytest
import uuid
import random
import allure
from playwright.sync_api import expect

def test_fail_to_add_student_with_invalid_email_format(page):
    base_url = "https://ai-samurai.tai.com.np"
    admin_email = "admin@tai.com.np"
    admin_password = "admin123"
    invalid_email = f"user_{uuid.uuid4().hex[:8]}@gmail.com"  # invalid email, must end with @kokorozashi.info

    # Generate other mandatory valid fields for student
    first_name = f"First{uuid.uuid4().hex[:6]}"
    last_name = f"Last{uuid.uuid4().hex[:6]}"
    student_phone = f"98{random.randint(10000000, 99999999)}"
    student_address = "123 Test Street"
    student_password = "Test@1234"

    for p in page:
        with allure.step("Navigate to login page"):
            p.goto(f"{base_url}/admin/login")

        with allure.step("Login as admin"):
            p.fill('input[name="email"]', admin_email)
            p.fill('input[name="password"]', admin_password)
            p.click('button[type="submit"]')

            expect(p).to_have_url(f"{base_url}/admin", timeout=10000)

        with allure.step("Navigate to add student page"):
            p.goto(f"{base_url}/admin/students/add-student")
            expect(p).to_have_url(f"{base_url}/admin/students/add-student", timeout=5000)

        with allure.step("Fill student form with invalid email and valid other fields"):
            p.fill('input[name="email"]', invalid_email)
            p.fill('input[name="firstName"]', first_name)
            p.fill('input[name="lastName"]', last_name)
            p.fill('input[name="phone"]', student_phone)
            p.fill('input[name="address"]', student_address)
            p.fill('input[name="password"]', student_password)
            p.fill('input[name="password_confirmation"]', student_password)

        with allure.step('Click "Proceed to confirmation" button'):
            p.locator('button:has-text("Proceed to confirmation")').click()

        with allure.step("Wait and assert validation error for invalid email domain"):
            p.wait_for_timeout(2000)
            error_message_locator = p.locator('text=/@kokorozashi\.info/i')
            expect(error_message_locator).to_be_visible(timeout=5000)
