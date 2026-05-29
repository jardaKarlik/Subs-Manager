import { useState, useEffect } from 'react'
import { CheckCircleIcon, ExclamationIcon, CheckIcon, XIcon } from 'react-feather'
import ApprovalCard from './ApprovalCard'

export default function ApprovalPage({ subscriptions = [], loading = false, usingDemoData = false, onPendingUpdated = () => {} }) {
  const [pendingSubscriptions, setPendingSubscriptions] = useState([])
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [actionLoading, setActionLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const [messageType, setMessageType] = useState(null)
  const [sortBy, setSortBy] = useState('cost-desc')

  // Filter and sort pending subscriptions
  useEffect(() => {
    let filtered = subscriptions.filter(sub => sub.approval_status === 'pending')
    
    switch(sortBy) {
      case 'cost-asc':
        filtered.sort((a, b) => a.cost - b.cost)
        break
      case 'cost-desc':
        filtered.sort((a, b) => b.cost - a.cost)
        break
      case 'name-asc':
        filtered.sort((a, b) => a.service_name.localeCompare(b.service_name))
        break
      case 'name-desc':
        filtered.sort((a, b) => b.service_name.localeCompare(a.service_name))
        break
      default:
        filtered.sort((a, b) => b.cost - a.cost)
    }
    
    setPendingSubscriptions(filtered)
  }, [subscriptions, sortBy])

  const showMessage = (text, type = 'success') => {
    setMessage(text)
    setMessageType(type)
    setTimeout(() => {
      setMessage(null)
      setMessageType(null)
    }, 4000)
  }

  const handleApprove = async (id) => {
    setActionLoading(true)
    try {
      const response = await fetch(`/api/subscriptions/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (!response.ok) throw new Error('Failed to approve')
      
      setPendingSubscriptions(prev => prev.filter(s => s.id !== id))
      selectedIds.delete(id)
      setSelectedIds(new Set(selectedIds))
      showMessage('Subscription approved ✓', 'success')
      onPendingUpdated?.()
    } catch (error) {
      showMessage(error.message || 'Failed to approve', 'error')
    } finally {
      setActionLoading(false)
    }
  }

  const handleDismiss = async (id) => {
    setActionLoading(true)
    try {
      const response = await fetch(`/api/subscriptions/${id}/dismiss`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      
      if (!response.ok) throw new Error('Failed to dismiss')
      
      setPendingSubscriptions(prev => prev.filter(s => s.id !== id))
      selectedIds.delete(id)
      setSelectedIds(new Set(selectedIds))
      showMessage('Subscription dismissed ✓', 'success')
      onPendingUpdated?.()
    } catch (error) {
      showMessage(error.message || 'Failed to dismiss', 'error')
    } finally {
      setActionLoading(false)
    }
  }

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedIds(new Set(pendingSubscriptions.map(s => s.id)))
    } else {
      setSelectedIds(new Set())
    }
  }

  const handleSelectOne = (id) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const handleBulkApprove = async () => {
    if (selectedIds.size === 0) return
    
    setActionLoading(true)
    try {
      const response = await fetch('/api/subscriptions/bulk-approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(selectedIds) })
      })
      
      if (!response.ok) throw new Error('Failed to approve selected items')
      
      const count = selectedIds.size
      setPendingSubscriptions(prev => prev.filter(s => !selectedIds.has(s.id)))
      setSelectedIds(new Set())
      showMessage(`${count} subscriptions approved ✓`, 'success')
      onPendingUpdated?.()
    } catch (error) {
      showMessage(error.message || 'Failed to approve selected items', 'error')
    } finally {
      setActionLoading(false)
    }
  }

  const handleBulkDismiss = async () => {
    if (selectedIds.size === 0) return
    
    setActionLoading(true)
    try {
      const response = await fetch('/api/subscriptions/bulk-dismiss', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(selectedIds) })
      })
      
      if (!response.ok) throw new Error('Failed to dismiss selected items')
      
      const count = selectedIds.size
      setPendingSubscriptions(prev => prev.filter(s => !selectedIds.has(s.id)))
      setSelectedIds(new Set())
      showMessage(`${count} subscriptions dismissed ✓`, 'success')
      onPendingUpdated?.()
    } catch (error) {
      showMessage(error.message || 'Failed to dismiss selected items', 'error')
    } finally {
      setActionLoading(false)
    }
  }

  const totalPendingCost = pendingSubscriptions.reduce((sum, sub) => sum + (sub.cost || 0), 0)
  const allSelected = pendingSubscriptions.length > 0 && selectedIds.size === pendingSubscriptions.length

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin">
          <ExclamationIcon className="w-12 h-12 text-palette-300" />
        </div>
        <p className="text-gray-400 mt-4">Loading pending approvals...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="glass-panel-lg p-6 rounded-2xl border border-palette-300/20 bg-gradient-to-br from-palette-900/40 to-palette-800/20">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold gradient-text mb-2">Approval Workflow</h1>
            <p className="text-palette-100/70 text-sm">
              {pendingSubscriptions.length} pending {pendingSubscriptions.length === 1 ? 'subscription' : 'subscriptions'} awaiting your review
            </p>
          </div>
          {pendingSubscriptions.length > 0 && (
            <div className="glass-panel px-4 py-3 rounded-lg border border-palette-300/20 bg-palette-300/10">
              <p className="text-sm text-palette-100/70">Total pending cost</p>
              <p className="text-2xl font-bold text-accent-yellow">
                {totalPendingCost.toLocaleString('en-US', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2
                })}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Demo Data Warning */}
      {usingDemoData && (
        <div className="glass-panel p-4 rounded-lg border-yellow-500/30 bg-yellow-500/10">
          <p className="text-yellow-200 text-sm">
            Demo mode: No pending subscriptions in demo data. In production, subscriptions from wallet_discovery will appear here.
          </p>
        </div>
      )}

      {/* Message Alerts */}
      {message && (
        <div className={`glass-panel p-4 rounded-lg border ${
          messageType === 'success' 
            ? 'border-green-500/30 bg-green-500/10 text-green-200' 
            : 'border-red-500/30 bg-red-500/10 text-red-200'
        }`}>
          <div className="flex items-center gap-2">
            {messageType === 'success' ? (
              <CheckCircleIcon className="w-5 h-5" />
            ) : (
              <ExclamationIcon className="w-5 h-5" />
            )}
            <p className="text-sm">{message}</p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {pendingSubscriptions.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl border border-palette-300/20 bg-gradient-to-br from-palette-900/40 to-palette-800/20 text-center">
          <div className="mb-4">
            <CheckCircleIcon className="w-16 h-16 text-green-400 mx-auto opacity-50" />
          </div>
          <h3 className="text-xl font-semibold text-palette-100 mb-2">All caught up!</h3>
          <p className="text-palette-100/70">No pending subscriptions to review at the moment.</p>
        </div>
      ) : (
        <>
          {/* Controls */}
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={handleSelectAll}
                className="w-5 h-5 rounded cursor-pointer accent-palette-300"
              />
              <span className="text-sm text-palette-100/70">
                {selectedIds.size > 0 ? `${selectedIds.size} selected` : 'Select all'}
              </span>
            </div>

            <div className="flex gap-2 items-center">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="glass-panel px-3 py-2 rounded-lg bg-palette-900/40 border border-palette-300/20 text-palette-100 text-sm cursor-pointer hover:border-palette-300/40 transition-smooth"
              >
                <option value="cost-desc">Cost (High to Low)</option>
                <option value="cost-asc">Cost (Low to High)</option>
                <option value="name-asc">Name (A-Z)</option>
                <option value="name-desc">Name (Z-A)</option>
              </select>
            </div>

            {selectedIds.size > 0 && (
              <div className="flex gap-2 w-full sm:w-auto">
                <button
                  onClick={handleBulkApprove}
                  disabled={actionLoading}
                  className="flex-1 sm:flex-none glass-panel px-4 py-2 rounded-lg bg-green-500/20 border border-green-500/30 hover:bg-green-500/30 text-green-400 font-medium transition-smooth disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <CheckIcon className="w-4 h-4" />
                  Approve ({selectedIds.size})
                </button>
                <button
                  onClick={handleBulkDismiss}
                  disabled={actionLoading}
                  className="flex-1 sm:flex-none glass-panel px-4 py-2 rounded-lg bg-red-500/20 border border-red-500/30 hover:bg-red-500/30 text-red-400 font-medium transition-smooth disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  <XIcon className="w-4 h-4" />
                  Dismiss ({selectedIds.size})
                </button>
              </div>
            )}
          </div>

          {/* Subscription Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pendingSubscriptions.map((sub) => (
              <ApprovalCard
                key={sub.id}
                subscription={sub}
                isSelected={selectedIds.has(sub.id)}
                onSelect={handleSelectOne}
                onApprove={handleApprove}
                onDismiss={handleDismiss}
                loading={actionLoading}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
