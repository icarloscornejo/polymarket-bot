import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { TradesTable } from '../components/TradesTable'
import type { Trade } from '../types'

const makeTrade = (overrides: Partial<Trade> = {}): Trade => ({
  id: 1, signal_id: 1, market_id: 'mkt-1', side: 'YES',
  entry_price: 0.6, entry_btc_price: 95000, entry_dtt: 500,
  entry_time_to_close: 20, position_size_usd: 10, status: 'OPEN',
  exit_price: null, resolved_at: null, pnl_usd: null, pnl_pct: null,
  mode: 'PAPER', opened_at: '2026-04-01T10:00:00Z', ...overrides,
})

describe('TradesTable', () => {
  it('shows empty message when no trades', () => {
    render(<TradesTable trades={[]} />)
    expect(screen.getByText('No trades yet')).toBeInTheDocument()
  })
  it('renders trade row', () => {
    render(<TradesTable trades={[makeTrade()]} />)
    expect(screen.getByText('OPEN')).toBeInTheDocument()
    expect(screen.getByText('PAPER')).toBeInTheDocument()
  })
  it('shows positive PnL in green', () => {
    render(<TradesTable trades={[makeTrade({ pnl_usd: 1.5, status: 'RESOLVED' })]} />)
    expect(screen.getByText('+1.50')).toBeInTheDocument()
  })
  it('shows negative PnL', () => {
    render(<TradesTable trades={[makeTrade({ pnl_usd: -0.5, status: 'RESOLVED' })]} />)
    expect(screen.getByText('-0.50')).toBeInTheDocument()
  })
  it('shows dash when pnl is null', () => {
    render(<TradesTable trades={[makeTrade({ pnl_usd: null })]} />)
    expect(screen.getByText('\u2014')).toBeInTheDocument()
  })
  it('shows NO side badge', () => {
    render(<TradesTable trades={[makeTrade({ side: 'NO' })]} />)
    expect(screen.getByText('NO')).toBeInTheDocument()
  })
  it('shows LIVE mode badge', () => {
    render(<TradesTable trades={[makeTrade({ mode: 'LIVE' })]} />)
    expect(screen.getByText('LIVE')).toBeInTheDocument()
  })
})
