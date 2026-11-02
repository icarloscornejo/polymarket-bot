import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { SignalsFeed } from '../components/SignalsFeed'
import type { Signal } from '../types'

const makeSignal = (overrides: Partial<Signal> = {}): Signal => ({
  id: 1, timestamp: '2026-04-01T10:00:00Z', market_id: 'mkt-1',
  side: 'YES', yes_price: 0.6, no_price: 0.4, btc_price: 95000,
  btc_price_source: 'binance', dtt: 500, time_to_close_sec: 20,
  potential_gain: 0.8, action_taken: 'PAPER_TRADE', skip_reason: null,
  strategy_params_id: 1, ...overrides,
})

describe('SignalsFeed', () => {
  it('shows empty message when no signals', () => {
    render(<SignalsFeed signals={[]} />)
    expect(screen.getByText('No signals yet')).toBeInTheDocument()
  })
  it('renders signal rows', () => {
    render(<SignalsFeed signals={[makeSignal()]} />)
    expect(screen.getByText('YES')).toBeInTheDocument()
    expect(screen.getByText('PAPER_TRADE')).toBeInTheDocument()
  })
  it('shows skip reason when present', () => {
    render(<SignalsFeed signals={[makeSignal({ action_taken: 'SKIPPED', skip_reason: 'DTT_BELOW_MIN' })]} />)
    expect(screen.getByText('SKIPPED (DTT_BELOW_MIN)')).toBeInTheDocument()
  })
  it('shows NO side badge', () => {
    render(<SignalsFeed signals={[makeSignal({ side: 'NO' })]} />)
    expect(screen.getByText('NO')).toBeInTheDocument()
  })
  it('shows LIVE_TRADE action', () => {
    render(<SignalsFeed signals={[makeSignal({ action_taken: 'LIVE_TRADE' })]} />)
    expect(screen.getByText('LIVE_TRADE')).toBeInTheDocument()
  })
})
