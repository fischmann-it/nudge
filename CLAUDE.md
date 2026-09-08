# Nudge — Claude Code instructions

This repository's agent instructions live in `AGENTS.md`, with topic-specific
guidance under `.agents/`. Claude Code imports them here so there is one source
of truth shared by every agent tool.

@AGENTS.md

## Claude Code specifics

- Read `.agents/swift-swiftui.md` before changing Swift code or the UI.
- Agent teams are the default for non-trivial parallel work so the operator can watch
  and steer teammates in real time. Use subagents only for fire-and-forget
  lookups where only the consolidated result matters. If agent teams appear
  unavailable, say so and ask the operator to verify before falling back.
- Execute prepared plans with `superpowers:subagent-driven-development`; do not
  offer inline execution unless the operator asks for it.
- Never commit or push unless asked. Work on a branch if on `main`.
