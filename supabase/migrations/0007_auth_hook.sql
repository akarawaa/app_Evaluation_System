-- 0007_auth_hook.sql
-- Custom Access Token Hook (Step 3): inject tenant context into every JWT.
-- Adds claims: company_id (uuid text | null), is_super_admin (bool), roles (text[] as jsonb array).
-- These are exactly the claims the RLS helpers in 0002 read.
--
-- SECURITY DEFINER (owned by postgres, which has BYPASSRLS) so it can read the
-- profile/role tables regardless of RLS. search_path is locked and every object
-- is schema-qualified to prevent search_path hijacking.

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
   where ur.profile_id = v_uid;

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

-- Only GoTrue (supabase_auth_admin) may invoke the hook.
grant usage   on schema app to supabase_auth_admin;
grant execute on function app.custom_access_token_hook(jsonb) to supabase_auth_admin;
revoke execute on function app.custom_access_token_hook(jsonb) from authenticated, anon, public;
