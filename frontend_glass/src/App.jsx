import { useState } from 'react'
import { Suspense } from 'react'
import Header from './components/Header'
import StatsPanel from './components/StatsPanel'
import GlassSubscriptionGrid from './components/GlassSubscriptionGrid'
import ReportsPage from './components/ReportsPage'
import useSubscriptions from './hooks/useSubscriptions'

export default function App() {
  const { subscriptions, events, usingDemoData, stats, loading, error, refetch } = useSubscriptions()
  const [view, setView] = useState('dashboard')
  const [focusedSubscriptionId, setFocusedSubscriptionId] = useState(null)

  const openInsights = (subscription) => {
    setFocusedSubscriptionId(subscription?.id || null)
    setView('reports')
  }

  return (
    <div className="w-full h-screen flex flex-col bg-glass-bg overflow-hidden">
      {/* Header */}
      <Header onSync={refetch} currentView={view} onNavigate={setView} />

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-7xl mx-auto">
          {view === 'dashboard' ? (
            <>
              {/* Stats Panels */}
              <Suspense fallback={<div className="text-center py-8 text-gray-400">Loading stats...</div>}>
                <StatsPanel stats={stats} loading={loading} />
              </Suspense>

              {/* Error State */}
              {usingDemoData && (
                <div className="glass-panel p-4 mb-8 border-yellow-500/30 bg-yellow-500/10">
                  <p className="text-yellow-200">Demo mode: backend API is offline, showing local test subscriptions.</p>
                </div>
              )}

              {error && (
                <div className="glass-panel p-4 mb-8 border-red-500/30 bg-red-500/10">
                  <p className="text-red-400">Error: {error}</p>
                </div>
              )}

              {/* Glass Subscription Grid */}
              <Suspense fallback={<div className="text-center py-12 text-gray-400">Loading subscriptions...</div>}>
                <GlassSubscriptionGrid subscriptions={subscriptions} loading={loading} onOpenInsights={openInsights} />
              </Suspense>
            </>
          ) : (
            <ReportsPage
              subscriptions={subscriptions}
              events={events}
              stats={stats}
              loading={loading}
              usingDemoData={usingDemoData}
              focusedSubscriptionId={focusedSubscriptionId}
              onFocusedSubscriptionHandled={() => setFocusedSubscriptionId(null)}
            />
          )}
        </div>
      </div>
    </div>
  )
}
