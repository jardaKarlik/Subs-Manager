// Shared data, primitive logos, and chart helpers for Subs dashboard

// ─── Color tokens ──────────────────────────────────────────────
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
  mono: '"JetBrains Mono", "SF Mono", ui-monospace, Menlo, monospace',
};

// ─── Service catalog ───────────────────────────────────────────
// Each service: { id, name, mono (1-2 chars), color, category, plan, monthly, billing, usage, since, status }
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

const SERVICES = [
  // Cloud
  { id:'aws',       name:'AWS',          mono:'aw', color:'#ff9900', cat:'cloud',  plan:'Pay-as-you-go', monthly: 142.30, billing:'Monthly', usage:0.92, since:'2021-04', status:'active' },
  { id:'vercel',    name:'Vercel',       mono:'▲',  color:'#ffffff', cat:'cloud',  plan:'Pro',           monthly:  20.00, billing:'Monthly', usage:0.71, since:'2022-09', status:'active' },
  { id:'cflare',    name:'Cloudflare',   mono:'CF', color:'#f48120', cat:'cloud',  plan:'Workers Paid',  monthly:   5.00, billing:'Monthly', usage:0.34, since:'2023-01', status:'active' },
  { id:'do',        name:'DigitalOcean', mono:'do', color:'#0080ff', cat:'cloud',  plan:'Droplet 4GB',   monthly:  24.00, billing:'Monthly', usage:0.18, since:'2020-02', status:'idle' },
  { id:'supabase',  name:'Supabase',     mono:'sb', color:'#3ecf8e', cat:'cloud',  plan:'Pro',           monthly:  25.00, billing:'Monthly', usage:0.66, since:'2023-06', status:'active' },

  // Dev Tools
  { id:'github',    name:'GitHub',       mono:'gh', color:'#e6e6e6', cat:'dev_tools', plan:'Team',          monthly:   4.00, billing:'Monthly', usage:0.95, since:'2019-08', status:'active' },
  { id:'linear',    name:'Linear',       mono:'L',  color:'#8a8df0', cat:'dev_tools', plan:'Standard',      monthly:  10.00, billing:'Monthly', usage:0.88, since:'2022-03', status:'active' },
  { id:'figma',     name:'Figma',        mono:'F',  color:'#f24e1e', cat:'dev_tools', plan:'Professional',  monthly:  15.00, billing:'Monthly', usage:0.72, since:'2021-11', status:'active' },
  { id:'notion',    name:'Notion',       mono:'N',  color:'#ffffff', cat:'dev_tools', plan:'Plus',          monthly:  10.00, billing:'Monthly', usage:0.61, since:'2020-07', status:'active' },
  { id:'sentry',    name:'Sentry',       mono:'sy', color:'#a07cff', cat:'dev_tools', plan:'Team',          monthly:  26.00, billing:'Monthly', usage:0.42, since:'2022-10', status:'active' },
  { id:'1pass',     name:'1Password',    mono:'1P', color:'#0572ec', cat:'security',  plan:'Family',        monthly:   4.99, billing:'Monthly', usage:0.99, since:'2018-05', status:'active' },

  // AI
  { id:'claude',    name:'Claude',       mono:'C',  color:'#d97757', cat:'ai',     plan:'Max',           monthly:  20.00, billing:'Monthly', usage:0.91, since:'2024-02', status:'active' },
  { id:'cursor',    name:'Cursor',       mono:'cu', color:'#ffffff', cat:'ai',     plan:'Pro',           monthly:  20.00, billing:'Monthly', usage:0.83, since:'2024-05', status:'active' },
  { id:'mj',        name:'Midjourney',   mono:'mj', color:'#b8b8b8', cat:'ai',     plan:'Standard',      monthly:  30.00, billing:'Monthly', usage:0.12, since:'2023-09', status:'idle' },
  { id:'eleven',    name:'ElevenLabs',   mono:'11', color:'#cdb4ff', cat:'ai',     plan:'Creator',       monthly:  22.00, billing:'Monthly', usage:0.28, since:'2024-01', status:'active' },
  { id:'replicate', name:'Replicate',    mono:'rp', color:'#ff5b3f', cat:'ai',     plan:'Pay-as-you-go', monthly:   8.40, billing:'Monthly', usage:0.45, since:'2023-12', status:'active' },

  // Streaming
  { id:'netflix',   name:'Netflix',      mono:'nf', color:'#e50914', cat:'streaming', plan:'Standard',      monthly:  15.49, billing:'Monthly', usage:0.65, since:'2017-03', status:'active' },
  { id:'hbo',       name:'Max',          mono:'M',  color:'#a020f0', cat:'streaming', plan:'Ad-Free',       monthly:  15.99, billing:'Monthly', usage:0.21, since:'2022-08', status:'idle' },
  { id:'disney',    name:'Disney+',      mono:'D+', color:'#0d6cff', cat:'streaming', plan:'Premium',       monthly:  13.99, billing:'Monthly', usage:0.08, since:'2021-12', status:'idle' },
  { id:'appletv',   name:'Apple TV+',    mono:'tv', color:'#ffffff', cat:'streaming', plan:'Standard',      monthly:   9.99, billing:'Monthly', usage:0.31, since:'2023-04', status:'active' },

  // Music
  { id:'spotify',   name:'Spotify',      mono:'sp', color:'#1ed760', cat:'music',  plan:'Family',        monthly:  16.99, billing:'Monthly', usage:0.98, since:'2016-01', status:'active' },
  { id:'tidal',     name:'Tidal',        mono:'ti', color:'#ffffff', cat:'music',  plan:'HiFi',          monthly:  10.99, billing:'Monthly', usage:0.04, since:'2024-06', status:'idle' },
  { id:'sc',        name:'SoundCloud',   mono:'sc', color:'#ff7700', cat:'music',  plan:'Go+',           monthly:   9.99, billing:'Monthly', usage:0.17, since:'2023-02', status:'idle' },
];

function fmt$(n) { return '$' + n.toFixed(2); }
function fmt$0(n) { return '$' + Math.round(n).toLocaleString(); }

function totalMonthly() { return SERVICES.reduce((s, x) => s + x.monthly, 0); }
function totalByCat() {
  const o = {};
  CATEGORIES.forEach(c => o[c.id] = 0);
  SERVICES.forEach(s => o[s.cat] += s.monthly);
  return o;
}
function idleSubs() { return SERVICES.filter(s => s.status === 'idle' || s.usage < 0.2); }
function topSpend(n=5) { return [...SERVICES].sort((a,b) => b.monthly - a.monthly).slice(0,n); }

// ─── Logo tile component ───────────────────────────────────────
function Logo({ svc, size = 28, radius }) {
  const r = radius ?? Math.round(size * 0.28);
  const fontSize = Math.round(size * 0.42);
  // Determine text color: light bg → black, dark or saturated → white
  const c = svc.color.toLowerCase();
  const lightBg = c === '#ffffff' || c === '#e6e6e6' || c === '#b8b8b8' || c === '#cdb4ff';
  const fg = lightBg ? '#0a0a0b' : '#fff';
  return (
    <div style={{
      width: size, height: size, borderRadius: r,
      background: svc.color,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: TOK.mono, fontWeight: 600, fontSize, color: fg,
      letterSpacing: -0.5, lineHeight: 1, textTransform: 'lowercase',
      boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.15)',
      flex: '0 0 auto',
    }}>{svc.mono}</div>
  );
}

// ─── Sparkline ─────────────────────────────────────────────────
function Sparkline({ data, w=80, h=24, stroke=TOK.yellow, fill }) {
  const max = Math.max(...data), min = Math.min(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((v - min) / range) * h;
    return [x, y];
  });
  const path = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  const areaPath = path + ` L ${w},${h} L 0,${h} Z`;
  return (
    <svg width={w} height={h} style={{ display: 'block', overflow: 'visible' }}>
      {fill && <path d={areaPath} fill={fill} />}
      <path d={path} stroke={stroke} strokeWidth={1.5} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ─── Area / line chart (multi-series) ──────────────────────────
function AreaChart({ series, w, h, padding=[18,12,28,40], showAxis=true, months }) {
  const [pt, pr, pb, pl] = padding;
  const iw = w - pl - pr, ih = h - pt - pb;
  const all = series.flatMap(s => s.data);
  const max = Math.max(...all) * 1.08;
  const n = series[0].data.length;
  const x = (i) => pl + (i / (n - 1)) * iw;
  const y = (v) => pt + ih - (v / max) * ih;

  const ticks = 4;
  const yTicks = Array.from({length: ticks + 1}, (_, i) => max * (i / ticks));

  return (
    <svg width={w} height={h} style={{ display: 'block' }}>
      {/* horizontal grid */}
      {yTicks.map((v, i) => (
        <line key={i} x1={pl} x2={w - pr} y1={y(v)} y2={y(v)} stroke={TOK.hairline} />
      ))}
      {/* axes */}
      {showAxis && yTicks.map((v, i) => (
        <text key={i} x={pl - 6} y={y(v) + 3} textAnchor="end"
          fill={TOK.textMute} fontSize={9} fontFamily={TOK.mono}>${Math.round(v)}</text>
      ))}
      {months && months.map((m, i) => (
        <text key={i} x={x(i)} y={h - pb + 14} textAnchor="middle"
          fill={TOK.textMute} fontSize={9} fontFamily={TOK.mono}>{m}</text>
      ))}
      {/* series */}
      {series.map((s, si) => {
        const path = s.data.map((v, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1)).join(' ');
        const area = path + ` L ${x(n-1)},${pt+ih} L ${x(0)},${pt+ih} Z`;
        return (
          <g key={si}>
            {s.fill && <path d={area} fill={s.fill} />}
            <path d={path} stroke={s.color} strokeWidth={s.width || 1.75} fill="none"
              strokeLinecap="round" strokeLinejoin="round" />
          </g>
        );
      })}
    </svg>
  );
}

// ─── Donut chart ───────────────────────────────────────────────
function Donut({ segments, size, thickness=18, gap=2 }) {
  const r = size / 2 - thickness / 2 - 2;
  const cx = size/2, cy = size/2;
  const total = segments.reduce((s, x) => s + x.value, 0);
  const C = 2 * Math.PI * r;
  let offset = 0;
  return (
    <svg width={size} height={size} style={{ display: 'block', transform: 'rotate(-90deg)' }}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={TOK.surface3} strokeWidth={thickness} />
      {segments.map((s, i) => {
        const len = (s.value / total) * C - gap;
        const dash = `${len} ${C - len}`;
        const el = <circle key={i} cx={cx} cy={cy} r={r} fill="none"
          stroke={s.color} strokeWidth={thickness} strokeDasharray={dash} strokeDashoffset={-offset} strokeLinecap="butt" />;
        offset += (s.value / total) * C;
        return el;
      })}
    </svg>
  );
}

// ─── Tiny progress bar ─────────────────────────────────────────
function Bar({ value, w=80, h=4, color=TOK.yellow, bg=TOK.surface3 }) {
  return (
    <div style={{ width: w, height: h, background: bg, borderRadius: h/2, overflow: 'hidden' }}>
      <div style={{ width: `${value*100}%`, height: '100%', background: color, borderRadius: h/2 }} />
    </div>
  );
}

// Random-ish but deterministic data shaped for currents (in monthly $)
function mkSpendSeries(seed=1) {
  const months = ['Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov'];
  // base trending up, with seasonal noise
  const base = [410, 425, 438, 442, 461, 472, 488, 502, 519, 528, 547, 562];
  return { months, data: base };
}

// ─── Palette presets ───────────────────────────────────────────
// Each palette overrides the two accent colors + their soft variants.
// Background/surface colors stay dark across all palettes.
const PALETTES = {
  'yellow-orange': {
    name: 'Volt',
    swatch: ['#ffe600', '#ff6b1a'],
    yellow: '#ffe600', yellowDim: '#c9b800',
    yellowSoft: 'rgba(255,230,0,0.12)',
    orange: '#ff6b1a', orangeSoft: 'rgba(255,107,26,0.14)',
  },
  'lime-magenta': {
    name: 'Acid',
    swatch: ['#c5ff3d', '#ff2d8a'],
    yellow: '#c5ff3d', yellowDim: '#9bd416',
    yellowSoft: 'rgba(197,255,61,0.12)',
    orange: '#ff2d8a', orangeSoft: 'rgba(255,45,138,0.14)',
  },
  'cyan-coral': {
    name: 'Reef',
    swatch: ['#5eead4', '#ff7a59'],
    yellow: '#5eead4', yellowDim: '#3fbfae',
    yellowSoft: 'rgba(94,234,212,0.12)',
    orange: '#ff7a59', orangeSoft: 'rgba(255,122,89,0.14)',
  },
  'mint-violet': {
    name: 'Spruce',
    swatch: ['#a3f9b9', '#b388ff'],
    yellow: '#a3f9b9', yellowDim: '#76d68d',
    yellowSoft: 'rgba(163,249,185,0.12)',
    orange: '#b388ff', orangeSoft: 'rgba(179,136,255,0.16)',
  },
  'amber-crimson': {
    name: 'Ember',
    swatch: ['#ffb547', '#ff3355'],
    yellow: '#ffb547', yellowDim: '#d68a14',
    yellowSoft: 'rgba(255,181,71,0.12)',
    orange: '#ff3355', orangeSoft: 'rgba(255,51,85,0.14)',
  },
  'paper-noir': {
    name: 'Noir',
    swatch: ['#f5f5f3', '#ff5f00'],
    yellow: '#f5f5f3', yellowDim: '#a0a0a0',
    yellowSoft: 'rgba(245,245,243,0.10)',
    orange: '#ff5f00', orangeSoft: 'rgba(255,95,0,0.16)',
  },
};

function applyPalette(key) {
  const p = PALETTES[key] || PALETTES['yellow-orange'];
  TOK.yellow = p.yellow;
  TOK.yellowDim = p.yellowDim;
  TOK.yellowSoft = p.yellowSoft;
  TOK.orange = p.orange;
  TOK.orangeSoft = p.orangeSoft;
  // Also update the AI and streaming category colors to match the new accent
  const aiCat = CATEGORIES.find(c => c.id === 'ai');
  if (aiCat) aiCat.color = p.yellow;
  const streamCat = CATEGORIES.find(c => c.id === 'streaming');
  if (streamCat) streamCat.color = p.orange;
}

Object.assign(window, {
  TOK, CATEGORIES, SERVICES, PALETTES, applyPalette,
  fmt$, fmt$0, totalMonthly, totalByCat, idleSubs, topSpend,
  Logo, Sparkline, AreaChart, Donut, Bar,
  mkSpendSeries,
});
