"""Evaluation lifecycle API (Phase 2, Step 2). All DB access via the tenant
session (RLS-scoped); state transitions + authorization live in the service."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_session
from app.core.security import CurrentUser, get_current_user
from app.schemas.evaluation import (
    ApproveIn,
    EvaluationCreate,
    FinalizeIn,
    ScoresUpdate,
)
from app.services import evaluations as svc

router = APIRouter(prefix="/api/evaluations")


@router.get("")
async def list_evaluations(session: AsyncSession = Depends(get_tenant_session)) -> list[dict]:
    return await svc.list_all(session)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    payload: EvaluationCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.create(session, user, payload)


@router.get("/{eval_id}")
async def get_evaluation(
    eval_id: str,
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.get_detail(session, eval_id)


@router.put("/{eval_id}/scores")
async def save_scores(
    eval_id: str,
    payload: ScoresUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_tenant_session),
) -> dict:
    return await svc.save_scores(session, user, eval_id, payload)


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
