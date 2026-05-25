import { useEffect, useMemo, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_HARNESS_OS_API_BASE ?? 'http://127.0.0.1:8000'

type TokenUsageDay = {
  day: string
  models: Record<string, number>
  total: number
}

type Props = {
  apiSecret: string
  backendUrl?: string
}

export function TokenUsagePage({ apiSecret, backendUrl = API_BASE }: Props) {
  const [data, setData] = useState<TokenUsageDay[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  const [tooltipPos, setTooltipPos] = useState({ left: 0, top: 0 })
  const chartSurfaceRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const headers: Record<string, string> = {}
        if (apiSecret) {
          headers['X-Harness-Secret'] = apiSecret
        }
        const res = await fetch(`${backendUrl}/api/costs/token-usage`, { headers })
        if (!res.ok) throw new Error(`토큰 사용량 API 오류: ${res.status}`)
        const payload = (await res.json()) as TokenUsageDay[]
        setData(payload)
      } catch (err) {
        console.error(err)
        setError(err instanceof Error ? err.message : '데이터 로드 실패')
      } finally {
        setLoading(false)
      }
    }
    void fetchData()
  }, [apiSecret, backendUrl])

  const modelColors: Record<string, string> = {
    'claude-opus-4-7': '#6d5ce7',
    'claude-sonnet-4-6': '#e67e22',
    'claude-haiku-4-5-20251001': '#169fbd',
    'claude-sonnet-4-5-20250929': '#c9a227',
    'claude-haiku-4-5': '#7b61ff',
    'claude-sonnet-4-5': '#d95f8d',
  }
  
  const getModelColor = (model: string) => {
    if (modelColors[model]) return modelColors[model]
    let hash = 0
    for (let i = 0; i < model.length; i++) {
      hash = model.charCodeAt(i) + ((hash << 5) - hash)
    }
    const h = Math.abs(hash % 360)
    return `hsl(${h}, 55%, 55%)`
  }

  const modelTotals = useMemo(() => {
    const totals: Record<string, number> = {}
    data.forEach(d => {
      Object.entries(d.models).forEach(([model, tokens]) => {
        totals[model] = (totals[model] ?? 0) + tokens
      })
    })
    return totals
  }, [data])

  const allModels = useMemo(() => {
    return Object.keys(modelTotals).sort((a, b) => (modelTotals[b] ?? 0) - (modelTotals[a] ?? 0))
  }, [modelTotals])

  const maxTotal = useMemo(() => {
    const max = Math.max(1, ...data.map(d => d.total))
    return Math.ceil(max * 1.1)
  }, [data])

  const totalTokens = useMemo(() => data.reduce((acc, cur) => acc + cur.total, 0), [data])

  const svgWidth = 800
  const svgHeight = 380
  const paddingLeft = 92
  const paddingRight = 30
  const paddingTop = 28
  const paddingBottom = 58

  const chartWidth = svgWidth - paddingLeft - paddingRight
  const chartHeight = svgHeight - paddingTop - paddingBottom

  const TOOLTIP_WIDTH = 260
  const TOOLTIP_HEIGHT = 196
  const TOOLTIP_MARGIN = 12

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const surface = chartSurfaceRef.current
    if (!surface) {
      return
    }
    const svgRect = e.currentTarget.getBoundingClientRect()
    const surfaceRect = surface.getBoundingClientRect()
    const mouseX = e.clientX - svgRect.left
    const scaleX = svgWidth / Math.max(svgRect.width, 1)
    const xInSvg = mouseX * scaleX
    const gap = chartWidth / Math.max(data.length, 1)
    const centers = data.map((_, i) => paddingLeft + i * gap + gap / 2)
    const nearest = centers.reduce(
      (best, centerX, i) => {
        const diff = Math.abs(centerX - xInSvg)
        if (diff < best.diff) return { index: i, diff }
        return best
      },
      { index: 0, diff: Number.POSITIVE_INFINITY },
    )
    const index = nearest.index
    const x = e.clientX - surfaceRect.left
    const y = e.clientY - surfaceRect.top

    let left = x + 18
    if (left + TOOLTIP_WIDTH + TOOLTIP_MARGIN > surfaceRect.width) {
      left = x - TOOLTIP_WIDTH - 18
    }
    left = Math.max(TOOLTIP_MARGIN, Math.min(left, surfaceRect.width - TOOLTIP_WIDTH - TOOLTIP_MARGIN))

    let top = y - TOOLTIP_HEIGHT / 2
    top = Math.max(TOOLTIP_MARGIN, Math.min(top, surfaceRect.height - TOOLTIP_HEIGHT - TOOLTIP_MARGIN))

    setTooltipPos({
      left,
      top,
    })
    setHoveredIndex(index)
  }

  const handleMouseLeave = () => {
    setHoveredIndex(null)
  }

  const formatAxisTick = (value: number) => {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
    if (value >= 1_000) return `${Math.round(value / 1_000)}K`
    return value.toLocaleString('ko-KR')
  }

  if (loading) {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '3rem' }}>
        <span className="spinner" />
        <p style={{ marginTop: '1rem', color: 'var(--color-text-muted)' }}>토큰 분석기 데이터를 집계 중입니다…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="panel error-panel" style={{ padding: '2rem' }}>
        <h3>데이터 호출 실패</h3>
        <p style={{ color: 'var(--color-danger)' }}>{error}</p>
      </div>
    )
  }

  return (
    <div className="token-usage-container">
      <section className="panel token-usage-panel">
        <div className="panel-head token-usage-head">
          <div className="token-usage-title-wrap">
            <h2 className="token-usage-title">LLM 토큰 사용량</h2>
            <p className="token-usage-subtitle">일별 모델 사용량 누적 스택 차트</p>
          </div>
          <div className="token-total-badge">
            <span className="token-total-label">전체 누적</span>
            <strong className="token-total-value">{totalTokens.toLocaleString('ko-KR')} tokens</strong>
          </div>
        </div>

        <div className="chart-legend">
          {allModels.map(model => (
            <div key={model} className="chart-legend-item">
              <span className="chart-legend-dot" style={{ background: getModelColor(model) }} />
              <span className="chart-legend-name" translate="no">{model}</span>
            </div>
          ))}
        </div>

        <div className="token-chart-surface" ref={chartSurfaceRef}>
          <div className="token-chart-scroll">
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              width="100%"
              height="auto"
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            >
            {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
              const y = paddingTop + chartHeight * (1 - ratio)
              const val = Math.round(maxTotal * ratio)
              return (
                <g key={i}>
                  <line
                    x1={paddingLeft}
                    y1={y}
                    x2={svgWidth - paddingRight}
                    y2={y}
                    stroke="var(--color-border)"
                    strokeWidth="1"
                    strokeDasharray="5,7"
                    opacity="0.8"
                  />
                  <text x={paddingLeft - 12} y={y + 4} textAnchor="end" fontSize="11" fill="var(--color-text-faint)" fontWeight="600">
                    {formatAxisTick(val)}
                  </text>
                </g>
              )
            })}

            {data.map((dayData, index) => {
              const barWidth = Math.max(12, Math.min(40, chartWidth / data.length - 10))
              const gap = chartWidth / data.length
              const x = paddingLeft + index * gap + (gap - barWidth) / 2

              let currentYOffset = 0
              return (
                <g key={dayData.day} style={{ cursor: 'crosshair' }}>
                  {allModels.map(model => {
                    const tokenVal = dayData.models[model] ?? 0
                    if (tokenVal <= 0) return null

                    const height = (tokenVal / maxTotal) * chartHeight
                    const y = paddingTop + chartHeight - currentYOffset - height
                    currentYOffset += height

                    return (
                      <rect
                        key={model}
                        x={x}
                        y={y}
                        width={barWidth}
                        height={height}
                        fill={getModelColor(model)}
                        opacity={hoveredIndex === index ? 0.95 : 0.82}
                        rx="3"
                        style={{ transition: 'all 0.2s ease' }}
                      />
                    )
                  })}

                  <rect
                    x={x - 4}
                    y={paddingTop}
                    width={barWidth + 8}
                    height={chartHeight}
                    fill="transparent"
                  />

                  <text
                    x={x + barWidth / 2}
                    y={svgHeight - paddingBottom + 28}
                    textAnchor="middle"
                    fontSize="11"
                    fill={hoveredIndex === index ? 'var(--color-accent)' : 'var(--color-text-muted)'}
                    fontWeight={hoveredIndex === index ? '700' : '500'}
                    transform={`rotate(-25, ${x + barWidth / 2}, ${svgHeight - paddingBottom + 20})`}
                  >
                    {dayData.day.slice(5)}
                  </text>
                </g>
              )
            })}

            <line
              x1={paddingLeft}
              y1={svgHeight - paddingBottom}
              x2={svgWidth - paddingRight}
              y2={svgHeight - paddingBottom}
              stroke="var(--color-border)"
              strokeWidth="2"
            />
            </svg>
          </div>

          {hoveredIndex !== null && data[hoveredIndex] && (
            <div className="token-tooltip" style={{ width: `${TOOLTIP_WIDTH}px`, left: `${tooltipPos.left}px`, top: `${tooltipPos.top}px` }}>
              <div className="token-tooltip-head">
                <span>{data[hoveredIndex].day}</span>
                <span className="token-tooltip-label">일일 누적</span>
              </div>
              <div className="token-tooltip-list">
                {allModels
                  .map(model => ({ model, value: data[hoveredIndex].models[model] ?? 0 }))
                  .filter(item => item.value > 0)
                  .map(({ model, value }) => (
                    <div key={model} className="token-tooltip-row">
                      <div className="token-tooltip-model">
                        <span className="token-tooltip-dot" style={{ background: getModelColor(model) }} />
                        <span className="token-tooltip-model-name" translate="no">
                          {model.length > 22 ? `${model.slice(0, 22)}…` : model}
                        </span>
                      </div>
                      <span className="token-tooltip-value">{value.toLocaleString('ko-KR')}</span>
                    </div>
                  ))}
              </div>
              <div className="token-tooltip-total">
                <span>합계</span>
                <span>{data[hoveredIndex].total.toLocaleString('ko-KR')}</span>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="panel token-model-table-panel">
        <div className="panel-head">
          <h3>모델별 상세 사용 비중 분석</h3>
        </div>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>모델 식별자</th>
                <th style={{ textAlign: 'right' }}>평균 일일 소모 토큰</th>
                <th style={{ textAlign: 'right' }}>최대 일일 소모 토큰</th>
                <th style={{ textAlign: 'right' }}>누적 소모 토큰</th>
              </tr>
            </thead>
            <tbody>
              {allModels.map(model => {
                const vals = data.map(d => d.models[model] ?? 0)
                const sum = vals.reduce((a, b) => a + b, 0)
                const avg = Math.round(sum / Math.max(1, data.length))
                const max = Math.max(...vals)
                return (
                  <tr key={model}>
                    <td style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', background: getModelColor(model), flexShrink: 0 }} />
                      <span translate="no">{model}</span>
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{avg.toLocaleString('ko-KR')}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace' }}>{max.toLocaleString('ko-KR')}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'monospace', fontWeight: 700, color: 'var(--color-accent)' }}>{sum.toLocaleString('ko-KR')}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
