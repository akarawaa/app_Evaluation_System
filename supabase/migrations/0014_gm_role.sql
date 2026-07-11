-- 0014_gm_role.sql
-- General Manager role. Interchangeable with MD at the MD approval stage
-- (GM/MD) — every "md" authorization check also accepts "gm". The approval
-- record still uses step='md' (the stage), while actor_id records who acted,
-- so no change to evaluation_approvals is needed.

insert into roles (code, description) values
  ('gm', 'General Manager — same approval rights as MD (acts at the MD/GM stage)')
on conflict (code) do nothing;
