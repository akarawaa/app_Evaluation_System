"""FastAPI entrypoint (skeleton).

Phase 1 wiring is added incrementally per docs/PHASE_1_PLAN.md:
  Step 5 -> JWT auth dependency + tenant guard, request_id + logging middleware,
            security headers, audit helper.
  Step 6 -> RBAC & tenant provisioning routers (mounted under /api).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="E-Appraisal API",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,   # allowlist only (OWASP A05)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


# TODO(Step 5): add_middleware(RequestIdMiddleware), security headers
# TODO(Step 5): app.dependency for get_current_user() + tenant_guard()
# TODO(Step 6): app.include_router(...) for provisioning / rbac / criteria
