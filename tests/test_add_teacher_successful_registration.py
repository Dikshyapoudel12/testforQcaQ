import pytest
import allure
import uuid
import random
import string
from playwright.sync_api import expect

# Constants
BASE_URL = "https://ai-samurai.tai.com.np"
LOGIN_URL = f"{BASE_URL}/admin/login"
ADD_TEACHER_URL = f"{BASE_URL}/admin/teachers/add-teacher"
ADMIN_EMAIL = "admin@tai.com.np"
ADMIN_PASSWORD = "admin123"


def random_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@gmail.com"


def random_first_name() -> str:
    first_names = ["Alice", "Bob", "Carol", "David", "Eva", "Frank", "Grace", "Hank", "Ivy", "Jack"]
    return random.choice(first_names)


def random_last_name() -> str:
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson"]
    return random.choice(last_names)


def random_phone() -> str:
    prefix = random.choice(["9", "8"])
    number = f"{prefix}{random.randint(100000000, 999999999)}"
    return number


def random_specialization() -> str:
    specializations = [
        "Mathematics",
        "Physics",
        "Chemistry",
        "Biology",
        "English Literature",
        "Computer Science",
        "History",
        "Geography",
        "Economics",
        "Art"
    ]
    return random.choice(specializations)


def random_password() -> str:
    password_chars = []
    password_chars.append(random.choice(string.ascii_uppercase))
    password_chars.append(random.choice(string.ascii_lowercase))
    password_chars.append(random.choice(string.digits))
    remaining_len = 5
    password_chars += random.choices(string.ascii_letters + string.digits, k=remaining_len)
    random.shuffle(password_chars)
    return "".join(password_chars)


def login_as_admin(p):
    p.goto(LOGIN_URL)
    p.fill('input[name="email"]', ADMIN_EMAIL)
    p.fill('input[name="password"]', ADMIN_PASSWORD)
    p.click('button[type="submit"]')
    # Wait for element that marks logged in state or URL changes from login page
    try:
        # Example: wait for logout button or sidebar item (adjust selector if needed)
        p.wait_for_selector('a[href="/admin/logout"], button#logout, nav', timeout=10000)
    except:
        # fallback to URL check to ensure login succeeded and page is not on login
        p.wait_for_url(lambda url: url != LOGIN_URL and url.startswith(f"{BASE_URL}/admin"), timeout=10000)


@allure.title("Successful teacher registration with valid inputs")
def test_successful_teacher_registration_with_valid_inputs(page):
    for p in page:
        with allure.step("Login as admin"):
            login_as_admin(p)

        with allure.step("Navigate to Add Teacher page"):
            p.goto(ADD_TEACHER_URL)
            expect(p).to_have_url(ADD_TEACHER_URL, timeout=5000)

        teacher_email = random_email()
        teacher_first_name = random_first_name()
        teacher_last_name = random_last_name()
        teacher_phone = random_phone()
        teacher_specialization = random_specialization()
        teacher_password = random_password()

        with allure.step("Fill Add Teacher form with valid inputs"):
            p.fill('input[name="email"]', teacher_email)
            p.fill('input[name="first_name"]', teacher_first_name)
            p.fill('input[name="last_name"]', teacher_last_name)
            p.fill('input[name="phone"]', teacher_phone)
            p.fill('input[name="specialization"]', teacher_specialization)
            p.fill('input[name="password"]', teacher_password)
            p.fill('input[name="password_confirmation"]', teacher_password)

        with allure.step("Submit the Add Teacher form"):
            p.click('button[type="submit"]')

        with allure.step("Verify success toast message"):
            expect(p.locator('text=Teacher added successfully!')).to_be_visible(timeout=8000)
