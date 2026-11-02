import type { Trade } from '../types'
import { Badge } from './Badge'

interface TradesTableProps {
  trades: Trade[]
}

export function TradesTable({ trades }: TradesTableProps) {
  if (trades.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 text-sm">No trades yet</div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-gray-400 border-b border-gray-800">
            <th className="pb-2 pr-4">Market</th>
            <th className="pb-2 pr-4">Side</th>
            <th className="pb-2 pr-4">Entry</th>
            <th className="pb-2 pr-4">Size</th>
            <th className="pb-2 pr-4">PnL</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2">Mode</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
              <td className="py-2 pr-4 font-mono text-xs text-gray-300 max-w-24 truncate">
                {t.market_id}
              </td>
              <td className="py-2 pr-4">
                <Badge color={t.side === 'YES' ? 'green' : 'red'}>{t.side}</Badge>
              </td>
              <td className="py-2 pr-4 text-gray-300">{(t.entry_price * 100).toFixed(1)}¢</td>
              <td className="py-2 pr-4 text-gray-300">${t.position_size_usd.toFixed(0)}</td>
              <td className="py-2 pr-4">
                {t.pnl_usd !== null ? (
                  <span className={t.pnl_usd >= 0 ? 'text-profit' : 'text-loss'}>
                    {t.pnl_usd >= 0 ? '+' : ''}{t.pnl_usd.toFixed(2)}
                  </span>
                ) : (
                  <span className="text-gray-500">—</span>
                )}
              </td>
              <td className="py-2 pr-4">
                <Badge color={t.status === 'OPEN' ? 'blue' : 'gray'}>{t.status}</Badge>
              </td>
              <td className="py-2">
                <Badge color={t.mode === 'LIVE' ? 'green' : 'yellow'}>{t.mode}</Badge>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
