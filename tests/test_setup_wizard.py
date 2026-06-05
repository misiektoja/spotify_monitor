import builtins
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from dotenv import dotenv_values

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "wizard_test_artifacts"


# Creates one disposable wizard test directory under the project local directory
def make_test_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT)


# Installs sequential plain input responses and an interactive stdin marker
def install_inputs(monkeypatch, responses):
    iterator = iter(responses)
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(builtins, "input", lambda prompt="": next(iterator))


# Installs a minimal mocked wizard flow for doctor and launch boundary tests
def install_minimal_wizard_flow(monkeypatch, method, auth, answers, report=None):
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: method)
    monkeypatch.setattr(monitor, "_wizard_target", lambda initial=None: "target.user")
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: 0)
    monkeypatch.setattr(monitor, "_wizard_collect_cookie_auth", lambda *args, **kwargs: dict(auth))
    monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda *args, **kwargs: 30)
    monkeypatch.setattr(monitor, "_wizard_collect_email", lambda config, secrets, env: [])
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", Mock(side_effect=list(answers)))
    if report is not None:
        monkeypatch.setattr(monitor, "build_doctor_report", Mock(return_value=report))
        monkeypatch.setattr(monitor, "render_doctor_report", lambda selected: "DOCTOR REPORT")


# Verifies required text re-prompts and applies defaults
def test_text_helper_required_and_default(monkeypatch, capsys):
    install_inputs(monkeypatch, ["", "value"])
    assert monitor._wizard_ask_text("Required", required=True) == "value"
    assert "required" in capsys.readouterr().out.casefold()
    install_inputs(monkeypatch, [""])
    assert monitor._wizard_ask_text("Optional", default="default") == "default"


# Verifies yes or no and numbered choices recover from invalid input
def test_yes_no_and_choice_helpers_validate(monkeypatch, capsys):
    install_inputs(monkeypatch, ["maybe", "yes"])
    assert monitor._wizard_ask_yes_no("Continue?") is True
    install_inputs(monkeypatch, ["9", "2"])
    assert monitor._wizard_ask_choice("Pick", [("One", ""), ("Two", "")]) == 1
    output = capsys.readouterr().out
    assert "answer 'y' or 'n'" in output
    assert "between 1 and 2" in output


# Verifies positive integer input rejects zero and non-numeric values
def test_positive_integer_helper_reprompts(monkeypatch, capsys):
    install_inputs(monkeypatch, ["bad", "0", "15"])
    assert monitor._wizard_ask_positive_int("Interval", 30) == 15
    assert capsys.readouterr().out.count("positive whole number") == 2


# Verifies Ctrl+C and Ctrl+D cancel cleanly without a traceback
@pytest.mark.parametrize("error_type", [KeyboardInterrupt, EOFError])
def test_input_cancellation_is_clean(monkeypatch, capsys, error_type):
    monkeypatch.setattr(builtins, "input", Mock(side_effect=error_type))
    with pytest.raises(SystemExit) as error:
        monitor._wizard_input("Prompt: ")
    assert error.value.code == 1
    assert "Setup cancelled" in capsys.readouterr().out


# Verifies secret input uses getpass and rejects an empty secret
def test_secret_helper_uses_getpass(monkeypatch, capsys):
    getpass_mock = Mock(side_effect=["", "private-value"])
    monkeypatch.setattr(monitor.getpass, "getpass", getpass_mock)
    assert monitor._wizard_ask_secret("Secret") == "private-value"
    assert getpass_mock.call_count == 2
    assert "private-value" not in capsys.readouterr().out


# Verifies target prompts accept every supported form and re-prompt after invalid input
@pytest.mark.parametrize("raw", ["target.user", "spotify:user:target.user", "https://open.spotify.com/user/target.user"])
def test_target_helper_normalizes_supported_forms(monkeypatch, raw):
    install_inputs(monkeypatch, ["bad target", raw])
    assert monitor._wizard_target() == "target.user"


# Verifies a confirmed manual-cookie setup keeps its secret out of the generated config and output
def test_manual_cookie_setup_persists_secret_only_to_dotenv(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        config_path = directory / "spotify_monitor.conf"
        env_path = directory / ".env"
        install_inputs(monkeypatch, ["spotify:user:target.user", "y", "1", "3", "", "n", "y", "n"])
        monkeypatch.setattr(monitor.getpass, "getpass", lambda prompt="": "cookie-private-value")
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=config_path, env_file=env_path)
        assert error.value.code == 0
        config = config_path.read_text(encoding="utf-8")
        assert 'TARGET_USER_URI_ID = "target.user"' in config
        assert "cookie-private-value" not in config
        assert dotenv_values(env_path, interpolate=False)["SP_DC_COOKIE"] == "cookie-private-value"
        output = capsys.readouterr().out
        assert "cookie-private-value" not in output
        assert "authentication has not been validated" in output


# Verifies declining final confirmation leaves both setup destinations unchanged
def test_cancellation_before_confirmation_changes_no_files(monkeypatch):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        config_path = directory / "spotify_monitor.conf"
        env_path = directory / ".env"
        install_inputs(monkeypatch, ["target.user", "y", "1", "4", "", "n", "n"])
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=config_path, env_file=env_path)
        assert error.value.code == 1
        assert not config_path.exists()
        assert not env_path.exists()


# Verifies a non-persisted target remains absent from config and appears in exact next commands
def test_nonpersisted_target_is_added_to_commands(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        install_inputs(monkeypatch, ["https://open.spotify.com/user/target.user", "n", "1", "4", "", "n", "y", "n"])
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "compose")
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=directory / ".env")
        assert error.value.code == 0
        config = (directory / "spotify_monitor.conf").read_text(encoding="utf-8")
        assert 'TARGET_USER_URI_ID = ""' in config
        output = capsys.readouterr().out
        assert "docker compose up requires a persisted target" in output
        assert "--doctor target.user" in output
        assert "spotify_monitor target.user --config-file" in output


# Verifies successful browser import receives the selected dotenv path and enables local launch eligibility
def test_browser_import_reuses_phase2_runner(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        env_path = directory / ".env"
        install_inputs(monkeypatch, ["target.user", "y", "1", "1", "", "", "n", "y", "n", "n"])
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        monkeypatch.setattr(monitor.platform, "system", lambda: "Darwin")
        import_mock = Mock(side_effect=lambda **kwargs: monitor.update_dotenv_file(kwargs["env_file"], {"SP_DC_COOKIE": "browser-private-value"}))
        monkeypatch.setattr(monitor, "run_browser_cookie_import", import_mock)
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=env_path)
        assert error.value.code == 0
        assert import_mock.call_args.kwargs["env_file"] == str(env_path.resolve())
        assert import_mock.call_args.kwargs["browser"] == "firefox"
        assert "browser-private-value" not in capsys.readouterr().out


# Verifies browser import failure can finish setup without discarding the generated config
def test_browser_import_failure_allows_incomplete_recovery(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        install_inputs(monkeypatch, ["target.user", "y", "1", "1", "", "", "n", "y", "3", "n"])
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        monkeypatch.setattr(monitor.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(monitor, "run_browser_cookie_import", Mock(side_effect=monitor.BrowserCookieImportError("safe import failure")))
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=directory / ".env")
        assert error.value.code == 0
        assert (directory / "spotify_monitor.conf").is_file()
        output = capsys.readouterr().out
        assert "safe import failure" in output
        assert "authentication is incomplete" in output


# Verifies failed browser import can retry through the same Phase 2 runner
def test_browser_import_retry_succeeds(monkeypatch):
    with make_test_directory() as directory_name:
        env_path = Path(directory_name) / ".env"
        auth = {"complete": False, "validated": False, "browser": "firefox", "source": "browser import (Firefox)"}
        runner = Mock(side_effect=[monitor.BrowserCookieImportError("safe failure"), str(env_path)])
        monkeypatch.setattr(monitor, "run_browser_cookie_import", runner)
        monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: 0)
        result = monitor._wizard_finish_browser_import(auth, env_path)
        assert runner.call_count == 2
        assert result["complete"] is True
        assert result["validated"] is True


# Verifies declining manual replacement retains an existing cookie without secret output
def test_manual_cookie_replacement_decline_retains_existing(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        env_path = Path(directory_name) / ".env"
        env_path.write_text("SP_DC_COOKIE=existing-private-value\n", encoding="utf-8")
        install_inputs(monkeypatch, ["3", "n"])
        monkeypatch.setattr(monitor.getpass, "getpass", lambda prompt="": "new-private-value")
        updates = {}
        result = monitor._wizard_collect_cookie_auth("manual", env_path, updates)
        assert updates == {}
        assert result["complete"] is True
        assert dotenv_values(env_path, interpolate=False)["SP_DC_COOKIE"] == "existing-private-value"
        output = capsys.readouterr().out
        assert "existing-private-value" not in output
        assert "new-private-value" not in output


# Verifies advanced client parsing stores non-secret values in config and refresh token only in dotenv
def test_client_mode_separates_refresh_token(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        login_path = directory / "login.protobuf"
        login_path.write_bytes(b"fixture")
        install_inputs(monkeypatch, ["target.user", "y", "2", "y", str(login_path), "n", "", "n", "y", "n"])
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        monkeypatch.setattr(monitor, "parse_login_request_body_file", lambda path: ("device-id", "system-id", "account-id", "refresh-private-value"))
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=directory / ".env")
        assert error.value.code == 0
        config = (directory / "spotify_monitor.conf").read_text(encoding="utf-8")
        assert 'TOKEN_SOURCE = "client"' in config
        assert 'DEVICE_ID = "device-id"' in config
        assert 'SYSTEM_ID = "system-id"' in config
        assert 'USER_URI_ID = "account-id"' in config
        assert "refresh-private-value" not in config
        assert dotenv_values(directory / ".env", interpolate=False)["REFRESH_TOKEN"] == "refresh-private-value"
        assert "refresh-private-value" not in capsys.readouterr().out


# Verifies disabled email clears every generated notification flag without SMTP access
def test_email_disabled_clears_all_flags(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: False)
    config_values = {name: True for name in ("ACTIVE_NOTIFICATION", "INACTIVE_NOTIFICATION", "TRACK_NOTIFICATION", "SONG_NOTIFICATION", "SONG_ON_LOOP_NOTIFICATION", "ERROR_NOTIFICATION")}
    assert monitor._wizard_collect_email(config_values, {}, Path("unused.env")) == []
    assert not any(config_values.values())


# Verifies the recommended email preset validates locally and queues only the password secret
def test_email_recommended_preset_uses_shared_validation(monkeypatch, tmp_path):
    yes_no = iter([True, True])
    text_values = iter(["smtp.example.com", "user", "sender@example.com", "receiver@example.com"])
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: next(yes_no))
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda *args, **kwargs: next(text_values))
    monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda *args, **kwargs: 587)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda *args, **kwargs: "smtp-private-value")
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: 0)
    connect_mock = Mock(side_effect=AssertionError("SMTP connected"))
    monkeypatch.setattr(monitor, "smtp_connect_and_login", connect_mock)
    config_values = {}
    secrets = {}
    enabled = monitor._wizard_collect_email(config_values, secrets, tmp_path / ".env")
    assert enabled == ["active", "inactive", "errors"]
    assert secrets == {"SMTP_PASSWORD": "smtp-private-value"}
    assert config_values["TRACK_NOTIFICATION"] is False
    assert config_values["SONG_NOTIFICATION"] is False
    assert config_values["SONG_ON_LOOP_NOTIFICATION"] is False
    connect_mock.assert_not_called()


# Verifies all-events and custom presets set each notification flag as selected
@pytest.mark.parametrize("preset,custom_answers,expected", [(1, [], [True, True, True, True, True, True]), (2, [True, False, True, False, True, False], [True, False, True, False, True, False])])
def test_email_all_and_custom_presets(monkeypatch, tmp_path, preset, custom_answers, expected):
    base_answers = [True, True]
    yes_no = iter(base_answers + custom_answers)
    text_values = iter(["smtp.example.com", "user", "sender@example.com", "receiver@example.com"])
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: next(yes_no))
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda *args, **kwargs: next(text_values))
    monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda *args, **kwargs: 587)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda *args, **kwargs: "smtp-private-value")
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: preset)
    config_values = {}
    monitor._wizard_collect_email(config_values, {}, tmp_path / ".env")
    names = ("ACTIVE_NOTIFICATION", "INACTIVE_NOTIFICATION", "TRACK_NOTIFICATION", "SONG_NOTIFICATION", "SONG_ON_LOOP_NOTIFICATION", "ERROR_NOTIFICATION")
    assert [config_values[name] for name in names] == expected


# Verifies an existing cookie can be retained without rewriting the dotenv file
def test_existing_cookie_retention(monkeypatch):
    with make_test_directory() as directory_name:
        env_path = Path(directory_name) / ".env"
        env_path.write_text("# keep\nSP_DC_COOKIE=existing-private-value\n", encoding="utf-8")
        before = env_path.read_bytes()
        install_inputs(monkeypatch, ["2", "y"])
        result = monitor._wizard_collect_cookie_auth("manual", env_path, {})
        assert result["complete"] is True
        assert result["source"] == "existing SP_DC_COOKIE"
        assert env_path.read_bytes() == before


# Verifies declining an existing config destination supports an alternate path
def test_existing_config_decline_uses_alternate_path(monkeypatch):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        existing = directory / "spotify_monitor.conf"
        alternate = directory / "alternate.conf"
        existing.write_text("old\n", encoding="utf-8")
        monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: False)
        monkeypatch.setattr(monitor, "_wizard_ask_text", lambda *args, **kwargs: str(alternate))
        assert monitor._wizard_choose_config_destination(existing) == alternate.resolve()


# Verifies a later dotenv failure reports partial persistence and leaves the config saved
def test_partial_persistence_failure_is_reported(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        config_path = directory / "spotify_monitor.conf"
        auth = {"complete": True, "validated": False, "browser": None, "source": "private manual entry"}
        install_minimal_wizard_flow(monkeypatch, "manual", auth, [True, True])
        monkeypatch.setattr(monitor, "_wizard_collect_cookie_auth", lambda method, env, updates: (updates.update({"SP_DC_COOKIE": "private-value"}) or dict(auth)))
        monkeypatch.setattr(monitor, "update_dotenv_file", Mock(side_effect=OSError("write failed")))
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=config_path, env_file=directory / ".env")
        assert error.value.code == 1
        assert config_path.is_file()
        output = capsys.readouterr().out
        assert "Configuration was saved but dotenv destination" in output
        assert "private-value" not in output


# Verifies a warning-only doctor allows a secret-free local exec boundary
def test_warning_only_doctor_allows_local_start(monkeypatch):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        auth = {"complete": True, "validated": False, "browser": None, "source": "existing SP_DC_COOKIE"}
        report = monitor.DoctorReport(checks=[monitor.DoctorCheck("Environment", "WARN", "Optional warning")])
        install_minimal_wizard_flow(monkeypatch, "manual", auth, [False, True, True, True], report)
        exec_mock = Mock()
        monkeypatch.setattr(monitor.os, "execv", exec_mock)
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=directory / ".env")
        assert error.value.code == 0
        exec_mock.assert_called_once()
        executable, arguments = exec_mock.call_args.args
        assert executable == monitor.sys.executable
        assert "target.user" in arguments
        assert "SP_DC_COOKIE" not in " ".join(arguments)


# Verifies doctor failures block the automatic local start offer
def test_doctor_failure_blocks_local_start(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        auth = {"complete": True, "validated": False, "browser": None, "source": "existing SP_DC_COOKIE"}
        report = monitor.DoctorReport(checks=[monitor.DoctorCheck("Authentication", "FAIL", "Authentication failed")])
        install_minimal_wizard_flow(monkeypatch, "pip", auth, [True, True, True], report)
        exec_mock = Mock()
        monkeypatch.setattr(monitor.os, "execv", exec_mock)
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=directory / ".env")
        assert error.value.code == 0
        exec_mock.assert_not_called()
        assert "saved but is not ready" in capsys.readouterr().out


# Verifies Compose prints up only for complete authentication with a persisted target
def test_compose_ready_setup_prints_up_without_exec(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        auth = {"complete": True, "validated": False, "browser": None, "source": "existing SP_DC_COOKIE"}
        install_minimal_wizard_flow(monkeypatch, "compose", auth, [True, True, False])
        exec_mock = Mock()
        monkeypatch.setattr(monitor.os, "execv", exec_mock)
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=directory / ".env")
        assert error.value.code == 0
        assert "docker compose up" in capsys.readouterr().out
        exec_mock.assert_not_called()


# Verifies advanced client mode can finish incomplete when no Protobuf is available
def test_client_mode_without_protobuf_is_incomplete(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: False)
    result = monitor._wizard_collect_client_auth({}, Path("unused.env"), {})
    assert result["complete"] is False
    assert result["source"] == "advanced client mode without credentials"


# Verifies interactive no-argument welcome launches setup when accepted
def test_interactive_welcome_accepts_setup(monkeypatch):
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: True)
    setup_mock = Mock()
    monkeypatch.setattr(monitor, "run_setup_wizard", setup_mock)
    monitor._wizard_welcome()
    setup_mock.assert_called_once_with()


# Verifies setup rejects noninteractive use before touching destination files
def test_noninteractive_setup_is_rejected(monkeypatch, capsys):
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: False))
    with pytest.raises(SystemExit) as error:
        monitor.run_setup_wizard(config_file="unused.conf", env_file="unused.env")
    assert error.value.code == 1
    assert "interactive terminal" in capsys.readouterr().out
