"""Audit helper — the single place that writes audit_logs, in the SAME
transaction as the mutation. See docs/LOGGING_AND_AUDIT.md."""
import json
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_INSERT = text(
    """
    insert into audit_logs
        (company_id, actor_profile_id, action, entity_type, entity_id, before, after)
    values
        (:company_id, :actor_id, :action, :entity_type, :entity_id,
         cast(:before as jsonb), cast(:after as jsonb))
    """
)


async def write_audit(
    session: AsyncSession,
    *,
    company_id: Optional[str],
    actor_id: Optional[str],
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    before: Optional[dict] = None,
    after: Optional[dict] = None,
) -> None:
    await session.execute(
        _INSERT,
        {
            "company_id": company_id,
            "actor_id": actor_id,
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id is not None else None,
            "before": json.dumps(before, default=str) if before is not None else None,
            "after": json.dumps(after, default=str) if after is not None else None,
        },
    )
