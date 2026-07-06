# Backend (FastAPI)

## Layout
```
app/
  main.py            # FastAPI entrypoint (CORS, health; middleware/routers added per PHASE_1_PLAN)
  core/              # config, security, logging, shared deps
  api/               # routers (thin HTTP layer)
  services/          # business logic + audit writes (single source)
  repositories/      # data access (SQLAlchemy async; sets RLS jwt claims)
  schemas/           # Pydantic DTOs + validation
```
Rule: `api -> services -> repositories`. Routers never touch the DB directly.

## Setup (later, when coding Step 5)
```
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env    # then fill values
uvicorn app.main:app --reload
```

## Security notes
- Connect to Postgres with a NON-BYPASSRLS role for tenant ops; `service_role` only for admin/provisioning.
- Every request sets `request.jwt.claims` on its DB session so RLS applies.
- See ../docs/SECURITY.md and ../docs/LOGGING_AND_AUDIT.md.
