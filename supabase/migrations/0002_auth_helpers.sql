-- 0002_auth_helpers.sql
-- Helper functions that read the JWT claims for RLS.
--
-- The claims are provided by:
--   * Supabase/PostgREST  -> sets `request.jwt.claims` automatically
--   * Our FastAPI backend  -> MUST call `set_config('request.jwt.claims', '<json>', true)`
--                             at the start of each request/transaction so RLS applies.
--
-- Required custom claims (injected via Supabase Custom Access Token Hook):
--   company_id     : uuid of the user's tenant
--   is_super_admin : boolean (platform-level admin)
--   roles          : json array of role codes, e.g. ["hr_admin","manager"]

create or replace function app.jwt_claims()
returns jsonb
language sql
stable
as $$
  select coalesce(
    nullif(current_setting('request.jwt.claims', true), '')::jsonb,
    '{}'::jsonb
  );
$$;

create or replace function app.current_company_id()
returns uuid
language sql
stable
as $$
  select nullif(app.jwt_claims() ->> 'company_id', '')::uuid;
$$;

create or replace function app.is_super_admin()
returns boolean
language sql
stable
as $$
  select coalesce((app.jwt_claims() ->> 'is_super_admin')::boolean, false);
$$;

-- true if the JWT `roles` array contains the given role code
create or replace function app.has_role(role_code text)
returns boolean
language sql
stable
as $$
  select coalesce(app.jwt_claims() -> 'roles' ? role_code, false);
$$;

-- shared trigger to maintain updated_at
create or replace function app.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;
