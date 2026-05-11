// Desktop Dashboard "A" — Command Center
// 1440 × 980 artboard. Sidebar + main grid.

function DesktopCommand({ section = 'overview' } = {}) {
  const total = totalMonthly();
  const annual = total * 12;
  const byCat = totalByCat();
  const catList = CATEGORIES.map(c => ({ ...c, value: byCat[c.id] }));
  const idle = idleSubs();
  const top = topSpend(5);
  const spend = mkSpendSeries();

  return (
    <div style={{
      width: '100%', height: '100%',
      background: TOK.bg, color: TOK.text,
      fontFamily: TOK.display,
      display: 'grid', gridTemplateColumns: '232px 1fr',
      overflow: 'hidden',
    }}>
      <Sidebar active={section} />
      <main style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <TopBar />
        <div style={{
          padding: '24px 32px 40px',
          display: 'grid',
          gridTemplateColumns: '1.6fr 1fr',
          gridTemplateRows: 'auto auto auto',
          gap: 18,
          overflow: 'hidden',
        }}>
          {/* Hero metric */}
          <HeroSpend total={total} annual={annual} spend={spend} />
          {/* Donut */}
          <CategoryDonut catList={catList} total={total} />

          {/* Categories row spans both */}
          <div style={{ gridColumn: '1 / -1' }}>
            <CategoriesStrip catList={catList} />
          </div>

          {/* Bottom row */}
          <TopServices top={top} total={total} />
          <IdlePanel idle={idle} />
        </div>
      </main>
    </div>
  );
}

// ─── Sidebar ───────────────────────────────────────────────────
function Sidebar({ active }) {
  const items = [
    { id: 'overview',   label: 'Overview' },
    { id: 'services',   label: 'All services' },
    { id: 'categories', label: 'Categories' },
    { id: 'spending',   label: 'Spending' },
    { id: 'idle',       label: 'Idle' },
    { id: 'renewals',   label: 'Renewals' },
  ];
  return (
    <aside style={{
      background: TOK.surface,
      borderRight: `1px solid ${TOK.hairline}`,
      padding: '20px 14px 14px',
      display: 'flex', flexDirection: 'column', gap: 4,
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 8px 22px' }}>
        <div style={{
          width: 26, height: 26, borderRadius: 7,
          background: TOK.yellow,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#000', fontWeight: 800, fontFamily: TOK.mono, fontSize: 13,
        }}>S</div>
        <div style={{ fontWeight: 600, fontSize: 16, letterSpacing: -0.4 }}>
          subs<span style={{ color: TOK.yellow }}>.</span>
        </div>
      </div>

      <div style={{
        fontFamily: TOK.mono, fontSize: 9.5, color: TOK.textMute,
        letterSpacing: 1.2, textTransform: 'uppercase', padding: '6px 8px 4px',
      }}>Workspace</div>

      {items.map(i => (
        <div key={i.id} onClick={() => window.__nav && window.__nav('section', i.id)} style={{
          display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer',
          padding: '8px 10px',
          borderRadius: 7,
          background: i.id === active ? TOK.surface3 : 'transparent',
          color: i.id === active ? TOK.text : TOK.textDim,
          fontSize: 13.5, fontWeight: 500,
          position: 'relative',
        }}>
          {i.id === active && (
            <span style={{
              position: 'absolute', left: -14, top: 8, bottom: 8, width: 2,
              background: TOK.yellow, borderRadius: 2,
            }}/>
          )}
          <span style={{
            width: 14, height: 14, borderRadius: 3,
            border: `1px solid ${i.id === active ? TOK.yellow : TOK.hairlineStrong}`,
            background: i.id === active ? TOK.yellowSoft : 'transparent',
          }}/>
          {i.label}
        </div>
      ))}

      <div style={{ flex: 1 }} />

      <div style={{
        fontFamily: TOK.mono, fontSize: 9.5, color: TOK.textMute,
        letterSpacing: 1.2, textTransform: 'uppercase', padding: '6px 8px 4px',
      }}>Categories</div>
      {CATEGORIES.map(c => (
        <div key={c.id} onClick={() => window.__nav && window.__nav('category', c.id)} style={{
          display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer',
          padding: '6px 10px',
          fontSize: 13, color: TOK.textDim,
        }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: c.color }} />
          {c.name}
        </div>
      ))}

      <div style={{ height: 1, background: TOK.hairline, margin: '16px 4px 12px' }}/>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 8px' }}>
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: `linear-gradient(135deg, ${TOK.orange}, #c93b00)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontWeight: 700, fontSize: 11, fontFamily: TOK.mono,
        }}>MK</div>
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
          <span style={{ fontSize: 12.5, fontWeight: 500 }}>Marek K.</span>
          <span style={{ fontSize: 10.5, color: TOK.textMute, fontFamily: TOK.mono }}>personal</span>
        </div>
      </div>
    </aside>
  );
}

// ─── Top bar ───────────────────────────────────────────────────
function TopBar() {
  return (
    <header style={{
      height: 64, padding: '0 32px',
      display: 'flex', alignItems: 'center', gap: 16,
      borderBottom: `1px solid ${TOK.hairline}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 600, letterSpacing: -0.6 }}>Overview</h1>
        <span style={{ fontFamily: TOK.mono, fontSize: 11, color: TOK.textMute }}>
          May 2026 · last sync 2 min ago
        </span>
      </div>
      <div style={{ flex: 1 }} />
      {/* Search */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        height: 34, padding: '0 12px', borderRadius: 8,
        background: TOK.surface2, border: `1px solid ${TOK.hairline}`,
        width: 240,
      }}>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke={TOK.textMute} strokeWidth="2">
          <circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>
        </svg>
        <span style={{ fontSize: 13, color: TOK.textMute }}>Search subscriptions</span>
        <div style={{ flex: 1 }}/>
        <kbd style={{
          fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute,
          padding: '2px 5px', borderRadius: 3,
          background: TOK.surface3, border: `1px solid ${TOK.hairline}`,
        }}>⌘K</kbd>
      </div>
      {/* CTA */}
      <button style={{
        height: 34, padding: '0 14px',
        background: TOK.yellow, color: '#0a0a0b',
        border: 'none', borderRadius: 8,
        fontFamily: TOK.display, fontWeight: 600, fontSize: 13,
        display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
      }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <path d="M12 5v14M5 12h14"/>
        </svg>
        Add subscription
      </button>
    </header>
  );
}

// ─── Hero Spend card ───────────────────────────────────────────
function HeroSpend({ total, annual, spend }) {
  // Big metric, area chart filling background, KPIs along bottom
  return (
    <div style={{
      gridColumn: '1', gridRow: '1',
      position: 'relative',
      background: TOK.surface,
      borderRadius: 14, padding: 22,
      border: `1px solid ${TOK.hairline}`,
      overflow: 'hidden',
      height: 280,
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Yellow corner accent */}
      <div style={{
        position: 'absolute', top: 0, left: 0,
        width: 64, height: 1, background: TOK.yellow,
      }}/>
      <div style={{
        position: 'absolute', top: 0, left: 0,
        width: 1, height: 64, background: TOK.yellow,
      }}/>

      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textMute, letterSpacing: 1.4, textTransform: 'uppercase' }}>
            Total monthly spend
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 8 }}>
            <span style={{ fontFamily: TOK.display, fontWeight: 600, fontSize: 56, letterSpacing: -2, lineHeight: 1 }}>
              ${total.toFixed(0)}
              <span style={{ color: TOK.textDim, fontSize: 28, letterSpacing: -0.6 }}>.{(total.toFixed(2)).split('.')[1]}</span>
            </span>
            <span style={{
              fontFamily: TOK.mono, fontSize: 11, color: TOK.orange,
              padding: '3px 7px', borderRadius: 4,
              background: TOK.orangeSoft, border: `1px solid ${TOK.orange}40`,
            }}>+ 6.2% vs Apr</span>
          </div>
          <div style={{ fontFamily: TOK.mono, fontSize: 11, color: TOK.textDim, marginTop: 6 }}>
            ${annual.toFixed(0).toLocaleString()} projected annual · {SERVICES.length} services active
          </div>
        </div>

        <div style={{ display: 'flex', gap: 6 }}>
          {['1M','3M','6M','1Y','All'].map((p, i) => (
            <span key={p} style={{
              fontFamily: TOK.mono, fontSize: 11,
              padding: '4px 9px', borderRadius: 6,
              border: `1px solid ${i===3 ? TOK.yellow : TOK.hairline}`,
              color: i===3 ? TOK.yellow : TOK.textDim,
              background: i===3 ? TOK.yellowSoft : 'transparent',
            }}>{p}</span>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, position: 'relative', marginTop: 4 }}>
        <AreaChart
          w={820} h={170}
          padding={[8, 4, 28, 36]}
          months={spend.months}
          series={[{
            data: spend.data,
            color: TOK.yellow,
            width: 2,
            fill: 'url(#heroFill)',
          }]}
        />
        <svg width="0" height="0" style={{ position: 'absolute' }}>
          <defs>
            <linearGradient id="heroFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={TOK.yellow} stopOpacity="0.28" />
              <stop offset="100%" stopColor={TOK.yellow} stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </div>
  );
}

// ─── Category donut ────────────────────────────────────────────
function CategoryDonut({ catList, total }) {
  const segments = catList.map(c => ({ color: c.color, value: c.value }));
  const biggest = [...catList].sort((a,b) => b.value - a.value)[0];
  return (
    <div style={{
      background: TOK.surface,
      borderRadius: 14, padding: 22,
      border: `1px solid ${TOK.hairline}`,
      height: 280, position: 'relative',
      display: 'flex', flexDirection: 'column', gap: 14,
    }}>
      <div style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textMute, letterSpacing: 1.4, textTransform: 'uppercase' }}>
        Spend by category
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 18, flex: 1 }}>
        <div style={{ position: 'relative', width: 138, height: 138, flex: '0 0 auto' }}>
          <Donut segments={segments} size={138} thickness={16} />
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute, letterSpacing: 1 }}>TOP</div>
            <div style={{ fontSize: 14, fontWeight: 600, marginTop: 1 }}>{biggest.name}</div>
            <div style={{ fontFamily: TOK.mono, fontSize: 11, color: TOK.yellow, marginTop: 2 }}>
              ${biggest.value.toFixed(0)}/mo
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1, minWidth: 0 }}>
          {catList.sort((a,b) => b.value - a.value).map(c => (
            <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: c.color, flex: '0 0 auto' }} />
              <span style={{ fontSize: 12.5, flex: 1, minWidth: 0 }}>{c.name}</span>
              <span style={{ fontFamily: TOK.mono, fontSize: 11.5, color: TOK.text }}>
                ${c.value.toFixed(0)}
              </span>
              <span style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute, width: 38, textAlign: 'right' }}>
                {Math.round(c.value/total*100)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Categories strip ──────────────────────────────────────────
function CategoriesStrip({ catList }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
      {catList.map(c => {
        const services = SERVICES.filter(s => s.cat === c.id);
        return (
          <div key={c.id} onClick={() => window.__nav && window.__nav('category', c.id)} style={{
            background: TOK.surface,
            borderRadius: 12, padding: 16,
            border: `1px solid ${TOK.hairline}`,
            position: 'relative', overflow: 'hidden', cursor: 'pointer',
            display: 'flex', flexDirection: 'column', gap: 12,
            height: 152,
            transition: 'transform .15s, border-color .15s',
          }}>
            {/* corner tick */}
            <span style={{
              position: 'absolute', top: 12, right: 12,
              width: 6, height: 6, borderRadius: '50%', background: c.color,
              boxShadow: `0 0 10px ${c.color}90`,
            }} />

            <div>
              <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute, letterSpacing: 1.2, textTransform: 'uppercase' }}>
                {c.name}
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 6 }}>
                <span style={{ fontSize: 24, fontWeight: 600, letterSpacing: -0.6 }}>
                  ${c.value.toFixed(0)}
                </span>
                <span style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textDim }}>/mo</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: -8, alignItems: 'center' }}>
              {services.slice(0, 5).map((s, i) => (
                <div key={s.id} style={{
                  marginLeft: i === 0 ? 0 : -6,
                  border: `2px solid ${TOK.surface}`, borderRadius: 8,
                }}>
                  <Logo svc={s} size={26} />
                </div>
              ))}
              {services.length > 5 && (
                <div style={{
                  marginLeft: -6,
                  width: 26, height: 26, borderRadius: 7,
                  background: TOK.surface3, border: `2px solid ${TOK.surface}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontFamily: TOK.mono, fontSize: 10, color: TOK.textDim,
                }}>+{services.length - 5}</div>
              )}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textDim }}>
                {services.length} services
              </span>
              <span style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.yellow }}>view →</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Top services list ─────────────────────────────────────────
function TopServices({ top, total }) {
  return (
    <div style={{
      background: TOK.surface,
      borderRadius: 14, padding: 20,
      border: `1px solid ${TOK.hairline}`,
      display: 'flex', flexDirection: 'column', gap: 4,
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Most expensive</div>
          <div style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textMute, marginTop: 2 }}>
            ranked by monthly bill
          </div>
        </div>
        <span style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textDim }}>see all →</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 2 }}>
        <div style={{
          display: 'grid', gridTemplateColumns: '24px 1.5fr 1fr 80px 60px',
          gap: 12, padding: '4px 6px',
          fontFamily: TOK.mono, fontSize: 9.5, color: TOK.textMute,
          letterSpacing: 1, textTransform: 'uppercase',
        }}>
          <span>#</span><span>Service</span><span>Usage · 30d</span><span style={{textAlign:'right'}}>Monthly</span><span style={{textAlign:'right'}}>Share</span>
        </div>
        {top.map((s, i) => {
          const cat = CATEGORIES.find(c => c.id === s.cat);
          return (
            <div key={s.id} onClick={() => window.__nav && window.__nav('category', s.cat, s.id)} style={{
              display: 'grid', gridTemplateColumns: '24px 1.5fr 1fr 80px 60px', cursor: 'pointer',
              gap: 12, padding: '9px 6px', alignItems: 'center',
              borderTop: `1px solid ${TOK.hairline}`,
            }}>
              <span style={{ fontFamily: TOK.mono, fontSize: 11, color: TOK.textMute }}>0{i+1}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
                <Logo svc={s} size={28} />
                <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                  <span style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.2 }}>{s.name}</span>
                  <span style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute }}>
                    {cat.name.toLowerCase()} · {s.plan}
                  </span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Bar value={s.usage} w={70} h={4} color={s.usage > 0.5 ? TOK.yellow : TOK.orange} />
                <span style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textDim }}>
                  {Math.round(s.usage*100)}%
                </span>
              </div>
              <span style={{ fontFamily: TOK.mono, fontSize: 13, color: TOK.text, textAlign: 'right' }}>
                ${s.monthly.toFixed(2)}
              </span>
              <span style={{ fontFamily: TOK.mono, fontSize: 11, color: TOK.textMute, textAlign: 'right' }}>
                {(s.monthly/total*100).toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Idle subscriptions panel ──────────────────────────────────
function IdlePanel({ idle }) {
  const wasted = idle.reduce((s, x) => s + x.monthly, 0);
  return (
    <div style={{
      background: TOK.surface,
      borderRadius: 14, padding: 20,
      border: `1px solid ${TOK.hairline}`,
      display: 'flex', flexDirection: 'column',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* warning tape */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: `repeating-linear-gradient(90deg, ${TOK.orange} 0 8px, transparent 8px 16px)`,
      }}/>

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              fontFamily: TOK.mono, fontSize: 10, color: TOK.orange,
              padding: '2px 6px', borderRadius: 3,
              background: TOK.orangeSoft, border: `1px solid ${TOK.orange}55`,
              letterSpacing: 1, textTransform: 'uppercase',
            }}>idle</span>
            <span style={{ fontSize: 14, fontWeight: 600 }}>Paying for nothing</span>
          </div>
          <div style={{ fontFamily: TOK.mono, fontSize: 10.5, color: TOK.textMute, marginTop: 4 }}>
            usage below 20% in the last 30 days
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute, letterSpacing: 1 }}>WASTING</div>
          <div style={{ fontSize: 22, fontWeight: 600, color: TOK.orange, letterSpacing: -0.6 }}>
            ${wasted.toFixed(0)}<span style={{ fontSize: 12, color: TOK.textDim }}>/mo</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {idle.slice(0, 5).map(s => (
          <div key={s.id} onClick={() => window.__nav && window.__nav('category', s.cat, s.id)} style={{
            display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer',
            padding: '8px 0', borderTop: `1px solid ${TOK.hairline}`,
          }}>
            <Logo svc={s} size={26} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12.5, fontWeight: 500, lineHeight: 1.2 }}>{s.name}</div>
              <div style={{ fontFamily: TOK.mono, fontSize: 10, color: TOK.textMute }}>
                last used {Math.floor((1 - s.usage) * 60)}d ago
              </div>
            </div>
            <Bar value={s.usage} w={48} h={3} color={TOK.orange} bg={TOK.surface3} />
            <span style={{ fontFamily: TOK.mono, fontSize: 11.5, color: TOK.text, width: 50, textAlign: 'right' }}>
              ${s.monthly.toFixed(0)}
            </span>
            <span style={{
              fontFamily: TOK.mono, fontSize: 10,
              color: TOK.textDim,
              padding: '3px 7px', borderRadius: 4,
              border: `1px solid ${TOK.hairline}`,
              cursor: 'pointer',
            }}>cancel</span>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { DesktopCommand });
