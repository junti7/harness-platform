import { useEffect, useRef, useState } from 'react'

type Props = {
  values: number[]
  colorClass: 'free' | 'paid' | 'cost'
  dates?: string[]
  height?: number
}

export function SparkChart({ values, colorClass, dates, height = 160 }: Props) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [width, setWidth] = useState(320)

  useEffect(() => {
    const node = containerRef.current
    if (!node) return
    const updateWidth = () => {
      const next = Math.max(280, Math.floor(node.getBoundingClientRect().width))
      setWidth(next)
    }
    updateWidth()
    const observer = new ResizeObserver(updateWidth)
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  if (!values || values.length === 0) {
    return <div style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>데이터 대기 중…</div>
  }

  const max = Math.max(1, ...values)
  const min = Math.min(...values)

  // 차트 스펙
  const paddingX = 15
  const paddingY = 15

  const chartWidth = width - paddingX * 2
  const chartHeight = height - paddingY * 2

  const points = values.map((val, idx) => {
    const x = paddingX + (idx * (chartWidth / Math.max(1, values.length - 1)))
    // 최솟값과 최댓값 사이 비중
    const range = max - min === 0 ? 1 : max - min
    const y = paddingY + chartHeight - ((val - min) / range) * chartHeight
    return { x, y, val, date: dates?.[idx] ?? '' }
  })

  // path string 생성
  let pathD = ''
  let areaD = ''
  if (points.length > 0) {
    pathD = `M ${points[0].x} ${points[0].y} `
    areaD = `M ${points[0].x} ${height - 10} L ${points[0].x} ${points[0].y} `
    for (let i = 1; i < points.length; i++) {
      pathD += `L ${points[i].x} ${points[i].y} `
      areaD += `L ${points[i].x} ${points[i].y} `
    }
    areaD += `L ${points[points.length - 1].x} ${height - 10} Z`
  }

  // 테마 색상 매핑
  const themeColors = {
    free: { stroke: '#00b894', glow: 'rgba(0, 184, 148, 0.25)', gradient: 'free-grad' },
    paid: { stroke: '#0984e3', glow: 'rgba(9, 132, 227, 0.25)', gradient: 'paid-grad' },
    cost: { stroke: '#d63031', glow: 'rgba(214, 48, 49, 0.25)', gradient: 'cost-grad' },
  }

  const activeColor = themeColors[colorClass] ?? themeColors.free

  const formatDateLabel = (raw: string) => {
    if (!raw) return ''
    if (/^\d{2}-\d{2}$/.test(raw)) return raw
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw.slice(5)
    return raw
  }

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseXInViewBox = mouseX * (width / Math.max(rect.width, 1))
    
    let closestIdx = 0
    let minDiff = Infinity
    points.forEach((pt, idx) => {
      const diff = Math.abs(pt.x - mouseXInViewBox)
      if (diff < minDiff) {
        minDiff = diff
        closestIdx = idx
      }
    })

    setHoveredIdx(closestIdx)
    setTooltipPos({
      x: points[closestIdx].x,
      y: points[closestIdx].y - 8,
    })
  }

  const handleMouseLeave = () => {
    setHoveredIdx(null)
  }

  const labelIndices = [0, Math.floor(values.length / 2), values.length - 1]
  const axisLabels = labelIndices
    .filter((idx, pos, arr) => idx >= 0 && idx < points.length && arr.indexOf(idx) === pos)
    .map(idx => ({
      idx,
      label: formatDateLabel(points[idx].date),
    }))
    .filter(item => item.label)

  return (
    <div 
      className={`sparkline-container ${colorClass}`} 
      style={{ position: 'relative', width: '100%', userSelect: 'none' }}
      onMouseLeave={handleMouseLeave}
      ref={containerRef}
    >
      <svg 
        width={width}
        height={height} 
        viewBox={`0 0 ${width} ${height}`} 
        style={{ overflow: 'visible', cursor: 'crosshair' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <defs>
          <linearGradient id={activeColor.gradient} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={activeColor.stroke} stopOpacity="0.4" />
            <stop offset="100%" stopColor={activeColor.stroke} stopOpacity="0.0" />
          </linearGradient>
          <filter id="glow" x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Area Gradient Fill */}
        {areaD && (
          <path d={areaD} fill={`url(#${activeColor.gradient})`} />
        )}

        {/* Background Grid Line (Min/Max guide lines) */}
        <line x1={paddingX} y1={paddingY} x2={width - paddingX} y2={paddingY} stroke="var(--color-border)" strokeWidth="0.5" strokeDasharray="3,3" />
        <line x1={paddingX} y1={height - 20} x2={width - paddingX} y2={height - 20} stroke="var(--color-border)" strokeWidth="0.5" strokeDasharray="3,3" />

        {/* The Sparkline Path */}
        {pathD && (
          <path 
            d={pathD} 
            fill="none" 
            stroke={activeColor.stroke} 
            strokeWidth="2.5" 
            strokeLinecap="round" 
            strokeLinejoin="round"
            filter="url(#glow)"
          />
        )}

        {/* Active Point Highlight Circle */}
        {hoveredIdx !== null && points[hoveredIdx] && (
          <g>
            {/* Guide line */}
            <line 
              x1={points[hoveredIdx].x} 
              y1={paddingY} 
              x2={points[hoveredIdx].x} 
              y2={height - 20} 
              stroke="var(--color-accent)" 
              strokeWidth="0.75" 
              strokeDasharray="2,2" 
            />
            {/* Outer pulsating ring */}
            <circle 
              cx={points[hoveredIdx].x} 
              cy={points[hoveredIdx].y} 
              r="6" 
              fill={activeColor.stroke} 
              opacity="0.3" 
            />
            {/* Inner solid core */}
            <circle 
              cx={points[hoveredIdx].x} 
              cy={points[hoveredIdx].y} 
              r="3.5" 
              fill="#fff" 
              stroke={activeColor.stroke} 
              strokeWidth="2" 
            />
          </g>
        )}
      </svg>

      {/* Micro-interaction Hover Tooltip Portal (Black Card) */}
      {hoveredIdx !== null && points[hoveredIdx] && (
        <div
          style={{
            position: 'absolute',
            left: `${tooltipPos.x}px`,
            top: `${tooltipPos.y}px`,
            transform: 'translate(-50%, -100%)',
            background: 'rgba(15, 23, 42, 0.95)',
            color: '#fff',
            padding: '0.4rem 0.6rem',
            borderRadius: '6px',
            boxShadow: '0 8px 16px rgba(0, 0, 0, 0.3)',
            fontSize: '0.75rem',
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
            zIndex: 10,
            backdropFilter: 'blur(4px)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            fontWeight: '600',
            fontFamily: 'sans-serif',
          }}
        >
          <span style={{ color: '#38bdf8', marginRight: '0.35rem' }}>
            {formatDateLabel(points[hoveredIdx].date) || '일자'}
          </span>
          <strong style={{ color: '#fff', fontFamily: 'monospace' }}>
            {points[hoveredIdx].val.toLocaleString('ko-KR')}
          </strong>
        </div>
      )}
      {axisLabels.length > 0 && (
        <div className="spark-date-axis" aria-hidden="true">
          <span>{axisLabels[0]?.label}</span>
          <span>{axisLabels[Math.floor(axisLabels.length / 2)]?.label}</span>
          <span>{axisLabels[axisLabels.length - 1]?.label}</span>
        </div>
      )}
    </div>
  )
}
