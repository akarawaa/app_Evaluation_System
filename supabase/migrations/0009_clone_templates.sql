-- 0009_clone_templates.sql
-- Clone every master criteria template (company_id IS NULL) into a target
-- tenant, remapping template/category/item ids and stamping company_id.
-- Used by tenant provisioning (Step 6).
--
-- SECURITY DEFINER so it can read master rows and insert under RLS, but it
-- self-guards: only a super_admin JWT may invoke it.

create or replace function app.clone_master_templates(p_company uuid)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  t        record;
  c        record;
  new_t    uuid;
  new_c    uuid;
  n_items  integer := 0;
begin
  if not app.is_super_admin() then
    raise exception 'only super_admin may clone master templates';
  end if;

  for t in
    select * from public.criteria_templates where company_id is null
  loop
    insert into public.criteria_templates (company_id, name, version, applies_to_level, status)
    values (p_company, t.name, t.version, t.applies_to_level, 'active')
    returning id into new_t;

    for c in
      select * from public.criteria_categories where template_id = t.id order by sort_order
    loop
      insert into public.criteria_categories (template_id, company_id, sort_order, name)
      values (new_t, p_company, c.sort_order, c.name)
      returning id into new_c;

      insert into public.criteria_items
        (category_id, company_id, sort_order, name, weight, desc_1, desc_2, desc_3, desc_4, desc_5)
      select new_c, p_company, i.sort_order, i.name, i.weight,
             i.desc_1, i.desc_2, i.desc_3, i.desc_4, i.desc_5
      from public.criteria_items i
      where i.category_id = c.id;

      get diagnostics n_items = row_count;
    end loop;
  end loop;

  return (select count(*)::int from public.criteria_templates where company_id = p_company);
end;
$$;

grant execute on function app.clone_master_templates(uuid) to authenticated;
revoke execute on function app.clone_master_templates(uuid) from anon, public;
