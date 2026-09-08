# Nudge agent instructions

## Project

Nudge is a native macOS application written in Swift and SwiftUI that encourages
users to install macOS updates. Work within the existing Xcode project and
architecture. The project currently uses Swift 5 language mode and a macOS 12.0
deployment target; check `Nudge.xcodeproj/project.pbxproj` before choosing APIs.
Do not raise these requirements unless the task calls for it.

Read [.agents/swift-swiftui.md](.agents/swift-swiftui.md) before changing Swift
code or the user interface. The `.agents/` folder holds repository-specific
guidance; this file is the entry point.

## Repository map

- `Nudge/UI/`: app entry point, shared UI, and simple/standard layouts.
- `Nudge/Utilities/`: preferences, update behavior, OS versions, logging, and UI logic.
- `Nudge/Preferences/`: preference structures and defaults.
- `Nudge/3rd Party Assets/`: SOFA and GDMF integration code.
- `Localizable.xcstrings`: localized strings.
- `NudgeTests/` and `NudgeUITests/`: XCTest targets.
- `Example Assets/` and `Schema/`: example configuration and management schema.
- `build_assets/`, `Nudge/Scripts/`, and `build_nudge.zsh`: deployment and packaging.

## Build and validation

Run commands from the repository root with a full Xcode installation selected:

```sh
xcodebuild -project Nudge.xcodeproj -scheme 'Nudge - Debug' -configuration Debug -destination 'platform=macOS' build
xcodebuild -project Nudge.xcodeproj -scheme 'Nudge - Debug' -destination 'platform=macOS' test
```

For focused unit validation, append `-only-testing:NudgeTests` or an individual
test identifier to the test command. The Debug scheme supplies `-unit-testing`
to its test action. Report toolchain or signing failures explicitly.

For UI verification, use the shared `Nudge - Debug (-demo-mode)` and
`Nudge - Debug (-demo-mode, -simple-mode)` schemes. Check both layouts and light
and dark appearances when a change affects shared UI. UI tests currently contain
commented-out launch tests, so passing that target alone does not verify visuals.

Use direct Xcode commands for routine validation. `build_nudge.zsh` is a release
workflow: it changes versions, switches Xcode with sudo, and can sign and package
artifacts. Run it only when release or packaging work is in scope.

Run checks appropriate to the change. Documentation-only edits need link and
diff checks, not an application build. State what was tested and any gaps.

## Working conventions

- Follow nearby code style and keep changes focused on the requested behavior.
- Preserve existing edits and avoid unrelated formatting or project-file churn.
- When adding Swift files, ensure they belong to the correct Xcode target.
- Keep preference names, defaults, decoding, examples, and schema consistent
  when configuration behavior changes.
- Preserve deferral, deadline, grace-period, and update behavior unless changing
  that behavior is part of the task. Add focused regression coverage for it.
- Keep generated build products, credentials, and machine-specific settings out
  of version control.

## Agent coordination

Prefer operator-visible agent teams for non-trivial parallel work so the operator can
watch and steer teammates. Use teams for cross-cutting research, multi-module
changes, and reviews that benefit from independent perspectives. Assign clear
ownership and tell teammates to preserve each other's changes.

If agent teams are unavailable or their required configuration appears missing,
say so and ask the operator to verify before falling back to subagents. Reserve subagents
for focused, fire-and-forget work where only the consolidated result matters.

When executing a prepared plan, use `superpowers:subagent-driven-development`.
Do not offer inline execution unless the operator explicitly requests it. Follow the
team-availability rule above if execution would require an unavailable capability.
