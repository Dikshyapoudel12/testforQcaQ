import pytest
import allure
import uuid
import random
from datetime import date
from playwright.sync_api import expect
import time


ADMIN_EMAIL = "admin@tai.com.np"
ADMIN_PASSWORD = "admin123"
LOGIN_URL = "https://ai-samurai.tai.com.np/admin/login"
ADD_STUDENT_URL = "https://ai-samurai.tai.com.np/admin/students/add-student"


def generate_random_email():
    return f"user_{uuid.uuid4().hex[:8]}@kokorozashi.info"


def generate_random_phone():
    # random 11 digit phone number starting with 9 or 8 or 7 for realism
    return f"{random.choice(['9','8','7'])}{random.randint(1000000000, 9999999999)}"


def generate_password():
    # Password with uppercase, lowercase, and number
    # Example: Test1234
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
        last_name_katakana = "スズキ"
        first_name_katakana = "タロウ"
        phone = generate_random_phone()
        email = generate_random_email()
        postal_code = f"{random.randint(10000, 99999)}"
        address = "123 Tokyo Street"
        nationality = "Japanese"
        hobby = "Reading"
        password = generate_password()
        gender = "male"

        with allure.step("Fill student form"):
            p.fill('input[name="lastName"]', last_name)
            p.fill('input[name="firstName"]', first_name)
            p.fill('input[name="lastNameKatakana"]', last_name_katakana)
            p.fill('input[name="firstNameKatakana"]', first_name_katakana)
            p.fill('input[name="phone"]', phone)
            p.fill('input[name="email"]', email)

            # Batch dropdown
            combobox_selector = 'div#batch_id[role="combobox"]'
            p.click(combobox_selector)
            time.sleep(0.5)  # wait 500 ms for options to load

            options = p.query_selector_all('div[role="listbox"] div[role="option"]')
            visible_options = [opt for opt in options if opt.is_visible()]

            if len(visible_options) > 1:
                visible_options[1].click()
                batch_option_text = visible_options[1].inner_text()
            elif len(visible_options) == 1:
                visible_options[0].click()
                batch_option_text = visible_options[0].inner_text()
            else:
                batch_option_text = None

            combobox_text = p.locator(combobox_selector).inner_text()
            if combobox_text.strip() == "Select Batch":
                val = p.locator(f'{combobox_selector} input[name="batch_id"]').input_value()
                batch_id_present = val.strip() != ""
                assert batch_id_present, "batch_id input is empty after selection"
            else:
                assert combobox_text.strip() != "Select Batch", "Batch combobox text did not change after selection"

            # Date of birth
            p.click('button[data-testid="CalendarIcon"]')
            p.click(f'[aria-current="date"]')

            # Gender
            p.click(f'button[value="{gender}"]')

            p.fill('input[name="postal_code"]', postal_code)
            p.fill('input[name="address"]', address)
            p.fill('input[name="nationality"]', nationality)
            p.fill('input[name="hobby"]', hobby)

            # Current country dropdown
            p.click('div#current_country_id[role="combobox"]')
            time.sleep(0.5)
            country_options = p.query_selector_all('div[role="listbox"] div[role="option"]')
            visible_countries = [opt for opt in country_options if opt.is_visible()]
            if len(visible_countries) > 1:
                visible_countries[1].click()
            elif len(visible_countries) == 1:
                visible_countries[0].click()

            p.fill('input[name="password"]', password)
            p.fill('input[name="password_confirmation"]', password)

        with allure.step("Submit the form and confirm registration"):
            p.click('button:has-text("Proceed to confirmation")')
            p.wait_for_timeout(1000)
            p.click('button:has-text("Register Now")')

            p.wait_for_timeout(3000)

            not_on_add_student_page = p.url != ADD_STUDENT_URL
            success_text_conditions = any([
                p.locator("text=successfully registered").count() > 0,
                p.locator("text=登録完了").count() > 0,
                p.locator("text=Registration completed").count() > 0,
            ])

            assert not_on_add_student_page or success_text_conditions, \
                "Student registration might have failed: still on add form page without success message"
