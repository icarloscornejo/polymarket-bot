import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { StrategyPanel } from '../components/StrategyPanel'
import type { StrategyParams } from '../types'

const mockParams: StrategyParams = {
  id: 1, valid_from: '2026-04-01T00:00:00Z', valid_to: null, updated_by: 'CONFIG',
  entry_window_min_sec: 5, entry_window_max_sec: 25,
  min_dtt: 10, min_gain_usd: 0.75, position_size_usd: 10,
  snapshot_interval_ms: 1000, logging_window_buffer_sec: 10,
}

describe('StrategyPanel', () => {
  it('shows loading skeleton when params is null', () => {
    const { container } = render(<StrategyPanel params={null} onUpdate={vi.fn()} />)
    expect(container.querySelector('.animate-pulse')).toBeTruthy()
  })
  it('shows params display view', () => {
    render(<StrategyPanel params={mockParams} onUpdate={vi.fn()} />)
    expect(screen.getByText('5\u201325s')).toBeInTheDocument()
    expect(screen.getAllByText('$10').length).toBeGreaterThan(0)
  })
  it('clicking Edit shows form', () => {
    render(<StrategyPanel params={mockParams} onUpdate={vi.fn()} />)
    fireEvent.click(screen.getByText('Edit'))
    expect(screen.getByText('Save')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })
  it('Cancel hides form', () => {
    render(<StrategyPanel params={mockParams} onUpdate={vi.fn()} />)
    fireEvent.click(screen.getByText('Edit'))
    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByText('Save')).not.toBeInTheDocument()
  })
  it('Save calls onUpdate', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined)
    render(<StrategyPanel params={mockParams} onUpdate={onUpdate} />)
    fireEvent.click(screen.getByText('Edit'))
    fireEvent.click(screen.getByText('Save'))
    await waitFor(() => expect(onUpdate).toHaveBeenCalled())
  })
  it('shows error when save fails', async () => {
    const onUpdate = vi.fn().mockRejectedValue(new Error('Save failed'))
    render(<StrategyPanel params={mockParams} onUpdate={onUpdate} />)
    fireEvent.click(screen.getByText('Edit'))
    fireEvent.click(screen.getByText('Save'))
    await waitFor(() => expect(screen.getByText('Save failed')).toBeInTheDocument())
  })
  it('shows generic error when non-Error thrown', async () => {
    const onUpdate = vi.fn().mockRejectedValue('oops')
    render(<StrategyPanel params={mockParams} onUpdate={onUpdate} />)
    fireEvent.click(screen.getByText('Edit'))
    fireEvent.click(screen.getByText('Save'))
    await waitFor(() => expect(screen.getByText('Save failed')).toBeInTheDocument())
  })
})
