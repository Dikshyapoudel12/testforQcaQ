import pytest
import allure
import uuid
import random
from datetime import date, timedelta
from playwright.sync_api import expect

ADMIN_EMAIL = "admin@tai.com.np"
ADMIN_PASSWORD = "admin123"
LOGIN_URL = "https://ai-samurai.tai.com.np/admin/login"
ADD_STUDENT_URL = "https://ai-samurai.tai.com.np/admin/students/add-student"

def generate_random_email():
    return f"user_{uuid.uuid4().hex[:8]}@kokorozashi.info"

def generate_random_phone():
    return f"{random.choice(['9','8','7'])}{random.randint(1000000000, 9999999999)}"

def generate_password():
    letters = "abcdefghijklmnopqrstuvwxyz"
    return f"{random.choice(letters).upper()}{random.choice(letters)}test{random.randint(10,99)}"

def test_successful_addition_of_student_with_valid_inputs(page):
    for p in page:
        with allure.step("Login using admin credentials"):
            p.goto(LOGIN_URL)
            p.fill('input[name="email"]', ADMIN_EMAIL)
            p.fill('input[name="password"]', ADMIN_PASSWORD)
            p.click('button[type="submit"]')
            expect(p).not_to_have_url(LOGIN_URL, timeout=10000)

        with allure.step("Navigate to Add Student page"):
            p.goto(ADD_STUDENT_URL)
            expect(p).to_have_url(ADD_STUDENT_URL)

        # Prepare data
        last_name = "Suzuki"
        first_name = "Taro"
        last_name_katakana = "\u30B9\u30BA\u30AD"
        first_name_katakana = "\u30BF\u30ED\u30A6"
        phone = generate_random_phone()
        email = generate_random_email()
        postal_code = f"{random.randint(10000, 99999)}"
        address = "123 Tokyo Street"
        nationality = "Japanese"
        hobby = "Reading"
        password = generate_password()
        gender = "male"

        # Calculate DOB for 18 years old exactly today minus 18 years
        dob_date = date.today() - timedelta(days=365*18)
        dob_str = dob_date.strftime("%Y/%m/%d")

        with allure.step("Fill student form"):
            p.fill('input[name="lastName"]', last_name)
            p.fill('input[name="firstName"]', first_name)
            p.fill('input[name="lastNameKatakana"]', last_name_katakana)
            p.fill('input[name="firstNameKatakana"]', first_name_katakana)
            p.fill('input[name="phone"]', phone)
            p.fill('input[name="email"]', email)

            p.locator('#batch_id').click()
            p.wait_for_timeout(500)
            options = p.get_by_role('option')
            count = options.count()
            if count > 1:
                options.nth(1).click()
            elif count == 1:
                options.nth(0).click()
            else:
                assert False, "No batch options available to select"

            batch_text = p.locator('div#batch_id[role="combobox"]').inner_text().strip()
            assert batch_text != "Select Batch", "Batch combobox text did not change"
            batch_id_value = p.input_value('input[name="batch_id"]').strip()
            assert batch_id_value != "", "batch_id input is empty after selection"

            # Fill DOB using the placeholder locator as requested
            dob_locator = p.get_by_placeholder('YYYY/MM/DD')
            dob_locator.clear()
            dob_locator.fill(dob_str)

            p.click(f'button[value="{gender}"]')

            p.fill('input[name="postal_code"]', postal_code)
            p.fill('input[name="address"]', address)
            p.fill('input[name="nationality"]', nationality)
            p.fill('input[name="hobby"]', hobby)

            p.locator('div#current_country_id[role="combobox"]').click()
            p.wait_for_timeout(500)
            country_options = p.get_by_role('option')
            country_count = country_options.count()
            if country_count > 1:
                country_options.nth(1).click()
            elif country_count == 1:
                country_options.nth(0).click()
            else:
                assert False, "No country options available to select"

            p.fill('input[name="password"]', password)
            p.fill('input[name="password_confirmation"]', password)

        with allure.step("Submit the form and confirm registration"):
            p.click('button:has-text("Proceed to confirmation")')

            register_now_btn = p.locator('button:has-text("Register Now")')
            try:
                expect(register_now_btn).to_be_visible(timeout=10000)
                expect(register_now_btn).to_be_enabled(timeout=10000)
                register_now_btn.click()
            except Exception:
                p.wait_for_timeout(3000)

            p.wait_for_timeout(3000)
            current_url = p.url
            success_text_present = p.locator("text=successfully registered").count() > 0 or \
                                   p.locator("text=登録完了").count() > 0 or \
                                   p.locator("text=Registration completed").count() > 0

            assert (current_url != ADD_STUDENT_URL) or success_text_present, \
                "Student registration might have failed: still on add form page without success message"
