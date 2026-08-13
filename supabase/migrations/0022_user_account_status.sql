-- 0022_user_account_status.sql
-- Lets hr_admin (own company) / super_admin (any company, explicit company_id
-- -- see backend/app/api/routes.py's _resolve_company) deactivate a login
-- without touching the person's employee record or evaluation history.
-- "Deactivate" = ban the auth.users row via GoTrue admin API (see
-- services/auth_admin.set_user_ban) -- not deleting the profile/user_roles,
-- so past evaluations they scored/approved/were subject to stay intact.

-- auth.users is locked down from normal roles (same reason
-- find_profile_by_email needed SECURITY DEFINER in 0021) -- expose only
-- banned_until, scoped to one company at a time, self-guarded the same way.
create or replace function app.list_company_users(p_company_id uuid default null)
returns table (id uuid, display_name text, employee_id uuid, roles jsonb, active boolean)
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_cid uuid := coalesce(p_company_id, app.current_company_id());
begin
  if not (app.is_super_admin() or v_cid = app.current_company_id()) then
    raise exception 'not authorized for this company';
  end if;

  return query
    select p.id, p.display_name, p.employee_id,
           coalesce(jsonb_agg(r.code order by r.code) filter (where r.code is not null), '[]'::jsonb),
           (u.banned_until is null or u.banned_until < now())
      from public.profiles p
      join auth.users u on u.id = p.id
      left join public.user_roles ur on ur.profile_id = p.id and ur.company_id = v_cid
      left join public.roles r on r.id = ur.role_id
     where p.company_id = v_cid
     group by p.id, p.display_name, p.employee_id, u.banned_until
     order by p.display_name;
end;
$$;

grant execute on function app.list_company_users(uuid) to authenticated;
revoke execute on function app.list_company_users(uuid) from anon, public;
