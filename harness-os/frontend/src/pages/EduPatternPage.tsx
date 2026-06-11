import { EduPatternMonitor } from '../components/EduPatternMonitor'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

export function EduPatternPage({ apiBase, authHeaders }: Props) {
  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <section
        style={{
          background: 'linear-gradient(135deg,#f8fafc,#eff6ff)',
          border: '1px solid #dbeafe',
          borderRadius: 18,
          padding: '18px 20px',
        }}
      >
        <div style={{ fontSize: '.78rem', color: '#2563eb', fontWeight: 800, letterSpacing: '.04em', textTransform: 'uppercase', marginBottom: 6 }}>
          Education Intelligence
        </div>
        <h2 style={{ margin: '0 0 8px', fontSize: '1.25rem', color: '#0f172a' }}>패턴 인텔리전스 관제</h2>
        <p style={{ margin: 0, fontSize: '.92rem', lineHeight: 1.65, color: '#475569', maxWidth: 900 }}>
          부모 AI 진단에서 어떤 자료를 읽었고, 어떤 로직으로 고민 패턴을 만들었는지, 그리고 그 결과가 Fact Check와 Red Team을 통과했는지를
          실시간으로 투명하게 확인하는 전용 화면입니다. 목적은 고객을 고정관념으로 분류하는 것이 아니라, 반복적으로 나타나는 주요 고민과 불만 신호를
          더 빨리 읽고 다음 답변 품질을 높이는 것입니다.
        </p>
      </section>

      <EduPatternMonitor apiBase={apiBase} authHeaders={authHeaders} />
    </div>
  )
}
