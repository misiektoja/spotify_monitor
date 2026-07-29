import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from dotenv import dotenv_values

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "spotify_monitor.py"


# Returns one isolated project-local private-settings path
def local_destination(name):
    destination = PROJECT_ROOT / "local" / f"test-lastfm-credentials-{os.getpid()}-{name}.env"
    if destination.exists():
        destination.unlink()
    return destination


# Deletes one project-local test destination after an assertion
def cleanup_destination(destination):
    if destination.exists():
        destination.unlink()


# Runs one standalone command without raising for a nonzero status
def run_cli(*arguments):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, str(CLI_PATH), *arguments], cwd=PROJECT_ROOT, capture_output=True, text=True, env=environment, timeout=30, check=False)


# Verifies private Last.fm setup requires an interactive terminal
def test_set_lastfm_credentials_requires_interactive_terminal():
    destination = local_destination("noninteractive")
    try:
        with pytest.raises(monitor.LastfmConfigurationError, match="interactive terminal"):
            monitor.run_set_lastfm_credentials(env_file=destination, interactive=False, getpass_func=Mock(side_effect=AssertionError("prompted")))
    finally:
        cleanup_destination(destination)


# Verifies standalone noninteractive use returns safe recovery guidance
def test_set_lastfm_credentials_cli_refuses_noninteractive_execution():
    result = run_cli("--set-lastfm-credentials")
    assert result.returncode == 1
    assert "needs an interactive terminal" in result.stdout
    assert "To fix:" in result.stdout


# Verifies disabling dotenv persistence is rejected before hidden entry
def test_set_lastfm_credentials_rejects_env_file_none():
    with pytest.raises(monitor.LastfmConfigurationError, match="requires a dotenv destination"):
        monitor.run_set_lastfm_credentials(env_file="none", interactive=True, getpass_func=Mock(side_effect=AssertionError("prompted")))
    result = run_cli("--set-lastfm-credentials", "--env-file", "none")
    assert result.returncode == 2
    assert "requires a writable dotenv destination" in result.stderr


# Verifies hidden entry atomically updates only the Last.fm API key
def test_set_lastfm_credentials_updates_only_api_key(monkeypatch, capsys):
    destination = local_destination("success")
    secret = "LASTFM-PRIVATE-KEY-SENTINEL"
    try:
        destination.write_text("# keep\nUNRELATED=stay\nLASTFM_API_KEY=old-value\n", encoding="utf-8")
        replace = Mock(wraps=os.replace)
        monkeypatch.setattr(monitor.os, "replace", replace)
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
        monkeypatch.setattr(monitor, "find_scrobble_health_config_file", lambda: None)

        result = monitor.run_set_lastfm_credentials(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: secret)

        output = capsys.readouterr().out
        assert result == str(destination.resolve())
        assert destination.read_text(encoding="utf-8").startswith("# keep\nUNRELATED=stay\n")
        assert dotenv_values(destination, interpolate=False) == {"UNRELATED": "stay", "LASTFM_API_KEY": secret}
        assert secret not in output
        assert monitor.LASTFM_API_ACCOUNTS_URL in output
        assert "--monitor-mode scrobble_health --doctor" in output
        assert "--monitor-mode scrobble_health" in output
        replace.assert_called_once()
        if os.name == "posix":
            assert destination.stat().st_mode & 0o777 == 0o600
    finally:
        cleanup_destination(destination)


# Verifies standalone Last.fm entry defaults to the isolated scrobble health dotenv file
def test_set_lastfm_credentials_uses_scrobble_health_default(monkeypatch):
    update_mock = Mock(return_value={})
    monkeypatch.chdir(PROJECT_ROOT / "local")
    monkeypatch.setattr(monitor, "_dotenv_contains_key", lambda path, key: False)
    monkeypatch.setattr(monitor, "update_dotenv_file", update_mock)
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "find_scrobble_health_config_file", lambda: None)
    destination = monitor.run_set_lastfm_credentials(interactive=True, getpass_func=lambda prompt: "private-key")
    assert destination == str((PROJECT_ROOT / "local" / ".env.scrobble_health").resolve())
    assert update_mock.call_args.args[0] == Path(destination)


# Verifies declined replacement leaves the existing key unchanged
def test_set_lastfm_credentials_requires_replacement_confirmation():
    destination = local_destination("declined")
    original = b"LASTFM_API_KEY=old-value\nUNRELATED=stay\n"
    try:
        destination.write_bytes(original)
        hidden_prompt = Mock(side_effect=AssertionError("hidden prompt used"))
        with pytest.raises(monitor.LastfmConfigurationError, match="cancelled"):
            monitor.run_set_lastfm_credentials(env_file=destination, interactive=True, input_func=lambda prompt: "n", getpass_func=hidden_prompt)
        hidden_prompt.assert_not_called()
        assert destination.read_bytes() == original
    finally:
        cleanup_destination(destination)


# Verifies invalid hidden input never changes or exposes the saved key
def test_set_lastfm_credentials_rejects_invalid_input_without_leak(capsys):
    destination = local_destination("invalid")
    original = b"UNRELATED=stay\n"
    secret = "PRIVATE\nKEY"
    try:
        destination.write_bytes(original)
        with pytest.raises(monitor.LastfmConfigurationError) as error:
            monitor.run_set_lastfm_credentials(env_file=destination, interactive=True, getpass_func=lambda prompt: secret)
        output = capsys.readouterr()
        assert secret not in str(error.value)
        assert secret not in output.out
        assert secret not in output.err
        assert destination.read_bytes() == original
    finally:
        cleanup_destination(destination)


@pytest.mark.parametrize("arguments", [("--setup",), ("--setup-scrobble-health",), ("--set-sp-dc",), ("--set-webhook-url",), ("--doctor",), ("--version",), ("--generate-config",), ("--list-friends",), ("--send-test-email",), ("--monitor-mode", "scrobble_health"), ("target.user",)])
# Verifies unrelated actions conflict with private Last.fm setup
def test_set_lastfm_credentials_argument_conflicts(arguments):
    result = run_cli("--set-lastfm-credentials", *arguments)
    assert result.returncode == 2
    assert "--set-lastfm-credentials cannot be combined with" in result.stderr


# Verifies a config path remains available for printed follow-up commands
def test_set_lastfm_credentials_cli_accepts_config_context():
    result = run_cli("--set-lastfm-credentials", "--config-file", "custom.conf")
    assert result.returncode == 1
    assert "needs an interactive terminal" in result.stdout
    assert "cannot be combined" not in result.stderr
