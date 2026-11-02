import type {
  DailySummary,
  HealthStatus,
  MaintenanceStatus,
  MonthlyPerformance,
  RuntimeSettings,
  Signal,
  Snapshot,
  StrategyParams,
  StrategyParamsUpdate,
  Trade,
} from '../types'

const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PATCH ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  health: () => get<HealthStatus>('/health'),

  signals: (limit = 50, marketId?: string) => {
    const params = new URLSearchParams({ limit: String(limit) })
    if (marketId) params.set('market_id', marketId)
    return get<Signal[]>(`/signals?${params}`)
  },

  trades: (mode?: string, status?: string) => {
    const params = new URLSearchParams()
    if (mode) params.set('mode', mode)
    if (status) params.set('status', status)
    const qs = params.toString()
    return get<Trade[]>(`/trades${qs ? `?${qs}` : ''}`)
  },

  snapshots: (marketId: string, limit = 100) =>
    get<Snapshot[]>(`/snapshots?market_id=${encodeURIComponent(marketId)}&limit=${limit}`),

  activeMarkets: () => get<string[]>('/markets/active'),

  setMode: (mode: 'PAPER' | 'LIVE') =>
    post<{ mode: string }>('/mode', { mode }),

  strategy: () => get<StrategyParams>('/strategy'),
  strategyHistory: () => get<StrategyParams[]>('/strategy/history'),
  updateStrategy: (body: StrategyParamsUpdate) => patch<StrategyParams>('/strategy', body),

  monthlyPerformance: (year: number, month: number, tz?: string) => {
    const params = new URLSearchParams({ year: String(year), month: String(month) })
    if (tz) params.set('tz', tz)
    return get<MonthlyPerformance>(`/performance/monthly?${params}`)
  },

  dailyPerformance: (date: string) =>
    get<DailySummary>(`/performance/daily?date=${date}`),

  settings: () => get<RuntimeSettings>('/settings'),
  updateSettings: (timezone: string) => patch<RuntimeSettings>('/settings', { timezone }),

  maintenanceStatus: () => get<MaintenanceStatus>('/maintenance/status'),
}
