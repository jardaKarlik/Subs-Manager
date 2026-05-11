// Desktop "B" — Editorial / Bento layout
// 1440 × 980 artboard. Big typographic header, asymmetric bento grid.

function DesktopEditorial() {
  const total = totalMonthly();
  const byCat = totalByCat();
  const catList = CATEGORIES.map(c => ({ ...c, value: byCat[c.id] }));
  const idle = idleSubs();
  const top = topSpend(4);
  const spend = mkSpendSeries();

  return (
    <div style={{
      width: '100%', height: '100%',
      background: TOK.bg, color: TOK.text,
      fontFamily: TOK.display,
      padding: '28px 36px 36px',
      display: 'flex', flexDirection: 'column', gap: 18,
      overflow: 'hidden',
    }}>
      {/* Header bar */}
      <header style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 8,
            background: TOK.yellow, color: '#000',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 800, fontFamily: TOK.mono, fontSize: 15,
          }}>S</div>
          <span style={{ fontWeight: 600, fontSize: 17, letterSpacing: -0.4 }}>
            subs<span style={{ color: TOK.yellow }}>.</span>
          </span>
        </div>

        <nav style={{ display: 'flex', gap: 4, marginLeft: 12 }}>
          {['Overview','Services','Categories','Spending','Idle'].map((x, i) => (
            <span key={x} style={{
              padding: '7px 14px', borderRadius: 7,
              fontSize: 13, fontWeight: 500,
              color: i === 0 ? TOK.text : TOK.textDim,
              background: i === 0 ? TOK.surface2 : 'transparent',
              border: i === 0 ? `1px solid ${TOK.hairline}` : '1px solid transparent',
            }}>{x}</span>
          ))}
        </nav>

        <div style={{ flex: 1 }} />

        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          height: 34, padding: '0 12px', borderRadius: 8,
          background: TOK.surface2, border: `1px solid ${TOK.hairline}`, width: 220,
        }}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={TOK.textMute} strokeWidth="2">
            <circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>
          </svg>
          <span style={{ fontSize: 13, color: TOK.textMute }}>Search</span>
        </div>

        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: `linear-gradient(135deg, ${TOK.orange}, #c93b00)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontWeight: 700, fontSize: 12, fontFamily: TOK.mono,
        }}>MK</div>
      </header>

      {/* Editorial intro */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 24,
        alignItems: 'end', padding: '14px 0 8px',
        borderBottom: `1px solid ${TOK.hairline}`,
      }}>
        <div>
          <div style={{
            fontFamily: TOK.mono, fontSize: 11, color: TOK.yellow,
            letterSpacing: 2, textTransform: 'uppercase', marginBottom: 14,
          }}>
            ▍ May 2026 — {SERVICES.length} active subscriptions
          </div>
          <h1 style={{
            margin: 0, fontWeight: 600,
            fontSize: 64, letterSpacing: -2.4, lineHeight: 0.95,
          }}>
            You spend{' '}
            <span style={{
              background: TOK.yellow, color: '#0a0a0b',
              padding: '0 10px', borderRadius: 6,
              fontVariantNumeric: 'tabular-nums',
            }}>${total.toFixed(0)}</span>{' '}
            a month<br/>
            on <em style={{ fontStyle: 'italic', color: TOK.orange }}>subscriptions</em>.
          </h1>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 6 }}>
          <div style={{ display: 'flex', gap: 18 }}>
            <KPI label="Annual" value={`$${Math.round(total*12).toLocaleString()}`} delta="+6.2%" />
            <KPI label="Idle" value={idle.length.toString()} delta={`-$${idle.reduce((s,x)=>s+x.monthly,0).toFixed(0)}`} deltaColor={TOK.orange} />
            <KPI label="Renews · 7d" value="4" delta={`$${(top.slice(0,4).reduce((s,x)=>s+x.monthly,0)).toFixed(0)}`} />
          </div>
          <div style={{ fontFamily: TOK.mono, fontSize: 11, color: TOK.textDim, lineHeight: 1.5 }}>
            Up from <span style={{ color: TOK.text }}>$528.43</span> in April. Largest line:{' '}
            <span style={{ color: TOK.yellow }}>AWS · $142.30</span>. Lowest-utilised:{' '}
            <span style={{ color: TOK.orange }}>Tidal · 4%</span>.
          </div>
        </div>
      </div>

      {/* Bento grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(12, 1fr)',
        gridTemplateRows: 'repeat(2, 1fr)',
        gap: 14, flex: 1, minHeight: 0,
      }}>
        {/* Big chart */}
        <BentoCard span="span 7" rowSpan="span 1">
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 10 }}>
            <div>
              <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute, letterSpacing: 1.4, textTransform: 'uppercase' }}>
                Monthly spend · 12 months
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, marginTop: 4 }}>Trending upward</div>
            </div>
            <div style={{ display: 'flex', gap: 14, fontFamily: TOK.mono, fontSize: 10.5 }}>
              <span style={{ color: TOK.textDim, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 8, height: 2, background: TOK.yellow }}/>This year
              </span>
              <span style={{ color: TOK.textMute, display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 8, height: 2, background: TOK.textMute, opacity: 0.6 }}/>Last year
              </span>
            </div>
          </div>
          <AreaChart
            w={690} h={210}
            padding={[8, 6, 28, 36]}
            months={spend.months}
            series={[
              { data: [380,395,400,410,425,430,445,460,470,485,500,512], color: 'rgba(255,255,255,0.18)', width: 1.2 },
              { data: spend.data, color: TOK.yellow, width: 2.2, fill: 'url(#editFill)' },
            ]}
          />
          <svg width="0" height="0" style={{ position: 'absolute' }}>
            <defs>
              <linearGradient id="editFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={TOK.yellow} stopOpacity="0.22" />
                <stop offset="100%" stopColor={TOK.yellow} stopOpacity="0" />
              </linearGradient>
            </defs>
          </svg>
        </BentoCard>

        {/* Donut + categories list */}
        <BentoCard span="span 5" rowSpan="span 1">
          <div style={{ display: 'flex', alignItems: 'center', gap: 18, height: '100%' }}>
            <div style={{ position: 'relative', width: 150, height: 150, flex: '0 0 auto' }}>
              <Donut segments={catList.map(c => ({color:c.color, value:c.value}))} size={150} thickness={18} />
              <div style={{
                position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
              }}>
                <span style={{ fontFamily: TOK.mono, fontSize: 9.5, color: TOK.textMute, letterSpacing: 1 }}>MONTHLY</span>
                <span style={{ fontSize: 24, fontWeight: 600, letterSpacing: -0.6 }}>${total.toFixed(0)}</span>
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute, letterSpacing: 1.4, textTransform: 'uppercase', marginBottom: 4 }}>
                By category
              </div>
              {catList.sort((a,b)=>b.value-a.value).map(c => (
                <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: c.color }} />
                  <span style={{ fontSize: 12.5, flex: 1 }}>{c.name}</span>
                  <span style={{ fontFamily: TOK.mono, fontSize: 11.5 }}>${c.value.toFixed(0)}</span>
                </div>
              ))}
            </div>
          </div>
        </BentoCard>

        {/* Most expensive vertical */}
        <BentoCard span="span 4" rowSpan="span 1">
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>Most expensive</span>
            <span style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute }}>top 4</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
            {top.map((s, i) => (
              <div key={s.id} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 0', borderTop: `1px solid ${TOK.hairline}`,
              }}>
                <span style={{ fontFamily: TOK.mono, fontSize: 11, color: TOK.textMute, width: 14 }}>0{i+1}</span>
                <Logo svc={s} size={26} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 500 }}>{s.name}</div>
                  <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute }}>{s.plan}</div>
                </div>
                <span style={{ fontFamily: TOK.mono, fontSize: 13, color: i===0 ? TOK.yellow : TOK.text }}>
                  ${s.monthly.toFixed(0)}
                </span>
              </div>
            ))}
          </div>
        </BentoCard>

        {/* Idle / wasting */}
        <BentoCard span="span 5" rowSpan="span 1" emphasis>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.orange, letterSpacing: 1.4, textTransform: 'uppercase' }}>
                ▍ Idle alert
              </div>
              <div style={{ fontSize: 18, fontWeight: 600, marginTop: 4, letterSpacing: -0.4 }}>
                {idle.length} subs barely used
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontFamily: TOK.mono, fontSize: 9.5, color: TOK.textMute, letterSpacing: 1 }}>SAVINGS</div>
              <div style={{ fontSize: 22, fontWeight: 600, color: TOK.orange, letterSpacing: -0.6 }}>
                -${idle.reduce((s,x)=>s+x.monthly,0).toFixed(0)}<span style={{ fontSize: 12, color: TOK.textDim }}>/mo</span>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
            {idle.map(s => (
              <div key={s.id} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 10px 6px 6px', borderRadius: 999,
                background: TOK.surface2, border: `1px solid ${TOK.hairline}`,
              }}>
                <Logo svc={s} size={20} />
                <span style={{ fontSize: 12, fontWeight: 500 }}>{s.name}</span>
                <span style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.orange }}>
                  {Math.round(s.usage*100)}%
                </span>
              </div>
            ))}
          </div>
        </BentoCard>

        {/* Upcoming renewals */}
        <BentoCard span="span 3" rowSpan="span 1">
          <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute, letterSpacing: 1.4, textTransform: 'uppercase' }}>
            Renewing soon
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 0, marginTop: 8 }}>
            {[
              { svc: SERVICES.find(s=>s.id==='netflix'), in: 'May 12', days: 2 },
              { svc: SERVICES.find(s=>s.id==='spotify'), in: 'May 15', days: 5 },
              { svc: SERVICES.find(s=>s.id==='claude'),  in: 'May 18', days: 8 },
              { svc: SERVICES.find(s=>s.id==='figma'),   in: 'May 22', days: 12 },
            ].map((r, i) => (
              <div key={r.svc.id} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 0', borderTop: `1px solid ${TOK.hairline}`,
              }}>
                <Logo svc={r.svc} size={22} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 500 }}>{r.svc.name}</div>
                  <div style={{ fontFamily: TOK.mono, fontSize: 9.5, color: i===0 ? TOK.orange : TOK.textMute }}>
                    {r.in} · in {r.days}d
                  </div>
                </div>
                <span style={{ fontFamily: TOK.mono, fontSize: 11.5 }}>${r.svc.monthly.toFixed(0)}</span>
              </div>
            ))}
          </div>
        </BentoCard>
      </div>
    </div>
  );
}

function KPI({ label, value, delta, deltaColor=TOK.green }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span style={{ fontFamily: TOK.mono, fontSize: 9.5, color: TOK.textMute, letterSpacing: 1.2, textTransform: 'uppercase' }}>
        {label}
      </span>
      <span style={{ fontSize: 24, fontWeight: 600, letterSpacing: -0.6 }}>{value}</span>
      <span style={{ fontFamily: TOK.mono, fontSize: 10.5, color: deltaColor }}>{delta}</span>
    </div>
  );
}

function BentoCard({ span, rowSpan, children, emphasis }) {
  return (
    <div style={{
      gridColumn: span,
      gridRow: rowSpan,
      background: TOK.surface,
      borderRadius: 14, padding: 18,
      border: `1px solid ${emphasis ? `${TOK.orange}50` : TOK.hairline}`,
      position: 'relative', overflow: 'hidden',
      display: 'flex', flexDirection: 'column',
    }}>
      {emphasis && (
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: 2,
          background: `repeating-linear-gradient(90deg, ${TOK.orange} 0 8px, transparent 8px 16px)`,
        }}/>
      )}
      {children}
    </div>
  );
}

Object.assign(window, { DesktopEditorial });
