import type { HTMLAttributes } from 'react'

import { cx } from './cx'

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx('rounded-card border border-line bg-surface p-5 shadow-card', className)}
      {...rest}
    />
  )
}
