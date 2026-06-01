import { useState, useEffect, useRef } from 'react'

// ── 적응형 AI 부모 진단 — 100% LLM 구동 자유 대화 PoC ────────────────────────
// rule-based 질문 트리 없음. 매 턴 백엔드 /api/edu/diagnose (Gemini)가 톤·내용 생성.
// 톤 사다리(공손→역술인 단정), 세그먼트별 화법, 실패 복구는 전부 LLM 프롬프트에서.

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

type Msg = { role: 'ai' | 'user'; text: string; toneLevel?: number; phase?: string }

const C = {
  ink: '#0f172a', muted: '#475569', faint: '#64748b', accent: '#2563eb',
  accentSoft: '#dbeafe', cyan: '#0ea5e9', surface: '#ffffff', border: '#e2e8f0',
  success: '#059669', successSoft: '#d1fae5', warning: '#d97706', warningSoft: '#fef3c7', danger: '#dc2626',
  bubbleAi: '#f1f5f9', bubbleUser: '#2563eb',
}

const PHASE_LABEL: Record<string, string> = {
  opening: '첫 인사', probing: '경청', reflecting: '단정(역술인)', recovering: '톤 후퇴(복구)', prescribing: '처방',
}

export function EduPilotPage({ apiBase, authHeaders }: Props) {
  const [segment, setSegment] = useState<'parent' | 'worker'>('parent')
  const [started, setStarted] = useState(false)
  const [msgs, setMsgs] = useState<Msg[]>([])
  const [quickReplies, setQuickReplies] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showOffer, setShowOffer] = useState(false)
  const [turn, setTurn] = useState(0)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [msgs, loading])

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

  // 첫 인사는 시간차 없이 즉시 — 고정 오프너(관찰+구체질문). 이후 턴부터 LLM.
  const OPENERS: Record<'parent' | 'worker', { text: string; quick: string[] }> = {
    parent: {
      text: '안녕하세요, 어머님·아버님. 요즘 "AI 때문에 우리 아이 공부를 어떻게 시켜야 하나" 고민하시는 분들이 정말 많으세요. 혹시 자녀분은 나이가 어떻게 되나요?',
      quick: ['초등학생이에요', '중학생이에요', '고등학생이에요'],
    },
    worker: {
      text: '안녕하세요. 요즘 회사에서 "AI 못 쓰면 도태된다"는 얘기, 한 번쯤 들어보셨죠? 비슷한 고민으로 오시는 분들이 많은데요. 혹시 어떤 일 하고 계세요?',
      quick: ['사무직이에요', '기획/마케팅이에요', '딱히 정해진 게 없어요'],
    },
  }

  function start(seg: 'parent' | 'worker') {
    setSegment(seg)
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

  const wrap: React.CSSProperties = {
    maxWidth: 480, margin: '0 auto', padding: '4px 4px 12px', fontFamily: "'Pretendard','Inter',sans-serif", color: C.ink,
    display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', minHeight: 480,
  }
  const btn: React.CSSProperties = {
    display: 'block', width: '100%', background: C.accent, color: '#fff', border: 'none', borderRadius: 14,
    padding: 16, fontSize: '1.02rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
    boxShadow: '0 4px 14px rgba(37,99,235,.25)',
  }

  // ── 시작 화면 (세그먼트만 선택, 질문 아님) ──
  if (!started) {
    return (
      <div style={{ ...wrap, justifyContent: 'center' }}>
        <div style={{ background: C.warningSoft, color: C.warning, fontSize: '.8rem', fontWeight: 600, padding: '8px 14px', borderRadius: 10, marginBottom: 18, textAlign: 'center' }}>
          🧪 1호 파일럿 PoC — 실제 대화는 매 턴 LLM이 생성합니다 (정해진 질문 없음)
        </div>
        <div style={{ fontSize: '.72rem', fontWeight: 700, letterSpacing: '.08em', color: C.accent, textTransform: 'uppercase', marginBottom: 6 }}>Harness · AI 진단</div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 10, lineHeight: 1.35 }}>편하게 대화하듯 시작해 보세요</h1>
        <p style={{ color: C.muted, fontSize: '1rem', marginBottom: 24 }}>
          정해진 질문지가 없습니다. 그냥 떠오르는 대로 답하시면, 대화가 알아서 이어집니다.
        </p>
        <p style={{ fontSize: '.85rem', color: C.faint, marginBottom: 12 }}>어느 쪽에 더 가까우세요?</p>
        <button style={{ ...btn, marginBottom: 12 }} onClick={() => start('parent')}>아이를 둔 부모예요</button>
        <button style={{ ...btn, background: C.surface, color: C.accent, border: `1.5px solid ${C.accent}`, boxShadow: 'none' }} onClick={() => start('worker')}>AI가 걱정되는 직장인이에요</button>
      </div>
    )
  }

  // ── 채팅 화면 ──
  return (
    <div style={wrap}>
      {/* 상단 디버그 바 (CEO가 톤 상승을 눈으로 확인) */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', background: C.surface, border: `1px solid ${C.border}`, borderRadius: 10, marginBottom: 8, fontSize: '.72rem', color: C.faint }}>
        <span>세그먼트: <b style={{ color: C.ink }}>{segment === 'parent' ? '부모' : '직장인'}</b></span>
        <span>턴 {turn} · 톤레벨 <b style={{ color: C.accent }}>{msgs.filter((m) => m.role === 'ai').slice(-1)[0]?.toneLevel ?? 0}</b> · {PHASE_LABEL[msgs.filter((m) => m.role === 'ai').slice(-1)[0]?.phase ?? 'opening'] ?? '-'}</span>
        <button onClick={() => setStarted(false)} style={{ background: 'none', border: 'none', color: C.faint, cursor: 'pointer', fontSize: '.72rem', textDecoration: 'underline' }}>처음</button>
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

        {/* 처방 offer (LLM이 show_offer 신호 줄 때만) */}
        {showOffer && (
          <div style={{ marginTop: 8 }}>
            <div style={{ background: `linear-gradient(135deg,${C.accentSoft},#eff6ff)`, border: `1.5px solid ${C.accent}`, borderRadius: 16, padding: 18, marginBottom: 10 }}>
              <span style={{ display: 'inline-block', background: C.danger, color: '#fff', fontSize: '.72rem', fontWeight: 700, padding: '3px 9px', borderRadius: 6, marginBottom: 8 }}>진단받은 분 한정 · 오늘만</span>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: '4px 0 6px' }}>나만을 위한 맞춤 처방</h3>
              <p style={{ fontSize: '.9rem', color: C.muted, marginBottom: 12 }}>오늘 나눈 대화를 바탕으로, 우리 상황에 정확히 맞춘 7일 행동 가이드를 드립니다.</p>
              <div><span style={{ fontSize: '1.5rem', fontWeight: 800, color: C.accent }}>₩9,900</span><span style={{ color: C.faint, textDecoration: 'line-through', fontSize: '.95rem', marginLeft: 8 }}>₩49,000</span></div>
              <button style={{ ...btn, marginTop: 12 }} onClick={() => alert('파일럿: 실제 버전에서는 ₩9,900 결제 → 맞춤 처방 PDF 생성')}>맞춤 처방 받기 →</button>
            </div>
            <div style={{ background: `linear-gradient(135deg,${C.successSoft},#ecfdf5)`, border: `1.5px solid ${C.success}`, borderRadius: 16, padding: 18 }}>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: C.success, margin: '0 0 6px' }}>또는 — 부모 먼저 4주 과정</h3>
              <p style={{ fontSize: '.9rem', color: C.muted, marginBottom: 12 }}>"부모가 AI를 먼저 이해한 후 아이를 가이드하는 법" · 2주 무료 체험</p>
              <button style={{ ...btn, background: C.success, boxShadow: '0 4px 14px rgba(5,150,105,.25)' }} onClick={() => alert('파일럿: 4주 과정 2주 무료 체험 시작')}>2주 무료로 시작하기 →</button>
            </div>
          </div>
        )}
      </div>

      {/* 빠른 응답 칩 (LLM 제공) */}
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
