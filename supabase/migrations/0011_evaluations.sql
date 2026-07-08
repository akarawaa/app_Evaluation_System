-- 0011_evaluations.sql
-- Evaluation core (Phase 2). tenant-scoped + RLS. See docs/EVALUATION_DESIGN.md.

-- ── evaluation_cycles (annual batching) ───────────────────────────────────
create table evaluation_cycles (
  id                  uuid primary key default gen_random_uuid(),
  company_id          uuid not null references companies(id) on delete cascade,
  name                text not null,
  year                int,
  period_start        date,
  period_end          date,
  default_template_id uuid references criteria_templates(id) on delete set null,
  status              text not null default 'open' check (status in ('open','closed')),
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  unique (company_id, name)
);

-- ── evaluations (header) ──────────────────────────────────────────────────
create table evaluations (
  id                   uuid primary key default gen_random_uuid(),
  company_id           uuid not null references companies(id) on delete cascade,
  cycle_id             uuid references evaluation_cycles(id) on delete set null,
  employee_id          uuid not null references employees(id) on delete cascade,
  evaluator_id         uuid references employees(id) on delete set null,   -- = employee.supervisor_id at creation
  template_id          uuid references criteria_templates(id) on delete set null,
  kind                 text not null check (kind in ('annual','probation')),
  probation_checkpoint text check (probation_checkpoint in ('30','60','90','119')),
  period_start         date,
  period_end           date,
  status               text not null default 'draft'
                         check (status in ('draft','submitted','dept_approved','md_approved','finalized','returned')),
  eval_score           numeric,
  eval_max             numeric,
  attendance_score     numeric,
  total_score          numeric,
  percentage           numeric,
  probation_decision   text check (probation_decision in ('hire','not_hire','extend','other')),
  probation_extend_days int,
  decision_note        text,
  snapshot_at          timestamptz,
  submitted_at         timestamptz,
  finalized_at         timestamptz,
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),
  constraint eval_kind_checkpoint check (
    (kind = 'probation' and probation_checkpoint is not null) or
    (kind = 'annual'    and probation_checkpoint is null)
  ),
  constraint eval_not_self check (evaluator_id is null or evaluator_id <> employee_id)
);
create unique index uq_eval_annual on evaluations(company_id, employee_id, cycle_id)
  where kind = 'annual' and cycle_id is not null;
create unique index uq_eval_probation on evaluations(company_id, employee_id, probation_checkpoint)
  where kind = 'probation';

-- ── evaluation_items (snapshot of criteria at creation) ───────────────────
create table evaluation_items (
  id             uuid primary key default gen_random_uuid(),
  evaluation_id  uuid not null references evaluations(id) on delete cascade,
  company_id     uuid not null references companies(id) on delete cascade,
  category_order int  not null,
  category_name  text not null,
  item_order     int  not null,
  item_name      text not null,
  weight         numeric not null default 1,
  source_item_id uuid,
  unique (evaluation_id, category_order, item_order)
);

-- ── evaluation_scores (per item, 1..5 in 0.5 steps) ───────────────────────
create table evaluation_scores (
  id                 uuid primary key default gen_random_uuid(),
  evaluation_id      uuid not null references evaluations(id) on delete cascade,
  company_id         uuid not null references companies(id) on delete cascade,
  evaluation_item_id uuid not null references evaluation_items(id) on delete cascade,
  score              numeric not null check (score >= 1 and score <= 5 and (score * 2) = trunc(score * 2)),
  updated_at         timestamptz not null default now(),
  unique (evaluation_id, evaluation_item_id)
);

-- ── evaluation_comments (category-level "ข้อคิดเห็นเพิ่มเติม") ────────────
create table evaluation_comments (
  id             uuid primary key default gen_random_uuid(),
  evaluation_id  uuid not null references evaluations(id) on delete cascade,
  company_id     uuid not null references companies(id) on delete cascade,
  category_order int  not null,
  comment        text,
  unique (evaluation_id, category_order)
);

-- ── evaluation_attendance (raw data + derived score, formula TBD by HR) ────
create table evaluation_attendance (
  evaluation_id    uuid primary key references evaluations(id) on delete cascade,
  company_id       uuid not null references companies(id) on delete cascade,
  sick_days        int not null default 0,
  personal_days    int not null default 0,
  late_count       int not null default 0,
  late_minutes     int not null default 0,
  absent_days      int not null default 0,
  attendance_score numeric,
  updated_at       timestamptz not null default now()
);

-- ── indexes (lead with company_id) ────────────────────────────────────────
create index idx_eval_cycles_company        on evaluation_cycles(company_id);
create index idx_evaluations_company_status on evaluations(company_id, status);
create index idx_evaluations_company_emp    on evaluations(company_id, employee_id);
create index idx_evaluations_company_evltr  on evaluations(company_id, evaluator_id);
create index idx_evaluations_cycle          on evaluations(cycle_id);
create index idx_eval_items_eval            on evaluation_items(evaluation_id);
create index idx_eval_items_company         on evaluation_items(company_id);
create index idx_eval_scores_eval           on evaluation_scores(evaluation_id);
create index idx_eval_scores_company        on evaluation_scores(company_id);
create index idx_eval_comments_eval         on evaluation_comments(evaluation_id);
create index idx_eval_attendance_company    on evaluation_attendance(company_id);

-- ── updated_at triggers ───────────────────────────────────────────────────
create trigger trg_eval_cycles_updated before update on evaluation_cycles for each row execute function app.set_updated_at();
create trigger trg_evaluations_updated  before update on evaluations       for each row execute function app.set_updated_at();
create trigger trg_eval_scores_updated  before update on evaluation_scores for each row execute function app.set_updated_at();
create trigger trg_eval_attend_updated  before update on evaluation_attendance for each row execute function app.set_updated_at();

-- ── RLS on all evaluation tables (same tenant policy as Phase 1) ──────────
do $$
declare t text;
begin
  foreach t in array array[
    'evaluation_cycles','evaluations','evaluation_items',
    'evaluation_scores','evaluation_comments','evaluation_attendance'
  ] loop
    execute format('alter table %I enable row level security', t);
    execute format('alter table %I force  row level security', t);
    execute format('create policy %I on %I for select using (app.is_super_admin() or company_id = app.current_company_id())', t||'_sel', t);
    execute format('create policy %I on %I for insert with check (app.is_super_admin() or company_id = app.current_company_id())', t||'_ins', t);
    execute format('create policy %I on %I for update using (app.is_super_admin() or company_id = app.current_company_id()) with check (app.is_super_admin() or company_id = app.current_company_id())', t||'_upd', t);
    execute format('create policy %I on %I for delete using (app.is_super_admin() or company_id = app.current_company_id())', t||'_del', t);
  end loop;
end $$;

grant select, insert, update, delete on
  evaluation_cycles, evaluations, evaluation_items,
  evaluation_scores, evaluation_comments, evaluation_attendance
to authenticated;
