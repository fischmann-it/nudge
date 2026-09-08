# Swift and SwiftUI guidance

## Implementation

- Match the surrounding Swift style, including four-space indentation and
  existing naming conventions. Avoid sweeping renames or architecture migrations.
- Keep view bodies focused on presentation. Put reusable policy and update logic
  in the existing utilities or preference layer rather than duplicating it in views.
- Follow existing `AppState`, `@StateObject`, and `@EnvironmentObject` ownership.
  Do not introduce a second source of truth for shared application state.
- Perform UI state mutations on the main thread. Keep blocking file, network,
  and process work out of view rendering and the main thread where practical.
- Preserve availability checks and provide compatible behavior for the project's
  minimum macOS version. Do not adopt newer Observation or Swift concurrency
  features without checking deployment and compiler compatibility.
- Handle optional values and failures explicitly; avoid new force unwraps in
  configuration, network, or system-data paths.

## User interface and localization

- Check shared changes in both `SimpleMode` and `StandardMode`.
- Reuse the existing localization helpers and `Localizable.xcstrings`; preserve
  administrator-configurable text and language overrides.
- Account for longer translations, light/dark appearance, keyboard navigation,
  and accessible labels on controls.
- Keep existing AppKit integration when it controls macOS window or lifecycle
  behavior. Verify changes to activation, focus, deferral, and quit controls in
  the relevant demo/debug scheme.

## Tests

- Use the existing XCTest targets and add coverage for changed behavior rather
  than tests that simply duplicate implementation details.
- Prefer deterministic inputs for dates, OS versions, preferences, and feed data.
  Avoid tests that depend on the developer machine's update state or live feeds.
- Restore preference overrides and other shared state after tests to prevent
  order-dependent results.
- For policy changes, cover meaningful boundaries such as before/at/after a
  deadline, grace-period expiry, and supported/unsupported OS versions.
- Treat a successful build, unit tests, and manual UI inspection as distinct
  evidence; report only the checks actually performed.
