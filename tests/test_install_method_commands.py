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


# Verifies container prefixes use host-side IDs only for selected Linux hosts
def test_install_method_command_prefixes(monkeypatch):
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor.sys, "executable", "/usr/bin/python")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py"])
    monkeypatch.setattr(monitor.os, "getuid", lambda: 10001, raising=False)
    assert monitor._wizard_cmd_prefix("manual") == "python3 spotify_monitor.py"
    assert monitor._wizard_cmd_prefix("pip") == "spotify_monitor"
    assert monitor._wizard_cmd_prefix("docker") == 'docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor'
    monkeypatch.setattr(monitor.os, "getuid", lambda: 1000, raising=False)
    assert monitor._wizard_cmd_prefix("docker") == 'docker run --rm -it --init --user "$(id -u):$(id -g)" -v "${PWD}:/data:z" misiektoja/spotify-monitor'
    assert monitor._wizard_cmd_prefix("docker", host_os="macos") == 'docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor'
    assert monitor._wizard_cmd_prefix("docker", host_os="linux") == 'docker run --rm -it --init --user "$(id -u):$(id -g)" -v "${PWD}:/data:z" misiektoja/spotify-monitor'
    assert monitor._wizard_cmd_prefix("docker", host_os="windows-powershell") == 'docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor'
    assert monitor._wizard_cmd_prefix("docker", host_os="windows-cmd") == 'docker run --rm -it --init -v "%cd%:/data:z" misiektoja/spotify-monitor'
    assert monitor._wizard_cmd_prefix("compose") == "docker compose run --rm spotify_monitor"


# Verifies Windows help uses python while exact commands safely quote every spaced path
def test_windows_manual_commands_are_friendly_and_space_safe(tmp_path, monkeypatch):
    script_path = tmp_path / "Project Space" / "spotify_monitor.py"
    config_path = tmp_path / "Config Space" / "spotify_monitor.conf"
    env_path = tmp_path / "Config Space" / ".env"
    monkeypatch.setattr(monitor.platform, "system", lambda: "Windows")
    monkeypatch.setattr(monitor.sys, "executable", r"C:\Python Tools\python.exe")
    monkeypatch.setattr(monitor.sys, "argv", [str(script_path)])
    monkeypatch.setattr(monitor, "__file__", str(script_path))
    assert monitor._wizard_cmd_prefix("manual") == "python spotify_monitor.py"
    command = monitor._wizard_action_command("manual", "--doctor", config_path, env_path)
    assert '"C:\\Python Tools\\python.exe"' in command
    assert f'"{script_path}"' in command
    assert f'"{config_path}"' in command
    assert f'"{env_path}"' in command
    assert monitor._wizard_cmd_prefix("pip", exact=True) == '"C:\\Python Tools\\python.exe" -m spotify_monitor'


# Verifies container doctor and monitoring commands use /data paths and preserve a non-persisted target
def test_container_action_commands_include_paths_and_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "spotify_monitor.conf"
    env_path = tmp_path / ".env"
    command = monitor._wizard_action_command("compose", "--doctor", config_path, env_path, "target.user")
    assert command == "docker compose run --rm spotify_monitor --doctor target.user --config-file /data/spotify_monitor.conf --env-file /data/.env"


# Verifies container setup defaults always target the bind-mounted data directory
@pytest.mark.parametrize("method", ["docker", "compose"])
def test_container_setup_destinations_use_data_mount(tmp_path, monkeypatch, method):
    monkeypatch.chdir(tmp_path)
    config_path, env_path = monitor._wizard_destinations(method=method)
    assert config_path == Path("/data/spotify_monitor.conf")
    assert env_path == Path("/data/.env")


# Verifies temporary container paths outside the bind mount are rejected
@pytest.mark.parametrize("method", ["docker", "compose"])
def test_container_setup_rejects_destinations_outside_data(method):
    with pytest.raises(ValueError, match="must be inside /data"):
        monitor._wizard_destinations("/tmp/custom.conf", "/data/.env", method=method)
    with pytest.raises(ValueError, match="must be inside /data"):
        monitor._wizard_destinations("/data/custom.conf", "/tmp/custom.env", method=method)


# Verifies paths already expressed inside the bind mount remain unchanged
def test_container_paths_already_inside_data_are_preserved():
    assert monitor._wizard_container_path("/data/nested/custom.conf") == "/data/nested/custom.conf"


# Verifies Firefox import commands use the selected host profile layout
@pytest.mark.parametrize("host_os,source", [("macos", '"${HOME}/Library/Application Support/Firefox:/home/spotify/.mozilla/firefox:ro"'), ("linux", '"$HOME/.mozilla/firefox:/home/spotify/.mozilla/firefox:ro"'), ("linux-snap", '"$HOME/snap/firefox/common/.mozilla/firefox:/home/spotify/.mozilla/firefox:ro"'), ("linux-flatpak", '"$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox:/home/spotify/.mozilla/firefox:ro"'), ("windows-powershell", '"$env:APPDATA\\Mozilla\\Firefox:/home/spotify/.mozilla/firefox:ro"'), ("windows-cmd", '"%APPDATA%\\Mozilla\\Firefox:/home/spotify/.mozilla/firefox:ro"')])
def test_firefox_import_commands_mount_selected_host_profile(tmp_path, monkeypatch, host_os, source):
    monkeypatch.chdir(tmp_path)
    compose = monitor._wizard_firefox_import_cmd("compose", tmp_path / ".env", host_os=host_os)
    docker = monitor._wizard_firefox_import_cmd("docker", tmp_path / ".env", host_os=host_os)
    assert compose == f"docker compose run --rm -v {source} spotify_monitor --import-browser-cookie --browser firefox --env-file /data/.env"
    assert f"-v {source} misiektoja/spotify-monitor" in docker
    assert ('--user "$(id -u):$(id -g)"' in docker) is host_os.startswith("linux")
    assert ('-v "%cd%:/data:z"' in docker) is (host_os == "windows-cmd")
    assert docker.endswith("--import-browser-cookie --browser firefox --env-file /data/.env")


# Verifies a setup-generated import carries the saved config and target into post-import guidance
def test_firefox_import_command_carries_followup_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    command = monitor._wizard_firefox_import_cmd("docker", tmp_path / ".env", host_os="macos", config_path=tmp_path / "spotify_monitor.conf", target="target.user")
    assert "--import-browser-cookie --browser firefox target.user" in command
    assert "--config-file /data/spotify_monitor.conf --env-file /data/.env" in command


# Verifies private entry commands use installation-aware dotenv paths
def test_set_sp_dc_commands_use_container_data_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert monitor._wizard_set_sp_dc_cmd("pip") == "spotify_monitor --set-sp-dc"
    assert monitor._wizard_set_sp_dc_cmd("docker", tmp_path / ".env").endswith("misiektoja/spotify-monitor --set-sp-dc --env-file /data/.env")
    assert monitor._wizard_set_sp_dc_cmd("compose", tmp_path / ".env") == "docker compose run --rm spotify_monitor --set-sp-dc --env-file /data/.env"
    assert monitor._wizard_set_sp_dc_cmd("compose", tmp_path / ".env", config_path=tmp_path / "custom.conf") == "docker compose run --rm spotify_monitor --set-sp-dc --config-file /data/custom.conf --env-file /data/.env"


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
    assert "Welcome to Spotify Monitor" not in output
    assert "For <spotify_target>, use a Spotify user ID or complete profile URL.\n" in output
    assert "Quickest start (already configured):\n    spotify_monitor <spotify_target>\n" in output
    assert "Easiest start (guided setup wizard):\n    spotify_monitor --setup   (or just answer Y below)\n" in output
    assert "Check setup before monitoring:\n    spotify_monitor --doctor <spotify_target>\n" in output
    assert "spotify_monitor --setup" in output
    assert "spotify_monitor <spotify_target>" in output
    assert "spotify_monitor --doctor" in output
    assert f"Guide:        {monitor.QUICK_START_GUIDE_URL}" in output


# Verifies noninteractive no-argument welcome never prompts and exits with concise guidance
def test_noninteractive_welcome_does_not_prompt(monkeypatch, capsys):
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: False))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", Mock(side_effect=AssertionError("prompted")))
    monitor._wizard_welcome()
    output = capsys.readouterr().out
    assert "Quickest start (already configured)" in output
    assert "Easiest start (guided setup wizard)" in output
    assert "or just answer Y below" not in output
    assert "Full options: spotify_monitor --help" in output
    assert monitor.QUICK_START_GUIDE_URL in output


# Verifies manual help examples preserve exact comments, indentation and portable commands
def test_manual_help_epilog_exact_raw_text(monkeypatch):
    force_install_environment(monkeypatch, argv0="spotify_monitor.py")
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor.sys, "executable", "/usr/bin/python3")
    assert monitor._build_help_epilog() == """Examples:
  # Guided setup, recommended for the first run
  python3 spotify_monitor.py --setup

  # Open https://open.spotify.com/ in Firefox and sign in first
  # Then import Spotify login from Firefox (recommended for local installs)
  python3 spotify_monitor.py --import-browser-cookie --browser firefox

  # Or enter the Spotify cookie through a hidden prompt
  python3 spotify_monitor.py --set-sp-dc

  # Save a Discord or ntfy webhook URL through a hidden prompt
  python3 spotify_monitor.py --set-webhook-url

  # Send one test webhook without starting monitoring
  python3 spotify_monitor.py --send-test-webhook

  # Monitor one Spotify user
  # A spotify:user URI or profile URL is also accepted
  python3 spotify_monitor.py <spotify_user_id>

  # Check authentication, connectivity and one target
  python3 spotify_monitor.py --doctor <spotify_user_id>

  # List friends visible to the configured Spotify account
  python3 spotify_monitor.py --list-friends

  # Advanced Spotify desktop client mode
  python3 spotify_monitor.py <spotify_user_id> --token-source client --login-request-body-file <protobuf_file>

Guide: https://misiektoja.github.io/spotify_monitor/setup-and-first-run/
"""


# Verifies pip help examples use the installed console command throughout
def test_pip_help_epilog_uses_console_command(monkeypatch):
    force_install_environment(monkeypatch, argv0="/usr/local/bin/spotify_monitor")
    epilog = monitor._build_help_epilog()
    assert "spotify_monitor --setup" in epilog
    assert "spotify_monitor --import-browser-cookie --browser firefox" in epilog
    assert "spotify_monitor --set-sp-dc" in epilog
    assert "recommended for local installs" in epilog
    assert "spotify_monitor <spotify_user_id>" in epilog
    assert "spotify_monitor --doctor <spotify_user_id>" in epilog
    assert "spotify_monitor --list-friends" in epilog


# Verifies Docker help examples include safe container paths and the Linux host note
def test_docker_help_epilog_uses_container_commands(monkeypatch):
    force_install_environment(monkeypatch, docker_env=True, argv0="spotify_monitor.py")
    epilog = monitor._build_help_epilog()
    prefix = monitor._wizard_cmd_prefix("docker")
    assert f"{prefix} --setup" in epilog
    assert f"{prefix} --set-sp-dc --env-file /data/.env" in epilog
    assert monitor._wizard_firefox_import_cmd("docker", Path.cwd() / ".env") in epilog
    assert epilog.index("--import-browser-cookie") < epilog.index("--set-sp-dc")
    assert "Linux host example" in epilog
    assert "profile read-only" in epilog
    assert "Host Spotify auto-play is unavailable by default" in epilog
    assert f"{prefix} --doctor <spotify_user_id>" in epilog
    assert "--login-request-body-file /data/login.protobuf" in epilog


# Verifies Compose help examples include service commands and the saved-target launch
def test_compose_help_epilog_uses_service_commands(monkeypatch):
    force_install_environment(monkeypatch, dockerenv=True, compose_env=True, argv0="spotify_monitor.py")
    epilog = monitor._build_help_epilog()
    prefix = monitor._wizard_cmd_prefix("compose")
    assert f"{prefix} --setup" in epilog
    assert f"{prefix} --set-sp-dc --env-file /data/.env" in epilog
    assert monitor._wizard_firefox_import_cmd("compose", Path.cwd() / ".env") in epilog
    assert epilog.index("--import-browser-cookie") < epilog.index("--set-sp-dc")
    assert f"{prefix} --list-friends" in epilog
    assert "--login-request-body-file /data/login.protobuf" in epilog
    assert "# Start from the target saved by setup\n  docker compose up --no-log-prefix" in epilog


# Verifies every help epilog avoids command-line secret flags and values
@pytest.mark.parametrize("method", ["manual", "pip", "docker", "compose"])
def test_help_epilog_contains_no_secret_bearing_examples(monkeypatch, method):
    force_install_environment(monkeypatch, dockerenv=method in ("docker", "compose"), compose_env=method == "compose", argv0="spotify_monitor.py" if method != "pip" else "spotify_monitor")
    epilog = monitor._build_help_epilog()
    for forbidden in ("--spotify-dc-cookie", " sp_dc", "refresh_token", "SMTP_PASSWORD", "SP_APP_CLIENT_ID", "SP_APP_CLIENT_SECRET", " -u "):
        assert forbidden not in epilog
