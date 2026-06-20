import { useEffect, useState } from 'react'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
}

type Bundle = {
  expected_tables?: string[]
  actual_tables?: string[]
  missing_expected_tables?: string[]
  missing_expected_views?: string[]
  tables?: Record<string, any>
  views?: Record<string, any>
  latest_pipeline_runs?: any[]
  latest_dead_letter_queue?: any[]
}

const OBJECT_METADATA: Record<string, { label: string; meaning: string; analyticsUse: string }> = {
  dead_letter_queue: {
    label: 'ingestion failure queue',
    meaning: '파이프라인이 적재에 실패한 레코드를 모아두는 큐입니다. 실패 원문과 에러 메시지가 그대로 남습니다.',
    analyticsUse: '어떤 소스/레코드가 반복적으로 깨지는지, 재시도 우선순위를 어떻게 잡을지 볼 때 확인합니다.',
  },
  pipeline_runs: {
    label: 'pipeline audit ledger',
    meaning: '배치 실행 단위의 시작/종료/상태/상관관계 ID를 남기는 감사 원장입니다.',
    analyticsUse: '언제 어떤 파이프라인이 돌았는지, 성공/실패 추세가 어떤지, 특정 DLQ와 어떤 run이 연결되는지 볼 때 씁니다.',
  },
  edu_knowledge_items: {
    label: 'normalized knowledge store',
    meaning: '교육용 근거 데이터를 정규화해서 적재하는 중심 테이블입니다. source, segment, rights, body, cite가 이 레이어에 모입니다.',
    analyticsUse: '실제 retrieval 후보군, 품질 점수, rights 경계, source 다양성을 분석할 때 핵심으로 봐야 하는 테이블입니다.',
  },
  edu_knowledge_items_customer_facing: {
    label: 'customer-safe retrieval view',
    meaning: '고객 응답에 노출 가능한 행만 필터링한 canonical view입니다. internal-only나 rights 위반 후보를 제외하는 경계 역할을 합니다.',
    analyticsUse: '실제 customer-facing retrieval이 어떤 안전한 근거만 읽어야 하는지 검증할 때 봅니다.',
  },
  edu_rag_accumulation: {
    label: 'generated accumulation buffer',
    meaning: 'RAG 누적/승격 후보를 담는 테이블입니다. 생성 결과를 바로 지식으로 승격하지 않고 중간 완충 레이어에 둡니다.',
    analyticsUse: '어떤 생성 산출물이 재사용 후보로 쌓이고 있는지, promoted 여부와 provenance를 분석할 때 봅니다.',
  },
  edu_customers: {
    label: 'customer identity table',
    meaning: '세그먼트, 이름, 연락수단, 선호 설정 등 고객 식별/설정 정보를 담는 기본 테이블입니다.',
    analyticsUse: '세그먼트 분포, 재방문 패턴, 로그인 채널, active 상태를 고객 단위로 볼 때 확인합니다.',
  },
  edu_cases: {
    label: 'case-level 상담 헤더',
    meaning: '한 고객의 상담/교육 케이스 단위 헤더입니다. 현재 phase, 상태, 최근 턴 시점이 이 레벨에 있습니다.',
    analyticsUse: '케이스 진행 상태, 단계별 퍼널, 장기 미종결 케이스를 파악할 때 기준 테이블이 됩니다.',
  },
  edu_case_turns: {
    label: 'turn-level transcript structure',
    meaning: '상담 케이스 안의 턴별 대화 구조화 테이블입니다. role, text, phase, tone level 등이 저장됩니다.',
    analyticsUse: '대화 흐름, 단계 전이, 패턴 추출, 턴 수 분포를 분석할 때 가장 직접적인 transcript 레이어입니다.',
  },
  edu_case_snapshots: {
    label: 'case state snapshots',
    meaning: '케이스 상태를 특정 시점에 스냅샷으로 저장하는 테이블입니다.',
    analyticsUse: 'phase 변화 전후 상태 비교, resume 복구, 특정 시점 진단값 회고에 씁니다.',
  },
  edu_case_offers: {
    label: 'offer tracking table',
    meaning: '케이스 중 제안된 offer 또는 후속 제안 이력을 저장하는 테이블입니다.',
    analyticsUse: '어느 단계에서 어떤 제안이 노출되는지, offer conversion과 연결할 때 봅니다.',
  },
  edu_magic_links: {
    label: 'magic-link auth ledger',
    meaning: '이메일 기반 이어하기 링크 발급/사용 기록을 담는 인증 보조 테이블입니다.',
    analyticsUse: '재진입 퍼널, 링크 만료/실패, 기기 전환 진입 흐름을 볼 때 확인합니다.',
  },
  edu_conversation_log: {
    label: 'append-only raw conversation ledger',
    meaning: '구조화된 case_turns와 별개로, 요청/응답 원문을 빠짐없이 남기는 append-only 원장입니다.',
    analyticsUse: '누락 없는 원문 감사, 법무/운영 추적, 구조화 레이어와 raw 원장의 차이를 대조할 때 중요합니다.',
  },
}

function useIsNarrowLayout(breakpoint = 1280): boolean {
  const [isNarrowLayout, setIsNarrowLayout] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth <= breakpoint : false
  )

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint}px)`)
    const handler = (e: MediaQueryListEvent) => setIsNarrowLayout(e.matches)
    setIsNarrowLayout(mq.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [breakpoint])

  return isNarrowLayout
}

function formatCellValue(value: unknown): string {
  if (value === null) return 'null'
  if (value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function collectRowColumns(rows: any[]): string[] {
  const seen = new Set<string>()
  for (const row of rows) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) continue
    for (const key of Object.keys(row)) seen.add(key)
  }
  return Array.from(seen)
}

export function EduDbInspectorPage({ apiBase, authHeaders }: Props) {
  const [bundle, setBundle] = useState<Bundle | null>(null)
  const [selectedName, setSelectedName] = useState<string>('')
  const [selectedObject, setSelectedObject] = useState<any | null>(null)
  const [selectedSampleRowIndex, setSelectedSampleRowIndex] = useState(0)
  const [debugResult, setDebugResult] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [debugLoading, setDebugLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('중학생 숙제할 때 AI 답부터 보는 아이를 부모가 어떻게 다뤄야 하나요?')
  const [segment, setSegment] = useState<'parent' | 'worker'>('parent')
  const [k, setK] = useState(6)
  const isNarrowLayout = useIsNarrowLayout()

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${apiBase}/api/admin/edu/db/transparency`, { headers: authHeaders() })
        if (!res.ok) throw new Error(`transparency API ${res.status}`)
        const data = await res.json()
        if (cancelled) return
        setBundle(data)
        const first = Object.keys(data.tables || {})[0] || Object.keys(data.views || {})[0] || ''
        setSelectedName(first)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'transparency load failed')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => { cancelled = true }
  }, [apiBase, authHeaders])

  useEffect(() => {
    let cancelled = false
    async function loadObject() {
      if (!selectedName) return
      setDetailLoading(true)
      try {
        const res = await fetch(
          `${apiBase}/api/admin/edu/db/object?name=${encodeURIComponent(selectedName)}&limit=20`,
          { headers: authHeaders() },
        )
        if (!res.ok) throw new Error(`object API ${res.status}`)
        const data = await res.json()
        if (!cancelled) setSelectedObject(data)
      } catch (err) {
        if (!cancelled) setSelectedObject({ error: err instanceof Error ? err.message : 'object load failed' })
      } finally {
        if (!cancelled) setDetailLoading(false)
      }
    }
    void loadObject()
    return () => { cancelled = true }
  }, [selectedName, apiBase, authHeaders])

  useEffect(() => {
    setSelectedSampleRowIndex(0)
  }, [selectedName])

  async function runDebug() {
    setDebugLoading(true)
    try {
      const res = await fetch(
        `${apiBase}/api/admin/edu/db/retrieval-debug?query=${encodeURIComponent(query)}&segment=${encodeURIComponent(segment)}&k=${encodeURIComponent(k)}`,
        { headers: authHeaders() },
      )
      if (!res.ok) throw new Error(`retrieval debug API ${res.status}`)
      setDebugResult(await res.json())
    } catch (err) {
      setDebugResult({ error: err instanceof Error ? err.message : 'retrieval debug failed' })
    } finally {
      setDebugLoading(false)
    }
  }

  const objectNames = [
    ...Object.keys(bundle?.tables || {}),
    ...Object.keys(bundle?.views || {}),
  ]

  const schemaRows = objectNames.map((name) => {
    const info = bundle?.tables?.[name] || bundle?.views?.[name] || {}
    return {
      name,
      type: info?.type || (bundle?.views?.[name] ? 'view' : 'table'),
      exists: Boolean(info?.exists),
      rowCount: info?.row_count ?? '-',
      owner: info?.owner || 'unknown',
      sourceOfTruth: info?.source_of_truth || 'n/a',
    }
  })

  const selectedSampleRows = Array.isArray(selectedObject?.sample_rows) ? selectedObject.sample_rows : []
  const selectedSampleColumns = collectRowColumns(selectedSampleRows)
  const selectedSampleRow = selectedSampleRows[selectedSampleRowIndex] ?? null
  const selectedMeta = selectedName ? OBJECT_METADATA[selectedName] : null

  const palette = {
    text: '#0f172a',
    textStrong: '#020617',
    textMuted: '#334155',
    textSoft: '#475569',
    border: '#cbd5e1',
    borderSoft: '#dbe4ee',
    surface: '#ffffff',
    surfaceMuted: '#f8fafc',
    surfaceActive: '#e0f2fe',
    codeBg: '#0f172a',
    codeText: '#e2e8f0',
  } as const

  const compactTableMinWidth = isNarrowLayout ? 560 : 680
  const rawTableMinWidth = isNarrowLayout ? 680 : 860
  const sectionTitleStyle = { margin: 0, fontSize: '.98rem', color: palette.textStrong } as const
  const codePanelStyle = {
    margin: 0,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
    background: palette.codeBg,
    color: palette.codeText,
    padding: 14,
    borderRadius: 10,
    fontSize: '.79rem',
    lineHeight: 1.55,
    overflow: 'auto',
  } as const

  return (
    <div style={{ display: 'grid', gap: 12, width: '100%', maxWidth: '100%' }}>
      <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 12, padding: '12px 14px' }}>
        <h2 style={{ margin: 0, fontSize: '1.05rem', color: palette.textStrong }}>Edu DB Inspector</h2>
        <p style={{ margin: '6px 0 0', color: palette.textSoft, fontSize: '.86rem', lineHeight: 1.5 }}>
          raw table browser. object list에서 선택하면 컬럼 구조와 sample rows dataframe이 바로 열립니다.
        </p>
      </section>

      {error && (
        <section style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', borderRadius: 12, padding: '12px 14px' }}>
          <strong>불러오기 실패</strong>
          <div style={{ marginTop: 6 }}>{error}</div>
        </section>
      )}

      <section style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12, alignItems: 'start', width: '100%', maxWidth: '100%' }}>
        <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12, minWidth: 0 }}>
          <div style={{ marginBottom: 10 }}>
            <h3 style={sectionTitleStyle}>Object List</h3>
            <p style={{ margin: '4px 0 0', color: palette.textSoft, fontSize: '.82rem' }}>
              actual `{bundle?.actual_tables?.length ?? 0}` · missing tables `{(bundle?.missing_expected_tables || []).join(', ') || '(none)'}`
            </p>
          </div>
          <div style={{ width: '100%', maxWidth: '100%', overflowX: 'auto', overflowY: 'hidden', WebkitOverflowScrolling: 'touch' }}>
            <table style={{ minWidth: 520, width: '100%', borderCollapse: 'collapse', fontSize: '.86rem', color: palette.text }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>object_name</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>type</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>exists</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>rows</th>
                </tr>
              </thead>
              <tbody>
                {schemaRows.map((row) => {
                  const active = selectedName === row.name
                  return (
                    <tr
                      key={row.name}
                      onClick={() => setSelectedName(row.name)}
                      style={{ background: active ? palette.surfaceActive : palette.surface, cursor: 'pointer' }}
                    >
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', fontFamily: 'monospace', color: palette.textStrong, fontWeight: 700 }}>{row.name}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px' }}>{row.type}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', color: row.exists ? '#166534' : '#b91c1c', fontWeight: 700 }}>{String(row.exists)}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px' }}>{String(row.rowCount)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>

        <div style={{ display: 'grid', gap: 12, minWidth: 0, width: '100%', maxWidth: '100%' }}>
          <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 12, padding: 12, minWidth: 0, overflow: 'hidden' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
              <div>
                <h3 style={sectionTitleStyle}>{selectedName || '선택 없음'}</h3>
                <p style={{ margin: '4px 0 0', color: palette.textSoft, fontSize: '.82rem' }}>raw structure + raw rows</p>
              </div>
              {detailLoading && <div style={{ color: palette.textSoft, fontSize: '.86rem', fontWeight: 600 }}>불러오는 중…</div>}
            </div>
            {selectedObject?.error ? (
              <div style={{ color: '#b91c1c' }}>{selectedObject.error}</div>
            ) : (
              <div style={{ display: 'grid', gap: 12 }}>
                {selectedMeta && (
                  <div style={{ background: palette.surfaceMuted, border: `1px solid ${palette.borderSoft}`, borderRadius: 10, padding: '12px 14px' }}>
                    <div style={{ fontSize: '.8rem', color: palette.textMuted, fontWeight: 800, marginBottom: 6 }}>{selectedMeta.label}</div>
                    <div style={{ fontSize: '.9rem', color: palette.textStrong, lineHeight: 1.55, marginBottom: 8 }}>{selectedMeta.meaning}</div>
                    <div style={{ fontSize: '.85rem', color: palette.textSoft, lineHeight: 1.55 }}>분석 포인트: {selectedMeta.analyticsUse}</div>
                  </div>
                )}
                <div style={{ width: '100%', maxWidth: '100%', overflowX: 'auto', overflowY: 'hidden', WebkitOverflowScrolling: 'touch' }}>
                  <table style={{ minWidth: compactTableMinWidth, width: 'max-content', maxWidth: 'none', borderCollapse: 'collapse', fontSize: '.86rem', color: palette.text }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>type</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>exists</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>row_count</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>owner</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>source_of_truth</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px' }}>{selectedObject?.type ?? '-'}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', fontWeight: 700 }}>{String(selectedObject?.exists ?? '-')}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px' }}>{String(selectedObject?.row_count ?? '-')}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px' }}>{selectedObject?.owner || 'n/a'}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', color: palette.textSoft }}>{selectedObject?.source_of_truth || 'n/a'}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div>
                  <h4 style={sectionTitleStyle}>Columns dataframe</h4>
                  <div style={{ width: '100%', maxWidth: '100%', overflowX: 'auto', overflowY: 'hidden', WebkitOverflowScrolling: 'touch', marginTop: 8 }}>
                    <table style={{ minWidth: compactTableMinWidth, width: 'max-content', maxWidth: 'none', borderCollapse: 'collapse', fontSize: '.86rem', color: palette.text }}>
                      <thead>
                        <tr>
                          <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>idx</th>
                          <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>column</th>
                          <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>type</th>
                          <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>nullable</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(selectedObject?.columns || []).map((col: any, index: number) => (
                          <tr key={col.column_name}>
                            <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', color: palette.textSoft }}>{index}</td>
                            <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', fontFamily: 'monospace', color: palette.textStrong, fontWeight: 700 }}>{col.column_name}</td>
                            <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px' }}>{col.data_type}</td>
                            <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px' }}>{col.is_nullable}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline', flexWrap: 'wrap' }}>
                    <h4 style={sectionTitleStyle}>Sample rows dataframe</h4>
                    <div style={{ color: palette.textSoft, fontSize: '.8rem' }}>row click to raw JSON</div>
                  </div>
                  {selectedSampleColumns.length > 0 ? (
                    <div style={{ width: '100%', maxWidth: '100%', overflowX: 'auto', overflowY: 'hidden', WebkitOverflowScrolling: 'touch', marginTop: 8 }}>
                      <table style={{ minWidth: rawTableMinWidth, width: 'max-content', maxWidth: 'none', borderCollapse: 'collapse', fontSize: '.84rem', color: palette.text }}>
                        <thead>
                          <tr>
                            <th style={{ position: 'sticky', top: 0, background: palette.surfaceMuted, textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>idx</th>
                            {selectedSampleColumns.map((column) => (
                              <th
                                key={column}
                                style={{
                                  position: 'sticky',
                                  top: 0,
                                  background: palette.surfaceMuted,
                                  textAlign: 'left',
                                  borderBottom: `1px solid ${palette.border}`,
                                  padding: '8px 6px',
                                  color: palette.textMuted,
                                  fontWeight: 800,
                                  fontFamily: 'monospace',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                {column}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {selectedSampleRows.map((row: any, rowIndex: number) => {
                            const active = selectedSampleRowIndex === rowIndex
                            return (
                              <tr
                                key={`sample-row-${rowIndex}`}
                                onClick={() => setSelectedSampleRowIndex(rowIndex)}
                                style={{ background: active ? '#dbeafe' : palette.surface, cursor: 'pointer' }}
                              >
                                <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', color: palette.textSoft }}>{rowIndex}</td>
                                {selectedSampleColumns.map((column) => (
                                <td key={`${rowIndex}-${column}`} style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', verticalAlign: 'top', minWidth: 180 }}>
                                  <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.42 }}>
                                    {formatCellValue(row?.[column])}
                                  </div>
                                  </td>
                                ))}
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div style={{ border: `1px solid ${palette.borderSoft}`, borderRadius: 10, padding: '12px 14px', color: palette.textSoft, marginTop: 8 }}>
                      sample row가 없습니다.
                    </div>
                  )}
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12, minWidth: 0 }}>
                  <div>
                    <h4 style={sectionTitleStyle}>Selected sample row raw JSON</h4>
                    <pre style={{ ...codePanelStyle, marginTop: 8, maxHeight: 320 }}>
{JSON.stringify(selectedSampleRow, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <h4 style={sectionTitleStyle}>Indexes / Definition raw JSON</h4>
                    <pre style={{ ...codePanelStyle, marginTop: 8, maxHeight: 320 }}>
{JSON.stringify({ indexes: selectedObject?.indexes || [], definition: selectedObject?.definition || null }, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            )}
          </section>

          <details style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 12, padding: '10px 12px', minWidth: 0, overflow: 'hidden' }}>
            <summary style={{ cursor: 'pointer', color: palette.textStrong, fontWeight: 700 }}>Ancillary raw JSON</summary>
            <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12, minWidth: 0 }}>
                <div>
                  <h4 style={sectionTitleStyle}>Latest Pipeline Runs raw JSON</h4>
                  <pre style={{ ...codePanelStyle, marginTop: 8, maxHeight: 320 }}>
{JSON.stringify(bundle?.latest_pipeline_runs || [], null, 2)}
                  </pre>
                </div>
                <div>
                  <h4 style={sectionTitleStyle}>Latest Dead Letter Queue raw JSON</h4>
                  <pre style={{ ...codePanelStyle, marginTop: 8, maxHeight: 320 }}>
{JSON.stringify(bundle?.latest_dead_letter_queue || [], null, 2)}
                  </pre>
                </div>
              </div>

              <div>
                <h4 style={sectionTitleStyle}>Customer-Facing Retrieval Debug</h4>
                <div style={{ display: 'grid', gridTemplateColumns: isNarrowLayout ? '1fr' : 'minmax(0,1fr) 120px 90px 140px', gap: 10, alignItems: 'end', marginTop: 8 }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '.8rem', color: palette.textMuted, fontWeight: 800, marginBottom: 6 }}>query</label>
                    <textarea value={query} onChange={(e) => setQuery(e.target.value)} style={{ width: '100%', minHeight: 92, borderRadius: 10, border: `1px solid ${palette.border}`, padding: 12, color: palette.textStrong, background: palette.surfaceMuted }} />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '.8rem', color: palette.textMuted, fontWeight: 800, marginBottom: 6 }}>segment</label>
                    <select value={segment} onChange={(e) => setSegment(e.target.value as 'parent' | 'worker')} style={{ width: '100%', borderRadius: 10, border: `1px solid ${palette.border}`, padding: 12, color: palette.textStrong, background: palette.surfaceMuted }}>
                      <option value="parent">parent</option>
                      <option value="worker">worker</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '.8rem', color: palette.textMuted, fontWeight: 800, marginBottom: 6 }}>k</label>
                    <input type="number" min={1} max={12} value={k} onChange={(e) => setK(Number(e.target.value))} style={{ width: '100%', borderRadius: 10, border: `1px solid ${palette.border}`, padding: 12, color: palette.textStrong, background: palette.surfaceMuted }} />
                  </div>
                  <button type="button" onClick={() => void runDebug()} style={{ border: 'none', borderRadius: 10, background: '#0f172a', color: '#fff', padding: '12px 14px', fontWeight: 800 }}>
                    {debugLoading ? '실행 중…' : '실행'}
                  </button>
                </div>
                <pre style={{ ...codePanelStyle, marginTop: 12, maxHeight: 420 }}>
{JSON.stringify(debugResult || {}, null, 2)}
                </pre>
              </div>
            </div>
          </details>
        </div>
      </section>

      {loading && <div style={{ color: palette.textSoft, fontWeight: 600 }}>투명성 스냅샷을 불러오는 중…</div>}
    </div>
  )
}
