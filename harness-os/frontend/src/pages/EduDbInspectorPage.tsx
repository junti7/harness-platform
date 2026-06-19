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

function useIsMobile(breakpoint = 980): boolean {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth <= breakpoint : false
  )

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint}px)`)
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches)
    setIsMobile(mq.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [breakpoint])

  return isMobile
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
  const isMobile = useIsMobile()

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

  const palette = {
    text: '#0f172a',
    textStrong: '#020617',
    textMuted: '#334155',
    textSoft: '#475569',
    border: '#cbd5e1',
    borderSoft: '#dbe4ee',
    surface: '#ffffff',
    surfaceMuted: '#f8fafc',
    surfaceActive: '#dff7f3',
  } as const

  const inspectorGridTemplate = isMobile ? '1fr' : '360px minmax(0, 1fr)'
  const compactTableMinWidth = isMobile ? 720 : 820
  const rawTableMinWidth = isMobile ? 900 : 1200

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <section
        style={{
          background: 'linear-gradient(135deg,#f8fafc,#ecfeff 50%,#fff7ed)',
          border: '1px solid #dbeafe',
          borderRadius: 18,
          padding: '18px 20px',
        }}
      >
        <div style={{ fontSize: '.78rem', color: '#0f766e', fontWeight: 800, letterSpacing: '.04em', textTransform: 'uppercase', marginBottom: 6 }}>
          Database Transparency
        </div>
        <h2 style={{ margin: '0 0 8px', fontSize: '1.25rem', color: '#0f172a' }}>Edu DB Inspector</h2>
        <p style={{ margin: 0, fontSize: '.92rem', lineHeight: 1.65, color: '#475569', maxWidth: 1080 }}>
          각 테이블이나 뷰를 누르면 바로 그 구조와 sample row를 원시 데이터프레임처럼 볼 수 있게 만든 화면입니다. 모바일에서는 표를 줄이지 않고 가로 스크롤로 그대로 조회합니다.
        </p>
      </section>

      {error && (
        <section style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', borderRadius: 16, padding: '14px 16px' }}>
          <strong>불러오기 실패</strong>
          <div style={{ marginTop: 6 }}>{error}</div>
        </section>
      )}

      <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
        <div style={{ fontSize: '.76rem', letterSpacing: '.08em', textTransform: 'uppercase', color: palette.textMuted, fontWeight: 800, marginBottom: 10 }}>
          Summary Dataframe
        </div>
        <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
          <table style={{ minWidth: compactTableMinWidth, width: '100%', borderCollapse: 'collapse', fontSize: '.9rem', color: palette.text }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>expected_tables_count</th>
                <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>actual_tables_count</th>
                <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>missing_tables</th>
                <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>missing_views</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', fontWeight: 700, color: palette.textStrong }}>{bundle?.expected_tables?.length ?? '-'}</td>
                <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', fontWeight: 700, color: palette.textStrong }}>{bundle?.actual_tables?.length ?? '-'}</td>
                <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', color: '#b91c1c', fontWeight: 700 }}>{(bundle?.missing_expected_tables || []).join(', ') || '(none)'}</td>
                <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', color: '#b91c1c', fontWeight: 700 }}>{(bundle?.missing_expected_views || []).join(', ') || '(none)'}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: inspectorGridTemplate, gap: 16, alignItems: 'start' }}>
        <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: '.76rem', letterSpacing: '.08em', textTransform: 'uppercase', color: palette.textMuted, fontWeight: 800 }}>Table List</div>
            <h3 style={{ margin: '6px 0 0', fontSize: '1.04rem', color: palette.textStrong }}>Object inventory</h3>
          </div>
          <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
            <table style={{ minWidth: 560, width: '100%', borderCollapse: 'collapse', fontSize: '.88rem', color: palette.text }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>object_name</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>type</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>exists</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>rows</th>
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
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', fontFamily: 'monospace', color: palette.textStrong, fontWeight: 700 }}>{row.name}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{row.type}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', color: row.exists ? '#166534' : '#b91c1c', fontWeight: 700 }}>{String(row.exists)}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{String(row.rowCount)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>

        <div style={{ display: 'grid', gap: 16 }}>
          <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 12, flexWrap: 'wrap' }}>
              <div>
                <div style={{ fontSize: '.76rem', letterSpacing: '.08em', textTransform: 'uppercase', color: palette.textMuted, fontWeight: 800 }}>Selected Table</div>
                <h3 style={{ margin: '6px 0 0', fontSize: '1.08rem', color: palette.textStrong }}>{selectedName || '선택 없음'}</h3>
              </div>
              {detailLoading && <div style={{ color: palette.textSoft, fontSize: '.88rem', fontWeight: 600 }}>불러오는 중…</div>}
            </div>
            {selectedObject?.error ? (
              <div style={{ color: '#b91c1c' }}>{selectedObject.error}</div>
            ) : (
              <div style={{ display: 'grid', gap: 16 }}>
                <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
                  <table style={{ minWidth: compactTableMinWidth, width: '100%', borderCollapse: 'collapse', fontSize: '.9rem', color: palette.text }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>type</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>exists</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>row_count</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>owner</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>source_of_truth</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{selectedObject?.type ?? '-'}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', fontWeight: 700 }}>{String(selectedObject?.exists ?? '-')}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{String(selectedObject?.row_count ?? '-')}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{selectedObject?.owner || 'n/a'}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', color: palette.textSoft }}>{selectedObject?.source_of_truth || 'n/a'}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div>
                  <h4 style={{ margin: '0 0 8px', color: palette.textStrong }}>Columns dataframe</h4>
                  <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
                    <table style={{ minWidth: compactTableMinWidth, width: '100%', borderCollapse: 'collapse', fontSize: '.9rem', color: palette.text }}>
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline', marginBottom: 8, flexWrap: 'wrap' }}>
                    <h4 style={{ margin: 0, color: palette.textStrong }}>Sample rows dataframe</h4>
                    <div style={{ fontSize: '.82rem', color: palette.textSoft }}>object API sample limit: 20 rows</div>
                  </div>
                  {selectedSampleColumns.length > 0 ? (
                    <div style={{ overflowX: 'auto', WebkitOverflowScrolling: 'touch' }}>
                      <table style={{ minWidth: rawTableMinWidth, width: '100%', borderCollapse: 'collapse', fontSize: '.88rem', color: palette.text }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>idx</th>
                            {selectedSampleColumns.map((column) => (
                              <th
                                key={column}
                                style={{
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
                                style={{ background: active ? '#eff6ff' : palette.surface, cursor: 'pointer' }}
                              >
                                <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', color: palette.textSoft }}>{rowIndex}</td>
                                {selectedSampleColumns.map((column) => (
                                  <td key={`${rowIndex}-${column}`} style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', verticalAlign: 'top', minWidth: 160, maxWidth: 320 }}>
                                    <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.45 }}>
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
                    <div style={{ border: `1px solid ${palette.borderSoft}`, borderRadius: 12, padding: '12px 14px', color: palette.textSoft }}>
                      sample row가 없습니다.
                    </div>
                  )}
                </div>

                <div>
                  <h4 style={{ margin: '0 0 8px', color: palette.textStrong }}>Selected sample row raw JSON</h4>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#0f172a', color: '#e2e8f0', padding: 14, borderRadius: 16, fontSize: '.8rem', lineHeight: 1.55, maxHeight: 320, overflow: 'auto' }}>
{JSON.stringify(selectedSampleRow, null, 2)}
                  </pre>
                </div>

                <div>
                  <h4 style={{ margin: '0 0 8px', color: palette.textStrong }}>Indexes / Definition raw JSON</h4>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#0f172a', color: '#e2e8f0', padding: 14, borderRadius: 16, fontSize: '.8rem', lineHeight: 1.55, maxHeight: 420, overflow: 'auto' }}>
{JSON.stringify({ indexes: selectedObject?.indexes || [], definition: selectedObject?.definition || null }, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </section>

          <section style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 16 }}>
            <div style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
              <h3 style={{ margin: '0 0 10px', fontSize: '1rem', color: palette.textStrong }}>Latest Pipeline Runs raw JSON</h3>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#0f172a', color: '#e2e8f0', padding: 14, borderRadius: 16, fontSize: '.8rem', lineHeight: 1.55, maxHeight: 360, overflow: 'auto' }}>
{JSON.stringify(bundle?.latest_pipeline_runs || [], null, 2)}
              </pre>
            </div>
            <div style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
              <h3 style={{ margin: '0 0 10px', fontSize: '1rem', color: palette.textStrong }}>Latest Dead Letter Queue raw JSON</h3>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#0f172a', color: '#e2e8f0', padding: 14, borderRadius: 16, fontSize: '.8rem', lineHeight: 1.55, maxHeight: 360, overflow: 'auto' }}>
{JSON.stringify(bundle?.latest_dead_letter_queue || [], null, 2)}
              </pre>
            </div>
          </section>

          <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '1rem', color: palette.textStrong }}>Customer-Facing Retrieval Debug</h3>
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'minmax(0,1fr) 120px 90px 140px', gap: 10, alignItems: 'end' }}>
              <div>
                <label style={{ display: 'block', fontSize: '.8rem', color: palette.textMuted, fontWeight: 800, marginBottom: 6 }}>query</label>
                <textarea value={query} onChange={(e) => setQuery(e.target.value)} style={{ width: '100%', minHeight: 92, borderRadius: 14, border: `1px solid ${palette.border}`, padding: 12, color: palette.textStrong, background: palette.surfaceMuted }} />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '.8rem', color: palette.textMuted, fontWeight: 800, marginBottom: 6 }}>segment</label>
                <select value={segment} onChange={(e) => setSegment(e.target.value as 'parent' | 'worker')} style={{ width: '100%', borderRadius: 14, border: `1px solid ${palette.border}`, padding: 12, color: palette.textStrong, background: palette.surfaceMuted }}>
                  <option value="parent">parent</option>
                  <option value="worker">worker</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '.8rem', color: palette.textMuted, fontWeight: 800, marginBottom: 6 }}>k</label>
                <input type="number" min={1} max={12} value={k} onChange={(e) => setK(Number(e.target.value))} style={{ width: '100%', borderRadius: 14, border: `1px solid ${palette.border}`, padding: 12, color: palette.textStrong, background: palette.surfaceMuted }} />
              </div>
              <button type="button" onClick={() => void runDebug()} style={{ border: 'none', borderRadius: 14, background: '#0f172a', color: '#fff', padding: '12px 14px', fontWeight: 800 }}>
                {debugLoading ? '실행 중…' : '실행'}
              </button>
            </div>
            <pre style={{ margin: '14px 0 0', whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#0f172a', color: '#e2e8f0', padding: 14, borderRadius: 16, fontSize: '.8rem', lineHeight: 1.55, maxHeight: 420, overflow: 'auto' }}>
{JSON.stringify(debugResult || {}, null, 2)}
            </pre>
          </section>
        </div>
      </section>

      {loading && <div style={{ color: palette.textSoft, fontWeight: 600 }}>투명성 스냅샷을 불러오는 중…</div>}
    </div>
  )
}
