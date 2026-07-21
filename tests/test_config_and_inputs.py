import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import dotenv_values

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "spotify_monitor.py"
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "test_artifacts"
ISOLATED_PRELUDE = "import requests, runpy, socket, sys; requests.sessions.Session.request = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network request attempted')); socket.create_connection = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network connection attempted')); "


# Creates a disposable test directory under the project local directory
def make_temp_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT)


# Runs an isolated CLI scenario with real network access blocked
def run_cli(arguments, runtime_setup="", cwd=PROJECT_ROOT):
    source = f"module = runpy.run_path({str(CLI_PATH)!r}, run_name='spotify_monitor_phase1_test'); runtime = module['main'].__globals__; runtime['sys'].argv = {[str(CLI_PATH), *arguments]!r}; runtime['CLEAR_SCREEN'] = False; runtime['signal'].signal = lambda *args, **kwargs: None; {runtime_setup} module['main']()"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-c", ISOLATED_PRELUDE + source], cwd=cwd, capture_output=True, text=True, env=environment, timeout=30, check=False)


# Verifies all accepted target forms normalize to one Spotify user ID
def test_target_normalization_accepts_supported_forms():
    cases = {
        "31abc123": "31abc123",
        "spotify:user:31abc123": "31abc123",
        "https://open.spotify.com/user/31abc123": "31abc123",
        "https://open.spotify.com/user/31abc123/": "31abc123",
        "https://open.spotify.com/user/31abc123?si=test": "31abc123",
        "https://open.spotify.com/user/legacy%2Euser": "legacy.user",
        "  legacy.user-name_1  ": "legacy.user-name_1",
    }
    for target, expected in cases.items():
        assert monitor.normalize_spotify_user_id(target) == expected


# Verifies invalid entities, hosts and malformed target values are rejected
def test_target_normalization_rejects_unsafe_forms():
    rejected = [
        "",
        "spotify:track:31abc123",
        "spotify:artist:31abc123",
        "spotify:album:31abc123",
        "spotify:playlist:31abc123",
        "spotify:user:",
        "spotify:user:abc:extra",
        "spotify:user:abc?si=test",
        "https://example.com/user/31abc123",
        "https://open.spotify.com/track/31abc123",
        "https://open.spotify.com/user/",
        "https://open.spotify.com/user/31abc123/extra",
        "https://open.spotify.com/user/legacy%2Fuser",
        "embedded space",
        "line\nbreak",
        "control\x00character",
        "control\x81character",
        "legacy\\user",
        "https://open.spotify.com/user/%ZZ",
    ]
    for target in rejected:
        with pytest.raises(ValueError, match="raw user ID"):
            monitor.normalize_spotify_user_id(target)


# Verifies a positional target overrides the configured target
def test_target_resolution_prefers_cli_value():
    result = monitor.resolve_target_user_id("spotify:user:cli.user", "https://open.spotify.com/user/config.user")
    assert result == "cli.user"


# Verifies the configured target is normalized when no positional target exists
def test_target_resolution_uses_configured_value():
    result = monitor.resolve_target_user_id(None, "https://open.spotify.com/user/config%2Euser?si=test")
    assert result == "config.user"


# Verifies a config-only CLI run monitors the normalized target and uses it as the file suffix
def test_config_only_monitoring_uses_normalized_target_and_suffix():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "spotify_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "https://open.spotify.com/user/config%2Euser?si=test"\nSP_DC_COOKIE = "test-cookie"\nDOTENV_FILE = "none"\nDISABLE_LOGGING = True\n', encoding="utf-8")
        setup = "runtime['check_internet'] = lambda: True; runtime['spotify_monitor_friend_uri'] = lambda user_id, tracks, csv_file: print(f'MONITOR_TARGET={user_id}\\nFILE_SUFFIX={runtime[\"FILE_SUFFIX\"]}');"
        result = run_cli(["--config-file", str(config_path)], setup)
    assert result.returncode == 0, result.stderr
    assert "MONITOR_TARGET=config.user" in result.stdout
    assert "FILE_SUFFIX=config.user" in result.stdout


# Verifies no-argument startup honors a target persisted in the discovered default config
def test_no_argument_monitoring_uses_persisted_default_target():
    with make_temp_directory() as directory_name:
        directory = Path(directory_name)
        config_path = directory / "spotify_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "persisted.user"\nSP_DC_COOKIE = "test-cookie"\nDOTENV_FILE = "none"\nDISABLE_LOGGING = True\n', encoding="utf-8")
        setup = "runtime['check_internet'] = lambda: True; runtime['spotify_monitor_friend_uri'] = lambda user_id, tracks, csv_file: print(f'MONITOR_TARGET={user_id}');"
        result = run_cli([], setup, cwd=directory)
    assert result.returncode == 0, result.stderr
    assert "MONITOR_TARGET=persisted.user" in result.stdout
    assert "Run the guided setup wizard now?" not in result.stdout


# Verifies invalid configured targets fail only when monitoring needs a target
def test_invalid_configured_target_is_rejected_for_monitoring():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "spotify_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "https://open.spotify.com/track/not-a-user"\nSP_DC_COOKIE = "test-cookie"\nDOTENV_FILE = "none"\nDISABLE_LOGGING = True\n', encoding="utf-8")
        result = run_cli(["--config-file", str(config_path)])
    assert result.returncode == 1
    assert "Invalid Spotify target" in result.stdout
    assert "network request attempted" not in result.stderr


# Verifies listing friends does not validate or require a monitoring target
def test_list_friends_does_not_require_configured_target():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "spotify_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "https://open.spotify.com/track/not-a-user"\nSP_DC_COOKIE = "test-cookie"\nDOTENV_FILE = "none"\nDISABLE_LOGGING = True\n', encoding="utf-8")
        setup = "runtime['check_internet'] = lambda: True; runtime['spotify_get_access_token_from_sp_dc'] = lambda cookie: 'token'; runtime['spotify_get_friends_json'] = lambda token: {}; runtime['spotify_list_friends'] = lambda friends, token: print('LISTED');"
        result = run_cli(["--config-file", str(config_path), "--list-friends"], setup)
    assert result.returncode == 0, result.stderr
    assert "LISTED" in result.stdout
    assert "Invalid Spotify target" not in result.stdout


# Verifies inline comments are split without treating quoted hashes as comments
def test_split_inline_comment_preserves_hashes_in_strings():
    assert monitor._split_inline_comment_preserving_strings('"a#b"  # actual') == ('"a#b"', "# actual")
    assert monitor._split_inline_comment_preserving_strings("'a#b'") == ("'a#b'", "")


# Verifies supported Python config value types produce compilable literals
def test_format_config_value_supports_required_types():
    values = ["text", True, 42, 3.5, ["a"], ("a",), {"a": 1}, None]
    for value in values:
        literal = monitor._format_config_value(value, prefer_double_quotes=True)
        assert eval(literal) == value


# Verifies rendered config preserves structure and substitutes non-secret runtime values
def test_rendered_config_compiles_and_uses_current_non_secret_values(monkeypatch):
    monkeypatch.setattr(monitor, "TARGET_USER_URI_ID", 'path\\with"quote#hash')
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 123)
    rendered = monitor.generate_config_with_current_values()
    namespace = {}
    exec(compile(rendered, "<rendered-config>", "exec"), namespace)
    assert namespace["TARGET_USER_URI_ID"] == 'path\\with"quote#hash'
    assert namespace["SPOTIFY_CHECK_INTERVAL"] == 123
    assert namespace["NTFY_IMAGES"] is True
    assert "# Select the method used to obtain the Spotify access token" in rendered
    assert "Do not create a new Spotify app only for this tool" in rendered
    assert "Create a new app" not in rendered
    assert "\n\n#" in rendered


# Verifies live secret values cannot leak into rendered config output
def test_rendered_config_never_substitutes_secret_values(monkeypatch):
    secret_values = {}
    for key in monitor.SECRET_KEYS:
        value = f"LIVE-{key}-VALUE"
        secret_values[key] = value
        monkeypatch.setattr(monitor, key, value)
    rendered = monitor.generate_config_with_current_values()
    namespace = {}
    exec(rendered, namespace)
    for key, value in secret_values.items():
        assert value not in rendered
        assert namespace[key] != value


# Verifies generated config never renders a potentially private custom header dictionary
def test_rendered_config_never_substitutes_webhook_headers(monkeypatch):
    secret = "Bearer private-header-value"
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"Authorization": secret, "X-Monitor": "spotify"})
    rendered = monitor.generate_config_with_current_values()
    namespace = {}
    exec(rendered, namespace)
    assert secret not in rendered
    assert namespace["WEBHOOK_HEADERS"] == {}


# Verifies multiline template structures remain unchanged when rendering current values
def test_rendered_config_preserves_multiline_structures(monkeypatch):
    template = "MULTI_VALUE = [\n    'template',\n]\n"
    monkeypatch.setattr(monitor, "CONFIG_BLOCK", template)
    monkeypatch.setattr(monitor, "MULTI_VALUE", ["runtime"], raising=False)
    rendered = monitor.generate_config_with_current_values()
    assert rendered == template
    compile(rendered, "<multiline-config>", "exec")


# Verifies a new config file is written without creating a backup
def test_safe_config_writer_creates_new_file():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / "spotify_monitor.conf"
        status = monitor.write_config_file(destination, 'TARGET_USER_URI_ID = "new-user"\n')
        assert destination.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "new-user"\n'
        assert status == {"path": str(destination), "backup_path": None}


# Verifies replacing a config creates a timestamped backup with the previous content
def test_safe_config_writer_backs_up_existing_file():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / "spotify_monitor.conf"
        destination.write_text('TARGET_USER_URI_ID = "old-user"\n', encoding="utf-8")
        status = monitor.write_config_file(destination, 'TARGET_USER_URI_ID = "new-user"\n')
        backup_path = Path(status["backup_path"])
        assert backup_path.match("spotify_monitor.conf.*.bak")
        assert backup_path.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "old-user"\n'
        assert destination.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "new-user"\n'


# Verifies invalid config content leaves an existing destination untouched
def test_safe_config_writer_rejects_invalid_content_before_touching_destination():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / "spotify_monitor.conf"
        destination.write_text('TARGET_USER_URI_ID = "old-user"\n', encoding="utf-8")
        with pytest.raises(SyntaxError):
            monitor.write_config_file(destination, 'TARGET_USER_URI_ID = "unterminated\n')
        assert destination.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "old-user"\n'
        assert list(destination.parent.glob("*.bak")) == []


# Verifies a failed atomic replacement preserves the destination and its backup
def test_safe_config_writer_preserves_original_when_replace_fails():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / "spotify_monitor.conf"
        destination.write_text('TARGET_USER_URI_ID = "old-user"\n', encoding="utf-8")
        with patch.object(monitor.os, "replace", side_effect=OSError("replace failed")), pytest.raises(OSError, match="replace failed"):
            monitor.write_config_file(destination, 'TARGET_USER_URI_ID = "new-user"\n')
        backups = list(destination.parent.glob("*.bak"))
        assert destination.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "old-user"\n'
        assert len(backups) == 1
        assert backups[0].read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "old-user"\n'


# Verifies dotenv updates preserve unrelated lines and safely round-trip special values
def test_dotenv_update_preserves_content_and_escapes_special_values(capsys):
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text("# keep this\nUNRELATED=stay\nSP_DC_COOKIE=old\n\nSP_DC_COOKIE=duplicate\n", encoding="utf-8")
        cookie_value = " space # single' double\" slash\\line\nnext ${HOME}"
        password_value = "smtp password"
        status = monitor.update_dotenv_file(destination, {"SP_DC_COOKIE": cookie_value, "SMTP_PASSWORD": password_value})
        content = destination.read_text(encoding="utf-8")
        parsed = dotenv_values(destination, interpolate=False)
        assert content.startswith("# keep this\nUNRELATED=stay\n")
        assert content.count("SP_DC_COOKIE=") == 1
        assert parsed["SP_DC_COOKIE"] == cookie_value
        assert parsed["SMTP_PASSWORD"] == password_value
        assert status == {"path": str(destination), "updated_keys": ("SP_DC_COOKIE", "SMTP_PASSWORD")}
        assert cookie_value not in repr(status)
        assert password_value not in repr(status)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# Verifies dotenv updates reject keys outside the secret allowlist
def test_dotenv_update_rejects_unknown_keys():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        with pytest.raises(ValueError, match="Unsupported dotenv key"):
            monitor.update_dotenv_file(destination, {"UNEXPECTED_KEY": "secret"})
        assert not destination.exists()


# Verifies dotenv files are restricted to mode 0600 on POSIX systems
def test_dotenv_update_sets_posix_mode():
    if os.name != "posix":
        pytest.skip("POSIX file modes are unavailable")
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        monitor.update_dotenv_file(destination, {"REFRESH_TOKEN": "secret"})
        assert destination.stat().st_mode & 0o777 == 0o600


# Verifies config syntax errors include precise source details and recovery guidance
def test_config_syntax_error_is_actionable(capsys):
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "broken.conf"
        config_path.write_text('TOKEN_SOURCE = "cookie"\nTARGET_USER_URI_ID = "broken\n', encoding="utf-8")
        assert monitor.load_config_file(config_path, {}) is False
    output = capsys.readouterr().out
    assert str(config_path) in output
    assert "* Line: 2" in output
    assert 'TARGET_USER_URI_ID = "broken' in output
    assert "* Parser:" in output
    assert "To fix:" in output
    assert "matching quotes" in output
    assert "forward slashes or doubled backslashes" in output


# Verifies invalid UTF-8 config content gets a useful error without a traceback
def test_config_invalid_utf8_is_actionable(capsys):
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "invalid-utf8.conf"
        config_path.write_bytes(b"TARGET_USER_URI_ID = \xff\n")
        assert monitor.load_config_file(config_path, {}) is False
    output = capsys.readouterr().out
    assert str(config_path) in output
    assert "valid UTF-8" in output
    assert "To fix:" in output
    assert "Traceback" not in output


# Verifies a missing explicit config path includes a direct recovery hint
def test_missing_explicit_config_is_actionable():
    with make_temp_directory() as directory_name:
        missing_path = Path(directory_name) / "missing.conf"
        result = run_cli(["--config-file", str(missing_path)])
    assert result.returncode == 1
    assert str(missing_path) in result.stdout
    assert "To fix:" in result.stdout
    assert "Traceback" not in result.stdout


# Verifies test email mode remains usable without any monitoring target
def test_send_test_email_does_not_require_target():
    setup = "runtime['check_internet'] = lambda: True; runtime['send_email'] = lambda *args, **kwargs: 0;"
    result = run_cli(["--send-test-email", "--env-file", "none"], setup)
    assert result.returncode == 0, result.stderr
    assert "Email sent successfully" in result.stdout
    assert "target is required" not in result.stdout


# Verifies container playback emits one warning before monitoring begins
def test_container_playback_warning_appears_once_before_monitoring():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "spotify_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "target.user"\nSP_DC_COOKIE = "test-cookie"\nDOTENV_FILE = "none"\nDISABLE_LOGGING = True\nTRACK_SONGS = True\n', encoding="utf-8")
        setup = "runtime['is_container_environment'] = lambda: True; runtime['check_internet'] = lambda: True; runtime['spotify_monitor_friend_uri'] = lambda *args: print('MONITOR_STARTED');"
        result = run_cli(["--config-file", str(config_path)], setup)
    assert result.returncode == 0, result.stderr
    assert result.stdout.count(monitor.CONTAINER_PLAYBACK_WARNING) == 1
    assert result.stdout.index(monitor.CONTAINER_PLAYBACK_WARNING) < result.stdout.index("MONITOR_STARTED")


# Verifies local playback does not emit the container warning
def test_local_playback_has_no_container_warning():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "spotify_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "target.user"\nSP_DC_COOKIE = "test-cookie"\nDOTENV_FILE = "none"\nDISABLE_LOGGING = True\nTRACK_SONGS = True\n', encoding="utf-8")
        setup = "runtime['is_container_environment'] = lambda: False; runtime['check_internet'] = lambda: True; runtime['spotify_monitor_friend_uri'] = lambda *args: print('MONITOR_STARTED');"
        result = run_cli(["--config-file", str(config_path)], setup)
    assert result.returncode == 0, result.stderr
    assert monitor.CONTAINER_PLAYBACK_WARNING not in result.stdout


# Verifies the missing-target hint does not advertise an unavailable setup command
def test_missing_target_hint_lists_current_options_only():
    setup = "runtime['find_config_file'] = lambda *args, **kwargs: None; runtime['check_internet'] = lambda: True;"
    result = run_cli(["--env-file", "none", "--spotify-dc-cookie", "test-cookie"], setup)
    assert result.returncode == 1
    assert "positional user ID" in result.stdout
    assert "TARGET_USER_URI_ID" in result.stdout
    assert "--setup" not in result.stdout


# Verifies successful config execution still updates the provided namespace
def test_successful_config_load_updates_namespace():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "valid.conf"
        config_path.write_text('TARGET_USER_URI_ID = "configured-user"\nSPOTIFY_CHECK_INTERVAL = 45\n', encoding="utf-8")
        namespace = {}
        assert monitor.load_config_file(config_path, namespace) is True
    assert namespace["TARGET_USER_URI_ID"] == "configured-user"
    assert namespace["SPOTIFY_CHECK_INTERVAL"] == 45
