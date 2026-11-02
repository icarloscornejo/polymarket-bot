import type { Signal } from '../types'
import { Badge } from './Badge'

interface SignalsFeedProps {
  signals: Signal[]
}

function actionColor(action: Signal['action_taken']): 'green' | 'blue' | 'gray' {
  if (action === 'PAPER_TRADE') return 'green'
  if (action === 'LIVE_TRADE') return 'blue'
  return 'gray'
}

export function SignalsFeed({ signals }: SignalsFeedProps) {
  if (signals.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 text-sm">No signals yet</div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-800">
            <th className="pb-2 pr-4">Time</th>
            <th className="pb-2 pr-4">Market</th>
            <th className="pb-2 pr-4">Side</th>
            <th className="pb-2 pr-4">DTT</th>
            <th className="pb-2 pr-4">Gain</th>
            <th className="pb-2">Action</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s) => (
            <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
              <td className="py-2 pr-4 text-gray-400 whitespace-nowrap">
                {new Date(s.timestamp).toLocaleTimeString()}
              </td>
              <td className="py-2 pr-4 font-mono text-xs text-gray-300 max-w-24 truncate">
                {s.market_id}
              </td>
              <td className="py-2 pr-4">
                <Badge color={s.side === 'YES' ? 'green' : 'red'}>{s.side}</Badge>
              </td>
              <td className="py-2 pr-4 text-gray-300">${s.dtt.toFixed(0)}</td>
              <td className="py-2 pr-4 text-profit">${s.potential_gain.toFixed(2)}</td>
              <td className="py-2">
                <Badge color={actionColor(s.action_taken)}>
                  {s.action_taken}
                  {s.skip_reason ? ` (${s.skip_reason})` : ''}
                </Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
