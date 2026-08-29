"""
Email delivery for signup verification OTPs.

Supports TWO modes:
1. EMAIL_PROVIDER=smtp (recommended for production & real Gmail delivery):
   Sends actual emails via Gmail or any standard SMTP server.
   Required .env settings:
     EMAIL_PROVIDER=smtp
     SMTP_HOST=smtp.gmail.com
     SMTP_PORT=587
     SMTP_USERNAME=your.real.email@gmail.com
     SMTP_PASSWORD=your_16_digit_app_password
     EMAIL_FROM_ADDRESS=your.real.email@gmail.com

2. EMAIL_PROVIDER=console (default for local dev without SMTP):
   Logs the OTP directly to the terminal output.

Safety feature: If SMTP fails (e.g. invalid password or network timeout),
it logs an error AND prints the OTP to terminal as a fallback so you are
never locked out during development.
"""
import smtplib
import ssl
from email.message import EmailMessage
from flask import current_app


def _otp_email_plain_body(name: str, otp_code: str, expiry_minutes: int, from_name: str) -> str:
    return (
        f"Hi {name},\n\n"
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in {expiry_minutes} minutes. Enter this code on the verification screen to activate your account.\n\n"
        f"If you didn't request this code, you can safely ignore this email.\n\n"
        f"Best regards,\n"
        f"The {from_name} Team"
    )


def _otp_email_html_body(name: str, otp_code: str, expiry_minutes: int, from_name: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify Your Email</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f5f7; margin: 0; padding: 30px 15px; color: #1e293b;">
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="max-width: 520px; width: 100%; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;">
    <!-- Header -->
    <tr>
      <td style="background-color: #0f172a; padding: 24px 32px; text-align: center;">
        <h1 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 1px;">{from_name}</h1>
      </td>
    </tr>
    <!-- Content -->
    <tr>
      <td style="padding: 32px;">
        <h2 style="margin-top: 0; margin-bottom: 16px; font-size: 20px; color: #0f172a; font-weight: 600;">Confirm your email address</h2>
        <p style="font-size: 15px; line-height: 1.5; color: #475569; margin-bottom: 24px;">
          Hi <strong>{name}</strong>,<br>
          Thank you for signing up! Use the 6-digit verification code below to complete your registration.
        </p>
        
        <!-- OTP Code Box -->
        <div style="background-color: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 24px;">
          <span style="font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #2563eb;">{otp_code}</span>
        </div>
        
        <p style="font-size: 14px; color: #64748b; margin-bottom: 24px;">
          ⏱️ This code is valid for <strong>{expiry_minutes} minutes</strong>. If you didn't request this email, please ignore it.
        </p>
      </td>
    </tr>
    <!-- Footer -->
    <tr>
      <td style="background-color: #f8fafc; padding: 16px 32px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8;">
        &copy; {from_name} • Secure Email Verification System
      </td>
    </tr>
  </table>
</body>
</html>"""


def _dispatch_otp_email(to_email: str, subject: str, otp_code: str, plain_body: str, html_body: str) -> bool:
    """Shared send/log dispatch used by both the signup-verification and
    password-reset emails."""
    provider = (current_app.config.get("EMAIL_PROVIDER") or "console").lower()

    if provider == "smtp":
        success = _send_via_smtp(to_email, subject, plain_body, html_body)
        if not success:
            # Fallback to console log so developer/user isn't blocked if SMTP fails
            current_app.logger.warning(
                "\n[SMTP FAILURE FALLBACK - OTP LOGGED TO CONSOLE]\nTo: %s\nOTP Code: %s\n",
                to_email, otp_code
            )
        return success

    current_app.logger.info(
        "\n[EMAIL - console provider, not actually sent]\nTo: %s\nSubject: %s\nOTP Code: %s\n\n%s\n",
        to_email, subject, otp_code, plain_body,
    )
    return True


def send_verification_email(to_email: str, name: str, otp_code: str) -> bool:
    """Sends (or, in console mode, logs) the signup verification OTP.
    Returns True on success/logged, False if a real send attempt failed."""
    expiry_minutes = current_app.config.get("OTP_EXPIRY_MINUTES", 10)
    from_name = current_app.config.get("EMAIL_FROM_NAME", "ResumeFolio")
    subject = f"{otp_code} is your verification code for {from_name}"

    plain_body = _otp_email_plain_body(name, otp_code, expiry_minutes, from_name)
    html_body = _otp_email_html_body(name, otp_code, expiry_minutes, from_name)
    return _dispatch_otp_email(to_email, subject, otp_code, plain_body, html_body)


def _reset_email_plain_body(name: str, otp_code: str, expiry_minutes: int, from_name: str) -> str:
    return (
        f"Hi {name},\n\n"
        f"We received a request to reset your password. Your reset code is: {otp_code}\n\n"
        f"This code expires in {expiry_minutes} minutes. If you didn't request this, "
        f"you can safely ignore this email — your password won't be changed.\n\n"
        f"Best regards,\n"
        f"The {from_name} Team"
    )


def _reset_email_html_body(name: str, otp_code: str, expiry_minutes: int, from_name: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your Password</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f5f7; margin: 0; padding: 30px 15px; color: #1e293b;">
  <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="max-width: 520px; width: 100%; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); border: 1px solid #e2e8f0;">
    <tr>
      <td style="background-color: #0f172a; padding: 24px 32px; text-align: center;">
        <h1 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 700; letter-spacing: 1px;">{from_name}</h1>
      </td>
    </tr>
    <tr>
      <td style="padding: 32px;">
        <h2 style="margin-top: 0; margin-bottom: 16px; font-size: 20px; color: #0f172a; font-weight: 600;">Reset your password</h2>
        <p style="font-size: 15px; line-height: 1.5; color: #475569; margin-bottom: 24px;">
          Hi <strong>{name}</strong>,<br>
          We received a request to reset your password. Use the 6-digit code below to choose a new one.
        </p>
        <div style="background-color: #f8fafc; border: 2px dashed #cbd5e1; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 24px;">
          <span style="font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #2563eb;">{otp_code}</span>
        </div>
        <p style="font-size: 14px; color: #64748b; margin-bottom: 24px;">
          ⏱️ This code is valid for <strong>{expiry_minutes} minutes</strong>. If you didn't request this, your password is safe — just ignore this email.
        </p>
      </td>
    </tr>
    <tr>
      <td style="background-color: #f8fafc; padding: 16px 32px; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8;">
        &copy; {from_name} • Secure Password Reset
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_password_reset_email(to_email: str, name: str, otp_code: str) -> bool:
    """Sends (or, in console mode, logs) a password-reset OTP."""
    expiry_minutes = current_app.config.get("OTP_EXPIRY_MINUTES", 10)
    from_name = current_app.config.get("EMAIL_FROM_NAME", "ResumeFolio")
    subject = f"{otp_code} is your password reset code for {from_name}"

    plain_body = _reset_email_plain_body(name, otp_code, expiry_minutes, from_name)
    html_body = _reset_email_html_body(name, otp_code, expiry_minutes, from_name)
    return _dispatch_otp_email(to_email, subject, otp_code, plain_body, html_body)


def _send_via_smtp(to_email: str, subject: str, plain_body: str, html_body: str) -> bool:
    cfg = current_app.config
    host = cfg.get("SMTP_HOST")
    username = cfg.get("SMTP_USERNAME", "")
    password = cfg.get("SMTP_PASSWORD", "")
    from_address = cfg.get("EMAIL_FROM_ADDRESS") or username or "no-reply@resumefolio.com"
    from_name = cfg.get("EMAIL_FROM_NAME", "ResumeFolio")

    if not host or "your-email" in username or "your-app-password" in password or not password:
        current_app.logger.error(
            "[SMTP ERROR] EMAIL_PROVIDER=smtp is enabled, but SMTP_USERNAME or SMTP_PASSWORD contains placeholder credentials in .env. Please update .env with your real Gmail address and 16-digit App Password."
        )
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_address}>"
    msg["To"] = to_email
    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        port = int(cfg.get("SMTP_PORT", 587))
        use_tls = cfg.get("SMTP_USE_TLS", True)

        context = ssl.create_default_context()

        if port == 465:
            # SSL Connection
            with smtplib.SMTP_SSL(host, port, context=context, timeout=10) as server:
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
        else:
            # TLS / STARTTLS Connection (e.g. Port 587)
            with smtplib.SMTP(host, port, timeout=10) as server:
                if use_tls:
                    server.starttls(context=context)
                if username and password:
                    server.login(username, password)
                server.send_message(msg)

        current_app.logger.info("Successfully sent verification email to %s via SMTP (%s)", to_email, host)
        return True

    except smtplib.SMTPAuthenticationError as e:
        current_app.logger.error(
            "SMTP Authentication Failed for %s: %s. "
            "For Gmail, ensure you are using a 16-character App Password (not your regular account password). "
            "Generate one at: https://myaccount.google.com/apppasswords",
            username, e
        )
        return False
    except Exception as e:  # noqa: BLE001
        current_app.logger.error("Failed to send verification email to %s via SMTP (%s:%s): %s", to_email, host, port, e)
        return False

