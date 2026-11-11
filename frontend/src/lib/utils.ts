import { type ClassValue, clsx } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

/** Format an integer paise value as an INR string. */
export function formatINR(paise: number | null | undefined): string {
  if (paise == null) return '—'
  const inr = paise / 100
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(inr)
}

/** Format a fraction (0-1) as a percentage string. */
export function formatPct(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${(value * 100).toFixed(0)}%`
}

/** Format a date YYYY-MM-DD into a short Indian-friendly string. */
export function formatDate(value: string | Date | null | undefined): string {
  if (!value) return '—'
  const d = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** Round to N decimals, returning null for non-numbers. */
export function round(value: number | null | undefined, decimals = 2): number | null {
  if (value == null) return null
  return Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals)
}
