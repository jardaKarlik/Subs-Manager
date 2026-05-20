# 🏗️ Architecture & Data Flow

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     SUBSCRIPTION MANAGER                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                              │
│                    frontend_glass/ (NEW)                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                    App.jsx (Root)                          │    │
│  ├─────────────────────────────────────────────────────────── ┤    │
│  │ ┌──────────────────────────────────────────────────────┐  │    │
│  │ │          Header Component                             │  │    │
│  │ │  • Logo & Navigation                                  │  │    │
│  │ │  • Sync & Add buttons                                 │  │    │
│  │ │  • Glass morphism styling                             │  │    │
│  │ └──────────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │ ┌──────────────────────────────────────────────────────┐  │    │
│  │ │          StatsPanel Component                         │  │    │
│  │ │  • Monthly Total ($)                                  │  │    │
│  │ │  • Yearly Total ($)                                   │  │    │
│  │ │  • Active Subscriptions (#)                           │  │    │
│  │ │  • Total Subscriptions (#)                            │  │    │
│  │ │  • Gradient cards with hover effects                  │  │    │
│  │ └──────────────────────────────────────────────────────┘  │    │
│  │                                                            │    │
│  │ ┌──────────────────────────────────────────────────────┐  │    │
│  │ │          GlassSubscriptionGrid Component             │  │    │
│  │ │  • Responsive layout (1-4 columns)                    │  │    │
│  │ │  • Loading states                                     │  │    │
│  │ │  • Error handling                                     │  │    │
│  │ │                                                        │  │    │
│  │ │ ┌───────────┬───────────┬───────────┬───────────┐    │  │    │
│  │ │ │ GlassCard │ GlassCard │ GlassCard │ GlassCard │    │  │    │
│  │ │ │  ┌─────┐  │  ┌─────┐  │  ┌─────┐  │  ┌─────┐ │    │  │    │
│  │ │ │  │ $ G │  │  │ * D │  │  │ AI  │  │  │ 🎵  │ │    │  │    │
│  │ │ │  │ HIB │  │  │ dev │  │  │ app │  │  │Spo  │ │    │  │    │
│  │ │ │  └─────┘  │  └─────┘  │  └─────┘  │  └─────┘ │    │  │    │
│  │ │ │ Glass... │ │ GitHub.. │ │ ChatGPT │ │Spotify │    │  │    │
│  │ │ │ $9.99/mo │ │$21/year  │ │$20/mo   │ │$0/mo   │    │  │    │
│  │ │ │ [active] │ │[active]  │ │[active] │ │[idle]  │    │  │    │
│  │ │ └─────────┘ └─────────┘ └─────────┘ └─────────┘    │  │    │
│  │ └──────────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ useSubscriptions Hook (State Management)                   │   │
│  │ • Fetches subscription data                                │   │
│  │ • Manages loading/error states                             │   │
│  │ • Calculates stats (monthly/yearly)                        │   │
│  │ • Handles email sync trigger                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Tech Stack: React 18 + Tailwind CSS + Three.js (optional)         │
└──────────────────────────────────────────────────────────────────────┘
                             ↕️ API Proxy
                         (vite.config.js)
┌──────────────────────────────────────────────────────────────────────┐
│                      BACKEND (Python)                                │
│                        api.py (FastAPI)                              │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                 HTTP Endpoints                             │    │
│  │                                                            │    │
│  │  GET  /api/subscriptions?page_size=100                    │    │
│  │  POST /api/sync-emails                                    │    │
│  │  GET  /api/stats                                          │    │
│  │  GET  /api/categories                                     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             ↕️
│  ┌────────────────────────────────────────────────────────────┐    │
│  │              Email Fetcher Service                         │    │
│  │  • Gmail (Composio OAuth)                                 │    │
│  │  • Outlook (Composio OAuth)                               │    │
│  │  • IMAP (Zoner mailbox)                                   │    │
│  │  • Email Classifier                                       │    │
│  └────────────────────────────────────────────────────────────┘    │
│                             ↕️
│  ┌────────────────────────────────────────────────────────────┐    │
│  │              Database (SQLAlchemy ORM)                     │    │
│  │  • Subscription (service_name, cost, category, status)    │    │
│  │  • ProcessedEmail (source, subject, sender, body)         │    │
│  │  • SubscriptionEvent (date, event_type, service_name)     │    │
│  └────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                             ↕️
┌──────────────────────────────────────────────────────────────────────┐
│                   External Services                                  │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │    Gmail     │  │   Outlook    │  │ IMAP/Zoner   │              │
│  │  (Composio)  │  │  (Composio)  │  │   (Native)   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Component Hierarchy

```
App
│
├── Header
│   ├── Logo
│   ├── Sync Button
│   └── Add Button
│
├── StatsPanel
│   ├── StatCard (Monthly)
│   ├── StatCard (Yearly)
│   ├── StatCard (Active)
│   └── StatCard (Total)
│
└── GlassSubscriptionGrid
    ├── Loading State
    ├── Error State
    ├── Empty State
    └── GlassCard (× N)
        ├── Icon (category color)
        ├── Service Name
        ├── Category Label
        ├── Cost & Currency
        ├── Billing Cycle
        ├── Status Badge
        ├── Next Billing Date
        └── Interactive Effects
            ├── Hover Parallax
            ├── Glow Effect
            ├── Shine Animation
            └── Scale & Elevation
```

---

## Data Flow Diagram

```
User Opens App
    ↓
React Mounts App Component
    ↓
useSubscriptions Hook Called
    ├─→ setLoading(true)
    ├─→ fetch("/api/subscriptions?page_size=100")
    │   ↓
    │   Backend Queries Database
    │   ↓
    │   Returns Paginated Data
    ├─→ Parse Response
    ├─→ Calculate Stats
    │   ├─→ Sum monthly costs
    │   ├─→ Calculate yearly (monthly × 12)
    │   ├─→ Count by category
    │   └─→ Count by status
    ├─→ setSubscriptions(data.items)
    ├─→ setStats(calculated_stats)
    └─→ setLoading(false)
    ↓
Components Re-render with Data
    ├─→ StatsPanel displays: $145.50/mo, $1,746/yr
    ├─→ GlassSubscriptionGrid displays cards
    └─→ GlassCard renders each subscription
    ↓
User Hovers Over Card
    ├─→ Mouse event tracked
    ├─→ Calculate parallax offset
    ├─→ Update card transform
    └─→ Render glow effect
    ↓
User Clicks Sync Button
    ├─→ post("/api/sync-emails", {sources: [...]})
    │   ↓
    │   Backend Fetches Emails
    │   ├─→ Fetch from Gmail
    │   ├─→ Fetch from Outlook
    │   ├─→ Fetch from IMAP
    │   ↓
    │   Classify Emails
    │   ↓
    │   Extract Subscriptions
    │   ↓
    │   Store in Database
    ├─→ Call refetch() to reload
    └─→ Display new data
```

---

## State Management

```
useSubscriptions Hook (Custom Hook)

State Variables:
├── subscriptions: Array<Subscription>
│   └── Each: { id, service_name, cost, category, status, ... }
├── stats: Object
│   ├── total_subscriptions: number
│   ├── total_monthly_cost: number
│   ├── total_yearly_cost: number
│   ├── by_category: { [key]: count }
│   └── by_status: { [key]: count }
├── loading: boolean
└── error: string | null

Functions:
├── fetchSubscriptions() → void
│   └── Fetches from /api/subscriptions
├── syncEmails() → void
│   └── Posts to /api/sync-emails
└── refetch() → void
    └── Re-runs fetchSubscriptions()

Effects:
└── useEffect(() => { fetchSubscriptions() }, [])
    └── Runs on component mount
```

---

## File Organization

```
frontend_glass/
│
├── src/
│   ├── components/              ← React Components
│   │   ├── Header.jsx
│   │   ├── StatsPanel.jsx
│   │   ├── GlassCard.jsx
│   │   ├── GlassSubscriptionGrid.jsx
│   │   └── GlassScene.jsx       ← 3D Effects (optional)
│   │
│   ├── hooks/                   ← Custom Hooks
│   │   └── useSubscriptions.js
│   │
│   ├── App.jsx                  ← Root Component
│   ├── main.jsx                 ← React Entry
│   └── index.css                ← Global Styles
│
├── index.html                   ← HTML Template
├── vite.config.js               ← Build Config & API Proxy
├── tailwind.config.js           ← Design Tokens
├── tsconfig.json                ← TypeScript Config
├── package.json                 ← Dependencies
├── postcss.config.js            ← CSS Processing
└── README.md                    ← Documentation
```

---

## API Contract

### Request/Response Cycle

```
Frontend Request:
  GET /api/subscriptions?page_size=100

Backend Response:
{
  "items": [
    {
      "id": 1,
      "service_name": "GitHub Pro",
      "category": "dev_tools",
      "cost": 21.0,
      "currency": "USD",
      "billing_cycle": "yearly",
      "status": "active",
      "start_date": "2026-01-15T00:00:00",
      "next_billing_date": "2027-01-15T00:00:00",
      "icon_url": null,
      "notes": "Professional development",
      "created_at": "2026-01-15T10:30:00",
      "updated_at": "2026-05-15T14:22:00"
    },
    ...more items...
  ],
  "total": 42,
  "page": 1,
  "page_size": 100,
  "pages": 1
}

Frontend Processing:
├─→ Validate response (check status, data shape)
├─→ Extract items array
├─→ Calculate totals
├─→ Group by category
├─→ Format currency/dates
└─→ Update state & render
```

---

## Performance Considerations

```
Optimization Strategies:
├── Code Splitting
│   └─ Components lazy-loaded with React.Suspense
├── Memoization
│   ├─ useCallback for event handlers
│   └─ React.memo for expensive renders
├── Animation Performance
│   ├─ CSS transforms (translateY, scale)
│   ├─ GPU acceleration
│   └─ Will-change hints
├── Bundling
│   ├─ Vite tree-shaking
│   ├─ Tailwind purging
│   └─ Minification
└── Caching
    ├─ Browser cache for static assets
    ├─ API response caching (optional)
    └─ Image lazy-loading (CSS gradients used instead)
```

---

## Deployment Architecture

```
Development:
  localhost:5173 (Frontend)
       ↓
       ↕️ CORS + API Proxy
       ↓
  localhost:8000 (Backend)

Production (Option 1 - Monolithic):
  API Server (port 8000)
  ├─ /api/* → Backend endpoints
  └─ /* → Serve frontend_glass_dist/

Production (Option 2 - Separate):
  CDN / Static Host (frontend_glass_dist/)
       ↓
       ↕️ CORS
       ↓
  API Server (production domain)
```

---

## Technologies & Versions

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| UI Framework | React | 18.2.0 | Component rendering |
| Build Tool | Vite | 5.0.0 | Dev server & bundler |
| Styling | Tailwind CSS | 3.3.0 | Utility-first CSS |
| 3D Graphics | Three.js | r183 | WebGL rendering |
| React 3D Bridge | @react-three/fiber | 8.16.0 | React for Three.js |
| 3D Utilities | @react-three/drei | 9.92.0 | Helper components |
| Effects | @react-three/postprocessing | 2.15.0 | Bloom, etc |
| Animation | Framer Motion | 10.16.0 | Spring animations |
| State | Zustand | 4.4.0 | Optional store |
| Language | JavaScript | ES2020 | Modern syntax |

---

## Browser Rendering Pipeline

```
1. Network Request
   └─→ Load HTML, CSS, JS bundles

2. Parse
   ├─→ Parse HTML
   ├─→ Parse CSS → CSSOM
   └─→ Parse JS → AST

3. Compile
   └─→ JavaScript JIT compilation

4. Render
   ├─→ React reconciliation (VDOM)
   ├─→ Layout calculation
   └─→ Paint (rasterization)

5. Composite
   ├─→ GPU composite layers
   ├─→ 3D transforms (GPU)
   └─→ Display on screen

6. Animation Loop
   ├─→ requestAnimationFrame
   ├─→ Update transforms (GPU)
   ├─→ 60fps (16.67ms per frame)
   └─→ Mouse/scroll events
```

---

**Last Updated**: May 15, 2026  
**Branch**: `feature/glass-design-upgrade`
