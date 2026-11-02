import type { MaintenanceStatus } from '../types'

interface MaintenanceCardProps {
  status: MaintenanceStatus | null
}

function fmt(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

export function MaintenanceCard({ status }: MaintenanceCardProps) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
      <h2 className="text-sm font-medium text-gray-400 mb-4">DB Status</h2>
      {!status ? (
        <div className="animate-pulse space-y-2">
          <div className="h-4 w-48 bg-gray-700 rounded" />
          <div className="h-4 w-32 bg-gray-700 rounded" />
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
          <Stat label="Raw snapshots" value={String(status.total_raw_snapshots)} />
          <Stat label="Archived markets" value={String(status.total_archived_markets)} />
          <Stat label="Daily summaries" value={String(status.total_daily_summaries)} />
          <div className="col-span-2 sm:col-span-1">
            <p className="text-xs text-gray-500">Last cleanup</p>
            <p className="text-gray-300">{fmt(status.last_cleanup_at)}</p>
          </div>
          <div className="col-span-2 sm:col-span-1">
            <p className="text-xs text-gray-500">Next cleanup</p>
            <p className="text-gray-300">{fmt(status.next_cleanup_at)}</p>
          </div>
          <div className="col-span-2 sm:col-span-1">
            <p className="text-xs text-gray-500">Oldest snapshot</p>
            <p className="text-gray-300">{fmt(status.oldest_raw_snapshot_timestamp)}</p>
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-2xl font-bold text-white">{value}</p>
    </div>
  )
}
