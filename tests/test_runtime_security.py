"""Regression tests for runtime deadlines, playback commands and cookie polling."""

import ast
import time
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, call

import pytest

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "request"}
HOSTILE_NAME = "Friend\x1b[2J\x1b[8mhidden\rOVERWRITTEN\x07\x9bA\ttab"


# Asserts no cursor, screen or title control sequence survived, allowing only the inert SGR colour codes this tool emits
def assert_no_terminal_controls(output: str) -> None:
    assert "\r" not in output and "\x07" not in output and "\x9b" not in output
    assert monitor.SGR_SEQUENCE_RE.sub("", output).count("\x1b") == 0


# Collects every outgoing HTTP call in the module together with the verify argument it passes
def http_calls_with_verification():
    tree = ast.parse((PROJECT_ROOT / "spotify_monitor.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in HTTP_METHODS:
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
        if "timeout" not in keywords and "verify" not in keywords:
            continue
        verify = keywords.get("verify")
        yield node.lineno, ast.unparse(node.func.value), None if verify is None else ast.unparse(verify)


@pytest.mark.parametrize("control", ["\x1b", "\r", "\x07", "\x00", "\x08", "\x0b", "\x0c", "\x7f", "\x9b"])
# Confirms every terminal control character is removed from Spotify-supplied text
def test_sanitize_terminal_text_strips_control_characters(control):
    assert control not in monitor.sanitize_terminal_text(f"name{control}payload")


# Confirms the terminal and logger stream boundaries sanitize untrusted text
def test_output_streams_sanitize_terminal_controls():
    terminal = StringIO()
    stream = monitor.TerminalStream(terminal)
    stream.write(HOSTILE_NAME + "\n")
    logger_terminal = StringIO()
    logger_log = StringIO()
    logger = monitor.Logger.__new__(monitor.Logger)
    logger.__dict__["terminal"] = logger_terminal
    logger.__dict__["logfile"] = logger_log
    logger.write(HOSTILE_NAME + "\n")

    for output in (terminal.getvalue(), logger_terminal.getvalue(), logger_log.getvalue()):
        assert "OVERWRITTEN" in output
        assert_no_terminal_controls(output)


# Confirms the early-exit friend listing is sanitized before logging policy is resolved
def test_list_friends_cli_sanitizes_before_exit(monkeypatch, capsys):
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor", "--list-friends", "--spotify-dc-cookie", "test-cookie", "--env-file", "none"])
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", False)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "USER_AGENT", "test-agent")
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "check_internet", lambda: True)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "test-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: {"friends": []})
    monkeypatch.setattr(monitor, "spotify_list_friends", lambda friends, token: print(HOSTILE_NAME))

    with pytest.raises(SystemExit) as error:
        monitor.main()

    output = capsys.readouterr().out
    assert error.value.code == 0
    assert "OVERWRITTEN" in output
    assert_no_terminal_controls(output)


# Verifies a nested request alarm restores the earlier loop-wide deadline
def test_nested_timeout_alarm_restores_outer_deadline(monkeypatch):
    if not hasattr(monitor.signal, "setitimer"):
        pytest.skip("POSIX interval timers are unavailable on Windows")
    get_handler = Mock(side_effect=["original-handler", monitor.timeout_handler])
    get_timer = Mock(side_effect=[(0.0, 0.0), (28.0, 0.0)])
    set_handler = Mock()
    set_timer = Mock()
    monotonic = Mock(side_effect=[100.0, 102.0, 103.0, 106.0])
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor.signal, "getsignal", get_handler)
    monkeypatch.setattr(monitor.signal, "getitimer", get_timer)
    monkeypatch.setattr(monitor.signal, "signal", set_handler)
    monkeypatch.setattr(monitor.signal, "setitimer", set_timer)
    monkeypatch.setattr(monitor.time, "monotonic", monotonic)

    outer_state = monitor._start_timeout_alarm(30)
    inner_state = monitor._start_timeout_alarm(60)
    monitor._restore_timeout_alarm(inner_state)
    monitor._restore_timeout_alarm(outer_state)

    assert set_timer.call_args_list == [
        call(monitor.signal.ITIMER_REAL, 30.0),
        call(monitor.signal.ITIMER_REAL, 28.0),
        call(monitor.signal.ITIMER_REAL, 27.0, 0.0),
        call(monitor.signal.ITIMER_REAL, 0, 0.0),
    ]
    assert set_handler.call_args_list[-2:] == [call(monitor.signal.SIGALRM, monitor.timeout_handler), call(monitor.signal.SIGALRM, "original-handler")]


# Verifies Windows retains request timeouts without attempting unsupported alarms
def test_timeout_alarm_is_noop_on_windows(monkeypatch):
    get_timer = Mock()
    monkeypatch.setattr(monitor.platform, "system", lambda: "Windows")
    monkeypatch.setattr(monitor.signal, "getitimer", get_timer, raising=False)

    assert monitor._start_timeout_alarm(30) is None
    monitor._restore_timeout_alarm(None)
    get_timer.assert_not_called()


# Verifies cached cookie tokens avoid a redundant buddy-list validity probe
def test_cached_cookie_token_skips_validity_probe(monkeypatch):
    validity_check = Mock(side_effect=AssertionError("redundant buddy-list request"))
    monkeypatch.setattr(monitor, "SP_CACHED_ACCESS_TOKEN", "cached-token")
    monkeypatch.setattr(monitor, "SP_ACCESS_TOKEN_EXPIRES_AT", time.time() + 300)
    monkeypatch.setattr(monitor, "SP_CACHED_CLIENT_ID", "client-id")
    monkeypatch.setattr(monitor, "check_token_validity", validity_check)

    assert monitor.spotify_get_access_token_from_sp_dc("cookie") == "cached-token"
    validity_check.assert_not_called()


# Verifies a successful refresh is returned without a second validity request
def test_refreshed_cookie_token_skips_duplicate_validity_probe(monkeypatch):
    validity_check = Mock(side_effect=AssertionError("duplicate buddy-list request"))
    monkeypatch.setattr(monitor, "SP_CACHED_ACCESS_TOKEN", None)
    monkeypatch.setattr(monitor, "SP_ACCESS_TOKEN_EXPIRES_AT", 0)
    monkeypatch.setattr(monitor, "refresh_access_token_from_sp_dc", lambda cookie: {"access_token": "fresh-token", "expires_at": int(time.time()) + 300, "client_id": "client-id", "length": 11})
    monkeypatch.setattr(monitor, "check_token_validity", validity_check)

    assert monitor.spotify_get_access_token_from_sp_dc("cookie") == "fresh-token"
    validity_check.assert_not_called()


# Verifies cached client tokens avoid a redundant buddy-list validity probe
def test_cached_client_token_skips_validity_probe(monkeypatch):
    validity_check = Mock(side_effect=AssertionError("redundant buddy-list request"))
    monkeypatch.setattr(monitor, "SP_CACHED_ACCESS_TOKEN", "cached-token")
    monkeypatch.setattr(monitor, "SP_ACCESS_TOKEN_EXPIRES_AT", time.time() + 300)
    monkeypatch.setattr(monitor, "check_token_validity", validity_check)

    assert monitor.spotify_get_access_token_from_client("device", "system", "user", "refresh", "client-token") == "cached-token"
    validity_check.assert_not_called()


# Verifies an expired cached client token is refreshed instead of returned
def test_expired_client_token_is_refreshed(monkeypatch):
    monkeypatch.setattr(monitor, "SP_CACHED_ACCESS_TOKEN", "stale-token")
    monkeypatch.setattr(monitor, "SP_ACCESS_TOKEN_EXPIRES_AT", time.time() - 1)
    monkeypatch.setattr(monitor, "check_token_validity", Mock(side_effect=AssertionError("redundant buddy-list request")))
    monkeypatch.setattr(monitor, "build_spotify_auth_protobuf", lambda *arguments: b"body")
    # Matching the message keeps the mocked buddy-list AssertionError from satisfying this assertion
    with pytest.raises(Exception, match="Client token is missing"):
        monitor.spotify_get_access_token_from_client("device", "system", "user", "refresh", "")


# Verifies externally supplied track text cannot reach a local command sink
@pytest.mark.parametrize("player", [monitor.spotify_macos_play_song, monitor.spotify_linux_play_song, monitor.spotify_win_play_song])
def test_playback_rejects_command_injection_before_launch(monkeypatch, player):
    subprocess_call = Mock()
    subprocess_open = Mock()
    monkeypatch.setattr(monitor.subprocess, "call", subprocess_call)
    monkeypatch.setattr(monitor.subprocess, "Popen", subprocess_open)

    with pytest.raises(ValueError, match="ASCII letters and digits"):
        player("abc'; touch /tmp/injected #")

    subprocess_call.assert_not_called()
    subprocess_open.assert_not_called()


# Verifies unsafe configured offline-track text fails startup validation
def test_offline_track_configuration_rejects_command_text(monkeypatch):
    monkeypatch.setattr(monitor, "SP_USER_GOT_OFFLINE_TRACK_ID", "abc'; touch /tmp/injected #")

    assert "SP_USER_GOT_OFFLINE_TRACK_ID must be a raw Spotify track ID containing only ASCII letters and digits" in monitor.runtime_configuration_errors()


# Verifies Linux playback passes the Spotify URI as one argument without a shell
def test_linux_playback_uses_argument_vector(monkeypatch):
    subprocess_call = Mock(return_value=0)
    monkeypatch.setattr(monitor.subprocess, "call", subprocess_call)

    monitor.spotify_linux_play_song("safeTrack123", method="dbus-send")

    subprocess_call.assert_called_once_with(("dbus-send", "--type=method_call", "--dest=org.mpris.MediaPlayer2.spotify", "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player.OpenUri", "string:spotify:track:safeTrack123"))


# Verifies Windows command playback passes the executable and URI separately
def test_windows_playback_uses_argument_vector(monkeypatch):
    subprocess_call = Mock(return_value=0)
    monkeypatch.setattr(monitor.subprocess, "call", subprocess_call)
    monkeypatch.setattr(monitor.os.path, "expandvars", lambda value: r"C:\Spotify\Spotify.exe")

    monitor.spotify_win_play_song("safeTrack123", method="spotify-cmd")

    subprocess_call.assert_called_once_with((r"C:\Spotify\Spotify.exe", "--uri=spotify:track:safeTrack123"))


# TLS verification must always come from the documented setting, since a call that hardcodes it either
# cannot be turned off for a TLS-inspecting proxy or cannot be turned back on for everyone else. This
# invariant is what the excluded py/request-without-cert-validation CodeQL query would otherwise cover
def test_every_http_call_verifies_through_the_configured_setting():
    calls = list(http_calls_with_verification())
    offenders = [(line, receiver, verify) for line, receiver, verify in calls if verify not in ("VERIFY_SSL", "verify")]

    # A refactor that renames the sessions must not quietly leave this test matching nothing
    assert len(calls) >= 20
    assert offenders == []


# Each in-code CodeQL suppression marks a print the query cannot tell apart from a leak, such as the
# sanitized debug line or a row that names a secret without its value. A suppression is only honoured
# while it sits on its own line directly above the flagged call and each one must carry its reason in
# the comment above it, so a refactor that moves the call or the comment fails here instead of
# silently logging in clear text
def test_every_logging_suppression_sits_above_a_print_with_its_reason():
    lines = (PROJECT_ROOT / "spotify_monitor.py").read_text(encoding="utf-8").splitlines()
    suppressions = [index for index, line in enumerate(lines) if line.strip() == "# codeql[py/clear-text-logging-sensitive-data]"]

    assert len(suppressions) == 8
    for index in suppressions:
        assert "print(" in lines[index + 1]
        reasons = [line for line in lines[max(index - 4, 0):index] if line.strip().startswith("# ")]
        assert reasons, f"line {index + 1} has no reason above its suppression"
    debug_line = next(index for index in suppressions if "sanitize_error_text(message)" in lines[index + 1])
    assert any("sanitize_error_text" in line for line in lines[max(debug_line - 4, 0):debug_line] if line.strip().startswith("#"))


# A setting assigned inside a function without a global declaration becomes a local, so the module value the
# rest of the tool reads never changes. --config-file none was recorded that way and every printed recovery
# command dropped the flag, which is invisible to ruff, to pyright and to any test that patches the module value
def test_every_setting_a_function_assigns_is_declared_global():
    tree = ast.parse((PROJECT_ROOT / "spotify_monitor.py").read_text(encoding="utf-8"))
    module_settings = {target.id for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name) and target.id.isupper()}
    shadowed = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        declared = {name for inner in ast.walk(node) if isinstance(inner, ast.Global) for name in inner.names}
        shadowed.extend(f"{node.name} line {inner.lineno}: {target.id}" for inner in ast.walk(node) if isinstance(inner, ast.Assign) for target in inner.targets if isinstance(target, ast.Name) and target.id in module_settings and target.id not in declared)

    assert sorted(set(shadowed)) == []
