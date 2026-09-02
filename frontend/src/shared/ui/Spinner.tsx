export function Spinner({ label = 'กำลังโหลด…' }: { label?: string }) {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-sm text-muted">{label}</div>
  )
}
