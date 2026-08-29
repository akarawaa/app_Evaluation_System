"""Transactional emails we compose ourselves (password-changed notice today;
the deferred employee-acknowledgement phase reuses this same account later).
Password *recovery* itself is sent by Supabase Auth directly, not through
here -- this is only for notices where we control the copy.

Sent via Brevo's transactional email HTTP API
(https://api.brevo.com/v3/smtp/email), NOT smtplib. This app originally used
SMTP, but a real production incident on the sibling app (app_leave_approve,
2026-08-29 -- same Render hosting, same shared Gmail account) found that
Render blocks ALL outbound SMTP at the network level: every send failed with
`OSError: [Errno 101] Network is unreachable` connecting to port 587,
regardless of provider or credentials. Brevo's API is plain HTTPS (same as
every other external call this app already makes), so it isn't affected.

`send_email` never raises -- a failed notice must never fail the action that
triggered it (here: a password change that already succeeded in Supabase
Auth before this is ever called).
"""
import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()

_SEND_URL = "https://api.brevo.com/v3/smtp/email"


async def send_email(to: str, subject: str, html_body: str) -> None:
    settings = get_settings()
    if not settings.brevo_configured:
        # Never block the caller's action (e.g. a password change already
        # succeeded in Supabase Auth) on our own notice email being unset up.
        logger.warning("brevo_not_configured", to=to, subject=subject)
        return

    payload = {
        "sender": {"email": settings.mail_from, "name": settings.mail_from_name},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html_body,
    }
    headers = {
        "api-key": settings.brevo_api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(_SEND_URL, headers=headers, json=payload)
        if resp.status_code >= 400:
            logger.error("email_send_rejected", to=to, subject=subject,
                         status=resp.status_code, body=resp.text[:500])
    except httpx.RequestError:  # noqa: BLE001 -- a failed notice must not fail the request
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
