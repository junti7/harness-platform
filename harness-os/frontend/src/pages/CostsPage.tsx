import React, { useCallback, useEffect, useState } from "react"
import type { CostsSummaryPayload } from "../components/types"
import { formatUsdAndKrw, formatUsdAndKrwDetailed } from "../components/utils"

interface CostsPageProps {
  apiSecret: string
  backendUrl: string
  exchangeRate?: number
}

export const CostsPage: React.FC<CostsPageProps> = ({ apiSecret, backendUrl, exchangeRate = 1400 }) => {
  const [data, setData] = useState<CostsSummaryPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")

  const fetchCosts = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${backendUrl}/api/costs/summary`, {
        headers: {
          "X-Harness-Secret": apiSecret,
        },
      })
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }
      const payload: CostsSummaryPayload = await res.json()
      setData(payload)
      setError(null)
    } catch (err) {
      console.error("Failed to fetch cost summary:", err)
      setError(err instanceof Error ? err.message : "Failed to load cost statistics")
    } finally {
      setLoading(false)
    }
  }, [apiSecret, backendUrl])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchCosts()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [fetchCosts])

  if (loading) {
    return (
      <div className="panel" style={{ padding: "3rem", display: "flex", justifyContent: "center", alignItems: "center", flexDirection: "column", gap: "1rem" }}>
        <div className="animate-spin" style={{ width: "40px", height: "40px", border: "3px solid var(--color-border)", borderTopColor: "var(--color-accent)", borderRadius: "50%" }}></div>
        <span className="text-muted">회사 지출 및 LLM 사용 로그 분석 중...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="panel" style={{ padding: "2rem" }}>
        <div className="banner banner-error">
          <div className="banner-title">지출 분석 실패</div>
          <div className="banner-desc">{error || "백엔드로부터 수집된 데이터가 없습니다."}</div>
          <button className="btn btn-secondary" onClick={fetchCosts} style={{ marginTop: "1rem" }}>
            분석 재시도
          </button>
        </div>
      </div>
    )
  }

  const {
    initial_budget_usd,
    total_spent_usd,
    remaining_budget_usd,
    burn_rate_percent,
    llm_subscriptions,
    daily_costs,
    breakdown_by_provider,
    breakdown_by_model,
  } = data

  const sortedDailyCosts = [...daily_costs].sort((a, b) => {
    return sortOrder === "asc" 
      ? a.day.localeCompare(b.day) 
      : b.day.localeCompare(a.day)
  })

  const getProviderLabel = (provider: string) => {
    switch (provider) {
      case "anthropic": return "Anthropic API (실제 콘솔 조회 최우선)"
      case "openai": return "OpenAI API / ChatGPT Plus (실제 콘솔 조회)"
      case "google": return "Google API / Gemini Advanced (실제 콘솔 조회)"
      case "copilot": return "GitHub Copilot (실제 Usage 확인 최우선)"
      default: return provider
    }
  }

  const getProviderAccent = (provider: string) => {
    switch (provider) {
      case "anthropic": return "hsl(28, 78%, 60%)"
      case "google": return "hsl(214, 84%, 58%)"
      case "openai": return "hsl(176, 65%, 48%)"
      case "copilot": return "hsl(332, 72%, 62%)"
      default: return "var(--color-accent)"
    }
  }

  const getProviderLink = (provider: string) => {
    switch (provider) {
      case "anthropic": return "https://console.anthropic.com/settings/billing"
      case "openai": return "https://platform.openai.com/settings/organization/billing/overview"
      case "google": return "https://console.cloud.google.com/billing"
      case "copilot": return "https://github.com/settings/billing/usage?period=3&group=0&customer=74539200"
      default: return "#"
    }
  }

  return (
    <div className="costs-page-container animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      
      {/* 1. TOP OVERVIEW PANEL */}
      <div className="panel" style={{ position: "relative", overflow: "hidden" }}>
        <div style={{
          position: "absolute",
          top: "-50px",
          left: "-50px",
          width: "200px",
          height: "200px",
          borderRadius: "50%",
          background: "radial-gradient(circle, hsla(220, 80%, 50%, 0.1) 0%, transparent 70%)",
          pointerEvents: "none"
        }} />
        
        <h2 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1.5rem" }}>
          투자 자본 및 LLM 리소스 종합 분석기
        </h2>

        {/* 정책 경고 안내 배너 추가 */}
        <div style={{ 
          background: "hsla(35, 80%, 50%, 0.1)", 
          border: "1px solid hsla(35, 80%, 55%, 0.3)", 
          borderRadius: "8px", 
          padding: "1rem", 
          marginBottom: "1.5rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.4rem"
        }}>
          <div style={{ color: "hsl(35, 90%, 65%)", fontWeight: 600, fontSize: "0.9rem" }}>
            비용 정산 검증 최우선 정책 지침
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", lineHeight: 1.5 }}>
            API 실시간 사용 비용과 구독 요금은 이메일(Gmail) 영수증 및 토큰 집계 방식에 의존하는 것을 <strong>차선책(보조 수단)</strong>으로 삼습니다. 이메일 누락 및 집계 지연 등의 리스크가 있으므로, 정확한 지출 정보는 가급적 <strong>각 서비스별 실제 어드민 콘솔(Anthropic, Google Cloud Console 등)에 직접 접속하여 실시간 청구 데이터를 확인하는 것을 최우선(기본 경로)</strong>으로 진행하여 주시기 바랍니다. 아래 요금제 카드별 직통 링크를 통해 직접 접근이 가능합니다.
          </div>
        </div>

        <div className="kpi-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1.25rem", marginBottom: "1.5rem" }}>
          
          {/* Card 1: Initial Budget */}
          <div className="card" style={{ padding: "1.25rem", background: "var(--color-surface-lighter)" }}>
            <div className="text-muted" style={{ fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
              초기 투자 예산
            </div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>
              {formatUsdAndKrw(initial_budget_usd, exchangeRate)}
            </div>
            <div className="text-muted" style={{ fontSize: "0.75rem", marginTop: "0.25rem" }}>
              지정 시드머니 예산 (USD/KRW)
            </div>
          </div>

          {/* Card 2: Cumulative Spent */}
          <div className="card" style={{ padding: "1.25rem", background: "var(--color-surface-lighter)" }}>
            <div className="text-muted" style={{ fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
              누적 지출 금액
            </div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "hsl(0, 75%, 65%)" }}>
              {formatUsdAndKrwDetailed(total_spent_usd, exchangeRate)}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
              예산 소모율: <strong>{burn_rate_percent.toFixed(4)}%</strong>
            </div>
          </div>

          {/* Card 3: Remaining Capital */}
          <div className="card" style={{ padding: "1.25rem", background: "var(--color-surface-lighter)" }}>
            <div className="text-muted" style={{ fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.05em", marginBottom: "0.5rem" }}>
              잔여 가용 예산
            </div>
            <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "hsl(140, 75%, 60%)" }}>
              {formatUsdAndKrwDetailed(remaining_budget_usd, exchangeRate)}
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)", marginTop: "0.25rem" }}>
              가용 잔여 금액 (USD/KRW)
            </div>
          </div>

        </div>

        {/* Big Visual Gauge Bar */}
        <div style={{ background: "var(--color-surface)", padding: "1.25rem", borderRadius: "12px", border: "1px solid var(--color-border)" }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "var(--color-text-muted)", marginBottom: "0.5rem" }}>
            <span>예산 소모율 진행 현황</span>
            <span>{formatUsdAndKrw(initial_budget_usd, exchangeRate)} 중 {burn_rate_percent.toFixed(4)}% 지출 완료</span>
          </div>
          <div style={{ height: "12px", width: "100%", background: "var(--color-surface-lighter)", borderRadius: "999px", overflow: "hidden" }}>
            <div 
              className="progress-bar-fill animate-progress"
              style={{ 
                height: "100%", 
                width: `${Math.min(100, Math.max(0.5, burn_rate_percent))}%`,
                background: "linear-gradient(90deg, hsl(220, 80%, 55%) 0%, hsl(340, 75%, 55%) 100%)",
                borderRadius: "999px"
              }}
            />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", color: "var(--color-text-muted)", marginTop: "0.4rem" }}>
            <span>0.00% (시작점)</span>
            <span>100.00% (예산 완전 소진)</span>
          </div>
        </div>

      </div>

      {/* 2. LLM SUBSCRIPTIONS GRID */}
      <div>
        <h3 style={{ fontSize: "1.05rem", fontWeight: 600, marginBottom: "0.75rem" }}>
          유료 AI 요금제 구독 및 API 연동 현황 (어드민 콘솔 직접 확인 최우선)
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
          {llm_subscriptions.map((sub) => (
            <div key={sub.provider} className="card interactive-card" style={{ padding: "1.25rem", display: "flex", flexDirection: "column", gap: "0.75rem", minHeight: "200px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h4 style={{ fontSize: "0.95rem", fontWeight: 600, margin: 0 }}>{sub.name}</h4>
                  <span className="text-muted" style={{ fontSize: "0.75rem" }}>{sub.provider}</span>
                </div>
                <div>
                  <span style={{ fontSize: "0.72rem", color: sub.key_configured ? "hsl(140, 75%, 60%)" : "hsl(0, 75%, 65%)", fontWeight: 600 }}>
                    {sub.key_configured ? "연결됨" : "연결 안됨"}
                  </span>
                </div>
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "0.8rem", color: "var(--color-text-muted)", marginBottom: "0.35rem" }}>
                  연동 완료된 핵심 모델 목록:
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.25rem", marginBottom: "0.5rem" }}>
                  {sub.models.map(m => (
                    <span key={m} style={{ fontSize: "0.7rem", background: "var(--color-surface-lighter)", padding: "0.15rem 0.35rem", borderRadius: "4px", border: "1px solid var(--color-border)", fontFamily: "monospace" }}>
                      {m}
                    </span>
                  ))}
                </div>
                <div style={{ marginTop: "0.5rem" }}>
                  <a 
                    href={getProviderLink(sub.provider)} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="link-hover"
                    style={{ 
                      fontSize: "0.75rem", 
                      color: "var(--color-accent)", 
                      fontWeight: 600,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.25rem"
                    }}
                  >
                    {sub.provider === "copilot" ? "GitHub Billing 확인 ↗" : "실제 빌링 콘솔에서 직접 확인 ↗"}
                  </a>
                </div>
              </div>

              <div style={{ 
                borderTop: "1px solid var(--color-border)", 
                paddingTop: "0.6rem", 
                display: "flex", 
                justifyContent: "space-between", 
                alignItems: "center", 
                fontSize: "0.8rem" 
              }}>
                <span className="text-muted">이번 달 지출액 (구독+사용량)</span>
                <strong style={{ color: sub.cost_spent_usd > 0 ? "var(--color-text-primary)" : "var(--color-text-muted)" }}>
                  {formatUsdAndKrwDetailed(sub.cost_spent_usd, exchangeRate)}
                </strong>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 3. COST STRUCTURE BREAKDOWN & DAILY LOG */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "1.5rem" }}>
        
        {/* Left Panel: Cost Structure (Provider & Model Share) */}
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>
            지출 항목 및 비중 분석
          </h3>

          {/* Provider Share */}
          <div>
            <div style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--color-text-muted)", marginBottom: "0.5rem" }}>
              공급업체 및 서비스별 지출 (구독료 포함)
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {breakdown_by_provider.map(item => (
                <div key={item.provider} style={{ fontSize: "0.8rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                    <span><strong>{getProviderLabel(item.provider)}</strong></span>
                    <span>{formatUsdAndKrwDetailed(item.cost_usd, exchangeRate)} ({item.percentage}%)</span>
                  </div>
                  <div style={{ height: "6px", width: "100%", background: "var(--color-surface-lighter)", borderRadius: "999px" }}>
                    <div style={{ 
                      height: "100%", 
                      width: `${item.percentage}%`, 
                      background: getProviderAccent(item.provider),
                      borderRadius: "999px" 
                    }} />
                  </div>
                </div>
              ))}
              {breakdown_by_provider.length === 0 && (
                <div className="text-muted" style={{ fontSize: "0.8rem", textAlign: "center", padding: "1rem" }}>
                  집계된 요금제 지출 기록이 없습니다.
                </div>
              )}
            </div>
          </div>

          <hr style={{ border: "none", borderTop: "1px solid var(--color-border)", margin: "0.5rem 0" }} />

          {/* Model Share */}
          <div>
            <div style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--color-text-muted)", marginBottom: "0.5rem" }}>
              세부 AI 모델별 지출 (사용량 비중 배분)
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
              {breakdown_by_model.map(item => (
                <div key={item.model} style={{ fontSize: "0.8rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                    <span style={{ fontFamily: "monospace" }}>
                      {item.model}
                    </span>
                    <span>{formatUsdAndKrwDetailed(item.cost_usd, exchangeRate)} ({item.percentage}%)</span>
                  </div>
                  <div style={{ height: "6px", width: "100%", background: "var(--color-surface-lighter)", borderRadius: "999px" }}>
                    <div style={{ 
                      height: "100%", 
                      width: `${item.percentage}%`, 
                      background: "hsl(220, 70%, 50%)", 
                      borderRadius: "999px" 
                    }} />
                  </div>
                </div>
              ))}
              {breakdown_by_model.length === 0 && (
                <div className="text-muted" style={{ fontSize: "0.8rem", textAlign: "center", padding: "1rem" }}>
                  집계된 모델 지출 기록이 없습니다.
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Right Panel: Daily Ledger Table */}
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3 style={{ fontSize: "1.05rem", fontWeight: 600, margin: 0 }}>
              일별 지출 명세서 (실제 콘솔 대조 및 영수증 백업용)
            </h3>
            <button 
              className="btn btn-secondary" 
              style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
              onClick={() => setSortOrder(prev => prev === "asc" ? "desc" : "asc")}
            >
              정렬: {sortOrder === "asc" ? "과거순 ⬆" : "최신순 ⬇"}
            </button>
          </div>

          <div style={{ overflowX: "auto", maxHeight: "320px" }}>
            <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", fontSize: "0.8rem", padding: "0.6rem 0.5rem" }}>결제 날짜</th>
                  <th style={{ textAlign: "right", fontSize: "0.8rem", padding: "0.6rem 0.5rem" }}>일일 API 사용액 (USD/KRW 병기)</th>
                  <th style={{ textAlign: "right", fontSize: "0.8rem", padding: "0.6rem 0.5rem" }}>전체 예산 대비 비율</th>
                </tr>
              </thead>
              <tbody>
                {sortedDailyCosts.map(item => {
                  const dayPercent = (item.cost_usd / initial_budget_usd) * 100.0
                  return (
                    <tr key={item.day} style={{ borderBottom: "1px solid var(--color-border)" }}>
                      <td style={{ fontSize: "0.8rem", padding: "0.6rem 0.5rem", fontWeight: 500 }}>
                        {item.day}
                      </td>
                      <td style={{ fontSize: "0.8rem", padding: "0.6rem 0.5rem", textAlign: "right", fontWeight: 600, color: "var(--color-text-primary)" }}>
                        {formatUsdAndKrwDetailed(item.cost_usd, exchangeRate)}
                      </td>
                      <td style={{ fontSize: "0.75rem", padding: "0.6rem 0.5rem", textAlign: "right", color: "var(--color-text-muted)" }}>
                        {dayPercent.toFixed(5)}%
                      </td>
                    </tr>
                  )
                })}
                {sortedDailyCosts.length === 0 && (
                  <tr>
                    <td colSpan={3} className="text-muted" style={{ textAlign: "center", padding: "2rem" }}>
                      해당 기간의 지출 내역이 존재하지 않습니다.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>

    </div>
  )
}
