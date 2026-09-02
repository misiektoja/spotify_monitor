import os
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
    "runtime['spotify_monitor_friend_uri'] = lambda user_id, tracks, csv_file: print(f'CHECK_INTERVAL={runtime[\"SPOTIFY_CHECK_INTERVAL\"]}') or print(f'LIVENESS_COUNTER={runtime[\"LIVENESS_CHECK_COUNTER\"]}'); "
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


# Reads one KEY=value line out of a captured CLI run
def probe_value(output, key):
    for line in output.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    raise AssertionError(f"{key} was never reported\n{output}")


# Confirms a config-file check interval rescales the liveness cadence rather than leaving the import-time ratio
def test_config_file_check_interval_rescales_the_liveness_cadence():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_CHECK_INTERVAL = 300\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path)], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CHECK_INTERVAL") == "300"
    assert float(probe_value(result.stdout, "LIVENESS_COUNTER")) == 144.0


# Confirms a command-line interval still wins over the config file and rescales the same value
def test_command_line_interval_overrides_the_config_file():
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, "SPOTIFY_CHECK_INTERVAL = 300\nLIVENESS_CHECK_INTERVAL = 43200\n")
        result = run_cli(["--config-file", str(config_path), "--check-interval", "600"], PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "CHECK_INTERVAL") == "600"
    assert float(probe_value(result.stdout, "LIVENESS_COUNTER")) == 72.0


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
    defaults = monitor.check_internet.__defaults__

    assert defaults == (None, None, None), "resolving these at import time would freeze them before any config file loads"


# Confirms an unedited webhook destination switches the channel off while a real one keeps it on
@pytest.mark.parametrize(("webhook_url", "expected"), (("your_webhook_url", "False"), ("https://ntfy.sh/some-topic", "True")))
def test_a_placeholder_webhook_url_switches_the_channel_off(webhook_url, expected):
    with make_temp_directory() as directory_name:
        config_path = write_config(directory_name, f'WEBHOOK_ENABLED = True\nWEBHOOK_PROVIDER = "ntfy"\nWEBHOOK_URL = "{webhook_url}"\n')
        result = run_cli(["--config-file", str(config_path)], WEBHOOK_PROBE_SETUP)

    assert result.returncode == 0, result.stderr
    assert probe_value(result.stdout, "WEBHOOK_ENABLED") == expected


# Confirms an unedited placeholder is never reported as a loaded secret, whichever layer recorded it
def test_placeholder_secrets_are_not_reported_as_loaded(monkeypatch):
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {"WEBHOOK_URL": "dotenv file", "SMTP_PASSWORD": "configuration file or command line"})
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "your_webhook_url")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "your_smtp_password")

    from_file, from_environment, from_settings = monitor.doctor_secret_sources(None)

    assert "WEBHOOK_URL" not in from_file + from_environment + from_settings
    assert "SMTP_PASSWORD" not in from_file + from_environment + from_settings


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
