-- 0003_tenant_identity.sql
-- Tenant & identity core. Every tenant-scoped table carries company_id.

-- ── companies (tenant root; id itself IS the tenant boundary) ──────────────
create table companies (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  slug       text not null unique,
  status     text not null default 'active' check (status in ('active','suspended')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ── branches ──────────────────────────────────────────────────────────────
create table branches (
  id         uuid primary key default gen_random_uuid(),
  company_id uuid not null references companies(id) on delete cascade,
  name       text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (company_id, name)
);

-- ── roles (global catalog; assignment is tenant-scoped via user_roles) ─────
create table roles (
  id          uuid primary key default gen_random_uuid(),
  code        text not null unique,          -- super_admin | hr_admin | manager | employee | ...
  description text
);

-- ── employees ─────────────────────────────────────────────────────────────
create table employees (
  id            uuid primary key default gen_random_uuid(),
  company_id    uuid not null references companies(id) on delete cascade,
  branch_id     uuid references branches(id) on delete set null,
  emp_code      text not null,
  full_name     text not null,
  position      text,
  level         text not null default 'operational' check (level in ('operational','supervisor')),
  supervisor_id uuid references employees(id) on delete set null,
  manager_id    uuid references employees(id) on delete set null,
  status        text not null default 'active' check (status in ('active','inactive')),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (company_id, emp_code),
  constraint employees_no_self_supervisor check (supervisor_id is null or supervisor_id <> id),
  constraint employees_no_self_manager    check (manager_id    is null or manager_id    <> id)
);

-- ── profiles (bridge to Supabase auth.users) ──────────────────────────────
create table profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  company_id   uuid not null references companies(id) on delete cascade,
  employee_id  uuid references employees(id) on delete set null,
  display_name text,
  is_active    boolean not null default true,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

-- ── user_roles (M:N; company_id denormalized for fast RLS) ─────────────────
create table user_roles (
  profile_id uuid not null references profiles(id) on delete cascade,
  role_id    uuid not null references roles(id)    on delete cascade,
  company_id uuid not null references companies(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (profile_id, role_id)
);

-- ── indexes (composite indexes lead with company_id) ──────────────────────
create index idx_branches_company             on branches(company_id);
create index idx_employees_company_status     on employees(company_id, status);
create index idx_employees_company_branch     on employees(company_id, branch_id);
create index idx_employees_company_supervisor on employees(company_id, supervisor_id);
create index idx_employees_company_manager    on employees(company_id, manager_id);
create index idx_profiles_company             on profiles(company_id);
create index idx_profiles_employee            on profiles(employee_id);
create index idx_user_roles_company_profile   on user_roles(company_id, profile_id);
create index idx_user_roles_role              on user_roles(role_id);

-- ── updated_at triggers ───────────────────────────────────────────────────
create trigger trg_companies_updated  before update on companies  for each row execute function app.set_updated_at();
create trigger trg_branches_updated   before update on branches   for each row execute function app.set_updated_at();
create trigger trg_employees_updated  before update on employees  for each row execute function app.set_updated_at();
create trigger trg_profiles_updated   before update on profiles   for each row execute function app.set_updated_at();
