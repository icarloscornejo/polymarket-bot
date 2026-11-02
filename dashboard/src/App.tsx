import { useState, useCallback } from 'react'
import { api } from './api/client'
import { usePolling } from './hooks/usePolling'
import { HealthBar } from './components/HealthBar'
import { ModeToggle } from './components/ModeToggle'
import { SignalsFeed } from './components/SignalsFeed'
import { TradesTable } from './components/TradesTable'
import { PerformanceCard } from './components/PerformanceCard'
import { StrategyPanel } from './components/StrategyPanel'
import { SettingsPanel } from './components/SettingsPanel'
import { MaintenanceCard } from './components/MaintenanceCard'
import type {
  HealthStatus, Signal, Trade, MonthlyPerformance,
  StrategyParams, StrategyParamsUpdate, RuntimeSettings, MaintenanceStatus,
} from './types'

type Tab = 'overview' | 'trades' | 'strategy' | 'maintenance'

export default function App() {
  const [tab, setTab] = useState<Tab>('overview')

  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [signals, setSignals] = useState<Signal[]>([])
  const [trades, setTrades] = useState<Trade[]>([])
  const [perf, setPerf] = useState<MonthlyPerformance | null>(null)
  const [strategy, setStrategy] = useState<StrategyParams | null>(null)
  const [settings, setSettings] = useState<RuntimeSettings | null>(null)
  const [maintenance, setMaintenance] = useState<MaintenanceStatus | null>(null)

  const now = new Date()

  const fetchAll = useCallback(async () => {
    try {
      const [h, s, t, p, sp, st, m] = await Promise.all([
        api.health(),
        api.signals(50),
        api.trades(),
        api.monthlyPerformance(now.getFullYear(), now.getMonth() + 1),
        api.strategy(),
        api.settings(),
        api.maintenanceStatus(),
      ])
      setHealth(h)
      setSignals(s)
      setTrades(t)
      setPerf(p)
      setStrategy(sp)
      setSettings(st)
      setMaintenance(m)
    } catch {
      // silent – stale data shown until next poll
    } finally {
      setHealthLoading(false)
    }
  }, [])

  usePolling(fetchAll, 5000)

  async function handleToggleMode(mode: 'PAPER' | 'LIVE') {
    await api.setMode(mode)
    const h = await api.health()
    setHealth(h)
  }

  async function handleUpdateStrategy(update: StrategyParamsUpdate) {
    const updated = await api.updateStrategy(update)
    setStrategy(updated)
  }

  async function handleUpdateSettings(timezone: string) {
    const updated = await api.updateSettings(timezone)
    setSettings(updated)
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'trades', label: 'Trades' },
    { id: 'strategy', label: 'Strategy' },
    { id: 'maintenance', label: 'DB' },
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <HealthBar health={health} loading={healthLoading} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
        {/* Mode toggle */}
        <div className="flex items-center justify-between mb-6">
          {health && (
            <ModeToggle mode={health.mode} onToggle={handleToggleMode} />
          )}
        </div>

        {/* Tab nav */}
        <nav className="flex gap-1 mb-6 bg-gray-900 rounded-lg p-1 w-fit">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                tab === t.id
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {/* Tab content */}
        {tab === 'overview' && (
          <div className="space-y-6">
            <PerformanceCard perf={perf} year={now.getFullYear()} month={now.getMonth() + 1} />
            <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
              <h2 className="text-sm font-medium text-gray-400 mb-4">Recent Signals</h2>
              <SignalsFeed signals={signals} />
            </div>
          </div>
        )}

        {tab === 'trades' && (
          <div className="bg-gray-900 rounded-xl border border-gray-800 p-4 sm:p-6">
            <h2 className="text-sm font-medium text-gray-400 mb-4">
              All Trades ({trades.length})
            </h2>
            <TradesTable trades={trades} />
          </div>
        )}

        {tab === 'strategy' && (
          <div className="space-y-6">
            <StrategyPanel params={strategy} onUpdate={handleUpdateStrategy} />
            <SettingsPanel settings={settings} onUpdate={handleUpdateSettings} />
          </div>
        )}

        {tab === 'maintenance' && (
          <MaintenanceCard status={maintenance} />
        )}
      </div>
    </div>
  )
}
