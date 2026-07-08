export type Me = {
  id: string
  email: string | null
  company_id: string | null
  is_super_admin: boolean
  roles: string[]
}

export type Employee = {
  id: string
  emp_code: string
  full_name: string
  level: string
  status: string
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
}

export type EvalComment = { category_order: number; comment: string | null }

export type EvalApproval = {
  step: string
  decision: string
  comment: string | null
  decided_at: string
}

export type EvalDetail = {
  id: string
  employee_id: string
  evaluator_id: string | null
  kind: string
  status: string
  eval_score: number | null
  eval_max: number | null
  attendance_score: number | null
  total_score: number | null
  percentage: number | null
  items: EvalItem[]
  comments: EvalComment[]
  attendance: { attendance_score: number | null } | null
  approvals: EvalApproval[]
}

export const STATUS_LABEL: Record<string, string> = {
  draft: 'ร่าง',
  submitted: 'ส่งแล้ว (รอ ผจก.แผนก)',
  dept_approved: 'ผจก.แผนกอนุมัติ (รอ MD)',
  md_approved: 'MD อนุมัติ (รอ HR)',
  finalized: 'ปิดใบแล้ว',
  returned: 'ตีกลับให้แก้',
}
