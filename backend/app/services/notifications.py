"""Daily digest: one email per person summarizing every evaluation action
pending on them, instead of a message per status transition.

Why this exists: real-time per-event notifications (one message the instant
a status changes) don't scale during evaluation season -- 300 employees
through ~4 approval stages each is ~1,200 events in a single month, which
would dwarf any shared per-channel quota (this suite's LINE OA free tier is
~200 messages/month, shared with app_leave_approve's own real-time leave
notifications). Collapsing to one email per person per day changes the
multiplier from (employees x stage transitions) to (people who currently
have something pending x days), which is the number that actually matters
for "how many messages does this cost," not how many evaluations exist.

Reuses exactly the same routing rules as services/evaluations.list_inbox
(score -> evaluator, dept_approve -> subject's manager, md_approve -> role
md/gm, finalize -> role hr_admin) but computed for every profile across
every company in one query, since a digest run has no single caller to
scope by. That requires reading auth.users.email, which no ordinary tenant
session can do -- hence core.db.service_session() (full postgres role, no
RLS) instead of get_tenant_session.
"""
from collections import defaultdict

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services import email as email_svc
from app.services.audit import write_audit

logger = structlog.get_logger()

ACTION_LABEL = {
    "score": "รอให้คะแนน",
    "dept_approve": "รออนุมัติ (ผจก.แผนก)",
    "md_approve": "รออนุมัติ (GM/MD)",
    "finalize": "รอสรุป/ปิดใบ (HR)",
}

# One CTE (`pending`) referenced by all four branches; each branch resolves
# a different kind of target (an employee_id for score/dept_approve, a role
# held in that evaluation's own company for md_approve/finalize) -- the same
# distinction list_inbox makes per-caller, just for every row at once here.
_QUERY = text("""
    with pending as (
        select ev.id, ev.company_id, ev.evaluator_id, ev.status,
               emp.emp_code, emp.full_name, emp.manager_id
        from evaluations ev
        join employees emp on emp.id = ev.employee_id
        where ev.status in ('draft', 'returned', 'submitted', 'dept_approved', 'md_approved')
    )
    select p.id as profile_id, pending.company_id, u.email, p.display_name,
           pending.id as eval_id, pending.emp_code, pending.full_name,
           'score' as action
    from pending
    join profiles p on p.employee_id = pending.evaluator_id
    join auth.users u on u.id = p.id
    where pending.status in ('draft', 'returned')

    union all

    select p.id, pending.company_id, u.email, p.display_name, pending.id,
           pending.emp_code, pending.full_name, 'dept_approve'
    from pending
    join profiles p on p.employee_id = pending.manager_id
    join auth.users u on u.id = p.id
    where pending.status = 'submitted'

    union all

    select p.id, pending.company_id, u.email, p.display_name, pending.id,
           pending.emp_code, pending.full_name, 'md_approve'
    from pending
    join profiles p on p.company_id = pending.company_id
    join user_roles ur on ur.profile_id = p.id and ur.company_id = pending.company_id
    join roles r on r.id = ur.role_id and r.code in ('md', 'gm')
    join auth.users u on u.id = p.id
    where pending.status = 'dept_approved'

    union all

    select p.id, pending.company_id, u.email, p.display_name, pending.id,
           pending.emp_code, pending.full_name, 'finalize'
    from pending
    join profiles p on p.company_id = pending.company_id
    join user_roles ur on ur.profile_id = p.id and ur.company_id = pending.company_id
    join roles r on r.id = ur.role_id and r.code = 'hr_admin'
    join auth.users u on u.id = p.id
    where pending.status = 'md_approved'
""")


def _build_email(display_name: str | None, items: list[dict]) -> tuple[str, str]:
    settings = get_settings()
    who = display_name or "คุณ"
    subject = f"สรุปงานรอดำเนินการ — ระบบ E-Appraisal ({len(items)} รายการ)"

    by_action: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        by_action[it["action"]].append(it)

    sections = []
    # Fixed order matches the approval chain, not dict/insertion order.
    for action in ("score", "dept_approve", "md_approve", "finalize"):
        rows = by_action.get(action)
        if not rows:
            continue
        lines = "".join(
            f'<li><a href="{settings.frontend_url}/evaluations/{r["eval_id"]}">'
            f'{r["emp_code"]} · {r["full_name"]}</a></li>'
            for r in rows
        )
        sections.append(f"<p><b>{ACTION_LABEL[action]} ({len(rows)} รายการ)</b></p><ul>{lines}</ul>")

    body = f"""
    <p>เรียน {who},</p>
    <p>คุณมีใบประเมินรอดำเนินการทั้งหมด {len(items)} รายการ:</p>
    {"".join(sections)}
    <p>หรือดูรายการทั้งหมดได้ที่: <a href="{settings.frontend_url}/inbox">งานที่รอฉัน</a></p>
    """
    return subject, body


async def send_daily_digests(session: AsyncSession) -> dict:
    """Runs the full cross-company query, groups by recipient, sends one
    email each, then writes one audit row per company (not per recipient --
    this is a system job touching many inboxes at once, the same "sensitive
    read at scale" rationale already used for evaluation exports/compare,
    not a per-user mutation with its own before/after state).

    Returns a small summary for the triggering endpoint to report back."""
    rows = (await session.execute(_QUERY)).mappings().all()

    by_profile: dict[str, dict] = {}
    for r in rows:
        entry = by_profile.setdefault(
            r["profile_id"],
            {"email": r["email"], "display_name": r["display_name"], "company_id": r["company_id"], "items": []},
        )
        entry["items"].append(dict(r))

    sent = 0
    for profile_id, data in by_profile.items():
        if not data["email"]:
            logger.warning("digest_skip_no_email", profile_id=profile_id)
            continue
        subject, body = _build_email(data["display_name"], data["items"])
        await email_svc.send_email(data["email"], subject, body)
        sent += 1

    by_company: dict[str, dict] = defaultdict(lambda: {"recipients": 0, "items": 0})
    for data in by_profile.values():
        by_company[data["company_id"]]["recipients"] += 1
        by_company[data["company_id"]]["items"] += len(data["items"])
    for company_id, totals in by_company.items():
        await write_audit(
            session, company_id=company_id, actor_id=None, action="digest_emails_sent",
            entity_type="notifications", after=totals,
        )

    logger.info("daily_digest_sent", recipients=sent, pending_rows=len(rows), companies=len(by_company))
    return {"recipients": sent, "pending_rows": len(rows)}
