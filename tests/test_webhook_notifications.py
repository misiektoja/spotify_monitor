import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
from dotenv import dotenv_values

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "webhook_test_artifacts"


# Creates one disposable webhook test directory under the project local directory
def make_test_directory():
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT)


# Stores one fake webhook response with optional rate-limit metadata
class FakeResponse:
    # Initializes one response value used by the isolated transport tests
    def __init__(self, status_code=204, text="", headers=None, payload=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}
        self.payload = payload

    # Returns the configured JSON payload or raises when none was provided
    def json(self):
        if self.payload is None:
            raise ValueError("no JSON payload")
        return self.payload


# Enables one valid test webhook without affecting email settings
def configure_webhook(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123/private-token")
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_SONG_NOTIFICATION", True)


# Verifies webhook URLs require complete HTTPS endpoints without embedded credentials
@pytest.mark.parametrize("url,expected", [("https://discord.com/api/webhooks/123/token", True), ("https://hooks.example.test/discord/path", True), ("http://discord.com/api/webhooks/123/token", False), ("https://user:password@example.test/hook", False), ("https://example.test", False), ("not-a-url", False), ("", False)])
def test_webhook_url_validation(url, expected):
    assert monitor.validate_webhook_url(url) is expected


# Verifies private webhook entry requires a TTY and a writable dotenv destination
def test_set_webhook_url_requires_safe_persistence():
    with pytest.raises(monitor.WebhookConfigurationError, match="interactive terminal"):
        monitor.run_set_webhook_url(interactive=False, getpass_func=Mock(side_effect=AssertionError("prompted")))
    with pytest.raises(monitor.WebhookConfigurationError, match="requires a dotenv destination"):
        monitor.run_set_webhook_url(env_file="none", interactive=True, getpass_func=Mock(side_effect=AssertionError("prompted")))


# Verifies private setup persists only the webhook key after confirmation
def test_set_webhook_url_updates_only_secret(monkeypatch):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        destination.write_text("# keep\nUNRELATED=stay\nWEBHOOK_URL=old-value\n", encoding="utf-8")
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")
        monkeypatch.setattr(monitor, "find_config_file", lambda: None)
        result = monitor.run_set_webhook_url(env_file=destination, interactive=True, input_func=lambda prompt: "y", getpass_func=lambda prompt: "https://discord.com/api/webhooks/123/new-private-token")
        assert result == str(destination.resolve())
        assert destination.read_text(encoding="utf-8").startswith("# keep\nUNRELATED=stay\n")
        assert dotenv_values(destination, interpolate=False) == {"UNRELATED": "stay", "WEBHOOK_URL": "https://discord.com/api/webhooks/123/new-private-token"}


# Verifies rejected private setup never writes or displays the entered URL
def test_set_webhook_url_rejects_invalid_secret_without_leak(capsys):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        secret = "http://example.test/private-token"
        with pytest.raises(monitor.WebhookConfigurationError, match="complete HTTPS") as error:
            monitor.run_set_webhook_url(env_file=destination, interactive=True, getpass_func=lambda prompt: secret)
        output = capsys.readouterr().out
        assert secret not in output
        assert secret not in str(error.value)
        assert not destination.exists()


# Verifies successful container setup prints install-aware commands without the secret
def test_set_webhook_url_uses_compose_commands_without_leak(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        destination = directory / ".env"
        config_path = directory / "spotify_monitor.conf"
        secret = "https://discord.com/api/webhooks/123/private-token"
        monkeypatch.chdir(directory)
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "compose")
        monitor.run_set_webhook_url(env_file=destination, interactive=True, getpass_func=lambda prompt: secret, config_path=config_path)
        output = capsys.readouterr().out
        assert "docker compose run --rm spotify_monitor --send-test-webhook --config-file /data/spotify_monitor.conf --env-file /data/.env" in output
        assert "docker compose run --rm spotify_monitor --doctor --config-file /data/spotify_monitor.conf --env-file /data/.env" in output
        assert secret not in output


# Verifies Discord payloads are bounded, mention-safe and secret-redacted
def test_webhook_payload_is_bounded_and_safe(monkeypatch):
    secret = "https://discord.com/api/webhooks/123/private-token"
    monkeypatch.setattr(monitor, "WEBHOOK_URL", secret)
    payload = monitor.build_webhook_payload("@everyone " + ("t" * 300), f"failed at {secret} @here", "error")
    embed = payload["embeds"][0]
    assert len(embed["title"]) == monitor.WEBHOOK_EMBED_TITLE_LIMIT
    assert secret not in embed["description"]
    assert payload["allowed_mentions"] == {"parse": []}
    assert embed["color"] == 0xE74C3C


# Verifies one successful webhook uses the isolated session with no Spotify adapter calls
def test_successful_webhook_uses_isolated_session(monkeypatch):
    configure_webhook(monkeypatch)
    webhook_post = Mock(return_value=FakeResponse())
    spotify_post = Mock(side_effect=AssertionError("Spotify session used"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    monkeypatch.setattr(monitor.SESSION, "post", spotify_post)
    assert monitor.send_webhook("Title", "Body", "song") == 0
    assert webhook_post.call_count == 1
    assert webhook_post.call_args.kwargs["timeout"] == monitor.WEBHOOK_TIMEOUT_SECONDS
    spotify_post.assert_not_called()


# Verifies ntfy receives a native UTF-8 topic message with its title in query parameters
def test_successful_ntfy_webhook_uses_native_topic_api(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.sh/private-topic?auth=private-auth-value")
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Spotify title za\u017c\u00f3\u0142\u0107", "Playing: Bj\u00f6rk", "song") == 0
    request = webhook_post.call_args
    assert request.args == ("https://ntfy.sh/private-topic?auth=private-auth-value",)
    assert request.kwargs["data"] == "Playing: Bj\u00f6rk".encode("utf-8")
    assert request.kwargs["params"] == {"title": "Spotify title za\u017c\u00f3\u0142\u0107"}
    assert request.kwargs["headers"]["Content-Type"] == "text/plain; charset=utf-8"
    assert "json" not in request.kwargs


# Verifies ntfy message truncation respects its UTF-8 byte limit without splitting a character
def test_ntfy_message_is_bounded_by_utf8_bytes():
    title, message = monitor.build_ntfy_webhook_message("Title", ("a" * (monitor.NTFY_MESSAGE_LIMIT_BYTES - 1)) + "\U0001f3b5")
    assert title == "Title"
    assert len(message.encode("utf-8")) == monitor.NTFY_MESSAGE_LIMIT_BYTES - 1
    assert not message.endswith("\U0001f3b5")


# Verifies unsupported webhook providers fail before any request is attempted
def test_invalid_webhook_provider_is_rejected(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "unsupported")
    webhook_post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song") == 1
    webhook_post.assert_not_called()


# Verifies an aggressive Retry-After value is capped and retried only once
def test_webhook_429_timer_is_capped_and_bounded(monkeypatch):
    configure_webhook(monkeypatch)
    responses = [FakeResponse(429, "slow down", {"Retry-After": "7200"}), FakeResponse(204)]
    post = Mock(side_effect=responses)
    sleeps = []
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
    assert monitor.send_webhook("Title", "Body", "song", sleeper=sleeps.append) == 0
    assert post.call_count == monitor.WEBHOOK_MAX_ATTEMPTS == 2
    assert sleeps == [monitor.WEBHOOK_MAX_RETRY_AFTER_SECONDS]


# Verifies client errors fail immediately while server errors receive one short retry
@pytest.mark.parametrize("statuses,expected_calls,expected_sleeps", [([404], 1, []), ([503, 503], 2, [monitor.WEBHOOK_FALLBACK_RETRY_SECONDS])])
def test_webhook_http_retry_boundaries(monkeypatch, statuses, expected_calls, expected_sleeps):
    configure_webhook(monkeypatch)
    post = Mock(side_effect=[FakeResponse(status, "failure") for status in statuses])
    sleeps = []
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
    assert monitor.send_webhook("Title", "Body", "song", sleeper=sleeps.append) == 1
    assert post.call_count == expected_calls
    assert sleeps == expected_sleeps


# Verifies email and webhook attempts remain independent in both directions
def test_notification_channels_are_independent(monkeypatch):
    email = Mock(return_value=0)
    webhook = Mock(return_value=0)
    monkeypatch.setattr(monitor, "send_email", email)
    monkeypatch.setattr(monitor, "send_webhook", webhook)
    assert monitor.send_notification_channels("song", "Title", "Body", email_enabled=True, webhook_enabled=False) == (True, False)
    email.assert_called_once()
    webhook.assert_not_called()
    email.reset_mock()
    assert monitor.send_notification_channels("song", "Title", "Body", email_enabled=False, webhook_enabled=True) == (False, True)
    email.assert_not_called()
    webhook.assert_called_once_with("Title", "Body", "song", force=True)


# Verifies the recommended wizard preset stores the URL privately without contacting it
def test_webhook_wizard_preset_is_hidden_and_offline(monkeypatch):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        post = Mock(side_effect=AssertionError("webhook request attempted"))
        monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: True)
        monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda *args, **kwargs: "https://discord.com/api/webhooks/123/private-token")
        monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: 0)
        monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
        config_values = {}
        secret_updates = {}
        enabled = monitor._wizard_collect_webhook(config_values, secret_updates, destination)
        assert enabled == ["active", "inactive", "errors"]
        assert secret_updates == {"WEBHOOK_URL": "https://discord.com/api/webhooks/123/private-token"}
        assert config_values["WEBHOOK_ENABLED"] is True
        assert config_values["WEBHOOK_PROVIDER"] == "discord"
        assert config_values["WEBHOOK_TRACK_NOTIFICATION"] is False
        assert config_values["WEBHOOK_SONG_NOTIFICATION"] is False
        assert config_values["WEBHOOK_SONG_ON_LOOP_NOTIFICATION"] is False
        post.assert_not_called()


# Verifies the wizard stores an ntfy topic URL and provider without contacting the service
def test_webhook_wizard_supports_ntfy(monkeypatch):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        choices = iter([1, 0])
        post = Mock(side_effect=AssertionError("webhook request attempted"))
        monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: True)
        secrets = iter(["https://ntfy.sh/private-topic", "my-access-token"])
        monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda *args, **kwargs: next(secrets))
        monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: next(choices))
        monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
        config_values = {}
        secret_updates = {}
        enabled = monitor._wizard_collect_webhook(config_values, secret_updates, destination)
        assert enabled == ["active", "inactive", "errors"]
        assert secret_updates == {
            "WEBHOOK_URL": "https://ntfy.sh/private-topic",
            "NTFY_ACCESS_TOKEN": "my-access-token",
        }
        assert config_values["WEBHOOK_ENABLED"] is True
        assert config_values["WEBHOOK_PROVIDER"] == "ntfy"
        post.assert_not_called()


# Verifies full setup persists webhook settings in config and the secret only in dotenv
def test_setup_wizard_persists_webhook_channel(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        config_path = directory / "spotify_monitor.conf"
        env_path = directory / ".env"
        secret = "https://discord.com/api/webhooks/123/private-token"
        answers = iter([True, False, True, True, False])
        monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        monkeypatch.setattr(monitor, "_wizard_target", lambda initial=None: "target.user")
        monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: next(answers))
        monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: 0)
        monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda *args, **kwargs: 30)
        monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda *args, **kwargs: secret)
        monkeypatch.setattr(monitor, "_wizard_collect_cookie_auth", lambda *args, **kwargs: {"complete": False, "validated": False, "browser": None, "source": "not configured", "mount_required": False})
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=config_path, env_file=env_path)
        assert error.value.code == 0
        config = config_path.read_text(encoding="utf-8")
        assert "WEBHOOK_ENABLED = True" in config
        assert 'WEBHOOK_PROVIDER = "discord"' in config
        assert "WEBHOOK_ACTIVE_NOTIFICATION = True" in config
        assert "WEBHOOK_INACTIVE_NOTIFICATION = True" in config
        assert "WEBHOOK_ERROR_NOTIFICATION = True" in config
        assert secret not in config
        assert dotenv_values(env_path, interpolate=False)["WEBHOOK_URL"] == secret
        assert secret not in capsys.readouterr().out


# Verifies the standalone test action skips every Spotify connectivity path
def test_send_test_webhook_cli_is_spotify_independent(monkeypatch):
    delivery = Mock(return_value=0)
    connectivity = Mock(side_effect=AssertionError("Spotify connectivity check attempted"))
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--send-test-webhook", "--env-file", "none"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "clear_screen", Mock())
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "send_webhook", delivery)
    monkeypatch.setattr(monitor, "check_internet", connectivity)
    with pytest.raises(SystemExit) as error:
        monitor.main()
    assert error.value.code == 0
    delivery.assert_called_once()
    connectivity.assert_not_called()


# Verifies the doctor checks webhook settings without sending a message
def test_doctor_webhook_check_is_read_only(monkeypatch):
    configure_webhook(monkeypatch)
    post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
    checks = monitor.doctor_check_webhook_notifications()
    assert checks == [monitor.make_doctor_check("Notifications", "PASS", "Webhook URL and alert choices look valid", "The private link was not displayed and no webhook was sent")]
    post.assert_not_called()


# Verifies doctor rejects an unsupported provider without sending a message
def test_doctor_rejects_invalid_webhook_provider(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "unsupported")
    post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
    checks = monitor.doctor_check_webhook_notifications()
    assert checks[0].status == "FAIL"
    assert "WEBHOOK_PROVIDER must be discord or ntfy" in checks[0].detail
    post.assert_not_called()


# Verifies Spotify and webhook retry caps remain deliberately separate
def test_spotify_retry_cap_is_unchanged_and_separate():
    assert monitor.MAX_RETRY_AFTER_SECONDS == 60
    assert monitor.WEBHOOK_MAX_RETRY_AFTER_SECONDS == 5.0
    assert monitor.retry.total == 5
    webhook_adapter = monitor.WEBHOOK_SESSION.adapters["https://"]
    assert isinstance(webhook_adapter, monitor.HTTPAdapter)
    assert webhook_adapter.max_retries.total == 0
