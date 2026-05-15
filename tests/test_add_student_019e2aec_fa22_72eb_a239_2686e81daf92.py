import pytest
import uuid
import random
import re
import asyncio
import nest_asyncio
from playwright.sync_api import expect

def test_add_student_successfully(page):
    base_url = "https://ai-samurai.tai.com.np"
    admin_email = "admin@tai.com.np"
    admin_password = "admin123"

    # Generate test data for student form
    last_name = "Tanaka"
    first_name = "Kenji"
    last_name_katakana = ""
    first_name_katakana = ""
    phone = f"090{random.randint(10000000, 99999999)}"  # random 11-digit phone starting with 090
    email = f"user_{uuid.uuid4().hex[:8]}@kokorozashi.info"
    dob = "2000/01/01"  # matches placeholder YYYY/MM/DD format
    gender_value = "male"  # choose male for gender toggle
    postal_code = "12345"
    address = "Tokyo Shinjuku 1-1-1"
    nationality = "Japanese"
    hobby = "Reading"
    password = f"TestPass123"  # At least one upper, one lower, one digit

    for p in page:
        # Step: Log in first (precondition)
        p.goto(f"{base_url}/admin/login")
        p.fill('input[name="email"]', admin_email)
        p.fill('input[name="password"]', admin_password)
        p.click('button[type="submit"]')
        # Wait for admin page after login
        expect(p).to_have_url(f"{base_url}/admin", timeout=10000)

        # Step: Navigate to add student page
        p.goto(f"{base_url}/admin/students/add-student")
        expect(p).to_have_url(f"{base_url}/admin/students/add-student", timeout=5000)

        # Fill student form fields according to steps
        p.fill('input[name="lastName"]', last_name)
        p.fill('input[name="firstName"]', first_name)
        p.fill('input[name="lastNameKatakana"]', last_name_katakana)
        p.fill('input[name="firstNameKatakana"]', first_name_katakana)
        p.fill('input[name="phone"]', phone)
        p.fill('input[name="email"]', email)

        # Click #batch_id combobox and select the first option using keyboard
        p.click('#batch_id')
        # Navigate options with keyboard: down arrow then enter to select first option
        p.keyboard.press("ArrowDown")
        p.keyboard.press("Enter")

        # Fill dob field with placeholder YYYY/MM/DD using 2000/01/01 (converted from 2000-01-01)
        # According to step, value is `2000-01-01`, but placeholder is YYYY/MM/DD -> Use format YYYY/MM/DD
        p.fill('input[placeholder="YYYY/MM/DD"]', dob)

        # Click gender toggle button by role selector with value male
        # Use button with role and value attribute
        p.click('role=button[name="male"]') or p.click('button[value="male"]')  # fallback if needed
        # Safer: use button[value="male"] if role selector not working
        # Playwright role selector for button by name should be role=button[name="male"]
        # Try click first on role and fallback
        try:
            p.click('role=button[name="male"]')
        except Exception:
            p.click('button[value="male"]')

        p.fill('input[name="postal_code"]', postal_code)
        p.fill('input[name="address"]', address)
        p.fill('input[name="nationality"]', nationality)
        p.fill('input[name="hobby"]', hobby)

        # Click div#current_country_id[role="combobox"] and select second option via role selector
        p.click('div#current_country_id[role="combobox"]')
        # Press ArrowDown twice to get second option and Enter
        p.keyboard.press("ArrowDown")
        p.keyboard.press("ArrowDown")
        p.keyboard.press("Enter")

        # Fill password and password_confirmation with the same value
        p.fill('input[name="password"]', password)
        p.fill('input[name="password_confirmation"]', password)

        # Click Proceed to confirmation button, assuming button text is unique
        p.click('button:has-text("Proceed to confirmation")')

        # Click Register Now button after confirmation
        # Wait and click button containing "Register Now"
        p.click('button:has-text("Register Now")')

        # Expected: redirected to confirmation page
        # The exact confirmation page URL is TBD, so check URL is not add-student page and contains "confirmation" keyword
        expect(p).not_to_have_url(f"{base_url}/admin/students/add-student", timeout=10000)
        # Optional: check URL contains "confirmation"
        assert "confirmation" in p.url.lower()
