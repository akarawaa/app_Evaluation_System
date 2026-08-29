"""App shim over `hr_platform_core.email` (platform-core/py, PLATFORM_ARCHITECTURE.md §12).

The Brevo transactional-email mechanism lives in the shared package now.
`send_email(to, subject, html_body)` keeps its historical signature and maps
this app's `get_settings()` onto the package's explicit args.
`password_changed_email` is Evaluate-specific copy and stays here; the
deferred employee-acknowledgement phase adds its own bodies here too.

Password *recovery* itself is still sent by Supabase Auth directly, not
through here -- this is only for notices where we control the copy.
"""
from hr_platform_core.email import send_email as _send_email

from app.core.config import get_settings

__all__ = ["send_email", "password_changed_email"]


async def send_email(to: str, subject: str, html_body: str) -> None:
    settings = get_settings()
    await _send_email(
        to,
        subject,
        html_body,
        api_key=settings.brevo_api_key,
        mail_from=settings.mail_from,
        mail_from_name=settings.mail_from_name,
    )


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
