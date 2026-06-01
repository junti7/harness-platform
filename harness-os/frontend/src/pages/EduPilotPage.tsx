import { useState, useEffect, useRef } from 'react'

// ── 진단 데이터 ─────────────────────────────────────────
const QUESTIONS = [
  {
    label: '질문 1 / 3',
    title: '저는…',
    opts: ['초·중·고 자녀를 둔 부모', 'AI 시대 아이 교육이 걱정되는 부모', '아이가 어린, 미리 준비하는 부모'],
  },
  {
    label: '질문 2 / 3',
    title: '지금 가장 걱정되는 것은?',
    opts: [
      '아이가 AI에 너무 의존하는 것 같아요',
      '아이가 AI를 안 써서 뒤처질까 봐요',
      '무엇이 옳은지 기준이 전혀 없어요',
      '내가 AI를 모르니 아이를 가이드 못 해요',
    ],
  },
  {
    label: '질문 3 / 3',
    title: 'AI를 직접 써보신 경험은?',
    opts: ['거의 없어요 (이제 막 시작)', '가끔 써봤어요 (아직 안 익숙)', '꽤 써봤지만 뭔가 부족한 느낌'],
  },
]

const DEEP_OPTS = [
  '아이가 AI 없이는 시작을 못 해요',
  'AI 답변을 그대로 제출해요',
  '아이가 AI를 어떻게 쓰는지 모르겠어요',
  '선생님이 쓰지 말랬는데 몰래 써요',
]

const TYPES: Record<number, { t: string; d: string; stage: string }> = {
  0: { t: 'AI 통제 불안형', d: '잘못될까 봐 막고 싶은 부모', stage: 'AI 의존 발아 단계 ⚠️' },
  1: { t: 'AI 조급 추격형', d: '뒤처질까 봐 서두르는 부모', stage: 'AI 활용 초기 단계 🌱' },
  2: { t: 'AI 기준 부재형', d: '알고 싶지만 어디서 시작할지 모르는 부모', stage: '기준 형성 골든타임 ⏳' },
  3: { t: '동반 성장 대기형', d: '아이와 함께 배울 준비가 된 부모', stage: '부모 먼저 단계 🧭' },
}

const BARNUM: Record<number, string[]> = {
  0: [
    '자녀가 AI를 쓰는 걸 봤을 때, 혼내야 할지 그냥 둬야 할지 판단이 안 서신 적 있으시죠?',
    '막자니 시대에 뒤처질 것 같고, 두자니 망칠 것 같고. 그 사이에서 매번 마음이 왔다 갔다 하셨을 거예요.',
    '그 불안, 완전히 이해합니다. 사실 그게 당연한 이유가 있어요.',
  ],
  1: [
    '"우리 애만 안 하고 있나" 싶어서 마음이 조급해지신 적 있으시죠?',
    '옆집 아이는 벌써 AI로 뭘 한다는데, 정작 뭘 어떻게 시작해야 할지는 아무도 정리해주지 않더라고요.',
    '그 답답함, 잘 압니다. 방향만 잡으면 생각보다 간단해요.',
  ],
  2: [
    '주변은 "AI 시켜라" vs "AI가 망친다"로 갈리는데, 정작 우리 아이에겐 뭐가 맞는지는 아무도 안 알려주죠?',
    '기준이 없으니 매번 그때그때 감으로 판단하게 되고, 그게 맞는 건지도 확신이 안 서고.',
    '그 막막함, 정확히 이해합니다. 기준은 만들 수 있어요.',
  ],
  3: [
    '"내가 먼저 알아야 아이한테 말해줄 텐데" 하는 생각, 이미 하고 계셨죠?',
    '사실 그 생각이 가장 건강한 출발점이에요. 대부분은 아이부터 어떻게 해보려다 막히거든요.',
    '비행기에서 산소마스크는 부모가 먼저 씁니다. AI도 똑같아요.',
  ],
}

const RX2: Record<number, string> = {
  0: '부모님이 먼저 같은 도구를 딱 10분만 써보세요. 막연한 불안이 구체적 판단으로 바뀝니다.',
  1: '이미 써보셨으니, 이번엔 "아이가 쓴 결과를 같이 검토"해보세요. 그게 진짜 교육입니다.',
  2: '쓰는 데 익숙하시니, 이제 "아이에게 질문하는 법"을 가르칠 차례예요. 도구보다 질문이 핵심입니다.',
}

type Stage = 'intro' | 'q' | 'barnum' | 'deep' | 'result' | 'share'

const C = {
  ink: '#0f172a', muted: '#475569', faint: '#64748b', accent: '#2563eb',
  accentSoft: '#dbeafe', cyan: '#0ea5e9', surface: '#ffffff', border: '#e2e8f0',
  success: '#059669', successSoft: '#d1fae5', warning: '#d97706', warningSoft: '#fef3c7', danger: '#dc2626',
}

export function EduPilotPage() {
  const [stage, setStage] = useState<Stage>('intro')
  const [qi, setQi] = useState(0)
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [deepText, setDeepText] = useState('')
  const [barnumShown, setBarnumShown] = useState(0)
  const timerRef = useRef<number | null>(null)

  const ty = TYPES[answers.q1 ?? 2] ?? TYPES[2]

  // Barnum 순차 노출
  useEffect(() => {
    if (stage !== 'barnum') return
    setBarnumShown(0)
    const lines = BARNUM[answers.q1 ?? 2] ?? BARNUM[2]
    let i = 0
    const tick = () => {
      i += 1
      setBarnumShown(i)
      if (i < lines.length) {
        timerRef.current = window.setTimeout(tick, 750)
      }
    }
    timerRef.current = window.setTimeout(tick, 1000)
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current)
    }
  }, [stage, answers.q1])

  const selectQ = (idx: number) => {
    const next = { ...answers, ['q' + qi]: idx }
    setAnswers(next)
    if (qi < 2) setQi(qi + 1)
    else setStage('barnum')
  }

  const wrap: React.CSSProperties = {
    maxWidth: 480, margin: '0 auto', padding: '4px 4px 40px', fontFamily: "'Pretendard','Inter',sans-serif", color: C.ink,
  }
  const btn: React.CSSProperties = {
    display: 'block', width: '100%', background: C.accent, color: '#fff', border: 'none', borderRadius: 14,
    padding: 17, fontSize: '1.05rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
    boxShadow: '0 4px 14px rgba(37,99,235,.25)', transition: 'transform .15s ease',
  }
  const ghost: React.CSSProperties = {
    ...btn, background: 'transparent', color: C.muted, boxShadow: 'none', border: `1.5px solid ${C.border}`,
    fontWeight: 600, fontSize: '.95rem', padding: 14, marginTop: 10,
  }
  const opt = (sel: boolean): React.CSSProperties => ({
    display: 'block', width: '100%', textAlign: 'left', background: sel ? C.accentSoft : C.surface,
    border: `1.5px solid ${sel ? C.accent : C.border}`, borderRadius: 14, padding: '16px 18px', marginBottom: 12,
    fontSize: '1rem', fontWeight: sel ? 600 : 500, color: sel ? C.accent : C.ink, cursor: 'pointer', fontFamily: 'inherit',
  })
  const card: React.CSSProperties = {
    background: C.surface, border: `1px solid ${C.border}`, borderRadius: 16, padding: 22, marginBottom: 18,
    boxShadow: '0 1px 3px rgba(15,23,42,.04)',
  }
  const brand: React.CSSProperties = {
    fontSize: '.72rem', fontWeight: 700, letterSpacing: '.08em', color: C.accent, textTransform: 'uppercase', marginBottom: 6,
  }

  return (
    <div style={wrap}>
      {/* 파일럿 안내 배너 */}
      <div style={{ background: C.warningSoft, color: C.warning, fontSize: '.8rem', fontWeight: 600, padding: '8px 14px', borderRadius: 10, marginBottom: 16, textAlign: 'center' }}>
        🧪 1호 고객 파일럿 제품 — 폰에서 직접 눌러보세요 (결제는 알림만)
      </div>

      {/* INTRO */}
      {stage === 'intro' && (
        <section>
          <div style={brand}>Harness · AI 부모 진단</div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: C.ink, marginBottom: 10, lineHeight: 1.35 }}>
            우리 아이의 AI,<br />나는 어떤 기준을 갖고 있을까?
          </h1>
          <p style={{ color: C.muted, fontSize: '1rem', marginBottom: 24 }}>
            90초, 3가지 질문이면 충분합니다. 정답을 찾는 게 아니라, <b>지금 내가 어디에 서 있는지</b>를 봅니다.
          </p>
          <div style={{ ...card }}>
            <p style={{ fontSize: '.95rem', color: C.muted }}>
              주변 엄마들은 <span style={{ color: C.accent, fontWeight: 600 }}>"AI 시켜야 한다"</span>와{' '}
              <span style={{ color: C.danger, fontWeight: 600 }}>"AI가 망친다"</span>로 갈리는데,<br />
              정작 <b>우리 아이에게 뭐가 맞는지</b>는 아무도 안 알려줍니다.<br /><br />
              그 답답함부터 풀어보겠습니다.
            </p>
          </div>
          <button style={btn} onClick={() => { setQi(0); setStage('q') }}>90초 진단 시작하기 →</button>
          <p style={{ fontSize: '.8rem', color: C.faint, textAlign: 'center', marginTop: 10 }}>결제·회원가입 없이 결과를 먼저 받아보세요.</p>
        </section>
      )}

      {/* QUESTIONS */}
      {stage === 'q' && (
        <section>
          <div style={{ height: 5, background: C.border, borderRadius: 99, margin: '4px 0 26px', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${((qi + 1) / 3) * 100}%`, background: `linear-gradient(90deg,${C.accent},${C.cyan})`, borderRadius: 99, transition: 'width .4s ease' }} />
          </div>
          <div style={{ fontSize: '.78rem', fontWeight: 700, color: C.accent, letterSpacing: '.04em', marginBottom: 8, textTransform: 'uppercase' }}>{QUESTIONS[qi].label}</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: C.ink, marginBottom: 20, lineHeight: 1.4 }}>{QUESTIONS[qi].title}</div>
          {QUESTIONS[qi].opts.map((o, i) => (
            <button key={i} style={opt(false)} onClick={() => selectQ(i)}>{o}</button>
          ))}
          {qi > 0 && <button style={ghost} onClick={() => setQi(qi - 1)}>← 이전</button>}
        </section>
      )}

      {/* BARNUM */}
      {stage === 'barnum' && (
        <section>
          <div style={brand}>분석 중</div>
          <div style={{ ...card, fontSize: '1.05rem', lineHeight: 1.75, minHeight: 140 }}>
            {barnumShown === 0 && <span style={{ color: C.faint }}>● ● ●</span>}
            {(BARNUM[answers.q1 ?? 2] ?? BARNUM[2]).slice(0, barnumShown).map((line, i) => (
              <p key={i} style={{ marginBottom: 14 }}>{line}</p>
            ))}
          </div>
          {barnumShown >= (BARNUM[answers.q1 ?? 2] ?? BARNUM[2]).length && (
            <button style={btn} onClick={() => setStage('deep')}>네, 맞아요 — 더 볼게요 →</button>
          )}
        </section>
      )}

      {/* DEEP */}
      {stage === 'deep' && (
        <section>
          <div style={{ fontSize: '.78rem', fontWeight: 700, color: C.accent, letterSpacing: '.04em', marginBottom: 8, textTransform: 'uppercase' }}>조금만 더</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: C.ink, marginBottom: 16 }}>최근에 아이가 AI를 쓴 구체적인 상황이 있었나요?</div>
          <textarea
            value={deepText}
            onChange={(e) => setDeepText(e.target.value)}
            placeholder="예: 독후감 숙제를 AI로 써서 그대로 제출했어요 (자유롭게)"
            style={{ width: '100%', border: `1.5px solid ${C.border}`, borderRadius: 12, padding: 14, fontSize: '1rem', fontFamily: 'inherit', resize: 'none', minHeight: 80, marginBottom: 16 }}
          />
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: C.ink, marginBottom: 14 }}>어떤 모습이 가장 걱정되셨어요?</div>
          {DEEP_OPTS.map((o, i) => (
            <button key={i} style={opt(answers.deep === i)} onClick={() => setAnswers({ ...answers, deep: i })}>{o}</button>
          ))}
          <button style={{ ...btn, marginTop: 6 }} onClick={() => setStage('result')}>내 맞춤 진단 결과 보기 →</button>
        </section>
      )}

      {/* RESULT */}
      {stage === 'result' && (
        <section>
          <div style={brand}>진단 완료</div>
          <div style={{ textAlign: 'center', padding: '26px 20px', borderRadius: 18, background: 'linear-gradient(135deg,#1e293b,#0f172a)', color: '#fff', marginBottom: 20 }}>
            <div style={{ fontSize: '.78rem', letterSpacing: '.06em', opacity: .7, textTransform: 'uppercase' }}>나의 AI 부모 유형</div>
            <div style={{ fontSize: '1.7rem', fontWeight: 800, margin: '8px 0 4px' }}>{ty.t}</div>
            <div style={{ fontSize: '.95rem', opacity: .9 }}>{ty.d}</div>
          </div>

          <div style={card}>
            <span style={{ display: 'inline-block', background: C.warningSoft, color: C.warning, fontSize: '.78rem', fontWeight: 700, padding: '4px 11px', borderRadius: 99, marginBottom: 14 }}>우리 아이: {ty.stage}</span>
            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: C.ink, marginBottom: 4 }}>지금 가장 중요한 것 3가지</h2>
            <p style={{ fontSize: '.9rem', color: C.faint, marginBottom: 14 }}>진단 결과에 맞춰 자동 정리했습니다.</p>

            <RxRow open icon="✓" head="오늘 당장" text='"AI를 왜 쓰는지" 아이에게 한 번 물어보세요. 이 질문 하나로 아이의 인식이 달라집니다.' />
            <RxRow open icon="✓" head="이번 주 안에" text={RX2[answers.q2 ?? 0] ?? RX2[0]} />
            <RxRow lock icon="🔒" head="가장 중요한 핵심 — 이게 없으면 1·2도 무효" text="○○님 아이의 구체적 상황에 맞는 접근법은…" lockLabel="🔒 맞춤 처방에서 공개됩니다" />
          </div>

          <div style={{ background: `linear-gradient(135deg,${C.accentSoft},#eff6ff)`, border: `1.5px solid ${C.accent}`, borderRadius: 16, padding: 20, marginBottom: 14 }}>
            <span style={{ display: 'inline-block', background: C.danger, color: '#fff', fontSize: '.72rem', fontWeight: 700, padding: '3px 9px', borderRadius: 6, marginBottom: 10 }}>진단받은 분 한정 · 오늘만</span>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: C.ink, margin: '4px 0 8px' }}>○○님 가정만을 위한 맞춤 처방</h3>
            <p style={{ fontSize: '.92rem', color: C.muted, marginBottom: 14 }}>오늘 받은 진단을 바탕으로, 우리 아이 상황에 정확히 맞춘 7일 행동 가이드를 드립니다.</p>
            <div><span style={{ fontSize: '1.6rem', fontWeight: 800, color: C.accent }}>₩9,900</span><span style={{ color: C.faint, textDecoration: 'line-through', fontSize: '1rem', marginLeft: 8 }}>₩49,000</span></div>
            <button style={{ ...btn, marginTop: 14 }} onClick={() => alert('파일럿: 실제 버전에서는 ₩9,900 결제 → 맞춤 처방 PDF가 생성됩니다.\n\n[다음 단계 산출물]\n· 7일 행동 가이드\n· 우리 아이 유형별 대화 스크립트\n· 부모용 AI 실습 체크리스트')}>맞춤 처방 받기 →</button>
          </div>

          <div style={{ background: `linear-gradient(135deg,${C.successSoft},#ecfdf5)`, border: `1.5px solid ${C.success}`, borderRadius: 16, padding: 20, marginBottom: 14 }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: C.success, margin: '0 0 8px' }}>또는 — 부모 먼저 4주 과정</h3>
            <p style={{ fontSize: '.92rem', color: C.muted, marginBottom: 14 }}>"부모가 AI를 먼저 이해한 후 아이를 가이드하는 법" · 2주 무료 체험</p>
            <button style={{ ...btn, background: C.success, boxShadow: '0 4px 14px rgba(5,150,105,.25)' }} onClick={() => alert('파일럿: 실제 버전에서는 4주 부모 AX 과정 2주 무료 체험이 시작됩니다.')}>2주 무료로 시작하기 →</button>
          </div>

          <button style={ghost} onClick={() => setStage('share')}>내 결과 카드 공유하기</button>
          <button style={{ ...ghost, marginTop: 8 }} onClick={() => { setStage('intro'); setAnswers({}); setQi(0); setDeepText('') }}>처음부터 다시</button>
        </section>
      )}

      {/* SHARE */}
      {stage === 'share' && (
        <section>
          <div style={brand}>공유</div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: C.ink, marginBottom: 8 }}>친구에게 보여주세요</h2>
          <p style={{ color: C.muted, fontSize: '1rem', marginBottom: 18 }}>같은 고민을 하는 엄마에게 가장 도움이 됩니다.</p>
          <div style={{ background: `linear-gradient(135deg,${C.accent},${C.cyan})`, borderRadius: 18, padding: 24, color: '#fff', textAlign: 'center', marginBottom: 16 }}>
            <div style={{ fontSize: '.78rem', opacity: .85, letterSpacing: '.05em' }}>📋 나의 AI 부모 유형</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, margin: '6px 0' }}>{ty.t}</div>
            <div style={{ fontSize: '.9rem', opacity: .92 }}>"{ty.d}"</div>
            <div style={{ height: 1, background: 'rgba(255,255,255,.25)', margin: '16px 0' }} />
            <div style={{ fontSize: '.78rem', opacity: .85 }}>우리 아이</div>
            <div style={{ fontSize: '1.15rem', fontWeight: 800, margin: '6px 0' }}>{ty.stage}</div>
            <div style={{ fontSize: '.9rem', opacity: .92 }}>→ 지금이 골든 타임</div>
            <div style={{ fontSize: '.72rem', opacity: .7, marginTop: 14, letterSpacing: '.08em' }}>진단 by Harness</div>
          </div>
          <button style={btn} onClick={() => alert('실제 버전에서는 카카오톡·인스타로 공유됩니다 (파일럿)')}>카카오톡으로 공유하기</button>
          <button style={ghost} onClick={() => setStage('result')}>← 결과로 돌아가기</button>
        </section>
      )}
    </div>
  )
}

function RxRow({ lock, icon, head, text, lockLabel }: { open?: boolean; lock?: boolean; icon: string; head: string; text: string; lockLabel?: string }) {
  return (
    <div style={{ display: 'flex', gap: 13, padding: '15px 0', borderBottom: `1px solid ${C.border}` }}>
      <div style={{ flexShrink: 0, width: 26, height: 26, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '.85rem', fontWeight: 700, background: lock ? C.warningSoft : C.successSoft, color: lock ? C.warning : C.success }}>{icon}</div>
      <div>
        <strong style={{ display: 'block', fontSize: '.78rem', color: C.faint, fontWeight: 600, marginBottom: 3, textTransform: 'uppercase', letterSpacing: '.03em' }}>{head}</strong>
        <div style={{ fontSize: '1rem', color: lock ? C.faint : C.ink, fontWeight: 500 }}>{text}</div>
        {lockLabel && <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: '.85rem', color: C.warning, fontWeight: 600, marginTop: 4 }}>{lockLabel}</span>}
      </div>
    </div>
  )
}
