// Shared data for Subs dashboard - FALLBACK ONLY
// This should be replaced by app.js with real backend data

const TOK = {
  bg: '#0a0a0b',
  surface: '#101013',
  surface2: '#16161a',
  surface3: '#1c1c21',
  hairline: 'rgba(255,255,255,0.06)',
  hairlineStrong: 'rgba(255,255,255,0.12)',
  text: '#f5f5f3',
  textDim: '#8a8a8e',
  textMute: '#56565b',
  yellow: '#ffe600',
  yellowDim: '#c9b800',
  yellowSoft: 'rgba(255,230,0,0.12)',
  orange: '#ff6b1a',
  orangeSoft: 'rgba(255,107,26,0.14)',
  red: '#ff4d4d',
  green: '#5fe39a',
  display: '"Space Grotesk", "Helvetica Neue", Helvetica, sans-serif',
  mono: '"JetBrains Mono", "SF Mono", Menlo, monospace',
};

const CATEGORIES = [
  { id: 'cloud',        name: 'Cloud',        color: '#7aa9ff' },
  { id: 'dev_tools',    name: 'Dev Tools',    color: '#a78bfa' },
  { id: 'ai',           name: 'AI',           color: '#ffe600' },
  { id: 'streaming',    name: 'Streaming',    color: '#ff6b1a' },
  { id: 'music',        name: 'Music',        color: '#5fe39a' },
  { id: 'music_tools',  name: 'Music Tools',  color: '#00d4aa' },
  { id: 'design',       name: 'Design',       color: '#ff5e99' },
  { id: 'productivity', name: 'Productivity', color: '#8a8df0' },
  { id: 'gaming',       name: 'Gaming',       color: '#ff4d4d' },
  { id: 'security',     name: 'Security',     color: '#0572ec' },
];

// Initialize empty - app.js will populate from backend
let SERVICES = [];

// Helper functions for dashboard components
function totalMonthly() {
  return SERVICES.reduce((sum, s) => sum + s.monthly, 0);
}

function totalByCat() {
  const result = {};
  CATEGORIES.forEach(c => { result[c.id] = 0; });
  SERVICES.forEach(s => {
    if (result[s.cat] !== undefined) result[s.cat] += s.monthly;
  });
  return result;
}

function idleSubs() {
  return SERVICES.filter(s => s.usage < 0.2);
}

function topSpend(n) {
  return [...SERVICES].sort((a, b) => b.monthly - a.monthly).slice(0, n);
}

function mkSpendSeries() {
  const months = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
  const data = months.map((_, i) => totalMonthly() * (0.9 + i * 0.01));
  return { months, data };
}
