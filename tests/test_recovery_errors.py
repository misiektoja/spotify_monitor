import io
import smtplib
import socket
from contextlib import redirect_stdout

import pytest
import requests

import spotify_monitor as monitor


# Creates a requests HTTP error carrying one status code
def make_http_error(status_code):
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://spotify.test/resource"
    return requests.HTTPError(f"HTTP {status_code}", response=response)


# Verifies the published recovery category set remains stable
def test_recovery_codes_are_stable():
    assert monitor.RECOVERY_CODES == frozenset({"config.missing", "config.invalid", "dependency.missing", "secret.missing", "auth.cookie_invalid", "auth.client_invalid", "auth.rejected", "network.unavailable", "network.timeout", "spotify.rate_limited", "spotify.unavailable", "target.invalid", "target.not_found", "target.not_visible", "smtp.invalid", "smtp.authentication", "smtp.connection", "webhook.invalid", "webhook.rejected", "webhook.rate_limited", "webhook.connection", "file.unreadable", "file.unwritable", "unknown"})


# Verifies HTTP status classification uses explicit Spotify context
@pytest.mark.parametrize("status,context,code", [(401, "cookie_auth", "auth.cookie_invalid"), (401, "client_auth", "auth.client_invalid"), (403, "metadata", "spotify.unavailable"), (403, "cookie_auth", "auth.rejected"), (404, "target", "target.not_found"), (429, "runtime", "spotify.rate_limited"), (500, "runtime", "spotify.unavailable"), (503, "runtime", "spotify.unavailable")])
def test_http_status_classification_is_context_sensitive(status, context, code):
    assert monitor.classify_recovery_error(make_http_error(status), context).code == code


# Verifies restricted legacy metadata points Development Mode app owners to Premium first
def test_legacy_metadata_recovery_mentions_app_owner_premium():
    advice = monitor.classify_recovery_error(make_http_error(403), "metadata")
    assert "owner has active Spotify Premium" in advice.fix
    assert "automatic web-player fallback" in advice.fix


# Verifies cookie failures recommend the portable Firefox import command
def test_cookie_recovery_recommends_firefox_import(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    advice = monitor.classify_recovery_error(RuntimeError("unsuccessful token request"), "cookie_auth")
    assert advice.code == "auth.cookie_invalid"
    assert monitor.SPOTIFY_WEB_LOGIN_URL in advice.fix
    assert "spotify_monitor --import-browser-cookie --browser firefox" in advice.fix


# Verifies manual script recovery uses the matching portable command
def test_cookie_recovery_matches_manual_script_install(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
    advice = monitor.classify_recovery_error(RuntimeError("unsuccessful token request"), "cookie_auth")
    assert "python3 spotify_monitor.py --import-browser-cookie --browser firefox" in advice.fix
    assert "spotify_monitor --import-browser-cookie" not in advice.fix


# Verifies container cookie recovery prefers hidden entry and retains mounted Firefox guidance
def test_container_cookie_recovery_prefers_private_entry(monkeypatch):
    monkeypatch.setattr(monitor, "is_container_environment", lambda: True)
    monkeypatch.setenv("SPOTIFY_MONITOR_COMPOSE", "1")
    advice = monitor.classify_recovery_error(RuntimeError("unsuccessful token request"), "cookie_auth")
    assert "docker compose run --rm spotify_monitor --set-sp-dc --env-file /data/.env" in advice.fix
    assert "Advanced Firefox alternative" in advice.fix
    assert advice.fix.index("--set-sp-dc") < advice.fix.index("--import-browser-cookie")
    assert monitor.MANUAL_COOKIE_GUIDE_URL in advice.fix


# Verifies client refresh failures point back to advanced desktop setup
def test_client_refresh_recovery_is_specific():
    advice = monitor.classify_recovery_error(RuntimeError("refresh token has expired"), "client_auth")
    assert advice.code == "auth.client_invalid"
    assert "Spotify Desktop Client" in advice.fix


# Verifies typed connection and timeout failures remain distinct
@pytest.mark.parametrize("error,code", [(requests.ConnectionError("connection refused"), "network.unavailable"), (socket.gaierror("name resolution"), "network.unavailable"), (requests.Timeout("request timed out"), "network.timeout")])
def test_typed_network_failures(error, code):
    assert monitor.classify_recovery_error(error).code == code


# Verifies TLS failures never recommend disabling certificate verification
def test_tls_failure_has_safe_recovery():
    advice = monitor.classify_recovery_error(requests.exceptions.SSLError("certificate verify failed"))
    assert advice.code == "network.unavailable"
    assert "disable" not in advice.fix.lower()


# Verifies target recovery categories distinguish input and visibility failures
@pytest.mark.parametrize("context,code", [("target_missing", "target.invalid"), ("target_invalid", "target.invalid"), ("target_not_visible", "target.not_visible")])
def test_target_recovery_categories(context, code):
    assert monitor.classify_recovery_error(context=context).code == code


# Verifies target visibility guidance includes a directly usable profile link when the ID is known
def test_target_visibility_recovery_includes_profile_link():
    advice = monitor.classify_recovery_error(context="target_not_visible", target_user_id="friend.user")
    assert "Profile: https://open.spotify.com/user/friend.user" in advice.fix
    assert advice.fix.index("Profile:") < advice.fix.index("Guide:")


# Verifies SMTP failures distinguish config authentication and connectivity
def test_smtp_recovery_categories():
    auth_error = smtplib.SMTPAuthenticationError(535, b"bad credentials")
    assert monitor.classify_recovery_error(context="smtp_config").code == "smtp.invalid"
    assert monitor.classify_recovery_error(auth_error, "smtp").code == "smtp.authentication"
    assert monitor.classify_recovery_error(requests.ConnectionError("connection refused"), "smtp").code == "smtp.connection"


# Verifies webhook failures stay distinct from Spotify rate-limit categories
def test_webhook_recovery_categories():
    assert monitor.classify_recovery_error(context="webhook_config").code == "webhook.invalid"
    assert monitor.classify_recovery_error(make_http_error(404), "webhook").code == "webhook.rejected"
    assert monitor.classify_recovery_error(make_http_error(429), "webhook").code == "webhook.rate_limited"
    assert monitor.classify_recovery_error(make_http_error(503), "webhook").code == "webhook.connection"
    assert monitor.classify_recovery_error(make_http_error(429), "runtime").code == "spotify.rate_limited"


# Verifies webhook recovery uses the published configuration guide
def test_webhook_recovery_guide_uses_generic_anchor():
    assert monitor.WEBHOOK_GUIDE_URL == monitor.DOCUMENTATION_URL + "/configuration/#webhook-settings"
    assert monitor.WEBHOOK_GUIDE_URL in monitor.classify_recovery_error(context="webhook_config").fix


# Verifies file access contexts map to read and write categories
def test_file_recovery_categories():
    assert monitor.classify_recovery_error(PermissionError("denied"), "file_read").code == "file.unreadable"
    assert monitor.classify_recovery_error(PermissionError("denied"), "file_write").code == "file.unwritable"


# Verifies unknown failures provide a safe diagnostic next step
def test_unknown_error_has_safe_next_step():
    advice = monitor.classify_recovery_error(RuntimeError("unexpected shape"))
    assert advice.code == "unknown"
    assert "--doctor" in advice.fix


# Verifies common onboarding failures link directly to the relevant documentation section
def test_recovery_guides_target_relevant_documentation():
    cases = (
        (monitor.classify_recovery_error(context="config_missing"), monitor.CONFIG_GUIDE_URL),
        (monitor.classify_recovery_error(RuntimeError("unsuccessful token request"), "cookie_auth"), monitor.COOKIE_GUIDE_URL),
        (monitor.classify_recovery_error(RuntimeError("refresh token expired"), "client_auth"), monitor.CLIENT_GUIDE_URL),
        (monitor.classify_recovery_error(context="target_not_visible"), monitor.FOLLOWING_GUIDE_URL),
        (monitor.classify_recovery_error(context="smtp_config"), monitor.SMTP_GUIDE_URL),
        (monitor.classify_recovery_error(make_http_error(429)), monitor.INTERVALS_GUIDE_URL),
    )
    for advice, guide_url in cases:
        assert f"\nGuide: {guide_url}" in advice.fix


# Verifies manual cookie entry failures link directly to extraction steps
def test_manual_cookie_recovery_uses_extraction_guide():
    advice = monitor.classify_recovery_error(RuntimeError("invalid or expired"), "set_sp_dc")
    assert monitor.MANUAL_COOKIE_GUIDE_URL == monitor.DOCUMENTATION_URL + "/configuration/#manual-cookie-extraction"
    assert monitor.MANUAL_COOKIE_GUIDE_URL in advice.fix
    assert monitor.COOKIE_GUIDE_URL not in advice.fix


# Verifies recovery output keeps every hint line flush left
def test_recovery_output_has_no_indented_hint_lines():
    rendered = monitor.render_recovery_error(RuntimeError("unexpected shape"), debug=True)
    assert "\nTo fix:" in rendered
    assert "\nGuide:" in rendered
    assert "\nTechnical detail:" in rendered
    assert not any(line.startswith((" ", "\t")) for line in rendered.splitlines())


# Verifies complete values and common serialized credentials are redacted
def test_secret_redaction_covers_values_and_serialized_forms(monkeypatch):
    secret = "FAKE-SECRET-VALUE-123456"
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", secret)
    text = f"Authorization: Bearer bearer-value Cookie: sp_dc=cookie-value access_token='access-value' refresh_token=refresh-value client-token: client-value smtp_password={secret}"
    sanitized = monitor.sanitize_error_text(text)
    for value in (secret, "bearer-value", "cookie-value", "access-value", "refresh-value", "client-value"):
        assert value not in sanitized
    assert sanitized.count("<redacted>") >= 6


# Verifies webhook URL secrets are redacted from assignments and request errors
def test_webhook_secret_redaction(monkeypatch):
    secret = "https://discord.com/api/webhooks/123/private-token"
    monkeypatch.setattr(monitor, "WEBHOOK_URL", secret)
    sanitized = monitor.sanitize_error_text(f"WEBHOOK_URL={secret}\nrequest failed for {secret}")
    assert secret not in sanitized
    assert sanitized.count("<redacted>") >= 2


# Verifies normal and debug recovery rendering never exposes a configured secret
@pytest.mark.parametrize("debug", [False, True])
def test_recovery_rendering_is_secret_safe(monkeypatch, debug):
    secret = "FAKE-COOKIE-DO-NOT-PRINT"
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", secret)
    rendered = monitor.render_recovery_error(RuntimeError(f"request failed with sp_dc={secret}"), "cookie_auth", debug=debug)
    assert secret not in rendered
    assert "To fix:" in rendered
    assert ("Technical detail:" in rendered) is debug


# Verifies debug logging sanitizes configured secrets before capture
def test_debug_log_output_is_secret_safe(monkeypatch, capsys):
    secret = "FAKE-DEBUG-SECRET"
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", secret)
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monitor.debug_print(f"cookie={secret}")
    assert secret not in capsys.readouterr().out


# Verifies structured recovery exception strings expose only the safe summary
def test_recovery_exception_string_is_safe(monkeypatch):
    secret = "FAKE-EXCEPTION-SECRET"
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", secret)
    cause = RuntimeError(f"401 cookie {secret}")
    advice = monitor.classify_recovery_error(cause, "cookie_auth")
    recovery_error = monitor.RecoveryError(advice, cause)
    assert secret not in str(recovery_error)
    assert recovery_error.__cause__ is cause


# Verifies repeated monitoring hints are suppressed until a success resets state
def test_monitoring_hint_deduplication_and_reset(capsys):
    tracker = monitor.RecoveryHintTracker()
    error = requests.ConnectionError("connection refused")
    monitor.print_monitor_recovery(error, "runtime", tracker, "* Error: ")
    monitor.print_monitor_recovery(error, "runtime", tracker, "* Error: ")
    first_output = capsys.readouterr().out
    assert first_output.count("To fix:") == 1
    tracker.reset()
    monitor.print_monitor_recovery(error, "runtime", tracker, "* Error: ")
    assert capsys.readouterr().out.count("To fix:") == 1


# Verifies a changed monitoring category prints a new recovery hint
def test_monitoring_hint_category_change(capsys):
    tracker = monitor.RecoveryHintTracker()
    monitor.print_monitor_recovery(requests.ConnectionError("connection refused"), "runtime", tracker, "* Error: ")
    monitor.print_monitor_recovery(make_http_error(429), "runtime", tracker, "* Error: ")
    assert capsys.readouterr().out.count("To fix:") == 2


# Verifies browser import rendering keeps safe messages while adding a fix line
def test_browser_import_recovery_preserves_safe_message():
    error = monitor.BrowserCookieImportError("No sp_dc cookie for spotify.com was found")
    rendered = monitor.render_recovery_error(error, "browser_import")
    assert "No sp_dc cookie" in rendered
    assert "To fix:" in rendered


# Verifies redirected stdout captures no configured secret from recovery output
def test_captured_recovery_output_is_secret_safe(monkeypatch):
    secret = "FAKE-CAPTURED-SECRET"
    monkeypatch.setattr(monitor, "REFRESH_TOKEN", secret)
    output = io.StringIO()
    with redirect_stdout(output):
        monitor.print_recovery_error(RuntimeError(f"refresh token {secret} is invalid"), "client_auth", debug=True)
    assert secret not in output.getvalue()
