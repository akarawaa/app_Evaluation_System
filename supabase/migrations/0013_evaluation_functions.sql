-- 0013_evaluation_functions.sql
-- Snapshot criteria into an evaluation, and recompute totals (equal-weight).
-- SECURITY INVOKER (default): run under the caller's RLS context — the caller
-- may read its own tenant's / master criteria and write its own evaluation rows.

create or replace function app.snapshot_evaluation_items(p_eval uuid)
returns integer
language plpgsql
as $$
declare n integer;
begin
  insert into public.evaluation_items
    (evaluation_id, company_id, category_order, category_name, item_order, item_name, weight, source_item_id)
  select e.id, e.company_id, cc.sort_order, cc.name, ci.sort_order, ci.name, ci.weight, ci.id
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

-- equal-weight scoring: eval_max = Σ(weight)*5 (weight defaults to 1 => count*5);
-- percentage over (eval_max + 40 attendance points), matching FMHR07 (180/250).
create or replace function app.recompute_evaluation_totals(p_eval uuid)
returns void
language plpgsql
as $$
declare
  v_sum numeric;
  v_max numeric;
  v_att numeric;
begin
  select coalesce(sum(s.score), 0), coalesce(sum(i.weight) * 5, 0)
    into v_sum, v_max
  from public.evaluation_items i
  left join public.evaluation_scores s on s.evaluation_item_id = i.id
  where i.evaluation_id = p_eval;

  select attendance_score into v_att
  from public.evaluation_attendance where evaluation_id = p_eval;
  v_att := coalesce(v_att, 0);

  update public.evaluations
     set eval_score       = v_sum,
         eval_max         = v_max,
         attendance_score = v_att,
         total_score      = v_sum + v_att,
         percentage       = case when (v_max + 40) > 0
                                 then round((v_sum + v_att) / (v_max + 40) * 100, 2)
                                 else null end
   where id = p_eval;
end;
$$;

grant execute on function app.snapshot_evaluation_items(uuid)    to authenticated;
grant execute on function app.recompute_evaluation_totals(uuid)  to authenticated;
