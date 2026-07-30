-- 0018_employee_acknowledgement.sql
-- Closes the biggest gap versus the paper form (FMHR07): the paper has FIVE
-- signature blocks and the employee's is the FIRST one, but the digital
-- workflow only implemented the four *approver* signatures (supervisor ->
-- dept manager -> MD -> HR). There was no record at all that the employee was
-- ever shown their own result, which is a regression from paper.
--
-- Two things here:
--   1) employees.email  — needed to notify the employee at all. Emails only
--      existed on auth.users (i.e. only for people who have a login), and the
--      plan is to reach employees who deliberately do NOT have one.
--   2) evaluation_acknowledgements — the acknowledgement record itself.
--
-- Design notes
-- ------------
-- * "Acknowledged" is NOT "agreed". Thai labour practice (and the paper form)
--   treats the employee signature as proof of *being informed*, and the form
--   has a separate comment box for the employee to dissent. Hence
--   decision='acknowledged_disagreed' is a first-class outcome, not an error,
--   and a refusal to sign is recordable rather than a dead end.
-- * employee_id = whose acknowledgement this is. actor_id = who pressed the
--   button in the system. They differ for paper: HR records it on the
--   employee's behalf after collecting a wet signature.
-- * signed_at is when the employee actually acknowledged/signed, which for
--   paper is usually earlier than when HR got round to keying it in
--   (created_at). Keep both; the legally interesting one is signed_at.
-- * content_hash pins what the employee was shown. evaluation_items is already
--   a snapshot, so scores can't drift, but a hash lets you *prove* that rather
--   than just assert it.
-- * Append-only (select + insert, no update/delete policy) like
--   evaluation_approvals and audit_logs -- an acknowledgement is evidence.

alter table employees add column email text;

-- Guard against the same address being attached to two people in one tenant
-- (would make "who acknowledged?" ambiguous once magic links are sent).
-- Partial index so the many employees without an email are unaffected.
create unique index idx_employees_company_email
  on employees (company_id, lower(email))
  where email is not null;

create table evaluation_acknowledgements (
  id              uuid primary key default gen_random_uuid(),
  company_id      uuid not null references companies(id) on delete cascade,
  evaluation_id   uuid not null references evaluations(id) on delete cascade,
  employee_id     uuid not null references employees(id) on delete restrict,

  method          text not null check (method in ('electronic','paper')),
  decision        text not null check (decision in ('acknowledged','acknowledged_disagreed','refused')),
  comment         text,                                  -- employee's own words (esp. when disagreeing)

  actor_id        uuid references profiles(id) on delete set null,
  signed_at       timestamptz not null default now(),

  -- evidentiary detail, electronic only
  content_hash    text,
  ip              text,
  user_agent      text,

  -- paper only
  witness_name    text,
  attachment_path text,

  created_at      timestamptz not null default now(),

  -- one acknowledgement per evaluation: also makes a double-submit race
  -- (employee clicks the emailed link while HR keys in the paper copy)
  -- fail loudly on the second write instead of silently duplicating.
  unique (evaluation_id),

  -- an employee cannot "refuse to sign" through the electronic flow: clicking
  -- the link IS the acknowledgement. Refusal is something HR witnesses offline.
  constraint ack_refused_is_paper
    check (decision <> 'refused' or method = 'paper')
);

create index idx_eval_ack_company on evaluation_acknowledgements(company_id, created_at desc);
create index idx_eval_ack_employee on evaluation_acknowledgements(employee_id);

alter table evaluation_acknowledgements enable row level security;
alter table evaluation_acknowledgements force  row level security;

create policy eval_ack_sel on evaluation_acknowledgements for select
  using (app.is_super_admin() or company_id = app.current_company_id());
create policy eval_ack_ins on evaluation_acknowledgements for insert
  with check (app.is_super_admin() or company_id = app.current_company_id());

-- NOTE: migration 0006 granted table privileges for tables that existed at the
-- time; tables added later must grant for themselves (same as 0011/0012/0017).
grant select, insert on evaluation_acknowledgements to authenticated;
