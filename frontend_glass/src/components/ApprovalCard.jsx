import { useState } from 'react'
import { CheckIcon, XIcon } from 'react-feather'

const ApprovalCard = ({
  subscription,
  isSelected,
  onSelect,
  onApprove,
  onDismiss,
  loading
}) => {
  const [hovering, setHovering] = useState(false)

  const getCategoryColor = (category) => {
    const colors = {
      'dev_tools': 'from-blue-500 to-blue-600',
      'gaming': 'from-purple-500 to-purple-600',
      'music': 'from-pink-500 to-pink-600',
      'music_tools': 'from-pink-500 to-pink-600',
      'productivity': 'from-green-500 to-green-600',
      'entertainment': 'from-orange-500 to-orange-600',
      'storage': 'from-cyan-500 to-cyan-600',
      'other': 'from-gray-500 to-gray-600'
    }
    return colors[category] || colors['other']
  }

  const getCategoryIcon = (category) => {
    const icons = {
      'dev_tools': '💻',
      'gaming': '🎮',
      'music': '🎵',
      'music_tools': '🎵',
      'productivity': '📊',
      'entertainment': '🎬',
      'storage': '☁️',
      'other': '📦'
    }
    return icons[category] || icons['other']
  }

  const categoryColor = getCategoryColor(subscription.category)
  const categoryIcon = getCategoryIcon(subscription.category)

  return (
    <div
      className="group relative glass-panel rounded-xl border border-palette-300/20 bg-gradient-to-br from-palette-900/40 to-palette-800/20 overflow-hidden transition-smooth hover:border-palette-300/40 hover:shadow-lg hover:shadow-palette-800/30"
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
    >
      {/* Animated gradient background on hover */}
      <div className={`absolute inset-0 bg-gradient-to-br ${categoryColor} opacity-0 group-hover:opacity-5 transition-opacity duration-300 pointer-events-none`} />
      
      {/* Header with checkbox and icon */}
      <div className="relative p-4 border-b border-palette-300/10 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onSelect(subscription.id)}
            className="w-5 h-5 rounded cursor-pointer accent-palette-300"
          />
          <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${categoryColor} flex items-center justify-center text-lg shadow-lg`}>
            {categoryIcon}
          </div>
        </div>
        <span className="inline-block px-2 py-1 rounded-full bg-yellow-500/20 border border-yellow-500/30 text-yellow-300 text-xs font-semibold">
          Pending
        </span>
      </div>

      {/* Content */}
      <div className="relative p-4 space-y-3">
        <div>
          <h3 className="font-semibold text-palette-100 text-lg line-clamp-2">
            {subscription.service_name}
          </h3>
          <p className="text-xs text-palette-100/60 capitalize">
            {subscription.category.replace('_', ' ')}
          </p>
        </div>

        {/* Cost Display */}
        <div className="flex items-baseline gap-2 py-2 px-3 rounded-lg bg-palette-900/40 border border-palette-300/10">
          <span className="text-2xl font-bold text-accent-yellow">
            {subscription.cost.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2
            })}
          </span>
          <span className="text-sm text-palette-100/70">{subscription.currency}</span>
          <span className="text-xs text-palette-100/60 capitalize ml-auto">
            {subscription.billing_cycle}
          </span>
        </div>

        {/* Billing Info */}
        {subscription.next_billing_date && (
          <div className="text-xs text-palette-100/60">
            Next billing: <span className="text-palette-100/80 font-medium">{subscription.next_billing_date}</span>
          </div>
        )}

        {subscription.notes && (
          <div className="text-xs text-palette-100/70 italic bg-palette-900/40 p-2 rounded border border-palette-300/10">
            {subscription.notes}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="relative p-4 border-t border-palette-300/10 flex gap-2">
        <button
          onClick={() => onApprove(subscription.id)}
          disabled={loading}
          className="flex-1 py-2 px-3 rounded-lg bg-green-500/20 border border-green-500/30 hover:bg-green-500/30 text-green-400 font-medium transition-smooth disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
        >
          <CheckIcon className="w-4 h-4" />
          Approve
        </button>
        <button
          onClick={() => onDismiss(subscription.id)}
          disabled={loading}
          className="flex-1 py-2 px-3 rounded-lg bg-red-500/20 border border-red-500/30 hover:bg-red-500/30 text-red-400 font-medium transition-smooth disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
        >
          <XIcon className="w-4 h-4" />
          Dismiss
        </button>
      </div>
    </div>
  )
}

export default ApprovalCard
