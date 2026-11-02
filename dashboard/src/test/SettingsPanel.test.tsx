import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { SettingsPanel } from '../components/SettingsPanel'
import type { RuntimeSettings } from '../types'

const mockSettings: RuntimeSettings = { timezone: 'America/El_Salvador', updated_at: '2026-04-01T00:00:00Z' }

describe('SettingsPanel', () => {
  it('shows current timezone', () => {
    render(<SettingsPanel settings={mockSettings} onUpdate={vi.fn()} />)
    expect(screen.getByText('America/El_Salvador')).toBeInTheDocument()
  })
  it('shows placeholder when settings is null', () => {
    render(<SettingsPanel settings={null} onUpdate={vi.fn()} />)
    expect(screen.getByText('...')).toBeInTheDocument()
  })
  it('clicking button calls onUpdate with typed value', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined)
    render(<SettingsPanel settings={mockSettings} onUpdate={onUpdate} />)
    fireEvent.change(screen.getByPlaceholderText('e.g. America/New_York'), { target: { value: 'UTC' } })
    fireEvent.click(screen.getByText('Update timezone'))
    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith('UTC'))
  })
  it('uses existing timezone when input is empty', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined)
    render(<SettingsPanel settings={mockSettings} onUpdate={onUpdate} />)
    fireEvent.click(screen.getByText('Update timezone'))
    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith('America/El_Salvador'))
  })
  it('shows success message after update', async () => {
    const onUpdate = vi.fn().mockResolvedValue(undefined)
    render(<SettingsPanel settings={mockSettings} onUpdate={onUpdate} />)
    fireEvent.click(screen.getByText('Update timezone'))
    await waitFor(() => expect(screen.getByText('Timezone updated')).toBeInTheDocument())
  })
  it('shows error on failure', async () => {
    const onUpdate = vi.fn().mockRejectedValue(new Error('Bad zone'))
    render(<SettingsPanel settings={mockSettings} onUpdate={onUpdate} />)
    fireEvent.click(screen.getByText('Update timezone'))
    await waitFor(() => expect(screen.getByText('Bad zone')).toBeInTheDocument())
  })
  it('shows generic error when non-Error thrown', async () => {
    const onUpdate = vi.fn().mockRejectedValue('oops')
    render(<SettingsPanel settings={null} onUpdate={onUpdate} />)
    fireEvent.click(screen.getByText('Update timezone'))
    await waitFor(() => expect(screen.getByText('Update failed')).toBeInTheDocument())
  })
})
