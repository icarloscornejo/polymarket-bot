import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { ModeToggle } from '../components/ModeToggle'

describe('ModeToggle', () => {
  it('shows current mode and switch button', () => {
    render(<ModeToggle mode="PAPER" onToggle={vi.fn()} />)
    expect(screen.getByText('PAPER')).toBeInTheDocument()
    expect(screen.getByText('Switch to LIVE')).toBeInTheDocument()
  })
  it('shows confirmation dialog on click', () => {
    render(<ModeToggle mode="PAPER" onToggle={vi.fn()} />)
    fireEvent.click(screen.getByText('Switch to LIVE'))
    expect(screen.getByText(/Switch to LIVE\?/)).toBeInTheDocument()
    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })
  it('cancel hides confirmation', () => {
    render(<ModeToggle mode="PAPER" onToggle={vi.fn()} />)
    fireEvent.click(screen.getByText('Switch to LIVE'))
    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByText('Confirm')).not.toBeInTheDocument()
  })
  it('confirm calls onToggle with new mode', async () => {
    const onToggle = vi.fn().mockResolvedValue(undefined)
    render(<ModeToggle mode="PAPER" onToggle={onToggle} />)
    fireEvent.click(screen.getByText('Switch to LIVE'))
    fireEvent.click(screen.getByText('Confirm'))
    await waitFor(() => expect(onToggle).toHaveBeenCalledWith('LIVE'))
  })
  it('shows Switch to PAPER when in LIVE mode', () => {
    render(<ModeToggle mode="LIVE" onToggle={vi.fn()} />)
    expect(screen.getByText('Switch to PAPER')).toBeInTheDocument()
  })
  it('disables confirm button while loading', async () => {
    let resolve: () => void
    const onToggle = vi.fn().mockReturnValue(new Promise<void>(r => { resolve = r }))
    render(<ModeToggle mode="PAPER" onToggle={onToggle} />)
    fireEvent.click(screen.getByText('Switch to LIVE'))
    fireEvent.click(screen.getByText('Confirm'))
    await waitFor(() => expect(screen.getByText('Switching...')).toBeDisabled())
    resolve!()
  })
})
