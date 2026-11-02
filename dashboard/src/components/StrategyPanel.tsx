import { useState } from 'react'
import type { StrategyParams, StrategyParamsUpdate } from '../types'

interface StrategyPanelProps {
  params: StrategyParams | null
  onUpdate: (update: StrategyParamsUpdate) => Promise<void>
}

export function StrategyPanel({ params, onUpdate }: StrategyPanelProps) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<StrategyParamsUpdate>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function startEdit() {
    if (!params) return
    setDraft({
      entry_window_min_sec: params.entry_window_min_sec,
      entry_window_max_sec: params.entry_window_max_sec,
      min_dtt: params.min_dtt,
      min_gain_usd: params.min_gain_usd,
      position_size_usd: params.position_size_usd,
      snapshot_interval_ms: params.snapshot_interval_ms,
      logging_window_buffer_sec: params.logging_window_buffer_sec,
    })
    setEditing(true)
    setError(null)
  }

  async function save() {
    setSaving(true)
    setError(null)
    try {
      await onUpdate(draft)
      setEditing(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  if (!params) {
    return (
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
        <div className="animate-pulse space-y-2">
          <div className="h-4 w-32 bg-gray-700 rounded" />
          <div className="h-4 w-48 bg-gray-700 rounded" />
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-medium text-gray-400">Strategy Params #{params.id}</h2>
        {!editing && (
          <button onClick={startEdit} className="text-xs text-blue-400 hover:text-blue-300">
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <div className="space-y-3">
          <ParamInput label="Entry window min (s)" value={draft.entry_window_min_sec ?? 0}
            onChange={(v) => setDraft(d => ({ ...d, entry_window_min_sec: v }))} />
          <ParamInput label="Entry window max (s)" value={draft.entry_window_max_sec ?? 0}
            onChange={(v) => setDraft(d => ({ ...d, entry_window_max_sec: v }))} />
          <ParamInput label="Min DTT ($)" value={draft.min_dtt ?? 0} step={0.5}
            onChange={(v) => setDraft(d => ({ ...d, min_dtt: v }))} />
          <ParamInput label="Min gain ($)" value={draft.min_gain_usd ?? 0} step={0.05}
            onChange={(v) => setDraft(d => ({ ...d, min_gain_usd: v }))} />
          <ParamInput label="Position size ($)" value={draft.position_size_usd ?? 0}
            onChange={(v) => setDraft(d => ({ ...d, position_size_usd: v }))} />
          <ParamInput label="Snapshot interval (ms)" value={draft.snapshot_interval_ms ?? 0}
            onChange={(v) => setDraft(d => ({ ...d, snapshot_interval_ms: v }))} />
          <ParamInput label="Logging buffer (s)" value={draft.logging_window_buffer_sec ?? 0}
            onChange={(v) => setDraft(d => ({ ...d, logging_window_buffer_sec: v }))} />
          {error && <p className="text-loss text-xs">{error}</p>}
          <div className="flex gap-2 pt-1">
            <button onClick={save} disabled={saving}
              className="px-3 py-1 rounded text-sm bg-blue-700 hover:bg-blue-600 text-white disabled:opacity-50">
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button onClick={() => setEditing(false)}
              className="px-3 py-1 rounded text-sm bg-gray-700 hover:bg-gray-600 text-white">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
          <ParamView label="Window" value={`${params.entry_window_min_sec}–${params.entry_window_max_sec}s`} />
          <ParamView label="Min DTT" value={`$${params.min_dtt}`} />
          <ParamView label="Min gain" value={`$${params.min_gain_usd}`} />
          <ParamView label="Position" value={`$${params.position_size_usd}`} />
          <ParamView label="Interval" value={`${params.snapshot_interval_ms}ms`} />
          <ParamView label="Log buffer" value={`${params.logging_window_buffer_sec}s`} />
        </div>
      )}
    </div>
  )
}

function ParamInput({ label, value, step = 1, onChange }: {
  label: string; value: number; step?: number; onChange: (v: number) => void
}) {
  return (
    <label className="flex items-center justify-between gap-4">
      <span className="text-xs text-gray-400 w-40">{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-28 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white text-right focus:outline-none focus:border-blue-500"
      />
    </label>
  )
}

function ParamView({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-white font-medium">{value}</p>
    </div>
  )
}
