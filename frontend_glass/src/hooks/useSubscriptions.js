import { useState, useCallback, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const demoSubscriptions = [
  { id: 1, service_name: 'AWS', category: 'cloud', cost: 127.45, currency: 'USD', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-06-02', notes: 'Plan: Pay-as-you-go', icon_url: 'https://logo.clearbit.com/aws.amazon.com', source: 'demo' },
  { id: 2, service_name: 'Adobe Creative Cloud', category: 'design', cost: 52.99, currency: 'USD', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-06-12', notes: 'Plan: All Apps', icon_url: 'https://logo.clearbit.com/adobe.com', source: 'demo' },
  { id: 3, service_name: 'Wix', category: 'productivity', cost: 484.17, currency: 'CZK', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-05-29', icon_url: 'https://logo.clearbit.com/wix.com', source: 'demo' },
  { id: 4, service_name: 'Google Cloud', category: 'cloud', cost: 280, currency: 'CZK', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-06-08', icon_url: 'https://logo.clearbit.com/google.com', source: 'demo' },
  { id: 5, service_name: 'Spotify', category: 'music', cost: 150, currency: 'CZK', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-06-01', icon_url: 'https://logo.clearbit.com/spotify.com', source: 'demo' },
  { id: 6, service_name: 'Netflix', category: 'streaming', cost: 136, currency: 'CZK', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-06-04', icon_url: 'https://logo.clearbit.com/netflix.com', source: 'demo' },
  { id: 7, service_name: 'GitHub Pro', category: 'dev_tools', cost: 4, currency: 'USD', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-06-15', icon_url: 'https://logo.clearbit.com/github.com', source: 'demo' },
  { id: 8, service_name: 'ChatGPT Plus', category: 'ai', cost: 20, currency: 'USD', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-05-25', icon_url: 'https://logo.clearbit.com/openai.com', source: 'demo' },
  { id: 9, service_name: 'JetBrains Toolbox', category: 'dev_tools', cost: 173, currency: 'USD', billing_cycle: 'yearly', status: 'active', next_billing_date: '2026-09-11', icon_url: 'https://logo.clearbit.com/jetbrains.com', source: 'demo' },
  { id: 10, service_name: 'Beatport', category: 'music_tools', cost: 200, currency: 'CZK', billing_cycle: 'monthly', status: 'idle', next_billing_date: '2026-06-20', icon_url: 'https://logo.clearbit.com/beatport.com', source: 'demo' },
  { id: 11, service_name: 'Cline', category: 'ai', cost: 8.75, currency: 'USD', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-05-27', icon_url: 'https://logo.clearbit.com/clineai.com', source: 'demo' },
  { id: 12, service_name: 'Native Instruments', category: 'music_tools', cost: 76, currency: 'CZK', billing_cycle: 'monthly', status: 'active', next_billing_date: '2026-06-17', icon_url: 'https://logo.clearbit.com/native-instruments.com', source: 'demo' },
]

function monthlyCost(subscription) {
  const cost = Number(subscription.cost || 0)
  if (subscription.billing_cycle === 'yearly') return cost / 12
  if (subscription.billing_cycle === 'weekly') return (cost * 52) / 12
  if (subscription.billing_cycle === 'daily') return cost * 30
  if (subscription.billing_cycle === 'one-time') return 0
  return cost
}

function buildDemoEvents(subscriptions) {
  const now = new Date()
  return subscriptions.flatMap((subscription) => {
    const base = monthlyCost(subscription)
    if (!base) return []
    return Array.from({ length: 12 }, (_, index) => {
      const date = new Date(now.getFullYear(), now.getMonth() - (11 - index), 6 + (subscription.id % 18))
      const seasonal = 0.86 + ((index + subscription.id) % 5) * 0.07
      return {
        id: Number(`${subscription.id}${index}`),
        subscription_id: subscription.id,
        service_name: subscription.service_name,
        category: subscription.category,
        amount: Number((base * seasonal).toFixed(2)),
        currency: subscription.currency,
        billing_cycle: subscription.billing_cycle,
        event_date: date.toISOString(),
        source_type: 'demo',
      }
    })
  })
}

function buildStats(items) {
  const monthlyTotal = items.reduce((sum, subscription) => sum + monthlyCost(subscription), 0)
  return {
    total_subscriptions: items.length,
    total_monthly_cost: monthlyTotal,
    total_yearly_cost: monthlyTotal * 12,
    by_category: items.reduce((acc, subscription) => {
      acc[subscription.category] = (acc[subscription.category] || 0) + 1
      return acc
    }, {}),
    by_status: items.reduce((acc, subscription) => {
      acc[subscription.status] = (acc[subscription.status] || 0) + 1
      return acc
    }, {}),
  }
}

export default function useSubscriptions() {
  const [subscriptions, setSubscriptions] = useState([])
  const [events, setEvents] = useState([])
  const [usingDemoData, setUsingDemoData] = useState(false)
  const [stats, setStats] = useState({
    total_subscriptions: 0,
    total_monthly_cost: 0,
    total_yearly_cost: 0,
    by_category: {},
    by_status: {},
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchSubscriptions = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [response, eventsResponse] = await Promise.all([
        fetch(`${API_BASE}/subscriptions?page_size=100`),
        fetch(`${API_BASE}/events?months=12`),
      ])
      if (!response.ok) throw new Error('Failed to fetch subscriptions')
      
      const data = await response.json()
      setSubscriptions(data.items || [])

      if (eventsResponse.ok) {
        const eventData = await eventsResponse.json()
        setEvents(eventData.events || [])
      } else {
        setEvents([])
      }

      setUsingDemoData(false)
      setStats(buildStats(data.items || []))
    } catch (err) {
      console.warn('API unavailable, using local demo subscriptions:', err)
      setSubscriptions(demoSubscriptions)
      setEvents(buildDemoEvents(demoSubscriptions))
      setStats(buildStats(demoSubscriptions))
      setUsingDemoData(true)
      setError(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const syncEmails = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/sync-emails`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sources: ['gmail', 'outlook', 'imap'],
          max_results: 100,
          since_days: 3,
        })
      })
      if (!response.ok) throw new Error('Sync failed')
      await fetchSubscriptions()
    } catch (err) {
      console.error('Sync error:', err)
      setError(err.message)
    }
  }, [fetchSubscriptions])

  // Fetch on mount
  useEffect(() => {
    fetchSubscriptions()
  }, [fetchSubscriptions])

  return {
    subscriptions,
    events,
    usingDemoData,
    stats,
    loading,
    error,
    refetch: fetchSubscriptions,
    syncEmails,
  }
}
