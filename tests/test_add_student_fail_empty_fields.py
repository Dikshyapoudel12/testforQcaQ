import pytest
import allure
from playwright.sync_api import expect


def test_fail_to_add_student_with_empty_mandatory_fields(page):
    base_url = "https://ai-samurai.tai.com.np"
    admin_email = "admin@tai.com.np"
    admin_password = "admin123"
    add_student_url = f"{base_url}/admin/students/add-student"
    login_url = f"{base_url}/admin/login"

    for p in page:
        with allure.step("Navigate to login page"):
            p.goto(login_url)

        with allure.step("Login as administrator"):
            p.fill('input[name="email"]', admin_email)
            p.fill('input[name="password"]', admin_password)
            p.click('button[type="submit"]')

        with allure.step("Verify login success by checking URL or page content"):
            expect(p).to_have_url(f"{base_url}/admin", timeout=10000)

        with allure.step("Navigate to Add Student page"):
            p.goto(add_student_url)
            expect(p).to_have_url(add_student_url)

        with allure.step("Leave mandatory fields empty and submit form"):
            p.fill('input[name="lastName"]', "")
            p.fill('input[name="firstName"]', "")
            p.fill('input[name="email"]', "")
            p.fill('input[name="password"]', "")
            p.fill('input[name="password_confirmation"]', "")

            with allure.step("Locate and log all buttons on the page"):
                buttons = p.locator("button")
                count = buttons.count()
                button_texts = []
                for i in range(count):
                    text = buttons.nth(i).inner_text().strip()
                    button_texts.append(text)
                allure.attach(str(button_texts), name="button_texts", attachment_type=allure.attachment_type.TEXT)

            with allure.step("Click on the Register Now button or fallback"):
                # Try to find button with exact or partial text "Register Now" ignoring case
                button_to_click = None
                for i in range(count):
                    btn = buttons.nth(i)
                    text = btn.inner_text().strip().lower()
                    if "register" in text and "now" in text:
                        button_to_click = btn
                        break
                if button_to_click:
                    button_to_click.click()
                else:
                    # fallback: click first button
                    if count > 0:
                        buttons.nth(0).click()
                    else:
                        raise Exception("No clickable button found on the page")

        with allure.step("Check for validation errors indicating mandatory fields cannot be empty"):
            validation_texts = ["required", "please", "mandatory", "can't be empty", "cannot be empty"]
            errors_found = False
            for text in validation_texts:
                if p.locator(f'text="{text}"').count() > 0:
                    errors_found = True
                    break

            if not errors_found:
                for field_name in ["lastName", "firstName", "email", "password", "password_confirmation"]:
                    if p.locator(f'input[name="{field_name}"][aria-invalid="true"]').count() > 0:
                        errors_found = True
                        break

            assert errors_found, "Expected validation error messages for empty mandatory fields"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
