import { useCallback, useEffect, useRef, useState } from 'react'

// 티커 → 기업명 매핑 (UI 표기용)
const TICKER_NAMES: Record<string, string> = {
  // Physical AI / AGI 인프라
  NVDA: 'NVIDIA',
  AVGO: 'Broadcom',
  TSM:  'TSMC',
  MU:   'Micron',
  ANET: 'Arista Networks',
  VRT:  'Vertiv',
  TER:  'Teradyne',
  CRWV: 'CoreWeave',
  SYM:  'Symbotic',
  ISRG: 'Intuitive Surgical',
  ROK:  'Rockwell Automation',
  PLTR: 'Palantir',
  TSLA: 'Tesla',
  ARM:  'ARM Holdings',
  // 전력 인프라
  CEG:  'Constellation Energy',
  VST:  'Vistra Corp',
  GEV:  'GE Vernova',
  PWR:  'Quanta Services',
  NEE:  'NextEra Energy',
  // 냉각수
  XYL:  'Xylem',
  ECL:  'Ecolab',
  VLTO: 'Veralto',
  // 배터리
  QS:   'QuantumScape',
  STEM: 'Stem Inc',
  ALTM: 'Arcadium Lithium',
  LTHM: 'Livent',
  // ETF
  SMH:  'VanEck Semiconductor ETF',
  SOXX: 'iShares Semiconductor ETF',
  BOTZ: 'Global X Robotics ETF',
  ROBO: 'Robo Global Robotics ETF',
  QQQ:  'Invesco NASDAQ-100 ETF',
  SPY:  'SPDR S&P500 ETF',
}

type DiaryEntry = {
  id: string
  timestamp: string
  type: 'trade_entry' | 'trade_exit' | 'ceo_note' | 'signal_scan' | 'research_update'
  ticker?: string
  company_name?: string
  selection_reason?: string
  side?: string
  shares?: number
  price?: number
  position_value?: number
  atr?: number
  stop_loss?: number
  risk_usd?: number
  system?: string
  signal?: string
  sector?: string
  harness_score?: number
  pnl?: number | null
  pnl_pct?: number | null
  exit_reason?: string
  entry_price?: number
  note?: string
  tags?: string[]
  summary?: string
  new_tickers?: string[]
  sectors?: string[]
  scanned_count?: number
  breakout_count?: number
}

type DiaryStats = {
  total_entries: number
  closed_trades: number
  win_rate_pct: number
  total_pnl: number
}

type Props = {
  apiBase: string
  authHeaders: Record<string, string>
}

const TYPE_LABELS: Record<string, string> = {
  trade_entry:     '매수',
  trade_exit:      '매도/청산',
  ceo_note:        '메모',
  signal_scan:     '신호스캔',
  research_update: '리서치',
}

const TYPE_COLORS: Record<string, string> = {
  trade_entry:     'var(--color-green, #22c55e)',
  trade_exit:      'var(--color-red, #ef4444)',
  ceo_note:        'var(--color-accent)',
  signal_scan:     'var(--color-muted)',
  research_update: '#a78bfa',
}

function fmtTime(ts: string) {
  try {
    const d = new Date(ts)
    return d.toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return ts }
}

function fmtDate(ts: string) {
  try {
    return new Date(ts).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
  } catch { return ts }
}

function PnlChip({ pnl, pnl_pct }: { pnl?: number | null; pnl_pct?: number | null }) {
  if (pnl == null) return null
  const positive = pnl >= 0
  return (
    <span style={{
      display: 'inline-block',
      padding: '0.15rem 0.5rem',
      borderRadius: '999px',
      fontSize: '0.78rem',
      fontWeight: 700,
      background: positive ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)',
      color: positive ? '#22c55e' : '#ef4444',
    }}>
      {positive ? '+' : ''}{pnl.toLocaleString('en-US', { style: 'currency', currency: 'USD' })}
      {pnl_pct != null && ` (${pnl_pct > 0 ? '+' : ''}${pnl_pct.toFixed(2)}%)`}
    </span>
  )
}

function EntryCard({ entry }: { entry: DiaryEntry }) {
  const color = TYPE_COLORS[entry.type] ?? 'var(--color-muted)'
  const label = TYPE_LABELS[entry.type] ?? entry.type

  return (
    <div style={{
      background: 'var(--color-surface)',
      border: '1px solid var(--color-border)',
      borderLeft: `4px solid ${color}`,
      borderRadius: '10px',
      padding: '0.9rem 1rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.4rem',
    }}>
      {/* 헤더 행 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
        <span style={{
          fontSize: '0.72rem', fontWeight: 700, padding: '0.1rem 0.45rem',
          borderRadius: '4px', background: color, color: '#fff', letterSpacing: '0.3px',
        }}>
          {label}
        </span>
        {entry.ticker && (
          <span style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
            <span style={{ fontWeight: 700, fontSize: '0.95rem', lineHeight: 1.2 }}>{entry.ticker}</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--color-muted)', lineHeight: 1.2 }}>
              {entry.company_name ?? TICKER_NAMES[entry.ticker] ?? ''}
            </span>
          </span>
        )}
        {entry.system && (
          <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)', fontWeight: 600 }}>
            {entry.system}
          </span>
        )}
        {entry.sector && (
          <span style={{ fontSize: '0.7rem', color: '#a78bfa', padding: '0.1rem 0.35rem', borderRadius: '4px', background: 'rgba(167,139,250,0.12)' }}>
            {entry.sector}
          </span>
        )}
        {entry.harness_score != null && entry.harness_score > 0 && (
          <span style={{ fontSize: '0.72rem', color: '#f59e0b', fontWeight: 700 }}>
            ★{entry.harness_score}
          </span>
        )}
        <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--color-muted)' }}>
          {fmtTime(entry.timestamp)}
        </span>
      </div>

      {/* 선정 사유 */}
      {entry.selection_reason && (
        <div style={{
          fontSize: '0.79rem',
          color: 'var(--color-text)',
          background: 'rgba(167,139,250,0.07)',
          borderRadius: '6px',
          padding: '0.4rem 0.6rem',
          borderLeft: '2px solid #a78bfa',
        }}>
          <span style={{ fontSize: '0.68rem', fontWeight: 700, color: '#a78bfa', marginRight: '0.4rem' }}>선정 사유</span>
          {entry.selection_reason}
        </div>
      )}

      {/* 거래 상세 */}
      {(entry.type === 'trade_entry' || entry.type === 'trade_exit') && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', fontSize: '0.82rem' }}>
          {entry.shares != null && entry.price != null && (
            <span>{entry.shares}주 @ ${entry.price.toLocaleString()}</span>
          )}
          {entry.position_value != null && (
            <span style={{ color: 'var(--color-muted)' }}>
              ${entry.position_value.toLocaleString()}
            </span>
          )}
          {entry.stop_loss != null && (
            <span style={{ color: '#ef4444' }}>손절 ${entry.stop_loss}</span>
          )}
          {entry.atr != null && (
            <span style={{ color: 'var(--color-muted)' }}>ATR {entry.atr}</span>
          )}
          {entry.type === 'trade_exit' && entry.exit_reason && (
            <span style={{ color: 'var(--color-muted)' }}>
              {entry.exit_reason === 'stop_loss' ? '🛑 손절' :
               entry.exit_reason.startsWith('exit_signal') ? '📉 청산신호' : entry.exit_reason}
            </span>
          )}
        </div>
      )}

      {/* PnL */}
      {entry.type === 'trade_exit' && <PnlChip pnl={entry.pnl} pnl_pct={entry.pnl_pct} />}

      {/* 신호 스캔 */}
      {entry.type === 'signal_scan' && (
        <div style={{ fontSize: '0.82rem', color: 'var(--color-muted)' }}>
          {entry.scanned_count}종목 스캔 — 브레이크아웃 {entry.breakout_count}건
        </div>
      )}

      {/* 리서치 업데이트 */}
      {entry.type === 'research_update' && (
        <div style={{ fontSize: '0.82rem' }}>
          {entry.summary && <div>{entry.summary}</div>}
          {entry.new_tickers && entry.new_tickers.length > 0 && (
            <div style={{ color: 'var(--color-muted)', marginTop: '0.25rem' }}>
              신규: {entry.new_tickers.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* 메모/노트 */}
      {entry.note && (
        <div style={{
          fontSize: '0.82rem',
          color: 'var(--color-text)',
          background: 'var(--color-bg)',
          borderRadius: '6px',
          padding: '0.4rem 0.6rem',
          borderLeft: '2px solid var(--color-border)',
          wordBreak: 'break-word',
        }}>
          {entry.note}
        </div>
      )}

      {/* 태그 */}
      {entry.tags && entry.tags.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
          {entry.tags.map(tag => (
            <span key={tag} style={{
              fontSize: '0.7rem', padding: '0.1rem 0.4rem',
              borderRadius: '4px', background: 'var(--color-border)',
              color: 'var(--color-muted)',
            }}>#{tag}</span>
          ))}
        </div>
      )}
    </div>
  )
}

export function TradingDiaryPage({ apiBase, authHeaders }: Props) {
  const [entries, setEntries] = useState<DiaryEntry[]>([])
  const [stats, setStats] = useState<DiaryStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<string>('all')
  const [tickerFilter, setTickerFilter] = useState('')
  const [note, setNote] = useState('')
  const [noteTicker, setNoteTicker] = useState('')
  const [noteLoading, setNoteLoading] = useState(false)
  const [error, setError] = useState('')
  const noteRef = useRef<HTMLTextAreaElement>(null)

  const fetchDiary = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ limit: '200' })
      if (filter !== 'all') params.set('entry_type', filter)
      if (tickerFilter.trim()) params.set('ticker', tickerFilter.trim().toUpperCase())
      const res = await fetch(`${apiBase}/api/trading/diary?${params}`, { headers: authHeaders })
      if (!res.ok) throw new Error(`${res.status}`)
      const data = await res.json()
      setEntries(data.entries ?? [])
      setStats(data.stats ?? null)
    } catch (e) {
      setError('일기 로드 실패: ' + String(e))
    } finally {
      setLoading(false)
    }
  }, [apiBase, authHeaders, filter, tickerFilter])

  useEffect(() => { fetchDiary() }, [fetchDiary])

  const handleAddNote = async () => {
    if (!note.trim()) return
    setNoteLoading(true)
    try {
      await fetch(`${apiBase}/api/trading/diary/note`, {
        method: 'POST',
        headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ note: note.trim(), ticker: noteTicker.trim().toUpperCase() }),
      })
      setNote('')
      setNoteTicker('')
      fetchDiary()
    } catch {
      // 실패해도 계속
    } finally {
      setNoteLoading(false)
    }
  }

  // 날짜별 그룹화
  const grouped: Record<string, DiaryEntry[]> = {}
  for (const e of entries) {
    const key = fmtDate(e.timestamp)
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(e)
  }

  const FILTERS = [
    { key: 'all',            label: '전체' },
    { key: 'trade_entry',    label: '매수' },
    { key: 'trade_exit',     label: '매도' },
    { key: 'ceo_note',       label: '메모' },
    { key: 'signal_scan',    label: '스캔' },
    { key: 'research_update',label: '리서치' },
  ]

  return (
    <div style={{ maxWidth: 700, margin: '0 auto', padding: '1rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>

      {/* 헤더 */}
      <div>
        <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700 }}>투자 일기장</h2>
        <p style={{ margin: '0.2rem 0 0', fontSize: '0.82rem', color: 'var(--color-muted)' }}>
          매수·매도·리서치 기록이 자동 누적됩니다. 메모를 직접 추가할 수 있습니다.
        </p>
      </div>

      {/* 성과 요약 카드 */}
      {stats && (
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.6rem',
        }}>
          {[
            { label: '총 기록', value: stats.total_entries + '건' },
            { label: '완료 거래', value: stats.closed_trades + '건' },
            { label: '승률', value: stats.win_rate_pct + '%', color: stats.win_rate_pct >= 50 ? '#22c55e' : '#ef4444' },
            { label: '누적 손익', value: (stats.total_pnl >= 0 ? '+' : '') + stats.total_pnl.toLocaleString('en-US', { style: 'currency', currency: 'USD' }), color: stats.total_pnl >= 0 ? '#22c55e' : '#ef4444' },
          ].map(item => (
            <div key={item.label} style={{
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: '10px',
              padding: '0.7rem 0.9rem',
            }}>
              <div style={{ fontSize: '0.73rem', color: 'var(--color-muted)', marginBottom: '0.2rem' }}>{item.label}</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: item.color ?? 'var(--color-text)' }}>{item.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* 메모 입력 */}
      <div style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: '10px',
        padding: '0.9rem 1rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.6rem',
      }}>
        <div style={{ fontSize: '0.82rem', fontWeight: 600 }}>CEO 메모 추가</div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            placeholder="티커 (선택)"
            value={noteTicker}
            onChange={e => setNoteTicker(e.target.value)}
            style={{
              width: '90px', padding: '0.45rem 0.6rem', borderRadius: '6px',
              border: '1px solid var(--color-border)', background: 'var(--color-bg)',
              color: 'var(--color-text)', fontSize: '0.82rem',
            }}
          />
          <textarea
            ref={noteRef}
            placeholder="투자 판단 근거, 시장 관찰, 아이디어..."
            value={note}
            onChange={e => setNote(e.target.value)}
            rows={2}
            style={{
              flex: 1, padding: '0.45rem 0.6rem', borderRadius: '6px',
              border: '1px solid var(--color-border)', background: 'var(--color-bg)',
              color: 'var(--color-text)', fontSize: '0.82rem', resize: 'vertical',
            }}
          />
        </div>
        <button
          onClick={handleAddNote}
          disabled={noteLoading || !note.trim()}
          style={{
            alignSelf: 'flex-end',
            padding: '0.45rem 1.1rem',
            borderRadius: '6px',
            border: 'none',
            background: note.trim() ? 'var(--color-accent)' : 'var(--color-border)',
            color: note.trim() ? '#fff' : 'var(--color-muted)',
            fontWeight: 600,
            fontSize: '0.82rem',
            cursor: note.trim() ? 'pointer' : 'default',
          }}
        >
          {noteLoading ? '저장 중...' : '기록'}
        </button>
      </div>

      {/* 필터 바 */}
      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              padding: '0.3rem 0.75rem',
              borderRadius: '999px',
              border: '1px solid var(--color-border)',
              background: filter === f.key ? 'var(--color-accent)' : 'var(--color-surface)',
              color: filter === f.key ? '#fff' : 'var(--color-text)',
              fontSize: '0.78rem',
              fontWeight: filter === f.key ? 700 : 400,
              cursor: 'pointer',
            }}
          >
            {f.label}
          </button>
        ))}
        <input
          type="text"
          placeholder="종목 검색"
          value={tickerFilter}
          onChange={e => setTickerFilter(e.target.value)}
          style={{
            padding: '0.3rem 0.65rem',
            borderRadius: '999px',
            border: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
            color: 'var(--color-text)',
            fontSize: '0.78rem',
            width: '90px',
          }}
        />
        <button
          onClick={fetchDiary}
          style={{
            marginLeft: 'auto',
            padding: '0.3rem 0.75rem',
            borderRadius: '999px',
            border: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
            color: 'var(--color-muted)',
            fontSize: '0.75rem',
            cursor: 'pointer',
          }}
        >
          {loading ? '로딩...' : '↻'}
        </button>
      </div>

      {/* 에러 */}
      {error && (
        <div style={{ color: '#ef4444', fontSize: '0.82rem', padding: '0.5rem 0.75rem', background: 'rgba(239,68,68,0.1)', borderRadius: '6px' }}>
          {error}
        </div>
      )}

      {/* 빈 상태 */}
      {!loading && entries.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '3rem 1rem',
          color: 'var(--color-muted)', fontSize: '0.9rem',
        }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📒</div>
          <div>아직 기록이 없습니다.</div>
          <div style={{ fontSize: '0.8rem', marginTop: '0.3rem' }}>
            매수/매도 시 자동으로 기록됩니다.
          </div>
        </div>
      )}

      {/* 날짜별 그룹 */}
      {Object.entries(grouped).map(([date, dayEntries]) => (
        <div key={date} style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <div style={{
            fontSize: '0.75rem', fontWeight: 700,
            color: 'var(--color-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            paddingBottom: '0.25rem',
            borderBottom: '1px solid var(--color-border)',
          }}>
            {date}
          </div>
          {dayEntries.map(e => <EntryCard key={e.id} entry={e} />)}
        </div>
      ))}
    </div>
  )
}
