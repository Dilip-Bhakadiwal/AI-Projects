# Implementation Plan: MarketPulse Institutional Terminal UI Enhancement

## Overview
We are organizing the MarketPulse Institutional Terminal design files from `stitch_marketpulse_liquid_glass_design.zip` into a clean, well-ordered folder structure (`ui/`), changing the HTML background from solid graphite to the provided Unsplash background image (`pietro-de-grandi-T7K4aEPoGGk-unsplash.jpg`), and fixing the left side panel (`<aside>`) specular hover effect so that it covers the entire panel from edge to edge without margin gaps.

## Architecture & UI Engineering Decisions
1. **Organized Folder Structure**:
   - Create `ui/` folder in the root workspace.
   - Copy `pietro-de-grandi-T7K4aEPoGGk-unsplash.jpg` into `ui/assets/bg-unsplash.jpg`.
   - Copy `DESIGN.md` and `screen.png` into `ui/`.
   - Create `ui/index.html` as the canonical production UI entry point (and sync changes back to `extracted_stitch_design/code.html`).
2. **Background Image Integration**:
   - Modify CSS `body` background styling to use `url('./assets/bg-unsplash.jpg') no-repeat center center fixed` with `background-size: cover`, while retaining `background-color: var(--surface-graphite)` as a fallback for accessibility and contrast.
   - Add a subtle dark overlay or backdrop blur if needed to preserve text readability (WCAG 4.5:1 contrast ratio) against the background image.
3. **Left Side Panel Hover Effect Fix**:
   - Currently, `.specular-highlight` is defined as `position: absolute; width: 100%; height: 100%;` without top/left coordinates. Inside the padded `<aside>` (`py-10 px-6`), it is constrained to the content box, leaving a 24px horizontal and 40px vertical margin around the hover glow.
   - Fix: Update `.specular-highlight` CSS to include `inset: 0; top: 0; left: 0; right: 0; bottom: 0;` and ensure `<aside>` has proper stacking context so that `--x` and `--y` mouse coordinates track across 100% of the panel area.

## Task List

### Phase 1: Foundation & Organization
- [ ] Task 1: Set up `ui/` directory structure and copy assets (`bg-unsplash.jpg`, `DESIGN.md`, `screen.png`).

### Phase 2: Core UI Modifications
- [ ] Task 2: Implement background image styling in `ui/index.html` with proper contrast fallback.
- [ ] Task 3: Fix left side panel (`<aside>`) `.specular-highlight` hover effect positioning and margin removal.
- [ ] Task 4: Sync updated UI code back to `extracted_stitch_design/code.html` for consistency.

### Phase 3: Verification & Quality Assurance
- [ ] Task 5: Verify WCAG accessibility, keyboard navigation, and responsive layout across breakpoints.
