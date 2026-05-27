import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ConferenceRoomDetail, ConferenceRoomPayload } from '../components/types'

const CONFERENCE_READ_STATE_KEY = 'harness-conference-read-state'
const CONFERENCE_PIN_STATE_KEY = 'harness-conference-pinned-state'
const CONFERENCE_PIN_PRIORITY_KEY = 'harness-conference-pin-priority'

const MEETING_TEMPLATES = [
  {
    id: 'decision',
    label: '대표 결정 논의',
    text:
      '[대표결정] 새 의제입니다.\n\n1. 논의 배경\n2. 각 팀이 답해야 할 질문\n3. 오늘 결론 내릴 항목\n4. 막힌 게이트 / 선행조건\n5. 대표 확인 필요 사항',
  },
  {
    id: 'risk',
    label: '리스크 점검 회의',
    text:
      '[리스크점검] 긴급 점검 의제입니다.\n\n1. 현재 리스크 요약\n2. 발생 확률 / 영향도\n3. 즉시 완화 조치\n4. Kill criteria 해당 여부\n5. 대표 승인 필요 액션',
  },
  {
    id: 'invest',
    label: '투자결정 소집',
    text:
      '[투자결정] 투자 판단 회의 소집입니다.\n\n1. Thesis\n2. Trigger\n3. Invalidation\n4. Position sizing / stress test\n5. legal_review / red_team / pre_mortem 상태',
  },
]

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
  viewRole: 'ceo' | 'vp'
  actorDisplay: string
}

const PERSONA_COLORS: Record<string, { bg: string; fg: string }> = {
  jarvis: { bg: 'rgba(37, 99, 235, 0.14)', fg: '#60a5fa' },
  kitt: { bg: 'rgba(234, 88, 12, 0.14)', fg: '#fb923c' },
  watchman: { bg: 'rgba(220, 38, 38, 0.14)', fg: '#f87171' },
  ledger: { bg: 'rgba(5, 150, 105, 0.14)', fg: '#34d399' },
  vision: { bg: 'rgba(124, 58, 237, 0.14)', fg: '#a78bfa' },
  tars: { bg: 'rgba(14, 165, 233, 0.14)', fg: '#38bdf8' },
  friday: { bg: 'rgba(217, 119, 6, 0.14)', fg: '#fbbf24' },
  c3po: { bg: 'rgba(217, 119, 6, 0.14)', fg: '#f59e0b' },
  coach: { bg: 'rgba(16, 185, 129, 0.14)', fg: '#6ee7b7' },
  ceo: { bg: 'rgba(37, 99, 235, 0.16)', fg: '#93c5fd' },
  vp: { bg: 'rgba(236, 72, 153, 0.14)', fg: '#f9a8d4' },
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function timestampValue(value?: string | null): number {
  if (!value) return 0
  const parsed = new Date(value).getTime()
  return Number.isFinite(parsed) ? parsed : 0
}

function personaSlug(author?: string | null): string {
  if (!author) return 'participant'
  const base = author.split('(')[0]?.trim().toLowerCase() ?? ''
  return base || 'participant'
}

function personaInitials(author?: string | null): string {
  const slug = personaSlug(author)
  if (slug === 'participant') return '??'
  return slug.replace(/[^a-z0-9]/g, '').slice(0, 2).toUpperCase()
}

function personaMeta(author?: string | null): { title: string; subtitle: string; bg: string; fg: string } {
  const title = author?.split('(')[0]?.trim() || 'Participant'
  const subtitle = author?.includes('(') ? author.slice(author.indexOf('(') + 1, author.lastIndexOf(')')) : '참여자'
  const palette = PERSONA_COLORS[personaSlug(author)] ?? { bg: 'rgba(148, 163, 184, 0.14)', fg: '#cbd5e1' }
  return { title, subtitle, bg: palette.bg, fg: palette.fg }
}

function isImportantThread(item: ConferenceRoomPayload['items'][number]): boolean {
  const title = (item.title || '').toLowerCase()
  return Boolean(
    item.linked_note?.id ||
    item.correlation_id ||
    title.includes('decision card') ||
    title.includes('결재') ||
    title.includes('대표')
  )
}

function isDecisionThread(item: ConferenceRoomPayload['items'][number]): boolean {
  const blob = [item.title, item.preview, item.correlation_id].filter(Boolean).join(' ').toLowerCase()
  return (
    blob.includes('[대표결정]') ||
    blob.includes('[투자결정]') ||
    blob.includes('대표결정') ||
    blob.includes('투자결정') ||
    blob.includes('결재') ||
    blob.includes('decision card')
  )
}

function isSystemNoiseThread(item: ConferenceRoomPayload['items'][number]): boolean {
  const blob = [item.title, item.preview, item.author_display].filter(Boolean).join(' ').toLowerCase()
  return (
    blob.includes('호출 실패') ||
    blob.includes('command [') ||
    blob.includes('timed out after') ||
    blob.includes('tool call') ||
    blob.includes('invalid_arguments')
  )
}

function shouldCollapseMessage(markdown?: string | null): boolean {
  if (!markdown) return false
  const lines = markdown.split('\n').length
  return markdown.length > 520 || lines > 9
}

function TeamAvatarGlyph({ author }: { author?: string | null }) {
  const slug = personaSlug(author)
  const stroke = 'currentColor'

  switch (slug) {
    case 'jarvis':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="6" y="7" width="12" height="10" rx="3" fill="none" stroke={stroke} strokeWidth="1.7" />
          <path d="M9 17v2m6-2v2M9 11h6M12 4v3" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
          <circle cx="10" cy="11" r="1" fill={stroke} />
          <circle cx="14" cy="11" r="1" fill={stroke} />
        </svg>
      )
    case 'kitt':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M8 6h8l2 3v8H6V9l2-3Z" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M9.5 9.5h5M9 13h6" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      )
    case 'watchman':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 4l7 3v5c0 4.4-2.9 6.9-7 8-4.1-1.1-7-3.6-7-8V7l7-3Z" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinejoin="round" />
          <path d="m9.5 12 1.6 1.6 3.7-3.7" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    case 'ledger':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="6" y="5" width="12" height="14" rx="2.5" fill="none" stroke={stroke} strokeWidth="1.7" />
          <path d="M9 9h6M9 12h6M9 15h3" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      )
    case 'vision':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M3.5 12s3-5 8.5-5 8.5 5 8.5 5-3 5-8.5 5-8.5-5-8.5-5Z" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinejoin="round" />
          <circle cx="12" cy="12" r="2.4" fill="none" stroke={stroke} strokeWidth="1.7" />
        </svg>
      )
    case 'tars':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 6h12v12H6z" fill="none" stroke={stroke} strokeWidth="1.7" />
          <path d="M12 6v12M6 12h12" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      )
    case 'friday':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 4v8l4 2" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
          <circle cx="12" cy="12" r="7.5" fill="none" stroke={stroke} strokeWidth="1.7" />
        </svg>
      )
    case 'scribe':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M7 5h7l3 3v11H7z" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M14 5v4h4M9 12h6M9 15h4" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      )
    case 'c3po':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="8" r="3" fill="none" stroke={stroke} strokeWidth="1.7" />
          <path d="M7 18c1.3-2.6 3-4 5-4s3.7 1.4 5 4" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      )
    case 'coach':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M6 18V8l6-3 6 3v10" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinejoin="round" />
          <path d="M9 18v-4h6v4" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    case 'ceo':
    case 'vp':
      return (
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M12 5l2.2 4.4 4.8.7-3.5 3.4.8 4.8-4.3-2.3-4.3 2.3.8-4.8-3.5-3.4 4.8-.7Z" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinejoin="round" />
        </svg>
      )
    default:
      return <span className="conference-avatar-fallback">{personaInitials(author)}</span>
  }
}

function TeamAvatar({
  author,
  variant = 'thread',
}: {
  author?: string | null
  variant?: 'thread' | 'message' | 'chip'
}) {
  const persona = personaMeta(author)
  return (
    <span
      className={`conference-avatar conference-avatar-${variant} conference-avatar-shell`}
      style={
        {
          '--avatar-bg': persona.bg,
          '--avatar-fg': persona.fg,
        } as CSSProperties
      }
      aria-hidden="true"
    >
      <span className="conference-avatar-core">
        <TeamAvatarGlyph author={author} />
      </span>
    </span>
  )
}

function MarkdownMessage({ markdown, collapsed = false }: { markdown: string; collapsed?: boolean }) {
  return (
    <div className={`conference-message-markdown ${collapsed ? 'collapsed' : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="conference-md-p">{children}</p>,
          ul: ({ children }) => <ul className="conference-md-ul">{children}</ul>,
          ol: ({ children }) => <ol className="conference-md-ol">{children}</ol>,
          li: ({ children }) => <li className="conference-md-li">{children}</li>,
          h1: ({ children }) => <h1 className="conference-md-h1">{children}</h1>,
          h2: ({ children }) => <h2 className="conference-md-h2">{children}</h2>,
          h3: ({ children }) => <h3 className="conference-md-h3">{children}</h3>,
          blockquote: ({ children }) => <blockquote className="conference-md-quote">{children}</blockquote>,
          table: ({ children }) => <div className="conference-md-table-wrap"><table className="conference-md-table">{children}</table></div>,
          thead: ({ children }) => <thead className="conference-md-thead">{children}</thead>,
          tbody: ({ children }) => <tbody>{children}</tbody>,
          tr: ({ children }) => <tr className="conference-md-tr">{children}</tr>,
          th: ({ children }) => <th className="conference-md-th">{children}</th>,
          td: ({ children }) => <td className="conference-md-td">{children}</td>,
          code: ({ children, className }) => className ? <code className="conference-md-codeblock">{children}</code> : <code className="conference-md-code">{children}</code>,
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  )
}

export function ConferenceRoomPage({ apiBase, authHeaders, viewRole, actorDisplay }: Props) {
  const [payload, setPayload] = useState<ConferenceRoomPayload | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<ConferenceRoomDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [posting, setPosting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [composeMode, setComposeMode] = useState<'reply' | 'root'>('reply')
  const [draft, setDraft] = useState('')
  const [pinState, setPinState] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem(CONFERENCE_PIN_STATE_KEY)
      return raw ? JSON.parse(raw) as Record<string, boolean> : {}
    } catch {
      return {}
    }
  })
  const [pinPriority, setPinPriority] = useState<Record<string, number>>(() => {
    try {
      const raw = localStorage.getItem(CONFERENCE_PIN_PRIORITY_KEY)
      return raw ? JSON.parse(raw) as Record<string, number> : {}
    } catch {
      return {}
    }
  })
  const [searchQuery, setSearchQuery] = useState('')
  const [participantFilter, setParticipantFilter] = useState<string>('all')
  const [threadView, setThreadView] = useState<'priority' | 'decision' | 'general' | 'system'>('priority')
  const [backgroundRefreshing, setBackgroundRefreshing] = useState(false)
  const [mobilePane, setMobilePane] = useState<'list' | 'thread'>('list')
  const [expandedMessages, setExpandedMessages] = useState<Record<string, boolean>>({})
  const [startMode, setStartMode] = useState<'direct' | 'cos_request' | null>(null)
  const [startSubmitting, setStartSubmitting] = useState(false)
  const [endingMeeting, setEndingMeeting] = useState(false)
  const [startTitle, setStartTitle] = useState('')
  const [startAgenda, setStartAgenda] = useState('')
  const [startParticipants, setStartParticipants] = useState<string[]>([])
  const [readState, setReadState] = useState<Record<string, number>>(() => {
    try {
      const raw = localStorage.getItem(CONFERENCE_READ_STATE_KEY)
      return raw ? JSON.parse(raw) as Record<string, number> : {}
    } catch {
      return {}
    }
  })

  const loadRoom = async (preserveSelection = true, silent = false) => {
    if (!silent || !payload) {
      setLoading(true)
    } else {
      setBackgroundRefreshing(true)
    }
    if (!silent) {
      setError(null)
    }
    try {
      const res = await fetch(`${apiBase}/api/conference-room`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`회의실 API ${res.status}`)
      const nextPayload = (await res.json()) as ConferenceRoomPayload
      setPayload(nextPayload)
      setSelectedId(current => {
        if (preserveSelection && current && nextPayload.items.some(item => item.id === current)) return current
        return nextPayload.items[0]?.id ?? null
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : '회의실 로드 실패')
    } finally {
      setLoading(false)
      setBackgroundRefreshing(false)
    }
  }

  const loadDetail = async (id: string | null) => {
    if (!id) {
      setDetail(null)
      return
    }
    setDetailLoading(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/conference-room/${encodeURIComponent(id)}`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`회의실 상세 API ${res.status}`)
      const nextDetail = (await res.json()) as ConferenceRoomDetail
      setDetail(nextDetail)
    } catch (err) {
      setError(err instanceof Error ? err.message : '회의실 상세 로드 실패')
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    const initial = window.setTimeout(() => {
      void loadRoom(false)
    }, 0)
    const timer = setInterval(() => {
      void loadRoom(true, true)
    }, 15000)
    return () => {
      window.clearTimeout(initial)
      clearInterval(timer)
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDetail(selectedId)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [selectedId])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (!selectedId) setComposeMode('root')
    }, 0)
    return () => window.clearTimeout(timer)
  }, [selectedId])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (selectedId) {
        setMobilePane('thread')
      }
    }, 0)
    return () => window.clearTimeout(timer)
  }, [selectedId])

  const togglePinned = (itemId: string) => {
    const currentlyPinned = Boolean(pinState[itemId])
    setPinState(current => {
      const next = { ...current, [itemId]: !currentlyPinned }
      localStorage.setItem(CONFERENCE_PIN_STATE_KEY, JSON.stringify(next))
      return next
    })
    setPinPriority(current => {
      const next = { ...current }
      if (currentlyPinned) {
        delete next[itemId]
      } else if (!next[itemId]) {
        next[itemId] = 2
      }
      localStorage.setItem(CONFERENCE_PIN_PRIORITY_KEY, JSON.stringify(next))
      return next
    })
  }

  const setPinnedPriority = (itemId: string, priority: number) => {
    setPinState(current => {
      const next = { ...current, [itemId]: true }
      localStorage.setItem(CONFERENCE_PIN_STATE_KEY, JSON.stringify(next))
      return next
    })
    setPinPriority(current => {
      const next = { ...current, [itemId]: priority }
      localStorage.setItem(CONFERENCE_PIN_PRIORITY_KEY, JSON.stringify(next))
      return next
    })
  }

  const markAllRead = () => {
    if (!payload?.items?.length) return
    const nowMap = Object.fromEntries(payload.items.map(item => [item.id, timestampValue(item.posted_at) || Date.now()]))
    setReadState(current => {
      const next = { ...current, ...nowMap }
      localStorage.setItem(CONFERENCE_READ_STATE_KEY, JSON.stringify(next))
      return next
    })
  }

  const startTemplate = (text: string) => {
    setComposeMode('root')
    setDraft(text)
  }

  const openStartFlow = (mode: 'direct' | 'cos_request') => {
    setStartMode(mode)
    setStartTitle('')
    setStartAgenda('')
    setStartParticipants([])
  }

  const closeStartFlow = () => {
    setStartMode(null)
    setStartSubmitting(false)
  }

  const toggleStartParticipant = (label: string) => {
    setStartParticipants(current =>
      current.includes(label) ? current.filter(item => item !== label) : [...current, label],
    )
  }

  const endMeeting = async (itemId: string) => {
    if (endingMeeting) return
    if (!confirm('이 회의를 종료하고 내용을 자동 요약할까요?')) return

    setEndingMeeting(true)
    try {
      const res = await fetch(`${apiBase}/api/conference-room/${encodeURIComponent(itemId)}/end`, {
        method: 'POST',
        headers: authHeaders(),
      })
      if (!res.ok) {
        throw new Error('Failed to end meeting')
      }
      
      const newDetail = (await res.json()) as ConferenceRoomDetail
      setDetail(newDetail)
      setPayload(prev => {
        if (!prev) return prev
        return {
          ...prev,
          items: prev.items.map(item => item.id === itemId ? newDetail : item)
        }
      })
    } catch (err) {
      console.error(err)
      alert('회의 종료 중 오류가 발생했습니다.')
    } finally {
      setEndingMeeting(false)
    }
  }

  useEffect(() => {
    if (!selectedId || !payload) return
    const target = payload.items.find(item => item.id === selectedId)
    const nextTimestamp = timestampValue(target?.posted_at) || Date.now()
    const timer = window.setTimeout(() => {
      setReadState(current => {
        if ((current[selectedId] ?? 0) >= nextTimestamp) return current
        const next = { ...current, [selectedId]: nextTimestamp }
        localStorage.setItem(CONFERENCE_READ_STATE_KEY, JSON.stringify(next))
        return next
      })
    }, 0)
    return () => window.clearTimeout(timer)
  }, [selectedId, payload])

  const submitMessage = async () => {
    const text = draft.trim()
    if (!text) return
    setPosting(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/conference-room/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({
          text,
          actor_role: viewRole,
          actor_display: actorDisplay,
          parent_ts: composeMode === 'reply' ? selectedId : null,
        }),
      })
      if (!res.ok) throw new Error(`회의실 전송 API ${res.status}`)
      const posted = (await res.json()) as { thread_ts?: string | null; ts?: string | null }
      setDraft('')
      await loadRoom(true)
      if (posted.thread_ts) {
        setSelectedId(posted.thread_ts)
        await loadDetail(posted.thread_ts)
      } else if (posted.ts) {
        setSelectedId(posted.ts)
        await loadDetail(posted.ts)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '회의실 전송 실패')
    } finally {
      setPosting(false)
    }
  }

  const roomEmptyLabel = useMemo(() => '회의실에 표시할 대화가 아직 없습니다.', [])
  const canReply = Boolean(selectedId)
  const participantOptions = useMemo(() => {
    const set = new Set<string>()
    for (const item of payload?.items ?? []) {
      if (item.author_display) set.add(item.author_display)
      for (const participant of item.participants ?? []) {
        if (participant) set.add(participant)
      }
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b, 'ko'))
  }, [payload])

  const filteredItems = useMemo(() => {
    const needle = searchQuery.trim().toLowerCase()
    return (payload?.items ?? []).filter(item => {
      if (participantFilter !== 'all') {
        const participantHit =
          item.author_display === participantFilter ||
          (item.participants ?? []).includes(participantFilter)
        if (!participantHit) return false
      }
      if (!needle) return true
      const haystack = [
        item.title,
        item.preview,
        item.author_display,
        ...(item.participants ?? []),
        item.correlation_id,
        item.linked_note?.title,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
      return haystack.includes(needle)
    })
  }, [payload, participantFilter, searchQuery])

  const importantItems = useMemo(() => filteredItems.filter(isImportantThread), [filteredItems])
  const decisionItems = useMemo(() => filteredItems.filter(isDecisionThread), [filteredItems])
  const systemItems = useMemo(() => filteredItems.filter(isSystemNoiseThread), [filteredItems])
  const regularItems = useMemo(
    () => filteredItems.filter(item => !isImportantThread(item) && !isDecisionThread(item) && !isSystemNoiseThread(item)),
    [filteredItems],
  )

  const sortPinnedItems = (items: ConferenceRoomPayload['items']) =>
    [...items].sort((a, b) => {
      const ap = pinPriority[a.id] ?? 2
      const bp = pinPriority[b.id] ?? 2
      if (ap !== bp) return ap - bp
      return timestampValue(b.posted_at) - timestampValue(a.posted_at)
    })

  const pinnedItems = useMemo(() => sortPinnedItems(filteredItems.filter(item => pinState[item.id])), [filteredItems, pinState, pinPriority])
  const importantUnpinnedItems = useMemo(
    () => importantItems.filter(item => !pinState[item.id] && !isSystemNoiseThread(item)),
    [importantItems, pinState],
  )
  const decisionUnpinnedItems = useMemo(
    () => decisionItems.filter(item => !pinState[item.id] && !isImportantThread(item) && !isSystemNoiseThread(item)),
    [decisionItems, pinState],
  )
  const regularUnpinnedItems = useMemo(
    () => regularItems.filter(item => !pinState[item.id]),
    [regularItems, pinState],
  )
  const systemUnpinnedItems = useMemo(
    () => systemItems.filter(item => !pinState[item.id]),
    [systemItems, pinState],
  )

  const isUnread = (item: ConferenceRoomPayload['items'][number]) => {
    const seenAt = readState[item.id] ?? 0
    const itemAt = timestampValue(item.posted_at)
    return itemAt > seenAt
  }

  const unreadCount = useMemo(() => filteredItems.filter(isUnread).length, [filteredItems, readState])
  const initialLoading = loading && !payload

  const threadTabs = useMemo(
    () => [
      { key: 'priority' as const, label: '중요', count: pinnedItems.length + importantUnpinnedItems.length },
      { key: 'decision' as const, label: '결정', count: decisionUnpinnedItems.length },
      { key: 'general' as const, label: '일반', count: regularUnpinnedItems.length },
      { key: 'system' as const, label: '시스템', count: systemUnpinnedItems.length },
    ],
    [decisionUnpinnedItems.length, importantUnpinnedItems.length, pinnedItems.length, regularUnpinnedItems.length, systemUnpinnedItems.length],
  )

  const visibleSections = useMemo(() => {
    if (threadView === 'priority') {
      return [
        { label: '고정됨', items: pinnedItems },
        { label: '중요 대화', items: importantUnpinnedItems },
      ].filter(section => section.items.length > 0)
    }
    if (threadView === 'decision') {
      return [{ label: '대표/투자/결재 판단', items: decisionUnpinnedItems }].filter(section => section.items.length > 0)
    }
    if (threadView === 'system') {
      return [{ label: '시스템 로그', items: systemUnpinnedItems }].filter(section => section.items.length > 0)
    }
    return [{ label: '일반 대화', items: regularUnpinnedItems }].filter(section => section.items.length > 0)
  }, [decisionUnpinnedItems, importantUnpinnedItems, pinnedItems, regularUnpinnedItems, systemUnpinnedItems, threadView])

  const markThreadRead = (itemId: string, itemAt?: string | null) => {
    const nextTimestamp = timestampValue(itemAt) || 1
    setReadState(current => {
      const next = { ...current, [itemId]: nextTimestamp }
      localStorage.setItem(CONFERENCE_READ_STATE_KEY, JSON.stringify(next))
      return next
    })
  }

  const markThreadUnread = (itemId: string) => {
    setReadState(current => {
      const next = { ...current, [itemId]: 0 }
      localStorage.setItem(CONFERENCE_READ_STATE_KEY, JSON.stringify(next))
      return next
    })
  }

  const toggleMessageExpanded = (messageId: string) => {
    setExpandedMessages(current => ({ ...current, [messageId]: !current[messageId] }))
  }

  const submitStartFlow = async () => {
    if (!startMode) return
    const title = startTitle.trim() || null
    const agenda = startAgenda.trim() || null
    if (startParticipants.length === 0) return
    setStartSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/conference-room/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({
          mode: startMode,
          actor_role: viewRole,
          actor_display: actorDisplay,
          title,
          agenda,
          participants: startParticipants,
        }),
      })
      if (!res.ok) throw new Error(`회의 생성 API ${res.status}`)
      const next = await res.json() as { thread_ts?: string | null }
      closeStartFlow()
      await loadRoom(true)
      if (next.thread_ts) {
        setSelectedId(next.thread_ts)
        setComposeMode('reply')
        setMobilePane('thread')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '회의 생성 실패')
    } finally {
      setStartSubmitting(false)
    }
  }

  return (
    <section className="conference-page">
      <article className="panel conference-shell">
        <div className="panel-head conference-head">
          <div>
            <h2 style={{ margin: 0 }}>회의실</h2>
            <p className="subtitle conference-subtitle">
              앞으로 진행되는 회의만 가볍게 쌓는 전용 대화면입니다. 과거 Slack/Notion 이력은 불러오지 않고, 현재부터 생성되는 회의 대화만 빠르게 보여줍니다.
            </p>
            <p className="data-meta" style={{ marginTop: '0.35rem' }}>
              데이터 출처: {payload?.source ?? '회의실 실시간 기록'} · 마지막 갱신: {formatDateTime(payload?.updated_at)}
            </p>
          </div>
          <div className="conference-head-actions">
            <span className={`conference-sync-pill ${payload?.sync_mode === 'local' ? 'live' : payload?.sync_mode === 'live' ? 'live' : 'fallback'}`}>
              {payload?.sync_mode === 'local' ? '회의실 전용 실시간 기록' : payload?.sync_mode === 'live' ? 'Slack 실시간 동기화' : '저장 기록 기반 표시'}
            </span>
            <button type="button" className="conference-refresh-button" onClick={() => void loadRoom(true)}>
              새로고침
            </button>
          </div>
        </div>

        {error && (
          <div className="banner banner-error">
            <div className="banner-title">회의실 오류</div>
            <div className="banner-desc">{error}</div>
          </div>
        )}

        {payload?.sync_error && (
          <div className="banner" style={{ background: 'rgba(243, 156, 18, 0.08)', border: '1px solid rgba(243, 156, 18, 0.28)', borderRadius: '12px', padding: '0.9rem 1rem' }}>
            <div className="banner-title">Slack 라이브 동기화 경고</div>
            <div className="banner-desc">{payload.sync_error}</div>
          </div>
        )}

        <div className="conference-summary-strip">
          <span>활성 {payload?.stats.threads ?? 0}</span>
          <span>메시지 {payload?.stats.messages ?? 0}</span>
          <span>참여자 {payload?.stats.participants ?? 0}</span>
          <span>읽지 않음 {unreadCount}</span>
          <span>{backgroundRefreshing ? '동기화 중' : '실시간 반영'}</span>
        </div>

        <div className="conference-quick-actions">
          <button type="button" className="conference-primary-action" onClick={() => openStartFlow('direct')}>
            새 회의 시작
          </button>
          <button type="button" className="conference-secondary-action" onClick={() => openStartFlow('cos_request')}>
            비서실장에게 소집 요청
          </button>
          <button type="button" className="conference-utility-button" onClick={markAllRead}>
            모두 읽음 처리
          </button>
          {MEETING_TEMPLATES.map(template => (
            <button
              key={template.id}
              type="button"
              className="conference-template-button"
              onClick={() => startTemplate(template.text)}
            >
              {template.label}
            </button>
          ))}
        </div>

        {startMode && (
          <div className="conference-start-panel">
            <div className="conference-start-head">
              <div>
                <strong>누구와 바로 논의할까요?</strong>
                <p>참여자만 선택하면 바로 회의를 열 수 있습니다. 제목과 안건은 나중에 자동 정리됩니다.</p>
              </div>
              <button type="button" className="conference-start-close" onClick={closeStartFlow}>
                닫기
              </button>
            </div>
            <div className="conference-start-grid" style={{ marginTop: '0.5rem' }}>
              <div className="conference-start-field conference-start-field-wide">
                <span>참여자 선택</span>
                <em>최소 1명만 고르면 바로 회의를 만들 수 있습니다.</em>
                {startParticipants.length > 0 && (
                  <div className="conference-start-selection">
                    <strong>{startParticipants.length}명 선택됨</strong>
                    <span>{startParticipants.join(' · ')}</span>
                  </div>
                )}
                <div className="conference-start-participants">
                  {(payload?.directory ?? []).map(entry => (
                    <button
                      key={entry.id}
                      type="button"
                      className={startParticipants.includes(entry.label) ? 'active' : ''}
                      onClick={() => toggleStartParticipant(entry.label)}
                    >
                      <TeamAvatar author={entry.label} variant="chip" />
                      {entry.label}
                    </button>
                  ))}
                </div>
              </div>
              
              <details className="conference-start-optional-details" style={{ gridColumn: '1 / -1', marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                <summary style={{ cursor: 'pointer', padding: '0.5rem 0', fontWeight: 600 }}>추가 옵션 (제목/안건 직접 입력)</summary>
                <div style={{ display: 'grid', gap: '1rem', marginTop: '0.5rem' }}>
                  <label className="conference-start-field">
                    <span>회의 제목 (선택)</span>
                    <input value={startTitle} onChange={event => setStartTitle(event.target.value)} placeholder="비워두면 회의 종료 후 자동 생성됩니다" />
                  </label>
                  <label className="conference-start-field">
                    <span>안건 (선택)</span>
                    <textarea value={startAgenda} onChange={event => setStartAgenda(event.target.value)} placeholder="비워두면 대화 내용을 바탕으로 자동 정리됩니다" />
                  </label>
                </div>
              </details>
            </div>
            <div className="conference-start-actions">
              <button type="button" className="conference-secondary-action" onClick={closeStartFlow}>
                취소
              </button>
              <button
                type="button"
                className="conference-primary-action"
                disabled={startSubmitting || startParticipants.length === 0}
                onClick={() => void submitStartFlow()}
              >
                {startSubmitting ? '요청 중…' : startMode === 'direct' ? '대화 열기' : '비서실장 호출'}
              </button>
            </div>
          </div>
        )}

        <div className={`conference-grid conference-grid-pane-${mobilePane}`}>
          <div className="conference-sidebar">
            <div className="conference-sidebar-head">
              <div>
                <strong>최근 대화</strong>
                <span>{filteredItems.length} threads</span>
              </div>
              {backgroundRefreshing && <span className="conference-sync-inline">동기화 중</span>}
            </div>
            <div className="conference-sidebar-controls">
              <input
                className="conference-search-input"
                value={searchQuery}
                onChange={event => setSearchQuery(event.target.value)}
                placeholder="제목, 본문, correlation_id, 참여자 검색"
              />
              <div className="conference-sidebar-tabs" role="tablist" aria-label="회의실 대화 분류">
                {threadTabs.map(tab => (
                  <button
                    key={tab.key}
                    type="button"
                    role="tab"
                    aria-selected={threadView === tab.key}
                    className={threadView === tab.key ? 'active' : ''}
                    onClick={() => setThreadView(tab.key)}
                  >
                    <span>{tab.label}</span>
                    <em>{tab.count}</em>
                  </button>
                ))}
              </div>
              <div className="conference-filter-strip">
                <button
                  type="button"
                  className={participantFilter === 'all' ? 'active' : ''}
                  onClick={() => setParticipantFilter('all')}
                >
                  전체
                </button>
                {participantOptions.map(option => (
                  <button
                    key={option}
                    type="button"
                    className={participantFilter === option ? 'active' : ''}
                    onClick={() => setParticipantFilter(option)}
                  >
                    {option}
                  </button>
                ))}
              </div>
            </div>
            {initialLoading ? (
              <div className="conference-empty-state">회의실을 준비하고 있습니다…</div>
            ) : payload && visibleSections.length > 0 ? (
              <div className="conference-thread-list">
                {visibleSections.map(section => (
                  <div key={section.label} className="conference-thread-section">
                    <div className="conference-thread-section-label">{section.label}</div>
                    {section.items.map(item => (
                      (() => {
                        const persona = personaMeta(item.author_display)
                        return (
                      <button
                        key={item.id}
                        type="button"
                        className={`conference-thread-row ${selectedId === item.id ? 'active' : ''}`}
                        onClick={() => {
                          setSelectedId(item.id)
                          setComposeMode('reply')
                          setMobilePane('thread')
                        }}
                      >
                        <div className="conference-thread-row-body">
                          <TeamAvatar author={item.author_display} variant="thread" />
                          <div className="conference-thread-row-copy">
                            <div className="conference-thread-topline">
                              <strong>{item.title}</strong>
                              <div className="conference-thread-topline-meta">
                                {pinState[item.id] && <span className="conference-pinned-badge">P{pinPriority[item.id] ?? 2}</span>}
                                {item.title_pending && <span className="conference-pending-badge">자동 제목</span>}
                                {isUnread(item) && <span className="conference-unread-dot" aria-label="읽지 않음" />}
                                <span>{formatDateTime(item.posted_at)}</span>
                              </div>
                            </div>
                            <p>{item.preview || '본문 미리보기가 없습니다.'}</p>
                            <div className="conference-thread-meta">
                              <span>{persona.title}</span>
                              <span>{persona.subtitle}</span>
                              <span>답글 {item.reply_count}개</span>
                              {item.linked_note?.title && <span className="conference-thread-note">회의록 연결</span>}
                            </div>
                          </div>
                        </div>
                        <div className="conference-thread-quick-actions">
                          <button
                            type="button"
                            className={`conference-thread-quick-button ${pinState[item.id] ? 'active' : ''}`}
                            onClick={event => {
                              event.stopPropagation()
                              togglePinned(item.id)
                            }}
                          >
                            {pinState[item.id] ? '고정 해제' : '고정'}
                          </button>
                          <button
                            type="button"
                            className="conference-thread-quick-button"
                            onClick={event => {
                              event.stopPropagation()
                              if (isUnread(item)) {
                                markThreadRead(item.id, item.posted_at)
                              } else {
                                markThreadUnread(item.id)
                              }
                            }}
                          >
                            {isUnread(item) ? '읽음' : '미읽음'}
                          </button>
                        </div>
                      </button>
                        )
                      })()
                    ))}
                  </div>
                ))}
              </div>
            ) : (
              <div className="conference-empty-state">
                {payload?.items?.length ? '현재 탭 또는 검색/필터 조건에 맞는 대화가 없습니다.' : roomEmptyLabel}
              </div>
            )}
          </div>

          <div className="conference-main">
            {detailLoading ? (
              <div className="conference-empty-state">대화 상세를 불러오는 중입니다…</div>
            ) : detail ? (
              <div className="conference-thread-panel">
                <div className="conference-thread-header">
                  <div>
                    <button type="button" className="conference-mobile-back" onClick={() => setMobilePane('list')}>
                      대화 목록
                    </button>
                    <h3>{detail.title}</h3>
                    <p>{detail.author_display} · {formatDateTime(detail.posted_at)} · 참여자 {detail.participant_count}명</p>
                    {(detail.title_pending || detail.agenda_pending) && (
                      <div className="conference-thread-note-banner">
                        제목 또는 안건이 아직 확정되지 않았습니다. 회의 종료 후 LLM이 대화 맥락을 읽고 자동 정리합니다.
                      </div>
                    )}
                    {detail.participant_statuses && detail.participant_statuses.length > 0 && (
                      <div className="conference-participant-statuses">
                        {detail.participant_statuses.map(participant => (
                          <span
                            key={participant.name}
                            className={`conference-participant-chip ${participant.status === 'joined' ? 'joined' : 'invited'}`}
                          >
                            {participant.name} · {participant.status === 'joined' ? '입장' : '소집됨'}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="conference-thread-badges">
                    <button
                      type="button"
                      className={`conference-inline-action ${pinState[detail.id] ? 'active' : ''}`}
                      onClick={() => togglePinned(detail.id)}
                    >
                      {pinState[detail.id] ? '고정 해제' : '대화 고정'}
                    </button>
                    {(detail.title_pending || detail.agenda_pending) && (
                      <button
                        type="button"
                        className="conference-inline-action"
                        style={{ color: 'var(--color-accent)', fontWeight: 800 }}
                        onClick={() => void endMeeting(detail.id)}
                        disabled={endingMeeting}
                      >
                        {endingMeeting ? '요약 중...' : '회의 종료 (자동 요약)'}
                      </button>
                    )}
                    {pinState[detail.id] && (
                      <div className="conference-priority-strip">
                        {[1, 2, 3].map(level => (
                          <button
                            key={level}
                            type="button"
                            className={`conference-priority-button ${(pinPriority[detail.id] ?? 2) === level ? 'active' : ''}`}
                            onClick={() => setPinnedPriority(detail.id, level)}
                          >
                            P{level}
                          </button>
                        ))}
                      </div>
                    )}
                    <span className="conference-inline-badge">{detail.reply_count} replies</span>
                  </div>
                </div>

                <div className="conference-message-stream">
                  {detail.messages.map(message => {
                    const persona = personaMeta(message.author_display)
                    const collapsed = shouldCollapseMessage(message.text_markdown) && !expandedMessages[message.id]
                    return (
                      <article key={message.id} className={`conference-message-card ${message.is_reply ? 'reply' : 'root'}`}>
                        <TeamAvatar author={message.author_display} variant="message" />
                        <div className="conference-message-bubble">
                          <div className="conference-message-head">
                            <div className="conference-message-author">
                              <strong>{persona.title}</strong>
                              <small>{persona.subtitle}</small>
                            </div>
                            <span>{formatDateTime(message.posted_at)}</span>
                          </div>
                          <MarkdownMessage markdown={message.text_markdown} collapsed={collapsed} />
                          {shouldCollapseMessage(message.text_markdown) && (
                            <button
                              type="button"
                              className="conference-message-toggle"
                              onClick={() => toggleMessageExpanded(message.id)}
                            >
                              {collapsed ? '더보기' : '접기'}
                            </button>
                          )}
                        </div>
                      </article>
                    )
                  })}
                </div>

                <div className="conference-composer">
                  <div className="conference-composer-head">
                    <div className="conference-compose-toggle">
                      <button
                        type="button"
                        className={composeMode === 'reply' && canReply ? 'active' : ''}
                        disabled={!canReply}
                        onClick={() => setComposeMode('reply')}
                      >
                        선택 스레드 답장
                      </button>
                      <button
                        type="button"
                        className={composeMode === 'root' ? 'active' : ''}
                        onClick={() => setComposeMode('root')}
                      >
                        새 의제 시작
                      </button>
                    </div>
                    <span className="conference-compose-meta">
                      {composeMode === 'reply' && canReply ? `${actorDisplay} 명의로 Slack 스레드에 답장` : `${actorDisplay} 명의로 새 루트 메시지 전송`}
                    </span>
                  </div>
                  <textarea
                    className="conference-composer-input"
                    value={draft}
                    onChange={event => setDraft(event.target.value)}
                    placeholder={composeMode === 'reply' ? '선택된 회의실 스레드에 답변하거나 추가 지시를 남기십시오.' : '새 의제, 새 지시, 새 토론 아젠다를 입력하십시오.'}
                  />
                  <div className="conference-composer-actions">
                    <button type="button" className="conference-send-button" disabled={posting || !draft.trim()} onClick={() => void submitMessage()}>
                      {posting ? '전송 중…' : composeMode === 'reply' ? 'Slack에 답장 전송' : 'Slack에 새 대화 시작'}
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="conference-empty-state">좌측 목록에서 회의실 대화를 선택하십시오.</div>
            )}
          </div>
        </div>
      </article>
    </section>
  )
}
