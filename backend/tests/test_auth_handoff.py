"""SSO handoff exchange (platform-core/docs/PORTAL.md C3).

Black-box against the running :8000 server (Eval's suite convention). The
full loop needs the portal service; here we cover the local contract: shape
validation and that a bad token_hash is 401, not 500.
"""
import pytest


@pytest.mark.asyncio
async def test_exchange_rejects_short_token(api):
    r = await api.post("/api/auth/exchange", json={"token_hash": "short"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_exchange_requires_token(api):
    r = await api.post("/api/auth/exchange", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_exchange_garbage_token_is_401_not_500(api):
    r = await api.post("/api/auth/exchange", json={"token_hash": "0" * 40})
    assert r.status_code == 401
