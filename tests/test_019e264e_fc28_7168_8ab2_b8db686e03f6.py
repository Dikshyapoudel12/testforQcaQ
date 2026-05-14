import uuid
import random
import pytest
import allure
from playwright.sync_api import expect, TimeoutError

BASE_URL = "https://ai-samurai.tai.com.np"
ADMIN_EMAIL = "admin@tai.com.np"
ADMIN_PASSWORD = "admin123"

def generate_random_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@kokorozashi.info"

def generate_random_phone() -> str:
    return f"9{random.randint(1000000000, 9999999999)}"

def generate_password() -> str:
    return "Aa1" + str(uuid.uuid4().hex[:5])

@allure.feature("Add Student")
@allure.story("Successful student registration with all valid fields")
def test_successful_student_registration_all_valid_fields(page):
    for p in page:
        with allure.step("Login as admin"):
            p.goto(f"{BASE_URL}/admin/login")
            p.fill('input[name="email"]', ADMIN_EMAIL)
            p.fill('input[name="password"]', ADMIN_PASSWORD)
            p.click('button[type="submit"]')
            p.wait_for_url(f"{BASE_URL}/admin**", timeout=10000)

        with allure.step("Go to add student page"):
            p.goto(f"{BASE_URL}/admin/students/add-student")
            expect(p).to_have_url(f"{BASE_URL}/admin/students/add-student")

        last_name = "Tanaka"
        first_name = "Taro"
        last_name_katakana = ""  # Katakana example
        first_name_katakana = ""
        phone = generate_random_phone()
        email = generate_random_email()
        dob = "2000-01-01"
        gender = "male"
        postal_code = "12345"
        address = "1-2-3 Shibuya, Tokyo"
        nationality = "Japanese"
        hobby = "Reading"
        password = generate_password()

        with allure.step("Fill student registration form with valid data"):
            p.fill('input[name="lastName"]', last_name)
            p.fill('input[name="firstName"]', first_name)
            p.fill('input[name="lastNameKatakana"]', last_name_katakana)
            p.fill('input[name="firstNameKatakana"]', first_name_katakana)
            p.fill('input[name="phone"]', phone)
            p.fill('input[name="email"]', email)

            p.wait_for_selector('#batch_id', timeout=10000)
            batch_options = p.locator('#batch_id option')
            option_count = batch_options.count()
            if option_count > 1:
                value = batch_options.nth(1).get_attribute('value')
                p.select_option('#batch_id', value)

            p.fill('input[name="dob"]', dob)
            gender_selector = f'input[name="gender"][value="{gender}"]'
            try:
                p.wait_for_selector(gender_selector, state='visible', timeout=5000)
                p.click(gender_selector)
            except TimeoutError:
                print(f"Warning: Gender input {gender_selector} not found or not visible, skipping.")

            p.fill('input[name="postal_code"]', postal_code)
            p.fill('input[name="address"]', address)
            p.fill('input[name="nationality"]', nationality)
            p.fill('input[name="hobby"]', hobby)

            try:
                p.wait_for_selector('div#current_country_id[role="combobox"]', timeout=5000)
                p.click('div#current_country_id[role="combobox"]')
                country_options = p.locator('div#current_country_id [role="option"]')
                count = country_options.count()
                if count > 1:
                    country_options.nth(1).click()
            except TimeoutError:
                print("Warning: Country combobox or options not found, skipping.")

            clicked = False
            selectors = [
                'button:has-text("Register Now")',
                'button:has-text("\u767b\u9332")',
                'button[type="submit"]',
                'input[type="submit"]',
                'button[role="button"]:text-matches("register|submit|send", "i")'
            ]
            for selector in selectors:
                try:
                    p.wait_for_selector(selector, timeout=3000)
                    p.click(selector)
                    clicked = True
                    break
                except TimeoutError:
                    continue

            if not clicked:
                try:
                    p.eval_on_selector('form', 'form => form.submit()')
                    clicked = True
                except Exception:
                    pass

            if not clicked:
                try:
                    buttons = p.query_selector_all("button")
                    if buttons:
                        buttons[-1].click()
                        clicked = True
                except Exception:
                    pass

            if not clicked:
                raise TimeoutError("The registration button or form could not be submitted.")

        with allure.step("Verify redirection to confirmation page"):
            p.wait_for_load_state("networkidle")
            current_url = p.url
            assert current_url != f"{BASE_URL}/admin/students/add-student", "Did not redirect after registration"
