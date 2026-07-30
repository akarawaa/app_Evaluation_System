-- 0019_acknowledgement_storage.sql
-- Private bucket for scanned paper acknowledgements (employee's wet
-- signature). Objects are stored at "{company_id}/{evaluation_id}.{ext}" so
-- the same folder-per-tenant convention used elsewhere maps directly onto
-- storage.objects RLS via (storage.foldername(name))[1].
--
-- Append-only like the acknowledgement row itself: select + insert only, no
-- update/delete policy. A scan is evidence -- once attached it should never
-- be silently replaced or removed through the API (re-scanning the same
-- paper for a correction is a new evaluation_acknowledgements row's problem,
-- not this one's, and the unique(evaluation_id) constraint on that table
-- already prevents a second acknowledgement for the same evaluation anyway).

insert into storage.buckets (id, name, public)
values ('acknowledgement-scans', 'acknowledgement-scans', false)
on conflict (id) do nothing;

create policy ack_scans_select on storage.objects for select
  using (
    bucket_id = 'acknowledgement-scans'
    and (app.is_super_admin() or (storage.foldername(name))[1] = app.current_company_id()::text)
  );

create policy ack_scans_insert on storage.objects for insert
  with check (
    bucket_id = 'acknowledgement-scans'
    and (app.is_super_admin() or (storage.foldername(name))[1] = app.current_company_id()::text)
  );
