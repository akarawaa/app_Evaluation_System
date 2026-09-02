-- 0023_attendance_brackets.sql
-- Replaces the linear formula (company_attendance_formula, 0017) as the
-- active attendance-scoring model. The real company policy (FMHR07 p.4,
-- photographed 2026-08-29) scores 4 categories independently by which
-- bracket the raw count falls in -- a linear "full_score - coef*count"
-- deduction cannot represent this (e.g. sick leave scores 10 for 0-5 days,
-- then drops unevenly: 8, 6, 4, 2, 1, 0 -- not a constant per-day penalty).
--
-- 0017's table/endpoints are left in place (harmless, unused by the active
-- scoring path from this point on) rather than dropped -- non-destructive,
-- in case a tenant already saved a custom value there.
--
-- One row per (company, category, bracket). Absence of any rows for a
-- company+category means "use the built-in defaults" (see
-- app/services/attendance_brackets.py), same fallback convention as 0017.

create table company_attendance_brackets (
  id          uuid primary key default gen_random_uuid(),
  company_id  uuid not null references companies(id) on delete cascade,
  category    text not null check (category in ('personal','absent','sick','late')),
  min_value   numeric not null check (min_value >= 0),
  max_value   numeric check (max_value is null or max_value >= min_value),  -- null = unbounded top bracket
  score       numeric not null check (score >= 0),
  sort_order  int not null,
  updated_at  timestamptz not null default now(),
  unique (company_id, category, sort_order)
);

create trigger trg_attendance_brackets_updated before update on company_attendance_brackets
  for each row execute function app.set_updated_at();

create index idx_attendance_brackets_company on company_attendance_brackets(company_id, category);

alter table company_attendance_brackets enable row level security;
alter table company_attendance_brackets force  row level security;

create policy attendance_brackets_select on company_attendance_brackets for select
  using (app.is_super_admin() or company_id = app.current_company_id());
create policy attendance_brackets_insert on company_attendance_brackets for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy attendance_brackets_update on company_attendance_brackets for update
  using      (app.is_super_admin() or company_id = app.current_company_id())
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy attendance_brackets_delete on company_attendance_brackets for delete
  using (app.is_super_admin() or company_id = app.current_company_id());

-- Non-negotiable #5 (CLAUDE.md): tables created after migration 0006 must
-- grant explicitly -- 0006's blanket grant doesn't retroactively cover
-- tables created afterward.
grant select, insert, update, delete on company_attendance_brackets to authenticated;
