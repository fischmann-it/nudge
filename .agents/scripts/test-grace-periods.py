#!/Library/ManagedFrameworks/Python/Python3.framework/Versions/Current/bin/python3
"""Exercise the built macOS app with local fixtures and verify unified logs."""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import time
import uuid


def iso(timestamp):
    return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def logged_date(timestamp):
    return iso(timestamp).replace("T", " ").replace("Z", " +0000")


def feed(release_date, patch=9):
    versions = []
    for major in (26, 15):
        latest = {
            "ProductVersion": f"{major}.7.{patch}", "Build": "TEST",
            "ReleaseDate": release_date, "ExpirationDate": "2030-01-01T00:00:00Z",
            "SupportedDevices": [], "SecurityInfo": "https://support.apple.com/",
            "CVEs": {}, "ActivelyExploitedCVEs": [], "UniqueCVEsCount": 0,
        }
        security = {**latest, "UpdateName": "Simulation", "DaysSincePreviousRelease": 1}
        versions.append({"OSVersion": f"macOS {major}", "Latest": latest,
                         "SecurityReleases": [security], "SupportedModels": []})
    uma = {key: "test" for key in ("title", "version", "build", "apple_slug", "url")}
    ipsw = {key: "test" for key in ("macos_ipsw_url", "macos_ipsw_build",
                                  "macos_ipsw_version", "macos_ipsw_apple_slug")}
    return {
        "UpdateHash": "grace-period-test", "OSVersions": versions, "Models": {},
        "XProtectPayloads": {"com.apple.XProtectFramework.XProtect": "0",
                             "com.apple.XprotectFramework.PluginService": "0", "ReleaseDate": release_date},
        "XProtectPlistConfigData": {"com.apple.XProtect": "0", "ReleaseDate": release_date},
        "InstallationApps": {"LatestUMA": uma, "AllPreviousUMA": [], "LatestMacIPSW": ipsw},
    }


def stop(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def scenarios():
    cases = []
    for major in (15, 26):
        for mode in ("sofa", "static"):
            cases.append((f"{mode}-{major}-lifecycle", major, mode, [
                {"name": "first", "day": 0, "first": True},
                {"name": "before-expiry", "day": 13},
                {"name": "at-expiry", "day": 14},
                {"name": "after-expiry", "day": 15},
            ]))
    changes = {
        "tighter-deadline": {"deadline_day": 1},
        "target-version": {"patch": 10},
        "sla": {"sla": 7},
        "grace-settings": {"install": 168},
        "disabled": {"enabled": False},
    }
    for name, change in changes.items():
        for mode in ("sofa", "static"):
            cases.append((f"{mode}-{name}", 15, mode, [
                {"name": "first", "day": 0, "first": True},
                {"name": "changed", "day": 1, "changed": True, **change},
                {"name": "reverted", "day": 2, "ended": True},
            ]))
    for mode in ("sofa", "static"):
        cases.extend([
            (f"{mode}-disabled-first", 15, mode, [
                {"name": "disabled-first", "day": 0, "enabled": False},
                {"name": "enabled-same-event", "day": 1, "ended": True},
                {"name": "enabled-tighter-deadline", "day": 2, "deadline_day": 1, "ended": True},
                {"name": "reverted", "day": 3, "ended": True},
            ]),
            (f"{mode}-missing-recorded-marker", 15, mode, [
                {"name": "first", "day": 0, "first": True},
                {"name": "hidden-after-expiry", "day": 15, "hide_marker": True, "marker_unavailable": True},
                {"name": "restored-after-expiry", "day": 16, "restore_marker": True},
            ]),
            (f"{mode}-changed-while-marker-missing", 15, mode, [
                {"name": "first", "day": 0, "first": True},
                {"name": "hidden-changed", "day": 1, "hide_marker": True,
                 "marker_unavailable": True, "deadline_day": 1, "changed": True},
                {"name": "hidden-reverted", "day": 2, "marker_unavailable": True, "ended": True},
                {"name": "restored-reverted", "day": 3, "restore_marker": True, "ended": True},
            ]),
        ])
    cases.extend([
        ("ui-only", 15, "sofa", [
            {"name": "first", "day": 0, "first": True},
            {"name": "text-edit", "day": 1, "ui": True},
        ]),
        ("later-original-deadline", 15, "static", [
            {"name": "first", "day": 0, "first": True, "deadline_day": 20},
            {"name": "after-expiry", "day": 15, "deadline_day": 20},
        ]),
        ("first-seen-expired", 15, "sofa", [
            {"name": "first", "day": 15, "no_allowance": True},
        ]),
        ("new-deployment", 15, "static", [
            {"name": "first", "day": 0, "first": True},
            {"name": "changed", "day": 1, "changed": True, "deadline_day": 1},
            {"name": "new-marker", "day": 0, "first": True, "new_marker": True},
        ]),
        ("launch-delay", 15, "sofa", [{"name": "suppressed", "day": 0, "launch": 1}]),
        ("disabled", 15, "sofa", [{"name": "disabled", "day": 0, "enabled": False}]),
        ("missing-marker", 15, "sofa", [{"name": "missing", "day": 0, "missing": True}]),
        ("demo-bypass", 15, "sofa", [{"name": "demo", "day": 0, "demo": True}]),
    ])
    return cases


def run_step(app, directory, bundle_id, marker, birth, major, mode, stage):
    directory.mkdir()
    base = int(birth) + 1
    now = base + stage["day"] * 86400
    deadline = base + stage.get("deadline_day", 2) * 86400
    patch = stage.get("patch", 9)
    sla = stage.get("sla", 14)
    install = stage.get("install", 336)
    launch = stage.get("launch", 0)
    sofa = directory / "sofa.json"
    # Keep the resolved deadline stable for SLA-only edits, isolating fingerprint changes.
    sofa.write_text(json.dumps(feed(iso(deadline - sla * 86400), patch)))
    config = {
        "optionalFeatures": {
            "utilizeSOFAFeed": mode != "static", "customSOFAFeedURL": sofa.as_uri(),
            "refreshSOFAFeedTime": -1,
            "attemptToCheckForSupportedDevice": False, "disableNudgeForStandardInstalls": False,
            "attemptToFetchMajorUpgrade": False, "disableSoftwareUpdateWorkflow": True,
            "aggressiveUserExperience": False, "aggressiveUserFullScreenExperience": False,
            "attemptToBlockApplicationLaunches": False, "terminateApplicationsOnLaunch": False,
        },
        "osVersionRequirements": [{
            "targetedOSVersionsRule": "default",
            "requiredMinimumOSVersion": f"{major}.7.{patch}" if mode == "static" else "latest-minor",
            "requiredInstallationDate": iso(deadline),
            "standardMinorUpdateSLA": sla, "nonActivelyExploitedCVEsMinorUpdateSLA": sla,
            "activelyExploitedCVEsMinorUpdateSLA": sla,
        }],
        "userExperience": {
            "allowGracePeriods": stage.get("enabled", True), "gracePeriodInstallDelay": install,
            "gracePeriodLaunchDelay": launch,
            "gracePeriodPath": str(directory / "missing") if stage.get("missing") else str(marker),
            "randomDelay": False, "loadLaunchAgent": False, "noTimers": True,
        },
    }
    if mode != "static":
        del config["osVersionRequirements"][0]["requiredInstallationDate"]
    if stage.get("ui"):
        config["userInterface"] = {"updateElements": [{"_language": "en", "mainContentText": "Changed simulation text"}]}
    config_path = directory / "config.json"
    config_path.write_text(json.dumps(config, indent=2))
    command = [str(app / "Contents/MacOS/Nudge"), "-json-url", config_path.as_uri(),
               "-simulate-os-version", f"{major}.7.8", "-simulate-date", iso(now),
               "-disable-random-delay"]
    if stage.get("demo"):
        command.append("-demo-mode")
    expected = []
    forbidden = []
    if stage.get("demo"):
        expected.append("Grace periods bypassed - demo mode is enabled")
    elif stage.get("missing"):
        expected.append("not found or unable to get creation date")
    elif not stage.get("enabled", True):
        expected.append("Grace periods bypassed - allowGracePeriods is false")
    else:
        expected.append("currentDate: " + logged_date(now))
        if launch:
            expected.append("within gracePeriodLaunchDelay")
        elif stage.get("changed"):
            expected.append("Installation grace ended - update requirements changed")
        elif stage.get("ended"):
            expected.append("Installation grace remains ended for this deployment")
        elif stage.get("no_allowance"):
            expected.append("First grace-period event has no installation allowance")
        else:
            effective = max(deadline, birth + (install + launch) * 3600)
            if stage.get("first"):
                expected.append("Recorded first grace-period event - installation deadline: " + logged_date(effective))
            expected.append("Applying first-event grace deadline - original: " + logged_date(deadline)
                            + ", effective: " + logged_date(effective))
    if stage.get("marker_unavailable"):
        expected.append("Grace period marker unavailable - using recorded creation date: " + logged_date(birth))
    if stage.get("changed") or stage.get("ended") or stage.get("no_allowance") or not stage.get("enabled", True):
        forbidden.append("Applying first-event grace deadline")
    if mode != "static" and not stage.get("demo"):
        expected.extend(["Setting requiredInstallationDate via SOFA to " + logged_date(deadline),
                         f"SOFA Matched OS Version: {major}.7.{patch}"])
    manifest = {"command": command, "bundleID": bundle_id, "markerBirthTime": birth,
                "expected": expected, "forbidden": forbidden,
                "markerPresent": marker.exists(), "stage": stage}
    (directory / "case.json").write_text(json.dumps(manifest, indent=2))
    log_path = directory / "unified.log"
    process = logger = None
    try:
        with log_path.open("w") as logs, (directory / "app.log").open("w") as output:
            logger = subprocess.Popen(["/usr/bin/log", "stream", "--style", "ndjson", "--level", "info",
                                       "--predicate", f'subsystem == "{bundle_id}"'],
                                      stdout=logs, stderr=subprocess.STDOUT)
            time.sleep(0.5)
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                       env={**os.environ, "OS_ACTIVITY_DT_MODE": "YES"})
            end = time.monotonic() + 20
            while time.monotonic() < end:
                text = log_path.read_text()
                if all(fragment in text for fragment in expected):
                    break
                time.sleep(0.2)
            text = log_path.read_text()
            missing = [fragment for fragment in expected if fragment not in text]
            unexpected = [fragment for fragment in forbidden if fragment in text]
            if missing or unexpected:
                raise AssertionError(f"{directory.parent.name}/{stage['name']}: missing {missing}; unexpected {unexpected}")
            print(f"PASS {directory.parent.name}/{stage['name']}", flush=True)
    finally:
        stop(process)
        stop(logger)
        # Preserve the domain between stages; export it as diagnostic evidence.
        result = subprocess.run(["/usr/bin/defaults", "export", bundle_id, "-"], capture_output=True)
        (directory / "preferences.plist").write_bytes(result.stdout)


def run_case(source, root, case):
    name, major, mode, stages = case
    directory = root / name
    directory.mkdir()
    app = directory / "Nudge.app"
    shutil.copytree(source, app, symlinks=True)
    bundle_id = "com.github.macadmins.Nudge.simulation." + uuid.uuid4().hex
    info = app / "Contents/Info.plist"
    with info.open("rb") as stream:
        plist = plistlib.load(stream)
    plist["CFBundleIdentifier"] = bundle_id
    with info.open("wb") as stream:
        plistlib.dump(plist, stream)
    marker = directory / "marker"
    marker.touch()
    birth = marker.stat().st_birthtime
    hidden_marker = directory / "hidden-marker"
    try:
        subprocess.run(["/usr/bin/codesign", "--force", "--deep", "--sign", "-", str(app)],
                       check=True, capture_output=True)
        for index, stage in enumerate(stages, 1):
            if stage.get("new_marker"):
                marker = directory / f"marker-{index}"
                marker.touch()
                birth = marker.stat().st_birthtime
            if stage.get("hide_marker"):
                marker.rename(hidden_marker)
            if stage.get("restore_marker"):
                hidden_marker.rename(marker)
                if marker.stat().st_birthtime != birth:
                    raise AssertionError("Restoring the marker changed its creation date")
            run_step(app, directory / f"{index:02}-{stage['name']}", bundle_id, marker, birth, major, mode, stage)
    finally:
        subprocess.run(["/usr/bin/defaults", "delete", bundle_id], capture_output=True)
        for parent in ("Application Support", "Caches", "Saved Application State"):
            suffix = ".savedState" if parent == "Saved Application State" else ""
            path = Path.home() / "Library" / parent / (bundle_id + suffix)
            if path.exists():
                shutil.rmtree(path)
        shutil.rmtree(app)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, help="Built Debug Nudge.app (never the installed production app)")
    parser.add_argument("--case", help="Run one named scenario, including all its relaunch stages")
    args = parser.parse_args()
    source = args.app.resolve()
    if not (source / "Contents/MacOS/Nudge").is_file():
        parser.error("Expected a built Nudge.app")
    root = Path(tempfile.mkdtemp(prefix="nudge-grace-simulations-"))
    print(f"Artifacts: {root}", flush=True)
    selected = [case for case in scenarios() if args.case is None or args.case == case[0]]
    if not selected:
        parser.error("Unknown case")
    failures = []
    for case in selected:
        try:
            run_case(source, root, case)
        except Exception as error:
            failures.append(str(error))
            print(f"FAIL {error}", flush=True)
    (root / "results.json").write_text(json.dumps({"cases": len(selected), "failures": failures}, indent=2))
    print(f"{len(selected) - len(failures)}/{len(selected)} passed; artifacts: {root}", flush=True)
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
