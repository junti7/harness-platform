import { useCallback, useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { MeetingNoteDetail, MeetingNotesPayload } from '../components/types'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
  initialSelectedId?: string | null
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function formatUsd(value?: number | null): string {
  if (typeof value !== 'number') return '-'
  return `$${value.toFixed(2)}`
}

function normalizeHeading(value: string): string {
  return value.replace(/[\s()·—\-_/]+/g, '').toLowerCase()
}

function parseSections(markdown?: string | null): Record<string, string> {
  const text = (markdown ?? '').trim()
  if (!text) return {}
  const sections: Record<string, string[]> = { body: [] }
  let current = 'body'
  for (const rawLine of text.split('\n')) {
    const match = rawLine.match(/^\s*##\s+(.+?)\s*$/)
    if (match) {
      current = match[1].trim()
      sections[current] = sections[current] ?? []
      continue
    }
    sections[current].push(rawLine)
  }
  return Object.fromEntries(Object.entries(sections).map(([key, lines]) => [key, lines.join('\n').trim()]))
}

function findSection(sections: Record<string, string>, ...needles: string[]): string {
  const normalizedNeedles = needles.map(normalizeHeading)
  for (const [key, value] of Object.entries(sections)) {
    const normalizedKey = normalizeHeading(key)
    if (normalizedNeedles.some(needle => normalizedKey.includes(needle))) return value
  }
  return ''
}

function cleanInline(value: string): string {
  return value.replace(/\*\*/g, '').replace(/\*/g, '').replace(/\s+/g, ' ').trim()
}

function extractBullets(sectionText: string, limit = 10): string[] {
  const items: string[] = []
  for (const raw of sectionText.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    if ((line.startsWith('- ') || line.startsWith('* ')) && line.length > 2) {
      items.push(cleanInline(line.slice(2)).slice(0, 320))
    }
    if (items.length >= limit) break
  }
  return items
}

function extractNumbered(sectionText: string, limit = 10): string[] {
  const items: string[] = []
  let buffer: string[] = []
  for (const raw of sectionText.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    const match = line.match(/^\d+\.\s+(.*)$/)
    if (match) {
      if (buffer.length) items.push(cleanInline(buffer.join(' ')).slice(0, 320))
      buffer = [match[1]]
      continue
    }
    if (buffer.length && !/^[-*]\s+/.test(line)) {
      buffer.push(line)
    }
  }
  if (buffer.length) items.push(cleanInline(buffer.join(' ')).slice(0, 320))
  return items.slice(0, limit)
}

function extractTableRows(sectionText: string, limit = 10, skipHeaders: string[] = []): string[] {
  const rows: string[] = []
  const normalizedHeaders = new Set(skipHeaders.map(header => header.toLowerCase()))
  for (const raw of sectionText.split('\n')) {
    const line = raw.trim()
    if (!(line.startsWith('|') && line.endsWith('|'))) continue
    if (/\|\s*-+\s*\|/.test(line)) continue
    const cells = line
      .slice(1, -1)
      .split('|')
      .map(cell => cleanInline(cell))
      .filter(Boolean)
    if (cells.length < 2) continue
    if (normalizedHeaders.has(cells[0].toLowerCase())) continue
    const row = cells.length >= 3 ? `${cells[0]} — ${cells[1]}: ${cells[2]}` : `${cells[0]} — ${cells[1]}`
    rows.push(row.slice(0, 360))
    if (rows.length >= limit) break
  }
  return rows
}

function extractHybrid(sectionText: string, limit = 10, skipHeaders: string[] = []): string[] {
  const bullets = extractBullets(sectionText, limit)
  if (bullets.length) return bullets
  const numbered = extractNumbered(sectionText, limit)
  if (numbered.length) return numbered
  const tableRows = extractTableRows(sectionText, limit, skipHeaders)
  if (tableRows.length) return tableRows
  const fallback = sectionText
    .split('\n')
    .map(line => cleanInline(line))
    .filter(Boolean)
    .filter(line => !line.startsWith('##'))
    .slice(0, limit)
    .map(line => line.slice(0, 320))
  return fallback
}

function buildMeetingDigest(markdown?: string | null) {
  const sections = parseSections(markdown)
  const summary = cleanInline(findSection(sections, '한줄요약', '요약')).slice(0, 360)
  const consensus = extractHybrid(findSection(sections, '합의된점', 'consensus'), 8, ['항목'])
  const dissent = extractHybrid(findSection(sections, '미합의', '이견', 'dissent'), 8, ['항목'])
  const actions = extractHybrid(findSection(sections, '권고액션', 'recommendedactions', '즉시수행지시'), 8, ['AR', '#'])
  const requests = extractHybrid(findSection(sections, '대표님결재요청사항', 'ceo결정요청사항', '결재요청사항'), 6, ['항목'])
  const gates = extractTableRows(findSection(sections, '막힌게이트', 'blockedgates', 'gatesblocking'), 8, ['게이트', 'gate'])
  return { summary, consensus, dissent, actions, requests, gates }
}

function MarkdownSurface({ markdown }: { markdown?: string | null }) {
  const source = (markdown ?? '').trim()
  if (!source) {
    return <div className="meeting-note-muted">기록 없음</div>
  }

  return (
    <div className="meeting-note-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="meeting-md-h1">{children}</h1>,
          h2: ({ children }) => <h2 className="meeting-md-h2">{children}</h2>,
          h3: ({ children }) => <h3 className="meeting-md-h3">{children}</h3>,
          p: ({ children }) => <p className="meeting-md-p">{children}</p>,
          ul: ({ children }) => <ul className="meeting-md-ul">{children}</ul>,
          ol: ({ children }) => <ol className="meeting-md-ol">{children}</ol>,
          li: ({ children }) => <li className="meeting-md-li">{children}</li>,
          hr: () => <hr className="meeting-md-hr" />,
          blockquote: ({ children }) => <blockquote className="meeting-md-blockquote">{children}</blockquote>,
          table: ({ children }) => (
            <div className="meeting-md-table-wrap">
              <table className="meeting-md-table">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="meeting-md-thead">{children}</thead>,
          tbody: ({ children }) => <tbody className="meeting-md-tbody">{children}</tbody>,
          tr: ({ children }) => <tr className="meeting-md-tr">{children}</tr>,
          th: ({ children }) => <th className="meeting-md-th">{children}</th>,
          td: ({ children }) => <td className="meeting-md-td">{children}</td>,
          code: ({ children, className }) =>
            className ? (
              <code className="meeting-md-codeblock">{children}</code>
            ) : (
              <code className="meeting-md-code">{children}</code>
            ),
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  )
}

export function MeetingNotesPage({ apiBase, authHeaders, initialSelectedId }: Props) {
  const [payload, setPayload] = useState<MeetingNotesPayload | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<MeetingNoteDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadMeetingNotes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/meeting-notes`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`회의록 API ${res.status}`)
      const nextPayload = (await res.json()) as MeetingNotesPayload
      setPayload(nextPayload)
      setSelectedId(current => current ?? nextPayload.items[0]?.id ?? null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '회의록 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [apiBase, authHeaders])

  const loadDetail = useCallback(async (id: string | null) => {
    if (!id) {
      setDetail(null)
      return
    }
    setDetailLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/meeting-notes/${id}`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`회의록 상세 API ${res.status}`)
      const nextDetail = (await res.json()) as MeetingNoteDetail
      setDetail(nextDetail)
    } catch (err) {
      setError(err instanceof Error ? err.message : '회의록 상세 로드 실패')
    } finally {
      setDetailLoading(false)
    }
  }, [apiBase, authHeaders])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadMeetingNotes()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [loadMeetingNotes])

  useEffect(() => {
    if (!initialSelectedId) return
    const timer = window.setTimeout(() => {
      setSelectedId(initialSelectedId)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [initialSelectedId])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDetail(selectedId)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [loadDetail, selectedId])

  const emptyLabel = useMemo(() => '저장된 회의록이 없습니다.', [])
  const digest = useMemo(() => buildMeetingDigest(detail?.decision), [detail?.decision])

  return (
    <section className="meeting-notes-page">
      <article className="panel meeting-notes-shell">
        <div className="panel-head meeting-notes-head">
          <div>
            <h2 style={{ margin: 0 }}>회의록</h2>
            <p className="subtitle meeting-notes-subtitle">
              `#회의실` 회의 결과를 Notion 저장본 기준으로 읽기 좋게 재구성한 내부 열람 화면입니다.
            </p>
            <p className="data-meta" style={{ marginTop: '0.35rem' }}>
              데이터 출처: {payload?.source ?? 'docs/reports/notion_minutes_runs.jsonl'} · 마지막 갱신: {formatDateTime(payload?.updated_at)}
            </p>
          </div>
          <div className="meeting-notes-count">{payload?.total ?? 0}건</div>
        </div>

        {error && (
          <div className="banner banner-error">
            <div className="banner-title">회의록 오류</div>
            <div className="banner-desc">{error}</div>
          </div>
        )}

        <div className="meeting-notes-grid">
          <div className="meeting-notes-list">
            <div className="meeting-notes-list-head">최근 회의록</div>
            {loading ? (
              <div className="meeting-notes-empty">회의록 로드 중…</div>
            ) : payload && payload.items.length > 0 ? (
              <div className="meeting-notes-items">
                {payload.items.map(item => (
                  <button
                    key={item.id}
                    type="button"
                    className={`meeting-note-row ${selectedId === item.id ? 'active' : ''}`}
                    onClick={() => setSelectedId(item.id)}
                  >
                    <div className="meeting-note-row-title">{item.title}</div>
                    {item.summary && <div className="meeting-note-row-summary">{item.summary}</div>}
                    <div className="meeting-note-row-meta">{formatDateTime(item.recorded_at)}</div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="meeting-notes-empty">{emptyLabel}</div>
            )}
          </div>

          <div className="panel meeting-notes-detail">
            {detailLoading ? (
              <div className="meeting-notes-empty">회의록 상세 로드 중…</div>
            ) : detail ? (
              <div className="meeting-note-detail-content">
                <div className="meeting-note-header">
                  <div>
                    <h3 className="meeting-note-title">{detail.title}</h3>
                    <div className="meeting-note-meta-line">
                      <span>{formatDateTime(detail.recorded_at)}</span>
                      <span>{detail.id}</span>
                    </div>
                  </div>
                  {detail.notion_url && (
                    <a className="meeting-note-link" href={detail.notion_url} target="_blank" rel="noreferrer">
                      Notion 원문 열기
                    </a>
                  )}
                </div>

                <div className="meeting-note-participants">
                  {detail.participants.map(persona => (
                    <span key={persona} className="meeting-note-participant">
                      {persona}
                    </span>
                  ))}
                </div>

                <div className="meeting-note-stats">
                  <div className="meeting-note-stat">
                    <span className="meeting-note-stat-label">라운드</span>
                    <strong>{detail.rounds ?? '-'}</strong>
                  </div>
                  <div className="meeting-note-stat">
                    <span className="meeting-note-stat-label">턴 수</span>
                    <strong>{detail.turns ?? '-'}</strong>
                  </div>
                  <div className="meeting-note-stat">
                    <span className="meeting-note-stat-label">LLM 호출</span>
                    <strong>{detail.llm_calls ?? '-'}</strong>
                  </div>
                  <div className="meeting-note-stat">
                    <span className="meeting-note-stat-label">추정 비용</span>
                    <strong>{formatUsd(detail.estimated_cost_usd)}</strong>
                  </div>
                </div>

                {digest.summary && (
                  <section className="meeting-note-summary-card">
                    <div className="meeting-note-section-label">핵심 요약</div>
                    <div className="meeting-note-summary-text">{digest.summary}</div>
                  </section>
                )}

                <div className="meeting-note-insight-grid">
                  <section className="meeting-note-insight-card">
                    <div className="meeting-note-section-label">합의된 핵심</div>
                    {digest.consensus.length > 0 ? (
                      <ul className="meeting-note-list-block">
                        {digest.consensus.map(item => <li key={item}>{item}</li>)}
                      </ul>
                    ) : (
                      <div className="meeting-note-muted">추출된 합의 사항이 없습니다.</div>
                    )}
                  </section>

                  <section className="meeting-note-insight-card">
                    <div className="meeting-note-section-label">미합의 / 이견</div>
                    {digest.dissent.length > 0 ? (
                      <ul className="meeting-note-list-block">
                        {digest.dissent.map(item => <li key={item}>{item}</li>)}
                      </ul>
                    ) : (
                      <div className="meeting-note-muted">명시된 이견이 없습니다.</div>
                    )}
                  </section>

                  <section className="meeting-note-insight-card">
                    <div className="meeting-note-section-label">즉시 액션</div>
                    {digest.actions.length > 0 ? (
                      <ol className="meeting-note-list-block ordered">
                        {digest.actions.map(item => <li key={item}>{item}</li>)}
                      </ol>
                    ) : (
                      <div className="meeting-note-muted">추출된 액션이 없습니다.</div>
                    )}
                  </section>

                  <section className="meeting-note-insight-card">
                    <div className="meeting-note-section-label">대표 확인 필요 사항</div>
                    {digest.requests.length > 0 ? (
                      <ul className="meeting-note-list-block">
                        {digest.requests.map(item => <li key={item}>{item}</li>)}
                      </ul>
                    ) : (
                      <div className="meeting-note-muted">별도 확인 요청이 없습니다.</div>
                    )}
                  </section>
                </div>

                <section className="meeting-note-section">
                  <div className="meeting-note-section-label">막힌 게이트</div>
                  {digest.gates.length > 0 ? (
                    <div className="meeting-note-gates">
                      {digest.gates.map(item => (
                        <div key={item} className="meeting-note-gate-row">{item}</div>
                      ))}
                    </div>
                  ) : (
                    <div className="meeting-note-muted">명시된 게이트 차단 사항이 없습니다.</div>
                  )}
                </section>

                <section className="meeting-note-section">
                  <div className="meeting-note-section-label">회의 지시 원문</div>
                  <div className="meeting-note-prose">
                    <MarkdownSurface markdown={detail.order} />
                  </div>
                </section>

                <section className="meeting-note-section">
                  <div className="meeting-note-section-label">원문 회의 결과</div>
                  <div className="meeting-note-prose">
                    <MarkdownSurface markdown={detail.decision} />
                  </div>
                </section>
              </div>
            ) : (
              <div className="meeting-notes-empty">좌측 목록에서 회의록을 선택하세요.</div>
            )}
          </div>
        </div>
      </article>
    </section>
  )
}
