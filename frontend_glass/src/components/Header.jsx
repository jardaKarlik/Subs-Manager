import { useState, useRef } from 'react'

export default function Header({ onSync, currentView = 'dashboard', onNavigate }) {
  const [syncing, setSyncing] = useState(false)
  const headerRef = useRef(null)
  const [rotation, setRotation] = useState({ x: 0, y: 0 })
  const [lightPos, setLightPos] = useState({ x: 50, y: 50 })
  const [isHovered, setIsHovered] = useState(false)

  const handleSync = async () => {
    setSyncing(true)
    try {
      await onSync()
    } finally {
      setSyncing(false)
    }
  }

  const handleMouseMove = (e) => {
    if (!headerRef.current) return
    const rect = headerRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const centerX = rect.width / 2
    const centerY = rect.height / 2
    
    // Subtle rotation for header
    setRotation({
      x: (y - centerY) / 20,
      y: (centerX - x) / 50
    })
    
    setLightPos({
      x: (x / rect.width) * 100,
      y: (y / rect.height) * 100
    })
  }

  const handleMouseLeave = () => {
    setIsHovered(false)
    setRotation({ x: 0, y: 0 })
  }

  return (
    <header 
      ref={headerRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={handleMouseLeave}
      className="sticky top-0 z-50 p-4 perspective-[1000px]"
    >
      <div 
        className="glass-panel-lg border-b backdrop-blur-xl relative overflow-hidden transition-transform duration-200 ease-out"
        style={{
          transform: isHovered 
            ? `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg) translateY(2px)` 
            : 'rotateX(0deg) rotateY(0deg) translateY(0)',
          '--light-x': `${lightPos.x}%`,
          '--light-y': `${lightPos.y}%`,
          boxShadow: isHovered ? '0 10px 30px rgba(0,0,0,0.3)' : '0 4px 10px rgba(0,0,0,0.1)'
        }}
      >
        {/* Soft glare reflection */}
        <div
          className="absolute inset-0 z-0 pointer-events-none rounded-2xl transition-opacity duration-300"
          style={{
            opacity: isHovered ? 0.6 : 0,
            background: `radial-gradient(
              800px circle at var(--light-x) var(--light-y),
              rgba(255, 255, 255, 0.08) 0%,
              transparent 40%
            )`,
            mixBlendMode: 'color-dodge',
          }}
        ></div>

        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-col gap-4 lg:flex-row lg:justify-between lg:items-center relative z-10">
          {/* Logo */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => onNavigate?.('dashboard')}
              className="flex items-center gap-3 group/logo"
              aria-label="Open dashboard"
            >
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-palette-600 to-palette-300 flex items-center justify-center shadow-lg shadow-palette-800/30 group-hover/logo:scale-105 transition-smooth">
                <span className="text-palette-900 font-bold text-lg">$</span>
              </div>
              <h1 className="text-2xl font-bold gradient-text">mySUBZ</h1>
            </button>
            <div className="hidden md:flex items-center gap-2 glass-panel px-3 py-2 rounded-full border-palette-300/20 bg-palette-300/10">
              <span className="w-2 h-2 rounded-full bg-accent-yellow shadow-[0_0_18px_rgba(255,230,0,0.8)]"></span>
              <span className="text-[11px] uppercase tracking-[0.22em] text-palette-100/80">
                Data window: last 12 months only
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="md:hidden w-full glass-panel px-3 py-2 rounded-full border-palette-300/20 bg-palette-300/10">
              <span className="text-[11px] uppercase tracking-[0.18em] text-palette-100/80">
                Data window: last 12 months only
              </span>
            </div>
            <button
              onClick={() => onNavigate?.('dashboard')}
              className={`glass-panel px-4 py-2 rounded-lg font-medium transition-smooth ${
                currentView === 'dashboard' ? 'bg-glass-200 text-white' : 'hover:bg-glass-100 text-gray-300'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => onNavigate?.('reports')}
              className={`glass-panel px-4 py-2 rounded-lg font-medium transition-smooth ${
                currentView === 'reports'
                  ? 'bg-palette-300/20 text-palette-100 border-palette-300/30 shadow-lg shadow-palette-800/20'
                  : 'hover:bg-palette-300/10 text-palette-100/80 border-palette-300/10'
              }`}
            >
              Reports
            </button>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="glass-panel px-4 py-2 rounded-lg font-medium hover:bg-glass-100 transition-smooth disabled:opacity-50"
            >
              {syncing ? '↻ Syncing...' : '↻ Sync'}
            </button>
            <button className="glass-panel px-4 py-2 rounded-lg font-medium bg-yellow-500/20 hover:bg-yellow-500/30 transition-smooth text-yellow-400 border-yellow-500/20">
              + Add
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
