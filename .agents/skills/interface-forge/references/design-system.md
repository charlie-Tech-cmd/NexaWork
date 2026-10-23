# Design system, tokens, governance and migration

## Inventory existing patterns first

Look for design tokens in CSS variables, Tailwind configuration, CSS-in-JS theme, component APIs and documentation. Inventory duplicate colors/spacing, inconsistent labels, dialogs, buttons, fields, data tables, navigation and feedback patterns. Build a mapping from current classes/components to desired semantic roles before proposing replacements.

## Token taxonomy

1. **Foundations**: color scales, font families/weights, spacing scale, radius, elevation, z-index, breakpoint and motion primitives.
2. **Semantic**: background.canvas, background.surface, text.primary, text.secondary, border.subtle, action.primary, state.success, state.warning, state.danger, focus.ring.
3. **Component**: button.primary.background, input.focus.border, badge.warning.foreground, table.row.hover.

Names must express purpose rather than raw appearance (`text-primary` rather than `purple-500` for UI semantics). Support light/dark/high-contrast if the project needs them. Include state/focus/disabled roles and typography presets. Avoid token proliferation without usage.

## Reference token example (illustrative only)

```css
:root {
  --if-space-1: 0.25rem;
  --if-space-2: 0.5rem;
  --if-space-3: 0.75rem;
  --if-space-4: 1rem;
  --if-radius-control: 0.5rem;
  --if-color-surface: #ffffff;
  --if-color-text: #171717;
  --if-color-action: #3158c9;
  --if-color-focus: #174ab3;
}
```

These values are *not* a recommended palette. Reconcile with current brand and verify contrast in all states.

## Component contract

For each shared component define: purpose; variants; semantic HTML/ARIA; props/state and keyboard behavior; text behavior including localization; responsiveness; tokens and slots; async/error/disabled patterns; tests; misuse rules. Reuse existing accessible primitives unless their behavior is demonstrably inadequate.

## Documentation

Record principles, tokens, typography, spacing, grid/breakpoints, iconography, imagery, component states, motion policy, and accessibility/QA notes in `.interface-forge/DESIGN-SYSTEM.md`. Maintain a decision log for deliberate exceptions.

## Migration rules

- Add tokens without breaking all consumers immediately.
- Migrate a representative vertical slice and validate it before broad replacement.
- Preserve existing DOM semantics, focus behavior, API bindings, and analytics unless approved.
- Avoid global CSS resets or large dependency swaps mid-feature.
- Check visual regression in both light/dark contexts where applicable.
- Remove deprecated variants only after usage inventory and affected tests are updated.

## Sample review questions

Does every component inherit meaningfully from tokens? Are focus/error/disabled states equally considered? Is design-system centralization actually reducing variants, or hiding more one-offs inside configuration?
