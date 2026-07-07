-- 0008_platform_tenant.sql
-- Reserved "platform" tenant. Platform-level super_admins live here so that
-- profiles.company_id can stay NOT NULL while super_admins are not tied to a
-- real customer tenant. Cross-tenant access is granted by is_super_admin(),
-- never by this company_id.

insert into companies (id, name, slug, status)
values ('00000000-0000-0000-0000-000000000001', 'Platform', '__platform__', 'active')
on conflict (id) do nothing;
