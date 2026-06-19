# Design

## Theme
- **Background**: `#E4F4FD` (Soft Sky Blue)
- **Primary / Brand**: `#0369A1` (Navy Blue)
- **Hover / Active**: `#0284c7` (Medium Blue)
- **Border**: `#daeaf6` (Subtle light blue border)
- **Text (Ink)**: `#000000` (High contrast primary text)
- **Text Muted**: `#475569` (Medium slate gray)

## Palette (OKLCH Guidance)
- **Brand / Accent**: `oklch(48% 0.16 235)` (approx `#0369A1`)
- **Success**: `oklch(62% 0.19 145)` (approx `#16a34a`)
- **Warning**: `oklch(72% 0.18 70)` (approx `#f59e0b`)
- **Danger**: `oklch(52% 0.22 25)` (approx `#dc2626`)

## Typography
- **Font Family**: Inherited system sans-serif (Inter, Roboto, or SF Pro) for high density legibility.
- **Form Labels**: Bold, high contrast.
- **Metric Values**: Large (1.55rem), extra bold (800 weight), using `$cctl-navy` or `$cctl-blue`.

## Layout & Components
- **Bento Grid**: 12-column layout for dashboard stats.
- **Stat Cards**: 18px border radius, subtle hover translate (`translateY(-2px)`), clean linear gradient background from white to light gray.
- **Alert Badges**: Rounded capsules, colored text on soft background tints (e.g. `$cctl-red-soft` and darken `$cctl-red` for text).
