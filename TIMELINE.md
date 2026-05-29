# Data Source Timeline Audit
*Generated: 2026-05-29 — WALLET-02*

---

## Source Coverage

| Source | Oldest Record | Latest Record | Volume | Notes |
|--------|--------------|---------------|--------|-------|
| **BudgetBakers Wallet** | **2026-02-24** | 2026-05-29 | 581 fin. records | Bank sync (Air Bank + RB + PayPal) |
| **Gmail** (j.karleek@gmail.com) | ≥ 2025-05-18 | 2026-05-15 | 8,113 processed | Oldest *detected sub*; full inbox likely older |
| **Outlook** (jaroslav.karlik@live.com) | ≥ 2025-05-24 | 2026-05-15 | 9,188 processed | Oldest *detected sub*; full inbox likely older |
| **IMAP** (karlik@klikni.org) | 2024-12-22 | 2026-05-15 | 397 total / 212 processed | Directly verified via IMAP probe |

---

## Detected Subscriptions (existing DB)

| Source | Count | Oldest start_date |
|--------|-------|-------------------|
| Gmail | 50 | 2025-05-18 |
| Outlook | 55 | 2025-05-24 |
| IMAP | 2 | 2025-06-02 |
| Total | **107** | **2025-05-18** |

---

## Accounts in Wallet

| Account | Type | Currency | Records | Date Range |
|---------|------|----------|---------|------------|
| Air Bank Hlavní Účet | Bank (sync) | CZK | 466 | 2026-02-24 → 2026-05-28 |
| Raiffeisenbank Firemní Běžný | Bank (sync) | CZK | 192 | 2026-02-26 → 2026-05-27 |
| Air Bank Filip | Bank (sync) | CZK | 44 | 2026-02-27 → 2026-05-23 |
| PayPal CZK | Bank (sync) | CZK | 50 | 2026-03-01 → 2026-05-27 |
| PayPal USD | Bank (sync) | USD | 17 | 2026-03-04 → 2026-05-24 |
| Air Bank Spořicí Účet | Bank (sync) | CZK | 13 | 2026-02-28 → 2026-05-10 |
| PayPal EUR | Bank (sync) | EUR | 8 | 2026-03-01 → 2026-05-06 |
| Hotovost / RB osobní | Cash / Bank | CZK | 0 | — |

---

## Key Findings

### 1. Wallet is the limiting factor
The bank sync only imported history from **2026-02-24** (~3 months). This defines the cross-reference window — we can only confirm subs via fin. records from that date forward.

### 2. Email data is much richer
107 subs already detected, email history goes back at least to **2024-12-22** (IMAP) and likely 2020+ for Gmail/Outlook. This backlog is valuable for historical sub timeline even without wallet confirmation.

### 3. Composio API key expired
Key `ak_3IvGhy75LPRH99Y0_qIm` returns 401. Must be refreshed at [app.composio.dev/settings](https://app.composio.dev/settings) before next email sync cycle.

### 4. Already-processed email data
17,513 emails already processed (8,113 Gmail + 9,188 Outlook + 212 IMAP). 107 subs in DB. No re-processing needed for those — only future incremental syncs.

---

## Intersection & Strategy

```
Email history:    2024-12 ──────────────────────────────────── 2026-05
                                          ↑
Wallet history:                     2026-02-24 ──────────────── 2026-05
                                    ↑____________↑
                              CROSS-REFERENCE WINDOW (~3 months)
```

### For cross-referencing (wallet confirmation):
- Window: **2026-02-24 → today**
- All 581 wallet records will be matched against 107 existing subs
- New subs discovered via wallet during this window get high confidence immediately

### For email backfill (sub detection without wallet):
- Window: **2025-05-18 → today** (from existing processed data)
- Subscriptions detected here are "email-confirmed" but not "wallet-confirmed"
- They still appear in dashboard with lower confidence badge

### For discovery mode (new providers):
- Wallet recurring transactions with no sub match → email search last 3 days
- Grows KNOWN_PROVIDERS list dynamically

---

## Action Items Before WALLET-03

- [ ] **Renew Composio API key** at app.composio.dev/settings → update `.env` COMPOSIO_API_KEY
- [ ] Consider importing more historical wallet data (manual CSV import into BudgetBakers if available)
- [ ] Wallet data goes back further if Air Bank/RB have older export history to import

---
*Next task: WALLET-03 — FinancialRecord DB table + Alembic migration*
