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
    recent?: Array<{
      item_id?: string
      symbol?: string
      exchange?: string
      name_hint?: string
      region?: string
      ts?: string
    }>
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
      name_hint?: string
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
  action_required?: { 
    source?: string
    updated_at?: string | null
    open: number; 
    closed: number; 
    total: number; 
    summary?: {
      pending: number
      in_progress: number
      hold: number
      blocked: number
      waiting_external: number
      overdue: number
      closed: number
    }
    items?: Array<{
      id: string;
      title: string;
      owner: string;
      owner_display?: string;
      due_date: string;
      status: string;
      status_code?: string;
      status_label?: string;
      status_variant?: string;
      is_closed?: boolean;
      description?: string;
      completion_note?: string;
      last_checked_at?: string | null;
      last_updated_at?: string | null;
      evidence_required?: string;
      evidence_path?: string | null;
      evidence_available?: boolean;
      source_correlation_id?: string;
      category?: string;
      is_legacy_newsletter?: boolean;
    }>;
  }
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
  data_collection_monitor?: {
    domain?: string
    total: number
    pending_count: number
    pass_count: number
    fail_count: number
    sources?: Array<{
      id: string; label: string; type: string
      channel?: string
      mode?: string
      status?: string
      count: number; last_ingested_at: string; active: boolean
      expected_signal_type?: string
      reliability_score?: number
      base_url?: string
      preferred_worker?: string
      requires_login?: boolean
      notes?: string
      activation_policy?: string
    }>
    channel_coverage?: Array<{
      channel: string
      label: string
      total_sources: number
      active_sources: number
      standby_sources: number
      restricted_sources: number
      preferred_worker?: string
      notes?: string[]
    }>
    tier2_worker?: {
      pending_count: number
      oldest_pending_at?: string
      latest_pending_at?: string
      mbp_active?: boolean
      main?: {
        loaded?: boolean
        running?: boolean
        pid?: number | null
        last_exit_code?: string | number | null
        label?: string
        interval_seconds?: number
        log_tail?: string[]
      }
      fast_lane?: {
        loaded?: boolean
        running?: boolean
        pid?: number | null
        last_exit_code?: string | number | null
        label?: string
        interval_seconds?: number
        active_threshold?: number
        log_tail?: string[]
      }
    }
    current_topics?: Array<{
      topic: string
      kind: string
      confidence?: number | null
      evidence_count?: number | null
      reason?: string
      sample_title?: string
      active?: boolean
    }>
    suggested_topics?: Array<{
      topic: string
      confidence?: number | null
      evidence_count?: number | null
      reason?: string
      sample_title?: string
      active?: boolean
    }>
    generated_query_sources?: Array<{
      name: string
      url: string
      topic?: string
      generated?: boolean
    }>
    topic_registry_generated_at?: string | null
    expansion_policy?: {
      safe_auto_channels?: string[]
      restricted_channels?: string[]
      auto_topic_expansion?: boolean
      auto_channel_expansion?: boolean
    }
    workers?: {
      mini?: { role?: string; active?: boolean }
      mbp?: { role?: string; active?: boolean; host?: string }
    }
    configured_languages?: Array<{ code: string; label: string; flag: string }>
    recent_activity?: Array<{ source: string; status: string; ingested_at: string; title: string }>
  }
}


export type ApprovalItem = {
  id: string
  title: string
  submitter: string
  submitter_display: string
  approver_role: 'ceo' | 'vp'
  body: string
  status: 'pending' | 'approved' | 'rejected'
  status_label: string
  submitted_at?: string | null
  decided_at?: string | null
  decided_by_display?: string | null
  decision_note?: string | null
  approval_type?: string | null
  target_type?: string | null
  target_id?: number | null
  correlation_id?: string | null
  openclaw_route?: string | null
  openclaw_command?: string | null
  workflow: Array<{
    stage: string
    actor: string
    acted_at?: string | null
  }>
}

export type ApprovalInboxPayload = {
  generated_at: string
  updated_at?: string | null
  role: 'ceo' | 'vp'
  box: 'pending' | 'resolved'
  suspended?: boolean
  suspension_message?: string
  counts: {
    pending: number
    resolved: number
  }
  items: ApprovalItem[]
}

export type MeetingNoteSummary = {
  id: string
  title: string
  summary?: string | null
  recorded_at?: string | null
  notion_url?: string | null
  participants: string[]
}

export type MeetingNoteDetail = MeetingNoteSummary & {
  source?: string
  rounds?: number | null
  turns?: number | null
  llm_calls?: number | null
  estimated_cost_usd?: number | null
  order?: string | null
  decision?: string | null
}

export type MeetingNotesPayload = {
  generated_at: string
  updated_at?: string | null
  source?: string
  total: number
  items: MeetingNoteSummary[]
}

export type ConferenceRoomSummary = {
  id: string
  ts: string
  posted_at?: string | null
  author_display: string
  author_role?: string | null
  title: string
  preview?: string | null
  reply_count: number
  participant_count: number
  participants: string[]
  correlation_id?: string | null
  title_pending?: boolean
  agenda_pending?: boolean
  sync_origin?: 'slack' | 'fallback' | string
  linked_note?: {
    id: string
    title: string
    notion_url?: string | null
  } | null
}

export type ConferenceRoomMessage = {
  id: string
  ts: string
  posted_at?: string | null
  author_display: string
  author_role?: string | null
  text_markdown: string
  is_reply: boolean
}

export type ConferenceRoomDetail = ConferenceRoomSummary & {
  messages: ConferenceRoomMessage[]
  participant_statuses?: Array<{
    name: string
    status: 'invited' | 'joined' | string
  }>
  linked_run?: {
    correlation_id: string
    participants: string[]
    rounds?: number | null
    turns?: number | null
    llm_calls?: number | null
    estimated_cost_usd?: number | null
    order?: string | null
    decision?: string | null
  } | null
}

export type ConferenceRoomPayload = {
  generated_at: string
  updated_at?: string | null
  source?: string
  sync_mode?: 'local' | 'live' | 'fallback' | string
  sync_error?: string | null
  channel: {
    id?: string | null
    name?: string | null
    live_sync: boolean
  }
  stats: {
    threads: number
    participants: number
    messages: number
  }
  directory?: Array<{
    id: string
    label: string
  }>
  items: ConferenceRoomSummary[]
}

export type JarvisResponse = {
  command: string
  output: string
  generated_at: string
  relay_notes?: string[]
}

export type GmailSearchItem = {
  id: string
  subject: string
  from: string
  date?: string | null
  labels?: string[]
  messageCount?: number
}

export type GmailSearchPayload = {
  runtime: {
    enabled: boolean
    target?: string
    account?: string
    mode?: string
  }
  query: string
  limit: number
  count: number
  items: GmailSearchItem[]
}

export type GmailMessageDetail = {
  id: string
  subject: string
  from: string
  to: string
  date: string
  body: string
  snippet: string
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

// ── Alpaca Paper Trading ──────────────────────────────────────────────────────

export type AlpacaAccount = {
  ok: boolean
  error?: string
  account_id?: string
  status?: string
  portfolio_value?: number
  equity?: number
  cash?: number
  buying_power?: number
  total_pnl?: number
  total_pnl_pct?: number
  day_trade_count?: number
}

export type AlpacaPosition = {
  error?: string
  symbol?: string
  qty?: number
  side?: string
  entry_price?: number
  current_price?: number
  market_value?: number
  unrealized_pnl?: number
  unrealized_pnl_pct?: number
  atr?: number
  stop_loss?: number | null
  near_stop?: boolean
}

export type TurtleSignal = {
  symbol: string
  signal: string
  direction?: string | null
  system?: string | null
  current_price?: number
  atr?: number
  s1_high?: number
  s1_low?: number
  s2_high?: number
  s2_low?: number
  stop_long?: number | null
  stop_short?: number | null
  as_of?: string
  bar_count?: number
  error?: string
}

export type AlpacaOrder = {
  error?: string
  id?: string
  symbol?: string
  side?: string
  type?: string
  qty?: string
  filled_qty?: string
  fill_price?: string | null
  status?: string
  submitted_at?: string
}

export type AlpacaAR018Kpi = {
  return_pct: number
  max_position_loss_pct: number
  max_loss_pass: boolean
  deposit_cap_usd: number
  week_target: number
}

export type AlpacaChartPoint = {
  date: string
  value: number
  pnl_pct: number
}

export type AlpacaPaperDashboard = {
  ok?: boolean
  error?: string
  account: AlpacaAccount
  positions: AlpacaPosition[]
  signals: TurtleSignal[]
  active_signals: TurtleSignal[]
  orders: AlpacaOrder[]
  history: { ok: boolean; chart: AlpacaChartPoint[]; base?: number; error?: string }
  ar018_kpi: AlpacaAR018Kpi
  universe: string[]
  generated_at: string
}

export type DropAlert = {
  id: string
  symbol: string
  trigger: 'rapid' | 'day'
  drop_pct: number
  current_price: number
  prev_price: number
  news_titles: string[]
  briefing: string
  detected_at: string
  acknowledged: boolean
}

// ─────────────────────────────────────────────────────────────────────────────

export type CostSubscription = {
  name: string
  provider: string
  status: string
  key_configured: boolean
  cost_spent_usd: number
  models: string[]
}

export type CostsSummaryPayload = {
  initial_budget_usd: number
  total_spent_usd: number
  remaining_budget_usd: number
  burn_rate_percent: number
  monthly_costs: Array<{ month: string; cost_usd: number }>
  daily_costs: Array<{ day: string; cost_usd: number }>
  breakdown_by_provider: Array<{ provider: string; cost_usd: number; percentage: number }>
  breakdown_by_model: Array<{ model: string; provider: string; cost_usd: number; percentage: number }>
  llm_subscriptions: CostSubscription[]
}
