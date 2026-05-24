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
        <h2>Trading API Monitor</h2>
        <p>IBKR CP API preflight · ETF registry · Read-only watchlist</p>
      </div>

      {error && <SectionError section="Trading API" message={error} />}

      {(staleCount > 0 || agingCount > 0) && (
        <div className={`risk-banner risk-${staleCount > 0 ? 'danger' : 'warn'}`} role="alert">
          <span className="risk-icon">{staleCount > 0 ? '⚠' : '△'}</span>
          <div>
            <strong>Quote freshness warning</strong>
            <span>
              {staleCount > 0
                ? `${staleCount}개 종목 stale — IBKR gateway/session 점검 필요`
                : `${agingCount}개 종목 aging — 실시간 판단 전 refresh 권장`}
            </span>
          </div>
        </div>
      )}

      <div className="toolbar">
        <button type="button" className="btn-secondary" onClick={refresh} disabled={refreshing}>
          {refreshing ? 'Refreshing…' : 'Refresh Trading API'}
        </button>
        <button type="button" className="btn-secondary" onClick={runCheck} disabled={runningCheck}>
          {runningCheck ? 'Running…' : 'Run IBKR ETF Check'}
        </button>
      </div>

      <div className="trading-grid">
        <article className="panel">
          <h3>IBKR Preflight</h3>
          <div className="split-2">
            <div>
              <p className="data-label">Gateway</p>
              <p className={`data-value ${gatewayOk ? 'ok' : 'danger'}`}>{gatewayOk ? 'Connected' : 'Blocked'}</p>
            </div>
            <div>
              <p className="data-label">Authenticated</p>
              <p className={`data-value ${authenticated === true ? 'ok' : 'warn'}`}>{boolLabel(authenticated)}</p>
            </div>
          </div>
          <ul className="data-list">
            <li>Base URL: {localApi.preflight.base_url ?? 'n/a'}</li>
            <li>TLS Verify: {boolLabel(localApi.preflight.tls_verify)}</li>
            <li>Visible Accounts: {localApi.accounts.count}</li>
            {localApi.preflight.error && <li className="data-warn">Error: {localApi.preflight.error}</li>}
          </ul>
        </article>

        <article className="panel">
          <h3>ETF Registry</h3>
          <div className="split-2">
            <div>
              <p className="data-label">Whitelist Items</p>
              <p className="data-value">{localApi.whitelist.item_count}</p>
            </div>
            <div>
              <p className="data-label">Approved Mappings</p>
              <p className="data-value">{localApi.registry.approved_count}</p>
            </div>
          </div>
          <ul className="data-list">
            <li>Whitelist: {localApi.whitelist.path}</li>
            <li>Generated: {localApi.whitelist.generated_at ?? 'n/a'}</li>
            <li>Registry: {localApi.registry.path}</li>
            <li>Watchlist source: {localApi.watchlist_meta.path}</li>
          </ul>
        </article>

        <article className="panel">
          <h3>Pending Review</h3>
          <div className="split-2">
            <div>
              <p className="data-label">Pending Items</p>
              <p className={`data-value ${localApi.pending.pending_count > 0 ? 'warn' : ''}`}>{localApi.pending.pending_count}</p>
            </div>
            <div>
              <p className="data-label">Recent</p>
              <p className="data-value">{localApi.pending.recent.length}</p>
            </div>
          </div>
          {localApi.pending.recent.length > 0 && (
            <ul className="data-list">
              {localApi.pending.recent.slice().reverse().slice(0, 3).map((r, i) => (
                <li key={`${r.item_id ?? r.query ?? 'p'}-${i}`}>{r.item_id ?? r.query ?? 'unknown'} · {r.reason ?? 'n/a'}</li>
              ))}
            </ul>
          )}
        </article>
      </div>

      <div className="trading-grid detail-grid">
        <article className="panel">
          <h3>IBKR Setup Checklist</h3>
          <div className="split-2">
            <div>
              <p className="data-label">Completed</p>
              <p className="data-value">{localApi.onboarding.completed_count}/{localApi.onboarding.total_count}</p>
            </div>
            <div>
              <p className="data-label">Next Required</p>
              <p className="data-value data-value-sm">{localApi.onboarding.next_required ?? 'Operational'}</p>
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
          <h3>Account Visibility</h3>
          {localApi.accounts.accounts.length === 0 ? (
            <p className="data-empty">{localApi.accounts.error ?? '표시 가능한 IBKR account 없음'}</p>
          ) : (
            <ul className="data-list">
              {localApi.accounts.accounts.map((a, i) => (
                <li key={`${a.id ?? 'acct'}-${i}`}>{a.id ?? 'unknown'} · {a.account_type ?? 'n/a'} · {a.currency ?? 'n/a'}</li>
              ))}
            </ul>
          )}
        </article>

        <article className="panel">
          <h3>Recent Approved</h3>
          {localApi.registry.recent.length === 0 ? (
            <p className="data-empty">승인된 instrument mapping 없음</p>
          ) : (
            <ul className="data-list">
              {localApi.registry.recent.slice().reverse().map((r, i) => (
                <li key={`${r.item_id ?? 'a'}-${i}`}>{r.item_id ?? 'unknown'} · {r.symbol ?? 'n/a'} · {r.exchange ?? 'n/a'} · conf {r.confidence ?? 'n/a'}</li>
              ))}
            </ul>
          )}
        </article>
      </div>

      <article className="panel watchlist-panel">
        <div className="watchlist-header">
          <h3>Watchlist Quotes</h3>
          <span className="data-label">Source: {localApi.watchlist_meta.mode} · {localApi.watchlist_meta.item_count} items</span>
          <label className="toggle-label">
            <input type="checkbox" checked={showInactive} onChange={e => setShowInactive(e.target.checked)} />
            <span>Show inactive ({inactiveCount})</span>
          </label>
        </div>
        <form className="watchlist-add" onSubmit={addItem}>
          {(['id', 'query', 'name', 'exchange', 'region', 'reason'] as const).map(field => (
            <input
              key={field}
              value={newWatch[field]}
              onChange={e => setNewWatch(prev => ({ ...prev, [field]: e.target.value }))}
              placeholder={field === 'id' ? 'id (예: us-QQQ)' : field}
            />
          ))}
          <button type="submit" disabled={adding}>{adding ? 'Adding…' : 'Add'}</button>
        </form>
        {visible.length === 0 ? (
          <p className="data-empty">승인된 watchlist instrument 없음</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Item</th><th>Symbol</th><th>Exchange</th><th>Reason</th>
                  <th>Last</th><th>Bid</th><th>Ask</th><th>Chg%</th>
                  <th>Status</th><th>Conf</th><th>Active</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((row, i) => (
                  <tr key={`${row.item_id ?? row.conid ?? 'w'}-${i}`}>
                    <td>{row.name_hint ?? row.item_id ?? row.query ?? 'n/a'}</td>
                    <td>{row.quote?.symbol ?? row.symbol ?? 'n/a'}</td>
                    <td>{row.exchange ?? row.exchange_hint ?? 'n/a'}</td>
                    <td>{row.watch_reason ?? 'n/a'}</td>
                    <td className="num">{formatMaybeNumber(row.quote?.last)}</td>
                    <td className="num">{formatMaybeNumber(row.quote?.bid)}</td>
                    <td className="num">{formatMaybeNumber(row.quote?.ask)}</td>
                    <td className="num">{formatMaybeNumber(row.quote?.change_pct)}</td>
                    <td>
                      <span className={`freshness-chip ${row.quote?.freshness_status ?? 'unknown'}`}>
                        {freshnessLabel(row.quote?.freshness_status)}
                      </span>
                    </td>
                    <td>{row.confidence ?? 'n/a'}</td>
                    <td>
                      <button
                        type="button"
                        className={`watchlist-toggle ${row.active === false ? 'inactive' : 'active'}`}
                        onClick={() => void toggleItem(row.item_id ?? '', row.active === false ? 'activate' : 'deactivate')}
                        disabled={!row.item_id || mutatingItem === row.item_id}
                      >
                        {mutatingItem === row.item_id ? '…' : row.active === false ? 'Activate' : 'Deactivate'}
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
          <h3>IBKR ETF Check Summary</h3>
          <div className="split-2">
            <div>
              <p className="data-label">High Confidence</p>
              <p className="data-value ok">{ibkrCheck.summary.resolved_high_confidence}</p>
            </div>
            <div>
              <p className="data-label">Low / Unresolved</p>
              <p className={`data-value ${ibkrCheck.summary.unresolved > 0 ? 'warn' : ''}`}>
                {ibkrCheck.summary.resolved_low_confidence + ibkrCheck.summary.unresolved}
              </p>
            </div>
          </div>
          <ul className="data-list">
            <li>Items total: {ibkrCheck.summary.items_total}</li>
            <li>Preflight ok: {boolLabel(ibkrCheck.preflight.ok && (ibkrCheck.preflight.auth?.authenticated ?? ibkrCheck.preflight.authenticated) === true)}</li>
            {(ibkrCheck.error ?? ibkrCheck.preflight.error) && <li className="data-warn">Error: {ibkrCheck.error ?? ibkrCheck.preflight.error}</li>}
          </ul>
          <div className="table-wrap">
            <table className="data-table">
              <thead><tr><th>Item</th><th>Query</th><th>Candidates</th><th>Best</th><th>Exchange</th><th>Conf</th></tr></thead>
              <tbody>
                {ibkrCheck.results.map((r, i) => (
                  <tr key={`${r.item.id ?? r.item.query ?? 'ibkr'}-${i}`}>
                    <td>{r.item.id ?? r.item.name_hint ?? 'n/a'}</td>
                    <td>{r.item.query ?? 'n/a'}</td>
                    <td>{r.candidate_count}</td>
                    <td>{r.best?.symbol ?? r.best?.conid ?? 'unresolved'}</td>
                    <td>{r.best?.exchange ?? r.item.exchange_hint ?? 'n/a'}</td>
                    <td>{r.best?.confidence ?? 'n/a'}</td>
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
