# Subscription Card - Visual Elements Guide

## Overview

This guide shows how each new UI element appears on subscription cards.

---

## 1. Expiration Warning Badges (Top-Right)

### Badge Examples

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                  ⚠ Renews in 3d ┃ <- Amber badge (expiring soon)
┃                     Annual     ┃
┃                     $180.00    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Expiring Soon (1-7 days)**
- Icon: ⚠ (warning emoji)
- Color: Amber/Yellow
- Text: "Renews in {days}d"
- Background: Amber-500 with 20% opacity
- Border: Amber-500 with 40% opacity
- Example: "⚠ Renews in 3d"

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                  🔴 Expired   ┃ <- Red badge (overdue)
┃                     Annual     ┃
┃                     $180.00    ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Expired (Overdue)**
- Icon: 🔴 (red circle emoji)
- Color: Red
- Text: "Expired"
- Background: Red-500 with 20% opacity
- Border: Red-500 with 40% opacity

---

## 2. Billing Cycle Progress Bar

### Visual Examples

**Early in cycle (15% complete):**
```
Billing cycle progress          15%
[#                                    ] <- Thin progress bar
```

**Mid-cycle (55% complete):**
```
Billing cycle progress          55%
[####################           ] <- Shows progress
```

**Near renewal (90% complete):**
```
Billing cycle progress          90%
[#########################################  ] <- Almost there
```

**Expiring soon (95% complete, amber/orange):**
```
Billing cycle progress          95%
[💥 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    ] <- Amber gradient
```

### Progress Bar Styling
- Height: 2px (thin, non-intrusive)
- Background: White with 10% opacity
- Active bar color:
  - **Normal**: Category gradient (e.g., blue to cyan for cloud)
  - **Expiring soon**: Amber to orange gradient
- Animation: Smooth width transition over 300ms
- Label: "Billing cycle progress" with percentage

---

## 3. Enhanced Next Billing Text

### Color-Coded Examples

```
Renews in 45 days      <- Gray text (>7 days away)
```

```
Renews in 5 days       <- Amber text (1-7 days away)
```

```
Renews in 1 day        <- Amber text (singular)
```

```
Renews tomorrow        <- Yellow text (renews in 1 day)
```

```
Renews today           <- Yellow text (renews today)
```

```
Expired                <- Red text (past renewal date)
```

### Color Reference
| State | Color | Hex | Use Case |
|-------|-------|-----|----------|
| > 7 days | Gray | gray-400 | Normal, plenty of time |
| 1-7 days | Amber | amber-400 | Warning, renewal approaching |
| Today | Yellow | yellow-400 | Action needed |
| Tomorrow | Yellow | yellow-400 | Action needed |
| Expired | Red | red-400 | Critical, overdue |

---

## 4. Pause Subscription Button

### Visual Appearance

```
              [Insights]
        Normal state: [   ⏸   ] <- Icon only, small circle
                        ^
                    8x8px icon
                    
Hover state:      [   ⏸   ] <- Slightly brighter
                   
```

### Button Details
- Shape: Circle (diameter 32px, 8x8 icon inside)
- Icon: ⏸ (pause emoji)
- Position: Right of "Insights" button
- Border: White with 20% opacity
- Background: White with 5% opacity (off state)
- Hover background: White with 10% opacity
- Icon color: White with 60% opacity
- Hover icon color: White (100% opacity)
- Tooltip: "Pause subscription"
- Transition: Smooth 300ms change

---

## 5. Full Card Example

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ 
┃ Netflix                           ⚠ Renews in 3d ┃
┃ 🎦 [ICON]                       Annual      ┃
┃                                     $180.00     ┃
┃ STREAMING                                       ┃
┃                                                  ┃
┃ $15.99                                           ┃
┃ per month                                        ┃
┃                                                  ┃
┃ Billing cycle progress         95%              ┃
┃ [#########################################   ]  ┃
┃                                                  ┃
┃ [─────────────────────────]            ┃
┃ monthly               active                     ┃
┃                                                  ┃
┃ Renews in 3 days                                ┃
┃                                   [⏸] [Insights] ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Card Layout
1. **Top-right**: Warning badges (if applicable)
2. **Top-right**: Annual cost
3. **Left side**: Icon/Logo
4. **Service name**: Large, bold text
5. **Category**: Small uppercase label
6. **Cost**: Large gradient text
7. **Billing cycle**: "per {cycle}"
8. **Progress bar**: (if not expired)
9. **Divider line**: Subtle separator
10. **Billing type & status**: Footer badges
11. **Renewal countdown**: Color-coded text
12. **Action buttons**: Pause + Insights

---

## Data Dependencies

These elements require:

```javascript
{
  next_billing_date: "2026-06-05T00:00:00",  // Required
  billing_cycle: "monthly",                   // daily|weekly|monthly|yearly
  status: "active"                           // active|idle|cancelled
}
```

### Fallback Behavior

If `next_billing_date` is missing or invalid:
- Progress bar: Hidden
- Warning badges: Hidden
- Countdown text: Hidden
- Other elements: Still display normally

---

## Responsive Behavior

### Mobile (375px)
- Badges stack vertically or appear inline
- Progress bar still visible
- Buttons stack horizontally
- All text remains readable

### Tablet (768px)
- Badges inline with annual cost
- Progress bar full width
- Buttons side-by-side

### Desktop (1200px+)
- All elements properly spaced
- Maximum readability
- Full design intention realized

---

## Animation States

### Progress Bar
- **Transition**: Width changes smoothly over 300ms
- **Easing**: ease-out (natural deceleration)
- **Trigger**: When progress percentage changes

### Hover Effects
- **Card**: Subtle scale up (1.05x)
- **Buttons**: Opacity and color change
- **Badges**: No hover effect (static)

---

## Accessibility Notes

- ✅ Color alone doesn't convey information (text labels present)
- ✅ Icon + text for buttons (pause emoji + title)
- ✅ Sufficient color contrast for WCAG AA
- ✅ Tooltips for icon-only buttons
- ✅ Readable at 200% zoom
