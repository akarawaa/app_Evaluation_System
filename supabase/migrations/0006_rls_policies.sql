-- 0006_rls_policies.sql
-- Row-Level Security = the primary tenant-isolation guardrail (OWASP A01).
--
-- IMPORTANT: The FastAPI backend must connect with a role that does NOT have
-- BYPASSRLS (i.e. NOT the service_role) for tenant operations, and must set
-- request.jwt.claims per request. The service_role key bypasses RLS and is
-- reserved for controlled admin tasks (e.g. tenant provisioning).
--
-- `force row level security` makes even the table owner obey the policies.

-- ── companies ─────────────────────────────────────────────────────────────
alter table companies enable row level security;
alter table companies force  row level security;

create policy companies_select on companies for select
  using (app.is_super_admin() or id = app.current_company_id());
create policy companies_insert on companies for insert
  with check (app.is_super_admin());
create policy companies_update on companies for update
  using      (app.is_super_admin() or id = app.current_company_id())
  with check (app.is_super_admin() or id = app.current_company_id());
create policy companies_delete on companies for delete
  using (app.is_super_admin());

-- ── generic tenant tables (company_id column) ─────────────────────────────
-- branches
alter table branches enable row level security;
alter table branches force  row level security;
create policy branches_select on branches for select
  using (app.is_super_admin() or company_id = app.current_company_id());
create policy branches_insert on branches for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy branches_update on branches for update
  using      (app.is_super_admin() or company_id = app.current_company_id())
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy branches_delete on branches for delete
  using (app.is_super_admin() or company_id = app.current_company_id());

-- employees
alter table employees enable row level security;
alter table employees force  row level security;
create policy employees_select on employees for select
  using (app.is_super_admin() or company_id = app.current_company_id());
create policy employees_insert on employees for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy employees_update on employees for update
  using      (app.is_super_admin() or company_id = app.current_company_id())
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy employees_delete on employees for delete
  using (app.is_super_admin() or company_id = app.current_company_id());

-- profiles
alter table profiles enable row level security;
alter table profiles force  row level security;
create policy profiles_select on profiles for select
  using (app.is_super_admin() or company_id = app.current_company_id());
create policy profiles_insert on profiles for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy profiles_update on profiles for update
  using      (app.is_super_admin() or company_id = app.current_company_id())
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy profiles_delete on profiles for delete
  using (app.is_super_admin() or company_id = app.current_company_id());

-- user_roles
alter table user_roles enable row level security;
alter table user_roles force  row level security;
create policy user_roles_select on user_roles for select
  using (app.is_super_admin() or company_id = app.current_company_id());
create policy user_roles_insert on user_roles for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy user_roles_update on user_roles for update
  using      (app.is_super_admin() or company_id = app.current_company_id())
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy user_roles_delete on user_roles for delete
  using (app.is_super_admin() or company_id = app.current_company_id());

-- ── roles (global reference data) ─────────────────────────────────────────
alter table roles enable row level security;
alter table roles force  row level security;
create policy roles_select on roles for select using (true);
create policy roles_insert on roles for insert with check (app.is_super_admin());
create policy roles_update on roles for update using (app.is_super_admin()) with check (app.is_super_admin());
create policy roles_delete on roles for delete using (app.is_super_admin());

-- ── criteria tables (master rows: company_id IS NULL, readable by all) ────
-- Only super_admin can write master rows (company_id NULL fails the tenant check).
-- criteria_templates
alter table criteria_templates enable row level security;
alter table criteria_templates force  row level security;
create policy templates_select on criteria_templates for select
  using (app.is_super_admin() or company_id is null or company_id = app.current_company_id());
create policy templates_insert on criteria_templates for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy templates_update on criteria_templates for update
  using      (app.is_super_admin() or company_id = app.current_company_id())
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy templates_delete on criteria_templates for delete
  using (app.is_super_admin() or company_id = app.current_company_id());

-- criteria_categories
alter table criteria_categories enable row level security;
alter table criteria_categories force  row level security;
create policy categories_select on criteria_categories for select
  using (app.is_super_admin() or company_id is null or company_id = app.current_company_id());
create policy categories_insert on criteria_categories for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy categories_update on criteria_categories for update
  using      (app.is_super_admin() or company_id = app.current_company_id())
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy categories_delete on criteria_categories for delete
  using (app.is_super_admin() or company_id = app.current_company_id());

-- criteria_items
alter table criteria_items enable row level security;
alter table criteria_items force  row level security;
create policy items_select on criteria_items for select
  using (app.is_super_admin() or company_id is null or company_id = app.current_company_id());
create policy items_insert on criteria_items for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy items_update on criteria_items for update
  using      (app.is_super_admin() or company_id = app.current_company_id())
  with check (app.is_super_admin() or company_id = app.current_company_id());
create policy items_delete on criteria_items for delete
  using (app.is_super_admin() or company_id = app.current_company_id());

-- ── audit_logs (APPEND-ONLY: select + insert only, no update/delete) ──────
alter table audit_logs enable row level security;
alter table audit_logs force  row level security;
create policy audit_select on audit_logs for select
  using (app.is_super_admin() or company_id = app.current_company_id());
create policy audit_insert on audit_logs for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());
-- (intentionally NO update/delete policy => immutable)

-- ── grants (RLS still restricts rows; grants just allow the command) ──────
grant usage on schema app to authenticated, service_role;
grant execute on all functions in schema app to authenticated, service_role;
grant select, insert, update, delete on all tables in schema public to authenticated;
grant usage, select on all sequences in schema public to authenticated;
