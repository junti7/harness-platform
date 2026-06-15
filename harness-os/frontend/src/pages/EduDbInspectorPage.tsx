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

export function EduDbInspectorPage({ apiBase, authHeaders }: Props) {
  const [bundle, setBundle] = useState<Bundle | null>(null)
  const [selectedName, setSelectedName] = useState<string>('')
  const [selectedObject, setSelectedObject] = useState<any | null>(null)
  const [debugResult, setDebugResult] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [debugLoading, setDebugLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('중학생 숙제할 때 AI 답부터 보는 아이를 부모가 어떻게 다뤄야 하나요?')
  const [segment, setSegment] = useState<'parent' | 'worker'>('parent')
  const [k, setK] = useState(6)

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
      expected: Object.prototype.hasOwnProperty.call(bundle?.tables || {}, name) || Object.prototype.hasOwnProperty.call(bundle?.views || {}, name),
      owner: info?.owner || 'unknown',
      rowCount: info?.row_count ?? '-',
      sourceOfTruth: info?.source_of_truth || 'n/a',
    }
  })

  const palette = {
    text: '#0f172a',
    textStrong: '#020617',
    textMuted: '#334155',
    textSoft: '#475569',
    border: '#cbd5e1',
    borderSoft: '#dbe4ee',
    surface: '#ffffff',
    surfaceMuted: '#f8fafc',
    surfaceStrong: '#eef4ff',
    surfaceActive: '#dff7f3',
    dangerSurface: '#fff7f7',
    dangerBorder: '#fca5a5',
  } as const

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
        <p style={{ margin: 0, fontSize: '.92rem', lineHeight: 1.65, color: '#475569', maxWidth: 960 }}>
          자료수집 데이터가 실제로 어떤 테이블과 뷰에 쌓였는지, 컬럼과 인덱스가 어떻게 생겼는지, 그리고 customer-facing retrieval이 어떤 경로를 타는지 숨기지 않고 그대로 보여주는 원시 관제 화면입니다.
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
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.9rem', color: palette.text }}>
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

      <section style={{ display: 'grid', gap: 16 }}>
        <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: '.76rem', letterSpacing: '.08em', textTransform: 'uppercase', color: palette.textMuted, fontWeight: 800 }}>Schema Dataframe</div>
              <h3 style={{ margin: '6px 0 0', fontSize: '1.04rem', color: palette.textStrong }}>Object inventory</h3>
            </div>
            <div style={{ fontSize: '.84rem', color: palette.textSoft, fontWeight: 600 }}>행을 클릭하면 아래에 상세 구조가 열립니다.</div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.9rem', color: palette.text }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>object_name</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>type</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>exists</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>row_count</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>owner</th>
                  <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>source_of_truth</th>
                </tr>
              </thead>
              <tbody>
                {schemaRows.map((row) => {
                  const active = selectedName === row.name
                  return (
                    <tr
                      key={row.name}
                      onClick={() => setSelectedName(row.name)}
                      style={{
                        background: active ? palette.surfaceActive : palette.surface,
                        cursor: 'pointer',
                      }}
                    >
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', fontFamily: 'monospace', color: palette.textStrong, fontWeight: 700 }}>{row.name}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{row.type}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', color: row.exists ? '#166534' : '#b91c1c', fontWeight: 700 }}>{String(row.exists)}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{String(row.rowCount)}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{row.owner}</td>
                      <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', color: palette.textSoft }}>{row.sourceOfTruth}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>

        <div style={{ display: 'grid', gap: 16 }}>
          <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: '.76rem', letterSpacing: '.08em', textTransform: 'uppercase', color: palette.textMuted, fontWeight: 800 }}>Selected Object Dataframe</div>
                <h3 style={{ margin: '6px 0 0', fontSize: '1.08rem', color: palette.textStrong }}>{selectedName || '선택 없음'}</h3>
              </div>
              {detailLoading && <div style={{ color: palette.textSoft, fontSize: '.88rem', fontWeight: 600 }}>불러오는 중…</div>}
            </div>
            {selectedObject?.error ? (
              <div style={{ color: '#b91c1c' }}>{selectedObject.error}</div>
            ) : (
              <>
                <div style={{ overflowX: 'auto', marginBottom: 16 }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.9rem', color: palette.text }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>type</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>exists</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>expected</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>row_count</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>owner</th>
                        <th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '10px 8px', color: palette.textMuted, fontWeight: 800 }}>source_of_truth</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{selectedObject?.type ?? '-'}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', fontWeight: 700 }}>{String(selectedObject?.exists ?? '-')}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', fontWeight: 700 }}>{String(selectedObject?.expected ?? '-')}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{String(selectedObject?.row_count ?? '-')}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px' }}>{selectedObject?.owner || 'n/a'}</td>
                        <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '10px 8px', color: palette.textSoft }}>{selectedObject?.source_of_truth || 'n/a'}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                  <div>
                    <h4 style={{ margin: '0 0 8px', color: palette.textStrong }}>Columns dataframe</h4>
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '.9rem', color: palette.text }}>
                        <thead><tr><th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>column</th><th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>type</th><th style={{ textAlign: 'left', borderBottom: `1px solid ${palette.border}`, padding: '8px 6px', color: palette.textMuted, fontWeight: 800 }}>nullable</th></tr></thead>
                        <tbody>
                          {(selectedObject?.columns || []).map((col: any) => (
                            <tr key={col.column_name}>
                              <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', fontFamily: 'monospace', color: palette.textStrong, fontWeight: 700 }}>{col.column_name}</td>
                              <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', color: palette.text }}>{col.data_type}</td>
                              <td style={{ borderBottom: `1px solid ${palette.borderSoft}`, padding: '8px 6px', color: palette.text }}>{col.is_nullable}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <div>
                    <h4 style={{ margin: '0 0 8px', color: palette.textStrong }}>Indexes / Definition</h4>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#0f172a', color: '#e2e8f0', padding: 14, borderRadius: 16, fontSize: '.8rem', lineHeight: 1.55, maxHeight: 420, overflow: 'auto' }}>
{JSON.stringify({ indexes: selectedObject?.indexes || [], definition: selectedObject?.definition || null }, null, 2)}
                    </pre>
                  </div>
                </div>
                <div style={{ marginTop: 14 }}>
                  <h4 style={{ margin: '0 0 8px', color: palette.textStrong }}>Sample Rows</h4>
                  <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#0f172a', color: '#e2e8f0', padding: 14, borderRadius: 16, fontSize: '.8rem', lineHeight: 1.55, maxHeight: 420, overflow: 'auto' }}>
{JSON.stringify(selectedObject?.sample_rows || [], null, 2)}
                  </pre>
                </div>
              </>
            )}
          </section>

          <section style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
              <h3 style={{ margin: '0 0 10px', fontSize: '1rem', color: palette.textStrong }}>Latest Pipeline Runs</h3>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#0f172a', color: '#e2e8f0', padding: 14, borderRadius: 16, fontSize: '.8rem', lineHeight: 1.55, maxHeight: 360, overflow: 'auto' }}>
{JSON.stringify(bundle?.latest_pipeline_runs || [], null, 2)}
              </pre>
            </div>
            <div style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
              <h3 style={{ margin: '0 0 10px', fontSize: '1rem', color: palette.textStrong }}>Latest Dead Letter Queue</h3>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word', background: '#0f172a', color: '#e2e8f0', padding: 14, borderRadius: 16, fontSize: '.8rem', lineHeight: 1.55, maxHeight: 360, overflow: 'auto' }}>
{JSON.stringify(bundle?.latest_dead_letter_queue || [], null, 2)}
              </pre>
            </div>
          </section>

          <section style={{ background: palette.surface, border: `1px solid ${palette.border}`, borderRadius: 18, padding: 16 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '1rem', color: palette.textStrong }}>Customer-Facing Retrieval Debug</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) 120px 90px 140px', gap: 10, alignItems: 'end' }}>
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
