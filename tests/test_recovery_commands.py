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
    command = next(line.split("Or run once with: ", 1)[1] for line in output.splitlines() if "Or run once with:" in line)

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
    command = next(line.split("Or run once with: ", 1)[1] for line in output.splitlines() if "Or run once with:" in line)
    tokens = shlex.split(command)
    assert tokens[tokens.index("--env-file") + 1] == str(explicit if override else saved)
