// Desktop "C" — Category detail (drill-down for AI tools)
// 1440 × 980 artboard.

function DesktopCategory({ catId = 'ai', selectedSvcId } = {}) {
  const cat = CATEGORIES.find(c => c.id === catId) || CATEGORIES[0];
  const services = SERVICES.filter(s => s.cat === cat.id);
  const [selected, setSelected] = React.useState(selectedSvcId || services[0].id);
  React.useEffect(() => { if (selectedSvcId) setSelected(selectedSvcId); }, [selectedSvcId]);
  const svc = services.find(s => s.id === selected) || services[0];
  const total = services.reduce((s,x)=>s+x.monthly,0);
  const spend12 = [82, 88, 90, 92, 96, 98, 100, 100.4, 100.4, 100.4, 100.4, 100.4];

  return (
    <div style={{
      width: '100%', height: '100%',
      background: TOK.bg, color: TOK.text,
      fontFamily: TOK.display,
      display: 'grid', gridTemplateColumns: '232px 1fr',
      overflow: 'hidden',
    }}>
      <Sidebar active="categories" />
      <main style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {/* Breadcrumb header */}
        <header style={{
          height: 64, padding: '0 32px',
          display: 'flex', alignItems: 'center', gap: 14,
          borderBottom: `1px solid ${TOK.hairline}`,
        }}>
          <span onClick={() => window.__nav && window.__nav('back')} style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: 28, height: 28, borderRadius: 7, cursor: 'pointer',
            border: `1px solid ${TOK.hairline}`, color: TOK.textDim, fontSize: 14,
          }}>‹</span>
          <span onClick={() => window.__nav && window.__nav('section', 'categories')} style={{ fontFamily: TOK.mono, fontSize: 11.5, color: TOK.textDim, cursor: 'pointer' }}>Categories</span>
          <span style={{ color: TOK.textMute }}>/</span>
          <span style={{ fontSize: 14, fontWeight: 600 }}>{cat.name === 'AI' ? 'AI tools' : cat.name}</span>
          <span style={{
            fontFamily: TOK.mono, fontSize: 10, color: cat.color,
            padding: '2px 7px', borderRadius: 3,
            background: `${cat.color}1a`, border: `1px solid ${cat.color}55`,
            letterSpacing: 1, textTransform: 'uppercase',
          }}>{services.length} services</span>
          <div style={{ flex: 1 }}/>
          <span style={{
            fontFamily: TOK.mono, fontSize: 11, color: TOK.textDim,
            padding: '6px 10px', borderRadius: 6, border: `1px solid ${TOK.hairline}`,
          }}>↓ Sort: monthly</span>
          <span style={{
            fontFamily: TOK.mono, fontSize: 11, color: TOK.textDim,
            padding: '6px 10px', borderRadius: 6, border: `1px solid ${TOK.hairline}`,
          }}>⚙ Filter</span>
        </header>

        <div style={{
          padding: '24px 32px',
          display: 'grid', gridTemplateColumns: '1fr 360px',
          gap: 22, overflow: 'hidden', flex: 1, minHeight: 0,
        }}>
          {/* Left column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18, minHeight: 0 }}>
            {/* Category header */}
            <div style={{
              background: TOK.surface,
              borderRadius: 14, padding: 22,
              border: `1px solid ${TOK.hairline}`,
              position: 'relative', overflow: 'hidden',
            }}>
              <div style={{
                position: 'absolute', inset: 0,
                background: `radial-gradient(600px 200px at 20% -10%, ${cat.color}1a, transparent 60%)`,
              }}/>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-end', gap: 32 }}>
                <div>
                  <div style={{ fontFamily: TOK.mono, fontSize: 11, color: cat.color, letterSpacing: 1.6, textTransform: 'uppercase' }}>
                    ▍ Category
                  </div>
                  <div style={{ fontSize: 36, fontWeight: 600, letterSpacing: -1.2, marginTop: 6 }}>
                    {cat.name === 'AI' ? 'AI tools' : cat.name}
                  </div>
                  <div style={{ fontFamily: TOK.mono, fontSize: 11.5, color: TOK.textDim, marginTop: 4 }}>
                    Coding · Creative · Voice · Image · API
                  </div>
                </div>
                <div style={{ flex: 1 }}/>
                <div style={{ display: 'flex', gap: 28 }}>
                  <Stat label="Monthly" value={`$${total.toFixed(2)}`} accent={cat.color} />
                  <Stat label="Annual" value={`$${(total*12).toFixed(0)}`} />
                  <Stat label="Active" value={`${services.filter(s=>s.status==='active').length}/${services.length}`} />
                  <Stat label="Avg use" value={`${Math.round(services.reduce((s,x)=>s+x.usage,0)/services.length*100)}%`} accent={TOK.yellow} />
                </div>
              </div>
            </div>

            {/* Services table */}
            <div style={{
              background: TOK.surface,
              borderRadius: 14, padding: '6px 0',
              border: `1px solid ${TOK.hairline}`,
              overflow: 'hidden', flex: 1, minHeight: 0,
              display: 'flex', flexDirection: 'column',
            }}>
              <div style={{
                display: 'grid', gridTemplateColumns: '34px 1.5fr 1fr 90px 70px 110px 28px',
                gap: 12, padding: '12px 20px',
                fontFamily: TOK.mono, fontSize: 9.5, color: TOK.textMute,
                letterSpacing: 1, textTransform: 'uppercase',
                borderBottom: `1px solid ${TOK.hairline}`,
              }}>
                <span></span><span>Service · Plan</span><span>Usage · 30d</span>
                <span style={{textAlign:'right'}}>Monthly</span>
                <span style={{textAlign:'right'}}>Since</span>
                <span>Trend</span><span></span>
              </div>
              <div style={{ flex: 1, overflow: 'auto' }}>
                {services.map((s, i) => {
                  const trend = [s.monthly*0.9, s.monthly*0.95, s.monthly, s.monthly, s.monthly*1.05, s.monthly, s.monthly];
                  const isSelected = s.id === svc.id;
                  return (
                    <div key={s.id} onClick={() => setSelected(s.id)} style={{
                      display: 'grid', gridTemplateColumns: '34px 1.5fr 1fr 90px 70px 110px 28px', cursor: 'pointer',
                      gap: 12, padding: '14px 20px', alignItems: 'center',
                      borderBottom: i < services.length - 1 ? `1px solid ${TOK.hairline}` : 'none',
                      background: isSelected ? TOK.yellowSoft : 'transparent',
                      borderLeft: isSelected ? `2px solid ${TOK.yellow}` : '2px solid transparent',
                    }}>
                      <Logo svc={s} size={32} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
                          {s.name}
                          {s.status === 'idle' && (
                            <span style={{
                              fontFamily: TOK.mono, fontSize: 9, color: TOK.orange,
                              padding: '1px 5px', borderRadius: 2,
                              background: TOK.orangeSoft, letterSpacing: 1, textTransform: 'uppercase',
                            }}>idle</span>
                          )}
                        </div>
                        <div style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textMute, marginTop: 2 }}>
                          {s.plan} · {s.billing}
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Bar value={s.usage} w={80} h={4} color={s.usage > 0.5 ? TOK.yellow : TOK.orange} />
                        <span style={{ fontFamily: TOK.mono, fontSize: 11, color: TOK.textDim }}>
                          {Math.round(s.usage*100)}%
                        </span>
                      </div>
                      <span style={{ fontFamily: TOK.mono, fontSize: 14, textAlign: 'right' }}>
                        ${s.monthly.toFixed(2)}
                      </span>
                      <span style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textDim, textAlign: 'right' }}>
                        {s.since}
                      </span>
                      <Sparkline data={trend} w={100} h={22} stroke={s.usage > 0.5 ? TOK.yellow : TOK.orange} />
                      <span style={{ fontFamily: TOK.mono, color: TOK.textMute, fontSize: 16, cursor: 'pointer' }}>⋯</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right column — sticky service detail */}
          <ServiceCard svc={svc} spend12={spend12} />
        </div>
      </main>
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ fontFamily: TOK.mono, fontSize: 9.5, color: TOK.textMute, letterSpacing: 1.2, textTransform: 'uppercase' }}>
        {label}
      </span>
      <span style={{ fontSize: 26, fontWeight: 600, letterSpacing: -0.8, color: accent || TOK.text }}>
        {value}
      </span>
    </div>
  );
}

function ServiceCard({ svc, spend12 }) {
  return (
    <div style={{
      background: TOK.surface, borderRadius: 14,
      border: `1px solid ${TOK.hairline}`,
      overflow: 'hidden', display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        padding: 20, position: 'relative',
        background: `linear-gradient(180deg, ${svc.color}15, transparent)`,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Logo svc={svc} size={44} />
          <div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>{svc.name}</div>
            <div style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textMute, marginTop: 2 }}>
              {svc.plan} · since {svc.since}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 18 }}>
          <span style={{ fontSize: 40, fontWeight: 600, letterSpacing: -1.2 }}>
            ${svc.monthly.toFixed(2)}
          </span>
          <span style={{ fontFamily: TOK.mono, fontSize: 12, color: TOK.textDim }}>/month</span>
        </div>
        <div style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textDim, marginTop: 4 }}>
          ${(svc.monthly*12).toFixed(0)} per year
        </div>
      </div>

      <div style={{ padding: '14px 20px', borderTop: `1px solid ${TOK.hairline}` }}>
        <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute, letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 8 }}>
          Spend · last 12mo
        </div>
        <AreaChart
          w={310} h={90}
          padding={[6, 0, 18, 0]}
          months={['','','','','J','','','','','','','M']}
          series={[{ data: spend12, color: TOK.yellow, width: 1.8, fill: 'url(#svcFill)' }]}
        />
        <svg width="0" height="0" style={{ position: 'absolute' }}>
          <defs>
            <linearGradient id="svcFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={TOK.yellow} stopOpacity="0.25" />
              <stop offset="100%" stopColor={TOK.yellow} stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      <div style={{ padding: '14px 20px', borderTop: `1px solid ${TOK.hairline}`, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <Row label="Usage · 30d" value={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Bar value={svc.usage} w={60} h={4} color={TOK.yellow} />
            <span style={{ fontFamily: TOK.mono, fontSize: 11.5 }}>{Math.round(svc.usage*100)}%</span>
          </div>
        } />
        <Row label="Renews" value={<span style={{ fontFamily: TOK.mono, fontSize: 11.5 }}>May 18 · in 8d</span>} />
        <Row label="Payment" value={<span style={{ fontFamily: TOK.mono, fontSize: 11.5 }}>•• 4242 · Mastercard</span>} />
        <Row label="Seats" value={<span style={{ fontFamily: TOK.mono, fontSize: 11.5 }}>1 of 1</span>} />
      </div>

      <div style={{ padding: '14px 20px', borderTop: `1px solid ${TOK.hairline}`, display: 'flex', gap: 8 }}>
        <button style={{
          flex: 1, height: 36, borderRadius: 8, border: 'none', cursor: 'pointer',
          background: TOK.yellow, color: '#000',
          fontFamily: TOK.display, fontWeight: 600, fontSize: 12.5,
        }}>Open service ↗</button>
        <button style={{
          height: 36, padding: '0 14px', borderRadius: 8,
          background: 'transparent', color: TOK.textDim, cursor: 'pointer',
          border: `1px solid ${TOK.hairline}`,
          fontFamily: TOK.display, fontSize: 12.5,
        }}>Edit</button>
        <button style={{
          height: 36, padding: '0 14px', borderRadius: 8,
          background: 'transparent', color: TOK.orange, cursor: 'pointer',
          border: `1px solid ${TOK.orange}66`,
          fontFamily: TOK.display, fontSize: 12.5,
        }}>Cancel</button>
      </div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <span style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textMute, letterSpacing: 0.6, textTransform: 'uppercase' }}>
        {label}
      </span>
      {value}
    </div>
  );
}

Object.assign(window, { DesktopCategory });
