from command_expectations import runtime_command
import inspect
import io
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Composes the two renderers the way run_doctor does, so a test can assert on the whole transcript
def render_doctor_report(report):
    return monitor.render_doctor_sections(report) + "\n" + monitor.render_doctor_summary(report.checks)


# Builds the minimal advice a WARN or FAIL row is required to carry
def actionable_advice():
    return monitor.make_recovery_advice("unknown", "a summary", "do the thing", False)


CLI_PATH = PROJECT_ROOT / "spotify_monitor.py"
ISOLATED_PRELUDE = "import requests, runpy, socket, sys; requests.sessions.Session.request = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network request attempted')); socket.create_connection = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network connection attempted')); "


# Provides one in-memory stream that behaves like an interactive terminal
class TTYBuffer(io.StringIO):
    # Reports interactive terminal capability for progress rendering
    def isatty(self):
        return True


# Runs an isolated doctor CLI scenario with real network access blocked
def run_cli(arguments, runtime_setup=""):
    source = f"module = runpy.run_path({str(CLI_PATH)!r}, run_name='spotify_monitor_phase3_test'); runtime = module['main'].__globals__; runtime['sys'].argv = {[str(CLI_PATH), *arguments]!r}; runtime['CLEAR_SCREEN'] = False; {runtime_setup} module['main']()"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-c", ISOLATED_PRELUDE + source], cwd=PROJECT_ROOT, capture_output=True, text=True, env=environment, timeout=30, check=False)


# Creates one valid buddy-list response for a selected target
def buddy_list(target="friend.user"):
    return {"friends": [{"user": {"uri": f"spotify:user:{target}", "name": "Friend"}, "track": {"artist": {"name": "Artist"}, "album": {"name": "Album", "uri": "spotify:album:a"}, "context": {"name": "Album", "uri": "spotify:album:a"}, "name": "Track", "uri": "spotify:track:t"}, "timestamp": 1700000000000}]}


# Configures a valid offline cookie-mode doctor baseline
def configure_valid_doctor(monkeypatch, target="friend.user"):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "fake-cookie")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "your_spotify_app_client_id")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "your_spotify_app_client_secret")
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "SPOTIFY_ERROR_INTERVAL", 180)
    monkeypatch.setattr(monitor, "SPOTIFY_INACTIVITY_CHECK", 660)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_ACTIVE_CHECK_INTERVAL", 10)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_ERROR_INTERVAL", 60)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_INACTIVITY_CHECK", 180)
    monkeypatch.setattr(monitor, "SPOTIFY_DISAPPEARED_CHECK_INTERVAL", 180)
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "MONITOR_LIST_FILE", "")
    monkeypatch.setattr(monitor, "CSV_FILE", "")
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", True)
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "INACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "TRACK_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "SONG_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "SONG_ON_LOOP_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_INACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_TRACK_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_SONG_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_SONG_ON_LOOP_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "TRACK_SONGS", False)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "fake-access-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: buddy_list(target))
    monkeypatch.setattr(monitor, "check_internet", lambda **kwargs: True)


# Returns a dependency finder that reports every module as installed
def all_dependencies_present(name):
    return object()


# Returns required advice after asserting one check carries it
def require_advice(check):
    assert check.advice is not None
    return check.advice


# Verifies section rendering uses explicit ASCII status markers and a summary
def test_report_markers_and_sections(monkeypatch):
    configure_valid_doctor(monkeypatch)
    report = monitor.build_doctor_report("friend.user", spec_finder=all_dependencies_present)
    rendered = render_doctor_report(report)
    for section in ("Environment", "Configuration", "Authentication", "Metadata", "Connectivity", "Target", "Notifications", "Summary"):
        assert section in rendered
    assert "[PASS]" in rendered
    assert "All checks passed. You are good to go!" in rendered
    assert f"Guide: {monitor.DOCTOR_GUIDE_URL}" in rendered
    assert "ASCII_LOG_SEPARATORS resolves" not in rendered


# Verifies the preflight notice reaches the user before any check runs rather than inside the report
def test_preflight_notice_precedes_the_report(monkeypatch, capsys):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "build_doctor_report", lambda *args, **kwargs: monitor.DoctorReport([monitor.make_doctor_check("Environment", "PASS", "ok")]))
    monitor.run_doctor()
    output = capsys.readouterr().out
    assert "Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval." in output
    assert output.index("Running preflight checks.") < output.index("Doctor\n")


# Verifies scrobble health mode names the one file Doctor may update
def test_preflight_notice_names_the_scrobble_health_write(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "MONITOR_MODE", "scrobble_health")
    monitor.render_doctor_notice()
    assert "A rotated Spotify recent-play refresh token may be updated in the selected dotenv file." in capsys.readouterr().out


# Verifies the install method is stated as context instead of a check that can never fail
def test_report_states_the_install_method_without_a_marker():
    report = monitor.DoctorReport([monitor.make_doctor_check("Environment", "PASS", "Python 3.12.0 is supported")])

    rendered = render_doctor_report(report)

    assert f"Doctor\nDetected install method: {monitor._wizard_install_method()}\n" in rendered
    assert "[PASS] Install method" not in rendered


# Verifies disabled output destinations are stated rather than left out of the report
def test_report_names_disabled_output_destinations(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "CSV_FILE", "")
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", True)

    rendered = render_doctor_report(monitor.build_doctor_report("friend.user", spec_finder=all_dependencies_present))

    # The labels say everything, so neither row carries a detail that only repeats them
    assert "[PASS] CSV logging is disabled\n[PASS] Output logging is disabled\n" in rendered


# Verifies Doctor visually attaches explanatory details to their check rows
def test_report_indents_check_details():
    report = monitor.DoctorReport([monitor.make_doctor_check("Configuration", "PASS", "Log destination appears writable", "Path: spotify_monitor")])

    rendered = render_doctor_report(report)

    assert "[PASS] Log destination appears writable\n  Path: spotify_monitor" in rendered


# Verifies reports omit sections that have no checks
def test_report_omits_empty_sections():
    report = monitor.DoctorReport([monitor.make_doctor_check("Scrobble health", "PASS", "Spotify recent-play access succeeded")])
    rendered = render_doctor_report(report)
    assert "\nScrobble health\n" in rendered
    for section in ("Environment", "Configuration", "Authentication", "Metadata", "Connectivity", "Target", "Notifications"):
        assert f"\n{section}\n" not in rendered


# Verifies a clean report returns success
def test_zero_failures_returns_success(monkeypatch, capsys):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "build_doctor_report", lambda *args, **kwargs: monitor.DoctorReport([monitor.make_doctor_check("Environment", "PASS", "ok")]))
    assert monitor.run_doctor() == 0
    assert "All checks passed. You are good to go!" in capsys.readouterr().out


# Verifies interactive doctor progress is transient while the final report still renders
def test_doctor_interactive_progress(monkeypatch):
    stream = TTYBuffer()

    # Emits one progress update before returning a passing report
    def build_report(*args, **kwargs):
        kwargs["progress"]("notifications")
        return monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", "ok")])

    monkeypatch.setattr(monitor.sys, "stdout", monitor.TerminalStream(stream))
    monkeypatch.setattr(monitor, "build_doctor_report", build_report)
    assert monitor.run_doctor() == 0
    output = stream.getvalue()
    assert "* Checking notifications ..." in output
    assert "Doctor\n" in output
    assert "All checks passed. You are good to go!" in output


# Verifies doctor progress stops at the visible message instead of padding to a fixed terminal column
def test_doctor_progress_uses_visible_message_width(monkeypatch):
    stream = TTYBuffer()
    monkeypatch.setattr(monitor.sys, "stdout", monitor.TerminalStream(stream))
    monitor._doctor_progress("authentication")
    line = "* Checking authentication ..."
    assert stream.getvalue() == "\r" + line
    monitor._doctor_progress_clear()
    assert stream.getvalue() == "\r" + line + "\r" + (" " * len(line)) + "\r"


# Verifies warnings alone preserve a zero exit code
def test_warnings_without_failures_return_success(monkeypatch):
    advice = monitor.classify_recovery_error(context="target_missing")
    report = monitor.DoctorReport([monitor.make_doctor_check("Target", "WARN", "No target", advice=advice)])
    monkeypatch.setattr(monitor, "build_doctor_report", lambda *args, **kwargs: report)
    assert monitor.run_doctor() == 0


# Verifies any failed check produces a nonzero exit code
def test_any_failure_returns_nonzero(monkeypatch):
    advice = monitor.classify_recovery_error(context="config_invalid")
    report = monitor.DoctorReport([monitor.make_doctor_check("Configuration", "FAIL", "bad config", advice=advice)])
    monkeypatch.setattr(monitor, "build_doctor_report", lambda *args, **kwargs: report)
    assert monitor.run_doctor() != 0


# Verifies interactive doctor delivery tests require separate default-no approvals
def test_doctor_delivery_tests_can_be_declined_independently(monkeypatch):
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", monitor.SMTP_READY_CHECK_LABEL), monitor.make_doctor_check("Notifications", "PASS", monitor.WEBHOOK_READY_CHECK_LABEL)])
    consent = Mock(side_effect=[False, False])
    email = Mock(side_effect=AssertionError("email sent without approval"))
    webhook = Mock(side_effect=AssertionError("webhook sent without approval"))
    stream = TTYBuffer()
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", stream)
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", consent)
    monkeypatch.setattr(monitor, "send_email", email)
    monkeypatch.setattr(monitor, "send_webhook", webhook)
    provider = monitor.webhook_provider_display_name()
    assert [(check.status, check.label) for check in monitor._doctor_offer_notification_tests(report)] == [("SKIP", "Test email was not sent"), ("SKIP", f"Test webhook through {provider} was not sent")]
    assert consent.call_count == 2
    email.assert_not_called()
    webhook.assert_not_called()
    output = stream.getvalue()
    assert "[SKIP] Test email was not sent" in output
    assert f"[SKIP] Test webhook through {provider} was not sent" in output
    # The declined row carries the same detail line the report gives every other row
    assert "  You declined the real delivery test. Run doctor again and approve the email test when ready" in output


# Verifies an empty doctor delivery answer defaults safely to no
def test_doctor_delivery_consent_defaults_to_no(monkeypatch):
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: (prompts.append(prompt) or ""))
    assert monitor._doctor_ask_yes_no("Send one test") is False
    assert prompts == ["Send one test [y/N]: "]


# Verifies separately approved doctor tests deliver one email and one webhook
def test_doctor_delivery_tests_send_approved_messages(monkeypatch):
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", monitor.SMTP_READY_CHECK_LABEL), monitor.make_doctor_check("Notifications", "PASS", monitor.WEBHOOK_READY_CHECK_LABEL)])
    consent = Mock(side_effect=[True, True])
    email = Mock(return_value=0)
    webhook = Mock(return_value=0)
    stream = TTYBuffer()
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", stream)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", consent)
    monkeypatch.setattr(monitor, "send_email", email)
    monkeypatch.setattr(monitor, "send_webhook", webhook)
    results = monitor._doctor_offer_notification_tests(report)
    assert [check.status for check in results] == ["PASS", "PASS"]
    email.assert_called_once_with("Spotify Monitor doctor test email", "This test email was sent after approval in --doctor. Your SMTP delivery settings work.", "", monitor.SMTP_SSL, smtp_timeout=5, report_delivery=False)
    webhook.assert_called_once_with("Spotify Monitor doctor test webhook", "This test notification was sent after approval in --doctor. Your webhook delivery settings work.", "song", force=True, report_delivery=False)
    output = stream.getvalue()
    assert "[PASS] Doctor test webhook through ntfy delivered" in output
    assert "  One real test webhook was sent after confirmation" in output


# Verifies the delivery-test gate still recognizes the readiness check once its label names the provider
def test_delivery_gate_matches_the_provider_named_label(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    label = f"{monitor.WEBHOOK_READY_CHECK_LABEL} for {monitor.webhook_provider_display_name()}"
    assert label.endswith("for Discord")
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", label)])
    consent = Mock(return_value=False)
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", Mock(isatty=lambda: True, write=lambda *args: None, flush=lambda: None))
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", consent)

    monitor._doctor_offer_notification_tests(report)

    assert consent.call_count == 1
    assert "Send one test webhook through Discord now?" in consent.call_args[0][0]


# Verifies noninteractive doctor runs never offer or send delivery tests
def test_noninteractive_doctor_never_offers_delivery_tests(monkeypatch):
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", monitor.SMTP_READY_CHECK_LABEL), monitor.make_doctor_check("Notifications", "PASS", monitor.WEBHOOK_READY_CHECK_LABEL)])
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", Mock(isatty=lambda: False))
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", Mock(side_effect=AssertionError("consent prompt attempted")))
    monkeypatch.setattr(monitor, "send_email", Mock(side_effect=AssertionError("email attempted")))
    monkeypatch.setattr(monitor, "send_webhook", Mock(side_effect=AssertionError("webhook attempted")))
    assert monitor._doctor_offer_notification_tests(report) == []


# Verifies an approved delivery failure makes the doctor command fail
def test_doctor_returns_nonzero_after_approved_delivery_failure(monkeypatch):
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", "SMTP connection and login succeeded")])
    stream = TTYBuffer()
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", stream)
    monkeypatch.setattr(monitor, "build_doctor_report", lambda *args, **kwargs: report)
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", Mock(return_value=True))
    monkeypatch.setattr(monitor, "send_email", Mock(return_value=1))
    assert monitor.run_doctor() == 1
    assert "[FAIL] Doctor test email delivery failed" in stream.getvalue()


# Verifies independent notification checks continue after authentication failure
def test_independent_checks_continue_after_failure(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "")
    report = monitor.build_doctor_report(spec_finder=all_dependencies_present)
    assert any(check.section == "Authentication" and check.status == "FAIL" for check in report.checks)
    assert any(check.section == "Notifications" for check in report.checks)


# Verifies dependent checks are clearly skipped after authentication failure
def test_dependent_checks_are_skipped_clearly(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "")
    report = monitor.build_doctor_report("friend.user", spec_finder=all_dependencies_present)
    assert any(check.section == "Connectivity" and check.status == "SKIP" and check.label == "Spotify connectivity was not checked" for check in report.checks)
    assert any(check.section == "Target" and check.status == "SKIP" and check.label == "The monitored profile was not checked" for check in report.checks)


# Verifies Python version support reports pass and fail states
def test_python_version_check():
    supported = monitor.doctor_check_environment((3, 9, 0), all_dependencies_present)
    unsupported = monitor.doctor_check_environment((3, 8, 18), all_dependencies_present)
    assert supported[0].status == "PASS"
    assert unsupported[0].status == "FAIL"
    assert not any(check.label.startswith("Install method") for check in supported)


# Verifies missing optional dependencies are warnings that do not affect normal monitoring
def test_optional_dependency_reporting(monkeypatch):
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    checks = monitor.doctor_check_environment((3, 9, 0), lambda name: None if name in ("spotipy", "pycookiecheat", "PIL") else object())
    optional = [check for check in checks if "Optional dependency" in check.label]
    assert len(optional) == 3
    assert all(check.status == "WARN" for check in optional)
    assert all("Every other feature is unaffected" in check.detail for check in optional)


# Verifies a warning about a library that cannot affect this machine is not shown at all
@pytest.mark.parametrize("system, reported", [("Windows", True), ("Linux", False), ("Darwin", False)])
def test_a_platform_specific_dependency_is_only_reported_where_it_applies(monkeypatch, system, reported):
    monkeypatch.setattr(monitor.platform, "system", lambda: system)

    checks = monitor.doctor_check_environment((3, 9, 0), lambda name: None)

    assert any("colorama" in check.label for check in checks) is reported


# Verifies the Windows colour library is reported there, so broken colours on that platform have a diagnostic
def test_missing_colorama_is_reported_on_windows(monkeypatch):
    monkeypatch.setattr(monitor.platform, "system", lambda: "Windows")

    checks = monitor.doctor_check_environment((3, 9, 0), lambda name: None if name == "colorama" else object())

    missing = next(check for check in checks if "colorama" in check.label)
    assert missing.status == "WARN"
    assert "Coloured output may not render in the classic Windows Command Prompt" in missing.detail
    assert "Windows Terminal, which needs nothing extra" in require_advice(missing).fix


# Verifies Chromium dependency guidance explicitly preserves Firefox import support
def test_installed_browser_dependency_explains_firefox_support():
    checks = monitor.doctor_check_environment((3, 9, 0), all_dependencies_present)
    check = next(item for item in checks if "pycookiecheat" in item.label)

    assert check.status == "PASS"
    assert check.detail == "Used only for importing cookies from Chromium-based browsers. Firefox cookie import does not need it"


# Verifies requested container playback is a warning rather than a failure
def test_doctor_reports_container_playback_as_warning(monkeypatch):
    monkeypatch.setattr(monitor, "is_container_environment", lambda: True)
    monkeypatch.setattr(monitor, "TRACK_SONGS", True)
    checks = monitor.doctor_check_container_playback()
    assert len(checks) == 1
    assert checks[0].status == "WARN"
    assert "unavailable by default" in checks[0].label
    assert monitor.CONTAINER_PLAYBACK_WARNING in checks[0].detail
    report = monitor.DoctorReport(checks)
    monkeypatch.setattr(monitor, "build_doctor_report", lambda *args, **kwargs: report)
    assert monitor.run_doctor() == 0


# Verifies local playback configuration has no container warning
def test_doctor_omits_container_playback_warning_locally(monkeypatch):
    monkeypatch.setattr(monitor, "is_container_environment", lambda: False)
    monkeypatch.setattr(monitor, "TRACK_SONGS", True)
    assert monitor.doctor_check_container_playback() == []


# Verifies an explicit missing config appears inside the doctor summary
def test_explicit_missing_config_is_reported():
    result = run_cli(["--doctor", "--config-file", "local/does-not-exist-phase3.conf", "--env-file", "none"], "runtime['run_doctor'] = lambda target, config, env, checks: (print(runtime['render_doctor_sections'](runtime['DoctorReport'](list(checks))) + runtime['render_doctor_summary'](list(checks))) or 1);")
    assert result.returncode == 1
    assert "configuration file was not found" in result.stdout.lower()
    assert "Summary" in result.stdout


# Verifies malformed config diagnostics retain the line and source inside doctor output
def test_malformed_config_is_reported_inside_summary(tmp_path):
    config_path = tmp_path / "broken.conf"
    config_path.write_text('TOKEN_SOURCE = "cookie"\nTARGET_USER_URI_ID = "broken\n', encoding="utf-8")
    result = run_cli(["--doctor", "--config-file", str(config_path), "--env-file", "none"], "runtime['run_doctor'] = lambda target, config, env, checks: (print(runtime['render_doctor_sections'](runtime['DoctorReport'](list(checks))) + runtime['render_doctor_summary'](list(checks))) or 1);")
    assert result.returncode == 1
    assert "Line: 2" in result.stdout
    assert 'TARGET_USER_URI_ID = "broken' not in result.stdout
    assert "Summary" in result.stdout


# Verifies an explicit missing dotenv file is a doctor failure
def test_explicit_missing_dotenv_is_reported():
    result = run_cli(["--doctor", "--env-file", "local/does-not-exist-phase3.env"], "runtime['run_doctor'] = lambda target, config, env, checks: (print(runtime['render_doctor_sections'](runtime['DoctorReport'](list(checks))) + runtime['render_doctor_summary'](list(checks))) or 1);")
    assert result.returncode == 1
    assert "dotenv file was not found" in result.stdout.lower()


# Verifies missing cookie credentials produce a direct import recovery action
def test_cookie_missing(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "your_sp_dc_cookie_value")
    report = monitor.DoctorReport()
    checks = monitor.doctor_check_authentication(report)
    assert checks[-1].status == "FAIL"
    assert require_advice(checks[-1]).code == "secret.missing"
    assert "--import-browser-cookie --browser firefox" in require_advice(checks[-1]).fix


# Verifies valid cookie authentication reuses the buddy-list endpoint
def test_cookie_validation_success(monkeypatch):
    configure_valid_doctor(monkeypatch)
    report = monitor.DoctorReport()
    checks = monitor.doctor_check_authentication(report)
    assert checks[-1].status == "PASS"
    assert report.buddy_list == buddy_list()


# Verifies rejected cookie credentials are classified separately
def test_cookie_invalid(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: (_ for _ in ()).throw(RuntimeError("unsuccessful token request")))
    report = monitor.DoctorReport()
    checks = monitor.doctor_check_authentication(report)
    assert require_advice(checks[-1]).code == "auth.cookie_invalid"


# Verifies cookie rate limiting is reported with its stable category
def test_cookie_rate_limited(monkeypatch):
    configure_valid_doctor(monkeypatch)
    response = requests.Response()
    response.status_code = 429
    error = requests.HTTPError("HTTP 429", response=response)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: (_ for _ in ()).throw(error))
    report = monitor.DoctorReport()
    assert require_advice(monitor.doctor_check_authentication(report)[-1]).code == "spotify.rate_limited"


# Verifies cookie network failures remain distinct from invalid credentials
def test_cookie_network_failure(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: (_ for _ in ()).throw(requests.ConnectionError("connection refused")))
    report = monitor.DoctorReport()
    assert require_advice(monitor.doctor_check_authentication(report)[-1]).code == "network.unavailable"


@pytest.mark.parametrize("cipher_bytes", [(), 17])
# Verifies invalid web-player TOTP parameters fail the configuration check in cookie mode, including a single
# number written in place of the sequence, which is truthy and would otherwise be iterated
def test_invalid_totp_config_fails(monkeypatch, cipher_bytes):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "TOTP_SECRET_CIPHER_BYTES", cipher_bytes)
    checks = monitor.doctor_check_configuration()
    totp_check = next(check for check in checks if "TOTP" in check.label)
    assert totp_check.status == "FAIL"
    assert require_advice(totp_check).code == "config.invalid"


# Verifies valid web-player TOTP parameters pass the configuration check in cookie mode
def test_valid_totp_config_passes(monkeypatch):
    configure_valid_doctor(monkeypatch)
    checks = monitor.doctor_check_configuration()
    totp_check = next(check for check in checks if "TOTP" in check.label)
    assert totp_check.status == "PASS"


# Verifies Doctor checks the final target-specific log filename
def test_doctor_configuration_uses_final_target_log_path(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "SP_LOGFILE", "spotify_monitor")
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "")

    checks = monitor.doctor_check_configuration(target_value="spotify:user:sq58")
    check = next(item for item in checks if item.label == "Log destination appears writable")

    assert check.detail == "Path: spotify_monitor_sq58.log"


# Verifies custom and scrobble-health suffixes use the runtime naming rules
def test_doctor_configuration_uses_effective_log_suffix(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "DISABLE_LOGGING", False)
    monkeypatch.setattr(monitor, "SP_LOGFILE", "logs/spotify")
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "friends")

    custom_checks = monitor.doctor_check_configuration(target_value="sq58")
    custom_check = next(item for item in custom_checks if item.label == "Log destination appears writable")
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "")
    scrobble_checks = monitor.doctor_check_configuration(lastfm_username="Last.fm User")
    scrobble_check = next(item for item in scrobble_checks if item.label == "Log destination appears writable")

    assert custom_check.detail == "Path: logs/spotify_friends.log"
    assert scrobble_check.detail == "Path: logs/spotify_lastfm_Last.fm_User.log"
    assert monitor.build_log_path("logs/fixed.log", "sq58") == Path("logs/fixed.log")


# Configures the minimum valid client-mode values
def configure_client_mode(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "client")
    monkeypatch.setattr(monitor, "DEVICE_ID", "device")
    monkeypatch.setattr(monitor, "SYSTEM_ID", "system")
    monkeypatch.setattr(monitor, "USER_URI_ID", "user")
    monkeypatch.setattr(monitor, "REFRESH_TOKEN", "refresh")
    monkeypatch.setattr(monitor, "LOGIN_REQUEST_BODY_FILE", "")
    monkeypatch.setattr(monitor, "CLIENTTOKEN_REQUEST_BODY_FILE", "")


# Verifies client mode lists each missing required field
def test_client_required_fields_missing(monkeypatch):
    configure_client_mode(monkeypatch)
    monkeypatch.setattr(monitor, "DEVICE_ID", "")
    report = monitor.DoctorReport()
    check = monitor.doctor_check_authentication(report)[-1]
    assert check.status == "FAIL"
    assert "DEVICE_ID" in check.detail


# Verifies successful client authentication validates through buddy-list data
def test_client_authentication_success(monkeypatch):
    configure_client_mode(monkeypatch)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_client_auto", lambda *args: "client-access")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: buddy_list())
    report = monitor.DoctorReport()
    assert monitor.doctor_check_authentication(report)[-1].status == "PASS"


# Verifies client authentication rejection uses the client recovery category
def test_client_authentication_failure(monkeypatch):
    configure_client_mode(monkeypatch)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_client_auto", lambda *args: (_ for _ in ()).throw(RuntimeError("refresh token has expired")))
    report = monitor.DoctorReport()
    assert require_advice(monitor.doctor_check_authentication(report)[-1]).code == "auth.client_invalid"


# Verifies incomplete optional OAuth credentials produce a warning
def test_incomplete_optional_oauth_pair(monkeypatch):
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "configured-id")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "")
    check = monitor.doctor_check_optional_oauth()[0]
    assert check.status == "WARN"
    assert "incomplete" in check.label.lower()


# Verifies missing Spotipy leaves the web-player fallback available
def test_missing_spotipy_with_optional_credentials(monkeypatch):
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "configured-id")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "configured-secret")
    monkeypatch.setattr(monitor.importlib.util, "find_spec", lambda name: None)
    check = monitor.doctor_check_optional_oauth()[0]
    assert check.status == "WARN"
    assert "web-player" in require_advice(check).fix


# Verifies doctor checks live legacy metadata with a memory-only OAuth token
def test_optional_oauth_live_metadata_success_uses_no_file_cache(monkeypatch):
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "configured-id")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "configured-secret")
    monkeypatch.setattr(monitor.importlib.util, "find_spec", lambda name: object())
    token_request = Mock(return_value="legacy-token")
    legacy_track = Mock(return_value={"sp_track_name": "Bohemian Rhapsody"})
    web_track = Mock()
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_oauth_app", token_request)
    monkeypatch.setattr(monitor, "_spotify_get_track_info_api", legacy_track)
    monkeypatch.setattr(monitor, "spotify_get_track_info_web", web_track)
    check = monitor.doctor_check_optional_oauth()[0]
    assert check.status == "PASS"
    assert "access succeeded" in check.label.lower()
    token_request.assert_called_once_with("configured-id", "configured-secret", use_file_cache=False)
    legacy_track.assert_called_once_with("legacy-token", monitor.OAUTH_APP_VALIDATION_TRACK_URI, oauth_app=True)
    web_track.assert_not_called()


# Verifies doctor warns without failing when automatic web metadata fallback works
def test_optional_oauth_live_failure_warns_when_web_fallback_succeeds(monkeypatch):
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "configured-id")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "configured-secret")
    monkeypatch.setattr(monitor.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_oauth_app", Mock(return_value="legacy-token"))
    monkeypatch.setattr(monitor, "_spotify_get_track_info_api", Mock(side_effect=RuntimeError("legacy restricted")))
    web_track = Mock(return_value={"sp_track_name": "Bohemian Rhapsody"})
    monkeypatch.setattr(monitor, "spotify_get_track_info_web", web_track)
    check = monitor.doctor_check_optional_oauth()[0]
    assert check.status == "WARN"
    assert "fallback succeeded" in check.detail.lower()
    assert "owner has active Spotify Premium" in require_advice(check).fix
    web_track.assert_called_once_with(monitor.OAUTH_APP_VALIDATION_TRACK_URI)


# Verifies doctor fails only when both live metadata backends fail
def test_optional_oauth_and_web_metadata_fail_together(monkeypatch):
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "configured-id")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "configured-secret")
    monkeypatch.setattr(monitor.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_oauth_app", Mock(side_effect=RuntimeError("invalid client")))
    monkeypatch.setattr(monitor, "spotify_get_track_info_web", Mock(side_effect=RuntimeError("web unavailable")))
    check = monitor.doctor_check_optional_oauth()[0]
    assert check.status == "FAIL"
    assert "both spotify metadata backends" in check.label.lower()


# Verifies no target is only a warning for auth-only preflight
def test_no_target_is_warning():
    check = monitor.doctor_check_target(monitor.DoctorReport(buddy_list=buddy_list()), None)[0]
    assert check.status == "WARN"


# Verifies a visible normalized target passes
def test_valid_target_passes():
    check = monitor.doctor_check_target(monitor.DoctorReport(buddy_list=buddy_list()), "spotify:user:friend.user")[0]
    assert check.status == "PASS"


# Verifies malformed target input fails before a live lookup
def test_malformed_target_fails():
    check = monitor.doctor_check_target(monitor.DoctorReport(buddy_list=buddy_list()), "spotify:track:not-user")[0]
    assert check.status == "FAIL"
    assert require_advice(check).code == "target.invalid"


# Verifies Doctor names the follow state of an invisible target, so the reader knows which sharing path to fix
@pytest.mark.parametrize("followed,expected", [
    (True, "The monitoring account follows the target, so the target is not sharing listening activity with it or is in a private session"),
    (False, "The monitoring account does not follow the target"),
])
def test_target_not_visible_names_the_follow_state(monkeypatch, followed, expected):
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", "listening_activity")
    monkeypatch.setattr(monitor, "spotify_user_is_followed", Mock(return_value=followed))
    check = monitor.doctor_check_target(monitor.DoctorReport(buddy_list=buddy_list("someone.else"), access_token="token"), "friend.user")[0]
    assert check.status == "FAIL"
    assert check.detail.endswith(expected)
    advice = require_advice(check)
    assert "unless the target shares listening activity with that account directly" in advice.fix
    assert "A private session hides the target until it ends\nGuide: " in advice.fix


# Verifies the legacy backend keeps the private session out of the invisible-target explanation and survives a failed follow lookup
def test_target_not_visible_with_the_legacy_backend_omits_private_sessions(monkeypatch):
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", "buddylist")
    monkeypatch.setattr(monitor, "spotify_user_is_followed", Mock(side_effect=RuntimeError("offline")))
    check = monitor.doctor_check_target(monitor.DoctorReport(buddy_list=buddy_list("someone.else"), access_token="token"), "friend.user")[0]
    assert check.status == "FAIL"
    assert check.detail == "Target 'friend.user' was absent from the authenticated buddylist response"
    assert "private session" not in require_advice(check).fix


# Verifies an absent target is described as invisible with its normalized profile link
@pytest.mark.parametrize("target_value", ["friend.user", "spotify:user:friend.user", "https://open.spotify.com/user/friend%2Euser?si=test"])
def test_target_absent_from_buddy_list_is_not_visible(target_value):
    check = monitor.doctor_check_target(monitor.DoctorReport(buddy_list=buddy_list("someone.else")), target_value)[0]
    assert check.status == "FAIL"
    assert require_advice(check).code == "target.not_visible"
    rendered = render_doctor_report(monitor.DoctorReport([check]))
    assert "deleted" not in rendered.lower()
    assert rendered.count("https://open.spotify.com/user/friend.user") == 1


# Verifies target checks reuse the authentication buddy-list response
def test_target_check_reuses_authentication_response(monkeypatch):
    configure_valid_doctor(monkeypatch)
    fetch = Mock(return_value=buddy_list())
    monkeypatch.setattr(monitor, "spotify_get_friends_json", fetch)
    report = monitor.build_doctor_report("friend.user", spec_finder=all_dependencies_present)
    assert fetch.call_count == 1
    assert any(check.section == "Target" and check.status == "PASS" for check in report.checks)


# Verifies disabled notifications never contact SMTP
def test_notifications_disabled_do_not_contact_smtp(monkeypatch):
    configure_valid_doctor(monkeypatch)
    connect = Mock(side_effect=AssertionError("SMTP should not be contacted"))
    monkeypatch.setattr(monitor, "smtp_connect_and_login", connect)
    assert monitor.doctor_check_notifications()[0].status == "PASS"
    connect.assert_not_called()


# Verifies incomplete enabled SMTP settings are reported before a connection, as a warning rather than a failure
def test_incomplete_enabled_smtp_config_warns(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "SMTP_HOST", "")
    check = monitor.doctor_check_notifications()[0]
    assert check.status == "WARN"
    assert require_advice(check).code == "smtp.invalid"


# Verifies email alerts that cannot deliver are one WARN whose detail and action name the same settings
def test_unusable_email_settings_warn_and_name_the_same_settings(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "monitor@example.invalid")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "owner@example.invalid")
    monkeypatch.setattr(monitor, "SMTP_USER", "your_smtp_user")
    monkeypatch.setattr(monitor, "smtp_connect_and_login", Mock(side_effect=AssertionError("SMTP was contacted")))

    check = monitor.doctor_check_notifications()[0]

    assert check.status == "WARN"
    assert check.label == monitor.EMAIL_UNUSABLE_CHECK_LABEL
    assert check.detail == "SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder"
    assert "Set SMTP_USER and SMTP_PASSWORD or turn the email alerts off" in require_advice(check).fix
    assert monitor.SMTP_GUIDE_URL in require_advice(check).fix


class FakeSMTP:
    # Initializes call tracking for one fake SMTP session
    def __init__(self):
        self.login_calls = []
        self.quit_calls = 0
        self.sendmail_calls = 0

    # Records one SMTP login without network access
    def login(self, username, password):
        self.login_calls.append((username, password))

    # Records a safe SMTP close
    def quit(self):
        self.quit_calls += 1

    # Fails if the passive doctor check attempts to send mail
    def sendmail(self, *args):
        self.sendmail_calls += 1
        raise AssertionError("passive doctor check must not send email")


# Configures complete enabled SMTP settings
def configure_smtp(monkeypatch):
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(monitor, "SMTP_PORT", 587)
    monkeypatch.setattr(monitor, "SMTP_USER", "smtp-user")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "smtp-password")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "sender@example.com")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "receiver@example.com")


# Verifies valid SMTP login closes without calling sendmail
def test_valid_smtp_connects_and_logs_in_without_sending(monkeypatch):
    configure_smtp(monkeypatch)
    fake = FakeSMTP()
    monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda *args, **kwargs: fake)
    check = monitor.doctor_check_notifications()[0]
    assert check.status == "PASS"
    assert fake.quit_calls == 1
    assert fake.sendmail_calls == 0


# Verifies SMTP authentication failure is classified and sends nothing
def test_smtp_login_failure(monkeypatch):
    configure_smtp(monkeypatch)
    monkeypatch.setattr(monitor, "smtp_connect_and_login", lambda *args, **kwargs: (_ for _ in ()).throw(monitor.smtplib.SMTPAuthenticationError(535, b"bad")))
    check = monitor.doctor_check_notifications()[0]
    assert check.status == "FAIL"
    assert require_advice(check).code == "smtp.authentication"


# Verifies doctor output redacts all known secret values
def test_doctor_output_contains_no_secret(monkeypatch):
    configure_valid_doctor(monkeypatch)
    secret = "FAKE-DOCTOR-SECRET"
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", secret)
    report = monitor.build_doctor_report("friend.user", spec_finder=all_dependencies_present)
    assert secret not in render_doctor_report(report)


# Verifies the doctor CLI can run without a positional target and bypass normal startup
def test_cli_doctor_without_target_bypasses_normal_startup():
    setup = "runtime['check_internet'] = lambda: (_ for _ in ()).throw(AssertionError('connectivity gate called')); runtime['spotify_monitor_friend_uri'] = lambda *args: (_ for _ in ()).throw(AssertionError('monitor loop called')); runtime['run_doctor'] = lambda *args: 0;"
    result = run_cli(["--doctor", "--env-file", "none"], setup)
    assert result.returncode == 0
    assert "connectivity gate called" not in result.stderr
    assert "monitor loop called" not in result.stderr
    assert "Start monitoring:" in result.stdout
    # Nothing supplies a target here, so the command keeps the placeholder rather than printing one that cannot run
    assert runtime_command("python3 spotify_monitor.py <spotify_target> --env-file none") in result.stdout
    assert "SPOTIFY_USER_URI_ID" not in result.stdout


# Verifies a successful Compose Doctor command prints the matching target and file context
def test_cli_doctor_success_prints_compose_monitoring_command():
    setup = "runtime['run_doctor'] = lambda *args: 0; runtime['_wizard_install_method'] = lambda: 'compose';"
    result = run_cli(["friend.user", "--doctor", "--env-file", "none"], setup)
    assert result.returncode == 0
    assert "Start monitoring:" in result.stdout
    assert "docker compose run --rm spotify_monitor friend.user --env-file none" in result.stdout
    assert "--doctor" not in result.stdout.split("Start monitoring:", 1)[1]


# Verifies successful scrobble Doctor output preserves local script paths and selected files
def test_cli_scrobble_doctor_success_prints_manual_monitoring_command(tmp_path):
    config_path = tmp_path / "spotify_monitor_scrobble_health.conf"
    env_path = tmp_path / ".env.scrobble_health"
    config_path.write_text(f'MONITOR_MODE = "scrobble_health"\nLASTFM_USERNAME = "lastfm-user"\nSPOTIFY_SCROBBLE_CLIENT_ID = "{"a" * 32}"\n', encoding="utf-8")
    env_path.write_text("LASTFM_API_KEY=private-api-key\nSPOTIFY_SCROBBLE_REFRESH_TOKEN=private-refresh-token\n", encoding="utf-8")
    result = run_cli(["--monitor-mode", "scrobble_health", "--doctor", "--config-file", str(config_path), "--env-file", str(env_path)], "runtime['run_scrobble_health_doctor'] = lambda *args: 0;")
    expected_prefix = monitor._wizard_cmd_prefix("manual")
    assert result.returncode == 0
    assert "Start scrobble health monitoring:" in result.stdout
    assert f"{expected_prefix} --monitor-mode scrobble_health --config-file {config_path} --env-file {env_path}" in result.stdout


# Verifies successful scrobble Doctor output detects Compose and preserves file-free selection
def test_cli_scrobble_doctor_success_prints_compose_monitoring_command():
    setup = "runtime['run_scrobble_health_doctor'] = lambda *args: 0; runtime['_wizard_install_method'] = lambda: 'compose';"
    result = run_cli(["--monitor-mode", "scrobble_health", "--doctor", "--config-file", "none", "--env-file", "none", "--lastfm-username", "lastfm-user", "--lastfm-api-key", "private-api-key", "--scrobble-client-id", "a" * 32, "--scrobble-refresh-token", "private-refresh-token"], setup)
    assert result.returncode == 0
    assert "Start scrobble health monitoring:" in result.stdout
    assert f"docker compose run --rm spotify_monitor --monitor-mode scrobble_health --lastfm-username lastfm-user --scrobble-client-id {'a' * 32} --lastfm-api-key LASTFM_API_KEY --scrobble-refresh-token SPOTIFY_SCROBBLE_REFRESH_TOKEN --config-file none --env-file none" in result.stdout
    assert "Replace the uppercase credential placeholders before running" in result.stdout
    assert "private-api-key" not in result.stdout
    assert "private-refresh-token" not in result.stdout


# Verifies a run with no target of its own prints no placeholder, so the command can be pasted as it is
def test_doctor_monitoring_command_carries_no_placeholder_target(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monitor._wizard_print_monitor_after_doctor(tmp_path / "spotify_monitor.conf", tmp_path / ".env")
    output = capsys.readouterr().out
    assert "SPOTIFY_USER_URI_ID" not in output
    assert f"--config-file {tmp_path / 'spotify_monitor.conf'}" in output
    assert f"--env-file {tmp_path / '.env'}" in output


# Verifies a failed Doctor still names the command, labelled so the failures are fixed first
def test_cli_doctor_failure_asks_for_the_failures_first():
    result = run_cli(["friend.user", "--doctor", "--env-file", "none"], "runtime['run_doctor'] = lambda *args: 1;")
    assert result.returncode == 1
    assert "After Doctor passes, start monitoring:" in result.stdout


# Verifies a real run with discovery switched off carries the sentinel into the recovery command it prints,
# since the command reads the config and pasting it without the flag would turn discovery back on
def test_cli_discovery_switched_off_reaches_the_printed_recovery_command():
    setup = "runtime['SP_DC_COOKIE'] = 'your_sp_dc_cookie_value'; runtime['TOKEN_SOURCE'] = 'cookie'; runtime['_wizard_install_method'] = lambda: 'manual'; runtime['check_internet'] = lambda *args, **kwargs: False;"
    result = run_cli(["--doctor", "--config-file", "none", "--env-file", "none"], setup)

    assert "--import-browser-cookie --browser firefox --config-file none" in result.stdout


# Verifies contradictory doctor action flags are rejected
@pytest.mark.parametrize("flag", ["--import-browser-cookie", "--send-test-email", "--list-friends"])
def test_contradictory_action_flags_are_rejected(flag):
    result = run_cli(["--doctor", flag])
    assert result.returncode == 2
    assert "cannot be combined" in result.stderr


# Verifies missing artwork support names the current NTFY_IMAGES setting and the install command
def test_optional_artwork_dependency_explains_ntfy_images(monkeypatch):
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    checks = monitor.doctor_check_environment((3, 10, 0), lambda name: None if name == "PIL" else object())
    check = next(item for item in checks if "Pillow" in item.label)

    assert check.status == "WARN"
    assert "NTFY_IMAGES is enabled" in check.detail
    assert "spotify_monitor[notification-images]" in require_advice(check).fix


# Verifies artwork guidance inside a container points at the published images instead of pip
def test_optional_artwork_dependency_guides_container_users(monkeypatch):
    monkeypatch.setattr(monitor, "NTFY_IMAGES", False)
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "docker")
    checks = monitor.doctor_check_environment((3, 13, 0), lambda name: None if name == "PIL" else object())
    check = next(item for item in checks if "Pillow" in item.label)

    assert "currently disabled" in check.detail
    assert "Docker images" in require_advice(check).fix
    assert "pip install" not in require_advice(check).fix


# Exported secrets are a documented alternative to a dotenv file, so they must apply when no file is loaded
def test_environment_secrets_apply_without_a_dotenv_file(monkeypatch):
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor", "--doctor", "--env-file", "none"])
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "", raising=False)
    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "tk_from_environment")

    with pytest.raises(SystemExit):
        monitor.main()

    assert monitor.NTFY_ACCESS_TOKEN == "tk_from_environment"


# Exported values win over duplicate dotenv keys and retain their effective source
def test_environment_secret_wins_over_duplicate_dotenv_key(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("NTFY_ACCESS_TOKEN=tk_from_file\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor", "--doctor", "--env-file", str(env_file)])
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {}, raising=False)
    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "tk_from_environment")

    with pytest.raises(SystemExit):
        monitor.main()

    assert monitor.NTFY_ACCESS_TOKEN == "tk_from_environment"
    assert monitor.SECRET_SOURCES["NTFY_ACCESS_TOKEN"] == "environment"


# The documented precedence covers the non-secret environment settings too, not only the secrets
def test_environment_setting_wins_over_duplicate_dotenv_key(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SPOTIFY_SCROBBLE_CLIENT_ID=client-from-file\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor", "--doctor", "--env-file", str(env_file)])
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_CLIENT_ID", "", raising=False)
    monkeypatch.setenv("SPOTIFY_SCROBBLE_CLIENT_ID", "client-from-environment")

    with pytest.raises(SystemExit):
        monitor.main()

    assert monitor.SPOTIFY_SCROBBLE_CLIENT_ID == "client-from-environment"


# An empty export is a shell-profile leftover rather than a value, so it neither blocks nor blanks the dotenv value
def test_an_empty_export_does_not_shadow_the_dotenv_value(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("NTFY_ACCESS_TOKEN=tk_from_file\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor", "--doctor", "--env-file", str(env_file)])
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {}, raising=False)
    monkeypatch.setenv("NTFY_ACCESS_TOKEN", "")

    with pytest.raises(SystemExit):
        monitor.main()

    assert monitor.NTFY_ACCESS_TOKEN == "tk_from_file"
    assert monitor.SECRET_SOURCES["NTFY_ACCESS_TOKEN"] == "dotenv file"


# The same leftover must not blank a value the config file supplied, where no dotenv assignment exists to restore it
def test_an_empty_export_does_not_blank_a_config_supplied_secret(monkeypatch):
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor", "--doctor", "--env-file", "none"])
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "cookie-from-the-config", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {}, raising=False)
    monkeypatch.setenv("SP_DC_COOKIE", "")

    with pytest.raises(SystemExit):
        monitor.main()

    assert monitor.SP_DC_COOKIE == "cookie-from-the-config"
    assert monitor.SECRET_SOURCES["SP_DC_COOKIE"] == "configuration file or command line"


# Each secret is attributed to the source it actually came from, so the report can name the dotenv path
def test_secret_sources_split_by_origin(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SMTP_PASSWORD=from-file\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "from-file", raising=False)
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/topic", raising=False)
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "your_sp_dc_cookie_value", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"SMTP_PASSWORD": "dotenv file", "WEBHOOK_URL": "environment"}, raising=False)

    from_file, from_environment, from_settings, from_command_line = monitor.doctor_secret_sources(str(env_file))

    assert "SMTP_PASSWORD" in from_file
    assert "WEBHOOK_URL" in from_environment
    assert "SP_DC_COOKIE" not in from_file + from_environment + from_settings + from_command_line


# Verifies a row whose advice repeats its own summary prints that text once rather than as two problems
def test_a_row_never_prints_its_summary_twice():
    repeated = "No valid sp_dc cookie was found"

    check = monitor.make_doctor_check("Configuration", "WARN", repeated, repeated, actionable_advice())

    assert check.label == repeated
    assert check.detail == ""


# Verifies a secret passed as an argument is reported under the command line rather than the configuration file
def test_a_command_line_secret_is_reported_as_such(monkeypatch):
    for name in monitor.SECRET_KEYS:
        monkeypatch.setattr(monitor, name, "your_placeholder", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"SMTP_PASSWORD": "command line"}, raising=False)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "a-real-secret-value", raising=False)

    labels = [check.label for check in monitor.doctor_secret_checks(None)]

    assert "Secrets loaded from the command line" in labels
    assert "Secrets loaded from the configuration file or command line" not in labels


# Verifies the Python row states the minimum it was judged against and that the fix names the same minimum
def test_the_python_row_names_the_minimum_supported_version():
    supported = monitor.doctor_check_environment((3, 9, 0), all_dependencies_present)[0]
    unsupported = monitor.doctor_check_environment((3, 8, 18), all_dependencies_present)[0]

    assert supported.detail == f"Minimum supported version: {monitor.MINIMUM_PYTHON_VERSION_TEXT}"
    assert unsupported.detail == supported.detail
    assert monitor.MINIMUM_PYTHON_VERSION_TEXT in require_advice(unsupported).fix


# Verifies valid numeric settings take no row, since a value that is merely fine is not a finding
def test_valid_numeric_settings_take_no_row(monkeypatch):
    configure_valid_doctor(monkeypatch)

    checks = monitor.doctor_check_configuration()

    assert not any("numeric" in check.label.casefold() for check in checks)


# Verifies every doctor detail keeps to the agreed shapes: it never repeats its label, gives an instruction or joins values with a pipe
def test_doctor_details_keep_to_the_agreed_shapes():
    import ast
    import inspect

    # Renders one detail argument as text, standing in {} for the parts an f-string fills at runtime
    def detail_text(node):
        if isinstance(node, ast.Constant):
            return node.value if isinstance(node.value, str) else None
        if isinstance(node, ast.JoinedStr):
            return "".join(part.value if isinstance(part, ast.Constant) and isinstance(part.value, str) else "{}" for part in node.values)
        return None

    offenders = []
    for node in ast.walk(ast.parse(inspect.getsource(monitor))):
        if not isinstance(node, ast.Call) or ast.unparse(node.func) not in {"make_doctor_check", "report.add"} or len(node.args) < 4:
            continue
        label, text = node.args[2], detail_text(node.args[3])
        if text is None:
            continue
        if isinstance(label, ast.Constant) and text == label.value:
            offenders.append(f"{node.lineno}: the detail repeats its label")
        if text.startswith(("Use ", "Set ", "Run ")):
            offenders.append(f"{node.lineno}: the detail gives an instruction, which belongs in the fix line")
        if " | " in text:
            offenders.append(f"{node.lineno}: the detail joins two values with a pipe")
        if text.endswith("."):
            offenders.append(f"{node.lineno}: the detail ends with a full stop")

    assert not offenders, "doctor details outside the agreed shapes:\n" + "\n".join(offenders)


# Verifies the constructor drops a detail that only repeats its label, so no row says the same thing twice
def test_a_detail_that_repeats_its_label_is_dropped():
    check = monitor.make_doctor_check("Configuration", "PASS", "Output logging is disabled", "Output logging is disabled")

    assert check.detail == ""


# Verifies a row the user has to act on cannot reach the report without an action
def test_an_actionable_row_is_rejected_without_a_fix():
    for status in ("WARN", "FAIL"):
        with pytest.raises(ValueError):
            monitor.make_doctor_check("Configuration", status, "a label", "some detail")

    assert monitor.make_doctor_check("Configuration", "SKIP", "a label").status == "SKIP"


# Verifies only the four shared markers can reach a report
def test_only_the_four_shared_markers_are_accepted():
    assert monitor.DOCTOR_STATUSES == ("PASS", "WARN", "FAIL", "SKIP")
    assert [monitor.make_doctor_check("Configuration", status, "a label", advice=actionable_advice()).status for status in monitor.DOCTOR_STATUSES] == list(monitor.DOCTOR_STATUSES)

    with pytest.raises(ValueError):
        monitor.make_doctor_check("Configuration", "INFO", "a label")


# Verifies one row reads as one block: the action lines sit under the marker at the detail indent while a pass row has none
def test_the_action_lines_sit_indented_under_their_marker(monkeypatch):
    monkeypatch.setattr(monitor, "colorize", lambda theme, text: text)
    advice = monitor.make_recovery_advice("unknown", "a summary", monitor.recovery_fix_with_guide("do the thing", monitor.DOCTOR_GUIDE_URL), True)
    report = monitor.DoctorReport([
        monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice),
        monitor.make_doctor_check("Configuration", "PASS", "a passing row", "", advice),
    ])

    lines = render_doctor_report(report).splitlines()
    rows = lines[lines.index("[WARN] a warning row"):]

    assert rows[:5] == ["[WARN] a warning row", "  a detail worth keeping", "  To fix: do the thing", f"  Guide: {monitor.DOCTOR_GUIDE_URL}", "[PASS] a passing row"]


# Verifies an approved delivery test that failed reaches the summary, so a failing run cannot report a clean one
def test_a_failed_delivery_test_reaches_the_summary(monkeypatch):
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", monitor.SMTP_READY_CHECK_LABEL)])
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", TTYBuffer())
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", Mock(return_value=True))
    monkeypatch.setattr(monitor, "send_email", Mock(return_value=1))

    monitor._doctor_offer_notification_tests(report)

    assert [(check.section, check.status, check.label) for check in report.checks][-1] == (monitor.DOCTOR_DELIVERY_SECTION, "FAIL", "Doctor test email delivery failed")
    assert "1 check(s) failed, 0 warning(s)." in monitor.render_doctor_summary(report.checks)


# Verifies every doctor entry point renders its summary after the delivery tests, so the sentence and the exit code describe one run
def test_the_summary_is_rendered_after_the_delivery_tests():
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(monitor))
    checked = 0
    for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        calls = [(call.lineno, ast.unparse(call.func)) for call in ast.walk(function) if isinstance(call, ast.Call)]
        offers = [lineno for lineno, name in calls if name.endswith("_doctor_offer_notification_tests")]
        summaries = [lineno for lineno, name in calls if name.endswith("render_doctor_summary")]
        if not offers or not summaries:
            continue
        checked += 1
        assert max(offers) < min(summaries), f"{function.name} renders the summary before the delivery tests"

    assert checked, "no doctor entry point runs the delivery tests and then the summary"


# Verifies the connectivity row carries the label and the endpoint detail shared with the sibling monitors
def test_the_connectivity_row_names_the_shared_endpoint(monkeypatch):
    monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://probe.example/ping")
    monkeypatch.setattr(monitor, "check_internet", lambda **kwargs: True)
    passing = monitor.doctor_connectivity_endpoint_check()
    monkeypatch.setattr(monitor, "check_internet", lambda **kwargs: False)
    failing = monitor.doctor_connectivity_endpoint_check()

    assert (passing.status, passing.label, passing.detail) == ("PASS", "The connectivity endpoint is reachable", "Endpoint: https://probe.example/ping")
    assert (failing.status, failing.label, failing.detail) == ("FAIL", "The connectivity endpoint could not be reached", "Endpoint: https://probe.example/ping")
    assert failing.advice is not None and failing.advice.fix == "Check network, DNS, proxy and CHECK_INTERNET_URL settings"


# Verifies Ctrl+C at a delivery prompt ends the run instead of declining one test and asking the next
def test_a_delivery_prompt_interrupt_ends_the_run(monkeypatch):
    def interrupt(prompt=""):
        raise KeyboardInterrupt

    # The handler restores the saved stream, so it is pointed at the one this test captures
    monkeypatch.setattr(monitor, "stdout_bck", monitor.sys.stdout)
    monkeypatch.setattr(monitor, "FLAG_FILE", "")
    monkeypatch.setattr("builtins.input", interrupt)

    with pytest.raises(SystemExit) as raised:
        monitor._doctor_ask_yes_no("Send one test")

    assert raised.value.code == 0


# An interval below the safe floor gets the account rate limited, which looks like the tool being broken
def test_a_rate_limiting_interval_is_warned_about(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", "buddylist")
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 5)

    rows = [item for item in monitor.doctor_check_configuration() if item.label == "Check intervals are short"]

    assert [item.status for item in rows] == ["WARN"]
    assert "SPOTIFY_CHECK_INTERVAL" in rows[0].detail
    assert str(monitor.DOCTOR_MIN_SAFE_CHECK_INTERVAL) in require_advice(rows[0]).fix


# The default interval is safe, so the row must stay away rather than warning about every run
def test_a_safe_interval_is_not_warned_about(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", "buddylist")
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", monitor.DOCTOR_MIN_SAFE_CHECK_INTERVAL)

    assert not [item for item in monitor.doctor_check_configuration() if item.label == "Check intervals are short"]


# The live backend judges its own timers against the lower live floor, so the legacy value and the live defaults stay quiet
def test_live_intervals_are_judged_against_the_live_floor(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", "listening_activity")
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 5)

    assert not [item for item in monitor.doctor_check_configuration() if item.label == "Check intervals are short"]

    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_ACTIVE_CHECK_INTERVAL", monitor.DOCTOR_MIN_SAFE_LIVE_CHECK_INTERVAL - 1)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_CHECK_INTERVAL", 2)
    rows = [item for item in monitor.doctor_check_configuration() if item.label == "Check intervals are short"]

    assert [item.status for item in rows] == ["WARN"]
    assert "SPOTIFY_LIVE_CHECK_INTERVAL" in rows[0].detail and "SPOTIFY_LIVE_ACTIVE_CHECK_INTERVAL" in rows[0].detail
    assert f"at least {monitor.DOCTOR_MIN_SAFE_LIVE_CHECK_INTERVAL} seconds" in require_advice(rows[0]).fix


# A run with no target warns with the sentence every monitor in this family uses, so the report reads the same
def test_a_missing_target_warns_with_the_shared_detail(monkeypatch):
    configure_valid_doctor(monkeypatch)

    checks = monitor.doctor_check_target(monitor.DoctorReport(), None)

    assert [check.status for check in checks] == ["WARN"]
    assert checks[0].detail == "Nothing will be monitored until one is given"


# Verifies a quoted interval is reported as an unusable setting, since comparing it against the safe floor used to raise
def test_an_interval_that_is_not_a_number_is_reported_rather_than_raised(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", "3600")

    labels = [item.label for item in monitor.doctor_check_configuration()]

    assert "One or more numeric settings are invalid" in labels
    assert "Check intervals are short" not in labels


# Verifies configured mail settings with no alert types selected warn, since nothing would ever be emailed
def test_email_configured_but_nothing_selected_warns(monkeypatch):
    configure_valid_doctor(monkeypatch)
    for name in ("ACTIVE_NOTIFICATION", "INACTIVE_NOTIFICATION", "TRACK_NOTIFICATION", "SONG_NOTIFICATION", "SONG_ON_LOOP_NOTIFICATION", "ERROR_NOTIFICATION"):
        monkeypatch.setattr(monitor, name, False)
    monkeypatch.setattr(monitor, "SMTP_HOST", "smtp.example.test")
    monkeypatch.setattr(monitor, "SMTP_USER", "monitor")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "private-password")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "monitor@example.test")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "alerts@example.test")
    monkeypatch.setattr(monitor, "smtp_connect_and_login", Mock(side_effect=AssertionError("SMTP was contacted")))

    check = monitor.doctor_check_notifications()[0]

    assert (check.status, check.label) == ("WARN", "Email is configured but no alert types are selected")
    assert check.detail == "Nothing would ever be emailed"
    assert require_advice(check).code == "smtp.invalid"


# Verifies webhook alert types selected while the channel is off warn, since nothing would ever be delivered
def test_webhook_alerts_selected_but_switched_off_warn(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_NOTIFICATION", True)

    check = monitor.doctor_check_webhook_notifications()[0]

    assert (check.status, check.label) == ("WARN", "Webhook alert types are selected but webhooks are switched off")
    assert "WEBHOOK_ENABLED" in require_advice(check).fix


# One row shape and one advice shape across the family: the advice rides on the row and its fix carries the
# guide, so a row or an advice copied from a sibling means the same thing here
def test_the_doctor_row_and_its_advice_share_one_contract():
    row_parameters = list(inspect.signature(monitor.make_doctor_check).parameters.values())
    advice_parameters = list(inspect.signature(monitor.make_recovery_advice).parameters.values())

    assert [parameter.name for parameter in row_parameters] == ["section", "status", "label", "detail", "advice"]
    assert [parameter.default for parameter in row_parameters[3:]] == ["", None]
    assert [parameter.name for parameter in advice_parameters] == ["code", "summary", "fix", "retryable", "detail"]
    assert monitor.recovery_fix_with_guide("do the thing", "https://example.invalid/page") == "do the thing\nGuide: https://example.invalid/page"


# A non-pass row is refused without advice and keeps the advice it was given, which is where its fix and guide live
def test_a_row_carries_its_advice_and_refuses_to_go_without():
    advice = monitor.make_recovery_advice("config.invalid", "a warning row", monitor.recovery_fix_with_guide("do the thing", monitor.DOCTOR_GUIDE_URL), False)

    row = monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping", advice)

    assert row.advice is advice
    assert not hasattr(advice, "guide_url")
    with pytest.raises(ValueError):
        monitor.make_doctor_check("Configuration", "WARN", "a warning row", "a detail worth keeping")


# A string such as "false" counts as on, so an on/off setting holding anything but True or False is named in one row
def test_invalid_boolean_settings_are_reported_in_one_row(monkeypatch):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", "false", raising=False)
    monkeypatch.setattr(monitor, "SMTP_SSL", 1, raising=False)

    rows = [item for item in monitor.doctor_check_configuration() if item.label == "One or more on/off settings are invalid"]

    assert [item.status for item in rows] == ["FAIL"]
    assert "ERROR_NOTIFICATION must be True or False, not 'false'" in rows[0].detail
    assert "SMTP_SSL must be True or False, not 1" in rows[0].detail
    assert require_advice(rows[0]).code == "config.invalid"


# An on/off setting written as 0 or 1 was accepted before the values were checked, so it still reads as off and on
def test_a_numeric_on_off_setting_is_read_as_a_boolean():
    parsed = monitor.parse_config_content("VERIFY_SSL = 0\nDISABLE_LOGGING = 1\n")

    assert parsed == {"VERIFY_SSL": False, "DISABLE_LOGGING": True}
    assert all(isinstance(value, bool) for value in parsed.values())


# The shipped defaults are all real booleans, so a run with nothing overridden never sees the on/off row
def test_the_shipped_defaults_pass_the_boolean_check():
    assert monitor.runtime_boolean_errors() == []


# A malformed destination is a FAIL under the label every tool in the family uses, so a fix reads the same everywhere
def test_a_malformed_webhook_url_fails_under_the_family_label(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "discord.com/api/webhooks/1/abc")

    check = monitor.doctor_check_webhook_notifications()[0]

    assert (check.status, check.label) == ("FAIL", "WEBHOOK_URL must contain a complete HTTPS link")
    assert require_advice(check).code == "webhook.invalid"
