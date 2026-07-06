# Supabase (Database, Auth, RLS)

Schema is managed here as SQL migrations — **single source of truth**.
The FastAPI backend uses SQLAlchemy to *access* these tables, not to migrate them.

## Migrations (run in order)
| file | purpose |
|---|---|
| 0001_extensions.sql   | pgcrypto + `app` schema |
| 0002_auth_helpers.sql | JWT claim helpers + updated_at trigger fn |
| 0003_tenant_identity.sql | companies, branches, roles, employees, profiles, user_roles + indexes |
| 0004_criteria.sql     | criteria_templates / categories / items (BARS) |
| 0005_audit.sql        | audit_logs (append-only) |
| 0006_rls_policies.sql | enable/force RLS + policies + grants |
| seed.sql              | role catalog + master FMHR07 templates |

## Local dev (recommended)
```
supabase init          # first time only (generates config.toml)
supabase start         # local stack (Postgres @ 54322, API @ 54321)
supabase db reset      # applies migrations + seed.sql
```

## Deploy to cloud
```
supabase link --project-ref <ref>
supabase db push
```

## Critical security note
- RLS is the primary tenant guardrail. The backend must connect with a role that
  does NOT bypass RLS, and set `request.jwt.claims` per request.
- `service_role` bypasses RLS — use only for controlled admin/provisioning tasks.
- Custom Access Token Hook must inject: `company_id`, `is_super_admin`, `roles`.
  (Configured in Step 3 — see ../docs/PHASE_1_PLAN.md.)
