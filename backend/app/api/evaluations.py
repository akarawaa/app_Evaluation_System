"""Evaluation lifecycle API (Phase 2, Step 2). All DB access via the tenant
session (RLS-scoped); state transitions + authorization live in the service."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_session
from app.core.security import CurrentUser, get_current_user, require_roles
from app.schemas.attendance_import import AttendanceImportResult
from app.schemas.evaluation import (
    ApproveIn,
    AttendanceSet,
    EvaluationCreate,
    FinalizeIn,
    ScoresUpdate,
)
from app.services import acknowledgement as ack_svc
from app.services import attendance_import as attendance_import_svc
from app.services import evaluations as svc
from app.services.audit import write_audit
from app.services.compare import build_comparison
from app.services.excel_export import build_evaluations_excel
from app.services.pdf import build_evaluation_pdf

router = APIRouter(prefix="/api/evaluations")


@router.get("")
async def list_evaluations(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[dict]:
    return await svc.list_all(session, user)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    payload: EvaluationCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.create(session, user, payload)


@router.get("/inbox")
async def inbox(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[dict]:
    """Evaluations awaiting the current user's action. Registered before
    /{eval_id} so 'inbox' isn't swallowed as a path parameter."""
    return await svc.list_inbox(session, user)


@router.get("/export")
async def export_evaluations(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> Response:
    """Excel export of every evaluation the caller can see (same visibility
    policy as list_all). Literal path — registered before /{eval_id}."""
    xlsx_bytes = await build_evaluations_excel(
        session, user, status=status_filter, date_from=date_from, date_to=date_to,
    )
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="evaluations_exported", entity_type="evaluations")
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="evaluations-export.xlsx"'},
    )


@router.get("/compare")
async def compare_evaluations(
    ids: list[str] = Query(...),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Side-by-side comparison of 2-5 evaluations (same cycle across
    employees, or same employee across time — the caller picks which).
    Literal path — registered before /{eval_id}."""
    return await build_comparison(session, user, ids)


@router.get("/attendance-import-template")
async def attendance_import_template(
    user: CurrentUser = Depends(require_roles("hr_admin")),
) -> Response:
    """Literal path — registered before /{eval_id} so it isn't swallowed as
    a path parameter (same convention as /inbox)."""
    return Response(
        content=attendance_import_svc.build_template_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="attendance-import-template.csv"'},
    )


@router.post("/attendance-import", response_model=AttendanceImportResult)
async def attendance_import(
    file: UploadFile,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    raw = await file.read()
    return await attendance_import_svc.import_attendance(session, user, raw)


@router.get("/{eval_id}")
async def get_evaluation(
    eval_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.view_detail(session, user, eval_id)


@router.get("/{eval_id}/pdf")
async def evaluation_pdf(
    eval_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> Response:
    ctx = await svc.get_report_context(session, user, eval_id)
    pdf_bytes = build_evaluation_pdf(ctx)
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="evaluation_exported", entity_type="evaluations", entity_id=eval_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="evaluation-{eval_id}.pdf"'},
    )


@router.put("/{eval_id}/scores")
async def save_scores(
    eval_id: str,
    payload: ScoresUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.save_scores(session, user, eval_id, payload)


@router.put("/{eval_id}/attendance")
async def set_attendance(
    eval_id: str,
    payload: AttendanceSet,
    user: CurrentUser = Depends(require_roles("hr_admin")),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.set_attendance(session, user, eval_id, payload)


@router.post("/{eval_id}/submit")
async def submit_evaluation(
    eval_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.submit(session, user, eval_id)


@router.post("/{eval_id}/approve")
async def approve_evaluation(
    eval_id: str,
    payload: ApproveIn,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.approve(session, user, eval_id, payload.comment)


@router.post("/{eval_id}/return")
async def return_evaluation(
    eval_id: str,
    payload: ApproveIn,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.return_to_draft(session, user, eval_id, payload.comment)


@router.post("/{eval_id}/finalize")
async def finalize_evaluation(
    eval_id: str,
    payload: FinalizeIn,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.finalize(session, user, eval_id, payload)


@router.post("/{eval_id}/acknowledge-paper")
async def acknowledge_paper(
    eval_id: str,
    decision: str = Form(...),
    comment: Optional[str] = Form(None),
    witness_name: Optional[str] = Form(None),
    signed_at: Optional[date] = Form(None),
    file: Optional[UploadFile] = File(None),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    """Records that the employee acknowledged (or refused to acknowledge) a
    printed copy in person, between the dept manager's approval and GM/MD's.
    Authorization is the evaluation's own org chain (evaluator / dept manager
    / HR), which route-level RBAC can't express -- see the service."""
    attachment_bytes = await file.read() if file else None
    return await ack_svc.record_paper_acknowledgement(
        session, user, eval_id,
        decision=decision, comment=comment, witness_name=witness_name, signed_at=signed_at,
        attachment_filename=file.filename if file else None,
        attachment_bytes=attachment_bytes,
    )


@router.get("/{eval_id}/acknowledgement-attachment")
async def acknowledgement_attachment(
    eval_id: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> Response:
    content, content_type = await ack_svc.get_attachment(session, user, eval_id)
    return Response(content=content, media_type=content_type)
