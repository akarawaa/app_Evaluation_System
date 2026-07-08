-- 0012_evaluation_workflow.sql
-- Approval trail (Phase 2). Append-only, like audit_logs.
-- Fixed chain: supervisor submit -> dept_manager -> md -> hr finalize (+ return).

create table evaluation_approvals (
  id            uuid primary key default gen_random_uuid(),
  company_id    uuid not null references companies(id) on delete cascade,
  evaluation_id uuid not null references evaluations(id) on delete cascade,
  step          text not null check (step in ('dept_manager','md','hr')),
  actor_id      uuid references profiles(id) on delete set null,
  decision      text not null check (decision in ('approved','returned')),
  comment       text,
  decided_at    timestamptz not null default now()
);

create index idx_eval_approvals_eval    on evaluation_approvals(evaluation_id);
create index idx_eval_approvals_company on evaluation_approvals(company_id, decided_at desc);

-- append-only: select + insert only (no update/delete policy => denied)
alter table evaluation_approvals enable row level security;
alter table evaluation_approvals force  row level security;
create policy eval_approvals_sel on evaluation_approvals for select
  using (app.is_super_admin() or company_id = app.current_company_id());
create policy eval_approvals_ins on evaluation_approvals for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());

grant select, insert on evaluation_approvals to authenticated;
