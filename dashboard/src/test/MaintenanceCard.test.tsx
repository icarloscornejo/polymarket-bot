import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MaintenanceCard } from '../components/MaintenanceCard'
import type { MaintenanceStatus } from '../types'

const mockStatus: MaintenanceStatus = {
  last_cleanup_at: '2026-04-01T03:00:00Z',
  oldest_raw_snapshot_timestamp: '2026-03-25T00:00:00Z',
  total_raw_snapshots: 500,
  total_archived_markets: 10,
  total_daily_summaries: 7,
  next_cleanup_at: '2026-04-02T03:00:00Z',
}

describe('MaintenanceCard', () => {
  it('shows loading skeleton when status is null', () => {
    const { container } = render(<MaintenanceCard status={null} />)
    expect(container.querySelector('.animate-pulse')).toBeTruthy()
  })
  it('shows snapshot count', () => {
    render(<MaintenanceCard status={mockStatus} />)
    expect(screen.getByText('500')).toBeInTheDocument()
  })
  it('shows archived markets count', () => {
    render(<MaintenanceCard status={mockStatus} />)
    expect(screen.getByText('10')).toBeInTheDocument()
  })
  it('shows daily summaries count', () => {
    render(<MaintenanceCard status={mockStatus} />)
    expect(screen.getByText('7')).toBeInTheDocument()
  })
  it('shows dash when last_cleanup_at is null', () => {
    render(<MaintenanceCard status={{ ...mockStatus, last_cleanup_at: null }} />)
    expect(screen.getAllByText('\u2014').length).toBeGreaterThan(0)
  })
  it('shows dash when oldest_raw_snapshot_timestamp is null', () => {
    render(<MaintenanceCard status={{ ...mockStatus, oldest_raw_snapshot_timestamp: null }} />)
    expect(screen.getAllByText('\u2014').length).toBeGreaterThan(0)
  })
})
