# Glass Design Frontend - Integration Guide

## Overview

This is a **standalone React + Three.js frontend** for the subscription manager, featuring:
- **Glass morphism design system** with frosted glass effects
- **3D interactive elements** using React Three Fiber
- **Responsive grid layout** with smooth animations
- **Full API integration** with the Python backend
- **Production-ready build system** with Vite

## Branch: `feature/glass-design-upgrade`

This feature is being developed independently from the backend to allow parallel development and testing.

---

## 📋 Setup Instructions

### 1. Backend Configuration

Ensure your backend (api.py) has CORS enabled for the frontend:

```python
# In api.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Add frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 2. Frontend Installation

```bash
# From project root
cd frontend_glass

# Install dependencies
npm install

# Start dev server
npm run dev
```

Server runs on: **http://localhost:5173**

### 3. Testing the Integration

1. Start backend: `python api.py` (localhost:8000)
2. Start frontend: `npm run dev` (localhost:5173)
3. Open http://localhost:5173 in browser
4. Check browser console for any API errors

---

## 🏗️ Project Structure

```
frontend_glass/
├── src/
│   ├── components/
│   │   ├── Header.jsx              # Navigation & sync button
│   │   ├── StatsPanel.jsx          # Dashboard stats cards
│   │   ├── GlassCard.jsx           # Individual subscription card
│   │   ├── GlassSubscriptionGrid.jsx # Grid layout
│   │   └── GlassScene.jsx          # 3D glass effects (Three.js)
│   ├── hooks/
│   │   └── useSubscriptions.js     # Data fetching & state
│   ├── App.jsx                     # Root component
│   ├── main.jsx                    # React entry
│   └── index.css                   # Global styles & animations
├── package.json                    # Dependencies & scripts
├── vite.config.js                  # Vite & API proxy config
├── tailwind.config.js              # Custom glass design tokens
├── tsconfig.json                   # TypeScript config
└── README.md                       # Component documentation

```

---

## 🎨 Design Features

### Glass Material Properties

Inspired by `glass-hero.md`, the subscription cards use physically-based glass simulation:

```javascript
// Material Parameters
transmission: 1.0         // Fully transparent
roughness: 0.41          // Semi-frosted (not mirror-like)
thickness: 1.35          // Volume thickness
ior: 2.14                // High refraction (diamond-like)
chromaticAberration: 0.415  // RGB light separation
iridescence: 1.0         // Soap-bubble effect
attenuationDistance: 4.7 // Light absorption depth
```

### Interactive Effects

1. **Mouse Parallax**: Cards track cursor position
2. **Hover Lift**: Cards elevate on hover (+translateY -4px)
3. **Glow Effect**: Radial light follows mouse on hover
4. **Shine Overlay**: Animated light sweep on hover

### Color System

| Category | Color | Hex |
|----------|-------|-----|
| Cloud | Blue → Cyan | `#7aa9ff` → `#00d4ff` |
| Dev Tools | Purple → Pink | `#a78bfa` → `#ff5e99` |
| AI | Yellow → Orange | `#ffe600` → `#ff6b1a` |
| Streaming | Orange → Red | `#ff6b1a` → `#ff4d4d` |
| Music | Green → Emerald | `#5fe39a` → `#10b981` |
| Design | Pink → Rose | `#ff5e99` → `#f43f5e` |
| Security | Blue → Indigo | `#0572ec` → `#6366f1` |

---

## 🔌 API Endpoints

All endpoints are proxied through `/api` (see vite.config.js):

### Get Subscriptions
```
GET /api/subscriptions?page_size=100
Response:
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 100,
  "pages": 1
}
```

### Get Statistics
```
GET /api/stats
Response:
{
  "total_subscriptions": 42,
  "total_monthly_cost": 145.50,
  "total_yearly_cost": 1746.00,
  "by_category": {...},
  "by_status": {...}
}
```

### Sync Emails
```
POST /api/sync-emails
Body:
{
  "sources": ["gmail", "outlook", "imap"],
  "max_results": 100,
  "since_days": 3
}
```

---

## 📦 Building for Production

### Development
```bash
npm run dev
```

### Production Build
```bash
npm run build
# Output: ../frontend_glass_dist/
```

### Preview Production Build
```bash
npm run preview
```

### Environment Variables for Production

Create `.env.local` or `.env.production`:
```
VITE_API_BASE=https://your-api-domain.com/api
```

---

## 🚀 Deployment

### Option 1: Serve from Backend (Recommended)

1. Build frontend:
   ```bash
   npm run build
   ```

2. Copy dist files to backend:
   ```bash
   cp -r ../frontend_glass_dist/* ../frontend/
   ```

3. Backend serves static files (already configured in api.py)

### Option 2: Separate Frontend Deployment

Deploy to Vercel, Netlify, or your hosting:

1. Build: `npm run build`
2. Configure API base: `VITE_API_BASE=https://your-api.com/api`
3. Deploy `frontend_glass_dist/` directory

### Option 3: Docker

```dockerfile
# Build stage
FROM node:18 AS builder
WORKDIR /app/frontend_glass
COPY . .
RUN npm install && npm run build

# Production stage
FROM node:18
WORKDIR /app
COPY --from=builder /app/frontend_glass_dist /app/dist
# Serve with your backend or nginx
```

---

## 🧪 Testing

### Manual Testing Checklist

- [ ] Cards load with subscription data
- [ ] Stats calculate correctly (monthly/yearly)
- [ ] Hover effects work smoothly
- [ ] Sync button triggers email fetch
- [ ] Responsive layout on mobile
- [ ] No console errors
- [ ] API calls complete successfully
- [ ] Status badges show correct colors

### Browser Compatibility

| Browser | Version | Support |
|---------|---------|---------|
| Chrome | 90+ | ✅ Full |
| Firefox | 88+ | ✅ Full |
| Safari | 15+ | ✅ Full |
| Edge | 90+ | ✅ Full |

**Note**: WebGL-based 3D effects require modern browsers.

---

## 🎯 Key Implementation Details

### useSubscriptions Hook

Handles all data fetching and state management:

```javascript
const {
  subscriptions,    // Array of subscription objects
  stats,            // Dashboard statistics
  loading,          // Loading state
  error,            // Error messages
  refetch,          // Refetch function
  syncEmails,       // Trigger email sync
} = useSubscriptions()
```

### GlassCard Component

Individual subscription display with:
- Gradient icon (category-based color)
- Cost formatting (currency, decimal places)
- Status badge with color coding
- Next billing date (if available)
- Hover parallax effect

### Responsive Breakpoints

```css
Mobile:    1 column
Tablet:    2 columns
Desktop:   3 columns
Wide:      4 columns
```

---

## 🐛 Troubleshooting

### API Connection Failed
- Check backend is running on localhost:8000
- Verify CORS settings in backend
- Check browser console for exact error

### Slow Performance
- Disable 3D scene if not needed
- Check network tab for slow API calls
- Reduce animation frame rate (check GlassCard.jsx)

### Styling Issues
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Rebuild Tailwind: `npm run dev` (rebuilds on file changes)
- Check tailwind.config.js for custom tokens

### Build Errors
- Ensure Node.js 18+ installed: `node --version`
- Delete vite cache: `rm -rf .vite && npm run build`

---

## 🔄 Workflow

### Development Workflow

1. Branch created: `feature/glass-design-upgrade` ✅
2. Frontend built independently
3. Integration tested locally
4. Components refined based on requirements
5. Ready for merge to main

### Merging to Main

When ready to integrate:

```bash
# In subscription_manager root
git checkout main
git pull origin main
git merge feature/glass-design-upgrade
git push origin main
```

Backend remains unchanged—this is a frontend-only feature.

---

## 📚 Technologies Used

| Package | Version | Purpose |
|---------|---------|---------|
| React | 18.2 | UI framework |
| Vite | 5.0 | Build tool |
| Three.js | r183 | WebGL rendering |
| @react-three/fiber | 8.16 | React reconciler for Three.js |
| Tailwind CSS | 3.3 | Utility styling |
| Zustand | 4.4 | State management (optional) |
| Framer Motion | 10.16 | Animations |

---

## 🎓 Learning Resources

- **Glass-Hero Analysis**: [glass-hero-analysis.md](../../glass-hero-analysis.md)
- **React Three Fiber**: https://docs.pmnd.rs/react-three-fiber/
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Three.js Docs**: https://threejs.org/docs/
- **Material UI Patterns**: https://www.ui-patterns.com/

---

## 💡 Future Enhancements

- [ ] Dark/light theme toggle
- [ ] Subscription detail modals
- [ ] Add/edit subscription flow
- [ ] Advanced filtering & sorting
- [ ] Category breakdown charts
- [ ] Email sync progress indicator
- [ ] Keyboard navigation
- [ ] Accessibility improvements (WCAG)
- [ ] Animations settings (reduced motion)
- [ ] Notification system

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review console errors in DevTools
3. Check API response in Network tab
4. Verify backend is running and accessible

---

**Status**: 🚀 Ready for development & testing  
**Branch**: `feature/glass-design-upgrade`  
**Last Updated**: May 15, 2026
