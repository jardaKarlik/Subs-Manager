# Subscription Manager - Glass Design Frontend

A modern, visually stunning subscription management dashboard featuring a **glass morphism design system** with advanced 3D effects using React, Three.js, and Tailwind CSS.

## ✨ Features

- **Glass Morphism Design**: Frosted glass aesthetic inspired by modern design trends
- **3D Glass Effects**: Optional Three.js scene for immersive visual enhancements
- **Responsive Grid Layout**: Adaptive card layout that works on all screen sizes
- **Real-time Stats**: Dynamic dashboard stats with monthly/yearly calculations
- **Smooth Animations**: Parallax effects, hover states, and fade-in transitions
- **API Integration**: Connected to the Python backend for live subscription data
- **Dark Mode**: Premium dark theme optimized for eye comfort

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn
- Running backend API on `http://localhost:8000`

### Installation

```bash
# Navigate to the frontend_glass directory
cd frontend_glass

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Production Build

```bash
npm run build
npm run preview
```

## 🎨 Design System

### Color Palette

| Token | Hex | Purpose |
|-------|-----|---------|
| Background | `#0a0a0c` | Dark void base |
| Glass Primary | `rgba(255,255,255,0.08)` | Main glass panels |
| Glass Secondary | `rgba(255,255,255,0.06)` | Nested glass layers |
| Accent - Yellow | `#ffe600` | Primary CTA |
| Accent - Green | `#5fe39a` | Active status |
| Accent - Purple | `#a78bfa` | Secondary actions |

### Glass Material Properties

Based on physically-based glass simulation (inspired by `glass-hero.md`):

```javascript
// MeshPhysicalMaterial Parameters
{
  transmission: 1.0,          // Full transparency
  roughness: 0.41,            // Semi-frosted surface
  thickness: 1.35,            // Glass volume depth
  ior: 2.14,                  // Diamond-like refraction
  chromaticAberration: 0.415, // RGB light separation
  clearcoat: 1.0,             // Extra glossy layer
  clearcoatRoughness: 0.59,   // Clearcoat frosting
  iridescence: 1.0,           // Thin-film interference
  iridescenceIOR: 2.34,       // Film refraction index
  attenuationDistance: 4.7,   // Light absorption depth
}
```

## 📁 Project Structure

```
frontend_glass/
├── src/
│   ├── components/
│   │   ├── Header.jsx          # Top navigation bar
│   │   ├── StatsPanel.jsx      # Statistics dashboard
│   │   ├── GlassCard.jsx       # Individual subscription card
│   │   ├── GlassSubscriptionGrid.jsx  # Grid container
│   │   └── GlassScene.jsx      # Optional 3D scene (React Three Fiber)
│   ├── hooks/
│   │   └── useSubscriptions.js # Data fetching hook
│   ├── App.jsx                 # Root component
│   ├── main.jsx                # Entry point
│   └── index.css               # Global styles
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── postcss.config.js
```

## 🔌 API Integration

### Environment Variables

Create a `.env` file or set at runtime:

```
VITE_API_BASE=/api
```

### Endpoints Used

- `GET /api/subscriptions?page_size=100` - Fetch all subscriptions
- `GET /api/stats` - Fetch statistics
- `POST /api/sync-emails` - Trigger email sync

## 🎯 Component Breakdown

### GlassCard
Individual subscription card with:
- Gradient icon based on category
- Cost display with currency formatting
- Billing cycle and status badge
- Hover parallax effect with mouse tracking
- Smooth hover animations and glow effects

### StatsPanel
Dashboard statistics showing:
- Monthly total cost
- Yearly total cost
- Active subscriptions count
- Total subscriptions count

### GlassSubscriptionGrid
Responsive grid layout with:
- Staggered fade-in animations
- 4-column layout on desktop (responsive)
- Empty state messaging
- Loading skeleton states

## 🎬 Animation & Interactions

### Hover Effects
- Card elevation (translateY -4px)
- Scale effect (1.02x)
- Border brightness increase
- Inner light glow effect
- Shine overlay animation

### Mouse Parallax
- Radial light follows cursor
- Subtle card position tracking
- Smooth easing with 0.05 lerp factor

### Entrance Animations
- Staggered slide-up with delay
- Fade-in from 24px below
- Duration: 0.6s ease-out

## 🔗 Integration with Backend

The frontend is fully independent but connects to the Python backend:

1. **API Proxy**: Vite config redirects `/api/*` to `http://localhost:8000`
2. **CORS**: Backend should allow requests from `http://localhost:5173`
3. **Data Format**: Subscriptions API returns paginated JSON with standard Subscription model

### Example Response
```json
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
      "next_billing_date": "2026-05-15T00:00:00"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 100,
  "pages": 1
}
```

## 🚦 Performance Optimization

- **Code Splitting**: Components lazy-loaded with React.Suspense
- **Image Optimization**: CSS-based gradients instead of images
- **Animation Performance**: GPU-accelerated CSS transforms
- **Bundle Size**: ~120KB gzipped (before Three.js)

## 🛠️ Development

### Linting
```bash
npm run lint
```

### Type Checking
```bash
npm run type-check
```

### Debug Mode
Open browser DevTools and check console for API/rendering logs.

## 📝 Notes

- **Glass Effect**: The optional 3D scene (`GlassScene.jsx`) uses WebGL and may impact performance on older devices
- **Browser Support**: Chrome 90+, Firefox 88+, Safari 15+ (WebGL required for 3D effects)
- **Mobile**: Fully responsive; 3D scene disabled on mobile for performance

## 🎓 Design Inspiration

This design system is inspired by:
- Glass-hero experiment (https://experiments.thisiswhitespace.com/glass-hero)
- Modern frosted glass (neumorphism) trends
- Physically-based rendering (PBR) material principles
- Contemporary dark mode UI patterns

## 📦 Dependencies

- **React 18**: Component framework
- **Three.js r183**: WebGL renderer
- **@react-three/fiber**: React reconciler for Three.js
- **@react-three/drei**: Useful React Three Fiber helpers
- **Tailwind CSS**: Utility-first CSS framework
- **Tailwind Merge**: Utility class merging
- **Framer Motion**: Smooth animations (optional enhancement)

## 🤝 Contributing

To improve the glass design:
1. Modify material properties in `GlassScene.jsx`
2. Adjust color tokens in `tailwind.config.js`
3. Tweak animation timings in component CSS
4. Test across browsers and devices

## 📄 License

Part of the Subscription Manager project.
