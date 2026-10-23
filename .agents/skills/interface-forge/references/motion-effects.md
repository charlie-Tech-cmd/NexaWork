# Motion, shaders, interactions and graceful degradation

Motion must communicate state, spatial relationship, hierarchy, progress or product personality. Do not animate just because a library makes it easy.

## Policy

- **Utility/enterprise/trust-critical:** default static or low-intensity motion; fast, predictable feedback. Avoid blocking transactions or distracting data movement.
- **Marketing/portfolio/creative:** expressive effects can support a story but cannot obscure CTA, reading, loading or mobile operation.
- Reduce or eliminate nonessential motion under `prefers-reduced-motion: reduce`. Avoid vestibular triggers, forced parallax, flashing or large constant movement.
- Never make hover the only means to reveal information or perform an action. Provide keyboard/touch alternatives.
- All interactive content must remain accessible without canvas/WebGL/WebGPU; treat effects as enhancement layers.

## Choose the smallest sufficient technology

1. Static CSS for purely presentational results.
2. CSS transitions/keyframes for simple state/entrance feedback (respect reduced motion).
3. Existing framework animation dependency only when sequencing/gestures require it.
4. Dedicated motion primitive or shader library only for measured value, after evaluating bundle, compatibility, SSR, license and fallback.

Prefer transform and opacity where suitable to minimize main-thread/layout cost; avoid long-running animations on large page surfaces. Measure real devices. Default effects should not prevent selection, scrolling, zoom or accessibility tree interpretation.

## Library fit assessments (2026-10-18, recheck before installation)

- **Motion Primitives** (`ibelick/motion-primitives`): React/Tailwind reusable motion components. Repository identifies itself as beta. Useful when already within stack and tested; do not assume stable API.
- **Trickle UI Kit** (`akaieuan/trickle-UI-kit`): CSS-first text animations, SSR-safe focus; favor when restrained text effects add value. Verify reduced-motion behavior in actual copied component.
- **UI Layouts** (`ui-layouts/uilayouts`): component patterns including interaction effects. Inspect source, licenses and accessibility individually.
- **Cursify** (`ui-layouts/cursify`): custom cursor effects for pointer-rich experiential sites; default **off** for essential task flows, touch-only devices and users preferring reduced motion.
- **Paper Shaders** (`paper-design/shaders`): GPU texture/background effects, Apache-2.0 upstream at review; pin version (upstream warns of breaking changes), preserve notices if redistributing code. Use only when fallback/static background works.
- **Canvas UI** (`DavidHDev/canvas-ui`): visual HTML overlays/WebGL/WebGPU with experimental HTML-in-canvas behavior depending on browser. Preserve semantic DOM and test graceful fallback. License is MIT with Commons Clause condition, not unrestricted MIT.
- **Hyperiux** (`Hyperiux-Immersion-Labs/hyperiux-components`): free effects have a special Effects License; Pro effects are proprietary. Never bundle/copy Pro code or assume every effect is MIT.

## Motion specification template

| Element | Trigger | Purpose | Duration/easing | Reduced motion | Failure/fallback | Test |
|---|---|---|---|---|---|---|
| Filter chips | selection | feedback | brief transition | instant state | CSS unavailable → immediate change | keyboard/touch/zoom |

No magic fixed durations. Choose based on task, distance and device; measure perceived latency. Keep async progress truthful, never animate to conceal slow or stalled backends.

## Performance / compatibility gate

Document effect count, JS/CSS/GPU impact, entry LCP/CLS impact, memory on low-end device if testable, browser support, accessibility behavior, reduced motion, SSR/hydration, static fallback and copyright/license. Reject effects that do not justify their cost.
