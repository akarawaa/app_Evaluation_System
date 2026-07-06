-- 0005_audit.sql
-- Append-only audit trail. See docs/LOGGING_AND_AUDIT.md.
-- Immutability is enforced in 0006 by granting only SELECT/INSERT via RLS
-- (no UPDATE/DELETE policy => those commands are denied).

create table audit_logs (
  id               bigint generated always as identity primary key,
  company_id       uuid references companies(id) on delete set null,   -- NULL = platform-level event
  actor_profile_id uuid references profiles(id)  on delete set null,
  action           text not null,        -- login_success | create | update | delete | view_sensitive | ...
  entity_type      text,                 -- employees | criteria_items | ...
  entity_id        text,
  before           jsonb,                -- prior values (secret fields stripped)
  after            jsonb,                -- new values (secret fields stripped)
  ip               inet,
  user_agent       text,
  created_at       timestamptz not null default now()
);

create index idx_audit_company_created on audit_logs(company_id, created_at desc);
create index idx_audit_actor           on audit_logs(actor_profile_id);
create index idx_audit_entity          on audit_logs(entity_type, entity_id);
