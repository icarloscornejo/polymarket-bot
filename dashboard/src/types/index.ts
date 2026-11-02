export interface HealthStatus {
  status: string
  mode: 'PAPER' | 'LIVE'
  current_params_id: number
  timezone: string
  btc_feed_active: string
}

export interface Signal {
  id: number
  timestamp: string
  market_id: string
  side: 'YES' | 'NO'
  yes_price: number
  no_price: number
  btc_price: number
  btc_price_source: string
  dtt: number
  time_to_close_sec: number
  potential_gain: number
  action_taken: 'SKIPPED' | 'PAPER_TRADE' | 'LIVE_TRADE'
  skip_reason: string | null
  strategy_params_id: number
}

export interface Trade {
  id: number
  signal_id: number
  market_id: string
  side: 'YES' | 'NO'
  entry_price: number
  entry_btc_price: number
  entry_dtt: number
  entry_time_to_close: number
  position_size_usd: number
  status: 'OPEN' | 'RESOLVED'
  exit_price: number | null
  resolved_at: string | null
  pnl_usd: number | null
  pnl_pct: number | null
  mode: 'PAPER' | 'LIVE'
  opened_at: string
}

export interface Snapshot {
  id: number
  timestamp: string
  market_id: string
  time_to_close_sec: number
  btc_price: number
  btc_price_source: string
  threshold: number
  dtt: number
  yes_price: number
  no_price: number
  spread: number
  book_depth_yes: number
  book_depth_no: number
  potential_gain_yes: number
  potential_gain_no: number
  strategy_params_id: number
}

export interface StrategyParams {
  id: number
  valid_from: string
  valid_to: string | null
  updated_by: string
  entry_window_min_sec: number
  entry_window_max_sec: number
  min_dtt: number
  min_gain_usd: number
  position_size_usd: number
  snapshot_interval_ms: number
  logging_window_buffer_sec: number
}

export interface StrategyParamsUpdate {
  entry_window_min_sec?: number
  entry_window_max_sec?: number
  min_dtt?: number
  min_gain_usd?: number
  position_size_usd?: number
  snapshot_interval_ms?: number
  logging_window_buffer_sec?: number
}

export interface MonthlyPerformance {
  year: number
  month: number
  timezone: string
  pnl_usd_paper: number
  pnl_usd_live: number
  total_invested_usd_paper: number
  total_invested_usd_live: number
  total_trades: number
  winning_trades: number
  pnl_pct_paper: number
  pnl_pct_live: number
  win_rate: number
}

export interface DailySummary {
  date: string
  total_markets_archived: number
  total_snapshots_archived: number
  total_signals: number
  signals_entered: number
  signals_skipped: number
  paper_trades_count: number
  paper_winning_trades: number
  paper_pnl_usd: number
  paper_invested_usd: number
  paper_pnl_pct: number
  live_trades_count: number
  live_winning_trades: number
  live_pnl_usd: number
  live_invested_usd: number
  live_pnl_pct: number
  win_rate: number
  cleanup_ran_at: string
}

export interface RuntimeSettings {
  timezone: string
  updated_at: string
}

export interface MaintenanceStatus {
  last_cleanup_at: string | null
  oldest_raw_snapshot_timestamp: string | null
  total_raw_snapshots: number
  total_archived_markets: number
  total_daily_summaries: number
  next_cleanup_at: string
}
