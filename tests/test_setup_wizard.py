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
COLLECT_WEBHOOK = monitor._wizard_collect_webhook


# Keeps wizard scenarios on deterministic Linux behavior and their original notification channel
@pytest.fixture(autouse=True)
def disable_webhook_collection_by_default(monkeypatch):
    monkeypatch.setattr(monitor.platform, "system", lambda: "Linux")
    monkeypatch.setattr(monitor, "_wizard_collect_webhook", lambda config, secrets, env: [])


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
    monkeypatch.setattr(monitor, "_wizard_offer_target_follow", Mock(return_value="already_followed"))
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
    assert "\nPick\n" in output


# Verifies the first webhook question names Discord and ntfy before the user opts in
def test_webhook_prompt_names_supported_services(monkeypatch):
    questions = []
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=False: (questions.append(question) or False))
    config_values = {}
    assert COLLECT_WEBHOOK(config_values, {}, Path("unused.env")) == []
    assert questions == ["Set up webhook alerts (Discord, ntfy etc.)?"]
    assert config_values["WEBHOOK_ENABLED"] is False


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


# Verifies local cookie setup keeps Firefox import as the recommended default
def test_local_cookie_setup_recommends_browser_import(monkeypatch):
    captured = {}
    monkeypatch.setattr(monitor, "_wizard_import_browsers", lambda method: ["firefox"])

    # Captures the first default choice without prompting
    def choose(question, options, default_index=0):
        captured["question"] = question
        captured["options"] = options
        captured["default_index"] = default_index
        return default_index

    monkeypatch.setattr(monitor, "_wizard_ask_choice", choose)
    result = monitor._wizard_collect_cookie_auth("pip", Path("unused.env"), {})
    assert result["browser"] == "firefox"
    assert captured["default_index"] == 0
    assert captured["options"][0][0] == "Import from Firefox, recommended"
    assert "no additional package" in captured["options"][0][1]


# Verifies supported local environments present Firefox and Chromium as separate paths
@pytest.mark.parametrize("dependency_available,description", [(True, "signed-in Chrome"), (False, "install the required pycookiecheat")])
def test_local_cookie_setup_splits_firefox_and_chromium(monkeypatch, dependency_available, description):
    captured = {}
    monkeypatch.setattr(monitor, "_wizard_import_browsers", lambda method: ["firefox", "chrome", "brave", "chromium"])
    monkeypatch.setattr(monitor, "_wizard_chromium_dependency_available", lambda: dependency_available)
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda question, options, default_index=0: (captured.update({"options": options}) or 0))
    result = monitor._wizard_collect_cookie_auth("manual", Path("unused.env"), {})
    assert result["browser"] == "firefox"
    assert [label for label, _ in captured["options"][:2]] == ["Import from Firefox, recommended", "Import from Chrome, Brave or Chromium"]
    assert description in captured["options"][1][1]


# Verifies missing Chromium support can be installed before choosing the exact browser
def test_chromium_setup_offers_one_step_dependency_install(monkeypatch):
    choices = iter([1, 2])
    availability = Mock(side_effect=[False, False])
    install_mock = Mock(return_value=True)
    monkeypatch.setattr(monitor, "_wizard_import_browsers", lambda method: ["firefox", "chrome", "brave", "chromium"])
    monkeypatch.setattr(monitor, "_wizard_chromium_dependency_available", availability)
    monkeypatch.setattr(monitor, "_wizard_install_chromium_dependency", install_mock)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: True)
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: next(choices))
    result = monitor._wizard_collect_cookie_auth("manual", Path("unused.env"), {})
    assert result["browser"] == "chromium"
    install_mock.assert_called_once_with("manual")


# Verifies dependency installation uses pip from the active Python environment
@pytest.mark.parametrize("method,requirement", [("pip", "spotify_monitor[browser]"), ("manual", "pycookiecheat>=0.8")])
def test_chromium_dependency_install_uses_active_python(monkeypatch, method, requirement):
    run_mock = Mock(return_value=subprocess.CompletedProcess([], 0))
    monkeypatch.setattr(monitor.sys, "executable", "/active/python")
    monkeypatch.setattr(monitor.subprocess, "run", run_mock)
    monkeypatch.setattr(monitor, "_wizard_chromium_dependency_available", lambda: True)
    assert monitor._wizard_install_chromium_dependency(method) is True
    run_mock.assert_called_once_with(["/active/python", "-m", "pip", "install", requirement], check=False)


# Verifies Docker recommends a read-only Firefox host profile mount when no cookie exists
def test_docker_cookie_setup_defaults_to_firefox_import(tmp_path, monkeypatch, capsys):
    captured = {}

    # Selects the displayed default while recording the container choices
    def choose(question, options, default_index=0):
        captured["options"] = options
        return default_index

    monkeypatch.setattr(monitor, "_wizard_ask_choice", choose)
    updates = {}
    result = monitor._wizard_collect_cookie_auth("docker", tmp_path / ".env", updates)
    output = capsys.readouterr().out
    assert captured["options"][0][0] == "Import from Firefox, recommended"
    assert "host Firefox profile mounted read-only" in captured["options"][0][1]
    assert updates == {}
    assert result["complete"] is False
    assert result["mount_required"] is True
    assert result["source"] == "Firefox import pending a read-only host profile mount"
    assert "needs the host profile mounted read-only" in output


# Verifies Docker naturally retains an existing non-placeholder cookie
def test_docker_cookie_setup_defaults_to_existing_cookie(tmp_path, monkeypatch):
    destination = tmp_path / ".env"
    destination.write_text("# keep\nSP_DC_COOKIE=existing-private-value\n", encoding="utf-8")
    original = destination.read_bytes()
    captured = {}

    # Selects the displayed default while recording the container choices
    def choose(question, options, default_index=0):
        captured["options"] = options
        return default_index

    monkeypatch.setattr(monitor, "_wizard_ask_choice", choose)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: True)
    result = monitor._wizard_collect_cookie_auth("compose", destination, {})
    assert captured["options"][0][0] == "Retain the existing SP_DC_COOKIE"
    assert result["complete"] is True
    assert result["source"] == "existing SP_DC_COOKIE"
    assert destination.read_bytes() == original


# Verifies hidden container cookie entry remains available as a private fallback
def test_container_cookie_setup_offers_hidden_manual_fallback(tmp_path, monkeypatch, capsys):
    secret = "PHASE6-DOCKER-SETUP-SECRET"
    captured = {}

    # Selects private entry while recording the displayed choices
    def choose(question, options, default_index=0):
        captured["options"] = options
        return 1

    monkeypatch.setattr(monitor, "_wizard_ask_choice", choose)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: secret)
    updates = {}
    result = monitor._wizard_collect_cookie_auth("docker", tmp_path / ".env", updates)
    assert captured["options"][1][0] == "Enter sp_dc privately"
    assert "hidden getpass prompt" in captured["options"][1][1]
    assert updates == {"SP_DC_COOKIE": secret}
    assert result["source"] == "private manual entry"
    assert secret not in capsys.readouterr().out


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
        install_inputs(monkeypatch, ["spotify:user:target.user", "y", "1", "4", "", "n", "", "n"])
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
        assert "Setup Wizard\n\nThis asks a few questions" in output
        assert "The monitoring account must follow the target. Setup checks this after authentication is saved." in output
        assert "If needed, the tool offers to follow the target. The target must also share listening activity." in output
        assert "Uses exported Protobuf request bodies.\n\nHow should cookie authentication be configured?" in output
        assert "Install method: manual\n\nWhat would you like to do?" in output
        assert "\nSaved files\n\n  Configuration:" in output
        assert "\nNext steps\n\nCheck setup again:" in output
        assert monitor.QUICK_START_GUIDE_URL in output
        assert monitor.FOLLOWING_GUIDE_URL in output
        assert f"Find the sp_dc cookie first: {monitor.MANUAL_COOKIE_GUIDE_URL}" in output
        assert f"  Find the sp_dc cookie first: {monitor.MANUAL_COOKIE_GUIDE_URL}" not in output


# Verifies declining final confirmation leaves both setup destinations unchanged
def test_cancellation_before_confirmation_changes_no_files(monkeypatch):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        config_path = directory / "spotify_monitor.conf"
        env_path = directory / ".env"
        install_inputs(monkeypatch, ["target.user", "y", "1", "5", "", "n", "3", "y"])
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=config_path, env_file=env_path)
        assert error.value.code == 1
        assert not config_path.exists()
        assert not env_path.exists()


# Verifies an edited polling section is reflected in the saved configuration
def test_setup_review_edits_polling_before_save(monkeypatch):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        config_path = directory / "spotify_monitor.conf"
        install_inputs(monkeypatch, ["target.user", "y", "1", "5", "", "n", "2", "3", "45", "", "n"])
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=config_path, env_file=directory / ".env")
        assert error.value.code == 0
        assert "SPOTIFY_CHECK_INTERVAL = 45" in config_path.read_text(encoding="utf-8")


# Verifies a non-persisted target remains absent from config and appears in exact next commands
def test_nonpersisted_target_is_added_to_commands(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        install_inputs(monkeypatch, ["https://open.spotify.com/user/target.user", "n", "1", "3", "", "n", "", "n"])
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "compose")
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=directory / ".env")
        assert error.value.code == 0
        config = (directory / "spotify_monitor.conf").read_text(encoding="utf-8")
        assert 'TARGET_USER_URI_ID = ""' in config
        output = capsys.readouterr().out
        assert "docker compose up --no-log-prefix requires a persisted target" in output
        assert "--doctor target.user" in output
        assert "spotify_monitor target.user --config-file" in output


# Verifies successful browser import receives the selected dotenv path and enables local launch eligibility
def test_browser_import_reuses_phase2_runner(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        env_path = directory / ".env"
        install_inputs(monkeypatch, ["target.user", "y", "1", "1", "", "n", "", "n", "n"])
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        monkeypatch.setattr(monitor.platform, "system", lambda: "Darwin")

        # Prints representative import guidance before saving one private test cookie
        def import_cookie(**kwargs):
            print("* Browser prerequisite: test guidance")
            return monitor.update_dotenv_file(kwargs["env_file"], {"SP_DC_COOKIE": "browser-private-value"})

        import_mock = Mock(side_effect=import_cookie)
        monkeypatch.setattr(monitor, "run_browser_cookie_import", import_mock)
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=env_path)
        assert error.value.code == 0
        assert import_mock.call_args.kwargs["env_file"] == str(env_path.resolve())
        assert import_mock.call_args.kwargs["browser"] == "firefox"
        output = capsys.readouterr().out
        assert monitor.SPOTIFY_WEB_LOGIN_URL in output
        assert f"  Configuration: {(directory / 'spotify_monitor.conf').resolve()}\n\n* Browser prerequisite: test guidance" in output
        assert "browser-private-value" not in output


# Verifies browser import failure can finish setup without discarding the generated config
def test_browser_import_failure_allows_incomplete_recovery(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        install_inputs(monkeypatch, ["target.user", "y", "1", "1", "", "n", "", "3", "n"])
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
        install_inputs(monkeypatch, ["4", "n"])
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
        install_inputs(monkeypatch, ["target.user", "y", "2", "y", str(login_path), "n", "", "n", "", "n"])
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
    questions = []
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, **kwargs: (questions.append(question) or next(yes_no)))
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
    assert questions == ["Configure email notifications?", "Enable TLS/SSL for SMTP?"]


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
        install_inputs(monkeypatch, ["3", "y"])
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


# Verifies setup review can edit one section then save without recollecting other sections
def test_setup_review_edits_one_section_then_saves(monkeypatch, tmp_path):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "spotify_monitor.conf", tmp_path / ".env", baseline, dict(baseline), {}, "old.user", True, {"complete": True, "source": "existing SP_DC_COOKIE"}, [], [])
    choices = iter([1, 0])
    edit_mock = Mock(side_effect=lambda selected, method: setattr(selected, "target", "new.user"))
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: next(choices))
    monkeypatch.setattr(monitor, "_wizard_edit_setup_section", edit_mock)
    assert monitor._wizard_review_setup(state, "manual") is True
    assert state.target == "new.user"
    edit_mock.assert_called_once_with(state, "manual")


# Verifies discard requires confirmation and a declined discard retains every answer
def test_setup_review_requires_confirmed_discard(monkeypatch, tmp_path):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "spotify_monitor.conf", tmp_path / ".env", baseline, dict(baseline), {}, "target.user", True, {"complete": True, "source": "existing SP_DC_COOKIE"}, [], [])
    choices = iter([2, 0])
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: next(choices))
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: False)
    assert monitor._wizard_review_setup(state, "manual") is True
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: 2)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: True)
    assert monitor._wizard_review_setup(state, "manual") is False


# Verifies all editable setup sections are offered and target edits update persisted state
def test_setup_edit_menu_offers_every_section(monkeypatch, tmp_path):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "spotify_monitor.conf", tmp_path / ".env", baseline, dict(baseline), {}, "old.user", True, {"complete": True, "source": "existing SP_DC_COOKIE"}, [], [])
    captured = {}
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda question, options, default_index=0: (captured.update({"question": question, "options": options}) or 0))
    monkeypatch.setattr(monitor, "_wizard_target", lambda initial=None: "new.user")
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: False)
    monitor._wizard_edit_setup_section(state, "manual")
    assert [label for label, _ in captured["options"]] == ["Target and persistence", "Authentication", "Polling interval", "Email notifications", "Webhook alerts", "File destinations", "Return to summary"]
    assert state.target == "new.user"
    assert state.config_values["TARGET_USER_URI_ID"] == ""


# Verifies each non-target edit choice invokes only its matching section collector
@pytest.mark.parametrize("section,function_name,with_method", [(1, "_wizard_collect_auth_section", True), (2, "_wizard_collect_polling_section", False), (3, "_wizard_collect_email_section", False), (4, "_wizard_collect_webhook_section", False), (5, "_wizard_collect_destination_section", True)])
def test_setup_edit_routes_to_selected_section(monkeypatch, tmp_path, section, function_name, with_method):
    baseline = dict(vars(monitor))
    state = monitor.WizardSetupState(tmp_path / "spotify_monitor.conf", tmp_path / ".env", baseline, dict(baseline), {}, "target.user", True, {"complete": True, "source": "existing SP_DC_COOKIE"}, [], [])
    collector = Mock()
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: section)
    monkeypatch.setattr(monitor, function_name, collector)
    monitor._wizard_edit_setup_section(state, "manual")
    expected = (state, "manual") if with_method else (state,)
    collector.assert_called_once_with(*expected)


# Verifies changing the dotenv destination recollects every secret-dependent section
def test_destination_edit_recollects_secret_sections(monkeypatch, tmp_path):
    baseline = dict(vars(monitor))
    old_env = tmp_path / "old.env"
    new_env = tmp_path / "new.env"
    state = monitor.WizardSetupState(tmp_path / "spotify_monitor.conf", old_env, baseline, dict(baseline), {"SP_DC_COOKIE": "private"}, "target.user", True, {"complete": True, "source": "private manual entry"}, [], [])
    text_answers = iter([str(state.config_path), str(new_env)])
    auth_mock = Mock()
    email_mock = Mock()
    webhook_mock = Mock()
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda *args, **kwargs: next(text_answers))
    monkeypatch.setattr(monitor, "_wizard_collect_auth_section", auth_mock)
    monkeypatch.setattr(monitor, "_wizard_collect_email_section", email_mock)
    monkeypatch.setattr(monitor, "_wizard_collect_webhook_section", webhook_mock)
    monitor._wizard_collect_destination_section(state, "manual")
    assert state.env_path == new_env.resolve()
    auth_mock.assert_called_once_with(state, "manual")
    email_mock.assert_called_once_with(state)
    webhook_mock.assert_called_once_with(state)


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


# Verifies Windows monitoring launch preserves every spaced path as one subprocess argument
def test_windows_launch_uses_argument_sequence(monkeypatch):
    arguments = [r"C:\Python Tools\python.exe", r"C:\Project Space\spotify_monitor.py", "--config-file", r"C:\Project Space\spotify_monitor.conf"]
    result = subprocess.CompletedProcess(arguments, 7)
    run_mock = Mock(return_value=result)
    monkeypatch.setattr(monitor.platform, "system", lambda: "Windows")
    monkeypatch.setattr(monitor.subprocess, "run", run_mock)
    assert monitor._wizard_launch_monitor(arguments) == 7
    run_mock.assert_called_once_with(arguments, check=False)


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


# Verifies Compose prints prefix-free up only for complete authentication with a persisted target
def test_compose_ready_setup_prints_up_without_exec(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        auth = {"complete": True, "validated": False, "browser": None, "source": "existing SP_DC_COOKIE"}
        install_minimal_wizard_flow(monkeypatch, "compose", auth, [True, False])
        exec_mock = Mock()
        monkeypatch.setattr(monitor.os, "execv", exec_mock)
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=directory / "spotify_monitor.conf", env_file=directory / ".env")
        assert error.value.code == 0
        assert "docker compose up --no-log-prefix" in capsys.readouterr().out
        exec_mock.assert_not_called()


# Verifies advanced client mode can finish incomplete when no Protobuf is available
def test_client_mode_without_protobuf_is_incomplete(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: False)
    result = monitor._wizard_collect_client_auth({}, Path("unused.env"), {})
    assert result["complete"] is False
    assert result["source"] == "advanced client mode without credentials"


# Verifies setup reports an existing follow without offering an account mutation
def test_setup_follow_check_reports_already_followed(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "doctor_check_authentication", lambda report: (setattr(report, "access_token", "authenticated-token") or []))
    monkeypatch.setattr(monitor, "spotify_user_is_followed", Mock(return_value=True))
    follow = Mock()
    ask = Mock()
    monkeypatch.setattr(monitor, "spotify_follow_user", follow)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", ask)
    assert monitor._wizard_offer_target_follow("target.user") == "already_followed"
    follow.assert_not_called()
    ask.assert_not_called()
    output = capsys.readouterr().out
    assert "\nThe monitoring account already follows 'target.user'.\n" in output
    assert "\n  The monitoring account" not in output


# Verifies declining the follow prompt leaves the Spotify account unchanged
def test_setup_follow_check_respects_declined_confirmation(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "doctor_check_authentication", lambda report: (setattr(report, "access_token", "authenticated-token") or []))
    monkeypatch.setattr(monitor, "spotify_user_is_followed", Mock(return_value=False))
    follow = Mock()
    ask = Mock(return_value=False)
    monkeypatch.setattr(monitor, "spotify_follow_user", follow)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", ask)
    assert monitor._wizard_offer_target_follow("target.user") == "declined"
    ask.assert_called_once_with("Follow 'target.user' now using the configured Spotify account?", default=False)
    follow.assert_not_called()
    output = capsys.readouterr().out
    assert "\nThe monitoring account does not follow 'target.user'.\n\n" in output
    assert "\n  The monitoring account" not in output
    assert "\nFollow skipped. Spotify Monitor will not change the account.\n" in output
    assert "\n  Follow" not in output


# Verifies an approved follow is rechecked before setup reports success
def test_setup_follow_check_verifies_approved_mutation(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "doctor_check_authentication", lambda report: (setattr(report, "access_token", "authenticated-token") or []))
    check = Mock(side_effect=[False, True])
    follow = Mock(return_value=True)
    monkeypatch.setattr(monitor, "spotify_user_is_followed", check)
    monkeypatch.setattr(monitor, "spotify_follow_user", follow)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", Mock(return_value=True))
    assert monitor._wizard_offer_target_follow("target.user") == "followed"
    follow.assert_called_once_with("authenticated-token", "target.user")
    assert check.call_count == 2
    output = capsys.readouterr().out
    assert "\nFollow verified. The monitoring account now follows 'target.user'.\n" in output
    assert "\n  Follow" not in output


# Verifies setup does not claim success when the post-mutation follow check stays false
def test_setup_follow_check_rejects_unverified_mutation(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "doctor_check_authentication", lambda report: (setattr(report, "access_token", "authenticated-token") or []))
    monkeypatch.setattr(monitor, "spotify_user_is_followed", Mock(side_effect=[False, False]))
    monkeypatch.setattr(monitor, "spotify_follow_user", Mock(return_value=True))
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", Mock(return_value=True))
    assert monitor._wizard_offer_target_follow("target.user") == "follow_failed"
    output = capsys.readouterr().out
    assert "\nSpotify accepted the follow request but verification still reports not followed.\n" in output
    assert "\nThe account was not verified as following the target.\n" in output
    assert "\n  Spotify" not in output
    assert "\n  The account" not in output


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
    output = capsys.readouterr().out
    assert "interactive terminal" in output
    assert monitor.QUICK_START_GUIDE_URL in output
