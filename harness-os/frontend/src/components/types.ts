export type SnapshotRow = {
  snapshot_date: string | null
  platform?: string | null
  free_subscribers?: number
  paid_subscribers?: number
  opens: number
  clicks: number
  replies: number
  shares: number
  unsubscribe_count: number
  paid_revenue_krw?: number
}

export type SubscriberHistoryRow = {
  snapshot_date: string
  free_subscribers: number
  paid_subscribers: number
  paid_revenue_krw: number
}

export type PlatformView = {
  latest_snapshot: SnapshotRow
  subscriber_history: SubscriberHistoryRow[]
  engagement: {
    opens: number
    clicks: number
    replies: number
    shares: number
  }
}

export type TradingWatchlistItem = {
  item_id?: string
  query?: string
  name_hint?: string
  exchange_hint?: string
  region?: string
  priority?: number
  active?: boolean
  watch_reason?: string
  conid?: string
  symbol?: string
  exchange?: string
  currency?: string
  confidence?: number
  tradable?: string
  approved_at?: string
  quote?: {
    conid?: string
    symbol?: string
    last?: string | number
    bid?: string | number
    ask?: string | number
    close?: string | number
    change_pct?: string | number
    currency?: string
    fetched_at?: string
    freshness_status?: string
  } | null
}

export type TradingApiPayload = {
  preflight: {
    ok: boolean
    authenticated?: boolean | null
    base_url?: string
    tls_verify?: boolean
    error?: string | null
  }
  accounts: {
    count: number
    error?: string | null
    accounts: Array<{
      id?: string
      account_type?: string
      currency?: string
      description?: string
    }>
  }
  onboarding: {
    path: string
    updated_at?: string | null
    owner_note?: string | null
    completed_count: number
    total_count: number
    next_required?: string | null
    steps: Array<{
      id: string
      label: string
      completed: boolean
      source: string
      note?: string | null
    }>
  }
  whitelist: {
    path: string
    item_count: number
    generated_at?: string | null
  }
  watchlist_meta: {
    path: string
    item_count: number
    mode: string
  }
  registry: {
    path: string
    approved_count: number
    recent: Array<{
      item_id?: string
      symbol?: string
      exchange?: string
      confidence?: number
      ts?: string
    }>
  }
  pending: {
    path: string
    pending_count: number
    recent: Array<{
      item_id?: string
      query?: string
      reason?: string
      ts?: string
    }>
  }
  watchlist: TradingWatchlistItem[]
}

export type DashboardPayload = {
  generated_at: string
  selected_platform?: string
  available_platforms?: string[]
  kpis: {
    free_subscribers: { value: number; target: number; progress: number }
    paid_subscribers: { value: number; target: number; progress: number }
    llm_daily_cost_usd: { value: number; budget_limit_usd: number }
    pending_red_team_reviews: { value: number }
  }
  latest_snapshot: SnapshotRow
  action_required?: { open: number; closed: number; total: number }
  risk_overview?: Record<string, number>
  orchestration?: {
    runs_today: number
    runs_last_90: number
    avg_estimated_cost_usd_last_20: number
  }
  subscriber_signal?: {
    history?: SubscriberHistoryRow[]
  }
  platform_views?: Record<string, PlatformView>
  cost_history?: Array<{ day: string; cost_usd: number }>
  command_templates?: Array<{ label: string; command: string }>
  trading_api?: TradingApiPayload
}

export type JarvisResponse = {
  command: string
  output: string
  generated_at: string
}

export type IbkrCheckPayload = {
  generated_at: string
  whitelist_path?: string
  preflight: {
    ok: boolean
    auth?: { authenticated?: boolean | null }
    authenticated?: boolean | null
    error?: string | null
  }
  summary: {
    items_total: number
    resolved_high_confidence: number
    resolved_low_confidence: number
    unresolved: number
  }
  results: Array<{
    item: { id?: string; query?: string; exchange_hint?: string; name_hint?: string }
    candidate_count: number
    best?: {
      conid?: string
      symbol?: string
      exchange?: string
      confidence?: number
      score_gap?: number
    } | null
  }>
  error?: string
}
