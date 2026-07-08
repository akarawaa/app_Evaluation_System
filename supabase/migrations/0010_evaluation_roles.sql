-- 0010_evaluation_roles.sql
-- Additional roles for the approval chain (Phase 2).

insert into roles (code, description) values
  ('dept_manager', 'Department manager — approves after the supervisor'),
  ('md',           'Managing director — final approver before HR summary')
on conflict (code) do nothing;
