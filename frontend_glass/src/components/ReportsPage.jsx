import { useEffect, useMemo, useState } from 'react'

const palette = ['#FBE4D8', '#DFB6B2', '#854F6C', '#522B5B', '#2B124C', '#ffe600', '#00d4ff', '#5fe39a']

const currencySymbols = {
  USD: '$',
  EUR: 'EUR',
  GBP: 'GBP',
  CZK: 'CZK',
}

function formatMoney(amount, currencyCode = 'USD') {
  const symbol = currencySymbols[currencyCode] || currencyCode || '$'
  const value = Number(amount || 0)
  if (symbol === 'CZK') return `${value.toFixed(0)} ${symbol}`
  return `${symbol}${value.toFixed(2)}`
}

function monthlyCost(subscription) {
  const cost = Number(subscription.cost || 0)
  switch (subscription.billing_cycle) {
    case 'yearly': return cost / 12
    case 'weekly': return (cost * 52) / 12
    case 'daily': return cost * 30
    case 'one-time': return 0
    case 'monthly':
    default: return cost
  }
}

function annualCost(subscription) {
  const cost = Number(subscription.cost || 0)
  switch (subscription.billing_cycle) {
    case 'yearly': return cost
    case 'weekly': return cost * 52
    case 'daily': return cost * 365
    case 'one-time': return cost
    case 'monthly':
    default: return cost * 12
  }
}

function monthKey(date) {
  return date.toLocaleDateString(undefined, { month: 'short' })
}

function ReportPanel({ title, eyebrow, children, className = '' }) {
  return (
    <section className={`glass-panel-lg rounded-3xl p-6 overflow-hidden ${className}`}>
      <div className="mb-5">
        {eyebrow && <p className="text-[11px] uppercase tracking-[0.24em] text-palette-300/80 mb-2">{eyebrow}</p>}
        <h2 className="text-xl font-semibold text-white">{title}</h2>
      </div>
      {children}
    </section>
  )
}

export default function ReportsPage({ subscriptions, events, stats, loading, usingDemoData, focusedSubscriptionId, onFocusedSubscriptionHandled }) {
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [category, setCategory] = useState('all')
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (focusedSubscriptionId) {
      setSelectedIds(new Set([focusedSubscriptionId]))
      onFocusedSubscriptionHandled?.()
    }
  }, [focusedSubscriptionId, onFocusedSubscriptionHandled])

  const categories = useMemo(() => ['all', ...new Set(subscriptions.map(s => s.category).filter(Boolean))], [subscriptions])
  const statuses = useMemo(() => ['all', ...new Set(subscriptions.map(s => s.status).filter(Boolean))], [subscriptions])

  const visibleSubscriptions = useMemo(() => {
    const searchTerm = search.trim().toLowerCase()
    return subscriptions.filter(sub => {
      const matchesCategory = category === 'all' || sub.category === category
      const matchesStatus = status === 'all' || sub.status === status
      const matchesSearch = !searchTerm || sub.service_name.toLowerCase().includes(searchTerm)
      const matchesSelection = selectedIds.size === 0 || selectedIds.has(sub.id)
      return matchesCategory && matchesStatus && matchesSearch && matchesSelection
    })
  }, [subscriptions, category, status, search, selectedIds])

  const report = useMemo(() => {
    const sorted = [...visibleSubscriptions].sort((a, b) => annualCost(b) - annualCost(a))
    const annualTotal = sorted.reduce((sum, sub) => sum + annualCost(sub), 0)
    const monthlyTotal = sorted.reduce((sum, sub) => sum + monthlyCost(sub), 0)
    const dominantCurrency = sorted.find(sub => sub.currency)?.currency || 'USD'
    const biggest = sorted[0]

    const byCategory = sorted.reduce((acc, sub) => {
      const key = sub.category || 'other'
      acc[key] = acc[key] || { name: key, annual: 0, monthly: 0, count: 0 }
      acc[key].annual += annualCost(sub)
      acc[key].monthly += monthlyCost(sub)
      acc[key].count += 1
      return acc
    }, {})

    const byCycle = sorted.reduce((acc, sub) => {
      const key = sub.billing_cycle || 'monthly'
      acc[key] = (acc[key] || 0) + 1
      return acc
    }, {})

    return {
      sorted,
      annualTotal,
      monthlyTotal,
      dominantCurrency,
      biggest,
      byCategory: Object.values(byCategory).sort((a, b) => b.annual - a.annual),
      byCycle,
    }
  }, [visibleSubscriptions])

  const trend = useMemo(() => {
    const now = new Date()
    const months = Array.from({ length: 12 }, (_, index) => {
      const date = new Date(now.getFullYear(), now.getMonth() - (11 - index), 1)
      return { key: `${date.getFullYear()}-${date.getMonth()}`, label: monthKey(date), value: 0 }
    })
    const selectedNames = new Set(visibleSubscriptions.map(s => s.service_name))

    events
      .filter(event => selectedNames.has(event.service_name))
      .forEach(event => {
        const date = new Date(event.event_date)
        const key = `${date.getFullYear()}-${date.getMonth()}`
        const bucket = months.find(month => month.key === key)
        if (bucket) bucket.value += Number(event.amount || 0)
      })

    if (months.every(month => month.value === 0)) {
      months.forEach(month => { month.value = report.monthlyTotal })
    }
    return months
  }, [events, visibleSubscriptions, report.monthlyTotal])

  const upcomingRenewals = useMemo(() => {
    return visibleSubscriptions
      .filter(sub => sub.next_billing_date)
      .map(sub => ({ ...sub, renewalDate: new Date(sub.next_billing_date) }))
      .filter(sub => !Number.isNaN(sub.renewalDate.getTime()))
      .sort((a, b) => a.renewalDate - b.renewalDate)
      .slice(0, 6)
  }, [visibleSubscriptions])

  const maxTrend = Math.max(...trend.map(month => month.value), 1)
  const topFiveTotal = report.sorted.slice(0, 5).reduce((sum, sub) => sum + annualCost(sub), 0)
  const concentration = report.annualTotal > 0 ? Math.round((topFiveTotal / report.annualTotal) * 100) : 0

  const toggleSelected = (id) => {
    setSelectedIds(previous => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (loading) {
    return <div className="glass-panel-lg rounded-3xl p-12 text-center text-gray-400">Preparing report cockpit...</div>
  }

  return (
    <div className="pb-12">
      <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="glass-panel-lg rounded-3xl p-8 relative overflow-hidden">
          <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-palette-300/10 blur-3xl"></div>
          <p className="text-[11px] uppercase tracking-[0.28em] text-palette-300/80 mb-3">Reports / 12-month ledger</p>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight text-white mb-4">
            Cost gravity map for every subscription.
          </h1>
          <p className="max-w-3xl text-sm md:text-base leading-7 text-palette-100/70">
            Treemap highlights the services pulling the most budget. Use filters and selection to compare categories, isolate a single service from card Insights, or review trends from captured payment events.
          </p>
          {usingDemoData && (
            <p className="mt-4 inline-flex rounded-full border border-yellow-500/30 bg-yellow-500/10 px-4 py-2 text-xs font-medium text-yellow-200">
              Demo mode: local test data is active because the API is offline.
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="glass-panel rounded-2xl p-5">
            <p className="text-[10px] uppercase tracking-[0.22em] text-gray-500">Analyzed annual</p>
            <p className="mt-2 text-3xl font-bold text-palette-100">{formatMoney(report.annualTotal, report.dominantCurrency)}</p>
          </div>
          <div className="glass-panel rounded-2xl p-5">
            <p className="text-[10px] uppercase tracking-[0.22em] text-gray-500">Top 5 weight</p>
            <p className="mt-2 text-3xl font-bold text-accent-yellow">{concentration}%</p>
          </div>
          <div className="glass-panel rounded-2xl p-5">
            <p className="text-[10px] uppercase tracking-[0.22em] text-gray-500">Subscriptions</p>
            <p className="mt-2 text-3xl font-bold text-white">{report.sorted.length}</p>
          </div>
          <div className="glass-panel rounded-2xl p-5">
            <p className="text-[10px] uppercase tracking-[0.22em] text-gray-500">All detected</p>
            <p className="mt-2 text-3xl font-bold text-palette-300">{stats.total_subscriptions}</p>
          </div>
        </div>
      </div>

      <ReportPanel title="Analysis selection" eyebrow="Scope control" className="mb-6">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_180px_160px_auto]">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search service name..."
            className="glass-panel rounded-xl px-4 py-3 text-sm text-white outline-none placeholder:text-gray-500 focus:border-palette-300/40"
          />
          <select value={category} onChange={(event) => setCategory(event.target.value)} className="glass-panel rounded-xl px-4 py-3 text-sm text-white outline-none">
            {categories.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
          <select value={status} onChange={(event) => setStatus(event.target.value)} className="glass-panel rounded-xl px-4 py-3 text-sm text-white outline-none">
            {statuses.map(item => <option key={item} value={item}>{item}</option>)}
          </select>
          <button onClick={() => setSelectedIds(new Set())} className="glass-panel rounded-xl px-4 py-3 text-sm font-medium text-palette-100 hover:bg-glass-100 transition-smooth">
            Clear selection
          </button>
        </div>

        <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
          {subscriptions.map(sub => (
            <button
              key={sub.id}
              onClick={() => toggleSelected(sub.id)}
              className={`shrink-0 rounded-full border px-3 py-1.5 text-xs transition-smooth ${
                selectedIds.has(sub.id)
                  ? 'border-palette-300/50 bg-palette-300/20 text-white'
                  : 'border-white/10 bg-white/5 text-gray-400 hover:text-white'
              }`}
            >
              {sub.service_name}
            </button>
          ))}
        </div>
      </ReportPanel>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.35fr_0.65fr]">
        <ReportPanel title="Spend treemap" eyebrow="Most costly visible first" className="min-h-[460px]">
          {report.sorted.length === 0 ? (
            <p className="text-gray-400">No subscriptions match current filters.</p>
          ) : (
            <div className="flex h-[380px] flex-wrap content-stretch gap-3">
              {report.sorted.map((sub, index) => {
                const annual = annualCost(sub)
                const share = report.annualTotal > 0 ? (annual / report.annualTotal) * 100 : 0
                const flexBasis = `${Math.max(18, Math.min(70, share * 2.2))}%`
                return (
                  <button
                    key={sub.id || sub.service_name}
                    onClick={() => toggleSelected(sub.id)}
                    className="group/tile relative min-h-[112px] flex-grow overflow-hidden rounded-3xl border border-white/10 p-4 text-left transition-smooth hover:-translate-y-1 hover:border-palette-300/40"
                    style={{ flexBasis, background: `linear-gradient(135deg, ${palette[index % palette.length]}33, ${palette[(index + 2) % palette.length]}14)` }}
                  >
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(255,255,255,0.18),transparent_36%)] opacity-60"></div>
                    <div className="relative z-10 flex h-full flex-col justify-between">
                      <div>
                        <p className="truncate text-lg font-bold text-white">{sub.service_name}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.18em] text-palette-100/50">{sub.category}</p>
                      </div>
                      <div>
                        <p className="text-2xl font-black text-palette-100">{formatMoney(annual, sub.currency)}</p>
                        <p className="text-xs text-gray-400">{share.toFixed(1)}% of selected annual spend</p>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </ReportPanel>

        <div className="space-y-6">
          <ReportPanel title="Category pressure" eyebrow="Annualized mix">
            <div className="space-y-4">
              {report.byCategory.map((cat, index) => {
                const width = report.annualTotal > 0 ? (cat.annual / report.annualTotal) * 100 : 0
                return (
                  <div key={cat.name}>
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="capitalize text-white">{cat.name}</span>
                      <span className="text-gray-400">{formatMoney(cat.annual, report.dominantCurrency)}</span>
                    </div>
                    <div className="h-3 overflow-hidden rounded-full bg-white/5">
                      <div className="h-full rounded-full" style={{ width: `${width}%`, background: palette[index % palette.length] }}></div>
                    </div>
                  </div>
                )
              })}
            </div>
          </ReportPanel>

          <ReportPanel title="Renewal radar" eyebrow="Known next billing">
            {upcomingRenewals.length === 0 ? (
              <p className="text-sm text-gray-400">No next billing dates captured yet.</p>
            ) : (
              <div className="space-y-3">
                {upcomingRenewals.map(sub => (
                  <div key={sub.id} className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-white">{sub.service_name}</p>
                      <p className="text-xs text-gray-500">{sub.billing_cycle}</p>
                    </div>
                    <p className="text-sm text-palette-100">{sub.renewalDate.toLocaleDateString()}</p>
                  </div>
                ))}
              </div>
            )}
          </ReportPanel>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ReportPanel title="12-month trend" eyebrow={events.length ? 'Payment events' : 'Projected recurring baseline'}>
          <div className="flex h-56 items-end gap-2 border-b border-white/10 pb-3">
            {trend.map(month => (
              <div key={month.key} className="flex flex-1 flex-col items-center gap-2">
                <div className="w-full rounded-t-xl bg-gradient-to-t from-palette-700 to-palette-300 transition-smooth hover:from-palette-600" style={{ height: `${Math.max(6, (month.value / maxTrend) * 180)}px` }}></div>
                <span className="text-[10px] text-gray-500">{month.label}</span>
              </div>
            ))}
          </div>
        </ReportPanel>

        <ReportPanel title="Billing rhythm" eyebrow="Cycle distribution">
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(report.byCycle).map(([cycle, count], index) => (
              <div key={cycle} className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <p className="text-[10px] uppercase tracking-[0.22em] text-gray-500">{cycle}</p>
                <p className="mt-2 text-4xl font-black" style={{ color: palette[index % palette.length] }}>{count}</p>
                <p className="text-xs text-gray-400">subscriptions</p>
              </div>
            ))}
          </div>
          {report.biggest && (
            <div className="mt-5 rounded-2xl bg-accent-yellow/10 p-4 text-sm text-palette-100">
              Biggest cost driver: <span className="font-bold text-white">{report.biggest.service_name}</span> at {formatMoney(annualCost(report.biggest), report.biggest.currency)} annually.
            </div>
          )}
        </ReportPanel>
      </div>
    </div>
  )
}

