---
name: Lime Graphite Glass
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1b1b1b'
  surface-container: '#20201f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353535'
  on-surface: '#e5e2e1'
  on-surface-variant: '#c6c9ab'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#909378'
  outline-variant: '#454932'
  surface-tint: '#b8d300'
  primary: '#ffffff'
  on-primary: '#2c3400'
  primary-container: '#d2f000'
  on-primary-container: '#5d6b00'
  inverse-primary: '#576500'
  secondary: '#c8c6c6'
  on-secondary: '#303030'
  secondary-container: '#474747'
  on-secondary-container: '#b6b5b4'
  tertiary: '#ffffff'
  on-tertiary: '#2f3131'
  tertiary-container: '#e3e2e2'
  on-tertiary-container: '#646464'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d2f000'
  primary-fixed-dim: '#b8d300'
  on-primary-fixed: '#191e00'
  on-primary-fixed-variant: '#414c00'
  secondary-fixed: '#e4e2e1'
  secondary-fixed-dim: '#c8c6c6'
  on-secondary-fixed: '#1b1c1c'
  on-secondary-fixed-variant: '#474747'
  tertiary-fixed: '#e3e2e2'
  tertiary-fixed-dim: '#c7c6c6'
  on-tertiary-fixed: '#1a1c1c'
  on-tertiary-fixed-variant: '#464747'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353535'
typography:
  headline-xl:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.03em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  gutter: 20px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style
The design system is a high-contrast, high-energy fusion of industrial precision and digital vibrancy. It targets a sophisticated audience of power users, developers, and creative technologists who demand both aesthetic edge and functional clarity.

The visual style is **Glassmorphism refined with Industrial Minimalism**. It utilizes deep, matte "Graphite" surfaces as a structural foundation, contrasted against "Lime Spark" accents that signify intelligence, activity, and progression. The emotional response is one of controlled intensity—dark, focused environments punctuated by electric, hyper-legible highlights. 

Key principles include:
- **Kinetic Energy:** Lime Spark is reserved for active states and "thinking" indicators, suggesting a living, breathing system.
- **Structural Depth:** Using "Liquid Glass" principles, the UI feels like layered sheets of dark mineral and etched glass.
- **Functional Contrast:** Extreme luminance gaps between background and foreground elements to ensure effortless scannability.

## Colors
The palette is dominated by the **Graphite** scale, providing a deep, matte canvas that absorbs light, allowing the **Lime Spark** to appear as if it is emitting light.

- **Primary (Lime Spark):** `#DFFF00`. Used for the most critical actions, primary buttons, and the "thinking" state of AI agents. It represents energy and the "go" signal.
- **Secondary (Graphite Medium):** `#2D2D2D`. Used for elevated surfaces, secondary containers, and component backgrounds.
- **Neutral (Graphite Dark):** `#1C1C1C`. The primary surface color for the main application chrome.
- **Base (Deep Matte):** `#0F0F0F`. The foundational background layer to maximize contrast.
- **Status Colors:** Use Lime Spark for positive/active states. Use a muted "Industrial Red" (#FF4B4B) only for critical errors. 
- **Glass Tint:** Semi-transparent layers should use a subtle Graphite tint with a Lime Spark specular highlight on the top edge.

## Typography
The typography strategy prioritizes technical precision. **Geist** provides a clean, Swiss-inspired neo-grotesque feel for headers and body text, while **JetBrains Mono** is used for metadata and labels to reinforce the "industrial" and "developer-centric" nature of this design system.

- **Scale:** Headlines use tight tracking and heavy weights to feel impactful against the dark background.
- **Monospace Accents:** All labels, tags, and status indicators must use JetBrains Mono in uppercase to create a distinct visual hierarchy from narrative content.
- **Color Application:** Headlines should be pure white (#FFFFFF). Body text should be off-white or light grey (#E0E0E0). Labels can utilize Lime Spark when indicating active status.

## Layout & Spacing
The design system employs a **Fluid-Fixed Hybrid Grid**. The sidebar and navigation elements are fixed-width to maintain structural integrity, while the main content area utilizes a fluid 12-column grid.

- **Rhythm:** A 4px base unit governs all padding and margins. Use 16px (md) for standard component spacing and 24px (lg) for section separation.
- **Glass Margins:** Floating glass panels should maintain a minimum of 8px margin from the screen edge on mobile and 24px on desktop.
- **Reflow:** On mobile, the 12-column grid collapses to a single column. Horizontal scrolling is permitted for "Graphite Plates" containing wide data tables or code blocks.

## Elevation & Depth
Depth is created through the **Liquid Glass** model, which avoids traditional fuzzy shadows in favor of luminosity and translucency.

1. **Base Level:** Matte Graphite (#0F0F0F). Solid, non-transparent.
2. **Plate Level:** Graphite Medium (#1C1C1C). Solid backing plates for primary content to ensure 100% legibility.
3. **Glass Level:** Layered blurs (Backdrop-filter: blur(20px)). Used for navigation bars, modals, and floating menus.
4. **Specular Highlights:** A 1px top-border with 20% opacity Lime Spark (#DFFF00) creates the illusion of a light source catching the edge of the glass.
5. **Thinking Glow:** When the agent is active, a subtle, 40px radius Lime Spark outer glow (opacity 10%) should emanate from the active panel.

## Shapes
The shape language is **Industrial/Architectural**. We use "Soft" corner radii (4px to 12px) to prevent the UI from feeling overly aggressive, while maintaining a structured, professional appearance.

- **Standard Elements:** 4px (0.25rem) for inputs, small buttons, and tags.
- **Containers:** 8px (0.5rem) for cards and main content areas.
- **Modals/Overlays:** 12px (0.75rem) to distinguish floating glass elements from the base grid.
- **No Pill Shapes:** Avoid fully rounded pill shapes to maintain the sophisticated, geometric aesthetic.

## Components
- **Buttons:** 
    - *Primary:* Solid Lime Spark (#DFFF00) background with Black (#000000) text. No shadow; high contrast.
    - *Secondary:* Transparent background with a 1px Graphite stroke (#2D2D2D) and White text.
- **Thinking State:** A pulsing, 2px wide Lime Spark ring around the agent's avatar or a linear "loading" bar at the top of the glass panel.
- **Input Fields:** Deep Graphite (#1C1C1C) background with a 1px bottom-border highlight in Lime Spark when focused. Monospaced text for input values.
- **Cards:** Solid Graphite backing plates with a subtle 1px specular highlight on the top edge. 
- **Chips/Tags:** JetBrains Mono font, uppercase. Graphite background with Lime Spark text for "active" or "success" states.
- **Scrollbars:** Ultra-thin (4px), Lime Spark thumb with no track background, appearing only on hover.