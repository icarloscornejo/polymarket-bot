import { useState } from 'react'
import { Badge } from './Badge'

interface ModeToggleProps {
  mode: 'PAPER' | 'LIVE'
  onToggle: (mode: 'PAPER' | 'LIVE') => Promise<void>
}

export function ModeToggle({ mode, onToggle }: ModeToggleProps) {
  const [confirming, setConfirming] = useState(false)
  const [loading, setLoading] = useState(false)

  const target = mode === 'PAPER' ? 'LIVE' : 'PAPER'

  async function handleConfirm() {
    setLoading(true)
    try {
      await onToggle(target)
    } finally {
      setLoading(false)
      setConfirming(false)
    }
  }

  if (confirming) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-400">Switch to {target}?</span>
        <button
          onClick={handleConfirm}
          disabled={loading}
          className="px-3 py-1 rounded text-sm bg-red-700 hover:bg-red-600 text-white disabled:opacity-50"
        >
          {loading ? 'Switching...' : 'Confirm'}
        </button>
        <button
          onClick={() => setConfirming(false)}
          className="px-3 py-1 rounded text-sm bg-gray-700 hover:bg-gray-600 text-white"
        >
          Cancel
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <Badge color={mode === 'LIVE' ? 'green' : 'yellow'}>{mode}</Badge>
      <button
        onClick={() => setConfirming(true)}
        className="px-3 py-1 rounded text-sm bg-gray-700 hover:bg-gray-600 text-white"
      >
        Switch to {target}
      </button>
    </div>
  )
}
