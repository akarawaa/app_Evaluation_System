"""Employee acknowledgement of a finalized evaluation -- paper method only
for now (electronic/email is a later phase). HR records that the employee
signed a printed copy, optionally attaching the scan.

"Acknowledged" is not "agreed": decision has three outcomes
(acknowledged / acknowledged_disagreed / refused) and a free-text comment,
same as the paper form's separate box for the employee's own dissent.
"""
import mimetypes
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.services import storage
from app.services.audit import write_audit
from app.services.evaluations import _load_viewable

_DECISIONS = {"acknowledged", "acknowledged_disagreed", "refused"}
_MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024  # 15 MB -- a scanned page or two


async def record_paper_acknowledgement(
    session: AsyncSession,
    user: CurrentUser,
    eval_id: str,
    *,
    decision: str,
    comment: str | None,
    witness_name: str | None,
    signed_at: date | None,
    attachment_filename: str | None,
    attachment_bytes: bytes | None,
) -> dict:
    if decision not in _DECISIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"decision must be one of {sorted(_DECISIONS)}")
    if decision == "refused" and not witness_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "การปฏิเสธลงนามต้องระบุชื่อพยาน")
    if attachment_bytes and len(attachment_bytes) > _MAX_ATTACHMENT_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ไฟล์แนบต้องไม่เกิน 15 MB")

    # HR-only: require_roles("hr_admin") already gates the route, but going
    # through _load_viewable (not a bare load) keeps the same "never reveal
    # existence outside your visibility" 404 rule as every other endpoint.
    ev = await _load_viewable(session, user, eval_id)
    if ev["status"] != "finalized":
        raise HTTPException(status.HTTP_409_CONFLICT, "บันทึกการรับทราบได้เฉพาะใบที่ปิดแล้ว (finalized)")

    existing = (await session.execute(text(
        "select id from evaluation_acknowledgements where evaluation_id = :id"
    ), {"id": eval_id})).first()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "ใบนี้มีบันทึกการรับทราบอยู่แล้ว")

    attachment_path = None
    if attachment_bytes:
        ext = (attachment_filename or "").rsplit(".", 1)[-1].lower() if "." in (attachment_filename or "") else "bin"
        attachment_path = f"{ev['company_id']}/{eval_id}.{ext}"
        content_type = mimetypes.guess_type(attachment_filename or "")[0] or "application/octet-stream"
        await storage.upload_object(attachment_path, attachment_bytes, content_type)

    signed_dt = datetime.combine(signed_at, datetime.min.time(), tzinfo=timezone.utc) if signed_at else None

    row = (await session.execute(text(
        "insert into evaluation_acknowledgements "
        "(company_id, evaluation_id, employee_id, method, decision, comment, "
        " actor_id, witness_name, attachment_path"
        + (", signed_at" if signed_dt else "") + ") "
        "values (:company_id, :eval_id, :employee_id, 'paper', :decision, :comment, "
        ":actor_id, :witness_name, :attachment_path"
        + (", :signed_at" if signed_dt else "") + ") "
        "returning id, signed_at"
    ), {
        "company_id": ev["company_id"], "eval_id": eval_id, "employee_id": ev["employee_id"],
        "decision": decision, "comment": comment, "actor_id": user.id,
        "witness_name": witness_name, "attachment_path": attachment_path,
        **({"signed_at": signed_dt} if signed_dt else {}),
    })).mappings().one()

    await write_audit(session, company_id=ev["company_id"], actor_id=user.id,
                      action="evaluation_acknowledged", entity_type="evaluations", entity_id=eval_id,
                      after={"method": "paper", "decision": decision, "has_attachment": attachment_path is not None})

    return {"id": str(row["id"]), "decision": decision, "signed_at": row["signed_at"]}


async def get_attachment(session: AsyncSession, user: CurrentUser, eval_id: str) -> tuple[bytes, str]:
    await _load_viewable(session, user, eval_id)
    row = (await session.execute(text(
        "select attachment_path from evaluation_acknowledgements where evaluation_id = :id"
    ), {"id": eval_id})).mappings().first()
    if not row or not row["attachment_path"]:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่มีไฟล์แนบสำหรับใบนี้")
    path = row["attachment_path"]
    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    return await storage.download_object(path), content_type
