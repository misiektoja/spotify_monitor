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
    rendered = monitor.render_doctor_report(report)
    for section in ("Environment", "Configuration", "Authentication", "Connectivity", "Target", "Notifications", "Summary"):
        assert section in rendered
    assert "[PASS]" in rendered
    assert "0 failure(s)" in rendered
    assert "run only after approval" in rendered
    assert f"Guide: {monitor.DOCTOR_GUIDE_URL}" in rendered


# Verifies a clean report returns success
def test_zero_failures_returns_success(monkeypatch, capsys):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "build_doctor_report", lambda *args, **kwargs: monitor.DoctorReport([monitor.make_doctor_check("Environment", "PASS", "ok")]))
    assert monitor.run_doctor() == 0
    assert "0 failure(s)" in capsys.readouterr().out


# Verifies interactive doctor progress is transient while the final report still renders
def test_doctor_interactive_progress(monkeypatch):
    stream = TTYBuffer()

    # Emits one progress update before returning a passing report
    def build_report(*args, **kwargs):
        kwargs["progress"]("notifications")
        return monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", "ok")])

    monkeypatch.setattr(monitor.sys, "stdout", stream)
    monkeypatch.setattr(monitor, "build_doctor_report", build_report)
    assert monitor.run_doctor() == 0
    output = stream.getvalue()
    assert "* Checking notifications ..." in output
    assert "Doctor\n" in output
    assert "0 failure(s)" in output


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
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", "SMTP connection and login succeeded"), monitor.make_doctor_check("Notifications", "PASS", "Webhook URL and alert choices look valid")])
    consent = Mock(side_effect=[False, False])
    email = Mock(side_effect=AssertionError("email sent without approval"))
    webhook = Mock(side_effect=AssertionError("webhook sent without approval"))
    stream = TTYBuffer()
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor.sys, "stdout", stream)
    monkeypatch.setattr(monitor, "_doctor_ask_yes_no", consent)
    monkeypatch.setattr(monitor, "send_email", email)
    monkeypatch.setattr(monitor, "send_webhook", webhook)
    assert monitor._doctor_offer_notification_tests(report) == []
    assert consent.call_count == 2
    email.assert_not_called()
    webhook.assert_not_called()
    output = stream.getvalue()
    assert "[SKIP] Test email was not sent" in output
    assert "[SKIP] Test webhook was not sent" in output


# Verifies an empty doctor delivery answer defaults safely to no
def test_doctor_delivery_consent_defaults_to_no(monkeypatch):
    prompts = []
    monkeypatch.setattr("builtins.input", lambda prompt: (prompts.append(prompt) or ""))
    assert monitor._doctor_ask_yes_no("Send one test") is False
    assert prompts == ["Send one test [y/N]: "]


# Verifies separately approved doctor tests deliver one email and one webhook
def test_doctor_delivery_tests_send_approved_messages(monkeypatch):
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", "SMTP connection and login succeeded"), monitor.make_doctor_check("Notifications", "PASS", "Webhook URL and alert choices look valid")])
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
    email.assert_called_once_with("spotify_monitor: doctor test email", "This test email was sent after approval in --doctor. Your SMTP delivery settings work.", "", monitor.SMTP_SSL, smtp_timeout=5)
    webhook.assert_called_once_with("Spotify Monitor doctor test", "This test notification was sent after approval in --doctor. Your webhook delivery settings work.", "song", force=True)
    assert "Delivery test summary: 0 failure(s)" in stream.getvalue()


# Verifies noninteractive doctor runs never offer or send delivery tests
def test_noninteractive_doctor_never_offers_delivery_tests(monkeypatch):
    report = monitor.DoctorReport([monitor.make_doctor_check("Notifications", "PASS", "SMTP connection and login succeeded"), monitor.make_doctor_check("Notifications", "PASS", "Webhook URL and alert choices look valid")])
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
    assert any(check.section == "Connectivity" and check.status == "WARN" and "skipped" in check.label.lower() for check in report.checks)
    assert any(check.section == "Target" and check.status == "WARN" and "skipped" in check.label.lower() for check in report.checks)


# Verifies Python version support reports pass and fail states
def test_python_version_check():
    supported = monitor.doctor_check_environment((3, 9, 0), all_dependencies_present)
    unsupported = monitor.doctor_check_environment((3, 8, 18), all_dependencies_present)
    assert supported[0].status == "PASS"
    assert unsupported[0].status == "FAIL"


# Verifies missing optional dependencies are warnings that do not affect normal monitoring
def test_optional_dependency_reporting():
    checks = monitor.doctor_check_environment((3, 9, 0), lambda name: None if name in ("spotipy", "pycookiecheat") else object())
    optional = [check for check in checks if "Optional dependency" in check.label]
    assert len(optional) == 2
    assert all(check.status == "WARN" for check in optional)
    assert all("Normal monitoring is unaffected" in check.detail for check in optional)


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
    result = run_cli(["--doctor", "--config-file", "local/does-not-exist-phase3.conf", "--env-file", "none"], "runtime['run_doctor'] = lambda target, config, env, checks: (print(runtime['render_doctor_report'](runtime['DoctorReport'](list(checks)))) or 1);")
    assert result.returncode == 1
    assert "configuration file was not found" in result.stdout.lower()
    assert "Summary" in result.stdout


# Verifies malformed config diagnostics retain the line and source inside doctor output
def test_malformed_config_is_reported_inside_summary(tmp_path):
    config_path = tmp_path / "broken.conf"
    config_path.write_text('TOKEN_SOURCE = "cookie"\nTARGET_USER_URI_ID = "broken\n', encoding="utf-8")
    result = run_cli(["--doctor", "--config-file", str(config_path), "--env-file", "none"], "runtime['run_doctor'] = lambda target, config, env, checks: (print(runtime['render_doctor_report'](runtime['DoctorReport'](list(checks)))) or 1);")
    assert result.returncode == 1
    assert "Line: 2" in result.stdout
    assert 'TARGET_USER_URI_ID = "broken' in result.stdout
    assert "Summary" in result.stdout


# Verifies an explicit missing dotenv file is a doctor failure
def test_explicit_missing_dotenv_is_reported():
    result = run_cli(["--doctor", "--env-file", "local/does-not-exist-phase3.env"], "runtime['run_doctor'] = lambda target, config, env, checks: (print(runtime['render_doctor_report'](runtime['DoctorReport'](list(checks)))) or 1);")
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


# Verifies invalid web-player TOTP parameters fail the configuration check in cookie mode
def test_invalid_totp_config_fails(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "TOTP_SECRET_CIPHER_BYTES", ())
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


# Verifies a target absent from buddy-list data is not described as deleted
def test_target_absent_from_buddy_list_is_not_visible():
    check = monitor.doctor_check_target(monitor.DoctorReport(buddy_list=buddy_list("someone.else")), "friend.user")[0]
    assert check.status == "FAIL"
    assert require_advice(check).code == "target.not_visible"
    assert "deleted" not in monitor.render_doctor_report(monitor.DoctorReport([check])).lower()


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


# Verifies incomplete enabled SMTP configuration fails before a connection
def test_incomplete_enabled_smtp_config_fails(monkeypatch):
    configure_valid_doctor(monkeypatch)
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "SMTP_HOST", "")
    check = monitor.doctor_check_notifications()[0]
    assert check.status == "FAIL"
    assert require_advice(check).code == "smtp.invalid"


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
    assert secret not in monitor.render_doctor_report(report)


# Verifies the doctor CLI can run without a positional target and bypass normal startup
def test_cli_doctor_without_target_bypasses_normal_startup():
    setup = "runtime['check_internet'] = lambda: (_ for _ in ()).throw(AssertionError('connectivity gate called')); runtime['spotify_monitor_friend_uri'] = lambda *args: (_ for _ in ()).throw(AssertionError('monitor loop called')); runtime['run_doctor'] = lambda *args: 0;"
    result = run_cli(["--doctor", "--env-file", "none"], setup)
    assert result.returncode == 0
    assert "connectivity gate called" not in result.stderr
    assert "monitor loop called" not in result.stderr


# Verifies contradictory doctor action flags are rejected
@pytest.mark.parametrize("flag", ["--import-browser-cookie", "--send-test-email", "--list-friends"])
def test_contradictory_action_flags_are_rejected(flag):
    result = run_cli(["--doctor", flag])
    assert result.returncode == 2
    assert "cannot be combined" in result.stderr
