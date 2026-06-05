import os
from pathlib import Path
from unittest.mock import Mock

import pytest

import spotify_monitor as monitor


# Forces install-method inputs to a known environment for one assertion
def force_install_environment(monkeypatch, dockerenv=False, docker_env=False, compose_env=False, argv0="spotify_monitor"):
    monkeypatch.setattr(monitor.os.path, "exists", lambda path: dockerenv and path == "/.dockerenv")
    if docker_env:
        monkeypatch.setenv("SPOTIFY_MONITOR_DOCKER", "1")
    else:
        monkeypatch.delenv("SPOTIFY_MONITOR_DOCKER", raising=False)
    if compose_env:
        monkeypatch.setenv("SPOTIFY_MONITOR_COMPOSE", "1")
    else:
        monkeypatch.delenv("SPOTIFY_MONITOR_COMPOSE", raising=False)
    monkeypatch.setattr(monitor.sys, "argv", [argv0])


# Verifies manual and pip launches are distinguished by the executable name
def test_install_method_detects_manual_and_pip(monkeypatch):
    force_install_environment(monkeypatch, argv0="spotify_monitor.py")
    assert monitor._wizard_install_method() == "manual"
    force_install_environment(monkeypatch, argv0="/usr/local/bin/spotify_monitor")
    assert monitor._wizard_install_method() == "pip"


# Verifies both Docker markers and the Compose marker follow the required precedence
def test_install_method_detects_docker_and_compose(monkeypatch):
    force_install_environment(monkeypatch, dockerenv=True, argv0="spotify_monitor.py")
    assert monitor._wizard_install_method() == "docker"
    force_install_environment(monkeypatch, docker_env=True, argv0="spotify_monitor.py")
    assert monitor._wizard_install_method() == "docker"
    force_install_environment(monkeypatch, dockerenv=True, compose_env=True, argv0="spotify_monitor.py")
    assert monitor._wizard_install_method() == "compose"


# Verifies every installation method has the requested portable command prefix
def test_install_method_command_prefixes():
    assert monitor._wizard_cmd_prefix("manual") == "python3 spotify_monitor.py"
    assert monitor._wizard_cmd_prefix("pip") == "spotify_monitor"
    assert monitor._wizard_cmd_prefix("docker") == 'docker run --rm -it --init -v "$PWD:/data" misiektoja/spotify-monitor'
    assert monitor._wizard_cmd_prefix("compose") == "docker compose run --rm spotify_monitor"


# Verifies container doctor and monitoring commands use /data paths and preserve a non-persisted target
def test_container_action_commands_include_paths_and_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "spotify_monitor.conf"
    env_path = tmp_path / ".env"
    command = monitor._wizard_action_command("compose", "--doctor", config_path, env_path, "target.user")
    assert command == "docker compose run --rm spotify_monitor --doctor target.user --config-file /data/spotify_monitor.conf --env-file /data/.env"


# Verifies the Linux Firefox mount command places the volume before the container service or image
def test_firefox_import_commands_mount_linux_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    compose = monitor._wizard_firefox_import_cmd("compose", tmp_path / ".env")
    docker = monitor._wizard_firefox_import_cmd("docker", tmp_path / ".env")
    assert compose == 'docker compose run --rm -v "$HOME/.mozilla/firefox:/home/spotify/.mozilla/firefox:ro" spotify_monitor --import-browser-cookie --browser firefox --env-file /data/.env'
    assert '-v "$HOME/.mozilla/firefox:/home/spotify/.mozilla/firefox:ro" misiektoja/spotify-monitor' in docker
    assert docker.endswith("--import-browser-cookie --browser firefox --env-file /data/.env")


# Verifies Chromium-family browser choices are removed on Windows and inside containers
def test_browser_choices_respect_platform_and_container(monkeypatch):
    monkeypatch.setattr(monitor.platform, "system", lambda: "Darwin")
    assert monitor._wizard_import_browsers("pip") == list(monitor.IMPORT_BROWSERS)
    monkeypatch.setattr(monitor.platform, "system", lambda: "Windows")
    assert monitor._wizard_import_browsers("pip") == ["firefox"]
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    assert monitor._wizard_import_browsers("docker") == ["firefox"]
    assert monitor._wizard_import_browsers("compose") == ["firefox"]


# Verifies interactive no-argument welcome can decline setup cleanly
def test_interactive_welcome_declines_setup(monkeypatch, capsys):
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: False)
    monitor._wizard_welcome()
    output = capsys.readouterr().out
    assert "spotify_monitor --setup" in output
    assert "spotify_monitor <spotify_user_id>" in output
    assert "spotify_monitor --doctor" in output


# Verifies noninteractive no-argument welcome never prompts and exits with concise guidance
def test_noninteractive_welcome_does_not_prompt(monkeypatch, capsys):
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: False))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", Mock(side_effect=AssertionError("prompted")))
    with pytest.raises(SystemExit) as error:
        monitor._wizard_welcome()
    assert error.value.code == 1
    output = capsys.readouterr().out
    assert "interactive terminal" in output
    assert "usage:" not in output.casefold() or "spotify_monitor" in output
