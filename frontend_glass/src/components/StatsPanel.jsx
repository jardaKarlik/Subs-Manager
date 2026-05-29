export default function StatsPanel({ stats, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="glass-panel p-6 rounded-xl animate-pulse-glass">
            <div className="h-4 bg-glass-100 rounded w-20 mb-3"></div>
            <div className="h-8 bg-glass-100 rounded w-32"></div>
          </div>
        ))}
      </div>
    )
  }

  const statCards = [
    {
      label: 'Monthly Total',
      value: `$${stats.total_monthly_cost.toFixed(2)}`,
      color: 'from-blue-500 to-cyan-500',
    },
    {
      label: 'Yearly Total',
      value: `$${stats.total_yearly_cost.toFixed(2)}`,
      color: 'from-purple-500 to-pink-500',
    },
    {
      label: 'Active',
      value: stats.by_status?.active || 0,
      color: 'from-green-500 to-emerald-500',
    },
    {
      label: 'Total',
      value: stats.total_subscriptions,
      color: 'from-orange-500 to-red-500',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
      {statCards.map((stat, i) => (
        <div key={i} className="glass-panel-lg p-6 rounded-2xl hover:bg-glass-200 transition-smooth cursor-pointer group">
          <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
            {stat.label}
          </div>
          <div className={`text-3xl font-bold bg-gradient-to-r ${stat.color} bg-clip-text text-transparent`}>
            {stat.value}
          </div>
          <div className="mt-4 h-1 w-12 bg-gradient-to-r from-glass-100 to-transparent rounded-full group-hover:w-full transition-all"></div>
        </div>
      ))}
    </div>
  )
}
