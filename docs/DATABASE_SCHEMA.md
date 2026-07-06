# Database Schema — E-Appraisal (Phase 1)

> อ้างอิงการออกแบบตาราง ก่อนเขียน SQL migration จริง
> **กติกา:** ทุกตาราง tenant-scoped ต้องมี `company_id uuid NOT NULL` + เปิด RLS

## แผนผังความสัมพันธ์ (ER — ระดับ concept)

```
companies (tenant)
   │ 1
   ├──< branches
   ├──< employees ──┐ (supervisor_id / manager_id self-ref)
   │                │
   ├──< profiles >──┘  (profiles.id = auth.users.id)
   │       │ M:N
   │       └──< user_roles >── roles
   │
   ├──< criteria_templates
   │        │ 1
   │        └──< criteria_categories
   │                 │ 1
   │                 └──< criteria_items (desc_1..desc_5)
   │
   └──< audit_logs (append-only)
```

## ตารางกลุ่ม Tenant & Identity

### companies  *(tenant root — ไม่มี company_id ในตัวเอง)*
| column | type | note |
|---|---|---|
| id | uuid PK | `gen_random_uuid()` |
| name | text NOT NULL | |
| slug | text UNIQUE NOT NULL | ใช้ระบุ tenant |
| status | text NOT NULL | active / suspended |
| created_at / updated_at | timestamptz | |

### branches
| id | uuid PK |
| company_id | uuid FK→companies **NOT NULL** |
| name | text NOT NULL |
| UNIQUE (company_id, name) |

### profiles  *(bridge กับ Supabase auth.users)*
| id | uuid PK, **= auth.users.id** (FK) |
| company_id | uuid FK→companies NOT NULL |
| employee_id | uuid FK→employees (nullable) |
| display_name | text |
| is_active | boolean default true |

### employees
| id | uuid PK |
| company_id | uuid FK→companies NOT NULL |
| branch_id | uuid FK→branches |
| emp_code | text | UNIQUE (company_id, emp_code) |
| full_name | text NOT NULL |
| position | text |
| level | text | `operational` (ข้อ1-11) / `supervisor` (ข้อ1-16) |
| supervisor_id | uuid FK→employees (self, nullable) |
| manager_id | uuid FK→employees (self, nullable) |
| status | text | active / inactive |
| **CHECK:** supervisor_id ≠ id, manager_id ≠ id (กัน self-loop ชั้นแรก) |

### roles
| id | uuid PK | code | text UNIQUE | `super_admin`/`hr_admin`/`manager`/`employee` |
| description | text |

### user_roles  *(M:N)*
| profile_id | uuid FK→profiles |
| role_id | uuid FK→roles |
| company_id | uuid | (denormalize เพื่อ RLS) |
| PK (profile_id, role_id) |

## ตารางกลุ่ม Criteria (BARS, template-driven)

### criteria_templates
| id | uuid PK |
| company_id | uuid FK→companies **NULLABLE** | NULL = master default (ใช้ร่วม/clone) |
| name | text NOT NULL |
| version | int NOT NULL default 1 |
| applies_to_level | text | operational / supervisor / all |
| status | text | draft / active / archived |
| UNIQUE (company_id, name, version) |

### criteria_categories
| id | uuid PK |
| template_id | uuid FK→criteria_templates NOT NULL |
| sort_order | int NOT NULL | (หมวด 1..16) |
| name | text NOT NULL |

### criteria_items
| id | uuid PK |
| category_id | uuid FK→criteria_categories NOT NULL |
| sort_order | int NOT NULL |
| name | text NOT NULL |
| weight | numeric default 1 |
| desc_1..desc_5 | text | **BARS behavioral anchors** ต่อระดับคะแนน |

## ตารางกลุ่ม Governance

### audit_logs  *(append-only — ดู LOGGING_AND_AUDIT.md)*
| id | bigint identity PK |
| company_id | uuid | (nullable สำหรับ platform-level events) |
| actor_profile_id | uuid | ใครทำ |
| action | text | login / create / update / delete / view_sensitive |
| entity_type | text | employees / criteria_items / ... |
| entity_id | text |
| before | jsonb | ค่าก่อนแก้ (ไม่เก็บ field ลับ) |
| after | jsonb | ค่าหลังแก้ |
| ip / user_agent | text |
| created_at | timestamptz default now() |
| **RLS:** SELECT ตาม company_id; **ไม่มี** UPDATE/DELETE policy (immutable) |

## Indexing plan (สำคัญต่อ performance & isolation)
- ทุก FK → สร้าง index
- **Composite index นำด้วย `company_id`** บนตารางที่ query บ่อย เช่น
  `employees (company_id, status)`, `employees (company_id, branch_id)`,
  `audit_logs (company_id, created_at desc)`, `user_roles (company_id, profile_id)`
- `employees (company_id, supervisor_id)` — สำหรับ query "ลูกน้องของฉัน"

## หมายเหตุ integrity
- Score จะถูกบังคับช่วง 1–5 (step 0.5) ตอนสร้างตาราง evaluations ใน **Phase 2** (ยังไม่อยู่ Phase 1)
- ป้องกัน supervisor/manager ข้าม tenant: ตรวจใน service layer + (option) trigger เช็ค company_id ตรงกัน
