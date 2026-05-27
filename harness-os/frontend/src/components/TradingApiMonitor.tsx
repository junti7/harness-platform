import { useState } from 'react'
import type { FormEvent } from 'react'
import type { TradingApiPayload, IbkrCheckPayload } from './types'
import { boolLabel, formatMaybeNumber, freshnessLabel } from './utils'
import { SectionError } from './KpiCard'

type Props = {
  tradingApi: TradingApiPayload
  apiBase: string
  authHeaders: () => Record<string, string>
}

export function TradingApiMonitor({ tradingApi, apiBase, authHeaders }: Props) {
  const [refreshing, setRefreshing] = useState(false)
  const [runningCheck, setRunningCheck] = useState(false)
  const [ibkrCheck, setIbkrCheck] = useState<IbkrCheckPayload | null>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [mutatingItem, setMutatingItem] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [localApi, setLocalApi] = useState<TradingApiPayload>(tradingApi)

  const [newWatch, setNewWatch] = useState({
    id: '', query: '', name: '', exchange: '', region: '', reason: ''
  })

  const staleCount = localApi.watchlist.filter(r => r.quote?.freshness_status === 'stale').length
  const agingCount = localApi.watchlist.filter(r => r.quote?.freshness_status === 'aging').length
  const inactiveCount = localApi.watchlist.filter(r => r.active === false).length
  const visible = localApi.watchlist.filter(r => showInactive || r.active !== false)

  const refresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/trading/monitor`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`Trading monitor ${res.status}`)
      setLocalApi(await res.json())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setRefreshing(false)
    }
  }

  const runCheck = async () => {
    setRunningCheck(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/trading/ibkr-check`, { headers: authHeaders() })
      if (!res.ok) throw new Error(`IBKR check ${res.status}`)
      setIbkrCheck(await res.json())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setRunningCheck(false)
    }
  }

  const toggleItem = async (itemId: string, action: 'activate' | 'deactivate') => {
    setMutatingItem(itemId)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/trading/watchlist/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({ item_id: itemId, action }),
      })
      if (!res.ok) throw new Error(`Toggle ${res.status}`)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setMutatingItem(null)
    }
  }

  const addItem = async (event: FormEvent) => {
    event.preventDefault()
    if (!newWatch.id.trim() || !newWatch.query.trim() || !newWatch.name.trim()) return
    setAdding(true)
    setError(null)
    try {
      const res = await fetch(`${apiBase}/api/trading/watchlist/add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          item_id: newWatch.id.trim(), query: newWatch.query.trim(), name_hint: newWatch.name.trim(),
          exchange_hint: newWatch.exchange.trim() || null, region: newWatch.region.trim() || null,
          watch_reason: newWatch.reason.trim() || null,
        }),
      })
      if (!res.ok) throw new Error(`Add ${res.status}`)
      setNewWatch({ id: '', query: '', name: '', exchange: '', region: '', reason: '' })
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setAdding(false)
    }
  }

  const gatewayOk = localApi.preflight.ok
  const authenticated = localApi.preflight.authenticated

  return (
    <section className="trading-section">
      <div className="section-head">
        <h2>증권계좌 연결 점검</h2>
        <p>실제 주문 전에 계좌 연결, 인증, 관심 종목 상태를 읽기 전용으로 확인합니다.</p>
        <p className="term-note">IBKR은 Interactive Brokers 증권계좌를 뜻합니다. API는 프로그램이 계좌 정보를 읽는 연결 통로입니다.</p>
      </div>

      {error && <SectionError section="증권계좌 연결" message={error} />}

      {(staleCount > 0 || agingCount > 0) && (
        <div className={`risk-banner risk-${staleCount > 0 ? 'danger' : 'warn'}`} role="alert">
          <span className="risk-icon">{staleCount > 0 ? '⚠' : '△'}</span>
          <div>
            <strong>호가 신선도 경고</strong>
            <span>
              {staleCount > 0
                ? `${staleCount}개 종목 가격 정보가 오래됐습니다. 증권계좌 연결 상태를 확인해야 합니다`
                : `${agingCount}개 종목 가격 정보가 늦어지고 있습니다. 판단 전에 새로고침을 권장합니다`}
            </span>
          </div>
        </div>
      )}

      <div className="toolbar">
        <button type="button" className="btn-secondary" onClick={refresh} disabled={refreshing}>
          {refreshing ? '새로고침 중…' : '계좌 연결 새로고침'}
        </button>
        <button type="button" className="btn-secondary" onClick={runCheck} disabled={runningCheck}>
          {runningCheck ? '검사 중…' : '해외 ETF 종목 확인'}
        </button>
      </div>

      <div className="trading-grid">
        <article className="panel">
          <h3>계좌 연결 사전 검증</h3>
          <div className="split-2">
            <div>
              <p className="data-label">게이트웨이</p>
              <p className={`data-value ${gatewayOk ? 'ok' : 'danger'}`}>{gatewayOk ? '연결됨' : '차단됨'}</p>
            </div>
            <div>
              <p className="data-label">인증 여부</p>
              <p className={`data-value ${authenticated === true ? 'ok' : 'warn'}`}>{authenticated === true ? '인증 완료' : '미인증'}</p>
            </div>
          </div>
          <ul className="data-list">
            <li>연결 주소: {localApi.preflight.base_url ?? '없음'}</li>
            <li>보안 연결 검증: {localApi.preflight.tls_verify ? '활성' : '비활성'}</li>
            <li>표시 가능한 계좌 수: {localApi.accounts.count}</li>
            {localApi.preflight.error && <li className="data-warn">오류: {localApi.preflight.error}</li>}
          </ul>
        </article>

        <article className="panel">
          <h3>ETF 등록소</h3>
          <div className="split-2">
            <div>
              <p className="data-label">화이트리스트 항목</p>
              <p className="data-value">{localApi.whitelist.item_count}</p>
            </div>
            <div>
              <p className="data-label">승인된 매핑 수</p>
              <p className="data-value">{localApi.registry.approved_count}</p>
            </div>
          </div>
          <ul className="data-list">
            <li>화이트리스트 경로: {localApi.whitelist.path}</li>
            <li>생성 시각: {localApi.whitelist.generated_at ?? '없음'}</li>
            <li>등록소 경로: {localApi.registry.path}</li>
            <li>관심종목 소스: {localApi.watchlist_meta.path}</li>
          </ul>
        </article>

        <article className="panel">
          <h3>검토 대기 중인 항목</h3>
          <div className="split-2">
            <div>
              <p className="data-label">대기 항목 수</p>
              <p className={`data-value ${localApi.pending.pending_count > 0 ? 'warn' : ''}`}>{localApi.pending.pending_count}</p>
            </div>
            <div>
              <p className="data-label">최근 내역</p>
              <p className="data-value">{localApi.pending.recent.length}</p>
            </div>
          </div>
          {localApi.pending.recent.length > 0 && (
            <ul className="data-list">
              {localApi.pending.recent.slice().reverse().slice(0, 3).map((r, i) => (
                <li key={`${r.item_id ?? r.query ?? 'p'}-${i}`}>{r.item_id ?? r.query ?? '미지정'} · {r.reason ?? '이유 없음'}</li>
              ))}
            </ul>
          )}
        </article>
      </div>

      <div className="trading-grid detail-grid">
        <article className="panel">
          <h3>계좌 연결 체크리스트</h3>
          <div className="split-2">
            <div>
              <p className="data-label">완료됨</p>
              <p className="data-value">{localApi.onboarding.completed_count}/{localApi.onboarding.total_count}</p>
            </div>
            <div>
              <p className="data-label">다음 필수 단계</p>
              <p className="data-value data-value-sm">
                {localApi.onboarding.next_required === 'Operational' ? '운영 가능' : (localApi.onboarding.next_required ?? '운영 가능')}
              </p>
            </div>
          </div>
          <ul className="checklist">
            {localApi.onboarding.steps.map(step => (
              <li key={step.id} className={step.completed ? 'done' : 'open'}>
                <span className={`check-dot ${step.completed ? 'done' : 'open'}`} />
                <span>{step.label}</span>
                <span className="source-tag">{step.source}</span>
              </li>
            ))}
          </ul>
        </article>

        <article className="panel">
          <h3>계좌 가시성</h3>
          {localApi.accounts.accounts.length === 0 ? (
            <p className="data-empty">{localApi.accounts.error ?? '표시 가능한 증권계좌가 없습니다'}</p>
          ) : (
            <ul className="data-list">
              {localApi.accounts.accounts.map((a, i) => (
                <li key={`${a.id ?? 'acct'}-${i}`}>{a.id ?? '알 수 없음'} · {a.account_type ?? '없음'} · {a.currency ?? 'USD'}</li>
              ))}
            </ul>
          )}
        </article>

        <article className="panel">
          <h3>최근 승인 목록</h3>
          {localApi.registry.recent.length === 0 ? (
            <p className="data-empty">승인된 금융상품 매핑이 없습니다</p>
          ) : (
            <ul className="data-list">
              {localApi.registry.recent.slice().reverse().map((r, i) => (
                <li key={`${r.item_id ?? 'a'}-${i}`}>{r.item_id ?? '알 수 없음'} · {r.symbol ?? '없음'} · {r.exchange ?? '없음'} · 신뢰도 {r.confidence ?? '없음'}</li>
              ))}
            </ul>
          )}
        </article>
      </div>

      <article className="panel watchlist-panel">
        <div className="watchlist-header">
          <h3>관심종목 실시간 호가</h3>
          <span className="data-label">소스: {localApi.watchlist_meta.mode} · {localApi.watchlist_meta.item_count}개 항목</span>
          <label className="toggle-label">
            <input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)} />
            <span>비활성 항목 표시 ({inactiveCount})</span>
          </label>
        </div>
        <form className="watchlist-add" onSubmit={addItem}>
          {(['id', 'query', 'name', 'exchange', 'region', 'reason'] as const).map(field => {
            const getPlaceholder = (f: string) => {
              switch (f) {
                case 'id': return 'ID (예: us-QQQ)'
                case 'query': return '검색 쿼리'
                case 'name': return '종목명'
                case 'exchange': return '거래소'
                case 'region': return '지역'
                case 'reason': return '감시 사유'
                default: return f
              }
            }
            return (
              <input
                key={field}
                value={newWatch[field]}
                onChange={e => setNewWatch(prev => ({ ...prev, [field]: e.target.value }))}
                placeholder={getPlaceholder(field)}
              />
            )
          })}
          <button type="submit" disabled={adding}>{adding ? '추가 중…' : '추가'}</button>
        </form>
        {visible.length === 0 ? (
          <p className="data-empty">승인된 관심종목 금융상품이 없습니다</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>항목</th><th>심볼</th><th>거래소</th><th>감시 사유</th>
                  <th>최근가</th><th>매수가</th><th>매도가</th><th>대비%</th>
                  <th>상태</th><th>신뢰도</th><th>활성 여부</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((row, i) => (
                  <tr key={`${row.item_id ?? row.conid ?? 'w'}-${i}`}>
                    <td>{row.name_hint ?? row.item_id ?? row.query ?? '없음'}</td>
                    <td>{row.quote?.symbol ?? row.symbol ?? '없음'}</td>
                    <td>{row.exchange ?? row.exchange_hint ?? '없음'}</td>
                    <td>{row.watch_reason ?? '없음'}</td>
                    <td className="num">{formatMaybeNumber(row.quote?.last)}</td>
                    <td className="num">{formatMaybeNumber(row.quote?.bid)}</td>
                    <td className="num">{formatMaybeNumber(row.quote?.ask)}</td>
                    <td className="num">{formatMaybeNumber(row.quote?.change_pct)}</td>
                    <td>
                      <span className={`freshness-chip ${row.quote?.freshness_status ?? 'unknown'}`}>
                        {freshnessLabel(row.quote?.freshness_status)}
                      </span>
                    </td>
                    <td>{row.confidence ?? '없음'}</td>
                    <td>
                      <button
                        type="button"
                        className={`watchlist-toggle ${row.active === false ? 'inactive' : 'active'}`}
                        onClick={() => void toggleItem(row.item_id ?? '', row.active === false ? 'activate' : 'deactivate')}
                        disabled={!row.item_id || mutatingItem === row.item_id}
                      >
                        {mutatingItem === row.item_id ? '…' : row.active === false ? '활성화' : '비활성화'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      {ibkrCheck && (
        <article className="panel watchlist-panel">
          <h3>해외 ETF 종목 확인 결과</h3>
          <div className="split-2">
            <div>
              <p className="data-label">높은 신뢰도</p>
              <p className="data-value ok">{ibkrCheck.summary.resolved_high_confidence}</p>
            </div>
            <div>
              <p className="data-label">낮음 / 미해결</p>
              <p className={`data-value ${ibkrCheck.summary.unresolved > 0 ? 'warn' : ''}`}>
                {ibkrCheck.summary.resolved_low_confidence + ibkrCheck.summary.unresolved}
              </p>
            </div>
          </div>
          <ul className="data-list">
            <li>총 항목 수: {ibkrCheck.summary.items_total}</li>
            <li>사전 검증 성공: {boolLabel(ibkrCheck.preflight.ok && (ibkrCheck.preflight.auth?.authenticated ?? ibkrCheck.preflight.authenticated) === true)}</li>
            {(ibkrCheck.error ?? ibkrCheck.preflight.error) && <li className="data-warn">오류: {ibkrCheck.error ?? ibkrCheck.preflight.error}</li>}
          </ul>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>항목</th><th>쿼리</th><th>후보 수</th><th>최적 매핑</th><th>거래소</th><th>신뢰도</th></tr></thead>
              <tbody>
                {ibkrCheck.results.map((r, i) => (
                  <tr key={`${r.item.id ?? r.item.query ?? 'ibkr'}-${i}`}>
                    <td>{r.item.id ?? r.item.name_hint ?? '없음'}</td>
                    <td>{r.item.query ?? '없음'}</td>
                    <td>{r.candidate_count}</td>
                    <td>{r.best?.symbol ?? r.best?.conid ?? '미해결'}</td>
                    <td>{r.best?.exchange ?? r.item.exchange_hint ?? '없음'}</td>
                    <td>{r.best?.confidence ?? '없음'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      )}
    </section>
  )
}
