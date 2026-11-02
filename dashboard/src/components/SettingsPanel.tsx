import { useState } from 'react'
import type { RuntimeSettings } from '../types'

interface SettingsPanelProps {
  settings: RuntimeSettings | null
  onUpdate: (timezone: string) => Promise<void>
}

export function SettingsPanel({ settings, onUpdate }: SettingsPanelProps) {
  const [tz, setTz] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  async function save() {
    setSaving(true)
    setError(null)
    setSuccess(false)
    try {
      await onUpdate(tz || (settings?.timezone ?? ''))
      setSuccess(true)
      setTz('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
      <h2 className="text-sm font-medium text-gray-400 mb-4">Settings</h2>
      <div className="space-y-3 max-w-sm">
        <div>
          <label className="text-xs text-gray-500 block mb-1">Timezone</label>
          <p className="text-white text-sm mb-2">{settings?.timezone ?? '...'}</p>
          <input
            type="text"
            placeholder="e.g. America/New_York"
            value={tz}
            onChange={(e) => setTz(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>
        {error && <p className="text-loss text-xs">{error}</p>}
        {success && <p className="text-profit text-xs">Timezone updated</p>}
        <button
          onClick={save}
          disabled={saving}
          className="px-4 py-2 rounded text-sm bg-blue-700 hover:bg-blue-600 text-white disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Update timezone'}
        </button>
      </div>
    </div>
  )
}
