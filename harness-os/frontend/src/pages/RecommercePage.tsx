import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './RecommercePage.css'

type Props = {
  apiBase: string
  authHeaders: () => Record<string, string>
  viewRole: 'ceo' | 'vp'
}

type ChecklistItem = { key: string; label: string; completed: boolean }
type Supplier = {
  id: string
  name: string
  contact_status: string
  evidence_status: string
  available_quantity: number
  quote_valid_until: string
  note: string
}
type Scores = Record<string, number>
type SkuCandidate = {
  id: string
  name: string
  supplier_id: string
  category: string
  conservative_sale_price: number
  full_variable_cost: number
  contribution: number
  contribution_rate: number
  total_score: number
  cost_review_condition_met: boolean
  evidence_status: string
  scores: Scores
}
type Workspace = {
  opportunity: { id: string; name: string; status: string; track: string }
  guardrails: { allowed: string[]; blocked: string[]; weekly_hours_cap: number; workspace_scope: string }
  phases: Array<{ id: number; label: string; state: string }>
  checklist: ChecklistItem[]
  suppliers: Supplier[]
  sku_candidates: SkuCandidate[]
  metrics: {
    weekly_hours: number
    checklist_completed: number
    checklist_total: number
    verified_suppliers: number
    supplier_count: number
    qualified_skus: number
    sku_count: number
  }
  allowed_categories: Array<{ value: string; label: string }>
  score_keys: string[]
  cost_keys: string[]
  stop_reasons: string[]
  next_action: string
  workspace_version: number
  updated_at?: string | null
  updated_by?: string | null
}
type MarketCandidate = {
  id: string; rank: number; name: string; query: string; category: string; why: string; training_goal: string
  risks: string[]; result_count: number; median_price: number | null; price_p25: number | null; price_p75: number | null
  market_low_price?: number; market_link?: string; image_url?: string; sample_size?: number; sample_mall_count?: number
  competitor_samples?: Array<{ name: string; price: number; mall: string; link: string }>; llm_score?: number
  conservative_sale_price?: number; max_allowable_supply_cost?: number; commercial_readiness?: string
}
type MarketResearch = {
  status: string; observed_at?: string | null; source?: string; method_note?: string
  selection_policy?: { human_manual_selection_allowed: boolean; llm_required: boolean; fail_closed: boolean; minimum_item_price: number }
  llm?: { provider?: string; model?: string; required?: boolean; error?: string | null }
  candidates: MarketCandidate[]; rejected: Array<{ query: string; reason: string; result_count?: number; median_price?: number | null }>
}


const COST_LABELS: Record<string, string> = {
  unit_purchase_cost: '상품 매입원가',
  platform_fee: '플랫폼 수수료',
  inbound_shipping: '입고 배송비',
  outbound_shipping: '출고 배송비',
  packaging_cost: '포장비',
  ad_coupon_cost: '광고·쿠폰비',
  return_defect_reserve: '반품·불량 충당금',
  labor_cost: '운영자 노동비',
  aging_markdown_loss: '재고 가격인하 손실',
  dispute_tax_reserve: '분쟁·세금 충당금',
}

const SCORE_LABELS: Record<string, string> = {
  demand: '수요', supply: '공급가', competition: '경쟁', shipping: '배송',
  returns: '반품', evidence: '증빙·안전', turnover: '회전', content: '콘텐츠',
}

const initialSupplierForm = {
  name: '', contact_status: 'not_contacted', evidence_status: 'unverified',
  available_quantity: 0, quote_valid_until: '', note: '',
}

const initialSkuForm = {
  name: '', supplier_id: '', category: 'stationery', conservative_sale_price: '',
  evidence_status: 'unverified', note: '', zero_cost_confirmed_keys: [] as string[],
  costs: Object.fromEntries(Object.keys(COST_LABELS).map(key => [key, ''])) as Record<string, string>,
  scores: Object.fromEntries(Object.keys(SCORE_LABELS).map(key => [key, 0])) as Scores,
}

function money(value: number) {
  return `${Math.round(value).toLocaleString('ko-KR')}원`
}

function isZeroCostValue(value: string) {
  return value.trim() !== '' && Number(value) === 0
}

function apiErrorMessage(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== 'object') return fallback
  const detail = (payload as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object' && typeof (detail as { message?: unknown }).message === 'string') {
    return String((detail as { message: string }).message)
  }
  return fallback
}

export function RecommercePage({ apiBase, authHeaders, viewRole }: Props) {
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [supplierForm, setSupplierForm] = useState(initialSupplierForm)
  const [skuForm, setSkuForm] = useState(initialSkuForm)
  const [research, setResearch] = useState<MarketResearch | null>(null)
  const [researchLoading, setResearchLoading] = useState(false)
  const [fieldMode, setFieldMode] = useState(false)
  const [fieldCandidateId, setFieldCandidateId] = useState<string | null>(null)
  const [fieldInputs, setFieldInputs] = useState({ price: '', shipping: '', returnShipping: '', targetPrice: '', bundleQuantity: '1' })
  const [fieldChecks, setFieldChecks] = useState<string[]>([])
  const [copied, setCopied] = useState(false)
  const canWrite = viewRole === 'ceo'

  const loadResearch = useCallback(async () => {
    const response = await fetch(`${apiBase}/api/recommerce/market-research`, { headers: authHeaders() })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(apiErrorMessage(payload, `Market research API ${response.status}`))
    setResearch(payload as MarketResearch)
  }, [apiBase, authHeaders])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`${apiBase}/api/recommerce/workspace`, { headers: authHeaders() })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(apiErrorMessage(payload, `Workspace API ${response.status}`))
      setWorkspace(payload as Workspace)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '사업 workspace를 불러오지 못했습니다.')
    } finally {
      setLoading(false)
    }
  }, [apiBase, authHeaders])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void load()
      void loadResearch().catch(() => setResearch(null))
    }, 0)
    return () => window.clearTimeout(timer)
  }, [load, loadResearch])

  const refreshResearch = async () => {
    if (!canWrite) return
    setResearchLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiBase}/api/recommerce/market-research/refresh`, { method: 'POST', headers: authHeaders() })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(apiErrorMessage(payload, `Refresh API ${response.status}`))
      setResearch(payload as MarketResearch)
      setNotice('시장 표본을 갱신했습니다. 매입 추천이 아니라 OJT shortlist입니다.')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '시장조사를 갱신하지 못했습니다.')
    } finally {
      setResearchLoading(false)
    }
  }

  const mutate = async (action: string, payload: Record<string, unknown>, successMessage: string) => {
    if (!workspace || !canWrite) return false
    setSaving(true)
    setNotice(null)
    setError(null)
    try {
      const response = await fetch(`${apiBase}/api/recommerce/workspace`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ expected_version: workspace.workspace_version, action, payload }),
      })
      const result = await response.json().catch(() => ({}))
      if (response.status === 409) {
        const fresh = result?.detail?.workspace as Workspace | undefined
        if (fresh) setWorkspace(fresh)
        throw new Error('다른 화면에서 먼저 수정했습니다. 최신 데이터로 갱신했으니 다시 확인하세요.')
      }
      if (!response.ok) throw new Error(apiErrorMessage(result, `Save API ${response.status}`))
      setWorkspace(result as Workspace)
      setNotice(successMessage)
      return true
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '변경사항을 저장하지 못했습니다.')
      return false
    } finally {
      setSaving(false)
    }
  }

  const checklistProgress = useMemo(() => {
    if (!workspace) return 0
    return Math.round((workspace.metrics.checklist_completed / Math.max(1, workspace.metrics.checklist_total)) * 100)
  }, [workspace])

  const supplierName = (id: string) => workspace?.suppliers.find(item => item.id === id)?.name || '공급처 미연결'

  const fieldCandidate = research?.candidates.find(item => item.id === fieldCandidateId) || research?.candidates[0] || null
  const fieldUnitCost = (Number(fieldInputs.price) || 0) + ((Number(fieldInputs.shipping) || 0) / Math.max(1, Number(fieldInputs.bundleQuantity) || 1))
  const fieldContribution = (Number(fieldInputs.targetPrice) || 0) - fieldUnitCost - ((Number(fieldInputs.targetPrice) || 0) * 0.33) - 2000
  const fieldReady = ['page', 'price', 'shipping', 'returns', 'identity'].every(item => fieldChecks.includes(item))
    && Number(fieldInputs.price) > 0 && Number(fieldInputs.shipping) >= 0
    && Number(fieldInputs.price) <= Number(fieldCandidate?.max_allowable_supply_cost || 0)
  const inquiryText = `[LLM 선정 조사대상: ${fieldCandidate?.name || '상품 미선정'}]\n1. 현재 실제 재고 수량과 확인 일시\n2. 사업자 판매 단가 및 수량별 할인 구간\n3. 최소 주문수량과 합배송 가능 수량\n4. 제조자·수입자·정확한 원산지\n5. 세금계산서 발행 가능 여부\n6. 최근 3개월 불량·파손률\n7. 불량·오배송·단순변심별 반품비 부담 주체\n※ 아직 주문 의사가 확정된 것은 아니며 견적·증빙 확인 요청입니다.`

  const startFieldResearch = (candidateId?: string) => {
    const target = research?.candidates.find(item => item.id === candidateId) || fieldCandidate
    if (!target) return
    setFieldCandidateId(target.id)
    setFieldInputs({ price: '', shipping: '', returnShipping: '', targetPrice: String(target.conservative_sale_price || ''), bundleQuantity: '1' })
    setFieldChecks([])
    setFieldMode(true)
    window.setTimeout(() => document.getElementById('recommerce-field-lab')?.scrollIntoView({ behavior: 'smooth' }), 0)
  }

  const submitSupplier = async (event: FormEvent) => {
    event.preventDefault()
    const saved = await mutate('add_supplier', supplierForm, '공급처 후보를 저장했습니다.')
    if (saved) setSupplierForm(initialSupplierForm)
  }

  const submitSku = async (event: FormEvent) => {
    event.preventDefault()
    const saved = await mutate('add_sku', {
      name: skuForm.name,
      supplier_id: skuForm.supplier_id,
      category: skuForm.category,
      conservative_sale_price: skuForm.conservative_sale_price,
      evidence_status: skuForm.evidence_status,
      note: skuForm.note,
      zero_cost_confirmed_keys: skuForm.zero_cost_confirmed_keys,
      ...Object.fromEntries(Object.entries(skuForm.costs).map(([key, value]) => [key, Number(value)])),
      scores: skuForm.scores,
    }, 'SKU 후보를 저장했습니다. 이는 시장검증 완료가 아닙니다.')
    if (saved) setSkuForm(initialSkuForm)
  }

  if (loading && !workspace) return <section className="recommerce-page"><div className="recommerce-loading">사업 workspace를 불러오는 중…</div></section>
  if (!workspace) return <section className="recommerce-page"><div className="recommerce-alert danger" role="alert"><strong>화면을 열 수 없습니다.</strong><span>{error}</span><button onClick={() => void load()}>다시 시도</button></div></section>

  return (
    <main className="recommerce-page" data-page-marker="recommerce-opportunity-workspace">
      <header className="recommerce-hero">
        <div>
          <span className="recommerce-eyebrow">보조 discovery track · Phase 0~2</span>
          <h2>재고가치회복 Mall 검증실</h2>
          <p>싸게 사는 화면이 아닙니다. 증빙 가능한 공급과 보수적 비용을 먼저 검토하는 내부 작업실입니다.</p>
          <div className="recommerce-hero-actions">
            <button className="recommerce-primary" disabled={!fieldCandidate} onClick={() => startFieldResearch()}>LLM 선정 OJT 시작</button>
            <span>{fieldCandidate ? '실제 시장근거로 공급가를 검증합니다' : '보수조건 통과 상품 없음'}</span>
          </div>
        </div>
        <div className="recommerce-status-stack" aria-label="사업기회 상태">
          <span className="recommerce-chip neutral">{workspace.opportunity.status}</span>
          <span className="recommerce-chip neutral">내부 검증 workspace</span>
          <span className="recommerce-chip locked">매입·판매 잠금</span>
        </div>
      </header>

      <section className="recommerce-guardrail" aria-label="허용 및 금지 범위">
        <div><strong>현재 허용</strong><span>{workspace.guardrails.allowed.join(' · ')}</span></div>
        <div><strong>현재 금지</strong><span>{workspace.guardrails.blocked.join(' · ')}</span></div>
      </section>

      {!canWrite && <div className="recommerce-alert info" role="status"><strong>VP 읽기 전용</strong><span>데이터 수정은 대표 계정에서만 가능합니다.</span></div>}
      {error && <div className="recommerce-alert danger" role="alert"><strong>저장 확인 필요</strong><span>{error}</span></div>}
      {notice && <div className="recommerce-alert success" role="status"><strong>저장됨</strong><span>{notice}</span></div>}
      {workspace.stop_reasons.map(reason => <div key={reason} className="recommerce-alert danger" role="alert"><strong>STOP</strong><span>{reason}</span></div>)}

      <section className="recommerce-kpis" aria-label="검증 준비 지표">
        <article><span>현재 범위</span><strong>Phase 0~2</strong><small>3~4 실행 잠금</small></article>
        <article><span>안전 checklist</span><strong>{checklistProgress}%</strong><small>{workspace.metrics.checklist_completed}/{workspace.metrics.checklist_total} 완료</small></article>
        <article><span>공급처 후보</span><strong>{workspace.metrics.supplier_count}</strong><small>증빙 확인 {workspace.metrics.verified_suppliers}</small></article>
        <article><span>SKU 후보</span><strong>{workspace.metrics.sku_count}</strong><small>비용조건 충족 {workspace.metrics.qualified_skus}</small></article>
        <article className={workspace.metrics.weekly_hours > 6 ? 'danger' : ''}><span>주간 투입시간</span><strong>{workspace.metrics.weekly_hours}h</strong><small>상한 6시간</small></article>
      </section>

      <section className="recommerce-next-action">
        <span>다음 행동 하나</span><strong>{workspace.next_action}</strong>
      </section>

      <section className="recommerce-section">
        <div className="recommerce-section-head"><div><span>진행 구조</span><h3>30일 검증 Phase</h3></div><small>Phase 변경 기능 없음</small></div>
        <div className="recommerce-phase-rail">
          {workspace.phases.map(phase => (
            <article key={phase.id} className={`recommerce-phase ${phase.state}`}>
              <span>Phase {phase.id}</span><strong>{phase.label}</strong><small>{phase.state === 'locked' ? '후속 승인 전 잠금' : '현재 workspace'}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="recommerce-grid two-column">
        <article className="recommerce-panel">
          <div className="recommerce-section-head"><div><span>Phase 0</span><h3>안전 경계 checklist</h3></div><small>{workspace.metrics.checklist_completed}/{workspace.metrics.checklist_total}</small></div>
          <div className="recommerce-checklist">
            {workspace.checklist.map(item => (
              <label key={item.key} className={item.completed ? 'completed' : ''}>
                <input type="checkbox" checked={item.completed} disabled={!canWrite || saving} onChange={event => void mutate('toggle_checklist', { key: item.key, completed: event.target.checked }, 'Checklist를 갱신했습니다.')} />
                <span>{item.label}</span>
              </label>
            ))}
          </div>
        </article>

        <article className="recommerce-panel">
          <div className="recommerce-section-head"><div><span>본업 보호</span><h3>주간 시간 cap</h3></div><small>6시간 초과 시 STOP</small></div>
          <label className="recommerce-field" htmlFor="weekly-hours"><span>두 운영자 합계 주간 투입시간</span><div className="recommerce-input-suffix"><input key={workspace.workspace_version} id="weekly-hours" type="number" min="0" max="168" step="0.5" defaultValue={workspace.metrics.weekly_hours} disabled={!canWrite || saving} onBlur={event => void mutate('set_weekly_hours', { hours: Number(event.target.value) }, '주간 투입시간을 갱신했습니다.')} /><span>시간</span></div></label>
          <div className="recommerce-rule-card"><strong>이 화면이 하지 않는 일</strong><p>주문, 매입, 예약금, paid demand, 매출을 기록하지 않습니다. 숫자가 좋아 보여도 사업 검증 완료가 아닙니다.</p></div>
        </article>
      </section>

      <section className="recommerce-section">
        <div className="recommerce-section-head"><div><span>Phase 1</span><h3>공급처 후보</h3></div><small>개인 연락처·계좌정보 저장 금지</small></div>
        {canWrite && <form className="recommerce-form supplier-form" onSubmit={event => void submitSupplier(event)}>
          <label className="recommerce-field"><span>공급처 표시명</span><input required maxLength={80} value={supplierForm.name} onChange={event => setSupplierForm(form => ({ ...form, name: event.target.value }))} /></label>
          <label className="recommerce-field"><span>접촉 상태</span><select value={supplierForm.contact_status} onChange={event => setSupplierForm(form => ({ ...form, contact_status: event.target.value }))}><option value="not_contacted">미접촉</option><option value="contacted">접촉</option><option value="interviewed">인터뷰 완료</option></select></label>
          <label className="recommerce-field"><span>증빙 상태</span><select value={supplierForm.evidence_status} onChange={event => setSupplierForm(form => ({ ...form, evidence_status: event.target.value }))}><option value="unverified">미확인</option><option value="requested">요청함</option><option value="verified">확인함</option></select></label>
          <label className="recommerce-field"><span>확인 당시 수량</span><input type="number" min="0" value={supplierForm.available_quantity} onChange={event => setSupplierForm(form => ({ ...form, available_quantity: Number(event.target.value) }))} /></label>
          <label className="recommerce-field"><span>견적 유효일</span><input type="date" value={supplierForm.quote_valid_until} onChange={event => setSupplierForm(form => ({ ...form, quote_valid_until: event.target.value }))} /></label>
          <label className="recommerce-field wide"><span>메모</span><input maxLength={240} value={supplierForm.note} onChange={event => setSupplierForm(form => ({ ...form, note: event.target.value }))} /></label>
          <button className="recommerce-primary" disabled={saving}>공급처 후보 저장</button>
        </form>}
        <div className="recommerce-card-list">
          {workspace.suppliers.map(item => <article key={item.id} className="recommerce-record-card"><div><strong>{item.name}</strong><span>{item.evidence_status === 'verified' ? '증빙 확인' : '증빙 미완료'} · 수량 {item.available_quantity}</span></div><div><span>견적 유효일 {item.quote_valid_until || '미입력'}</span>{canWrite && <button className="recommerce-delete" disabled={saving} onClick={() => void mutate('delete_supplier', { id: item.id }, '공급처 후보를 삭제했습니다.')}>삭제</button>}</div></article>)}
          {workspace.suppliers.length === 0 && <div className="recommerce-empty">등록된 공급처 후보가 없습니다.</div>}
        </div>
      </section>

      <section className="recommerce-section recommerce-ojt-launcher">
        <div className="recommerce-section-head"><div><span>초보자 OJT · 모의훈련</span><h3>상품을 보고, 공급을 이해하고, 매입하지 않는 판단까지</h3></div>{canWrite && <button className="recommerce-secondary" disabled={researchLoading} onClick={() => void refreshResearch()}>{researchLoading ? '조사 중…' : '시장 표본 갱신'}</button>}</div>
        <div className="recommerce-source-warning"><strong>사람이 상품을 고르지 않습니다.</strong><p>로컬 LLM이 실제 가격표본을 심사하고 코드 하드게이트가 재검증합니다. 통과 상품이 없으면 OJT도 시작되지 않습니다.</p></div>
        <div className="recommerce-training-grid">
          {research?.candidates.map(candidate => <article key={candidate.id} className={`recommerce-training-card ${candidate.rank === 1 ? 'recommended' : ''}`}><div className="recommerce-sku-head"><div><span>LLM 보수심사 {candidate.rank}순위</span><h4>{candidate.name}</h4></div><span className="recommerce-chip neutral">매입 금지</span></div><dl><div><dt>고유사도 가격표본</dt><dd>{candidate.sample_size || 0}건</dd></div><div><dt>보수 판매가</dt><dd>{candidate.conservative_sale_price ? money(candidate.conservative_sale_price) : '미확인'}</dd></div><div><dt>허용 공급가 상한</dt><dd>{candidate.max_allowable_supply_cost ? money(candidate.max_allowable_supply_cost) : '미확인'}</dd></div><div><dt>LLM 점수</dt><dd>{candidate.llm_score || 0}/100</dd></div></dl><p>{candidate.why}</p><button className={candidate.rank === 1 ? 'recommerce-primary' : 'recommerce-secondary'} onClick={() => startFieldResearch(candidate.id)}>근거 확인하며 조사</button></article>)}
          {research && research.candidates.length === 0 && <div className="recommerce-empty"><strong>선정 보류</strong><p>현재 표본에서 보수조건을 모두 통과한 상품이 없습니다. 상품을 억지로 추천하지 않습니다.</p><small>{research.llm?.provider || 'LLM'} · {research.llm?.model || '모델 미확인'} · {research.status}</small></div>}
          {!research && <div className="recommerce-empty">시장조사 결과를 불러오지 못했습니다.</div>}
        </div>
        <p className="recommerce-method-note">{research?.method_note || '검색 결과 수와 가격 표본은 판매량 증명이 아닙니다.'}</p>
        {research && research.rejected.length > 0 && <details className="recommerce-rejected"><summary>자동 탈락 후보 {research.rejected.length}개 보기</summary>{research.rejected.map(item => <p key={item.query}><strong>{item.query}</strong> — {item.reason}</p>)}</details>}
      </section>

      {fieldMode && fieldCandidate && <section id="recommerce-field-lab" className="recommerce-field-lab" aria-labelledby="field-lab-title">
        <header className="recommerce-field-head"><div><span className="recommerce-eyebrow">LLM SELECTED · 구매 없는 실전 조사</span><h3 id="field-lab-title">{fieldCandidate.name}</h3><p>LLM이 선정한 근거를 확인하고, 허용 공급가 이하의 실제 공급처 견적이 존재하는지 검증합니다.</p></div><span className="recommerce-chip locked">상업 준비도 BLOCK</span></header>
        <div className="recommerce-field-status"><div><span>현재 목표</span><strong>구매가 아니라 “추가 확인이 필요한 이유”를 증거로 설명</strong></div><button className="recommerce-text-button dark" onClick={() => setFieldMode(false)}>실전 조사 닫기</button></div>
        <div className="recommerce-field-columns">
          <article className="recommerce-field-task"><span className="recommerce-task-number">01</span><h4>LLM 시장근거 확인</h4><p><strong>{fieldCandidate.name}</strong><br />가격표본 {fieldCandidate.sample_size || 0}건 · 판매처 {fieldCandidate.sample_mall_count || 0}곳</p><a className="recommerce-primary recommerce-external-link" href={fieldCandidate.market_link} target="_blank" rel="noreferrer">Naver 상품 원문 열기 ↗</a><div className="recommerce-observed-facts"><div><span>시장 최저표본</span><strong>{money(fieldCandidate.market_low_price || 0)}</strong></div><div><span>하위 25% 가격</span><strong>{money(fieldCandidate.price_p25 || 0)}</strong></div><div><span>가격 중간값</span><strong>{money(fieldCandidate.median_price || 0)}</strong></div><div><span>허용 공급가 상한</span><strong>{money(fieldCandidate.max_allowable_supply_cost || 0)}</strong></div></div><div className="recommerce-source-note">Naver API 가격에는 배송비가 없습니다. 따라서 이 선정은 공급처 조사대상일 뿐 판매·매입 추천이 아닙니다.</div></article>
          <article className="recommerce-field-task"><span className="recommerce-task-number">02</span><h4>실제 공급견적 입력</h4><div className="recommerce-field-input-grid"><label><span>공급처 견적 단가</span><div><input type="number" value={fieldInputs.price} onChange={event => setFieldInputs(value => ({ ...value, price: event.target.value }))} /><em>원</em></div></label><label><span>소비자 배송비</span><div><input type="number" value={fieldInputs.shipping} onChange={event => setFieldInputs(value => ({ ...value, shipping: event.target.value }))} /><em>원</em></div></label><label><span>반품 편도비</span><div><input type="number" value={fieldInputs.returnShipping} onChange={event => setFieldInputs(value => ({ ...value, returnShipping: event.target.value }))} /><em>원</em></div></label><label><span>보수적 판매가</span><div><input type="number" value={fieldInputs.targetPrice} readOnly /><em>원</em></div></label><label><span>배송 1건당 묶음 수량</span><div><input type="number" min="1" value={fieldInputs.bundleQuantity} onChange={event => setFieldInputs(value => ({ ...value, bundleQuantity: event.target.value }))} /><em>개</em></div></label></div><div className="recommerce-live-math"><div><span>배송 배분 포함 원가</span><strong>{money(fieldUnitCost)}</strong></div><div className={fieldContribution > 0 ? 'positive' : 'negative'}><span>보수비용 차감 후 잔액</span><strong>{money(fieldContribution)}</strong></div><small>수수료 15% + 반품 8% + 광고 10% + 노동·포장 2,000원 가정. 배송비는 한 번만 계산.</small></div></article>
          <article className="recommerce-field-task"><span className="recommerce-task-number">03</span><h4>증빙 빈칸 표시</h4><p>원문에서 직접 확인했으면 체크. “상세참조”는 확인으로 보지 않습니다.</p><div className="recommerce-field-checks">{[['page','상품명·상품코드'],['price','공급처 견적 단가'],['shipping','배송·합배송 조건'],['returns','반품비와 책임 조건'],['identity','제조자·수입자·원산지']].map(([value,label]) => <label key={value} className={fieldChecks.includes(value) ? 'checked' : ''}><input type="checkbox" checked={fieldChecks.includes(value)} onChange={() => setFieldChecks(items => items.includes(value) ? items.filter(item => item !== value) : [...items, value])} /><span>{label}</span></label>)}</div><div className={`recommerce-field-verdict ${fieldReady ? 'review' : 'hold'}`}><span>현재 판정</span><strong>{fieldReady ? '계산 검토 가능 · 아직 구매 금지' : 'HOLD · 증빙 미완료'}</strong><p>{fieldReady ? '다음은 공급처 답변으로 단가·재고·불량률을 갱신하는 단계입니다.' : '체크되지 않은 항목을 공급처에 질문해야 합니다.'}</p></div></article>
          <article className="recommerce-field-task"><span className="recommerce-task-number">04</span><h4>실제 문의 초안 만들기</h4><p>복사만 합니다. 자동 발송하지 않습니다. 오너클랜 정책상 플랫폼 1:1 문의를 사용하고 직거래를 제안하지 마세요.</p><pre className="recommerce-inquiry">{inquiryText}</pre><button className="recommerce-secondary" onClick={() => { void navigator.clipboard.writeText(inquiryText).then(() => { setCopied(true); window.setTimeout(() => setCopied(false), 1800) }) }}>{copied ? '복사됨' : '문의문 복사'}</button></article>
        </div>
        <footer className="recommerce-field-outcome"><div><span>이 실전에서 얻는 경험</span><strong>실제 페이지 판독 → 비용 입력 → 결손 증빙 식별 → 공급처 질문 작성</strong></div><div><span>아직 하지 않는 일</span><strong>회원가입 · 문의 전송 · 샘플 주문 · 판매 등록</strong></div></footer>
      </section>}

      <section className="recommerce-section">
        <div className="recommerce-section-head"><div><span>Phase 1~2</span><h3>SKU 비용 검토</h3></div><small>허용 category만 등록 가능</small></div>
        {canWrite && <form className="recommerce-form sku-form" onSubmit={event => void submitSku(event)}>
          <label className="recommerce-field"><span>상품 후보명</span><input required maxLength={100} value={skuForm.name} onChange={event => setSkuForm(form => ({ ...form, name: event.target.value }))} /></label>
          <label className="recommerce-field"><span>공급처</span><select value={skuForm.supplier_id} onChange={event => setSkuForm(form => ({ ...form, supplier_id: event.target.value }))}><option value="">미연결</option>{workspace.suppliers.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
          <label className="recommerce-field"><span>허용 category</span><select value={skuForm.category} onChange={event => setSkuForm(form => ({ ...form, category: event.target.value }))}>{workspace.allowed_categories.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label className="recommerce-field"><span>보수적 판매가</span><input type="number" required min="1" value={skuForm.conservative_sale_price} onChange={event => setSkuForm(form => ({ ...form, conservative_sale_price: event.target.value }))} /></label>
          <div className="recommerce-subhead wide"><strong>모든 비용 입력</strong><span>빈칸을 0원으로 가정하지 않습니다.</span></div>
          {Object.entries(COST_LABELS).map(([key, label]) => <div key={key} className="recommerce-cost-field"><label className="recommerce-field"><span>{label}</span><input type="number" required min={key === 'unit_purchase_cost' ? 1 : 0} value={skuForm.costs[key]} onChange={event => setSkuForm(form => ({ ...form, costs: { ...form.costs, [key]: event.target.value }, zero_cost_confirmed_keys: isZeroCostValue(event.target.value) ? form.zero_cost_confirmed_keys : form.zero_cost_confirmed_keys.filter(item => item !== key) }))} /></label>{key !== 'unit_purchase_cost' && isZeroCostValue(skuForm.costs[key]) && <label className="recommerce-zero-confirm"><input type="checkbox" required checked={skuForm.zero_cost_confirmed_keys.includes(key)} onChange={event => setSkuForm(form => ({ ...form, zero_cost_confirmed_keys: event.target.checked ? [...new Set([...form.zero_cost_confirmed_keys, key])] : form.zero_cost_confirmed_keys.filter(item => item !== key) }))} /><span>{label} 없음 확인</span></label>}</div>)}
          <div className="recommerce-subhead wide"><strong>8축 score</strong><span>각 0~5점. 증빙·안전 4점 미만이면 비용조건 충족 불가.</span></div>
          {Object.entries(SCORE_LABELS).map(([key, label]) => <label key={key} className="recommerce-field"><span>{label}</span><input type="number" required min="0" max="5" value={skuForm.scores[key]} onChange={event => setSkuForm(form => ({ ...form, scores: { ...form.scores, [key]: Number(event.target.value) } }))} /></label>)}
          <label className="recommerce-field"><span>증빙 관찰 상태</span><select value={skuForm.evidence_status} onChange={event => setSkuForm(form => ({ ...form, evidence_status: event.target.value }))}><option value="unverified">미확인</option><option value="requested">요청함</option><option value="verified">확인함</option></select></label>
          <label className="recommerce-field wide"><span>비민감 메모</span><input maxLength={240} value={skuForm.note} onChange={event => setSkuForm(form => ({ ...form, note: event.target.value }))} /></label>
          <button className="recommerce-primary" disabled={saving}>SKU 비용 후보 저장</button>
        </form>}

        <div className="recommerce-sku-grid">
          {workspace.sku_candidates.map(item => <article key={item.id} className={`recommerce-sku-card ${item.cost_review_condition_met ? 'condition-met' : ''}`}><div className="recommerce-sku-head"><div><span>{workspace.allowed_categories.find(category => category.value === item.category)?.label}</span><h4>{item.name}</h4><small>{supplierName(item.supplier_id)}</small></div><span className={`recommerce-chip ${item.cost_review_condition_met ? 'clear' : 'neutral'}`}>{item.cost_review_condition_met ? '비용검토 조건 충족' : '조건 미충족'}</span></div><dl><div><dt>총 변동비</dt><dd>{money(item.full_variable_cost)}</dd></div><div><dt>공헌이익</dt><dd>{money(item.contribution)}</dd></div><div><dt>공헌이익률</dt><dd>{item.contribution_rate}%</dd></div><div><dt>8축 score</dt><dd>{item.total_score}/40</dd></div></dl><p>이 결과는 입력값 산술검토입니다. 실제 수요·판매 가능성 검증이 아닙니다.</p>{canWrite && <button className="recommerce-delete" disabled={saving} onClick={() => void mutate('delete_sku', { id: item.id }, 'SKU 후보를 삭제했습니다.')}>후보 삭제</button>}</article>)}
          {workspace.sku_candidates.length === 0 && <div className="recommerce-empty">등록된 SKU 후보가 없습니다.</div>}
        </div>
      </section>

      <footer className="recommerce-footer"><strong>승인 경계</strong><p>이 화면의 어떤 상태도 `opportunity_approve`, `legal_review_approve`, `monetization_experiment_approve`, `capital_action_approve`를 대신하지 않습니다.</p><small>workspace v{workspace.workspace_version} · {workspace.updated_at ? new Date(workspace.updated_at).toLocaleString('ko-KR') : '아직 저장 없음'}</small></footer>
    </main>
  )
}
