-- 0001_extensions.sql
-- Base extensions. Run first.

create extension if not exists pgcrypto;      -- gen_random_uuid()

-- Dedicated schema for our helper functions (keeps public clean)
create schema if not exists app;
