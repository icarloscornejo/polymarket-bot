import type { HealthStatus } from '../types'
import { Badge } from './Badge'

interface HealthBarProps {
  health: HealthStatus | null
  loading: boolean
}

export function HealthBar({ health, loading }: HealthBarProps) {
  if (loading) {
    return (
      <header className="bg-gray-900 border-b border-gray-800 px-4 sm:px-6 py-3">
        <div className="animate-pulse flex gap-4">
          <div className="h-5 w-24 bg-gray-700 rounded" />
          <div className="h-5 w-20 bg-gray-700 rounded" />
          <div className="h-5 w-32 bg-gray-700 rounded" />
        </div>
      </header>
    )
  }

  if (!health) return null

  return (
    <header className="bg-gray-900 border-b border-gray-800 px-4 sm:px-6 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-base font-semibold text-white mr-2">Polymarket Bot</h1>
        <Badge color={health.mode === 'LIVE' ? 'green' : 'yellow'}>
          {health.mode}
        </Badge>
        <Badge color={health.btc_feed_active === 'binance' ? 'green' : 'yellow'}>
          BTC: {health.btc_feed_active}
        </Badge>
        <Badge color="gray">{health.timezone}</Badge>
        <Badge color={health.status === 'ok' ? 'green' : 'red'}>
          {health.status}
        </Badge>
      </div>
    </header>
  )
}
