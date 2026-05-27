import { SparkChart } from './SparkChart'
import { formatPercent } from './utils'

type KpiCardProps = {
  title: string
  value: string | number
  subtitle?: string
  progress?: number
  progressLabel?: string
  trend?: number[]
  trendColorClass?: 'free' | 'paid' | 'cost'
  trendDates?: string[]
  statusVariant?: 'ok' | 'warn' | 'danger' | 'neutral'
  badge?: string
  className?: string
  onClick?: () => void
  actionLabel?: string
}

export function KpiCard({
  title, value, subtitle, progress, progressLabel,
  trend, trendColorClass, trendDates, statusVariant = 'neutral', badge, className, onClick, actionLabel
}: KpiCardProps) {
  const classes = ['kpi-card', `kpi-${statusVariant}`, className].filter(Boolean).join(' ')
  const isActionable = typeof onClick === 'function'
  return (
    <article
      className={isActionable ? `${classes} kpi-card-actionable` : classes}
      onClick={onClick}
      role={isActionable ? 'button' : undefined}
      tabIndex={isActionable ? 0 : undefined}
      onKeyDown={isActionable ? (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      } : undefined}
    >
      <div className="kpi-header">
        <h2 className="kpi-title">{title}</h2>
        {badge && <span className="kpi-badge">{badge}</span>}
      </div>
      <strong className="kpi-value">{value}</strong>
      {progress !== undefined && (
        <div className="kpi-meter" role="progressbar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={100}>
          <div className="kpi-meter-fill" style={{ width: formatPercent(Math.min(1, progress)) }} />
        </div>
      )}
      {progressLabel && <p className="kpi-meta">{progressLabel}</p>}
      {subtitle && <p className="kpi-meta">{subtitle}</p>}
      {trend && trend.length > 0 && trendColorClass && (
        <div className="kpi-trend">
          <SparkChart values={trend} colorClass={trendColorClass} dates={trendDates} height={92} />
        </div>
      )}
      {isActionable && actionLabel && <p className="kpi-action-label">{actionLabel}</p>}
    </article>
  )
}

type RiskBannerProps = {
  title: string
  message: string
  level: 'warn' | 'danger' | 'info'
}

export function RiskBanner({ title, message, level }: RiskBannerProps) {
  const icon = level === 'danger' ? '⚠' : level === 'warn' ? '△' : 'ℹ'
  return (
    <div className={`risk-banner risk-${level}`} role="alert">
      <span className="risk-icon">{icon}</span>
      <div>
        <strong>{title}</strong>
        <span>{message}</span>
      </div>
    </div>
  )
}

type SectionErrorProps = {
  section: string
  message: string
}

export function SectionError({ section, message }: SectionErrorProps) {
  return (
    <div className="section-error" role="alert">
      <strong>{section}</strong>: {message}
    </div>
  )
}
