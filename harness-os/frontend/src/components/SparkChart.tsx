import type { ReactNode } from 'react'
import { normalizePersonaLabel } from './utils'

type Props = {
  values: number[]
  colorClass: 'free' | 'paid' | 'cost'
  dates?: string[]
}

export function SparkChart({ values, colorClass, dates }: Props) {
  const max = Math.max(1, ...values)
  return (
    <div className={`spark-chart ${colorClass}`} role="img" aria-label="trend chart">
      {values.map((value, index) => {
        const heightPct = Math.max(8, Math.round((value / max) * 100))
        const label = dates?.[index] ? `${dates[index]}: ${value}` : String(value)
        return (
          <span
            key={`${colorClass}-${index}`}
            className="spark-bar"
            style={{ height: `${heightPct}%` }}
            title={label}
          >
            <span className="spark-tooltip">{label}</span>
          </span>
        )
      })}
    </div>
  )
}

export function renderPersonaLabel(value: string): ReactNode {
  const normalized = normalizePersonaLabel(value)
  const matched = normalized.match(/^(.+?)\s*\((.+)\)$/)
  if (!matched) return normalized
  const personaName = matched[1].trim()
  const team = matched[2].trim()
  return (
    <>
      <span className="persona-name" translate="no">{personaName}</span>
      ({team})
    </>
  )
}

export function renderTableCell(value: string): ReactNode {
  const trimmed = value.trim()
  if (!trimmed) return '—'
  return renderPersonaLabel(trimmed)
}

export function textFromNode(children: ReactNode): string | null {
  if (typeof children === 'string' || typeof children === 'number') return String(children)
  if (Array.isArray(children)) {
    let acc = ''
    for (const child of children) {
      if (typeof child === 'string' || typeof child === 'number') acc += String(child)
      else return null
    }
    return acc
  }
  return null
}
