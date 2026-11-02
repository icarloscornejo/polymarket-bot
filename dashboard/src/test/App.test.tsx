import { render, screen, waitFor, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import App from '../App'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    health: vi.fn(),
    signals: vi.fn(),
    trades: vi.fn(),
    monthlyPerformance: vi.fn(),
    strategy: vi.fn(),
    settings: vi.fn(),
    maintenanceStatus: vi.fn(),
    setMode: vi.fn(),
    updateStrategy: vi.fn(),
    updateSettings: vi.fn(),
  },
}))

const mockApi = api as Record<string, ReturnType<typeof vi.fn>>

const health = { status: 'ok', mode: 'PAPER' as const, current_params_id: 1, timezone: 'UTC', btc_feed_active: 'binance' }
const perf = { year: 2026, month: 4, timezone: 'UTC', pnl_usd_paper: 5, pnl_usd_live: 0, total_invested_usd_paper: 100, total_invested_usd_live: 0, total_trades: 2, winning_trades: 1, pnl_pct_paper: 5, pnl_pct_live: 0, win_rate: 0.5 }
const strategy = { id: 1, valid_from: '', valid_to: null, updated_by: 'CONFIG', entry_window_min_sec: 5, entry_window_max_sec: 25, min_dtt: 10, min_gain_usd: 0.75, position_size_usd: 10, snapshot_interval_ms: 1000, logging_window_buffer_sec: 10 }
const settings = { timezone: 'UTC', updated_at: '' }
const maintenance = { last_cleanup_at: null, oldest_raw_snapshot_timestamp: null, total_raw_snapshots: 0, total_archived_markets: 0, total_daily_summaries: 0, next_cleanup_at: '2026-04-02T03:00:00Z' }

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  mockApi.health.mockResolvedValue(health)
  mockApi.signals.mockResolvedValue([])
  mockApi.trades.mockResolvedValue([])
  mockApi.monthlyPerformance.mockResolvedValue(perf)
  mockApi.strategy.mockResolvedValue(strategy)
  mockApi.settings.mockResolvedValue(settings)
  mockApi.maintenanceStatus.mockResolvedValue(maintenance)
})

afterEach(() => { vi.useRealTimers(); vi.clearAllMocks() })

describe('App', () => {
  it('renders health bar after loading', async () => {
    render(<App />)
    // Both HealthBar and ModeToggle show PAPER badge; verify at least one renders
    await waitFor(() => expect(screen.getAllByText('PAPER').length).toBeGreaterThan(0))
  })

  it('tab navigation switches to Trades tab', async () => {
    render(<App />)
    await waitFor(() => screen.getAllByText('PAPER'))
    fireEvent.click(screen.getByRole('button', { name: 'Trades' }))
    await waitFor(() => expect(screen.getByText('All Trades (0)')).toBeInTheDocument())
  })

  it('tab navigation switches to Strategy tab', async () => {
    render(<App />)
    await waitFor(() => screen.getAllByText('PAPER'))
    fireEvent.click(screen.getByRole('button', { name: 'Strategy' }))
    await waitFor(() => expect(screen.getByText(/Strategy Params/)).toBeInTheDocument())
  })

  it('tab navigation switches to DB tab', async () => {
    render(<App />)
    await waitFor(() => screen.getAllByText('PAPER'))
    fireEvent.click(screen.getByRole('button', { name: 'DB' }))
    await waitFor(() => expect(screen.getByText('DB Status')).toBeInTheDocument())
  })

  it('mode toggle calls setMode and refreshes health', async () => {
    mockApi.setMode.mockResolvedValue({ mode: 'LIVE' })
    mockApi.health.mockResolvedValueOnce(health).mockResolvedValue({ ...health, mode: 'LIVE' })
    render(<App />)
    await waitFor(() => screen.getByText('Switch to LIVE'))
    fireEvent.click(screen.getByText('Switch to LIVE'))
    fireEvent.click(screen.getByText('Confirm'))
    await waitFor(() => expect(mockApi.setMode).toHaveBeenCalledWith('LIVE'))
  })

  it('handles fetch error gracefully', async () => {
    mockApi.health.mockRejectedValue(new Error('network'))
    render(<App />)
    await waitFor(() => expect(screen.queryByText('PAPER')).not.toBeInTheDocument())
  })

  it('polls every 5 seconds', async () => {
    render(<App />)
    await waitFor(() => screen.getAllByText('PAPER'))
    const initialCalls = mockApi.health.mock.calls.length
    await act(async () => {
      vi.advanceTimersByTime(5000)
    })
    await waitFor(() => expect(mockApi.health.mock.calls.length).toBeGreaterThan(initialCalls))
  })
})
