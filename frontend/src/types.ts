export type Me = {
  id: string
  email: string | null
  company_id: string | null
  is_super_admin: boolean
  roles: string[]
  employee_id: string | null
}

export type Employee = {
  id: string
  emp_code: string
  full_name: string
  position: string | null
  level: string
  status: string
  branch_id: string | null
  branch_name: string | null
  supervisor_id: string | null
  supervisor_name: string | null
  manager_id: string | null
  manager_name: string | null
}

export type Branch = { id: string; name: string }

export type ImportRowError = { row: number; emp_code: string | null; message: string }

export type ImportResult = {
  created: number
  updated: number
  linked: number
  branches_created: number
  errors: ImportRowError[]
}

export type Tenant = {
  id: string
  name: string
  slug: string
  status: string
  created_at: string
  employee_count: number
  user_count: number
}

export type TenantUser = {
  id: string
  display_name: string | null
  employee_id: string | null
  roles: string[]
}

export type TenantDetail = Tenant & { users: TenantUser[] }

export const ROLE_LABEL: Record<string, string> = {
  super_admin: 'ผู้ดูแลระบบ (Platform)',
  hr_admin: 'ฝ่ายบุคคล',
  manager: 'หัวหน้างาน',
  dept_manager: 'ผจก.แผนก',
  md: 'กรรมการผู้จัดการ (MD)',
  gm: 'ผู้จัดการทั่วไป (GM)',
  employee: 'พนักงาน',
}

// GM and MD are interchangeable at the top approval stage.
export const INVITE_ROLES = ['hr_admin', 'manager', 'dept_manager', 'md', 'gm', 'employee']

export const LEVEL_LABEL: Record<string, string> = {
  operational: 'พนักงานปฏิบัติการ',
  supervisor: 'หัวหน้างาน',
}

export type Template = {
  id: string
  name: string
  applies_to_level: string
  status: string
}

export type EvalListItem = {
  id: string
  employee_id: string
  status: string
  kind: string
  eval_score: number | null
  eval_max: number | null
  total_score: number | null
  percentage: number | null
}

export type EvalItem = {
  id: string
  category_order: number
  category_name: string
  item_order: number
  item_name: string
  weight: number
  score: number | null
  desc_1: string | null
  desc_2: string | null
  desc_3: string | null
  desc_4: string | null
  desc_5: string | null
}

export type EvalComment = { category_order: number; comment: string | null }

export type EvalApproval = {
  step: string
  decision: string
  comment: string | null
  decided_at: string
}

export type AttendanceDetail = {
  sick_days: number
  personal_days: number
  late_count: number
  late_minutes: number
  absent_days: number
  attendance_score: number | null
  attendance_score_overridden: boolean
}

export type EvalDetail = {
  id: string
  employee_id: string
  evaluator_id: string | null
  emp_supervisor_id: string | null
  emp_manager_id: string | null
  kind: string
  status: string
  eval_score: number | null
  eval_max: number | null
  attendance_score: number | null
  total_score: number | null
  percentage: number | null
  items: EvalItem[]
  comments: EvalComment[]
  attendance: AttendanceDetail | null
  approvals: EvalApproval[]
}

export type AttendanceImportRowError = { row: number; emp_code: string | null; message: string }

export type AttendanceImportResult = {
  updated: number
  skipped_overridden: number
  errors: AttendanceImportRowError[]
}

export type InboxAction = 'score' | 'dept_approve' | 'md_approve' | 'finalize'

export type InboxItem = {
  id: string
  employee_id: string
  emp_code: string
  full_name: string
  kind: string
  status: string
  percentage: number | null
  action: InboxAction
}

export const ACTION_LABEL: Record<InboxAction, string> = {
  score: 'รอให้คะแนน',
  dept_approve: 'รออนุมัติ (ผจก.แผนก)',
  md_approve: 'รออนุมัติ (GM/MD)',
  finalize: 'รอสรุป/ปิดใบ (HR)',
}

export const STATUS_LABEL: Record<string, string> = {
  draft: 'ร่าง',
  submitted: 'ส่งแล้ว (รอ ผจก.แผนก)',
  dept_approved: 'ผจก.แผนกอนุมัติ (รอ MD)',
  md_approved: 'MD อนุมัติ (รอ HR)',
  finalized: 'ปิดใบแล้ว',
  returned: 'ตีกลับให้แก้',
}
