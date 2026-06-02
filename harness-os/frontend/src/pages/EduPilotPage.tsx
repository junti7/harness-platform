import { useState, useEffect, useRef } from 'react'

// ── 적응형 AI 부모 자가점검 — 100% LLM 구동 자유 대화 PoC ───────────────────────
// rule-based 질문 트리 없음. 매 턴 백엔드 /api/edu/diagnose (Gemini)가 톤·내용 생성.
// 톤 사다리(공손→역술인 단정), 세그먼트별 화법, 실패 복구는 전부 LLM 프롬프트에서.

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

type Msg = { role: 'ai' | 'user'; text: string; toneLevel?: number; phase?: string }
type SetupStep = 'segment' | 'info' | 'salutation'

const C = {
  ink: '#0f172a', muted: '#475569', faint: '#64748b', accent: '#2563eb',
  accentSoft: '#dbeafe', cyan: '#0ea5e9', surface: '#ffffff', border: '#e2e8f0',
  success: '#059669', successSoft: '#d1fae5', warning: '#d97706', warningSoft: '#fef3c7', danger: '#dc2626',
  bubbleAi: '#f1f5f9', bubbleUser: '#2563eb', bg: '#f8fafc',
}

const PHASE_LABEL: Record<string, string> = {
  opening: '첫 인사', probing: '경청', reflecting: '단정(역술인)', recovering: '톤 후퇴(복구)', prescribing: '처방',
}

const OPENERS: Record<'parent' | 'worker', { text: string; quick: string[] }> = {
  parent: {
    text: '오셨군요. … 요즘 이 자리에 오시는 보호자분들, 열에 아홉은 같은 데서 막히세요. "우리 아이 AI를 어떻게 해야 하나." 우선 하나만 봅시다 — 자녀분, 몇 학년이죠?',
    quick: ['초등학생이에요', '중학생이에요', '고등학생이에요'],
  },
  worker: {
    text: '앉으세요. … 요즘 이쪽으로 오시는 분들, 대부분 같은 이유예요. "AI 못 따라가면 끝이다" 싶은 거죠. 우선 하나 봅시다 — 지금 무슨 일 하세요?',
    quick: ['사무직이에요', '기획/마케팅이에요', '딱히 정해진 게 없어요'],
  },
}

export function EduPilotPage({ apiBase, authHeaders }: Props) {
  // ── setup state ──
  const [setupStep, setSetupStep] = useState<SetupStep>('segment')
  const [segment, setSegment] = useState<'parent' | 'worker'>('parent')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [salutation, setSalutation] = useState<'neutral' | 'father' | 'mother' | 'name'>('neutral')

  // ── chat state ──
  const [started, setStarted] = useState(false)
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [quickReplies, setQuickReplies] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showOffer, setShowOffer] = useState(false)
  const [turn, setTurn] = useState(0)

  // ── tester panel (CEO/VP 전용, started=false 일 때만) ──
  const [testerName, setTesterName] = useState('')
  const [testerEmail, setTesterEmail] = useState('')
  const [testerSegment, setTesterSegment] = useState<'parent' | 'worker'>('parent')
  const [testerSalutation, setTesterSalutation] = useState<'neutral' | 'father' | 'mother' | 'name'>('neutral')
  const [testerLocale, setTesterLocale] = useState<'ko-KR' | 'en-US'>('ko-KR')
  const [testerForceNew, setTesterForceNew] = useState(true)
  const [testerLink, setTesterLink] = useState('')
  const [testerCreating, setTesterCreating] = useState(false)
  const [showTester, setShowTester] = useState(false)

  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [msgs, loading])

  // ── API calls ──
  async function callDiagnose(userText: string, history: Msg[], turnNo: number) {
    setLoading(true)
    try {
      const res = await fetch(`${apiBase}/api/edu/diagnose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          segment,
          turn: turnNo,
          history: history.map((m) => ({ role: m.role, text: m.text })),
          user_text: userText,
        }),
      })
      const data = await res.json()
      const aiMsg: Msg = { role: 'ai', text: data.message || '…', toneLevel: data.tone_level, phase: data.phase }
      setMsgs((prev) => [...prev, aiMsg])
      setQuickReplies(data.quick_replies || [])
      if (data.show_offer) setShowOffer(true)
    } catch {
      setMsgs((prev) => [...prev, { role: 'ai', text: '(연결이 잠깐 끊겼어요. 다시 말씀해 주시겠어요?)', phase: 'recovering' }])
    } finally {
      setLoading(false)
    }
  }

  async function createMagicLink() {
    if (!testerEmail.trim()) { alert('테스트할 이메일을 입력하세요.'); return }
    setTesterCreating(true)
    try {
      const res = await fetch(`${apiBase}/api/edu/magic-link/test-create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          segment: testerSegment, name: testerName, email: testerEmail,
          preferred_salutation: testerSalutation, locale: testerLocale, force_new: testerForceNew,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.detail || `HTTP ${res.status}`)
      setTesterLink(data.magic_link || '')
    } catch (err) {
      alert(`테스트 링크 생성 실패: ${err instanceof Error ? err.message : 'unknown'}`)
    } finally {
      setTesterCreating(false)
    }
  }

  // ── start chat ──
  function startChat(seg: 'parent' | 'worker') {
    setStarted(true)
    setShowOffer(false)
    setTurn(0)
    const op = OPENERS[seg]
    setMsgs([{ role: 'ai', text: op.text, toneLevel: 0, phase: 'opening' }])
    setQuickReplies(op.quick)
  }

  function send(text: string) {
    const t = text.trim()
    if (!t || loading) return
    const userMsg: Msg = { role: 'user', text: t }
    const newHistory = [...msgs, userMsg]
    setMsgs(newHistory)
    setInput('')
    setQuickReplies([])
    const nextTurn = turn + 1
    setTurn(nextTurn)
    void callDiagnose(t, newHistory, nextTurn)
  }

  function resetAll() {
    setStarted(false)
    setSetupStep('segment')
    setName('')
    setEmail('')
    setSalutation('neutral')
    setSegment('parent')
    setMsgs([])
    setQuickReplies([])
    setInput('')
    setShowOffer(false)
    setTurn(0)
  }

  // ── styles ──
  const wrap: React.CSSProperties = {
    maxWidth: 480, margin: '0 auto', padding: '4px 4px 12px',
    fontFamily: "'Pretendard','Inter',sans-serif", color: C.ink,
    display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', minHeight: 480,
  }
  const btn: React.CSSProperties = {
    display: 'block', width: '100%', background: C.accent, color: '#fff', border: 'none', borderRadius: 14,
    padding: 16, fontSize: '1.02rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
    boxShadow: '0 4px 14px rgba(37,99,235,.25)',
  }
  const inputStyle: React.CSSProperties = {
    width: '100%', border: `1.5px solid ${C.border}`, borderRadius: 12,
    padding: '13px 14px', fontSize: '.97rem', fontFamily: 'inherit',
    boxSizing: 'border-box', outline: 'none',
  }

  // ── Chat Screen ── (started=true 이면 폼 전혀 없음)
  if (started) {
    const lastAi = [...msgs].reverse().find((m) => m.role === 'ai') ?? { toneLevel: 0, phase: 'opening' }
    return (
      <div style={wrap}>
        {/* 최소한의 상태 바 + 리셋 */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, marginBottom: 8, fontSize: '.72rem', color: C.faint }}>
          <span><b style={{ color: C.ink }}>{name || email || (segment === 'parent' ? '부모' : '직장인')}</b> · {segment === 'parent' ? '부모' : '직장인'}</span>
          <span>턴 {turn} · 톤 <b style={{ color: C.accent }}>{lastAi.toneLevel ?? 0}</b> · {PHASE_LABEL[(lastAi as Msg).phase ?? 'opening'] ?? '-'}</span>
          <button onClick={resetAll} style={{ background: 'none', border: 'none', color: C.faint, cursor: 'pointer', fontSize: '.72rem', textDecoration: 'underline' }}>처음</button>
        </div>

        {/* 메시지 영역 */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '6px 2px', display: 'flex', flexDirection: 'column', gap: 10 }}>
          {msgs.map((m, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div style={{
                maxWidth: '82%', padding: '11px 15px', borderRadius: 16,
                borderBottomLeftRadius: m.role === 'ai' ? 4 : 16, borderBottomRightRadius: m.role === 'user' ? 4 : 16,
                background: m.role === 'user' ? C.bubbleUser : C.bubbleAi,
                color: m.role === 'user' ? '#fff' : C.ink, fontSize: '1rem', lineHeight: 1.6, whiteSpace: 'pre-wrap',
              }}>{m.text}</div>
            </div>
          ))}
          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div style={{ padding: '12px 16px', borderRadius: 16, borderBottomLeftRadius: 4, background: C.bubbleAi, color: C.faint, fontSize: '1.1rem', letterSpacing: 2 }}>···</div>
            </div>
          )}

          {showOffer && (
            <div style={{ marginTop: 8 }}>
              <div style={{ background: `linear-gradient(135deg,${C.accentSoft},#eff6ff)`, border: `1.5px solid ${C.accent}`, borderRadius: 16, padding: 18, marginBottom: 10 }}>
                <span style={{ display: 'inline-block', background: C.danger, color: '#fff', fontSize: '.72rem', fontWeight: 700, padding: '3px 9px', borderRadius: 6, marginBottom: 8 }}>무료로 먼저 시작</span>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: '4px 0 6px', color: C.ink }}>지금 바로 해볼 수 있는 무료 커리큘럼 3개</h3>
                <p style={{ fontSize: '.9rem', color: C.muted, marginBottom: 12 }}>아래 3개부터 해보시면 현재 상황이 훨씬 또렷해질 거예요.</p>
                <div style={{ display: 'grid', gap: 8 }}>
                  {['1. 부모가 먼저 이해해야 할 AI 기초', '2. 아이의 현재 AI 사용 패턴 점검', '3. 오늘 저녁 바로 써볼 대화 문장'].map((t) => (
                    <div key={t} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
                      <strong>{t}</strong>
                    </div>
                  ))}
                </div>
                <button style={{ ...btn, marginTop: 12 }} onClick={() => alert('파일럿: 다음 버전에서 무료 커리큘럼 3개가 실제 콘텐츠로 연결됩니다.')}>무료 단계부터 이어서 보기 →</button>
              </div>
              <div style={{ background: `linear-gradient(135deg,${C.successSoft},#ecfdf5)`, border: `1.5px solid ${C.success}`, borderRadius: 16, padding: 18 }}>
                <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: C.success, margin: '0 0 6px' }}>다음 단계에서 받게 될 도움</h3>
                <p style={{ fontSize: '.9rem', color: C.muted, marginBottom: 12 }}>여기까지 해보신 뒤 원하시면, 보호자님 상황에 맞는 더 구체적인 가이드와 심화 커리큘럼도 이어서 받아보실 수 있을 거예요.</p>
                <button style={{ ...btn, background: C.success, boxShadow: '0 4px 14px rgba(5,150,105,.25)' }} onClick={() => alert('파일럿: 다음 버전에서 단계형 가이드와 심화 과정을 자연스럽게 이어줍니다.')}>다음 단계가 어떻게 이어지는지 보기 →</button>
              </div>
            </div>
          )}
        </div>

        {/* 빠른 응답 칩 */}
        {quickReplies.length > 0 && !loading && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, padding: '8px 2px' }}>
            {quickReplies.map((q, i) => (
              <button key={i} onClick={() => send(q)} style={{ background: C.surface, border: `1.5px solid ${C.accent}`, color: C.accent, borderRadius: 99, padding: '8px 14px', fontSize: '.9rem', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}>{q}</button>
            ))}
          </div>
        )}

        {/* 입력창 */}
        <div style={{ display: 'flex', gap: 8, paddingTop: 8 }}>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') send(input) }}
            placeholder="편하게 입력하세요…"
            disabled={loading}
            style={{ flex: 1, border: `1.5px solid ${C.border}`, borderRadius: 12, padding: '13px 15px', fontSize: '1rem', fontFamily: 'inherit', outline: 'none' }}
          />
          <button onClick={() => send(input)} disabled={loading || !input.trim()} style={{ background: input.trim() && !loading ? C.accent : C.border, color: '#fff', border: 'none', borderRadius: 12, padding: '0 20px', fontSize: '1rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>전송</button>
        </div>
      </div>
    )
  }

  // ── Setup Wizard (started=false) ──
  return (
    <div style={{ ...wrap, justifyContent: 'flex-start' }}>
      {/* CEO/VP 테스트 런처 (접기/펼치기) */}
      <div style={{ marginBottom: 16 }}>
        <button
          onClick={() => setShowTester((v) => !v)}
          style={{ background: 'none', border: `1px solid ${C.border}`, borderRadius: 10, padding: '7px 14px', fontSize: '.78rem', fontWeight: 700, color: C.faint, cursor: 'pointer', fontFamily: 'inherit', letterSpacing: '.04em' }}
        >
          🧪 CEO / VP 테스트 런처 {showTester ? '▲' : '▼'}
        </button>
        {showTester && (
          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 16, padding: 16, marginTop: 8 }}>
            <div style={{ fontSize: '.82rem', color: C.muted, lineHeight: 1.6, marginBottom: 12 }}>
              매직 링크를 생성하거나 독립형 앱을 새 탭에서 열 수 있습니다. 기본값은 새 케이스 시작입니다.
            </div>
            <div style={{ display: 'grid', gap: 10 }}>
              <input value={testerName} onChange={(e) => setTesterName(e.target.value)} placeholder="이름" style={inputStyle} />
              <input value={testerEmail} onChange={(e) => setTesterEmail(e.target.value)} placeholder="이메일" style={inputStyle} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <select value={testerSalutation} onChange={(e) => setTesterSalutation(e.target.value as 'neutral' | 'father' | 'mother' | 'name')} style={{ ...inputStyle, background: C.surface }}>
                  <option value="neutral">중립 호칭</option>
                  <option value="father">아버지</option>
                  <option value="mother">어머니</option>
                  <option value="name">이름으로</option>
                </select>
                <select value={testerLocale} onChange={(e) => setTesterLocale(e.target.value as 'ko-KR' | 'en-US')} style={{ ...inputStyle, background: C.surface }}>
                  <option value="ko-KR">한국어</option>
                  <option value="en-US">English</option>
                </select>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '.88rem', color: C.ink, cursor: 'pointer' }}>
                  <input type="checkbox" checked={testerForceNew} onChange={(e) => setTesterForceNew(e.target.checked)} /> 새 케이스로 시작
                </label>
                <div style={{ display: 'flex', gap: 6 }}>
                  {(['parent', 'worker'] as const).map((seg) => (
                    <button key={seg} onClick={() => setTesterSegment(seg)} style={{ padding: '7px 12px', borderRadius: 10, fontSize: '.85rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', border: `1.5px solid ${C.accent}`, background: testerSegment === seg ? C.accent : C.surface, color: testerSegment === seg ? '#fff' : C.accent }}>
                      {seg === 'parent' ? '부모' : '직장인'}
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button onClick={createMagicLink} disabled={testerCreating} style={{ ...btn, width: 'auto', padding: '11px 14px', fontSize: '.88rem', boxShadow: 'none' }}>
                  {testerCreating ? '생성 중…' : '매직 링크 생성'}
                </button>
                <button onClick={() => window.open('/edu-pilot-app.html', '_blank', 'noopener,noreferrer')} style={{ ...btn, width: 'auto', padding: '11px 14px', background: C.surface, color: C.accent, border: `1.5px solid ${C.accent}`, boxShadow: 'none', fontSize: '.88rem' }}>
                  기본 앱 열기
                </button>
                {testerLink && (
                  <button onClick={() => window.open(testerLink, '_blank', 'noopener,noreferrer')} style={{ ...btn, width: 'auto', padding: '11px 14px', background: C.success, boxShadow: 'none', fontSize: '.88rem' }}>
                    생성된 링크 열기
                  </button>
                )}
              </div>
              {testerLink && (
                <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: 12, padding: 12 }}>
                  <div style={{ fontSize: '.75rem', color: C.faint, marginBottom: 4 }}>테스트 링크 · {testerForceNew ? '새 케이스' : '이어보기'}</div>
                  <div style={{ fontSize: '.85rem', color: C.ink, lineHeight: 1.5, wordBreak: 'break-all' }}>{testerLink}</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Step 1: 세그먼트 선택 ── */}
      {setupStep === 'segment' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontSize: '.72rem', fontWeight: 700, letterSpacing: '.08em', color: C.accent, textTransform: 'uppercase', marginBottom: 8 }}>Harness · AI 자가점검 — 1/3</div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: 10, lineHeight: 1.35 }}>어느 쪽에 더 가까우세요?</h1>
          <p style={{ color: C.muted, fontSize: '.95rem', marginBottom: 28, lineHeight: 1.6 }}>정해진 질문지가 없습니다. 대화가 자연스럽게 이어집니다.</p>
          <button style={{ ...btn, marginBottom: 12 }} onClick={() => { setSegment('parent'); setSetupStep('info') }}>
            👨‍👩‍👧 아이를 둔 부모예요
          </button>
          <button style={{ ...btn, background: C.surface, color: C.accent, border: `1.5px solid ${C.accent}`, boxShadow: 'none' }} onClick={() => { setSegment('worker'); setSetupStep('info') }}>
            💼 AI가 걱정되는 직장인이에요
          </button>
        </div>
      )}

      {/* ── Step 2: 이름 + 이메일 ── */}
      {setupStep === 'info' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontSize: '.72rem', fontWeight: 700, letterSpacing: '.08em', color: C.accent, textTransform: 'uppercase', marginBottom: 8 }}>Harness · AI 자가점검 — 2/3</div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 8, lineHeight: 1.35 }}>간단히 확인할게요</h1>
          <p style={{ color: C.muted, fontSize: '.92rem', marginBottom: 24, lineHeight: 1.6 }}>대화를 이어보시려면 이메일이 필요합니다. 이름은 선택이에요.</p>
          <div style={{ display: 'grid', gap: 12, marginBottom: 24 }}>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="이름 (선택)" style={inputStyle} />
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="이메일 *" type="email" style={inputStyle} />
          </div>
          <button style={{ ...btn, marginBottom: 10 }} onClick={() => {
            if (!email.trim() || !email.includes('@')) { alert('이메일을 올바르게 입력해 주세요.'); return }
            setSetupStep('salutation')
          }}>
            다음 →
          </button>
          <button style={{ background: 'none', border: 'none', color: C.faint, fontSize: '.88rem', cursor: 'pointer', fontFamily: 'inherit' }} onClick={() => setSetupStep('segment')}>← 이전</button>
        </div>
      )}

      {/* ── Step 3: 호칭 선택 + 시작 ── */}
      {setupStep === 'salutation' && (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ fontSize: '.72rem', fontWeight: 700, letterSpacing: '.08em', color: C.accent, textTransform: 'uppercase', marginBottom: 8 }}>Harness · AI 자가점검 — 3/3</div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 800, marginBottom: 8, lineHeight: 1.35 }}>어떻게 불러드릴까요?</h1>
          <p style={{ color: C.muted, fontSize: '.92rem', marginBottom: 20, lineHeight: 1.6 }}>AI가 대화 중 사용할 호칭을 고르세요.</p>
          <div style={{ display: 'grid', gap: 10, marginBottom: 24 }}>
            {([['neutral', '보호자분 (중립)'], ['father', '아버지'], ['mother', '어머니'], ['name', `${name || '이름'}으로 불러줘`]] as const).map(([val, label]) => (
              <button key={val} onClick={() => setSalutation(val)} style={{ padding: '14px 16px', borderRadius: 14, fontSize: '.97rem', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left', border: `1.5px solid ${salutation === val ? C.accent : C.border}`, background: salutation === val ? C.accentSoft : C.surface, color: salutation === val ? C.accent : C.ink, transition: 'all .15s' }}>
                {salutation === val ? '✓ ' : ''}{label}
              </button>
            ))}
          </div>
          <button style={{ ...btn, marginBottom: 10 }} onClick={() => startChat(segment)}>
            대화 시작하기 →
          </button>
          <button style={{ background: 'none', border: 'none', color: C.faint, fontSize: '.88rem', cursor: 'pointer', fontFamily: 'inherit' }} onClick={() => setSetupStep('info')}>← 이전</button>
        </div>
      )}
    </div>
  )
}
