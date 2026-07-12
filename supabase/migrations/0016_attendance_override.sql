-- 0016_attendance_override.sql
-- Attendance becomes HR-owned factual data: HR enters the raw figures
-- (sick/personal leave, lateness, absence) and the system computes the score
-- from a configurable formula. HR may override the computed score; this flag
-- records that so re-editing the raw figures doesn't silently recompute over
-- a deliberate manual value.

alter table evaluation_attendance
  add column attendance_score_overridden boolean not null default false;
