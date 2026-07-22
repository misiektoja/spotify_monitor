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


# Runs one standalone command without allowing a nonzero status to raise
def run_cli(*arguments):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, str(CLI_PATH), *arguments], cwd=PROJECT_ROOT, capture_output=True, text=True, env=environment, timeout=30, check=False)


# Verifies private cookie replacement refuses a noninteractive terminal
def test_set_sp_dc_requires_interactive_terminal(tmp_path):
    with pytest.raises(monitor.BrowserCookieImportError, match="interactive terminal"):
        monitor.run_set_sp_dc(env_file=tmp_path / ".env", interactive=False, getpass_func=Mock(side_effect=AssertionError("prompted")))


# Verifies the standalone CLI reports noninteractive use without contacting Spotify
def test_set_sp_dc_cli_refuses_noninteractive_execution():
    result = run_cli("--set-sp-dc")
    assert result.returncode == 1
    assert "requires an interactive terminal" in result.stdout
    assert "To fix:" in result.stdout


# Verifies disabling dotenv persistence is rejected before any hidden prompt
def test_set_sp_dc_rejects_env_file_none():
    with pytest.raises(monitor.BrowserCookieImportError, match="requires a dotenv destination"):
        monitor.run_set_sp_dc(env_file="none", interactive=True, getpass_func=Mock(side_effect=AssertionError("prompted")))
    result = run_cli("--set-sp-dc", "--env-file", "none")
    assert result.returncode == 2
    assert "requires a writable dotenv destination" in result.stderr


# Verifies successful validation atomically replaces only SP_DC_COOKIE
def test_set_sp_dc_success_updates_only_cookie_atomically(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    destination.write_text("# keep\nUNRELATED=stay\nSP_DC_COOKIE=old-value\n\n", encoding="utf-8")
    validate = Mock(return_value=True)
    replace = Mock(wraps=os.replace)
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", validate)
    monkeypatch.setattr(monitor.os, "replace", replace)
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "find_config_file", lambda: None)

    result = monitor.run_set_sp_dc(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: "new-private-cookie")

    assert result == str(destination.resolve())
    assert destination.read_text(encoding="utf-8").startswith("# keep\nUNRELATED=stay\n")
    assert dotenv_values(destination, interpolate=False) == {"UNRELATED": "stay", "SP_DC_COOKIE": "new-private-cookie"}
    validate.assert_called_once_with("new-private-cookie")
    replace.assert_called_once()


# Verifies failed validation preserves an existing dotenv file byte for byte
def test_set_sp_dc_failed_validation_preserves_dotenv_bytes(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    original = b"# keep\nSP_DC_COOKIE=old-value\nUNRELATED=stay\n"
    destination.write_bytes(original)
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(side_effect=monitor.BrowserCookieImportError("invalid or expired")))

    with pytest.raises(monitor.BrowserCookieImportError, match="invalid or expired"):
        monitor.run_set_sp_dc(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: "new-private-cookie")
    assert destination.read_bytes() == original


# Verifies an existing cookie cannot be replaced without explicit confirmation
def test_set_sp_dc_existing_cookie_requires_confirmation(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    original = b"SP_DC_COOKIE=old-value\n"
    destination.write_bytes(original)
    getpass_mock = Mock(side_effect=AssertionError("hidden prompt used"))
    validate_mock = Mock(side_effect=AssertionError("validation used"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", validate_mock)

    with pytest.raises(monitor.BrowserCookieImportError, match="cancelled"):
        monitor.run_set_sp_dc(env_file=destination, interactive=True, input_func=lambda prompt: "n", getpass_func=getpass_mock)
    getpass_mock.assert_not_called()
    validate_mock.assert_not_called()
    assert destination.read_bytes() == original


# Verifies entered cookie values never appear in output or raised errors
def test_set_sp_dc_never_exposes_entered_cookie(tmp_path, monkeypatch, capsys):
    secret = "PHASE6-PRIVATE-COOKIE-SENTINEL"
    destination = tmp_path / ".env"
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(side_effect=RuntimeError(f"rejected {secret}")))

    with pytest.raises(monitor.BrowserCookieImportError) as error:
        monitor.run_set_sp_dc(env_file=destination, interactive=True, getpass_func=lambda prompt: secret)
    captured = capsys.readouterr()
    assert secret not in str(error.value)
    assert secret not in captured.out
    assert secret not in captured.err
    assert monitor.MANUAL_COOKIE_GUIDE_URL in captured.out
    assert not destination.exists()


# Verifies success output uses Compose commands and container paths without a secret
def test_set_sp_dc_success_uses_install_aware_container_commands(tmp_path, monkeypatch, capsys):
    secret = "PHASE6-COMPOSE-COOKIE-SENTINEL"
    destination = tmp_path / ".env"
    config_path = tmp_path / "spotify_monitor.conf"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "compose")

    monitor.run_set_sp_dc(env_file=destination, interactive=True, getpass_func=lambda prompt: secret, config_path=config_path)

    output = capsys.readouterr().out
    assert "docker compose run --rm spotify_monitor --doctor --config-file /data/spotify_monitor.conf --env-file /data/.env" in output
    assert "docker compose run --rm spotify_monitor SPOTIFY_USER_URI_ID --config-file /data/spotify_monitor.conf --env-file /data/.env" in output
    assert str(destination.resolve()) in output
    assert secret not in output


# Verifies all unrelated standalone actions and secret-bearing flags conflict with --set-sp-dc
@pytest.mark.parametrize("arguments", [("--setup",), ("--doctor",), ("--import-browser-cookie",), ("--version",), ("--generate-config",), ("--list-friends",), ("--send-test-email",), ("--spotify-dc-cookie", "value"), ("--force",), ("target.user",)])
def test_set_sp_dc_argument_conflicts(arguments):
    result = run_cli("--set-sp-dc", *arguments)
    assert result.returncode == 2
    assert "--set-sp-dc cannot be combined with" in result.stderr
