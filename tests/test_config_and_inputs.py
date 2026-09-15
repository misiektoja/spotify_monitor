import stat
import re
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
    environment["PYTHONIOENCODING"] = "utf-8"
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
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
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
        if os.name == "posix":
            assert backup_path.stat().st_mode & 0o777 == 0o600


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


# Verifies a secret cleared by its owner leaves the file rather than staying behind as an empty value
def test_a_cleared_secret_is_removed_rather_than_emptied():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text('UNRELATED=stay\nNTFY_ACCESS_TOKEN="tk_old"\n', encoding="utf-8")

        monitor.update_dotenv_file(destination, {"NTFY_ACCESS_TOKEN": ""})

        content = destination.read_text(encoding="utf-8")
        assert "NTFY_ACCESS_TOKEN" not in content
        assert dotenv_values(destination, interpolate=False) == {"UNRELATED": "stay"}


# Verifies clearing a secret the file never held does not add an empty line for it
def test_clearing_an_absent_secret_writes_nothing():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text("UNRELATED=stay\n", encoding="utf-8")

        monitor.update_dotenv_file(destination, {"NTFY_ACCESS_TOKEN": ""})

        assert destination.read_text(encoding="utf-8") == "UNRELATED=stay\n"


# Verifies a generated config asks before it replaces a file, and keeps a backup once it does
def test_a_generated_config_asks_before_replacing_an_existing_file():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / "spotify_monitor.conf"
        destination.write_text('TARGET_USER_URI_ID = "old-user"\n', encoding="utf-8")

        backup_path, written = monitor.write_generated_config(destination, 'TARGET_USER_URI_ID = "new-user"\n', interactive=True, input_func=lambda prompt: "y")

        assert written is True
        assert destination.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "new-user"\n'
        assert Path(backup_path).read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "old-user"\n'


# Verifies a declined replacement leaves the existing file exactly as it was
def test_a_declined_replacement_keeps_the_existing_config():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / "spotify_monitor.conf"
        destination.write_text('TARGET_USER_URI_ID = "old-user"\n', encoding="utf-8")

        backup_path, written = monitor.write_generated_config(destination, 'TARGET_USER_URI_ID = "new-user"\n', interactive=True, input_func=lambda prompt: "n")

        assert (backup_path, written) == (None, False)
        assert destination.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "old-user"\n'
        assert list(destination.parent.glob("*.bak")) == []


# Verifies --force replaces without asking, so a scripted run is not left waiting on a prompt
def test_force_replaces_an_existing_config_without_asking():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / "spotify_monitor.conf"
        destination.write_text('TARGET_USER_URI_ID = "old-user"\n', encoding="utf-8")

        def refuse(prompt=""):
            raise AssertionError("asked despite --force")

        backup_path, written = monitor.write_generated_config(destination, 'TARGET_USER_URI_ID = "new-user"\n', force=True, interactive=True, input_func=refuse)

        assert written is True
        assert destination.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "new-user"\n'
        assert Path(backup_path).exists()


# Verifies a new destination is written without a prompt, because there is nothing to replace
def test_a_new_destination_is_written_without_a_prompt():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / "spotify_monitor.conf"

        def refuse(prompt=""):
            raise AssertionError("asked about a file that does not exist")

        backup_path, written = monitor.write_generated_config(destination, 'TARGET_USER_URI_ID = "new-user"\n', interactive=True, input_func=refuse)

        assert (backup_path, written) == (None, True)
        assert destination.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "new-user"\n'


# Verifies a run with no terminal refuses instead of silently replacing a file nobody can confirm
def test_a_replacement_without_a_terminal_is_refused():
    with make_temp_directory() as directory_name:
        destination = Path(directory_name) / "spotify_monitor.conf"
        destination.write_text('TARGET_USER_URI_ID = "old-user"\n', encoding="utf-8")

        with pytest.raises(FileExistsError, match="already exists"):
            monitor.write_generated_config(destination, 'TARGET_USER_URI_ID = "new-user"\n', interactive=False)

        assert destination.read_text(encoding="utf-8") == 'TARGET_USER_URI_ID = "old-user"\n'


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
    assert "Line: 2" in output
    assert 'TARGET_USER_URI_ID = "broken' in output
    assert "Parser:" in output
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
    setup = "runtime['check_internet'] = lambda: True; runtime['validate_smtp_configuration'] = lambda: None; runtime['send_email'] = lambda *args, **kwargs: 0;"
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


# Verifies config loading rejects executable expressions without invoking them
def test_config_loader_rejects_executable_content(monkeypatch, capsys):
    system_call = patch.object(monitor.os, "system")
    with make_temp_directory() as directory_name, system_call as system_mock:
        config_path = Path(directory_name) / "malicious.conf"
        config_path.write_text('TARGET_USER_URI_ID = __import__("os").system("unexpected")\n', encoding="utf-8")
        assert monitor.load_config_file(config_path, {}) is False
    system_mock.assert_not_called()
    output = capsys.readouterr().out
    assert "only documented NAME = literal assignments" in output


# Verifies config loading rejects undocumented names and control-flow statements
@pytest.mark.parametrize("content", ['UNSUPPORTED_SETTING = 1\n', 'if True:\n    TARGET_USER_URI_ID = "user"\n'])
def test_config_loader_rejects_unsupported_statements(content, capsys):
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "unsupported.conf"
        config_path.write_text(content, encoding="utf-8")
        assert monitor.load_config_file(config_path, {}) is False
    assert "unsupported content" in capsys.readouterr().out


# Verifies a configuration written by an older version still loads when it carries retired settings
def test_config_loader_ignores_retired_settings(capsys):
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "legacy.conf"
        config_path.write_text('TOTP_VER = 0\nSECRET_CIPHER_DICT = {"12": [1, 2]}\nSECRET_CIPHER_DICT_URL = "https://example.invalid/secrets.json"\nSPOTIFY_CHECK_INTERVAL = 45\n', encoding="utf-8")
        namespace = {}
        assert monitor.load_config_file(config_path, namespace) is True
    assert namespace["SPOTIFY_CHECK_INTERVAL"] == 45
    for retired_setting in monitor.RETIRED_CONFIG_SETTINGS:
        assert retired_setting not in namespace
    output = capsys.readouterr().out
    assert "TOTP_VER" in output
    assert "are ignored" in output


# Verifies retired settings are reported to the caller so Doctor can surface them without printing
def test_config_loader_reports_retired_settings_to_caller():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "legacy.conf"
        config_path.write_text("TOTP_VER = 0\nSPOTIFY_CHECK_INTERVAL = 45\n", encoding="utf-8")
        retired = []
        assert monitor.load_config_file(config_path, {}, report_errors=False, retired_out=retired) is True
    assert retired == ["TOTP_VER"]


# Verifies ignoring retired names does not weaken rejection of any other unknown setting
def test_retired_allowance_does_not_accept_other_unknown_names():
    assert monitor.RETIRED_CONFIG_SETTINGS.isdisjoint(monitor._config_allowed_names())
    with pytest.raises(ValueError, match="unsupported configuration setting"):
        monitor.parse_config_content("TOTP_VERSION_TYPO = 1\n")


# Verifies invalid Friend Activity timing flags fail during argument validation
@pytest.mark.parametrize("option", ["--check-interval", "--offline-timer", "--disappeared-timer"])
def test_nonpositive_friend_activity_timing_flags_are_rejected(option):
    result = run_cli([option, "0", "--doctor", "--env-file", "none"])
    assert result.returncode == 2
    assert f"{option} must be greater than zero" in result.stderr


# Verifies invalid configured timing values stop startup before network access
def test_invalid_configured_timing_stops_before_network_access():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "invalid-timing.conf"
        config_path.write_text('TARGET_USER_URI_ID = "configured-user"\nSPOTIFY_CHECK_INTERVAL = 0\nDOTENV_FILE = "none"\n', encoding="utf-8")
        result = run_cli(["--config-file", str(config_path)])
    assert result.returncode == 1
    assert "SPOTIFY_CHECK_INTERVAL must be a number greater than zero" in result.stdout
    assert "network request attempted" not in result.stderr


# Verifies activity flag failures are visible and disable the integration
def test_flag_file_failure_is_visible_and_disables_integration(monkeypatch, capsys):
    with make_temp_directory() as directory_name:
        monkeypatch.setattr(monitor, "FLAG_FILE", directory_name)
        assert monitor.flag_file_delete() is False
    assert monitor.FLAG_FILE == ""
    assert "Activity flag integration was disabled" in capsys.readouterr().out


@pytest.mark.parametrize("uri,expected", [
    ("spotify:user:MiXeD", "https://open.spotify.com/user/MiXeD?si=1"),
    ("spotify:playlist:37i9dQZF1DX", "https://open.spotify.com/playlist/37i9dQZF1DX?si=1"),
    ("  spotify:track:abc  ", "https://open.spotify.com/track/abc?si=1"),
    ("SPOTIFY:TRACK:abc", "https://open.spotify.com/track/abc?si=1"),
])
# Verifies a valid URI converts with its identifier case preserved, since Spotify IDs are case sensitive
def test_convert_uri_to_url_accepts_valid_references(uri, expected):
    assert monitor.spotify_convert_uri_to_url(uri) == expected


@pytest.mark.parametrize("uri", [
    "spotify:playlist:idspotify:user:evil",
    "spotify:episode:abc",
    "spotify:user:",
    "spotify:user:abc:extra",
    "::37i9dQZF1DX",
    "spotify:user",
    "https://open.spotify.com/user/abc",
    "",
    "   ",
    None,
    42,
])
# Verifies an unsupported or malformed reference yields an empty string instead of a wrong or partial link
def test_convert_uri_to_url_rejects_unparseable_references(uri):
    assert monitor.spotify_convert_uri_to_url(uri) == ""


# Verifies the object type is matched as a whole part, so an ID containing another type cannot redirect the link
def test_convert_uri_to_url_matches_whole_parts():
    assert monitor.spotify_convert_uri_to_url("spotify:album:trackfulID") == "https://open.spotify.com/album/trackfulID?si=1"
    assert monitor.spotify_convert_uri_to_url("spotify:playlist:userlike") == "https://open.spotify.com/playlist/userlike?si=1"


# Verifies ntfy artwork ships disabled and the generated config explains the optional install
def test_ntfy_images_ships_disabled_and_documents_optional_dependency():
    assert "NTFY_IMAGES = False" in monitor.CONFIG_BLOCK
    assert 'pip install "spotify_monitor[notification-images]"' in monitor.CONFIG_BLOCK


# Confirms a generated config that cannot be written reports the destination problem with a fix
def test_a_generated_config_that_cannot_be_written_is_reported_with_a_fix():
    with make_temp_directory() as directory_name:
        read_only = Path(directory_name) / "read-only"
        read_only.mkdir()
        read_only.chmod(0o500)
        target = read_only / "spotify_monitor.conf"
        try:
            result = run_cli(["--generate-config", str(target)])
        finally:
            read_only.chmod(0o700)

    assert result.returncode == 1, result.stdout
    assert "* Error: An output destination is not writable" in result.stdout
    assert "To fix: Choose a writable path and verify its parent directory permissions then retry" in result.stdout


# Verifies an assignment the owner exported keeps its export, since dropping it changes what a shell sourcing the file exports
def test_an_exported_assignment_keeps_its_export(tmp_path):
    destination = tmp_path / ".env"
    destination.write_text('export SMTP_PASSWORD="old"\nOTHER=keep\n', encoding="utf-8")

    monitor.update_dotenv_file(destination, {"SMTP_PASSWORD": "new"})

    assert destination.read_text(encoding="utf-8") == 'export SMTP_PASSWORD="new"\nOTHER=keep\n'


# Verifies a line break inside a value is escaped rather than written through, since a raw one would split the assignment
def test_a_line_break_in_a_value_cannot_split_the_assignment(tmp_path):
    destination = tmp_path / ".env"

    monitor.update_dotenv_file(destination, {"SMTP_PASSWORD": "one\ntwo"})

    assert destination.read_text(encoding="utf-8") == 'SMTP_PASSWORD="one\\ntwo"\n'


# Verifies the writer refuses a key this tool does not ship, so a typo cannot put an unknown name in the private file
def test_the_writer_refuses_a_key_this_tool_does_not_ship(tmp_path):
    with pytest.raises(ValueError):
        monitor.update_dotenv_file(tmp_path / ".env", {"NOT_A_SECRET": "value"})


# Verifies the writer refuses a value that is not text, so a mistyped caller fails before the file is touched
def test_the_writer_refuses_a_value_that_is_not_text(tmp_path):
    with pytest.raises(TypeError):
        monitor.update_dotenv_file(tmp_path / ".env", {"SMTP_PASSWORD": 1234})


# Verifies the backup name every tool in this family writes, so one documented shape covers them all
def test_the_backup_carries_the_family_name_and_mode(tmp_path):
    destination = tmp_path / "monitor.conf"
    destination.write_text("SETTING = 1\n", encoding="utf-8")

    backup_path = monitor.create_timestamped_backup(destination)

    assert re.fullmatch(r"monitor\.conf\.\d{14}\.bak", Path(backup_path).name)
    assert Path(backup_path).read_text(encoding="utf-8") == "SETTING = 1\n"
    assert stat.S_IMODE(Path(backup_path).stat().st_mode) == 0o600


# Verifies a second backup in the same second takes its own name rather than overwriting the first
def test_a_second_backup_in_the_same_second_keeps_the_first(tmp_path):
    destination = tmp_path / "monitor.conf"
    destination.write_text("first\n", encoding="utf-8")
    first = monitor.create_timestamped_backup(destination)
    destination.write_text("second\n", encoding="utf-8")

    second = monitor.create_timestamped_backup(destination)

    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "first\n"
    assert Path(second).read_text(encoding="utf-8") == "second\n"


# Verifies a destination that is not there yet earns no backup, since there is nothing to copy
def test_a_missing_destination_earns_no_backup(tmp_path):
    assert monitor.create_timestamped_backup(tmp_path / "absent.conf") is None
