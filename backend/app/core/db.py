"""Async DB access with per-request RLS enforcement.

The engine connects as `postgres`, but every tenant request DOWNGRADES to the
non-privileged `authenticated` role and injects the verified JWT claims into
`request.jwt.claims`. Postgres then applies the same RLS policies that protect
the PostgREST/Supabase path — so a missing WHERE clause can never leak tenants.
"""
import json
from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import CurrentUser, get_current_user

_settings = get_settings()
engine = create_async_engine(_settings.database_url, pool_pre_ping=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_tenant_session(
    user: CurrentUser = Depends(get_current_user),
) -> AsyncIterator[AsyncSession]:
    """Yield a session bound to the caller's tenant; commits on success."""
    async with SessionLocal() as session:
        async with session.begin():
            # order matters: set claims (as postgres) then drop privileges
            await session.execute(
                text("select set_config('request.jwt.claims', :claims, true)"),
                {"claims": json.dumps(user.claims)},
            )
            await session.execute(text("set local role authenticated"))

            # A suspended tenant's own members are locked out at this single
            # choke point (super_admin, who isn't tied to a customer tenant,
            # is exempt). Enforced here rather than per-RLS-policy so
            # suspend/reactivate needs no schema changes to any table.
            if not user.is_super_admin and user.company_id:
                row = (
                    await session.execute(
                        text("select status from companies where id = :cid"),
                        {"cid": user.company_id},
                    )
                ).first()
                if row is None or row[0] != "active":
                    raise HTTPException(status.HTTP_403_FORBIDDEN, "This company's account is suspended")

            yield session
