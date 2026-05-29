import { useState, useRef } from 'react'

const currencySymbols = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  CZK: 'Kč',
}

// Map of service names to Clearbit logo URLs
const clearbitLogos = {
  'AWS': 'https://logo.clearbit.com/aws.amazon.com',
  'Adobe Creative Cloud': 'https://logo.clearbit.com/adobe.com',
  'Wix': 'https://logo.clearbit.com/wix.com',
  'Google Cloud': 'https://logo.clearbit.com/google.com',
  'Spotify': 'https://logo.clearbit.com/spotify.com',
  'Netflix': 'https://logo.clearbit.com/netflix.com',
  'GitHub Pro': 'https://logo.clearbit.com/github.com',
  'ChatGPT Plus': 'https://logo.clearbit.com/openai.com',
  'JetBrains Toolbox': 'https://logo.clearbit.com/jetbrains.com',
  'Beatport': 'https://logo.clearbit.com/beatport.com',
  'Cline': 'https://logo.clearbit.com/clineai.com',
  'Native Instruments': 'https://logo.clearbit.com/native-instruments.com',
}

function formatMoney(amount, currencyCode) {
  const symbol = currencySymbols[currencyCode] || currencyCode || '$'
  const value = Number(amount || 0)
  if (symbol === 'Kč') return `${value.toFixed(0)} ${symbol}`
  return `${symbol}${value.toFixed(2)}`
}

function annualizedCost(subscription) {
  const cost = Number(subscription.cost || 0)
  switch (subscription.billing_cycle) {
    case 'yearly':
      return cost
    case 'weekly':
      return cost * 52
    case 'daily':
      return cost * 365
    case 'one-time':
      return cost
    case 'monthly':
    default:
      return cost * 12
  }
}

function daysUntilBilling(nextBillingDate) {
  if (!nextBillingDate) return null
  const nextDate = new Date(nextBillingDate)
  if (isNaN(nextDate.getTime())) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  nextDate.setHours(0, 0, 0, 0)
  const diff = nextDate - today
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

function getBillingProgress(daysLeft, billingCycle) {
  if (!daysLeft || daysLeft < 0) return 0
  const cycleDays = {
    daily: 1,
    weekly: 7,
    monthly: 30,
    yearly: 365,
    'one-time': 365,
  }
  const totalDays = cycleDays[billingCycle] || 30
  const progress = Math.max(0, Math.min(100, ((totalDays - daysLeft) / totalDays) * 100))
  return Math.round(progress)
}

function isExpiringSoon(daysLeft) {
  return daysLeft !== null && daysLeft > 0 && daysLeft <= 7
}

function isExpired(daysLeft) {
  return daysLeft !== null && daysLeft <= 0
}

export default function GlassCard({ subscription, initials, colors, delay, onOpenInsights }) {
  const [logoFailed, setLogoFailed] = useState(false)
  const [isHovered, setIsHovered] = useState(false)
  const cardRef = useRef(null)
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })
  const [cardRotation, setCardRotation] = useState({ x: 0, y: 0 })
  const [lightPos, setLightPos] = useState({ x: 50, y: 50 })

  const daysLeft = daysUntilBilling(subscription.next_billing_date)
  const progress = getBillingProgress(daysLeft, subscription.billing_cycle)
  const expiringSoon = isExpiringSoon(daysLeft)
  const expired = isExpired(daysLeft)

  const handleMouseMove = (e) => {
    if (!cardRef.current) return
    const rect = cardRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    setMousePos({ x, y })
    const centerX = rect.width / 2
    const centerY = rect.height / 2
    const rotateX = (y - centerY) / 4
    const rotateY = (centerX - x) / 4
    setCardRotation({ x: rotateX, y: rotateY })
    setLightPos({
      x: (x / rect.width) * 100,
      y: (y / rect.height) * 100,
    })
  }

  const handleMouseEnter = () => setIsHovered(true)
  const handleMouseLeave = () => {
    setIsHovered(false)
    setCardRotation({ x: 0, y: 0 })
    setLightPos({ x: 50, y: 50 })
  }

  const cost = formatMoney(subscription.cost, subscription.currency)
  const annualTotal = formatMoney(annualizedCost(subscription), subscription.currency)

  const statusColors = {
    active: 'text-green-400 bg-green-500/10',
    idle: 'text-orange-400 bg-orange-500/10',
    cancelled: 'text-gray-400 bg-gray-500/10',
  }

  const getIconUrl = () => {
    let iconUrl = null
    if (subscription.icon_url) {
      if (typeof subscription.icon_url === 'string' && subscription.icon_url.trim() !== '') {
        iconUrl = subscription.icon_url
      } else if (typeof subscription.icon_url === 'object') {
        if (typeof subscription.icon_url.url === 'string' && subscription.icon_url.url.trim() !== '') {
          iconUrl = subscription.icon_url.url
        } else if (typeof subscription.icon_url.src === 'string' && subscription.icon_url.src.trim() !== '') {
          iconUrl = subscription.icon_url.src
        }
      }
    }
    if (!iconUrl && clearbitLogos[subscription.service_name]) {
      iconUrl = clearbitLogos[subscription.service_name]
    }
    return iconUrl
  }

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      style={{
        '--mouse-x': `${mousePos.x}px`,
        '--mouse-y': `${mousePos.y}px`,
        '--delay': `${delay}s`,
        animation: `slideUp 0.6s ease-out ${delay}s both`,
      }}
      className="group relative h-full"
    >
      {isHovered && (
        <div
          style={{
            left: 'var(--mouse-x)',
            top: 'var(--mouse-y)',
          }}
          className="absolute w-32 h-32 bg-white/5 rounded-full blur-2xl pointer-events-none -translate-x-1/2 -translate-y-1/2 transition-opacity"
        ></div>
      )}

      <div
        className={`relative h-full glass-panel-lg rounded-2xl p-6 transition-smooth cursor-pointer overflow-hidden border ${
          isHovered
            ? 'bg-white/12 border-white/20 shadow-2xl'
            : 'border-white/10 hover:border-white/15'
        }`}
        style={{
          transform: `perspective(1000px) rotateX(${cardRotation.x}deg) rotateY(${cardRotation.y}deg) translateZ(${isHovered ? 20 : 0}px) scale(${isHovered ? 1.05 : 1})`,
          boxShadow: isHovered
            ? `0 30px 80px rgba(10,12,14,0.6), 0 8px 30px rgba(0,0,0,0.6), inset 0 1px 1px rgba(255, 255, 255, 0.12)`
            : 'none',
          '--light-x': `${lightPos.x}%`,
          '--light-y': `${lightPos.y}%`,
        }}
      >
        <div
          className="absolute inset-0 z-20 pointer-events-none rounded-2xl transition-opacity duration-300"
          style={{
            opacity: isHovered ? 1 : 0,
            background: `radial-gradient(
              600px circle at var(--light-x) var(--light-y),
              rgba(255, 255, 255, 0.1) 0%,
              transparent 40%
            )`,
            mixBlendMode: 'color-dodge',
          }}
        ></div>

        <div className={`absolute inset-0 opacity-0 group-hover:opacity-5 bg-gradient-to-br ${colors.bg} transition-opacity pointer-events-none rounded-2xl`}></div>

        <div className="relative z-10 flex h-full flex-col">
          <div className="absolute right-0 top-0 flex flex-col items-end gap-2 p-4">
            {expiringSoon && !expired && (
              <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-amber-500/20 border border-amber-500/40">
                <span className="text-amber-400 text-xs font-medium">⚠ Renews in {daysLeft}d</span>
              </div>
            )}
            {expired && (
              <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-red-500/20 border border-red-500/40">
                <span className="text-red-400 text-xs font-medium">🔴 Expired</span>
              </div>
            )}
            <div className="text-right">
              <p className="text-[10px] uppercase tracking-[0.18em] text-gray-500">Annual</p>
              <p className="text-sm font-semibold text-palette-100">{annualTotal}</p>
            </div>
          </div>

          {(() => {
            const rawIcon = subscription.icon_url;
            const iconUrl = (() => {
              if (!rawIcon) return null;
              if (typeof rawIcon === 'string' && rawIcon.trim() !== '') return rawIcon;
              if (rawIcon && typeof rawIcon === 'object') {
                if (typeof rawIcon.url === 'string' && rawIcon.url.trim() !== '') return rawIcon.url;
                if (typeof rawIcon.src === 'string' && rawIcon.src.trim() !== '') return rawIcon.src;
              }
              return null;
            })();

            return (
              <div className="w-14 h-14 rounded-xl bg-white/10 flex items-center justify-center mb-4 shadow-lg group-hover:shadow-xl transition-all overflow-hidden">
                {iconUrl && !logoFailed ? (
                  <img
                    src={iconUrl}
                    alt={subscription.service_name}
                    className="w-10 h-10 object-contain"
                    loading="lazy"
                    onError={() => setLogoFailed(true)}
                  />
                ) : (
                  <div
                    className={`w-full h-full bg-gradient-to-br ${colors.bg} flex items-center justify-center font-bold text-lg text-white`}
                  >
                    {initials}
                  </div>
                )}
              </div>
            );
          })()}
          </div>

          <h3 className="text-lg font-semibold text-white mb-1 truncate">
            {subscription.service_name}
          </h3>
          <p className="text-xs uppercase tracking-wider text-gray-400 mb-4">
            {subscription.category}
          </p>

          <div className="mb-6">
            <div className={`text-3xl font-bold bg-gradient-to-r ${colors.bg} bg-clip-text text-transparent`}>
              {cost}
            </div>
            <p className="text-xs text-gray-500 mt-1">per {subscription.billing_cycle}</p>
          </div>

          {daysLeft !== null && !expired && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400">Billing cycle progress</span>
                <span className="text-xs font-semibold text-gray-300">{progress}%</span>
              </div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 rounded-full ${
                    expiringSoon
                      ? 'bg-gradient-to-r from-amber-500 to-orange-500'
                      : `bg-gradient-to-r ${colors.bg}`
                  }`}
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          )}

          <div className="flex-1"></div>

          <div className="flex items-center justify-between pt-4 border-t border-white/5">
            <span className="text-xs text-gray-400 capitalize">
              {subscription.billing_cycle}
            </span>
            <span className={`text-xs font-medium px-2 py-1 rounded-md ${statusColors[subscription.status] || statusColors.active}`}>
              {subscription.status}
            </span>
          </div>

          {daysLeft !== null && (
            <div className="mt-3 flex items-center justify-between text-xs">
              <span className="text-gray-500">
                {expired ? (
                  <span className="text-red-400">Expired</span>
                ) : daysLeft === 0 ? (
                  <span className="text-yellow-400">Renews today</span>
                ) : daysLeft === 1 ? (
                  <span className="text-yellow-400">Renews tomorrow</span>
                ) : daysLeft <= 7 ? (
                  <span className="text-amber-400">Renews in {daysLeft} day{daysLeft !== 1 ? 's' : ''}</span>
                ) : (
                  <span className="text-gray-400">Renews in {daysLeft} days</span>
                )}
              </span>
            </div>
          )}

          <div className="mt-4 flex gap-2 justify-end">
            <button
              type="button"
              className="inline-flex items-center justify-center w-8 h-8 rounded-full border border-white/20 bg-white/5 text-white/60 hover:text-white hover:bg-white/10 transition-smooth text-sm"
              title="Pause subscription"
            >
              ⏸
            </button>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation()
                onOpenInsights?.(subscription)
              }}
              className="group/insight inline-flex items-center gap-2 rounded-full border border-palette-300/20 bg-palette-300/10 px-3 py-1.5 text-xs font-medium text-palette-100 transition-smooth hover:border-palette-300/40 hover:bg-palette-300/20"
            >
              Insights
              <span className="transition-transform group-hover/insight:translate-x-0.5">→</span>
            </button>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(24px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  )
}
