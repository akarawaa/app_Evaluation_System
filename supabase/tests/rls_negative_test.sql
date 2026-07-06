-- RLS negative test (Phase 1, Step 8).
-- Proves tenant isolation: a Company A user cannot see or modify Company B data,
-- master criteria templates are shared, and audit_logs is append-only.
--
-- Run against the local stack:
--   cat supabase/tests/rls_negative_test.sql | \
--     docker exec -i supabase_db_<project> psql -U postgres -d postgres -v ON_ERROR_STOP=1
--
-- Each "act as user" block is ONE transaction so the transaction-local JWT claim
-- (set_config ..., true) stays in effect across the queries.
\set ON_ERROR_STOP on

-- ── cleanup + setup (as postgres superuser => bypasses RLS) ───────────────
delete from audit_logs where action = 'test_event';
delete from companies where slug in ('company-a','company-b');

insert into companies (id, name, slug) values
  ('11111111-1111-1111-1111-111111111111','Company A','company-a'),
  ('22222222-2222-2222-2222-222222222222','Company B','company-b');
insert into branches (company_id, name) values
  ('11111111-1111-1111-1111-111111111111','A-HQ'),
  ('22222222-2222-2222-2222-222222222222','B-HQ');
insert into employees (company_id, emp_code, full_name) values
  ('11111111-1111-1111-1111-111111111111','A001','Alice A'),
  ('22222222-2222-2222-2222-222222222222','B001','Bob B');

-- ══ act as Company A user (single transaction) ════════════════════════════
begin;
set local role authenticated;
select set_config('request.jwt.claims',
  '{"company_id":"11111111-1111-1111-1111-111111111111","is_super_admin":false,"roles":["hr_admin"]}', true);

select '1. employees visible (expect 1)'        as check, count(*) as n from employees;
select '2. branches visible (expect 1)'         as check, count(*) as n from branches;
select '3. company B rows leaked? (expect 0)'   as check, count(*) as n
       from employees where company_id='22222222-2222-2222-2222-222222222222';
select '4. master templates visible (expect 2)' as check, count(*) as n
       from criteria_templates where company_id is null;

-- 5. cross-tenant INSERT must be blocked by RLS WITH CHECK
do $$
begin
  insert into employees (company_id, emp_code, full_name)
  values ('22222222-2222-2222-2222-222222222222','HACK','Cross Tenant');
  raise notice '5. FAIL: cross-tenant insert SUCCEEDED (RLS broken)';
exception when others then
  raise notice '5. PASS: cross-tenant insert blocked -> %', sqlerrm;
end $$;

-- 6. audit_logs append-only: own insert allowed, delete must remove 0 rows
insert into audit_logs (company_id, action) values
  ('11111111-1111-1111-1111-111111111111','test_event');
do $$
declare deleted int;
begin
  delete from audit_logs where action = 'test_event';
  get diagnostics deleted = row_count;
  if deleted = 0 then
    raise notice '6. PASS: audit delete removed 0 rows (append-only enforced)';
  else
    raise notice '6. FAIL: audit delete removed % row(s)', deleted;
  end if;
exception when others then
  raise notice '6. PASS: audit delete denied -> %', sqlerrm;
end $$;
commit;

-- ══ act as Company B user ═════════════════════════════════════════════════
begin;
set local role authenticated;
select set_config('request.jwt.claims',
  '{"company_id":"22222222-2222-2222-2222-222222222222","is_super_admin":false,"roles":["hr_admin"]}', true);
select '7. company B sees own employees (expect 1 / Bob B)' as check,
       count(*) as n, min(full_name) as who from employees;
commit;

-- ── teardown ──────────────────────────────────────────────────────────────
delete from audit_logs where action = 'test_event';
delete from companies where slug in ('company-a','company-b');
