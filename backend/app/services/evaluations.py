"""Evaluation lifecycle + approval routing (Phase 2, Step 2).

Approval is routed by the real org chain (see docs/EVALUATION_DESIGN.md):
  supervisor (employee.supervisor_id) scores -> submit
  dept manager (employee.manager_id) approves
  MD (role 'md') approves
  HR (role 'hr_admin') finalizes
Every transition writes an audit row in the same transaction.
"""
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser
from app.services import attendance_brackets
from app.services.audit import write_audit


async def _actor_employee_id(session: AsyncSession, user_id: str):
    row = (
        await session.execute(
            text("select employee_id from profiles where id = :id"), {"id": user_id}
        )
    ).first()
    return row[0] if row and row[0] is not None else None


def _same_employee(a, b) -> bool:
    """actor_emp == ev["emp_manager_id"] style checks must NOT pass when both
    sides are unset. Python's `None == None` is True (unlike SQL NULL = NULL,
    which is unknown/false), so a profile with no employee_id linked yet
    (e.g. a freshly invited user) could otherwise be treated as the manager
    of any employee whose manager_id also happens to be unset."""
    return a is not None and b is not None and a == b


def _is_md_or_gm(user: CurrentUser) -> bool:
    """MD and GM are interchangeable at the top approval stage (GM/MD)."""
    return "md" in user.roles or "gm" in user.roles


async def _has_active_acknowledgement(session: AsyncSession, eval_id: str) -> bool:
    row = (await session.execute(text(
        "select 1 from evaluation_acknowledgements "
        "where evaluation_id = :id and superseded_at is null"
    ), {"id": eval_id})).first()
    return row is not None


def _sees_all_evaluations(user: CurrentUser) -> bool:
    """Who may read every evaluation in the tenant: HR (oversight) and the
    GM/MD top approvers (they act on all of them). Everyone else is limited to
    their own evaluation (as the subject) or their direct reports'."""
    return user.is_super_admin or "hr_admin" in user.roles or _is_md_or_gm(user)


def _can_view(user: CurrentUser, actor_emp, ev: dict) -> bool:
    if _sees_all_evaluations(user):
        return True
    return (
        _same_employee(actor_emp, ev["employee_id"])       # the subject themselves
        or _same_employee(actor_emp, ev["emp_supervisor_id"])  # direct supervisor
        or _same_employee(actor_emp, ev["emp_manager_id"])     # dept manager
    )


async def _load(session: AsyncSession, eval_id: str) -> dict:
    row = (
        await session.execute(
            text(
                "select ev.*, emp.supervisor_id as emp_supervisor_id, "
                "emp.manager_id as emp_manager_id "
                "from evaluations ev join employees emp on emp.id = ev.employee_id "
                "where ev.id = :id"
            ),
            {"id": eval_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "evaluation not found")
    return dict(row)


async def get_detail(session: AsyncSession, eval_id: str) -> dict:
    ev = await _load(session, eval_id)
    # The subject (who is being evaluated) plus the evaluator / dept-manager
    # approver, so the detail page names everyone instead of leaving viewers to
    # guess from status alone. The subject's name matters most -- without it you
    # can't tell whose evaluation you opened.
    names = (await session.execute(text(
        "select "
        "  (select emp_code  from employees where id = :employee_id) as employee_code, "
        "  (select full_name from employees where id = :employee_id) as employee_name, "
        "  (select position  from employees where id = :employee_id) as employee_position, "
        "  (select full_name from employees where id = :evaluator_id) as evaluator_name, "
        "  (select full_name from employees where id = :manager_id) as dept_manager_name"
    ), {"employee_id": ev.get("employee_id"), "evaluator_id": ev.get("evaluator_id"),
        "manager_id": ev.get("emp_manager_id")})).mappings().first()
    ev["employee_code"] = names["employee_code"] if names else None
    ev["employee_name"] = names["employee_name"] if names else None
    ev["employee_position"] = names["employee_position"] if names else None
    ev["evaluator_name"] = names["evaluator_name"] if names else None
    ev["dept_manager_name"] = names["dept_manager_name"] if names else None
    items = (await session.execute(text(
        "select i.id, i.category_order, i.category_name, i.item_order, i.item_name, "
        "i.weight, i.desc_1, i.desc_2, i.desc_3, i.desc_4, i.desc_5, s.score "
        "from evaluation_items i "
        "left join evaluation_scores s on s.evaluation_item_id = i.id "
        "where i.evaluation_id = :id order by i.category_order, i.item_order"
    ), {"id": eval_id})).mappings().all()
    comments = (await session.execute(text(
        "select category_order, comment from evaluation_comments where evaluation_id = :id "
        "order by category_order"
    ), {"id": eval_id})).mappings().all()
    attendance = (await session.execute(text(
        "select sick_days, personal_days, late_count, late_minutes, absent_days, "
        "attendance_score, attendance_score_overridden "
        "from evaluation_attendance where evaluation_id = :id"
    ), {"id": eval_id})).mappings().first()
    # actor_name: the signature block on the printed form needs a person's name,
    # not a profile uuid. Prefer the linked employee record's real name and fall
    # back to the profile display name (super_admin has no employee row).
    approvals = (await session.execute(text(
        "select a.step, a.actor_id, a.decision, a.comment, a.decided_at, "
        "       coalesce(e.full_name, p.display_name) as actor_name "
        "from evaluation_approvals a "
        "left join profiles  p on p.id = a.actor_id "
        "left join employees e on e.id = p.employee_id "
        "where a.evaluation_id = :id order by a.decided_at"
    ), {"id": eval_id})).mappings().all()
    acknowledgement = (await session.execute(text(
        "select method, decision, comment, signed_at, witness_name, "
        "       attachment_path, content_hash, created_at "
        "from evaluation_acknowledgements where evaluation_id = :id and superseded_at is null"
    ), {"id": eval_id})).mappings().first()
    ev["items"] = [dict(x) for x in items]
    ev["comments"] = [dict(x) for x in comments]
    ev["attendance"] = dict(attendance) if attendance else None
    ev["approvals"] = [dict(x) for x in approvals]
    ev["acknowledgement"] = dict(acknowledgement) if acknowledgement else None
    return ev


async def get_report_context(session: AsyncSession, user: CurrentUser, eval_id: str) -> dict:
    await _load_viewable(session, user, eval_id)
    ev = await get_detail(session, eval_id)
    emp = (await session.execute(text(
        "select emp_code, full_name, position from employees where id = :id"
    ), {"id": ev["employee_id"]})).mappings().first()
    ev["_employee"] = dict(emp) if emp else {}
    ev["_evaluator"] = {}
    if ev.get("evaluator_id"):
        evr = (await session.execute(text(
            "select full_name from employees where id = :id"
        ), {"id": ev["evaluator_id"]})).mappings().first()
        ev["_evaluator"] = dict(evr) if evr else {}
    comp = (await session.execute(text(
        "select name from companies where id = :id"
    ), {"id": ev["company_id"]})).mappings().first()
    ev["_company"] = dict(comp) if comp else {}
    return ev


async def _load_viewable(session: AsyncSession, user: CurrentUser, eval_id: str) -> dict:
    """Load an evaluation only if the caller is allowed to read it; otherwise
    404 (never reveal that an id exists to someone who may not see it)."""
    ev = await _load(session, eval_id)
    actor_emp = await _actor_employee_id(session, user.id)
    if not _can_view(user, actor_emp, ev):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "evaluation not found")
    return ev


async def view_detail(session: AsyncSession, user: CurrentUser, eval_id: str) -> dict:
    await _load_viewable(session, user, eval_id)
    return await get_detail(session, eval_id)


async def list_all(session: AsyncSession, user: CurrentUser) -> list[dict]:
    see_all = _sees_all_evaluations(user)
    actor_emp = None if see_all else await _actor_employee_id(session, user.id)
    rows = (await session.execute(text(
        "select ev.id, ev.employee_id, ev.evaluator_id, ev.kind, ev.probation_checkpoint, ev.status, "
        "ev.eval_score, ev.eval_max, ev.total_score, ev.percentage, ev.created_at, "
        "ack.decision as acknowledgement_decision, ack.signed_at as acknowledgement_signed_at "
        "from evaluations ev join employees emp on emp.id = ev.employee_id "
        "left join evaluation_acknowledgements ack "
        "       on ack.evaluation_id = ev.id and ack.superseded_at is null "
        "where :see_all "                                  # HR / GM / MD / super_admin
        "   or emp.id = :actor_emp "                       # the subject themselves
        "   or emp.supervisor_id = :actor_emp "            # direct supervisor
        "   or emp.manager_id = :actor_emp "               # dept manager
        "order by ev.created_at desc"
    ), {"see_all": see_all, "actor_emp": actor_emp})).mappings().all()
    return [dict(r) for r in rows]


async def list_inbox(session: AsyncSession, user: CurrentUser) -> list[dict]:
    """Evaluations awaiting *this* user's action, resolved the same way
    approve()/return_to_draft()/finalize() authorize each step:
      score        -> user is the assigned evaluator (supervisor), status draft/returned
      dept_approve -> user is the subject's manager, status submitted
      md_approve   -> user holds role 'md', status dept_approved
      finalize     -> user holds role 'hr_admin', status md_approved
    """
    actor_emp = await _actor_employee_id(session, user.id)
    is_md = user.is_super_admin or _is_md_or_gm(user)
    is_hr = user.is_super_admin or "hr_admin" in user.roles
    rows = (await session.execute(text(
        "select ev.id, ev.employee_id, emp.emp_code, emp.full_name, ev.kind, ev.status, "
        "ev.percentage, ev.updated_at, ev.created_at, "
        "case "
        "  when ev.status in ('draft','returned') and ev.evaluator_id = :actor_emp then 'score' "
        "  when ev.status = 'submitted' and emp.manager_id = :actor_emp then 'dept_approve' "
        "  when ev.status = 'dept_approved' and :is_md then 'md_approve' "
        "  when ev.status = 'md_approved' and :is_hr then 'finalize' "
        "end as action "
        "from evaluations ev join employees emp on emp.id = ev.employee_id "
        "where (ev.status in ('draft','returned') and ev.evaluator_id = :actor_emp) "
        "   or (ev.status = 'submitted' and emp.manager_id = :actor_emp) "
        "   or (ev.status = 'dept_approved' and :is_md) "
        "   or (ev.status = 'md_approved' and :is_hr) "
        "order by coalesce(ev.updated_at, ev.created_at) desc"
    ), {"actor_emp": actor_emp, "is_md": is_md, "is_hr": is_hr})).mappings().all()
    return [dict(r) for r in rows]


async def create(session: AsyncSession, user: CurrentUser, payload) -> dict:
    emp = (await session.execute(text(
        "select id, company_id, supervisor_id, manager_id from employees where id = :id"
    ), {"id": str(payload.employee_id)})).mappings().first()
    if emp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "employee not found")
    if emp["supervisor_id"] is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "employee has no supervisor to evaluate them")

    actor_emp = await _actor_employee_id(session, user.id)
    allowed = user.is_super_admin or "hr_admin" in user.roles or _same_employee(actor_emp, emp["supervisor_id"])
    if not allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not allowed to create this evaluation")

    # The evaluation belongs to whichever company owns the EMPLOYEE, not the
    # actor -- for every normal (non-super_admin) caller these are always the
    # same company anyway (RLS already prevents them from ever selecting an
    # employee outside their own tenant), so this is a no-op in practice.
    # It matters only for super_admin, whose own company_id is the reserved
    # platform tenant: using user.company_id there would have silently filed
    # the evaluation under the platform tenant instead of the real company,
    # making it invisible to that company's own hr_admin/staff afterward.
    target_company = emp["company_id"]

    tmpl = (await session.execute(
        text("select company_id from criteria_templates where id = :id"),
        {"id": str(payload.template_id)},
    )).mappings().first()
    if tmpl is None or tmpl["company_id"] != target_company:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "template does not belong to this employee's company")

    ev = (await session.execute(text(
        "insert into evaluations "
        "(company_id, cycle_id, employee_id, evaluator_id, template_id, kind, "
        " probation_checkpoint, period_start, period_end) "
        "values (:cid, :cycle, :emp, :evltr, :tmpl, :kind, :chk, :ps, :pe) "
        "returning id"
    ), {
        "cid": target_company, "cycle": str(payload.cycle_id) if payload.cycle_id else None,
        "emp": str(payload.employee_id), "evltr": emp["supervisor_id"],
        "tmpl": str(payload.template_id), "kind": payload.kind,
        "chk": payload.probation_checkpoint,
        "ps": payload.period_start, "pe": payload.period_end,
    })).mappings().one()
    eval_id = str(ev["id"])

    n = (await session.execute(
        text("select app.snapshot_evaluation_items(:id)"), {"id": eval_id}
    )).scalar_one()
    if not n:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "template has no criteria to snapshot")

    await write_audit(session, company_id=target_company, actor_id=user.id,
                      action="evaluation_created", entity_type="evaluations",
                      entity_id=eval_id, after={"employee_id": str(payload.employee_id),
                                                "kind": payload.kind, "items": n})
    return await get_detail(session, eval_id)


def _require_editable(ev: dict) -> None:
    if ev["status"] not in ("draft", "returned"):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"evaluation is '{ev['status']}' and can no longer be edited")


async def _require_evaluator(session: AsyncSession, user: CurrentUser, ev: dict) -> None:
    actor_emp = await _actor_employee_id(session, user.id)
    if not (user.is_super_admin or _same_employee(actor_emp, ev["evaluator_id"])):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only the assigned supervisor may do this")


async def save_scores(session: AsyncSession, user: CurrentUser, eval_id: str, payload) -> dict:
    ev = await _load(session, eval_id)
    _require_editable(ev)
    await _require_evaluator(session, user, ev)

    valid = {r[0] for r in (await session.execute(
        text("select id from evaluation_items where evaluation_id = :id"), {"id": eval_id}
    )).all()}
    for s in payload.scores:
        if s.evaluation_item_id not in valid:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "score references an item not in this evaluation")
        await session.execute(text(
            "insert into evaluation_scores (evaluation_id, company_id, evaluation_item_id, score) "
            "values (:e, :c, :i, :s) "
            "on conflict (evaluation_id, evaluation_item_id) do update set score = excluded.score, updated_at = now()"
        ), {"e": eval_id, "c": user.company_id, "i": str(s.evaluation_item_id), "s": s.score})

    for cm in payload.comments:
        await session.execute(text(
            "insert into evaluation_comments (evaluation_id, company_id, category_order, comment) "
            "values (:e, :c, :o, :m) "
            "on conflict (evaluation_id, category_order) do update set comment = excluded.comment"
        ), {"e": eval_id, "c": user.company_id, "o": cm.category_order, "m": cm.comment})

    await session.execute(text("select app.recompute_evaluation_totals(:id)"), {"id": eval_id})
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="score_saved", entity_type="evaluations", entity_id=eval_id,
                      after={"scores": len(payload.scores)})
    return await get_detail(session, eval_id)


async def set_attendance(session: AsyncSession, user: CurrentUser, eval_id: str, payload) -> dict:
    """HR-only: record raw attendance facts for the period. The evaluator's
    save_scores no longer accepts attendance (kept read-only there) — HR owns
    this data so a supervisor can't silently overwrite what HR entered."""
    ev = await _load(session, eval_id)
    if ev["status"] == "finalized":
        raise HTTPException(status.HTTP_409_CONFLICT, "ปิดใบแล้ว แก้ไขข้อมูลการมา-ลาไม่ได้")

    existing = (await session.execute(text(
        "select attendance_score, attendance_score_overridden from evaluation_attendance where evaluation_id = :id"
    ), {"id": eval_id})).mappings().first()

    brackets = await attendance_brackets.get_brackets(session, user.company_id)
    computed = attendance_brackets.compute_score(brackets, payload.sick_days, payload.personal_days,
                                                  payload.late_count, payload.absent_days)
    if payload.clear_override:
        score, overridden = computed, False
    elif payload.attendance_score is not None:
        score, overridden = payload.attendance_score, True
    elif existing and existing["attendance_score_overridden"]:
        # a previous manual override exists and this request doesn't touch it —
        # re-editing the raw figures must not silently recompute over it.
        score, overridden = existing["attendance_score"], True
    else:
        score, overridden = computed, False

    await session.execute(text(
        "insert into evaluation_attendance "
        "(evaluation_id, company_id, sick_days, personal_days, late_count, late_minutes, absent_days, "
        " attendance_score, attendance_score_overridden) "
        "values (:e,:c,:sd,:pd,:lc,:lm,:ad,:ascore,:ov) "
        "on conflict (evaluation_id) do update set sick_days=excluded.sick_days, "
        "personal_days=excluded.personal_days, late_count=excluded.late_count, "
        "late_minutes=excluded.late_minutes, absent_days=excluded.absent_days, "
        "attendance_score=excluded.attendance_score, "
        "attendance_score_overridden=excluded.attendance_score_overridden, updated_at=now()"
    ), {"e": eval_id, "c": user.company_id, "sd": payload.sick_days, "pd": payload.personal_days,
        "lc": payload.late_count, "lm": payload.late_minutes, "ad": payload.absent_days,
        "ascore": score, "ov": overridden})

    await session.execute(text("select app.recompute_evaluation_totals(:id)"), {"id": eval_id})
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="attendance_updated", entity_type="evaluations", entity_id=eval_id,
                      after={"attendance_score": score, "overridden": overridden})
    return await get_detail(session, eval_id)


async def submit(session: AsyncSession, user: CurrentUser, eval_id: str) -> dict:
    ev = await _load(session, eval_id)
    _require_editable(ev)
    await _require_evaluator(session, user, ev)

    counts = (await session.execute(text(
        "select (select count(*) from evaluation_items where evaluation_id=:id) as items, "
        "(select count(*) from evaluation_scores where evaluation_id=:id) as scores"
    ), {"id": eval_id})).mappings().one()
    if counts["items"] == 0 or counts["scores"] < counts["items"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "all items must be scored before submit")

    await session.execute(text("select app.recompute_evaluation_totals(:id)"), {"id": eval_id})
    await session.execute(text(
        "update evaluations set status='submitted', submitted_at=now() where id=:id"
    ), {"id": eval_id})
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="evaluation_submitted", entity_type="evaluations", entity_id=eval_id)
    return await get_detail(session, eval_id)


async def approve(session: AsyncSession, user: CurrentUser, eval_id: str, comment) -> dict:
    ev = await _load(session, eval_id)
    actor_emp = await _actor_employee_id(session, user.id)

    if ev["status"] == "submitted":
        if not (user.is_super_admin or _same_employee(actor_emp, ev["emp_manager_id"])):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "only the department manager may approve now")
        new_status, step = "dept_approved", "dept_manager"
    elif ev["status"] == "dept_approved":
        if not (user.is_super_admin or _is_md_or_gm(user)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "only the GM/MD may approve now")
        # The employee signs between the dept manager's approval and this one,
        # so GM/MD always approve an evaluation the employee has already been
        # shown. A refusal to sign counts too (recorded with a witness) --
        # otherwise one uncooperative employee would freeze the evaluation
        # forever.
        if not await _has_active_acknowledgement(session, eval_id):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "ต้องบันทึกการรับทราบของพนักงานก่อน GM/MD จึงจะอนุมัติได้")
        new_status, step = "md_approved", "md"
    else:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"evaluation in '{ev['status']}' cannot be approved (use finalize for HR)")

    await session.execute(text("update evaluations set status=:s where id=:id"),
                          {"s": new_status, "id": eval_id})
    await session.execute(text(
        "insert into evaluation_approvals (company_id, evaluation_id, step, actor_id, decision, comment) "
        "values (:c,:e,:st,:a,'approved',:cm)"
    ), {"c": user.company_id, "e": eval_id, "st": step, "a": user.id, "cm": comment})
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="evaluation_approved", entity_type="evaluations", entity_id=eval_id,
                      after={"step": step, "status": new_status})
    return await get_detail(session, eval_id)


async def return_to_draft(session: AsyncSession, user: CurrentUser, eval_id: str, comment) -> dict:
    ev = await _load(session, eval_id)
    actor_emp = await _actor_employee_id(session, user.id)

    if ev["status"] == "submitted":
        authorized = user.is_super_admin or _same_employee(actor_emp, ev["emp_manager_id"])
        step = "dept_manager"
    elif ev["status"] == "dept_approved":
        authorized = user.is_super_admin or _is_md_or_gm(user)
        step = "md"
    elif ev["status"] == "md_approved":
        authorized = user.is_super_admin or "hr_admin" in user.roles
        step = "hr"
    else:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"evaluation in '{ev['status']}' cannot be returned")
    if not authorized:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not the current approver")

    await session.execute(text("update evaluations set status='returned' where id=:id"), {"id": eval_id})
    # The employee signed for a specific set of scores; a return means those
    # scores are about to change, so that signature stops counting. It is kept
    # (never deleted -- it is evidence of what was shown at the time) and a
    # fresh one must be collected after the rescore.
    superseded = (await session.execute(
        text("select app.supersede_acknowledgement(:e, :c)"),
        {"e": eval_id, "c": ev["company_id"]},
    )).scalar_one()
    await session.execute(text(
        "insert into evaluation_approvals (company_id, evaluation_id, step, actor_id, decision, comment) "
        "values (:c,:e,:st,:a,'returned',:cm)"
    ), {"c": user.company_id, "e": eval_id, "st": step, "a": user.id, "cm": comment})
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="evaluation_returned", entity_type="evaluations", entity_id=eval_id,
                      after={"step": step, "acknowledgements_superseded": superseded})
    return await get_detail(session, eval_id)


async def finalize(session: AsyncSession, user: CurrentUser, eval_id: str, payload) -> dict:
    ev = await _load(session, eval_id)
    if ev["status"] != "md_approved":
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"evaluation in '{ev['status']}' cannot be finalized (needs md_approved)")
    if not (user.is_super_admin or "hr_admin" in user.roles):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only HR may finalize")

    await session.execute(text("select app.recompute_evaluation_totals(:id)"), {"id": eval_id})
    await session.execute(text(
        "update evaluations set status='finalized', finalized_at=now(), "
        "probation_decision=:pd, probation_extend_days=:ped, decision_note=:dn where id=:id"
    ), {"pd": payload.probation_decision, "ped": payload.probation_extend_days,
        "dn": payload.decision_note, "id": eval_id})
    await session.execute(text(
        "insert into evaluation_approvals (company_id, evaluation_id, step, actor_id, decision, comment) "
        "values (:c,:e,'hr',:a,'approved',:cm)"
    ), {"c": user.company_id, "e": eval_id, "a": user.id, "cm": payload.comment})
    await write_audit(session, company_id=user.company_id, actor_id=user.id,
                      action="evaluation_finalized", entity_type="evaluations", entity_id=eval_id,
                      after={"probation_decision": payload.probation_decision})
    return await get_detail(session, eval_id)
