"""Transactional emails we compose ourselves (password-changed notice today;
the deferred employee-acknowledgement phase reuses this same SMTP account
later). Password *recovery* itself is sent by Supabase Auth directly, not
through here -- this is only for notices where we control the copy.

smtplib is blocking; every call runs in a thread so it never stalls the
event loop other requests are sharing.
"""
import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from app.core.config import get_settings

logger = structlog.get_logger()


def _send_sync(to: str, subject: str, html_body: str) -> None:
    settings = get_settings()
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.mail_from or settings.smtp_user
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.starttls(context=context)
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(msg["From"], [to], msg.as_string())


async def send_email(to: str, subject: str, html_body: str) -> None:
    settings = get_settings()
    if not settings.smtp_configured:
        # Never block the caller's action (e.g. a password change already
        # succeeded in Supabase Auth) on our own notice email being unset up.
        logger.warning("smtp_not_configured", to=to, subject=subject)
        return
    try:
        await asyncio.to_thread(_send_sync, to, subject, html_body)
    except Exception:  # noqa: BLE001 -- a failed notice must not fail the request
        logger.exception("email_send_failed", to=to, subject=subject)


def password_changed_email(display_name: str | None) -> tuple[str, str]:
    who = display_name or "คุณ"
    subject = "รหัสผ่านบัญชี E-Appraisal ของคุณถูกเปลี่ยนแล้ว"
    body = f"""
    <p>เรียน {who},</p>
    <p>รหัสผ่านสำหรับเข้าใช้งานระบบ E-Appraisal ของคุณเพิ่งถูกเปลี่ยนเมื่อครู่นี้</p>
    <p><b>หากคุณเป็นผู้เปลี่ยนเอง ไม่ต้องดำเนินการใด ๆ เพิ่มเติม</b></p>
    <p>หากคุณ<b>ไม่ได้</b>เป็นผู้เปลี่ยนรหัสผ่านนี้ กรุณาติดต่อฝ่ายบุคคลหรือผู้ดูแลระบบทันที
    เพื่อตรวจสอบว่าบัญชีของคุณปลอดภัย</p>
    """
    return subject, body
