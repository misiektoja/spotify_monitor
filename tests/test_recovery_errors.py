import ast
import inspect
import io
import re
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
    assert monitor.RECOVERY_CODES == frozenset({"config.missing", "config.invalid", "config.insecure", "dependency.missing", "secret.missing", "secret.entry", "auth.cookie_invalid", "auth.client_invalid", "auth.rejected", "auth.scrobble_expired", "network.unavailable", "network.timeout", "spotify.rate_limited", "spotify.quota_exceeded", "spotify.unavailable", "target.invalid", "target.not_found", "target.not_visible", "smtp.invalid", "smtp.authentication", "smtp.connection", "webhook.invalid", "webhook.rejected", "webhook.rate_limited", "webhook.connection", "file.unreadable", "file.unwritable", "file.exists", "resource.exhausted", "unknown"})


# Verifies a local file descriptor limit is reported as itself rather than as a failure of the call that hit it
def test_a_file_descriptor_limit_is_not_reported_as_a_service_failure():
    try:
        try:
            raise OSError(24, "Too many open files")
        except OSError as inner:
            raise RuntimeError("the Spotify request failed") from inner
    except RuntimeError as error:
        advice = monitor.classify_recovery_error(error)

    assert advice.code == "resource.exhausted"
    assert advice.retryable is False
    assert "not a Spotify problem" in advice.summary
    assert "ulimit -n 4096" in advice.fix


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


# Verifies container cookie recovery points to host-specific guidance and private entry
def test_container_cookie_recovery_prefers_firefox_import(monkeypatch):
    monkeypatch.setattr(monitor, "is_container_environment", lambda: True)
    monkeypatch.setenv("SPOTIFY_MONITOR_COMPOSE", "1")
    advice = monitor.classify_recovery_error(RuntimeError("unsuccessful token request"), "cookie_auth")
    assert "host-specific read-only profile import command" in advice.fix
    assert "Manual fallback with hidden entry" in advice.fix
    assert "docker compose run --rm spotify_monitor --set-sp-dc --env-file /data/.env" in advice.fix
    assert monitor.CONTAINER_FIREFOX_GUIDE_URL in advice.fix


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


# Verifies the setting that makes delivery impossible is named in the summary rather than only under --debug
@pytest.mark.parametrize("setting,value,named", [("SMTP_HOST", "not a host", "SMTP_HOST is not a valid IP address or hostname"), ("SMTP_PORT", 0, "SMTP_PORT is not a port number between 1 and 65535"), ("SENDER_EMAIL", "not-an-address", "SENDER_EMAIL or RECEIVER_EMAIL is not an email address"), ("SMTP_USER", "your_smtp_user", "SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder")])
def test_an_unusable_mail_setting_is_named_in_the_summary(monkeypatch, capsys, setting, value, named):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    for name, usable in (("SMTP_HOST", "smtp.example.com"), ("SMTP_PORT", 587), ("SMTP_USER", "user"), ("SMTP_PASSWORD", "secret"), ("SENDER_EMAIL", "sender@example.com"), ("RECEIVER_EMAIL", "receiver@example.com")):
        monkeypatch.setattr(monitor, name, usable)
    monkeypatch.setattr(monitor, setting, value)

    assert monitor.send_email("subject", "body", "", False) == 1
    assert f"* Error: {named}" in capsys.readouterr().out


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


# Verifies added context does not replace the error text the rules read, which used to make every such failure unknown
@pytest.mark.parametrize("message, expected", [("429 rate limit exceeded", "spotify.rate_limited"), ("Connection timed out", "network.timeout")])
def test_a_caller_supplied_detail_does_not_hide_the_error(message, expected):
    advice = monitor.classify_recovery_error(Exception(message), detail="Cannot read the recent plays")

    assert advice.code == expected
    assert "Cannot read the recent plays" in advice.detail


# Verifies a configured Protobuf file that is not there is reported with a fix instead of a bare line
@pytest.mark.parametrize("setting", ["LOGIN_REQUEST_BODY_FILE", "CLIENTTOKEN_REQUEST_BODY_FILE"])
def test_a_missing_protobuf_file_is_reported_with_a_fix(monkeypatch, tmp_path, capsys, setting):
    if not hasattr(monitor.signal, "SIGHUP"):
        pytest.skip("SIGHUP is unavailable on Windows")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "client")
    monkeypatch.setattr(monitor, "LOGIN_REQUEST_BODY_FILE", "")
    monkeypatch.setattr(monitor, "CLIENTTOKEN_REQUEST_BODY_FILE", "")
    monkeypatch.setattr(monitor, setting, str(tmp_path / "absent.bin"))

    monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)

    printed = capsys.readouterr().out
    assert "* Error: A required file could not be read" in printed
    assert "To fix: Verify the path, file format and read permissions then retry" in printed


# Returns every literal string one argument can evaluate to, following a conditional or a code held in a local name
def literal_values(node, assignments):
    if isinstance(node, ast.Constant):
        return {node.value} if isinstance(node.value, str) else set()
    if isinstance(node, ast.IfExp):
        return literal_values(node.body, assignments) | literal_values(node.orelse, assignments)
    if isinstance(node, ast.Name) and assignments.get(node.id):
        return set().union(*(literal_values(value, assignments) for value in assignments[node.id]))
    return set()


# Returns every code an advice builder can pass, which is what makes a declared code with no producer visible
def builder_codes(source):
    tree = ast.parse(source)
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    codes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("advice", "make_recovery_advice") and node.args:
            codes |= literal_values(node.args[0], assignments)
    return codes


# Verifies every declared code has a producer, so the set records what the tool reports rather than what it might
def test_every_declared_code_is_reachable():
    unreachable = set(monitor.RECOVERY_CODES) - builder_codes(inspect.getsource(monitor))

    assert unreachable == set(), f"codes with no producer: {sorted(unreachable)}"


# Verifies no advice builder names a code outside the declared set, so the set stays the whole taxonomy
def test_no_code_outside_the_declared_set_is_produced():
    undeclared = builder_codes(inspect.getsource(monitor)) - set(monitor.RECOVERY_CODES)

    assert undeclared == set(), f"codes produced but not declared: {sorted(undeclared)}"


# Every place that reports a problem without the classifier and the reason it cannot use one
CLASSIFIER_EXEMPTIONS = {
    "or higher required": "runs at import on an interpreter too old to load the rest of the file",
    "Cannot clear the screen contents": "a cosmetic notice with nothing for the operator to recover from",
    "Operational alert deferred": "a note about when the alert fires, printed under the classified failure above it",
    "Installation could not start": "a wizard result printed above the question that offers another option",
    "could not be installed": "a wizard result printed above the question that offers another option",
    "need the optional Pillow package": "a wizard hint above the question that offers to switch the feature off",
    "artwork cannot be attached": "a wizard hint above the question that offers to switch the feature off",
    "Follow status could not be checked": "a wizard result followed by the step that resumes the setup",
    "follow verification failed": "a wizard result followed by the step that resumes the setup",
    "could not follow the target": "a wizard result followed by the step that resumes the setup",
    "dotenv destination": "a wizard result that reports what was saved and what was not",
    "Setup needs a writable dotenv file": "an answer hint inside the question that re-asks, where the next prompt is the recovery",
    "Redirect URI is invalid": "an answer hint inside the question that re-asks, where the next prompt is the recovery",
    "Missing-play threshold": "a setup summary label rather than a failure",
    "operational error alerts": "a setup summary label rather than a failure",
    "could not write configuration file": "a wizard result that reports what was saved and what was not",
    "Setup was saved": "a wizard result followed by the step that finishes the setup",
    "consecutive missing plays": "a line of setup guidance describing the shipped default",
}

# Words that mark a printed line as a report of something going wrong
TROUBLE_WORDS = re.compile(r"error|cannot|can't|failed|failure|invalid|not valid|missing|not installed|no such|refused|unsupported|needs to be|could not|couldn't|unable to", re.IGNORECASE)


# Returns the literal text one print argument shows, leaving out the parts an f-string fills at runtime
def printed_text(node):
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else ""
    if isinstance(node, ast.JoinedStr):
        return "".join(printed_text(part) for part in node.values)
    if isinstance(node, ast.BinOp):
        return printed_text(node.left) + printed_text(node.right)
    return ""


# Returns every printed line that reads as a problem, paired with the line it sits on
def reported_problems(source):
    found = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}):
            continue
        text = " ".join(printed_text(argument) for argument in node.args)
        if TROUBLE_WORDS.search(text):
            found.append((node.lineno, " ".join(text.split())))
    return found


# A problem reported without a category leaves the reader with a message and no next step
def test_every_reported_problem_goes_through_the_classifier():
    unexplained = [f"line {line}: {text[:120]}" for line, text in reported_problems(inspect.getsource(monitor)) if not any(marker in text for marker in CLASSIFIER_EXEMPTIONS)]

    assert unexplained == []


# An exemption list that stopped matching anything would quietly cover the whole file
def test_the_classifier_guard_still_inspects_the_source():
    source = inspect.getsource(monitor)
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in {"print", "SystemExit"}]
    problems = reported_problems(source)

    assert len(inspected) > 300
    assert all(any(marker in text for _, text in problems) for marker in CLASSIFIER_EXEMPTIONS), "an exemption stopped matching a printed line"


# The only advice that names no page, and the reason no page covers it
GUIDELESS_ADVICE = {
    "The connectivity endpoint did not answer in time": "no page covers this check and the doctor report already ends with the troubleshooting link",
    "The connectivity endpoint could not be reached": "no page covers this check and the doctor report already ends with the troubleshooting link",
}

# The guide sits in this positional slot for each builder, or inside the fix when the signature carries no slot
GUIDE_SLOT = {"advice": 4, "make_recovery_advice": 5}


# True when this builder attaches a documentation link in any of the three shapes the tool uses
def attaches_a_guide(node, source):
    slot = GUIDE_SLOT.get(getattr(node.func, "id", ""))
    if slot is not None and len(node.args) > slot:
        return True
    if any(keyword.arg in ("guide_url", "guide") for keyword in node.keywords):
        return True
    return "recovery_fix_with_guide" in (ast.get_source_segment(source, node.args[2]) or "")


# Returns every expression assigned to each plain name in the module, so a fix held in a variable can be read
def assigned_expressions(tree):
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments.setdefault(target.id, []).append(node.value)
    return assignments


# Returns the text of the summary or fix, resolving one level of plain-name assignment
def resolved_text(node, source, assignments):
    if isinstance(node, ast.Name):
        return " ".join(ast.get_source_segment(source, value) or "" for value in assignments.get(node.id, []))
    return ast.get_source_segment(source, node) or ""


# Returns every advice builder that names no page, paired with the summary it reports
def guideless_advice(source):
    tree = ast.parse(source)
    assignments = assigned_expressions(tree)
    found = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT) or len(node.args) < 3:
            continue
        # A builder that re-wraps an already-classified advice carries whatever guide that advice was given
        if isinstance(node.args[2], ast.Attribute) and node.args[2].attr == "fix":
            continue
        if attaches_a_guide(node, source) or "recovery_fix_with_guide" in resolved_text(node.args[2], source, assignments):
            continue
        found.append((node.lineno, resolved_text(node.args[1], source, assignments)))
    return found


# A failure with no page to read leaves the operator with a one-line fix and nowhere to go next
def test_every_failure_names_a_page():
    source = inspect.getsource(monitor)
    unexplained = [f"line {line}: {summary[:100]}" for line, summary in guideless_advice(source) if not any(marker in summary for marker in GUIDELESS_ADVICE)]

    assert unexplained == []


# An allowlist that stopped matching anything would quietly cover every failure in the file
def test_the_guide_guard_still_inspects_the_source():
    source = inspect.getsource(monitor)
    inspected = [node for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Call) and getattr(node.func, "id", "") in GUIDE_SLOT]
    bare = guideless_advice(source)

    assert len(inspected) > 60
    assert all(any(marker in summary for _, summary in bare) for marker in GUIDELESS_ADVICE), "an allowlisted summary stopped matching a builder"
