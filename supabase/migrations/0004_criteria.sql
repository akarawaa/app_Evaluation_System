-- 0004_criteria.sql
-- BARS criteria, template-driven. company_id NULL = shared master template.
-- company_id is denormalized onto categories/items so RLS is uniform & fast.

create table criteria_templates (
  id               uuid primary key default gen_random_uuid(),
  company_id       uuid references companies(id) on delete cascade,   -- NULL = master
  name             text not null,
  version          int  not null default 1,
  applies_to_level text not null default 'all'
                     check (applies_to_level in ('operational','supervisor','all')),
  status           text not null default 'draft'
                     check (status in ('draft','active','archived')),
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now(),
  unique (company_id, name, version)
);
-- enforce uniqueness for master rows too (company_id NULLs are distinct in UNIQUE)
create unique index uq_master_template on criteria_templates(name, version) where company_id is null;

create table criteria_categories (
  id          uuid primary key default gen_random_uuid(),
  template_id uuid not null references criteria_templates(id) on delete cascade,
  company_id  uuid references companies(id) on delete cascade,   -- mirrors template.company_id
  sort_order  int  not null,
  name        text not null,
  unique (template_id, sort_order)
);

create table criteria_items (
  id          uuid primary key default gen_random_uuid(),
  category_id uuid not null references criteria_categories(id) on delete cascade,
  company_id  uuid references companies(id) on delete cascade,   -- mirrors template.company_id
  sort_order  int  not null,
  name        text not null,
  weight      numeric not null default 1,
  desc_1      text,   -- BARS behavioral anchors (1..5). NULL = to be filled by HR.
  desc_2      text,
  desc_3      text,
  desc_4      text,
  desc_5      text,
  unique (category_id, sort_order)
);

create index idx_templates_company  on criteria_templates(company_id);
create index idx_categories_template on criteria_categories(template_id);
create index idx_categories_company  on criteria_categories(company_id);
create index idx_items_category      on criteria_items(category_id);
create index idx_items_company       on criteria_items(company_id);

create trigger trg_templates_updated before update on criteria_templates
  for each row execute function app.set_updated_at();
