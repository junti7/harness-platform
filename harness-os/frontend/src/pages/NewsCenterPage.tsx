import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

/* ─────────────────────────────────────────────────────────────
   NewsCenterPage — "Calm Mission Control" for daily signal feed
   Apple Newsroom × Bloomberg Terminal aesthetic
   ───────────────────────────────────────────────────────────── */

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

/* ── API Types ───────────────────────────────────────────── */

type Channel = {
  id: string
  label: string
  icon: string
  description: string
}

type FeedItem = {
  id: number
  title: string
  source: string
  url: string
  channel: string
  tier2_score: number | string | null
  tier2_insight: string | null
  tier2_reason: string | null
  ingested_at: string
  abstract: string | null
}

type FeedResponse = {
  total: number
  channel: string
  date: string
  items: FeedItem[]
  channel_counts: Record<string, number>
}

type DigestResponse = {
  date: string
  total_signals: number
  channels: Record<string, number>
  top_sources: string[]
  generated_at: string
}

/* ── Channel visual config ───────────────────────────────── */

const CHANNEL_META: Record<string, { color: string; softBg: string; icon: string }> = {
  tech_ai:        { color: '#2563eb', softBg: 'rgba(37,99,235,0.08)',   icon: '🤖' },
  edu_business:   { color: '#7c3aed', softBg: 'rgba(124,58,237,0.08)', icon: '📚' },
  market_invest:  { color: '#059669', softBg: 'rgba(5,150,105,0.08)',   icon: '📈' },
  policy_reg:     { color: '#d97706', softBg: 'rgba(217,119,6,0.08)',   icon: '⚖️' },
  _default:       { color: '#64748b', softBg: 'rgba(100,116,139,0.08)', icon: '📰' },
}

function channelVisual(channelId: string) {
  return CHANNEL_META[channelId] ?? CHANNEL_META._default
}

/* ── Utility helpers ─────────────────────────────────────── */

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  if (diff < 0) return '방금'
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return '방금'
  if (mins < 60) return `${mins}분 전`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}시간 전`
  const days = Math.floor(hrs / 24)
  return `${days}일 전`
}

function scoreNum(raw: number | string | null): number {
  if (raw == null) return 0
  const n = typeof raw === 'string' ? parseFloat(raw) : raw
  return Number.isFinite(n) ? n : 0
}

function scoreColor(score: number): string {
  if (score >= 8) return 'var(--success)'
  if (score >= 5) return 'var(--accent)'
  return 'var(--text-faint)'
}

function todayStr(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function formatDateKR(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${y}년 ${parseInt(m, 10)}월 ${parseInt(d, 10)}일`
}

/* ── Animated counter hook ───────────────────────────────── */

function useAnimatedCount(target: number, durationMs = 600): number {
  const [current, setCurrent] = useState(0)
  const frameRef = useRef<number>(0)

  useEffect(() => {
    const start = current
    const diff = target - start
    if (diff === 0) return
    const t0 = performance.now()
    const tick = (now: number) => {
      const elapsed = now - t0
      const progress = Math.min(elapsed / durationMs, 1)
      // ease-out quad
      const eased = 1 - (1 - progress) * (1 - progress)
      setCurrent(Math.round(start + diff * eased))
      if (progress < 1) frameRef.current = requestAnimationFrame(tick)
    }
    frameRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, durationMs])

  return current
}

/* ── Skeleton Placeholder ────────────────────────────────── */

function Skeleton({ width = '100%', height = 16, radius = 6 }: { width?: string | number; height?: number; radius?: number }) {
  return (
    <div style={{
      width, height, borderRadius: radius,
      background: 'linear-gradient(90deg, var(--border) 25%, var(--bg-elevated) 50%, var(--border) 75%)',
      backgroundSize: '200% 100%',
      animation: 'nc-shimmer 1.4s ease-in-out infinite',
    }} />
  )
}

/* ── Stat Card (for Quick Stats Bar) ─────────────────────── */

function StatCard({ icon, label, count, active, onClick }: {
  icon: string; label: string; count: number; active: boolean; onClick: () => void
}) {
  const animCount = useAnimatedCount(count)
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 'var(--sp-sm)',
        padding: '10px 18px', borderRadius: 'var(--r-lg)',
        border: active ? '1.5px solid var(--accent)' : '1px solid var(--border)',
        background: active ? 'var(--accent-soft)' : 'var(--surface)',
        cursor: 'pointer', transition: 'all var(--dur) var(--ease)',
        boxShadow: active ? '0 0 16px rgba(37,99,235,0.12)' : 'var(--shadow-sm)',
        flex: '0 0 auto', whiteSpace: 'nowrap',
      }}
      onMouseEnter={e => {
        if (!active) (e.currentTarget.style.borderColor = 'var(--accent)')
        e.currentTarget.style.transform = 'translateY(-1px)'
      }}
      onMouseLeave={e => {
        if (!active) (e.currentTarget.style.borderColor = 'var(--border)')
        e.currentTarget.style.transform = 'translateY(0)'
      }}
    >
      <span style={{ fontSize: 20 }}>{icon}</span>
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: 'var(--text-muted)', fontWeight: 500 }}>{label}</span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700,
        color: active ? 'var(--accent)' : 'var(--ink-strong)',
        minWidth: 28, textAlign: 'right',
      }}>{animCount}</span>
    </button>
  )
}

/* ── Score Badge ──────────────────────────────────────────── */

function ScoreBadge({ score }: { score: number }) {
  const clr = scoreColor(score)
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 'var(--r-pill)',
      fontSize: 12, fontWeight: 700, fontFamily: 'var(--font-mono)',
      color: clr,
      background: score >= 8 ? 'rgba(5,150,105,0.1)' : score >= 5 ? 'rgba(37,99,235,0.1)' : 'rgba(100,116,139,0.1)',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: clr }} />
      {score.toFixed(1)}
    </span>
  )
}

/* ── Source Pill ──────────────────────────────────────────── */

function SourcePill({ source }: { source: string }) {
  return (
    <span style={{
      padding: '2px 10px', borderRadius: 'var(--r-pill)',
      fontSize: 11, fontWeight: 600, letterSpacing: '0.02em',
      color: 'var(--text-muted)', background: 'var(--bg-elevated)',
      border: '1px solid var(--border)',
      textTransform: 'uppercase',
    }}>{source}</span>
  )
}

/* ═══════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════ */

export function NewsCenterPage({ apiBase, authHeaders }: Props) {

  /* ── State ─────────────────────────────────────────────── */
  const [channels, setChannels] = useState<Channel[]>([])
  const [feed, setFeed] = useState<FeedResponse | null>(null)
  const [digest, setDigest] = useState<DigestResponse | null>(null)
  const [activeChannel, setActiveChannel] = useState<string>('all')
  const [selectedDate, setSelectedDate] = useState(todayStr())
  const [loading, setLoading] = useState(true)
  const [loadingAction, setLoadingAction] = useState<'pdf' | 'slack' | null>(null)
  const [detailItem, setDetailItem] = useState<FeedItem | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [appeared, setAppeared] = useState(false)

  /* ── Fetch channels ────────────────────────────────────── */
  useEffect(() => {
    ;(async () => {
      try {
        const res = await fetch(`${apiBase}/api/news-center/channels`, { headers: authHeaders() })
        if (res.ok) {
          const data = await res.json()
          setChannels(data.channels ?? [])
        }
      } catch { /* channels are optional for render */ }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase])

  /* ── Fetch feed + digest on channel/date change ────────── */
  const fetchFeed = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const channelParam = activeChannel === 'all' ? '' : `&channel=${activeChannel}`
      const [feedRes, digestRes] = await Promise.all([
        fetch(`${apiBase}/api/news-center/feed?date=${selectedDate}&limit=50&offset=0${channelParam}`, { headers: authHeaders() }),
        fetch(`${apiBase}/api/news-center/daily-digest?date=${selectedDate}`, { headers: authHeaders() }),
      ])
      if (feedRes.ok) setFeed(await feedRes.json())
      else setError('피드를 불러올 수 없습니다.')
      if (digestRes.ok) setDigest(await digestRes.json())
    } catch {
      setError('네트워크 오류가 발생했습니다.')
    } finally {
      setLoading(false)
      setTimeout(() => setAppeared(true), 60)
    }
  }, [apiBase, authHeaders, activeChannel, selectedDate])

  useEffect(() => { fetchFeed() }, [fetchFeed])

  /* ── Actions ───────────────────────────────────────────── */
  const generatePdf = async () => {
    setLoadingAction('pdf')
    try {
      const res = await fetch(`${apiBase}/api/news-center/generate-pdf`, { method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify({ date: selectedDate }) })
      if (!res.ok) throw new Error()
      // success toast could go here
    } catch { setError('PDF 생성 실패') } finally { setLoadingAction(null) }
  }

  const sendSlack = async () => {
    setLoadingAction('slack')
    try {
      const res = await fetch(`${apiBase}/api/news-center/send-slack`, { method: 'POST', headers: { ...authHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify({ date: selectedDate }) })
      if (!res.ok) throw new Error()
    } catch { setError('Slack 발송 실패') } finally { setLoadingAction(null) }
  }

  /* ── Derived data ──────────────────────────────────────── */
  const items = feed?.items ?? []
  const sortedItems = useMemo(() =>
    [...items].sort((a, b) => scoreNum(b.tier2_score) - scoreNum(a.tier2_score)),
  [items])
  const featuredItem = sortedItems[0] ?? null
  const gridItems = sortedItems.slice(1)
  const totalSignals = digest?.total_signals ?? feed?.total ?? 0
  const channelCounts = feed?.channel_counts ?? digest?.channels ?? {}

  /* ── Channel tabs (derived from channels list + counts) ── */
  const tabItems = useMemo(() => {
    const all = { id: 'all', label: '전체', icon: '📋' }
    const mapped = channels.map(c => ({ id: c.id, label: c.label, icon: c.icon }))
    return [all, ...mapped]
  }, [channels])

  /* ── Inline style injection (keyframes) ────────────────── */
  const styleTag = `
    @keyframes nc-shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
    @keyframes nc-fadeUp {
      from { opacity: 0; transform: translateY(12px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes nc-slideIn {
      from { transform: translateX(100%); opacity: 0; }
      to   { transform: translateX(0); opacity: 1; }
    }
    @keyframes nc-pulse {
      0%, 100% { opacity: 1; }
      50%      { opacity: 0.5; }
    }
    @keyframes nc-countUp {
      from { opacity: 0; transform: scale(0.7); }
      to   { opacity: 1; transform: scale(1); }
    }
    @keyframes nc-heroGradient {
      0%   { background-position: 0% 50%; }
      50%  { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
  `

  /* ── Render ─────────────────────────────────────────────── */
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', fontFamily: 'var(--font-sans)' }}>
      <style>{styleTag}</style>

      {/* ═══ HERO HEADER ═══════════════════════════════════ */}
      <header style={{
        position: 'relative', overflow: 'hidden',
        padding: '48px 40px 36px',
        background: 'linear-gradient(135deg, var(--surface) 0%, var(--accent-soft) 40%, rgba(14,165,233,0.08) 100%)',
        backgroundSize: '200% 200%',
        animation: 'nc-heroGradient 12s ease infinite',
        borderBottom: '1px solid var(--border)',
      }}>
        {/* Decorative grid overlay */}
        <div style={{
          position: 'absolute', inset: 0, opacity: 0.035,
          backgroundImage: `
            linear-gradient(var(--ink) 1px, transparent 1px),
            linear-gradient(90deg, var(--ink) 1px, transparent 1px)
          `,
          backgroundSize: '48px 48px',
          pointerEvents: 'none',
        }} />
        {/* Decorative accent circle */}
        <div style={{
          position: 'absolute', top: -60, right: -40, width: 260, height: 260,
          borderRadius: '50%', background: 'var(--accent)', opacity: 0.04,
          filter: 'blur(60px)', pointerEvents: 'none',
        }} />

        <div style={{ position: 'relative', maxWidth: 1280, margin: '0 auto' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--sp-md)' }}>
            <div>
              <h1 style={{
                margin: 0, fontSize: 36, fontWeight: 800, letterSpacing: '-0.025em',
                color: 'var(--ink-strong)',
                background: 'linear-gradient(135deg, var(--ink-strong) 0%, var(--accent) 100%)',
                WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
              }}>
                뉴스 센터
              </h1>
              <p style={{ margin: '6px 0 0', fontSize: 15, color: 'var(--text-muted)', fontWeight: 500 }}>
                {formatDateKR(selectedDate)} · <span style={{ color: 'var(--accent)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{totalSignals}</span> 건의 시그널 수집
              </p>
            </div>

            {/* Actions cluster */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-sm)', flexWrap: 'wrap' }}>
              <input
                type="date"
                value={selectedDate}
                onChange={e => setSelectedDate(e.target.value)}
                style={{
                  padding: '8px 14px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)',
                  background: 'var(--surface)', color: 'var(--ink)', fontSize: 13, fontFamily: 'var(--font-sans)',
                  cursor: 'pointer', outline: 'none', transition: 'border-color var(--dur) var(--ease)',
                }}
                onFocus={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
                onBlur={e => (e.currentTarget.style.borderColor = 'var(--border)')}
              />
              <button
                onClick={generatePdf}
                disabled={loadingAction === 'pdf'}
                style={{
                  padding: '8px 20px', borderRadius: 'var(--r-md)', border: 'none',
                  background: 'var(--accent)', color: '#fff', fontSize: 13, fontWeight: 600,
                  cursor: loadingAction === 'pdf' ? 'wait' : 'pointer',
                  opacity: loadingAction === 'pdf' ? 0.65 : 1,
                  transition: 'all var(--dur) var(--ease)',
                  boxShadow: '0 1px 4px rgba(37,99,235,0.18)',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent-hover)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.transform = 'translateY(0)' }}
              >
                {loadingAction === 'pdf' ? '생성 중…' : '📄 PDF 리포트'}
              </button>
              <button
                onClick={sendSlack}
                disabled={loadingAction === 'slack'}
                style={{
                  padding: '8px 20px', borderRadius: 'var(--r-md)',
                  border: '1px solid var(--border)', background: 'var(--surface)',
                  color: 'var(--ink)', fontSize: 13, fontWeight: 600,
                  cursor: loadingAction === 'slack' ? 'wait' : 'pointer',
                  opacity: loadingAction === 'slack' ? 0.65 : 1,
                  transition: 'all var(--dur) var(--ease)',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.color = 'var(--accent)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--ink)'; e.currentTarget.style.transform = 'translateY(0)' }}
              >
                {loadingAction === 'slack' ? '발송 중…' : '💬 Slack 발송'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ═══ BODY ══════════════════════════════════════════ */}
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '0 40px 80px' }}>

        {/* ── Quick Stats Bar ─────────────────────────────── */}
        <div style={{
          display: 'flex', gap: 'var(--sp-sm)', overflowX: 'auto',
          padding: '24px 0 8px', scrollbarWidth: 'none',
        }}>
          {Object.keys(channelCounts).length > 0
            ? Object.entries(channelCounts).map(([chId, cnt]) => {
                const meta = channels.find(c => c.id === chId)
                const vis = channelVisual(chId)
                return (
                  <StatCard
                    key={chId}
                    icon={meta?.icon ?? vis.icon}
                    label={meta?.label ?? chId}
                    count={cnt as number}
                    active={activeChannel === chId}
                    onClick={() => setActiveChannel(prev => prev === chId ? 'all' : chId)}
                  />
                )
              })
            : loading
              ? Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} style={{ padding: '10px 18px', borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', background: 'var(--surface)', display: 'flex', gap: 8, alignItems: 'center' }}>
                    <Skeleton width={24} height={24} radius={12} />
                    <Skeleton width={60} height={14} />
                    <Skeleton width={28} height={20} />
                  </div>
                ))
              : null
          }
        </div>

        {/* ── Channel Filter Tabs ─────────────────────────── */}
        <nav style={{
          display: 'flex', gap: 6, padding: '16px 0 24px',
          overflowX: 'auto', scrollbarWidth: 'none',
        }}>
          {tabItems.map(tab => {
            const isActive = activeChannel === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveChannel(tab.id)}
                style={{
                  padding: '7px 18px', borderRadius: 'var(--r-pill)', border: 'none',
                  background: isActive ? 'var(--accent)' : 'transparent',
                  color: isActive ? '#fff' : 'var(--text-muted)',
                  fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  transition: 'all var(--dur) var(--ease)',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--bg-elevated)' }}
                onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent' }}
              >
                {tab.icon} {tab.label}
              </button>
            )
          })}
        </nav>

        {/* ── Error banner ────────────────────────────────── */}
        {error && (
          <div style={{
            padding: '12px 20px', borderRadius: 'var(--r-md)',
            background: 'rgba(220,38,38,0.06)', border: '1px solid rgba(220,38,38,0.2)',
            color: 'var(--danger)', fontSize: 13, fontWeight: 500, marginBottom: 20,
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span>⚠️</span> {error}
            <button onClick={() => setError(null)} style={{ marginLeft: 'auto', border: 'none', background: 'none', color: 'var(--danger)', cursor: 'pointer', fontWeight: 700, fontSize: 14 }}>✕</button>
          </div>
        )}

        {/* ── Loading State ───────────────────────────────── */}
        {loading && (
          <div>
            {/* Featured skeleton */}
            <div style={{ borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', padding: 32, marginBottom: 28, background: 'var(--surface)' }}>
              <Skeleton width="60%" height={28} />
              <div style={{ height: 12 }} />
              <Skeleton width="80%" height={16} />
              <div style={{ height: 8 }} />
              <Skeleton width="40%" height={14} />
              <div style={{ height: 16 }} />
              <Skeleton width="100%" height={80} radius={8} />
            </div>
            {/* Grid skeletons */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 20 }}>
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} style={{ borderRadius: 'var(--r-lg)', border: '1px solid var(--border)', padding: 24, background: 'var(--surface)' }}>
                  <Skeleton width="85%" height={18} />
                  <div style={{ height: 10 }} />
                  <Skeleton width="50%" height={13} />
                  <div style={{ height: 12 }} />
                  <Skeleton width="100%" height={48} radius={6} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Empty state ─────────────────────────────────── */}
        {!loading && sortedItems.length === 0 && (
          <div style={{
            textAlign: 'center', padding: '80px 20px',
            color: 'var(--text-faint)',
          }}>
            <div style={{ fontSize: 56, marginBottom: 16, opacity: 0.4 }}>📭</div>
            <p style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-muted)', margin: 0 }}>아직 수집된 시그널이 없습니다</p>
            <p style={{ fontSize: 14, marginTop: 6 }}>파이프라인을 실행하거나 날짜를 변경해 보세요.</p>
          </div>
        )}

        {/* ═══ FEATURED ARTICLE ═════════════════════════════ */}
        {!loading && featuredItem && (
          <article
            onClick={() => setDetailItem(featuredItem)}
            style={{
              position: 'relative', borderRadius: 'var(--r-lg)', overflow: 'hidden',
              border: '1px solid var(--border)', background: 'var(--surface)',
              padding: '36px 40px', marginBottom: 28, cursor: 'pointer',
              transition: 'all 240ms var(--ease)',
              boxShadow: 'var(--shadow-card)',
              animation: appeared ? undefined : 'nc-fadeUp 0.5s var(--ease) both',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'translateY(-3px)'
              e.currentTarget.style.boxShadow = '0 12px 40px rgba(0,0,0,0.08)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--shadow-card)'
            }}
          >
            {/* channel accent bar */}
            <div style={{
              position: 'absolute', top: 0, left: 0, bottom: 0, width: 4,
              background: channelVisual(featuredItem.channel).color,
              borderRadius: '4px 0 0 4px',
            }} />

            {/* Featured label */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <span style={{
                padding: '3px 10px', borderRadius: 'var(--r-pill)',
                background: 'linear-gradient(135deg, var(--accent) 0%, var(--accent-cyan) 100%)',
                color: '#fff', fontSize: 10, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em',
              }}>Featured</span>
              <SourcePill source={featuredItem.source} />
              <ScoreBadge score={scoreNum(featuredItem.tier2_score)} />
              <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
                {relativeTime(featuredItem.ingested_at)}
              </span>
            </div>

            <h2 style={{
              margin: 0, fontSize: 24, fontWeight: 800, lineHeight: 1.35,
              color: 'var(--ink-strong)', letterSpacing: '-0.015em',
            }}>
              {featuredItem.title}
            </h2>

            {(featuredItem.abstract || featuredItem.tier2_insight) && (
              <p style={{
                margin: '14px 0 0', fontSize: 15, lineHeight: 1.7,
                color: 'var(--text-muted)', maxWidth: 780,
              }}>
                {featuredItem.tier2_insight || featuredItem.abstract}
              </p>
            )}

            {/* Score bar */}
            {scoreNum(featuredItem.tier2_score) > 0 && (
              <div style={{ marginTop: 18, display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 11, color: 'var(--text-faint)', fontWeight: 600 }}>적합도</span>
                <div style={{
                  flex: 1, maxWidth: 200, height: 5, borderRadius: 3,
                  background: 'var(--bg-elevated)',
                }}>
                  <div style={{
                    height: '100%', borderRadius: 3,
                    width: `${Math.min(scoreNum(featuredItem.tier2_score) * 10, 100)}%`,
                    background: `linear-gradient(90deg, ${scoreColor(scoreNum(featuredItem.tier2_score))}, var(--accent-cyan))`,
                    transition: 'width 0.6s var(--ease)',
                  }} />
                </div>
              </div>
            )}
          </article>
        )}

        {/* ═══ ARTICLE GRID ════════════════════════════════ */}
        {!loading && gridItems.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
            gap: 20,
          }}>
            {gridItems.map((item, idx) => (
              <ArticleCard
                key={item.id}
                item={item}
                index={idx}
                appeared={appeared}
                onClick={() => setDetailItem(item)}
              />
            ))}
          </div>
        )}
      </div>

      {/* ═══ DETAIL SLIDE-OVER PANEL ═══════════════════════ */}
      {detailItem && (
        <DetailPanel
          item={detailItem}
          onClose={() => setDetailItem(null)}
        />
      )}
    </div>
  )
}

/* ── Article Card ─────────────────────────────────────────── */

function ArticleCard({ item, index, appeared, onClick }: {
  item: FeedItem; index: number; appeared: boolean; onClick: () => void
}) {
  const vis = channelVisual(item.channel)
  const score = scoreNum(item.tier2_score)
  const [expanded, setExpanded] = useState(false)

  return (
    <article
      onClick={onClick}
      style={{
        position: 'relative', borderRadius: 'var(--r-lg)',
        border: '1px solid var(--border)', background: 'var(--surface)',
        padding: '22px 24px 20px 28px', cursor: 'pointer',
        transition: 'all 220ms var(--ease)',
        animation: appeared ? undefined : `nc-fadeUp 0.45s var(--ease) ${80 + index * 50}ms both`,
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-2px)'
        e.currentTarget.style.boxShadow = '0 8px 28px rgba(0,0,0,0.07)'
        e.currentTarget.style.borderColor = vis.color
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(0)'
        e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.borderColor = 'var(--border)'
      }}
    >
      {/* Channel accent */}
      <div style={{
        position: 'absolute', top: 12, left: 0, bottom: 12, width: 3,
        borderRadius: '0 3px 3px 0', background: vis.color,
      }} />

      {/* Meta row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
        <SourcePill source={item.source} />
        <ScoreBadge score={score} />
        <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-faint)', fontFamily: 'var(--font-mono)', whiteSpace: 'nowrap' }}>
          {relativeTime(item.ingested_at)}
        </span>
      </div>

      {/* Title */}
      <h3 style={{
        margin: 0, fontSize: 15, fontWeight: 700, lineHeight: 1.45,
        color: 'var(--ink-strong)',
        display: '-webkit-box', WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical', overflow: 'hidden',
      }}>
        {item.title}
      </h3>

      {/* Insight preview */}
      {item.tier2_insight && (
        <p
          onClick={e => { e.stopPropagation(); setExpanded(prev => !prev) }}
          style={{
            margin: '10px 0 0', fontSize: 13, lineHeight: 1.6,
            color: 'var(--text-muted)',
            display: expanded ? 'block' : '-webkit-box',
            WebkitLineClamp: expanded ? undefined : 2,
            WebkitBoxOrient: 'vertical',
            overflow: expanded ? 'visible' : 'hidden',
            cursor: 'pointer',
          }}
        >
          {item.tier2_insight}
        </p>
      )}

      {/* Channel tag */}
      <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{
          fontSize: 11, padding: '2px 8px', borderRadius: 'var(--r-sm)',
          background: vis.softBg, color: vis.color, fontWeight: 600,
        }}>
          {vis.icon} {item.channel}
        </span>
      </div>
    </article>
  )
}

/* ── Detail Panel (slide-over) ────────────────────────────── */

function DetailPanel({ item, onClose }: { item: FeedItem; onClose: () => void }) {
  const vis = channelVisual(item.channel)
  const score = scoreNum(item.tier2_score)

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 999,
          background: 'rgba(15,23,42,0.3)',
          backdropFilter: 'blur(4px)',
          animation: 'nc-fadeUp 0.2s var(--ease) both',
        }}
      />

      {/* Panel */}
      <aside style={{
        position: 'fixed', top: 0, right: 0, bottom: 0,
        width: 'min(520px, 92vw)', zIndex: 1000,
        background: 'var(--surface)', borderLeft: '1px solid var(--border)',
        boxShadow: '-8px 0 40px rgba(0,0,0,0.1)',
        display: 'flex', flexDirection: 'column',
        animation: 'nc-slideIn 0.3s var(--ease) both',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{
          padding: '20px 24px', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0,
          background: 'linear-gradient(180deg, var(--surface) 0%, var(--bg-elevated) 100%)',
        }}>
          <div style={{
            width: 4, height: 32, borderRadius: 2, background: vis.color,
          }} />
          <span style={{
            fontSize: 11, padding: '2px 10px', borderRadius: 'var(--r-pill)',
            background: vis.softBg, color: vis.color, fontWeight: 700,
          }}>
            {vis.icon} {item.channel}
          </span>
          <button
            onClick={onClose}
            style={{
              marginLeft: 'auto', width: 32, height: 32, borderRadius: 'var(--r-md)',
              border: '1px solid var(--border)', background: 'var(--surface)',
              color: 'var(--text-muted)', fontSize: 15, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all var(--dur) var(--ease)',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-elevated)'; e.currentTarget.style.borderColor = 'var(--accent)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--surface)'; e.currentTarget.style.borderColor = 'var(--border)' }}
            aria-label="닫기"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div style={{
          flex: 1, overflowY: 'auto', padding: '28px 28px 40px',
          scrollbarWidth: 'thin',
        }}>
          {/* Title */}
          <h2 style={{
            margin: 0, fontSize: 22, fontWeight: 800, lineHeight: 1.4,
            color: 'var(--ink-strong)', letterSpacing: '-0.01em',
          }}>
            {item.title}
          </h2>

          {/* Meta row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
            <SourcePill source={item.source} />
            <ScoreBadge score={score} />
            <span style={{ fontSize: 12, color: 'var(--text-faint)', fontFamily: 'var(--font-mono)' }}>
              {relativeTime(item.ingested_at)}
            </span>
          </div>

          {/* Abstract */}
          {item.abstract && (
            <section style={{ marginTop: 28 }}>
              <h4 style={sectionHeadStyle}>요약</h4>
              <p style={{
                margin: 0, fontSize: 14, lineHeight: 1.75, color: 'var(--ink)',
                padding: '14px 18px', borderRadius: 'var(--r-md)',
                background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              }}>
                {item.abstract}
              </p>
            </section>
          )}

          {/* Tier2 Analysis */}
          <section style={{ marginTop: 28 }}>
            <h4 style={sectionHeadStyle}>Tier-2 분석</h4>
            <div style={{
              padding: '18px 20px', borderRadius: 'var(--r-md)',
              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            }}>
              {/* Score bar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                <span style={{ fontSize: 12, color: 'var(--text-faint)', fontWeight: 600, minWidth: 50 }}>점수</span>
                <div style={{ flex: 1, height: 6, borderRadius: 3, background: 'var(--border)' }}>
                  <div style={{
                    height: '100%', borderRadius: 3,
                    width: `${Math.min(score * 10, 100)}%`,
                    background: `linear-gradient(90deg, ${scoreColor(score)}, var(--accent-cyan))`,
                    transition: 'width 0.8s var(--ease)',
                  }} />
                </div>
                <span style={{ fontSize: 16, fontWeight: 800, fontFamily: 'var(--font-mono)', color: scoreColor(score) }}>
                  {score.toFixed(1)}
                </span>
              </div>

              {/* Reason */}
              {item.tier2_reason && (
                <div style={{ marginBottom: 12 }}>
                  <span style={analysisLabelStyle}>판단 근거</span>
                  <p style={analysisTextStyle}>{item.tier2_reason}</p>
                </div>
              )}

              {/* Insight */}
              {item.tier2_insight && (
                <div>
                  <span style={analysisLabelStyle}>인사이트</span>
                  <p style={analysisTextStyle}>{item.tier2_insight}</p>
                </div>
              )}
            </div>
          </section>

          {/* External link */}
          {item.url && (
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={e => e.stopPropagation()}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 28,
                padding: '10px 22px', borderRadius: 'var(--r-md)',
                background: 'var(--accent)', color: '#fff', fontSize: 13, fontWeight: 600,
                textDecoration: 'none',
                transition: 'all var(--dur) var(--ease)',
                boxShadow: '0 2px 8px rgba(37,99,235,0.2)',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--accent-hover)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.transform = 'translateY(0)' }}
            >
              🔗 원문 보기
              <span style={{ fontSize: 11, opacity: 0.8 }}>↗</span>
            </a>
          )}
        </div>
      </aside>
    </>
  )
}

/* ── Shared inline style tokens ───────────────────────────── */

const sectionHeadStyle: React.CSSProperties = {
  margin: '0 0 10px', fontSize: 12, fontWeight: 700,
  color: 'var(--text-faint)', textTransform: 'uppercase',
  letterSpacing: '0.06em',
}

const analysisLabelStyle: React.CSSProperties = {
  fontSize: 11, fontWeight: 700, color: 'var(--text-faint)',
  textTransform: 'uppercase', letterSpacing: '0.04em',
}

const analysisTextStyle: React.CSSProperties = {
  margin: '4px 0 0', fontSize: 13.5, lineHeight: 1.7, color: 'var(--ink)',
}
