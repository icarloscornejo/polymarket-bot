import type { MonthlyPerformance } from '../types'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

interface PerformanceCardProps {
  perf: MonthlyPerformance | null
  year: number
  month: number
}

export function PerformanceCard({ perf, year, month }: PerformanceCardProps) {
  const label = `${MONTHS[month - 1]} ${year}`

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
      <h2 className="text-sm font-medium text-gray-400 mb-4">Monthly Performance — {label}</h2>
      {!perf ? (
        <div className="animate-pulse space-y-2">
          <div className="h-8 w-24 bg-gray-700 rounded" />
          <div className="h-4 w-32 bg-gray-700 rounded" />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <Stat label="PAPER %" value={`${perf.pnl_pct_paper.toFixed(2)}%`} positive={perf.pnl_pct_paper >= 0} />
            <Stat label="LIVE %" value={`${perf.pnl_pct_live.toFixed(2)}%`} positive={perf.pnl_pct_live >= 0} />
            <Stat label="Win Rate" value={`${(perf.win_rate * 100).toFixed(1)}%`} />
            <Stat label="Trades" value={String(perf.total_trades)} />
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm text-gray-400">
            <div>PAPER PnL: <span className={perf.pnl_usd_paper >= 0 ? 'text-profit' : 'text-loss'}>${perf.pnl_usd_paper.toFixed(2)}</span></div>
            <div>LIVE PnL: <span className={perf.pnl_usd_live >= 0 ? 'text-profit' : 'text-loss'}>${perf.pnl_usd_live.toFixed(2)}</span></div>
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  const color = positive === undefined ? 'text-white' : positive ? 'text-profit' : 'text-loss'
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}
