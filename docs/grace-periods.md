# Grace periods and SOFA deadlines

Nudge evaluates grace periods after SOFA has selected the required OS version
and calculated its installation deadline. An explicit `requiredInstallationDate`
takes precedence over SOFA's calculated deadline. Configure grace-period settings
under `userExperience`.

## First-event installation grace

With `allowGracePeriods` enabled, the first event observed for a deployment can
receive a fixed installation deadline. The marker at `gracePeriodPath` must be
present and younger than `gracePeriodInstallDelay` hours when that event is first
observed. A launch without a resolved update target does not consume that event.
Nudge uses the file's **creation date**, not its modification date.

The effective first-event deadline is the later of:

- The event's original configured or SOFA-derived deadline.
- Marker creation time plus `gracePeriodInstallDelay + gracePeriodLaunchDelay` hours.

This can extend a future deadline as well as one that has already passed. It
never shortens a later original deadline. The launch delay remains part of the
combined allowance: the default 23-hour install delay and 1-hour launch delay
produce a deadline 24 hours after marker creation. With a zero launch delay,
a 336-hour install delay gives 14 days from marker creation.

Nudge saves this first event and its deadline in the user's preferences under
`firstRunGracePeriodState`. Relaunching does not move the deadline. The saved date
continues to apply after the marker reaches the install-delay age, including
when that saved deadline is overdue. If the marker subsequently becomes
unavailable, Nudge logs a warning and uses its recorded creation date for this
same event; it does not silently restore the earlier event deadline.

A first launch after the marker has already aged out receives no installation
grace. The existing deadline is used. The allowance cannot be acquired later
by changing the configuration or relaunching.

## Later events and configuration changes

Once Nudge observes a changed update requirement, the installation allowance ends
for that deployment. Nudge honors the new configured or SOFA deadline, including
an urgent deadline earlier than the original allowance. Reverting the change
does not bring the allowance back.

Changes that end the allowance include:

- The resolved required OS version, including a new SOFA `latest-minor` target.
- The configured OS target or the original/configured installation deadline,
  even when the required OS version stays the same.
- An update SLA, minor-version recalculation threshold, or switching SOFA use.
- The install or launch grace delay. Disabling grace also ends the allowance;
  enabling it later for an already-observed disabled first event does not grant it.

Text, appearance, and unrelated preference edits do not end installation grace.
Reinstalling an identical profile is not a new event. Nudge compares effective
update requirements rather than file formatting or profile installation time.

A recreated marker with a new creation date, or a new marker path, identifies a
new deployment and can establish a new first event. Merely touching an existing
file does not reset its creation date. State is per user, like existing Nudge
deferral preferences; deleting that state removes its history. Older releases
stored the previous target version but not the original deadline. On upgrade,
a known different previous target prevents a fresh allowance, but historical
deadline-only changes cannot be reconstructed.

## Launch suppression

`gracePeriodLaunchDelay` still suppresses Nudge's normal UI while the marker's
age in whole hours is less than that delay. This is separate from installation
grace and remains in effect even if a later event has ended the installation
allowance. Nudge records the first event before exiting during launch grace.
A zero launch delay disables this suppression. Demo mode bypasses grace-period
state and ignores external configuration.

## Example

Assume a marker created August 18 at midnight UTC, `gracePeriodInstallDelay = 336`,
`gracePeriodLaunchDelay = 0`, and an initial SOFA deadline of August 20 at midnight.
The first launch occurs August 18.

| Subsequent launch or change | Effective deadline |
| --- | --- |
| First launch August 18 | September 1 |
| Same event, August 25 | September 1 |
| Same event, September 1 | September 1 |
| Same event, September 2 | September 1, now overdue |
| Admin changes deadline to August 25 for the same OS version | August 25; first-event installation grace ends |
| Admin reverts the deadline to August 20 | August 20; the ended allowance does not return |

If the original deadline were September 10 instead, the unchanged first event
would keep September 10. Grace never brings a later deadline forward.

## Diagnosing a deployment

Capture unified logs while launching Nudge:

```sh
/usr/bin/log stream --style compact --level info \
  --predicate 'subsystem == "com.github.macadmins.Nudge"'
```

The decision logs explain both the original and effective dates:

- `Evaluating grace periods`: evaluation time, original deadline, marker path and
  creation date, age, and configured delays.
- `Recorded first grace-period event`: the fixed installation deadline saved.
- `Applying first-event grace deadline`: original and effective deadlines,
  including on launches after the marker ages out.
- `Installation grace ended - update requirements changed`: a newly observed
  event takes precedence over the initial allowance.
- `Installation grace remains ended for this deployment`: a later launch cannot
  restart an allowance that has ended.
- `First grace-period event has no installation allowance`: the first event was
  ineligible or an earlier event is already known.
- `within gracePeriodLaunchDelay`: Nudge exits during launch suppression.
- `Grace periods bypassed`: grace is disabled or demo mode is active.

A missing marker without recorded state produces an error. An unavailable marker
with recorded state produces a warning. Unreadable saved state produces an error
and uses the event's original deadline, without granting a fresh allowance.

To inspect intended settings, use `-print-profile-config` and
`-print-json-config`. Profile settings take precedence over JSON, and keys must
be in the correct dictionary. To reproduce behavior, use the
[configuration and simulation workflow](../.agents/simulation-testing.md).
