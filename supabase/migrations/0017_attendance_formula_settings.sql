-- 0017_attendance_formula_settings.sql
-- Lets HR tune the attendance-score formula per tenant instead of it being
-- hardcoded (services.evaluations.compute_attendance_score used a fixed
-- 40/4/1/0.5/1). One row per company; absence of a row means "use the
-- built-in defaults" (see app/services/attendance_formula.py).

create table company_attendance_formula (
  company_id     uuid primary key references companies(id) on delete cascade,
  full_score     numeric not null default 40 check (full_score >= 0),
  coef_absent    numeric not null default 4  check (coef_absent >= 0),
  coef_personal  numeric not null default 1  check (coef_personal >= 0),
  coef_sick      numeric not null default 0.5 check (coef_sick >= 0),
  coef_late      numeric not null default 1  check (coef_late >= 0),
  updated_at     timestamptz not null default now()
);

create trigger trg_attendance_formula_updated before update on company_attendance_formula
  for each row execute function app.set_updated_at();

alter table company_attendance_formula enable row level security;
alter table company_attendance_formula force  row level security;

create policy attendance_formula_select on company_attendance_formula for select
  using (app.is_super_admin() or company_id = app.current_company_id());
create policy attendance_formula_insert on company_attendance_formula for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy attendance_formula_update on company_attendance_formula for update
  using      (app.is_super_admin() or company_id = app.current_company_id())
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy attendance_formula_delete on company_attendance_formula for delete
  using (app.is_super_admin() or company_id = app.current_company_id());

grant select, insert, update, delete on company_attendance_formula to authenticated;
