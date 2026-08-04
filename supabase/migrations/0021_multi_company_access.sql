-- 0021_multi_company_access.sql
-- Lets one login (one auth.users row) hold roles in more than one company and
-- switch which one is "active". `profiles.company_id` becomes the currently
-- active company rather than a fixed home company; `user_roles` already has
-- its own `company_id` per row so a profile can already accumulate roles
-- across companies at the schema level -- what was missing was (a) the hook
-- correctly scoping the `roles` JWT claim to the active company, and (b) a
-- safe, server-validated way to list/switch which company is active.

-- Schema fix + prerequisite: user_roles' primary key was (profile_id,
-- role_id) -- it did not include company_id, so the same role code (e.g.
-- hr_admin) could never exist twice for one profile even across two
-- different companies. Found by the negative/positive test suite for this
-- migration, not by static review of the constraint list. Widen the key to
-- (profile_id, role_id, company_id) so a profile can hold the same role code
-- in more than one company.
alter table user_roles drop constraint user_roles_pkey;
alter table user_roles add primary key (profile_id, role_id, company_id);

-- Bug fix + prerequisite: the roles claim was NOT company-scoped -- it
-- aggregated role codes across every company a profile has a user_roles row
-- in, regardless of which company_id ended up in the same JWT. Harmless
-- while no profile had multi-company roles; a real leak the moment one does.
create or replace function app.custom_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  claims       jsonb;
  v_uid        uuid;
  v_company_id uuid;
  v_roles      jsonb;
  v_is_super   boolean;
begin
  v_uid  := (event ->> 'user_id')::uuid;
  claims := coalesce(event -> 'claims', '{}'::jsonb);

  select p.company_id
    into v_company_id
    from public.profiles p
   where p.id = v_uid;

  select coalesce(jsonb_agg(r.code order by r.code), '[]'::jsonb)
    into v_roles
    from public.user_roles ur
    join public.roles r on r.id = ur.role_id
   where ur.profile_id = v_uid
     and ur.company_id = v_company_id;

  v_is_super := coalesce(v_roles ? 'super_admin', false);

  claims := jsonb_set(
    claims, '{company_id}',
    case when v_company_id is null then 'null'::jsonb
         else to_jsonb(v_company_id::text) end
  );
  claims := jsonb_set(claims, '{is_super_admin}', to_jsonb(v_is_super));
  claims := jsonb_set(claims, '{roles}', v_roles);

  return jsonb_set(event, '{claims}', claims);
end;
$$;

-- List every company the calling profile holds a user_roles row in (not just
-- the currently-active one -- the RLS-scoped session can only ever see its
-- own active company's `companies` row, which is exactly why this needs to
-- be SECURITY DEFINER). Always derived from the caller's own verified JWT
-- `sub` claim, never a client-supplied id -- mirrors the hook's own trust
-- model (see 0007_auth_hook.sql).
create or replace function app.list_my_companies()
returns table (company_id uuid, company_name text, roles jsonb)
language sql
stable
security definer
set search_path = ''
as $$
  select c.id, c.name,
         coalesce(jsonb_agg(r.code order by r.code), '[]'::jsonb)
    from public.user_roles ur
    join public.companies c on c.id = ur.company_id
    join public.roles r on r.id = ur.role_id
   where ur.profile_id = nullif(app.jwt_claims() ->> 'sub', '')::uuid
   group by c.id, c.name
   order by c.name;
$$;

grant execute on function app.list_my_companies() to authenticated;
revoke execute on function app.list_my_companies() from anon, public;

-- Switch the calling profile's active company. Self-validating: only
-- succeeds if a user_roles row already ties this profile to the target
-- company (granted separately, super_admin only -- see
-- backend/app/services/tenant_admin.py grant_company_access). Returns false
-- rather than raising so the FastAPI route can turn it into a clean 403.
create or replace function app.switch_active_company(target_company_id uuid)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid;
  v_ok  boolean;
begin
  v_uid := nullif(app.jwt_claims() ->> 'sub', '')::uuid;

  select exists(
    select 1 from public.user_roles
     where profile_id = v_uid and company_id = target_company_id
  ) into v_ok;

  if not v_ok then
    return false;
  end if;

  update public.profiles set company_id = target_company_id where id = v_uid;
  return true;
end;
$$;

grant execute on function app.switch_active_company(uuid) to authenticated;
revoke execute on function app.switch_active_company(uuid) from anon, public;

-- Look up an existing profile by email so super_admin can grant it a second
-- company's role without re-inviting/re-creating the auth user. Reads
-- auth.users (locked down from normal roles) via SECURITY DEFINER, same
-- self-guard style as clone_master_templates -- avoids another GoTrue admin
-- API round trip, which has been this project's flakiest external call.
create or replace function app.find_profile_by_email(p_email text)
returns uuid
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_id uuid;
begin
  if not app.is_super_admin() then
    raise exception 'only super_admin may look up users by email';
  end if;

  select p.id into v_id
    from auth.users u
    join public.profiles p on p.id = u.id
   where lower(u.email) = lower(p_email)
   limit 1;

  return v_id;
end;
$$;

grant execute on function app.find_profile_by_email(text) to authenticated;
revoke execute on function app.find_profile_by_email(text) from anon, public;
