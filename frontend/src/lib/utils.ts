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

/** Format an integer or decimal rupee (INR) value directly as an INR string. */
export function formatRupees(inr: number | null | undefined): string {
  if (inr == null) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(inr)
}

/** Format a fraction (0-1) as a whole-number percentage string. */
export function formatPct(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${(value * 100).toFixed(0)}%`
}

/** Format a fraction (0-1) as a readable percentage string with precision (e.g. 14.1%). */
export function formatPctPrecise(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—'
  return `${(value * 100).toFixed(decimals)}%`
}

/** Format a raw integer or decimal count using Indian grouping (e.g. 1,240). */
export function formatNumber(value: number | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('en-IN').format(value)
}

/** Format a percentage delta number (e.g. -32.5 -> "-32.5%", +14.2 -> "+14.2%"). */
export function formatDeltaPct(value: number | null | undefined): string {
  if (value == null) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
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
