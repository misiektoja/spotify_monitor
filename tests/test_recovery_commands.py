"""Recovery commands retain their arguments while diagnostic credentials stay hidden."""

import shlex
import sys

import pytest

import spotify_monitor as monitor


@pytest.mark.parametrize("secret", ["data", "spotify", "--browser", "env", "https"])
@pytest.mark.parametrize("method", ["pip", "manual", "compose", "docker"])
# Keeps generated cookie recovery instructions independent of unrelated credential values
def test_cookie_recovery_commands_survive_secret_collisions(monkeypatch, tmp_path, secret, method):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: method)
    monkeypatch.setattr(monitor, "is_container_environment", lambda: method in ("compose", "docker"))
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", str(tmp_path / "data" / "settings.conf"))
    monkeypatch.setattr(monitor, "DOTENV_FILE", str(tmp_path / "data" / "private.env"))
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "")
    expected = monitor.cookie_auth_recovery_fix()
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", secret)

    advice = monitor.classify_recovery_error(RuntimeError(f"expired sp_dc, password={secret}"), "cookie_auth")
    rendered = monitor.render_recovery_advice(advice, debug=True)

    assert expected in rendered
    assert f"password={secret}" not in advice.detail
    assert "<redacted>" in advice.detail


@pytest.mark.parametrize("colored", [False, True])
# Preserves complete backend switch arguments through the final Doctor rendering
def test_doctor_backend_command_preserves_paths_and_target(monkeypatch, tmp_path, colored):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", colored)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {"header": "\x1b[36m", "section": "\x1b[37m", "error": "\x1b[31m", "info": "\x1b[34m"})
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "data")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "private-cookie-value")
    monkeypatch.setattr(monitor, "TARGET_USER_URI_ID", "")
    config = tmp_path / "data directory" / "settings.conf"
    env = tmp_path / "data directory" / "private.env"
    fix = monitor.backend_switch_fix("buddylist", "data.friend", str(config), str(env))
    advice = monitor.make_recovery_advice("target.not_visible", "Other backend lists the target", fix, False)
    check = monitor.make_doctor_check("Target", "FAIL", advice.summary, "cookie=private-cookie-value", advice)

    rendered = monitor.render_doctor_sections(monitor.DoctorReport([check]))
    assert ("\x1b[" in rendered) is colored
    output = monitor.ANSI_ESCAPE_RE.sub("", rendered)
    command = next(line.strip() for line in output.splitlines() if line.strip().startswith("spotify_monitor --friend-activity-backend "))

    assert shlex.split(command) == ["spotify_monitor", "--friend-activity-backend", "buddylist", "data.friend", "--config-file", str(config), "--env-file", str(env)]
    assert "private-cookie-value" not in output


# Redacts externally supplied Doctor fields even when a caller constructs the row directly
def test_doctor_raw_fields_remain_secret_safe(monkeypatch):
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "private-cookie-value")
    check = monitor.DoctorCheck("Target", "PASS", "reply private-cookie-value", "access_token=unconfigured-token")

    output = monitor.render_doctor_sections(monitor.DoctorReport([check]))

    assert "private-cookie-value" not in output
    assert "unconfigured-token" not in output


@pytest.mark.parametrize("override", [False, True])
# Uses the selected dotenv file in Doctor commands when configuration and CLI paths differ
def test_doctor_cli_keeps_selected_dotenv_path(monkeypatch, tmp_path, capsys, override):
    saved = tmp_path / "saved.env"
    explicit = tmp_path / "selected.env"
    config = tmp_path / "settings.conf"
    saved.write_text("", encoding="utf-8")
    explicit.write_text("", encoding="utf-8")
    config.write_text(f"DOTENV_FILE = {str(saved)!r}\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor, "_doctor_offer_notification_tests", lambda report: [])
    monkeypatch.chdir(tmp_path)

    # Exercises the real CLI path selection and report renderer without remote checks
    def build_report(target_value, config_path, env_path, startup_checks, progress=None):
        fix = monitor.backend_switch_fix("buddylist", target_value, config_path, env_path)
        advice = monitor.make_recovery_advice("target.not_visible", "Other backend lists the target", fix, False)
        return monitor.DoctorReport([monitor.make_doctor_check("Target", "FAIL", advice.summary, advice=advice)])

    monkeypatch.setattr(monitor, "build_doctor_report", build_report)
    arguments = ["spotify_monitor", "friend", "--doctor", "--config-file", str(config), "--no-color"]
    if override:
        arguments.extend(["--env-file", str(explicit)])
    monkeypatch.setattr(sys, "argv", arguments)

    with pytest.raises(SystemExit) as result:
        monitor.main()

    assert result.value.code == 1
    output = capsys.readouterr().out
    command = next(line.strip() for line in output.splitlines() if line.strip().startswith("spotify_monitor --friend-activity-backend "))
    tokens = shlex.split(command)
    assert tokens[tokens.index("--env-file") + 1] == str(explicit if override else saved)


@pytest.mark.parametrize("backend", ["buddylist", "listening_activity"])
@pytest.mark.parametrize("config", [None, "none", "settings.conf"])
# Keeps disabled file discovery in the switch command and explains how to save a backend choice
def test_backend_switch_guidance_distinguishes_configuration_states(monkeypatch, tmp_path, backend, config):
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "TARGET_USER_URI_ID", "")
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "CONFIG_DISCOVERY_DISABLED", config == "none")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "none")
    selected = str(tmp_path / config) if config == "settings.conf" else config

    fix = monitor.backend_switch_fix(backend, "friend", config_path=selected)
    command = next(line.strip() for line in fix.splitlines() if line.strip().startswith("spotify_monitor "))
    tokens = shlex.split(command)

    assert tokens[:4] == ["spotify_monitor", "--friend-activity-backend", backend, "friend"]
    assert tokens[-2:] == ["--env-file", "none"]
    assert "each time you start monitoring" in fix
    assert "run once" not in fix
    if selected is None:
        assert "--config-file" not in tokens
        assert "create or select a configuration file" in fix
    elif selected == "none":
        assert tokens[tokens.index("--config-file") + 1] == "none"
        assert "Configuration loading is disabled by --config-file none" in fix
        assert "load it with --config-file PATH" in fix
    else:
        assert tokens[tokens.index("--config-file") + 1] == selected
        assert f"in '{selected}' for future runs" in fix
        assert "does not change the configuration file" in fix


@pytest.mark.parametrize("mode", ["friend_activity", "scrobble_health"])
# Replays the printed Doctor command to verify mode, backend, timers and disabled switches survive
def test_doctor_next_command_preserves_effective_overrides(monkeypatch, tmp_path, capsys, mode):
    config = tmp_path / "settings.conf"
    opposite_mode = "scrobble_health" if mode == "friend_activity" else "friend_activity"
    saved = f'MONITOR_MODE = "{opposite_mode}"\nLASTFM_USERNAME = "example"\nFRIEND_ACTIVITY_BACKEND = "listening_activity"\nSPOTIFY_CHECK_INTERVAL = 30\nSCROBBLE_HEALTH_CHECK_INTERVAL = 180\nSCROBBLE_HEALTH_REPEAT_INTERVAL = 120\nERROR_NOTIFICATION = True\nWEBHOOK_ENABLED = True\nTRUNCATE_CHARS = 80\n'
    config.write_text(saved, encoding="utf-8")
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    observations = []

    # Records settings at the Doctor boundary without making remote requests
    def doctor(*args):
        observations.append((monitor.MONITOR_MODE, monitor.FRIEND_ACTIVITY_BACKEND, monitor.SPOTIFY_CHECK_INTERVAL, monitor.SCROBBLE_HEALTH_CHECK_INTERVAL, monitor.SCROBBLE_HEALTH_REPEAT_INTERVAL, monitor.ERROR_NOTIFICATION, monitor.WEBHOOK_ENABLED, monitor.TRUNCATE_CHARS, monitor.USER_AGENT))
        return 0

    monkeypatch.setattr(monitor, "run_doctor", doctor)
    monkeypatch.setattr(monitor, "run_scrobble_health_doctor", doctor)
    arguments = ["spotify_monitor", "--doctor", "--monitor-mode", mode, "--config-file", str(config), "--env-file", "none", "--friend-activity-backend", "buddylist", "--check-interval", "70", "--scrobble-check-interval", "300", "--scrobble-repeat-interval", "0", "--no-webhook", "--no-error-notify", "--truncate", "0", "--user-agent=-example agent", "--no-color"]
    if mode == "friend_activity":
        arguments.append("friend")
    monkeypatch.setattr(sys, "argv", arguments)
    with pytest.raises(SystemExit) as result:
        monitor.main()
    assert result.value.code == 0
    output = capsys.readouterr().out
    command = next(line.strip() for line in output.splitlines() if line.strip().startswith("spotify_monitor "))
    tokens = shlex.split(command)
    assert "--doctor" not in tokens
    assert tokens[tokens.index("--friend-activity-backend") + 1] == "buddylist"
    assert "--no-webhook" in tokens
    assert "--no-error-notify" in tokens
    monkeypatch.setattr(sys, "argv", [*tokens, "--doctor"])
    with pytest.raises(SystemExit) as replay:
        monitor.main()
    assert replay.value.code == 0
    assert observations == [(mode, "buddylist", 70, 300, 0, False, False, 0, "-example agent")] * 2
    assert config.read_text(encoding="utf-8") == saved


# Retains private command-line options as placeholders without printing their supplied values
def test_doctor_next_command_uses_placeholders_for_private_overrides(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "run_scrobble_health_doctor", lambda *args: 0)
    arguments = ["spotify_monitor", "--doctor", "--monitor-mode", "scrobble_health", "--lastfm-username", "example", "--config-file", "none", "--env-file", "none", "--spotify-dc-cookie", "private-cookie", "--oauth-app-creds", "app-id:private-app-secret", "--webhook-url", "https://ntfy.sh/private-destination", "--lastfm-api-key", "private-api-key", "--scrobble-refresh-token", "private-refresh", "--no-color"]
    monkeypatch.setattr(sys, "argv", arguments)

    with pytest.raises(SystemExit) as result:
        monitor.main()

    assert result.value.code == 0
    output = capsys.readouterr().out
    for secret in ("private-cookie", "private-app-secret", "private-destination", "private-api-key", "private-refresh"):
        assert secret not in output
    for pair in ("--spotify-dc-cookie SP_DC_COOKIE", "--oauth-app-creds SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET", "--webhook-url WEBHOOK_URL", "--lastfm-api-key LASTFM_API_KEY", "--scrobble-refresh-token SPOTIFY_SCROBBLE_REFRESH_TOKEN"):
        assert pair in output
    assert "Replace the uppercase credential placeholders before running" in output
