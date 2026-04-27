"""
Email service — sends transactional emails via SMTP.
Falls back to logging the content when SMTP is not configured (dev mode).
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str, text_body: str = "") -> None:
    if not settings.smtp_host:
        logger.info(
            "SMTP not configured — would send email to %s\nSubject: %s\n%s",
            to, subject, text_body or html_body,
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        import aiosmtplib
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_tls,
        )
        logger.info("Email sent to %s: %s", to, subject)
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)


async def send_password_reset_email(to: str, full_name: str, reset_token: str) -> None:
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
    subject = "GDF-AutoMon — Reset your password"

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:32px;">
  <div style="max-width:480px;margin:0 auto;background:#1e293b;border-radius:12px;padding:32px;">
    <h1 style="color:#34d399;font-size:22px;margin:0 0 8px;">GDF-AutoMon</h1>
    <p style="color:#94a3b8;font-size:13px;margin:0 0 24px;">Goat &amp; Dairy Farm Monitoring</p>
    <h2 style="font-size:18px;margin:0 0 12px;">Reset your password</h2>
    <p style="color:#cbd5e1;">Hi {full_name},</p>
    <p style="color:#cbd5e1;">
      We received a request to reset the password for your account.
      Click the button below to choose a new password. This link expires in <strong>1 hour</strong>.
    </p>
    <a href="{reset_url}"
       style="display:inline-block;margin:24px 0;background:#059669;color:#fff;text-decoration:none;
              padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;">
      Reset Password
    </a>
    <p style="color:#64748b;font-size:12px;">
      If you didn't request this, you can safely ignore this email — your password won't change.
    </p>
    <p style="color:#64748b;font-size:12px;word-break:break-all;">
      Or copy this link: {reset_url}
    </p>
  </div>
</body>
</html>
"""

    text_body = (
        f"Hi {full_name},\n\n"
        "Reset your GDF-AutoMon password by visiting:\n"
        f"{reset_url}\n\n"
        "This link expires in 1 hour. If you didn't request this, ignore this email."
    )

    await send_email(to, subject, html_body, text_body)


async def send_welcome_email(to: str, full_name: str) -> None:
    subject = "Welcome to GDF-AutoMon"
    login_url = f"{settings.frontend_url}/login"

    html_body = f"""
<!DOCTYPE html>
<html>
<body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:32px;">
  <div style="max-width:480px;margin:0 auto;background:#1e293b;border-radius:12px;padding:32px;">
    <h1 style="color:#34d399;font-size:22px;margin:0 0 8px;">GDF-AutoMon</h1>
    <p style="color:#94a3b8;font-size:13px;margin:0 0 24px;">Goat &amp; Dairy Farm Monitoring</p>
    <h2 style="font-size:18px;margin:0 0 12px;">Welcome, {full_name}! 🐐</h2>
    <p style="color:#cbd5e1;">
      Your account has been created. You can now sign in to the dashboard and
      start monitoring your farm sensors in real-time.
    </p>
    <a href="{login_url}"
       style="display:inline-block;margin:24px 0;background:#059669;color:#fff;text-decoration:none;
              padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;">
      Sign In
    </a>
    <p style="color:#64748b;font-size:12px;">
      If you have any questions, contact your farm administrator.
    </p>
  </div>
</body>
</html>
"""

    await send_email(to, subject, html_body)
