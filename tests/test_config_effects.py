import inspect
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "spotify_monitor.py"
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "config_effect_test_artifacts"
ISOLATED_PRELUDE = "import requests, runpy, socket, sys; requests.sessions.Session.request = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network request attempted')); socket.create_connection = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network connection attempted')); "

# Records what the startup connectivity check actually resolved, then reports the interval-derived
# value the monitor loop will use. Both are read after the config file and dotenv have been applied
PROBE_SETUP = (
    "runtime['req'].get = lambda url, **kwargs: print(f'CONNECTIVITY_URL={url}') or print(f'CONNECTIVITY_TIMEOUT={kwargs[\"timeout\"]}') or print(f'CONNECTIVITY_VERIFY={kwargs[\"verify\"]}') or type('Response', (), {'status_code': 200})(); "
    "runtime['urllib3'].disable_warnings = lambda *args, **kwargs: print('INSECURE_WARNINGS_DISABLED'); "
    "runtime['spotify_monitor_friend_uri'] = lambda user_id, tracks, csv_file: print(f'CHECK_INTERVAL={runtime[\"activity_check_interval\"]()}') or print(f'LIVENESS_SECONDS={runtime[\"LIVENESS_REMINDER_SECONDS\"]}'); "
)
DIAGNOSTIC_CONFIG_PROBE_SETUP = "original_load_config = runtime['load_config_file']; runtime['load_config_file'] = lambda *args, **kwargs: print(f'DEBUG_DURING_CONFIG={runtime[\"DEBUG_MODE\"]}') or print(f'VERBOSE_DURING_CONFIG={runtime[\"VERBOSE_MODE\"]}') or original_load_config(*args, **kwargs); " + PROBE_SETUP
WEBHOOK_PROBE_SETUP = PROBE_SETUP + "runtime['spotify_monitor_friend_uri'] = lambda user_id, tracks, csv_file: print(f'WEBHOOK_ENABLED={runtime[\"WEBHOOK_ENABLED\"]}'); "


# Creates a disposable test directory under the project local directory
def make_temp_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT)


# Runs an isolated CLI scenario with real network access blocked
def run_cli(arguments, runtime_setup="", cwd=PROJECT_ROOT):
    source = f"module = runpy.run_path({str(CLI_PATH)!r}, run_name='spotify_monitor_config_test'); runtime = module['main'].__globals__; runtime['sys'].argv = {[str(CLI_PATH), *arguments]!r}; runtime['CLEAR_SCREEN'] = False; runtime['signal'].signal = lambda *args, **kwargs: None; {runtime_setup} module['main']()"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run([sys.executable, "-c", ISOLATED_PRELUDE + source], cwd=cwd, capture_output=True, text=True, env=environment, timeout=60, check=False)


# Writes one config file carrying the supplied settings plus the minimum needed to reach monitoring
def write_config(directory_name, settings):
    config_path = Path(directory_name) / "spotify_monitor.conf"
    baseline = 'TARGET_USER_URI_ID = "config.user"\nSP_DC_COOKIE = "test-cookie"\nDOTENV_FILE = "none"\nDISABLE_LOGGING = True\n'
    config_path.write_text(baseline + settings, encoding="utf-8")
    return config_path


# Reads a setting's shipped default from the module source, unaffected by values other tests leave behind
def source_default(name):
    match = re.search(rf"^{name} = (\d+)", inspect.getsource(monitor), re.MULTILINE)
    assert match, f"{name} has no numeric default"
    return match.group(1)


# Reads one KEY=value line out of a captured CLI run
def probe_value(output, key):
    for line in output.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    raise AssertionError(f"{key} was never reported\n{output}")


# Confirms a config-file liveness interval reaches the loop rather than leaving the built-in default
def test_config_file_liveness_interval_reaches_the_loop():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_LIVE_CHECK_INTERVAL = 300\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CHECK_INTERVAL") == "300"
    assert float(probe_value(result.stdout, "LIVENESS_SECONDS")) == 43200.0


# Confirms a check interval longer than the liveness interval leaves the configured reminder alone
def test_a_long_check_interval_keeps_the_configured_liveness_interval():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_LIVE_CHECK_INTERVAL = 86400\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert float(probe_value(result.stdout, "LIVENESS_SECONDS")) == 43200.0


# Confirms a command-line interval still wins over the config file for the selected backend and leaves the liveness reminder alone
@pytest.mark.parametrize("backend_config", ["", 'FRIEND_ACTIVITY_BACKEND = "buddylist"\nSPOTIFY_CHECK_INTERVAL = 300\n'])
def test_command_line_interval_overrides_the_config_file(backend_config):
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, backend_config + "SPOTIFY_LIVE_CHECK_INTERVAL = 300\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path), "--check-interval", "600"], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CHECK_INTERVAL") == "600"
    assert float(probe_value(result.stdout, "LIVENESS_SECONDS")) == 43200.0


# Confirms the timing flags only touch the timers of the selected backend
@pytest.mark.parametrize("backend,changed,untouched", [("listening_activity", ("SPOTIFY_LIVE_CHECK_INTERVAL", "SPOTIFY_LIVE_INACTIVITY_CHECK", "SPOTIFY_LIVE_DISAPPEARED_CHECK_INTERVAL"), ("SPOTIFY_CHECK_INTERVAL", "SPOTIFY_INACTIVITY_CHECK", "SPOTIFY_DISAPPEARED_CHECK_INTERVAL")), ("buddylist", ("SPOTIFY_CHECK_INTERVAL", "SPOTIFY_INACTIVITY_CHECK", "SPOTIFY_DISAPPEARED_CHECK_INTERVAL"), ("SPOTIFY_LIVE_CHECK_INTERVAL", "SPOTIFY_LIVE_INACTIVITY_CHECK", "SPOTIFY_LIVE_DISAPPEARED_CHECK_INTERVAL"))])
def test_timing_flags_follow_the_selected_backend(backend, changed, untouched):
    names = changed + untouched + ("SPOTIFY_LIVE_ACTIVE_CHECK_INTERVAL",)
    probe = PROBE_SETUP + "runtime['spotify_monitor_friend_uri'] = lambda user_id, tracks, csv_file: [print(f'{name}={runtime[name]}') for name in " + repr(names) + "]; "
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, f'FRIEND_ACTIVITY_BACKEND = "{backend}"\n')
        result = run_cli(["--config-file", str(config_path), "--check-interval", "77", "--offline-timer", "555", "--active-check-interval", "7", "--disappeared-timer", "44"], probe)

    assert result.returncode == 0, result.stderr
    assert [probe_value(result.stdout, name) for name in changed] == ["77", "555", "44"]
    assert [probe_value(result.stdout, name) for name in untouched] == [source_default(name) for name in untouched]
    assert probe_value(result.stdout, "SPOTIFY_LIVE_ACTIVE_CHECK_INTERVAL") == "7"


# Confirms the startup connectivity check honors a config-file URL and timeout rather than the built-in defaults
def test_config_file_connectivity_settings_reach_the_startup_check():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, 'CHECK_INTERNET_URL = "https://probe.example/ping"\nCHECK_INTERNET_TIMEOUT = 17\n')
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CONNECTIVITY_URL") == "https://probe.example/ping"
    assert probe_value(result.stdout, "CONNECTIVITY_TIMEOUT") == "17"


# Confirms VERIFY_SSL from a config file reaches the startup check and silences insecure-request warnings
def test_config_file_verify_ssl_reaches_the_startup_check():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "VERIFY_SSL = False\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CONNECTIVITY_VERIFY") == "False", "a TLS-inspecting proxy setup must not be blocked by the startup check"
    assert "INSECURE_WARNINGS_DISABLED" in result.stdout, "VERIFY_SSL = False must suppress the warnings it exists to avoid"


# Confirms the default configuration still verifies TLS and leaves the warnings in place
def test_default_configuration_keeps_tls_verification():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CONNECTIVITY_VERIFY") == "True"
    assert "INSECURE_WARNINGS_DISABLED" not in result.stdout


@pytest.mark.parametrize(("flag", "setting"), (("--verbose", "VERBOSE_MODE"), ("--debug", "DEBUG_MODE")))
# Confirms explicit diagnostic flags are already active while the config is loading
def test_diagnostic_flag_applies_during_config_load(flag, setting):
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, f"{setting} = False\n")
        result = run_cli(["--config-file", str(config_path), flag], DIAGNOSTIC_CONFIG_PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, f"{setting.removesuffix('_MODE')}_DURING_CONFIG") == "True"


@pytest.mark.parametrize("url,timeout,verify", [("https://explicit.example", 3, False), ("https://other.example", 9, True)])
# Confirms an explicit argument still wins over the resolved global, so callers keep full control
def test_explicit_connectivity_arguments_win(monkeypatch, url, timeout, verify):
    recorded = {}
    monkeypatch.setattr(monitor, "CHECK_INTERNET_URL", "https://global.example")
    monkeypatch.setattr(monitor, "CHECK_INTERNET_TIMEOUT", 99)
    monkeypatch.setattr(monitor, "VERIFY_SSL", not verify)
    monkeypatch.setattr(monitor.req, "get", lambda target, **kwargs: recorded.update(url=target, **kwargs))

    assert monitor.check_internet(url, timeout, verify) is True
    assert (recorded["url"], recorded["timeout"], recorded["verify"]) == (url, timeout, verify)


# Confirms no connectivity setting is frozen into the function signature where a config file cannot reach it
def test_connectivity_defaults_are_not_bound_at_import():
    parameters = inspect.signature(monitor.check_internet).parameters

    assert [parameters[name].default for name in ("url", "timeout", "verify")] == [None, None, None], "resolving these at import time would freeze them before any config file loads"


# Confirms an unedited webhook destination remains selected and unavailable
@pytest.mark.parametrize(("webhook_url", "expected"), (("your_webhook_url", "True"), ("https://ntfy.sh/some-topic", "True")))
def test_a_placeholder_webhook_url_switches_the_channel_off(webhook_url, expected):
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, f'WEBHOOK_ENABLED = True\nWEBHOOK_PROVIDER = "ntfy"\nWEBHOOK_URL = "{webhook_url}"\n')
        result = run_cli(["--config-file", str(config_path)], WEBHOOK_PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "WEBHOOK_ENABLED") == expected


# The diagnostic line is documented as comma-separated key=value fields, so the length travels as its own field
@pytest.mark.parametrize("key, value, fields", [
    ("SP_APP_CLIENT_ID", "0123456789abcdef0123456789abcdef", {"value": "set", "chars": 32}),
    ("SMTP_PASSWORD", "a-password-the-user-picked", {"value": "set", "chars": None}),
    ("LASTFM_API_KEY", "your_lastfm_api_key", {"value": "not set", "chars": None}),
    ("SP_DC_COOKIE", "", {"value": "not set", "chars": None}),
])
def test_no_secret_field_value_carries_a_comma(key, value, fields):
    assert monitor.secret_fields(value, key) == fields
    assert all("," not in str(part) for part in fields.values())


# A source outside the set is a typo rather than a new layer, so it is refused instead of reaching the summary
def test_an_unsupported_secret_source_is_refused(monkeypatch):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {})

    with pytest.raises(ValueError, match="Unsupported secret source"):
        monitor.record_secret_source("SMTP_PASSWORD", "somewhere else", "a-password-the-user-picked")

    assert monitor.SECRET_SOURCES == {}


# A placeholder is not a value, so recording it clears the earlier answer rather than adding a row
def test_a_placeholder_clears_the_recorded_source(monkeypatch):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"SMTP_PASSWORD": "dotenv file"})

    monitor.record_secret_source("SMTP_PASSWORD", "command line", "your_smtp_password")

    assert monitor.SECRET_SOURCES == {}


# Confirms every layer that can supply a secret is traced under the source that actually supplied it
@pytest.mark.parametrize("arguments, setup, expected", [
    ([], "", "name=SMTP_PASSWORD, source=configuration file or command line, value=set"),
    ([], "runtime['os'].environ['NTFY_ACCESS_TOKEN'] = 'tk_exported_token'; ", "name=NTFY_ACCESS_TOKEN, source=environment, value=set"),
    (["--webhook-url", "https://ntfy.sh/traced-topic"], "", "name=WEBHOOK_URL, source=command line, value=set"),
    (["--oauth-app-creds", "0123456789abcdef0123456789abcdef:fedcba9876543210fedcba9876543210"], "", "name=SP_APP_CLIENT_ID, source=command line, value=set, chars=32"),
])
def test_every_secret_layer_is_traced(arguments, setup, expected):
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, 'SMTP_PASSWORD = "a-password-the-user-picked"\n')
        result = run_cli(["--config-file", str(config_path), "--debug", "--doctor"] + arguments, setup)

    assert f"Secret resolution: {expected}" in result.stdout
    assert "a-password-the-user-picked" not in result.stdout


# The command line is the last layer to supply a secret, so a run with none says so only after it has had its say
def test_a_run_with_no_secret_anywhere_says_so():
    with make_temp_directory() as directory_name:
        config_path = Path(directory_name) / "spotify_monitor.conf"
        config_path.write_text('TARGET_USER_URI_ID = "config.user"\nDOTENV_FILE = "none"\nDISABLE_LOGGING = True\n', encoding="utf-8")
        result = run_cli(["--config-file", str(config_path), "--env-file", "none", "--debug", "--doctor"])

    assert "Secret resolution:" not in result.stdout
    assert "No private settings were resolved from config, dotenv, environment or the command line" in result.stdout


# Confirms an unedited placeholder is never reported as a loaded secret, whichever layer recorded it
def test_placeholder_secrets_are_not_reported_as_loaded(monkeypatch):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"WEBHOOK_URL": "dotenv file", "SMTP_PASSWORD": "configuration file or command line"})
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "your_webhook_url")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "your_smtp_password")

    from_file, from_environment, from_settings, from_command_line = monitor.doctor_secret_sources(None)

    assert "WEBHOOK_URL" not in from_file + from_environment + from_settings + from_command_line
    assert "SMTP_PASSWORD" not in from_file + from_environment + from_settings + from_command_line


# Verifies the settings count is a debug trace rather than a verbose line, since it says nothing a user acts on
def test_the_config_settings_count_is_a_debug_only_trace(tmp_path, monkeypatch, capsys):
    config = tmp_path / "spotify_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\nDISABLE_LOGGING = True\n", encoding="utf-8")
    namespace = {}

    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monitor.load_config_file(config, namespace=namespace)
    assert "settings from the configuration file" not in capsys.readouterr().out

    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monitor.load_config_file(config, namespace=namespace)
    assert "Configuration applied" in capsys.readouterr().out


# Confirms only debug keeps the screen, since a cleared terminal loses the run being compared against
@pytest.mark.parametrize(("flag", "expected"), (("--debug", False), ("--verbose", True)))
def test_only_debug_mode_keeps_the_screen(monkeypatch, flag, expected):
    cleared = []
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: cleared.append(bool(enabled)))
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: True, raising=False)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "check_internet", lambda: True)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "test-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: {"friends": []})
    monkeypatch.setattr(monitor, "spotify_list_friends", lambda friends, token: None)
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor", "--list-friends", "--spotify-dc-cookie", "test-cookie", "--env-file", "none", flag])

    with pytest.raises(SystemExit):
        monitor.main()

    assert cleared == [expected]


# Verifies the one-shot commands keep whatever is already on the screen, so their output stays scrollable
@pytest.mark.parametrize(("argv", "expected"), ((["spotify_monitor", "--doctor"], True), (["spotify_monitor", "--set-sp-dc"], True), (["spotify_monitor", "--send-test-email"], True), (["spotify_monitor", "--help"], True), (["spotify_monitor", "test-user"], False)))
def test_one_shot_commands_keep_the_terminal_history(monkeypatch, argv, expected):
    monkeypatch.setattr(monitor.sys, "argv", argv)

    assert monitor.keep_terminal_history() is expected


# Verifies a redirected stdout is never cleared, so no escape sequence or TERM warning reaches the captured output
def test_a_redirected_stdout_is_never_cleared(monkeypatch):
    commands = []
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(monitor.os, "system", lambda command: commands.append(command))

    monitor.clear_screen(True)

    assert commands == []


@pytest.mark.parametrize("source, position", [("dotenv file", 0), ("environment", 1), ("configuration file or command line", 2), ("command line", 3)])
# Verifies each source that can supply a secret lands in its own bucket, so none of them is filed under another
def test_each_secret_source_lands_in_its_own_bucket(monkeypatch, source, position):
    for name in monitor.SECRET_KEYS:
        monkeypatch.setattr(monitor, name, "your_placeholder", raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"SMTP_PASSWORD": source}, raising=False)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "a-real-secret-value", raising=False)

    buckets = monitor.doctor_secret_sources(None)

    assert buckets[position] == ["SMTP_PASSWORD"]
    assert [names for index, names in enumerate(buckets) if index != position] == [[], [], []]


# Confirms an unusable separator mode names the three values it accepts instead of repeating the raised text alone
def test_an_unusable_separator_mode_names_the_accepted_values():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, 'ASCII_LOG_SEPARATORS = "Maybe"\n')
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 1, result.stdout
    assert "* Error: ASCII_LOG_SEPARATORS must be" in result.stdout
    assert 'To fix: Set ASCII_LOG_SEPARATORS to "Auto", "On" or "Off"' in result.stdout
    assert f"Guide: {monitor.TERMINAL_GUIDE_URL}" in result.stdout


# Confirms a terminal whose width cannot be detected asks for a fixed width rather than printing the OS error alone
def test_an_undetectable_terminal_width_asks_for_a_fixed_width():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "")
        raising_size = "runtime['resolve_truncate_chars'] = lambda *args, **kwargs: (_ for _ in ()).throw(OSError('no terminal')); "
        result = run_cli(["--config-file", str(config_path), "--truncate", "999"], PROBE_SETUP + raising_size)

    assert result.returncode == 1, result.stdout
    assert "* Error: Cannot determine the terminal screen width: no terminal" in result.stdout
    assert "To fix: Pass a fixed width with --truncate <chars>" in result.stdout
    assert f"Guide: {monitor.TERMINAL_GUIDE_URL}" in result.stdout
