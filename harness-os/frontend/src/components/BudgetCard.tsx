import React from "react"
import type { CostsSummaryPayload } from "./types"
import { formatUsdAndKrw, formatUsdAndKrwDetailed } from "./utils"

interface BudgetCardProps {
  data: CostsSummaryPayload | null
  loading: boolean
  onClickDetail: () => void
  exchangeRate?: number
}

export const BudgetCard: React.FC<BudgetCardProps> = ({ data, loading, onClickDetail, exchangeRate = 1400 }) => {
  if (loading || !data) {
    return (
      <div className="card loading-card animate-pulse">
        <div className="h-4 w-24 bg-surface-lighter rounded mb-2"></div>
        <div className="h-8 w-40 bg-surface-lighter rounded mb-4"></div>
        <div className="h-2 w-full bg-surface-lighter rounded"></div>
      </div>
    )
  }

  const {
    initial_budget_usd,
    total_spent_usd,
    remaining_budget_usd,
    burn_rate_percent,
  } = data

  return (
    <div 
      className="card interactive-card budget-kpi-card" 
      onClick={onClickDetail}
      style={{
        cursor: "pointer",
        position: "relative",
        overflow: "hidden"
      }}
    >
      {/* Background radial glow */}
      <div 
        style={{
          position: "absolute",
          top: "-50%",
          right: "-50%",
          width: "200px",
          height: "200px",
          borderRadius: "50%",
          background: "radial-gradient(circle, hsla(220, 90%, 50%, 0.15) 0%, transparent 70%)",
          pointerEvents: "none"
        }}
      />
      
      <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <span className="card-title text-muted" style={{ fontSize: "0.85rem", fontWeight: 500, letterSpacing: "0.05em" }}>
          초기 투자 예산
        </span>
        <span className="badge badge-accent" style={{ fontSize: "0.75rem", background: "hsla(220, 80%, 55%, 0.15)", color: "hsl(220, 90%, 65%)" }}>
          USD 기준
        </span>
      </div>

      <div className="kpi-value-container" style={{ display: "flex", alignItems: "baseline", gap: "0.5rem", marginBottom: "0.5rem" }}>
        <span className="kpi-value" style={{ fontSize: "1.45rem", fontWeight: 700, letterSpacing: "-0.03em" }}>
          {formatUsdAndKrw(initial_budget_usd, exchangeRate)}
        </span>
        <span className="kpi-unittext-muted" style={{ fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
          목표 설정액
        </span>
      </div>

      {/* Progress Bar Area */}
      <div className="progress-section" style={{ marginBottom: "1rem" }}>
        <div 
          className="progress-meta" 
          style={{ 
            display: "flex", 
            justifyContent: "space-between", 
            fontSize: "0.8rem", 
            color: "var(--color-text-muted)",
            marginBottom: "0.35rem"
          }}
        >
          <span>지출: <strong style={{ color: "var(--color-text-primary)" }}>{formatUsdAndKrwDetailed(total_spent_usd, exchangeRate)}</strong></span>
          <span>소진율 {burn_rate_percent.toFixed(3)}%</span>
        </div>
        <div 
          className="progress-bar-bg" 
          style={{ 
            height: "6px", 
            width: "100%", 
            background: "var(--color-surface-lighter)", 
            borderRadius: "999px",
            overflow: "hidden" 
          }}
        >
          <div 
            className="progress-bar-fill animate-progress"
            style={{ 
              height: "100%", 
              width: `${Math.min(100, Math.max(0.5, burn_rate_percent))}%`, 
              background: "linear-gradient(90deg, hsl(220, 80%, 50%) 0%, hsl(200, 95%, 45%) 100%)",
              borderRadius: "999px",
              boxShadow: "0 0 8px hsla(220, 80%, 50%, 0.5)"
            }}
          />
        </div>
      </div>

      <div 
        className="card-footer" 
        style={{ 
          display: "flex", 
          justifyContent: "space-between", 
          alignItems: "center",
          borderTop: "1px solid var(--color-border)",
          paddingTop: "0.75rem",
          fontSize: "0.8rem",
          color: "var(--color-text-muted)"
        }}
      >
        <span>잔여 예산: <strong style={{ color: "hsl(140, 75%, 60%)" }}>{formatUsdAndKrwDetailed(remaining_budget_usd, exchangeRate)}</strong></span>
        <span 
          className="link-hover" 
          style={{ 
            color: "var(--color-accent)", 
            fontSize: "0.75rem", 
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: "0.25rem" 
          }}
        >
          상세 분석 ↗
        </span>
      </div>
    </div>
  )
}
