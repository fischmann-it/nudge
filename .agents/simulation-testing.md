# Configuration and command-line simulation tests

Use real Debug app launches in addition to unit tests when changing deadline,
grace-period, SOFA, preference, or startup behavior. Confirm decisions in unified
logs, not only the visible UI or the process exit status.

## Build and run the grace-period matrix

From the repository root, select full Xcode for the command without changing the
machine's selected developer directory:

```sh
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcodebuild -project Nudge.xcodeproj -scheme 'Nudge - Debug' \
  -configuration Debug -destination 'platform=macOS' \
  -derivedDataPath /tmp/nudge-simulation-build build

./.agents/scripts/test-grace-periods.py \
  /tmp/nudge-simulation-build/Build/Products/Debug/Nudge.app
```

Install MacAdmins Python first; the runner uses its framework shebang rather than
an interpreter selected from `PATH`. The Python standard-library runner creates local JSON configuration and SOFA
fixtures, copies the built app with framework symlinks preserved, gives each
copy a unique bundle identifier, and signs that copy ad hoc. It does not modify
the source app or production Nudge preferences. It captures unified logs at info
level with a predicate for the temporary bundle identifier before launching each
case. Keep a logged-in macOS desktop session available; these are real app launches
and windows may appear briefly.

The matrix covers simulated macOS 15 and 26 with both static and SOFA deadlines.
Lifecycle scenarios reuse one app copy, bundle identifier, marker, and preference
domain across launches. They verify a fixed first-event deadline before and after
the 14-day installation allowance expires, including the first representable
whole-second launch at expiration. Unit tests cover exact fractional boundaries.
Other scenarios change the deadline, target version, SLA, grace settings, or enable
flag and then revert the configuration to prove an ended allowance cannot return.
Text-only edits retain the allowance; a new deployment marker can receive a new
allowance. Later original deadlines, first launches after expiration, launch grace,
disabled grace, missing markers, and demo bypass are also covered. A disabled
first launch must prevent a later opt-in for the same marker. Recorded-marker
scenarios physically move the original marker away and restore it without changing
its path or birth date: unchanged events retain their deadline after expiry, while
requirements changed during absence permanently revoke the allowance even if the
configuration and marker are later restored. These differ from an initially
missing marker, for which no deployment creation date has been recorded.

The policy expectation is a first-event deadline of the later of the original
deadline and marker creation plus installation and launch delays. The first event
must be observed while the marker is younger than the installation delay to gain
an allowance. The saved deadline remains stable after the marker ages out; changed
update requirements end that allowance permanently for this deployment.

For a focused rerun:

```sh
./.agents/scripts/test-grace-periods.py \
  /tmp/nudge-simulation-build/Build/Products/Debug/Nudge.app \
  --case sofa-15-lifecycle
```

The printed temporary artifact directory contains a subdirectory per scenario
and numbered launch stage. Each stage retains `config.json`, `sofa.json`,
`case.json` (exact command, bundle identifier, marker birth time, expected and
forbidden log fragments), `unified.log`, `app.log`, and `preferences.plist`.
The root contains `results.json`. Every stage starts a fresh log capture after
the preceding app process has stopped, so previous decisions cannot satisfy
later assertions.
The runner stops only its own processes and removes only its temporary app copies
and their unique preference/cache domains. Preserve artifacts when diagnosing a
failure; keep them out of version control. Report failures explicitly.

## Manual simulations and caveats

The underlying invocation is:

```sh
/path/to/test-copy/Nudge.app/Contents/MacOS/Nudge \
  -json-url file:///absolute/path/config.json \
  -simulate-os-version 15.7.8 \
  -simulate-date 2026-08-18T00:00:00Z \
  -disable-random-delay
```

- Use ISO 8601 UTC dates. Verify the evaluation log actually uses that date;
  accepting the command-line argument alone does not prove a code path uses it.
  Grace-period evaluation uses `DateManager().getCurrentDate()` unless a unit test
  explicitly supplies a date. New policy code should use this same clock rather
  than calling `Date()` directly.
- `-simulate-os-version` simulates policy input, not a different macOS runtime.
  It cannot validate API availability or OS-specific window activation behavior.
- Do not combine `-demo-mode` or `-unit-testing` with configuration behavior tests:
  those modes ignore external configuration. Use demo mode only for its own
  bypass case or visual checks.
- Use a local SOFA fixture via `optionalFeatures.customSOFAFeedURL` with a `file://`
  URL and omit `requiredInstallationDate` when testing SOFA deadline calculation;
  an explicit date takes precedence. A unique bundle identifier prevents a previously cached feed or managed
  profile from masking the intended fixture. For repeated launches, set
  `optionalFeatures.refreshSOFAFeedTime` to `-1` so cached feeds cannot hide
  changes in fresh per-stage fixtures. Other app startup paths may still
  consult system services; do not claim these are fully isolated OS tests.
- Disable random delay, LaunchAgent management, software-update downloads,
  application blocking/termination, and aggressive UI in test configuration.
  Do not delete production preferences or caches to make a test pass.
- Marker **creation time** matters. `touch` on an existing marker does not reset
  it. The runner creates a new marker and derives simulated dates from its actual
  birth time. Unit tests exercise exact before/at/after boundaries with injected dates.
- Test disabled and error paths as well as successful extensions. Check both
  configured and SOFA-derived deadlines, and retain the existing deadline policy
  unless a behavior change is explicitly in scope.
