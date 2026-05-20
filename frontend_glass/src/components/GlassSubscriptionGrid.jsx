import GlassCard from './GlassCard'

const categoryColors = {
  cloud: { bg: 'from-palette-800 to-palette-700', light: '#2B124C' },
  dev_tools: { bg: 'from-palette-700 to-palette-600', light: '#522B5B' },
  ai: { bg: 'from-palette-600 to-palette-300', light: '#854F6C' },
  streaming: { bg: 'from-palette-300 to-palette-100', light: '#DFB6B2' },
  music: { bg: 'from-palette-700 to-palette-300', light: '#522B5B' },
  music_tools: { bg: 'from-palette-800 to-palette-600', light: '#2B124C' },
  design: { bg: 'from-palette-600 to-palette-100', light: '#854F6C' },
  productivity: { bg: 'from-palette-300 to-palette-600', light: '#DFB6B2' },
  gaming: { bg: 'from-palette-800 to-palette-300', light: '#2B124C' },
  security: { bg: 'from-palette-700 to-palette-100', light: '#522B5B' },
  other: { bg: 'from-palette-800 to-palette-700', light: '#2B124C' },
}

export default function GlassSubscriptionGrid({ subscriptions, loading, onOpenInsights }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div key={i} className="glass-panel p-6 rounded-xl h-48 animate-pulse-glass">
            <div className="h-12 bg-glass-100 rounded-lg mb-4 w-12"></div>
            <div className="h-4 bg-glass-100 rounded w-24 mb-2"></div>
            <div className="h-3 bg-glass-100 rounded w-16"></div>
          </div>
        ))}
      </div>
    )
  }

  if (subscriptions.length === 0) {
    return (
      <div className="glass-panel-lg p-12 rounded-3xl text-center">
        <p className="text-gray-400 text-lg">No subscriptions yet. Sync your email to get started.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 pb-12">
      {subscriptions.map((sub, index) => {
        const colors = categoryColors[sub.category] || categoryColors.other
        const initials = sub.service_name.substring(0, 2).toUpperCase()

        return (
          <GlassCard
            key={sub.id || index}
            subscription={sub}
            initials={initials}
            colors={colors}
            delay={index * 0.05}
            onOpenInsights={onOpenInsights}
          />
        )
      })}
    </div>
  )
}
