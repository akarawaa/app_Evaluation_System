-- 0015_bars_snapshot.sql
-- Carry the BARS behavioral anchors (desc_1..5) into the evaluation snapshot
-- so raters see, per item, what each score level means while scoring. Older
-- evaluations simply keep NULLs. The anchor *content* is filled on the master
-- template by supabase/seed.sql (runs after migrations); this migration only
-- adds the columns and teaches the snapshot function to copy them.

alter table evaluation_items
  add column desc_1 text,
  add column desc_2 text,
  add column desc_3 text,
  add column desc_4 text,
  add column desc_5 text;

create or replace function app.snapshot_evaluation_items(p_eval uuid)
returns integer
language plpgsql
as $$
declare n integer;
begin
  insert into public.evaluation_items
    (evaluation_id, company_id, category_order, category_name, item_order, item_name, weight,
     source_item_id, desc_1, desc_2, desc_3, desc_4, desc_5)
  select e.id, e.company_id, cc.sort_order, cc.name, ci.sort_order, ci.name, ci.weight,
         ci.id, ci.desc_1, ci.desc_2, ci.desc_3, ci.desc_4, ci.desc_5
  from public.evaluations e
  join public.criteria_templates  t  on t.id  = e.template_id
  join public.criteria_categories cc on cc.template_id = t.id
  join public.criteria_items      ci on ci.category_id = cc.id
  where e.id = p_eval;

  get diagnostics n = row_count;
  update public.evaluations set snapshot_at = now() where id = p_eval;
  return n;
end;
$$;
