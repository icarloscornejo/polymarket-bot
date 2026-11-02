import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { PerformanceCard } from '../components/PerformanceCard'
import type { MonthlyPerformance } from '../types'

const mockPerf: MonthlyPerformance = {
  year: 2026, month: 4, timezone: 'UTC',
  pnl_usd_paper: 5.0, pnl_usd_live: 0,
  total_invested_usd_paper: 100, total_invested_usd_live: 0,
  total_trades: 10, winning_trades: 7,
  pnl_pct_paper: 5.0, pnl_pct_live: 0, win_rate: 0.7,
}

describe('PerformanceCard', () => {
  it('shows loading skeleton when perf is null', () => {
    const { container } = render(<PerformanceCard perf={null} year={2026} month={4} />)
    expect(container.querySelector('.animate-pulse')).toBeTruthy()
  })
  it('shows monthly label', () => {
    render(<PerformanceCard perf={mockPerf} year={2026} month={4} />)
    expect(screen.getByText(/Apr 2026/)).toBeInTheDocument()
  })
  it('shows paper pnl pct', () => {
    render(<PerformanceCard perf={mockPerf} year={2026} month={4} />)
    expect(screen.getByText('5.00%')).toBeInTheDocument()
  })
  it('shows win rate', () => {
    render(<PerformanceCard perf={mockPerf} year={2026} month={4} />)
    expect(screen.getByText('70.0%')).toBeInTheDocument()
  })
  it('shows total trades', () => {
    render(<PerformanceCard perf={mockPerf} year={2026} month={4} />)
    expect(screen.getByText('10')).toBeInTheDocument()
  })
  it('shows negative paper pnl', () => {
    render(<PerformanceCard perf={{ ...mockPerf, pnl_pct_paper: -3.5, pnl_usd_paper: -3.5 }} year={2026} month={4} />)
    expect(screen.getByText('-3.50%')).toBeInTheDocument()
  })
})
