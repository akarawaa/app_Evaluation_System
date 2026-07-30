-- 0020_acknowledgement_in_workflow.sql
-- Moves employee acknowledgement INTO the approval chain instead of after it.
--
-- Old flow:  supervisor -> dept manager -> GM/MD -> HR finalize -> (later) employee acknowledges
-- New flow:  supervisor -> dept manager -> EMPLOYEE SIGNS -> GM/MD -> HR finalize
--
-- This is closer to the paper form than what we had: on FMHR07 the MD signs
-- last, after everyone including the employee. GM/MD can now see that the
-- employee was already shown the result before giving final approval.
--
-- Consequence: an acknowledgement can now be invalidated. If GM/MD (or HR)
-- returns the evaluation for rescoring, the scores the employee signed for no
-- longer exist, so that signature must stop counting -- but it must not be
-- deleted either, since it is evidence of what happened at the time. Hence
-- superseded_at: the row stays, stops being the active acknowledgement, and a
-- fresh signature can be collected after the rescore.

alter table evaluation_acknowledgements
  add column superseded_at timestamptz;

-- One *active* acknowledgement per evaluation; superseded ones accumulate as
-- history. Replaces the old unconditional unique(evaluation_id).
alter table evaluation_acknowledgements
  drop constraint evaluation_acknowledgements_evaluation_id_key;

create unique index idx_eval_ack_one_active
  on evaluation_acknowledgements (evaluation_id)
  where superseded_at is null;

-- The table is append-only by design (0018 grants select+insert only, no
-- update policy), which is what we want for evidence. Superseding is the one
-- controlled exception, so it goes through a SECURITY DEFINER function rather
-- than by opening the table up to arbitrary UPDATEs.
--
-- p_company is supplied by the caller from an evaluation row it already read
-- through its own RLS-scoped session, so it cannot be used to reach into
-- another tenant; the function still filters on it explicitly as a belt-and-
-- braces check since SECURITY DEFINER bypasses RLS.
create or replace function app.supersede_acknowledgement(p_eval uuid, p_company uuid)
returns integer
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare n integer;
begin
  update public.evaluation_acknowledgements
     set superseded_at = now()
   where evaluation_id = p_eval
     and company_id    = p_company
     and superseded_at is null;
  get diagnostics n = row_count;
  return n;
end;
$$;

grant execute on function app.supersede_acknowledgement(uuid, uuid) to authenticated;
