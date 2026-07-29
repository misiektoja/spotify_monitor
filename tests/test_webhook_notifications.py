import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from dotenv import dotenv_values
from PIL import Image

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


# Stores one requests-compatible streaming response for image download tests
class FakeDownloadResponse:
    # Initializes one streamed response from fixed bytes and headers
    def __init__(self, content, headers=None, status_code=200):
        self.content = content
        self.headers = headers or {"Content-Type": "image/png", "Content-Length": str(len(content))}
        self.status_code = status_code

    # Returns this response when entering its context manager
    def __enter__(self):
        return self

    # Leaves the response context without suppressing exceptions
    def __exit__(self, exc_type, exc_value, traceback):
        return False

    # Raises a requests error for unsuccessful status codes
    def raise_for_status(self):
        if self.status_code >= 400:
            raise monitor.req.HTTPError(f"HTTP {self.status_code}")

    # Yields the stored response body in requested chunk sizes
    def iter_content(self, chunk_size):
        for offset in range(0, len(self.content), chunk_size):
            yield self.content[offset:offset + chunk_size]


# Enables one valid test webhook without affecting email settings
def configure_webhook(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123/private-token")
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_USERNAME", "Spotify Monitor")
    monkeypatch.setattr(monitor, "WEBHOOK_AVATAR_URL", "")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {})
    monkeypatch.setattr(monitor, "WEBHOOK_TRANSFORMS", [])
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "")
    monkeypatch.setattr(monitor, "NTFY_IMAGES", False)
    monkeypatch.setattr(monitor, "NTFY_SHORT", False)
    monkeypatch.setattr(monitor, "WEBHOOK_SONG_NOTIFICATION", True)


# Verifies webhook URLs require complete HTTPS endpoints without embedded credentials
@pytest.mark.parametrize("url,expected", [("https://discord.com/api/webhooks/123/token", True), ("https://hooks.example.test/discord/path", True), ("http://discord.com/api/webhooks/123/token", False), ("https://user:password@example.test/hook", False), ("https://example.test", False), ("not-a-url", False), ("", False)])
def test_webhook_url_validation(url, expected):
    assert monitor.validate_webhook_url(url) is expected


@pytest.mark.parametrize("url,expected", [("https://discord.com/api/webhooks/123/token", "discord"), ("https://canary.discord.com/api/v10/webhooks/123/token", "discord"), ("https://ntfy.sh/private-topic", "ntfy"), ("https://ntfy.example.test/private-topic", ""), ("https://example.test/custom-hook", "")])
# Verifies distinctive Discord and public ntfy URLs select the proper payload provider
def test_webhook_provider_detection(url, expected):
    assert monitor.detect_webhook_provider(url) == expected


# Verifies SIGHUP adopts rotated client credentials, clears auth caches and redetects ntfy
def test_sighup_reload_clears_auth_caches_and_updates_webhook_provider(monkeypatch):
    if not hasattr(monitor.signal, "SIGHUP"):
        pytest.skip("SIGHUP is unavailable on Windows")
    replacements = {"REFRESH_TOKEN": "new-refresh-token", "WEBHOOK_URL": "https://ntfy.sh/new-private-topic"}
    monkeypatch.setattr(monitor, "DOTENV_FILE", "test.env")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "client")
    monkeypatch.setattr(monitor, "LOGIN_REQUEST_BODY_FILE", "")
    monkeypatch.setattr(monitor, "CLIENTTOKEN_REQUEST_BODY_FILE", "")
    monkeypatch.setattr(monitor, "REFRESH_TOKEN", "old-refresh-token")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://discord.com/api/webhooks/123/old-token")
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "SP_CACHED_ACCESS_TOKEN", "cached-access")
    monkeypatch.setattr(monitor, "SP_CACHED_REFRESH_TOKEN", "cached-refresh")
    monkeypatch.setattr(monitor, "SP_ACCESS_TOKEN_EXPIRES_AT", 999)
    monkeypatch.setattr(monitor, "SP_CACHED_CLIENT_ID", "cached-client-id")
    monkeypatch.setattr(monitor, "SP_CACHED_OAUTH_APP_TOKEN", "cached-oauth")
    monkeypatch.setattr(monitor, "SP_CACHED_CLIENT_TOKEN", "cached-client-token")
    monkeypatch.setattr(monitor, "SP_CLIENT_TOKEN_EXPIRES_AT", 999)
    monkeypatch.setattr(monitor, "SP_CACHED_SCROBBLE_ACCESS_TOKEN", "cached-scrobble-token")
    monkeypatch.setattr(monitor, "SP_SCROBBLE_ACCESS_TOKEN_EXPIRES_AT", 999)
    monkeypatch.setattr(monitor, "SP_CACHED_SCROBBLE_AUTH_FINGERPRINT", "cached-scrobble-auth")
    with patch("dotenv.load_dotenv"), patch.object(monitor.os, "getenv", side_effect=replacements.get):
        monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)
    assert monitor.REFRESH_TOKEN == "new-refresh-token"
    assert monitor.WEBHOOK_PROVIDER == "ntfy"
    assert monitor.SP_CACHED_ACCESS_TOKEN is None
    assert monitor.SP_CACHED_REFRESH_TOKEN is None
    assert monitor.SP_ACCESS_TOKEN_EXPIRES_AT == 0
    assert monitor.SP_CACHED_CLIENT_ID == ""
    assert monitor.SP_CACHED_OAUTH_APP_TOKEN is None
    assert monitor.SP_CACHED_CLIENT_TOKEN is None
    assert monitor.SP_CLIENT_TOKEN_EXPIRES_AT == 0
    assert monitor.SP_CACHED_SCROBBLE_ACCESS_TOKEN is None
    assert monitor.SP_SCROBBLE_ACCESS_TOKEN_EXPIRES_AT == 0
    assert monitor.SP_CACHED_SCROBBLE_AUTH_FINGERPRINT == ""


# Verifies ntfy input normalization preserves HTTPS URLs and expands only valid bare topics
@pytest.mark.parametrize("value,expected", [("https://ntfy.example.test/private-topic?auth=value", "https://ntfy.example.test/private-topic?auth=value"), (" private_Topic-123 ", "https://ntfy.sh/private_Topic-123"), ("a" * 64, f"https://ntfy.sh/{'a' * 64}"), ("a" * 65, ""), ("ntfy.sh/private-topic", ""), ("http://ntfy.sh/private-topic", ""), ("private.topic", ""), ("private/topic", ""), (None, "")])
def test_ntfy_topic_url_normalization(value, expected):
    assert monitor.normalize_ntfy_topic_url(value) == expected


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


# Verifies custom templates, avatars, transformations and header placeholders share sanitized values
def test_advanced_webhook_customization_matches_instagram_features(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_AVATAR_URL", "https://cdn.example.test/avatar.png")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"X-Webhook-Title": "{title}", "X-Webhook-Version": "{version}"})
    monkeypatch.setattr(monitor, "WEBHOOK_TEMPLATE", {"content": "{title}: {description}", "avatar_url": "{avatar_url}", "color": "{color}", "allowed_mentions": {"parse": ["everyone"]}})
    monkeypatch.setattr(monitor, "WEBHOOK_TRANSFORMS", [("title", "replace", "secret", "masked"), ("description", "upper")])
    webhook_post = Mock(return_value=FakeResponse())
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("secret title", "custom body", "song") == 0
    request = webhook_post.call_args
    assert request.kwargs["json"] == {"content": "masked title: CUSTOM BODY", "avatar_url": "https://cdn.example.test/avatar.png", "color": 0x3498DB, "allowed_mentions": {"parse": []}}
    assert request.kwargs["headers"]["X-Webhook-Title"] == "masked title"
    assert request.kwargs["headers"]["X-Webhook-Version"] == monitor.VERSION


# Verifies a string webhook template is delivered as a raw request body
def test_string_webhook_template_uses_raw_body(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_TEMPLATE", "{title}: {description}")
    webhook_post = Mock(return_value=FakeResponse())
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song") == 0
    assert webhook_post.call_args.kwargs["data"] == "Title: Body"
    assert "json" not in webhook_post.call_args.kwargs


# Verifies formatted headers are validated again before network delivery
def test_formatted_webhook_headers_reject_injected_line_breaks(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"X-Description": "{description}"})
    webhook_post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "first\nsecond", "song") == 1
    webhook_post.assert_not_called()


# Verifies generated configuration includes advanced defaults and current non-secret settings
def test_generated_config_includes_advanced_webhook_settings(monkeypatch):
    monkeypatch.setattr(monitor, "WEBHOOK_AVATAR_URL", "https://cdn.example.test/avatar.png")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"Authorization": "Bearer private-header"})
    monkeypatch.setattr(monitor, "WEBHOOK_TEMPLATE", {"content": "private-template"})
    monkeypatch.setattr(monitor, "WEBHOOK_TRANSFORMS", [("title", "upper")])
    monkeypatch.setattr(monitor, "NTFY_SHORT", True)
    rendered = monitor.generate_config_with_current_values()
    namespace = {}
    exec(rendered, namespace)
    assert namespace["WEBHOOK_AVATAR_URL"] == "https://cdn.example.test/avatar.png"
    assert namespace["WEBHOOK_HEADERS"] == {}
    assert namespace["WEBHOOK_TEMPLATE"]["allowed_mentions"] == {"parse": []}
    assert namespace["WEBHOOK_TRANSFORMS"] == [("title", "upper")]
    assert namespace["NTFY_SHORT"] is True
    assert "private-header" not in rendered
    assert "private-template" not in rendered


# Verifies debug mode retains sanitized HTTP diagnostics for troubleshooting
def test_debug_mode_keeps_http_diagnostics(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monitor.debug_print("HTTP GET https://example.test/path -> 200")
    assert "HTTP GET https://example.test/path -> 200" in capsys.readouterr().out


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


# Verifies Instagram-style static headers are copied to webhook requests
def test_custom_webhook_headers_match_instagram_monitor_configuration(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"Authorization": "Basic shared-private-value", "X-Monitor": "spotify"})
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song") == 0
    headers = webhook_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Basic shared-private-value"
    assert headers["X-Monitor"] == "spotify"
    assert headers["User-Agent"] == f"SpotifyMonitor/{monitor.VERSION}"
    assert headers["Content-Type"] == "text/plain; charset=utf-8"


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


# Verifies ntfy cover art is downloaded with bounds and converted entirely in memory
def test_ntfy_image_is_bounded_and_built_in_memory(monkeypatch):
    source = BytesIO()
    Image.new("RGB", (320, 640), (12, 34, 56)).save(source, format="PNG")
    image_get = Mock(return_value=FakeDownloadResponse(source.getvalue()))
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "get", image_get)
    result = monitor.build_ntfy_image("https://i.scdn.co/image/cover.png")
    assert isinstance(result, bytes)
    with Image.open(BytesIO(result)) as output:
        assert output.format == "JPEG"
        assert output.size == (400, 160)
    request = image_get.call_args
    assert request.args == ("https://i.scdn.co/image/cover.png",)
    assert request.kwargs["stream"] is True
    assert request.kwargs["allow_redirects"] is False
    assert request.kwargs["timeout"] == monitor.WEBHOOK_TIMEOUT_SECONDS


# Verifies declared oversized ntfy images are rejected before their body is read
def test_ntfy_image_rejects_oversized_download(monkeypatch):
    response = FakeDownloadResponse(b"ignored", headers={"Content-Type": "image/jpeg", "Content-Length": str(monitor.NTFY_IMAGE_DOWNLOAD_LIMIT_BYTES + 1)})
    response.iter_content = Mock(side_effect=AssertionError("oversized response body was read"))
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "get", Mock(return_value=response))
    assert monitor.build_ntfy_image("https://i.scdn.co/image/oversized.jpg") is None
    response.iter_content.assert_not_called()


# Verifies the shared image builder respects the canonical Pillow availability flag
def test_ntfy_image_respects_pillow_availability_flag(monkeypatch):
    image_get = Mock(side_effect=AssertionError("image download was attempted without Pillow"))
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor, "NTFY_IMAGES_AVAILABLE", False)
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "get", image_get)
    assert monitor.build_ntfy_image("https://i.scdn.co/image/cover.jpg") is None
    image_get.assert_not_called()


# Verifies image downloads cannot target arbitrary hosts through Spotify metadata
def test_ntfy_image_rejects_non_spotify_hosts(monkeypatch):
    image_get = Mock(side_effect=AssertionError("untrusted image host was contacted"))
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "get", image_get)
    assert monitor.build_ntfy_image("https://127.0.0.1/private-image.jpg") is None
    assert monitor.build_ntfy_image("https://evilscdn.co/private-image.jpg") is None
    assert monitor.build_ntfy_image("https://[invalid/private-image.jpg") is None
    image_get.assert_not_called()


# Verifies a successful ntfy image upload retains authentication and native metadata
def test_successful_ntfy_image_upload_preserves_headers(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "tk_private_access_token")
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor, "build_ntfy_image", Mock(return_value=b"jpeg-data"))
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song", image_url="https://i.scdn.co/image/cover.jpg") == 0
    request = webhook_post.call_args
    assert request.kwargs["data"] == b"jpeg-data"
    assert request.kwargs["params"] == {"title": "Title", "message": "Body"}
    assert request.kwargs["headers"]["Authorization"] == "Bearer tk_private_access_token"
    assert request.kwargs["headers"]["Content-Type"] == "image/jpeg"
    assert request.kwargs["headers"]["X-Filename"] == monitor.NTFY_IMAGE_FILENAME


# Verifies image preparation failure still delivers the ntfy alert as text
def test_ntfy_image_build_failure_falls_back_to_text(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor, "build_ntfy_image", Mock(return_value=None))
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song", image_url="https://i.scdn.co/image/cover.jpg") == 0
    assert webhook_post.call_count == 1
    assert webhook_post.call_args.kwargs["data"] == b"Body"
    assert webhook_post.call_args.kwargs["headers"]["Content-Type"] == "text/plain; charset=utf-8"


# Verifies rejected image uploads retry once as text without dropping the alert
@pytest.mark.parametrize("first_result,expected_sleeps", [(FakeResponse(400, "bad attachment"), []), (monitor.req.ConnectionError("upload failed"), [monitor.WEBHOOK_FALLBACK_RETRY_SECONDS])])
def test_ntfy_image_upload_failure_falls_back_to_text(monkeypatch, first_result, expected_sleeps):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    monkeypatch.setattr(monitor, "NTFY_IMAGES", True)
    monkeypatch.setattr(monitor, "build_ntfy_image", Mock(return_value=b"jpeg-data"))
    webhook_post = Mock(side_effect=[first_result, FakeResponse(200)])
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    sleeps = []
    assert monitor.send_webhook("Title", "Body", "song", image_url="https://i.scdn.co/image/cover.jpg", sleeper=sleeps.append) == 0
    assert webhook_post.call_count == 2
    assert webhook_post.call_args_list[0].kwargs["data"] == b"jpeg-data"
    assert webhook_post.call_args_list[1].kwargs["data"] == b"Body"
    assert sleeps == expected_sleeps


# Verifies the private ntfy token overrides custom auth while retaining safe custom headers
def test_ntfy_access_token_uses_bearer_authentication(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"authorization": "Basic older-value", "Content-Type": "application/json", "X-Priority": "high"})
    monkeypatch.setattr(monitor, "NTFY_ACCESS_TOKEN", "tk_private_access_token")
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song") == 0
    headers = webhook_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer tk_private_access_token"
    assert "authorization" not in headers
    assert headers["Content-Type"] == "text/plain; charset=utf-8"
    assert headers["X-Priority"] == "high"
    assert "tk_private_access_token" not in monitor.sanitize_error_text("NTFY_ACCESS_TOKEN=tk_private_access_token")


# Verifies malformed custom headers fail before a webhook request is attempted
@pytest.mark.parametrize("headers", [[("Authorization", "Bearer value")], {"Bad Header": "value"}, {"X-Test": 3}, {"X-Test": "first\nsecond"}, {"Authorization": "Bearer first", "authorization": "Bearer second"}])
def test_invalid_webhook_headers_are_rejected(monkeypatch, headers):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", headers)
    webhook_post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song") == 1
    webhook_post.assert_not_called()


# Verifies malformed advanced customization fails before a webhook request is attempted
@pytest.mark.parametrize("setting,value", [("WEBHOOK_USERNAME", 3), ("WEBHOOK_AVATAR_URL", "http://example.test/avatar.png"), ("WEBHOOK_TEMPLATE", 3), ("WEBHOOK_TRANSFORMS", [("title", "missing_method")]), ("WEBHOOK_TRANSFORMS", [("title",)]), ("NTFY_SHORT", "yes")])
def test_invalid_webhook_customization_is_rejected(monkeypatch, setting, value):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, setting, value)
    webhook_post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song") == 1
    webhook_post.assert_not_called()


# Verifies long ntfy messages stay below the server attachment boundary with a visible truncation marker
def test_ntfy_message_stays_below_attachment_boundary():
    title, message = monitor.build_ntfy_webhook_message("Title", ("a" * monitor.NTFY_MESSAGE_LIMIT_BYTES) + "\U0001f3b5")
    assert title == "Title"
    assert message.endswith(monitor.NTFY_TRUNCATION_SUFFIX)
    assert len(message.encode("utf-8")) <= monitor.NTFY_MESSAGE_LIMIT_BYTES
    assert len(message.encode("utf-8")) < 4096
    assert "\ufffd" not in message


# Verifies compact ntfy playback bodies preserve metadata and configured playlist suffixes
@pytest.mark.parametrize("playlist,playlist_suffix,expected", [("", "", "Track\nArtist\nAlbum"), ("Playlist", "", "Track\nArtist\nAlbum\n[Playlist]"), ("90s Pop", " (by Spotify)", "Track\nArtist\nAlbum\n[90s Pop (by Spotify)]")])
def test_short_ntfy_body_keeps_playlist_metadata(playlist, playlist_suffix, expected):
    assert monitor.build_short_ntfy_body("Track", "Artist", "Album", playlist, playlist_suffix) == expected


# Verifies compact notification durations use abbreviated time units
def test_short_ntfy_duration_uses_abbreviated_units():
    assert monitor.calculate_timespan(90061, 0, short=True) == "1 day, 1 hr, 1 min"


# Verifies compact ntfy session titles separate duration from song count consistently
@pytest.mark.parametrize("inactive,expected", [(False, "User (1 hr, 10 mins & 20 songs)"), (True, "User is inactive (after 1 hr, 10 mins & 20 songs)")])
def test_short_ntfy_session_subject_uses_readable_separator(inactive, expected):
    duration = monitor.calculate_timespan(4220, 0, show_seconds=False, short=True)
    assert monitor.build_short_ntfy_session_subject("User", duration, 20, inactive=inactive) == expected


# Verifies valid ntfy priority and tags are sent as native query parameters
def test_ntfy_metadata_is_sent_as_query_parameters(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    webhook_post = Mock(return_value=FakeResponse(200))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song", ntfy_priority=5, ntfy_tags=" warning,musical_note ") == 0
    assert webhook_post.call_args.kwargs["params"] == {"title": "Title", "priority": 5, "tags": "warning,musical_note"}


# Verifies invalid ntfy metadata fails before a webhook request is attempted
@pytest.mark.parametrize("priority,tags", [(-1, ""), (6, ""), (True, ""), (0, ["warning"]), (0, "warning\nalert")])
def test_invalid_ntfy_metadata_is_rejected(monkeypatch, priority, tags):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "ntfy")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "https://ntfy.example.test/private-topic")
    webhook_post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", webhook_post)
    assert monitor.send_webhook("Title", "Body", "song", ntfy_priority=priority, ntfy_tags=tags) == 1
    webhook_post.assert_not_called()


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
    webhook.assert_called_once_with("Title", "Body", "song", force=True, image_url="", ntfy_priority=0, ntfy_tags="")


# Verifies compact content is ntfy-only and missing compact fields fall back to normal content
@pytest.mark.parametrize("provider,notification_type,subject_short,body_short,expected_subject,expected_body", [("ntfy", "song", "Short title", "Short body", "Short title", "Short body"), ("ntfy", "error", "", "", "Normal title", "Normal body"), ("discord", "song", "Short title", "Short body", "Normal title", "Normal body")])
def test_short_notification_content_is_ntfy_only_with_fallbacks(monkeypatch, provider, notification_type, subject_short, body_short, expected_subject, expected_body):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", provider)
    monkeypatch.setattr(monitor, "NTFY_SHORT", True)
    webhook = Mock(return_value=0)
    monkeypatch.setattr(monitor, "send_webhook", webhook)
    assert monitor.send_notification_channels(notification_type, "Normal title", "Normal body", webhook_enabled=True, subject_short=subject_short, body_short=body_short) == (False, True)
    webhook.assert_called_once_with(expected_subject, expected_body, notification_type, force=True, image_url="", ntfy_priority=0, ntfy_tags="")


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


# Verifies the wizard preserves ntfy URLs and expands bare ntfy.sh topics without contacting the service
@pytest.mark.parametrize("entered_value,saved_url", [("https://ntfy.sh/private-topic", "https://ntfy.sh/private-topic"), ("private-topic", "https://ntfy.sh/private-topic")])
def test_webhook_wizard_supports_ntfy(monkeypatch, entered_value, saved_url):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        answers = iter([True, False])
        choices = iter([1, 0])
        post = Mock(side_effect=AssertionError("webhook request attempted"))
        monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: next(answers))
        monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda *args, **kwargs: entered_value)
        monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: next(choices))
        monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
        config_values = {}
        secret_updates = {}
        enabled = monitor._wizard_collect_webhook(config_values, secret_updates, destination)
        assert enabled == ["active", "inactive", "errors"]
        assert secret_updates == {"WEBHOOK_URL": saved_url}
        assert config_values["WEBHOOK_ENABLED"] is True
        assert config_values["WEBHOOK_PROVIDER"] == "ntfy"
        post.assert_not_called()


# Verifies the ntfy wizard collects an access token privately for dotenv persistence
def test_webhook_wizard_collects_ntfy_access_token(monkeypatch):
    with make_test_directory() as directory_name:
        destination = Path(directory_name) / ".env"
        answers = iter([True, True])
        choices = iter([1, 0])
        secrets = iter(["https://ntfy.example.test/private-topic", "tk_private_access_token"])
        post = Mock(side_effect=AssertionError("webhook request attempted"))
        monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: next(answers))
        monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda *args, **kwargs: next(secrets))
        monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: next(choices))
        monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
        config_values = {}
        secret_updates = {}
        enabled = monitor._wizard_collect_webhook(config_values, secret_updates, destination)
        assert enabled == ["active", "inactive", "errors"]
        assert secret_updates == {"WEBHOOK_URL": "https://ntfy.example.test/private-topic", "NTFY_ACCESS_TOKEN": "tk_private_access_token"}
        assert "tk_private_access_token" not in str(config_values)
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
        monkeypatch.setattr(monitor, "_doctor_ask_yes_no", lambda question: False)
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


# Verifies full setup persists ntfy URL and token only in the dotenv file
def test_setup_wizard_persists_ntfy_access_token(monkeypatch, capsys):
    with make_test_directory() as directory_name:
        directory = Path(directory_name)
        config_path = directory / "spotify_monitor.conf"
        env_path = directory / ".env"
        topic_url = "https://ntfy.example.test/private-topic"
        token = "tk_private_access_token"
        answers = iter([True, False, True, True, False])
        choices = iter([0, 1, 0, 0])
        secrets = iter([topic_url, token])
        monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=lambda: True))
        monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
        monkeypatch.setattr(monitor, "_wizard_target", lambda initial=None: "target.user")
        monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda *args, **kwargs: next(answers))
        monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda *args, **kwargs: next(choices))
        monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda *args, **kwargs: 30)
        monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda *args, **kwargs: next(secrets))
        monkeypatch.setattr(monitor, "_wizard_collect_cookie_auth", lambda *args, **kwargs: {"complete": False, "validated": False, "browser": None, "source": "not configured", "mount_required": False})
        with pytest.raises(SystemExit) as error:
            monitor.run_setup_wizard(config_file=config_path, env_file=env_path)
        assert error.value.code == 0
        config = config_path.read_text(encoding="utf-8")
        dotenv = dotenv_values(env_path, interpolate=False)
        assert 'WEBHOOK_PROVIDER = "ntfy"' in config
        assert topic_url not in config
        assert token not in config
        assert dotenv["WEBHOOK_URL"] == topic_url
        assert dotenv["NTFY_ACCESS_TOKEN"] == token
        output = capsys.readouterr().out
        assert topic_url not in output
        assert token not in output


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


# Verifies one-run webhook CLI options override provider, URL and error delivery
def test_send_test_webhook_cli_applies_runtime_overrides(monkeypatch):
    delivery = Mock(return_value=0)
    url = "https://ntfy.example.test/private-topic"
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--webhook-provider", "ntfy", "--webhook-url", url, "--webhook-errors", "--send-test-webhook", "--env-file", "none"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "")
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "clear_screen", Mock())
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "send_webhook", delivery)
    with pytest.raises(SystemExit) as error:
        monitor.main()
    assert error.value.code == 0
    assert monitor.WEBHOOK_PROVIDER == "ntfy"
    assert monitor.WEBHOOK_URL == url
    assert monitor.WEBHOOK_ENABLED is True
    assert monitor.WEBHOOK_ERROR_NOTIFICATION is True
    delivery.assert_called_once_with("Spotify Monitor test", "Your webhook alerts are set up correctly.", "song", force=True)


# Verifies a known ntfy URL corrects a stale configured provider before Doctor or test delivery
def test_send_test_webhook_cli_autodetects_ntfy_provider(monkeypatch, capsys):
    delivery = Mock(return_value=0)
    url = "https://ntfy.sh/private-topic"
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--webhook-url", url, "--send-test-webhook", "--env-file", "none"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", "")
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "clear_screen", Mock())
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "send_webhook", delivery)
    with pytest.raises(SystemExit) as error:
        monitor.main()
    assert error.value.code == 0
    assert monitor.WEBHOOK_PROVIDER == "ntfy"
    assert "Using ntfy" in capsys.readouterr().out
    delivery.assert_called_once_with("Spotify Monitor test", "Your webhook alerts are set up correctly.", "song", force=True)


# Verifies the direct webhook URL CLI override retains strict HTTPS validation
def test_webhook_url_cli_rejects_insecure_url(monkeypatch, capsys):
    delivery = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--webhook-url", "http://example.test/private-topic", "--send-test-webhook", "--env-file", "none"])
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "clear_screen", Mock())
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "send_webhook", delivery)
    with pytest.raises(SystemExit) as error:
        monitor.main()
    assert error.value.code == 2
    assert "complete HTTPS link without embedded credentials" in capsys.readouterr().err
    delivery.assert_not_called()


# Verifies the doctor checks webhook settings without sending a message
def test_doctor_webhook_check_is_read_only(monkeypatch):
    configure_webhook(monkeypatch)
    post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
    checks = monitor.doctor_check_webhook_notifications()
    assert checks == [monitor.make_doctor_check("Notifications", "PASS", "Webhook URL and alert choices look valid", "The private link was not displayed. No webhook was sent during this passive check")]
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


# Verifies the doctor validates custom headers without contacting the webhook service
def test_doctor_rejects_invalid_webhook_headers(monkeypatch):
    configure_webhook(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"Bad Header": "private-value"})
    post = Mock(side_effect=AssertionError("webhook request attempted"))
    monkeypatch.setattr(monitor.WEBHOOK_SESSION, "post", post)
    checks = monitor.doctor_check_webhook_notifications()
    assert checks[0].status == "FAIL"
    assert "invalid HTTP header name" in checks[0].detail
    post.assert_not_called()


# Verifies Spotify and webhook retry caps remain deliberately separate
def test_spotify_retry_cap_is_unchanged_and_separate():
    assert monitor.MAX_RETRY_AFTER_SECONDS == 60
    assert monitor.WEBHOOK_MAX_RETRY_AFTER_SECONDS == 5.0
    assert monitor.retry.total == 5
    webhook_adapter = monitor.WEBHOOK_SESSION.adapters["https://"]
    assert isinstance(webhook_adapter, monitor.HTTPAdapter)
    assert webhook_adapter.max_retries.total == 0
