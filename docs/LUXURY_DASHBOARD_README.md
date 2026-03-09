# WACH Insight — Luxury Dashboard

A world-class analytics dashboard featuring industrial luxury aesthetics, smooth animations, and context-aware AI.

## Features

### 🎨 Industrial Luxury Design
- **Deep Charcoal Theme**: Background color `#0F1115` for a premium, dark-mode aesthetic
- **Emerald & Gold Accents**: Emerald (`#10b981`) for health metrics, Gold (`#f59e0b`) for warnings
- **Glassmorphism**: Semi-transparent cards with backdrop blur (`backdrop-filter: blur(12px)`)
- **Noise Texture**: Subtle SVG noise overlay (opacity 0.03) for brushed metal feel

### ✨ Smooth Animations
- **Framer Motion**: 60FPS transitions for all interactive elements
- **Spring Physics**: Natural, bouncy animations using spring easing curves
- **Golden Thread Transition**: Health Index appears as background watermark, scales to dashboard position

### 📊 Smart Dashboard Components
1. **HealthGauge**: SVG Donut chart with dynamic colors based on health tier
2. **BentoCards**: Strategic Overview cards with summary and latest insight
3. **ExpandableMetricCard**: Scroll-to-enlarge plot system with sparkline preview
4. **FloatingChatButton**: Persistent AI chat widget with glass effect and pulse animation

### 🎯 Advanced Features
- **Scroll-Snap**: Soft CSS scroll-snap pulls headers to center
- **Parallax Plots**: Mouse-over 3D tilt effect on charts
- **Magnetic Buttons**: Subtle pull toward cursor when hovering buttons
- **Skeleton Shimmer**: Elegant loading states instead of spinning loaders

## Components

### Landing.jsx
Full-screen welcome page with:
- Mesh gradient background animation
- Staggered text reveal on load
- "Enter Dashboard" CTA with glow effect
- Golden Thread: Health Index as subtle background watermark

### HealthGauge.jsx
Health Index visualization with:
- SVG Donut chart that animates on load
- Dynamic colors: Emerald → Gold → Orange → Red based on health tier
- Centered number and tier label

### BentoCards.jsx
Strategic Overview cards with:
- Left: Health Summary (AI-generated)
- Right: Latest Insight (most recent data point)
- Glassmorphism effect with backdrop blur

### ExpandableMetricCard.jsx
Expandable metric cards with:
- Sparkline preview (always visible, lightweight)
- Expand for full interactive chart
- AI Analysis panel on expansion
- Key metrics sidebar

### FloatingChatButton.jsx
Persistent chat widget with:
- Glowing pulse animation when closed
- Spring animation on open/close
- Context-aware AI messages based on active section

## Usage

### Start the Development Server
```bash
# Terminal 1 - Backend
cd /Users/rdmasia/wach-insight
./start.sh

# Terminal 2 - Frontend
cd /Users/rdmasia/wach-insight/frontend
npm run dev
```

### View the Application
Open http://localhost:3000 in your browser

### Navigation Flow
1. **Landing Page**: Shows welcome screen with Health Index watermark
2. **Click "Enter Dashboard"**: Golden Thread animation to dashboard
3. **Dashboard View**: HealthGauge, BentoCards, ExpandableMetricCards
4. **Chat Button**: Floating AI chat in bottom-right corner

## Tech Stack

| Library | Purpose |
|---------|---------|
| React 18.3 | Component framework |
| Framer Motion | Smooth animations |
| Zustand | Global state management |
| Lenis (optional) | Smooth scrolling |

## CSS Variables

```css
:root {
  /* Backgrounds */
  --bg-base:        #0F1115;
  --bg-panel:       #171A21;
  --bg-elevated:    #1F232E;

  /* Accents */
  --emerald:        #10b981;
  --gold:           #f59e0b;

  /* Borders */
  --border:         #2A3040;
}
```

## File Structure

```
frontend/src/
├── components/
│   ├── Landing.jsx              # Welcome page
│   ├── HealthGauge.jsx          # SVG Donut chart
│   ├── BentoCards.jsx           # Strategic Overview cards
│   ├── ExpandableMetricCard.jsx # Scroll-to-enlarge plots
│   └── FloatingChatButton.jsx   # AI chat widget
├── lib/
│   ├── store.js                 # Zustand global state
│   └── summaryGenerator.js      # AI content generation
├── hooks/
│   └── useActiveSection.js      # Context-aware AI hook
└── index.css                    # Luxury theme + styles
```

## Performance Optimizations

1. **Lazy Loading**: Heavy charts only load when expanded
2. **Sparkline Previews**: Lightweight SVG sparklines for scroll
3. **Condition Rendering**: Only render expanded content when needed
4. **CSS Hardware Acceleration**: Transform/opacity for GPU acceleration

## Customization

### Change Health Thresholds
```javascript
// In HealthGauge.jsx
if (value >= 80) return '#10b981'; // Healthy
if (value >= 60) return '#f59e0b'; // Monitor
if (value >= 40) return '#f97316'; // Maintenance Soon
return '#ef4444'; // Critical
```

### Adjust Animation Speeds
```javascript
// In Framer Motion components
transition={{ type: 'spring', damping: 20, stiffness: 100 }}
// Increase damping for slower animation
```

### Modify Color Palette
```css
/* In index.css :root */
--emerald: #10b981;   /* Change to your brand color */
--gold:    #f59e0b;   /* Change to your secondary color */
```

## Build for Production

```bash
cd frontend
npm run build
```

Output:
- `dist/index.html` (0.68 kB)
- `dist/assets/index.css` (31.14 kB, 6.62 kB gzipped)
- `dist/assets/index.js` (772.88 kB, 226.68 kB gzipped)

## Troubleshooting

### Animation Jank
- Ensure all animated elements use `transform` and `opacity`
- Avoid animating layout properties like `width`, `height`

### Chart Not Loading
- Check browser console for API errors
- Ensure backend is running on port 8081

### Build Errors
```bash
# Clear cache and rebuild
rm -rf node_modules/.cache .vite
npm run build
```

## Future Enhancements

1. **Dark Mode Toggle**: Allow users to switch between light/dark themes
2. **Custom Themes**:让用户 define their own color palettes
3. **Data Export**: Download charts as PNG/PDF
4. **Real-time Updates**: WebSocket for live data streaming
5. **Device Comparison Mode**: Side-by-side device comparison

## Credits

- Design: Luxury dashboard patterns from Apple, Stripe, high-end automotive interfaces
- Icons: Custom SVG icons
- Charts: Recharts (planned migration)
