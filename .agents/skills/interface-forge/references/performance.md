# Performance and measurable budgets

## Core Web Vitals

Google's *good* field thresholds at the 75th percentile of page loads, segmented mobile/desktop:

- **LCP ≤2.5 seconds** (loading)
- **INP ≤200 milliseconds** (responsiveness)
- **CLS ≤0.1** (visual stability)

Source: https://web.dev/articles/vitals. A Lighthouse run or locally simulated metric isn't equivalent to field measurement; label lab results and field data separately. Low traffic may mean field data unavailable: report **Not measured** rather than pass.

## Project-specific budgets

Set explicit, realistic budgets based on devices/network/audience, e.g. initial route JS, image/video size, long tasks, third-party scripts, CSS, font loading, interactive readiness and page transition behavior. Baseline before rewriting code. Avoid universal budget numbers unbacked by project assumptions.

## Performance-first patterns

- Prioritize real hero image/primary content; do not lazy-load LCP image.
- Specify image dimensions / `aspect-ratio`, responsive formats and correct compression.
- Use font-display and fallbacks; avoid font proliferation and layout shift.
- Dynamically import heavy noncritical effects; avoid unnecessary client rendering.
- Virtualize large sets only when measured and when keyboard/AT semantics survive.
- Keep skeleton geometry similar to loaded content; prevent CLS from alerts, ads, errors, image decode.
- Debounce appropriate expensive interactions but don't delay important feedback.
- Avoid effects that compete with INP-critical controls or continuous GPU burn.
- Evaluate low-end Android and unreliable mobile networks when the audience warrants it.

## Measurement protocol

1. Define routes and representative flows; record versions, deployment environment, browser, device profile and network conditions.
2. Capture baseline lab trace (e.g. Lighthouse/DevTools) and field data where legitimately available.
3. Implement improvements; repeat like-for-like measurements; report distribution, not a single cherry-picked run.
4. Compare regressions across routes and states, particularly auth, hydrated screens and real data.
5. Record evidence and unresolved constraints in `.interface-forge/QA-REPORT.md`.

## Conditions for pass

Metric met in the appropriate measurement source and environment, or a documented team-approved exception. Without execution access or realistic data, report **Not run** or **Unknown**. Do not infer performance from using a particular framework or library.
