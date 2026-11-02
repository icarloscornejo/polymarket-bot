import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { HealthBar } from '../components/HealthBar'
import type { HealthStatus } from '../types'

const mockHealth: HealthStatus = {
  status: 'ok', mode: 'PAPER', current_params_id: 1,
  timezone: 'America/El_Salvador', btc_feed_active: 'binance',
}

describe('HealthBar', () => {
  it('shows skeleton when loading', () => {
    const { container } = render(<HealthBar health={null} loading={true} />)
    expect(container.querySelector('.animate-pulse')).toBeTruthy()
  })
  it('renders nothing when not loading and no health', () => {
    const { container } = render(<HealthBar health={null} loading={false} />)
    expect(container.firstChild).toBeNull()
  })
  it('shows mode badge', () => {
    render(<HealthBar health={mockHealth} loading={false} />)
    expect(screen.getByText('PAPER')).toBeInTheDocument()
  })
  it('shows btc feed source', () => {
    render(<HealthBar health={mockHealth} loading={false} />)
    expect(screen.getByText('BTC: binance')).toBeInTheDocument()
  })
  it('shows timezone', () => {
    render(<HealthBar health={mockHealth} loading={false} />)
    expect(screen.getByText('America/El_Salvador')).toBeInTheDocument()
  })
  it('shows LIVE badge when in LIVE mode', () => {
    render(<HealthBar health={{ ...mockHealth, mode: 'LIVE' }} loading={false} />)
    expect(screen.getByText('LIVE')).toBeInTheDocument()
  })
  it('shows coinbase badge when btc_feed is coinbase', () => {
    render(<HealthBar health={{ ...mockHealth, btc_feed_active: 'coinbase' }} loading={false} />)
    expect(screen.getByText('BTC: coinbase')).toBeInTheDocument()
  })
  it('shows error status badge when status is not ok', () => {
    render(<HealthBar health={{ ...mockHealth, status: 'error' }} loading={false} />)
    expect(screen.getByText('error')).toBeInTheDocument()
  })
})
