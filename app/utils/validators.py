import re
import random

# Common disposable / temp-mail domains. Not exhaustive, but blocks the
# overwhelming majority of "fake email" signups seen in the wild.
DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "tempmail.com", "temp-mail.org", "guerrillamail.com",
    "guerrillamail.info", "guerrillamail.biz", "guerrillamail.de", "sharklasers.com",
    "10minutemail.com", "10minutemail.net", "yopmail.com", "yopmail.net",
    "trashmail.com", "trashmail.net", "throwawaymail.com", "getnada.com",
    "maildrop.cc", "mintemail.com", "dispostable.com", "fakeinbox.com",
    "spamgourmet.com", "mailnesia.com", "mytemp.email", "moakt.com",
    "tempinbox.com", "emailondeck.com", "mohmal.com", "temp-mail.io",
    "burnermail.io", "mailcatch.com", "inboxbear.com", "tempmailo.com",
    "discard.email", "discardmail.com", "spam4.me", "cs.email",
}


def is_valid_email(email: str) -> bool:
    if not email:
        return False
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


def is_disposable_email(email: str) -> bool:
    """True if the email's domain is a known disposable/temp-mail provider."""
    if not email or "@" not in email:
        return False
    domain = email.rsplit("@", 1)[-1].strip().lower()
    return domain in DISPOSABLE_EMAIL_DOMAINS


# At least 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special character.
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+\[\]{};:'\",.<>/?\\|`~]).{8,}$"
)


def is_valid_password(password: str) -> bool:
    return bool(password) and PASSWORD_PATTERN.match(password) is not None


def password_requirements_message() -> str:
    return (
        "Password must be at least 8 characters and include one uppercase letter, "
        "one lowercase letter, one number, and one special character."
    )


# --- Email verification OTP ---
OTP_PATTERN = re.compile(r"^\d{6}$")


def generate_otp() -> str:
    """6-digit numeric code, zero-padded."""
    return f"{random.randint(0, 999999):06d}"


def is_valid_otp_format(otp: str) -> bool:
    return bool(otp) and OTP_PATTERN.match(otp.strip()) is not None


def error_response(message, status=400, details=None):
    body = {"success": False, "error": message}
    if details:
        body["details"] = details
    return body, status


def success_response(data=None, message=None, status=200):
    body = {"success": True}
    if message:
        body["message"] = message
    if data is not None:
        body["data"] = data
    return body, status
