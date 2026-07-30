import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import dotenv
import pytest

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "spotify_monitor.py"


# Runs one CLI command without raising for a nonzero status
def run_cli(*arguments):
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, str(CLI_PATH), *arguments], cwd=PROJECT_ROOT, capture_output=True, text=True, env=environment, timeout=30, check=False)


# Installs deterministic focused-wizard inputs for one project-local destination pair
def install_scrobble_setup_flow(monkeypatch, config_path, env_path, auth, yes_no_answers, choice_answers=(0,), positive_answers=None, method="manual"):
    answers = iter(yes_no_answers)
    choices = iter(choice_answers)
    positive_values = iter(positive_answers) if positive_answers is not None else None
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=Mock(return_value=True)))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: method)
    monkeypatch.setattr(monitor, "_wizard_destinations", lambda config_file, env_file, method=None, **kwargs: (config_path, env_path))
    monkeypatch.setattr(monitor, "_wizard_choose_config_destination", lambda path: path)
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: "lastfm-user")
    monkeypatch.setattr(monitor, "_wizard_ask_duration", lambda question, default: next(positive_values) if positive_values is not None else default)
    monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda question, default: next(positive_values) if positive_values is not None else default)
    monkeypatch.setattr(monitor, "_wizard_existing_secret", lambda key, path: True)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", Mock(side_effect=lambda question, default=True: next(answers)))
    monkeypatch.setattr(monitor, "_wizard_ask_choice", Mock(side_effect=lambda question, options: next(choices)))
    # Supplies stable app settings without opening a real browser during broader setup tests
    def collect_auth(state, selected_method):
        state.config_values["SPOTIFY_SCROBBLE_CLIENT_ID"] = "a" * 32
        state.config_values["SPOTIFY_SCROBBLE_REDIRECT_URI"] = "http://127.0.0.1:8888/callback"
        state.auth = dict(auth)
        if auth.get("complete"):
            state.secret_updates["SPOTIFY_SCROBBLE_REFRESH_TOKEN"] = "private-refresh-token"

    monkeypatch.setattr(monitor, "_wizard_collect_scrobble_health_auth_section", collect_auth)
    monkeypatch.setattr(monitor, "_wizard_collect_email", lambda values, updates, path, scrobble_health=False: [])
    monkeypatch.setattr(monitor, "_wizard_collect_webhook", lambda values, updates, path, scrobble_health=False: [])


# Builds one completed Spotify play with stable metadata
def spotify_play(timestamp, track="Track", artist="Artist"):
    return monitor.SpotifyPlay(float(timestamp), artist, track, 180000, f"spotify:track:{timestamp}")


# Builds one completed Last.fm scrobble with stable metadata
def lastfm_scrobble(timestamp, track="Track", artist="Artist"):
    return monitor.LastfmScrobble(float(timestamp), artist, track)


# Confirms user-owned PKCE authorization asks only for recent-play access
def test_spotify_build_scrobble_authorization_url_uses_minimal_scope():
    authorization_url = monitor.spotify_build_scrobble_authorization_url("a" * 32, "http://127.0.0.1:8888/callback", "verifier", "state-value")
    parameters = monitor.parse_qs(monitor.urlparse(authorization_url).query)
    assert parameters["client_id"] == ["a" * 32]
    assert parameters["redirect_uri"] == ["http://127.0.0.1:8888/callback"]
    assert parameters["scope"] == ["user-read-recently-played"]
    assert parameters["state"] == ["state-value"]
    assert parameters["code_challenge_method"] == ["S256"]
    assert "client_secret" not in parameters


# Confirms pasted callbacks must match the registered redirect and authorization state
def test_spotify_parse_scrobble_callback_validates_redirect_and_state():
    redirect_uri = "http://127.0.0.1:8888/callback"
    assert monitor.spotify_parse_scrobble_callback(f"{redirect_uri}?code=authorization-code&state=expected", redirect_uri, "expected") == "authorization-code"
    with pytest.raises(monitor.SpotifyScrobbleAuthorizationError, match="invalid state"):
        monitor.spotify_parse_scrobble_callback(f"{redirect_uri}?code=authorization-code&state=wrong", redirect_uri, "expected")
    with pytest.raises(monitor.SpotifyScrobbleAuthorizationError, match="complete redirected URL"):
        monitor.spotify_parse_scrobble_callback("http://127.0.0.1:9999/callback?code=authorization-code&state=expected", redirect_uri, "expected")


# Confirms refresh-token authorization uses the user's Spotify app and caches the result
def test_spotify_get_scrobble_access_token_uses_user_owned_app(monkeypatch):
    token_response = Mock(status_code=200)
    token_response.raise_for_status.return_value = None
    token_response.json.return_value = {"access_token": "scoped-token", "refresh_token": "rotated-refresh", "expires_in": 3600}
    session = Mock()
    session.post.return_value = token_response
    monkeypatch.setattr(monitor, "SP_CACHED_SCROBBLE_ACCESS_TOKEN", None)
    monkeypatch.setattr(monitor, "SP_SCROBBLE_ACCESS_TOKEN_EXPIRES_AT", 0)
    monkeypatch.setattr(monitor, "SP_CACHED_SCROBBLE_AUTH_FINGERPRINT", "")
    monkeypatch.setattr(monitor, "USER_AGENT", "test-agent")
    persistence = Mock(return_value=True)
    monkeypatch.setattr(monitor, "persist_spotify_scrobble_refresh_token", persistence)

    token = monitor.spotify_get_scrobble_access_token("a" * 32, "private-refresh", session)

    assert token == "scoped-token"
    assert session.post.call_args.kwargs["data"] == {"client_id": "a" * 32, "grant_type": "refresh_token", "refresh_token": "private-refresh"}
    persistence.assert_called_once_with("rotated-refresh")


# Confirms an expired Spotify grant points to standalone reauthorization
def test_spotify_get_scrobble_access_token_reports_expired_grant(monkeypatch):
    response = Mock(status_code=400)
    response.json.return_value = {"error": "invalid_grant", "error_description": "Refresh token revoked"}
    session = Mock()
    session.post.return_value = response
    monkeypatch.setattr(monitor, "SP_CACHED_SCROBBLE_ACCESS_TOKEN", None)
    monkeypatch.setattr(monitor, "SP_SCROBBLE_ACCESS_TOKEN_EXPIRES_AT", 0)
    monkeypatch.setattr(monitor, "SP_CACHED_SCROBBLE_AUTH_FINGERPRINT", "")
    with pytest.raises(monitor.SpotifyScrobbleAuthorizationError, match="expired or was revoked") as error:
        monitor.spotify_get_scrobble_access_token("a" * 32, "private-refresh", session)
    advice = monitor.classify_recovery_error(error.value, "scrobble_health")
    assert "--authorize-scrobble-health" in advice.fix


# Confirms standalone authorization guides app creation and stores only the private refresh token
def test_run_authorize_scrobble_health_guides_and_saves(monkeypatch, capsys):
    artifact_root = PROJECT_ROOT / "local"
    artifact_root.mkdir(parents=True, exist_ok=True)
    env_path = artifact_root / f"test-scrobble-authorize-{os.getpid()}.env"
    config_path = artifact_root / f"test-scrobble-authorize-{os.getpid()}.conf"
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
    monkeypatch.setattr(monitor, "_dotenv_contains_key", lambda path, key: False)
    monkeypatch.setattr(monitor, "spotify_authorize_scrobble_health", lambda *args, **kwargs: {"access_token": "access-token", "refresh_token": "private-refresh-token", "expires_in": 3600})
    try:
        result = monitor.run_authorize_scrobble_health("a" * 32, "http://127.0.0.1:8888/callback", env_file=env_path, config_path=config_path, interactive=True)
        values = dotenv.dotenv_values(env_path, interpolate=False)
        output = capsys.readouterr().out
        assert result == str(env_path)
        assert values == {"SPOTIFY_SCROBBLE_REFRESH_TOKEN": "private-refresh-token"}
        assert monitor.SPOTIFY_DEVELOPER_DASHBOARD_URL in output
        assert monitor.SPOTIFY_APPS_GUIDE_URL in output
        assert monitor.SPOTIFY_PKCE_GUIDE_URL in output
        assert "--monitor-mode scrobble_health --doctor" in output
    finally:
        for path in (config_path, env_path):
            if path.exists():
                path.unlink()


# Confirms Spotify recent-play parsing keeps only completed track-shaped records
def test_spotify_get_recent_plays_parses_completed_tracks(monkeypatch):
    response = Mock(status_code=200)
    response.raise_for_status.return_value = None
    response.json.return_value = {"items": [{"played_at": "2026-07-28T10:00:00.000Z", "track": {"name": "Track", "artists": [{"name": "Artist"}], "duration_ms": 123000, "uri": "spotify:track:1"}}, {"played_at": "invalid", "track": {"name": "Ignored", "artists": [{"name": "Artist"}]}}]}
    session = Mock()
    session.get.return_value = response
    monkeypatch.setattr(monitor, "spotify_get_scrobble_access_token", lambda client_id, refresh_token, selected_session: "token")

    plays = monitor.spotify_get_recent_plays("a" * 32, "private-refresh", session)

    assert [(play.artist, play.track, play.duration_ms, play.uri) for play in plays] == [("Artist", "Track", 123000, "spotify:track:1")]


# Confirms Last.fm parsing excludes the unscrobbled currently playing row
def test_lastfm_get_recent_scrobbles_ignores_now_playing():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"recenttracks": {"track": [{"name": "Current", "artist": {"#text": "Artist"}, "@attr": {"nowplaying": "true"}}, {"name": "Completed", "artist": {"#text": "Artist"}, "date": {"uts": "1000"}}]}}
    session = Mock()
    session.get.return_value = response

    scrobbles = monitor.lastfm_get_recent_scrobbles("lastfm-user", "api-key", session)

    assert [(scrobble.artist, scrobble.track, scrobble.played_at) for scrobble in scrobbles] == [("Artist", "Completed", 1000.0)]


# Confirms the focused wizard persists scrobble mode and its conservative defaults
def test_scrobble_health_setup_wizard_writes_mode(monkeypatch, capsys):
    config_path = PROJECT_ROOT / "local" / f"test-scrobble-health-setup-{os.getpid()}.conf"
    env_path = PROJECT_ROOT / "local" / f"test-scrobble-health-setup-{os.getpid()}.env"
    auth = {"complete": True, "validated": False, "source": "user-owned Spotify app with PKCE"}
    install_scrobble_setup_flow(monkeypatch, config_path, env_path, auth, (False, False))

    try:
        with pytest.raises(SystemExit) as exc_info:
            monitor.run_scrobble_health_setup_wizard()
        content = config_path.read_text(encoding="utf-8")
        assert exc_info.value.code == 0
        assert 'MONITOR_MODE = "scrobble_health"' in content
        assert 'LASTFM_USERNAME = "lastfm-user"' in content
        assert "SCROBBLE_HEALTH_MIN_UNMATCHED = 5" in content
        assert "Monitoring was not offered because scrobble health Doctor has not passed" in capsys.readouterr().out
    finally:
        for path in (config_path, env_path):
            if path.exists():
                path.unlink()


# Confirms focused setup clears an interactive screen like regular setup
def test_scrobble_health_setup_uses_normal_startup_clear(monkeypatch):
    clear_mock = Mock()
    output = Mock()
    output.isatty.return_value = True
    output.fileno.return_value = 1
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--setup-scrobble-health"])
    monkeypatch.setattr(monitor.sys, "stdout", output)
    monkeypatch.setattr(monitor, "clear_screen", clear_mock)
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor, "run_scrobble_health_setup_wizard", Mock(side_effect=SystemExit(0)))
    with pytest.raises(SystemExit) as error:
        monitor.main()
    assert error.value.code == 0
    clear_mock.assert_called_once_with(bool(monitor.CLEAR_SCREEN))


@pytest.mark.parametrize("arguments", [("--token-source", "client"), ("--spotify-dc-cookie", "private-cookie"), ("--lastfm-username", "lastfm-user"), ("--lastfm-api-key", "private-api-key"), ("--webhook-url", "https://example.test/private"), ("--scrobble-dead-period", "10"), ("--scrobble-match-window", "10"), ("--scrobble-state-file", "state.json"), ("--debug",), ("--browser", "firefox"), ("--notify-active",), ("--track-in-spotify",)])
# Confirms focused setup rejects unrelated options instead of silently ignoring them
def test_scrobble_health_setup_rejects_unrelated_cli_options(arguments):
    result = run_cli("--setup-scrobble-health", *arguments)
    assert result.returncode == 2
    assert "--setup-scrobble-health cannot be combined with" in result.stderr


# Confirms focused setup accepts only its config and dotenv destination options
def test_scrobble_health_setup_accepts_file_options():
    result = run_cli("--setup-scrobble-health", "--config-file", "local/test.conf", "--env-file=local/test.env")
    assert result.returncode == 1
    assert "needs an interactive terminal" in result.stdout
    assert "cannot be combined with" not in result.stderr


# Confirms focused setup cannot disable the config file it must create
def test_scrobble_health_setup_rejects_disabled_config_destination():
    result = run_cli("--setup-scrobble-health", "--config-file", "none")
    assert result.returncode == 2
    assert "requires a config destination and cannot use --config-file none" in result.stderr


# Confirms standalone reauthorization accepts only app settings plus file destinations
def test_scrobble_health_authorize_accepts_guided_options():
    result = run_cli("--authorize-scrobble-health", "--config-file", "none", "--env-file", "local/test-authorize.env", "--scrobble-client-id", "a" * 32, "--scrobble-redirect-uri", "http://127.0.0.1:8888/callback")
    assert result.returncode == 1
    assert "requires an interactive terminal" in result.stdout
    assert "does not exist" not in result.stdout
    assert "cannot be combined with" not in result.stderr


# Confirms focused setup requests isolated default destinations
def test_scrobble_health_setup_requests_isolated_default_destinations(monkeypatch):
    destination_mock = Mock(side_effect=SystemExit(0))
    monkeypatch.setattr(monitor.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
    monkeypatch.setattr(monitor, "_wizard_destinations", destination_mock)
    with pytest.raises(SystemExit) as error:
        monitor.run_scrobble_health_setup_wizard()
    assert error.value.code == 0
    destination_mock.assert_called_once_with(None, None, method="manual", default_config_filename=monitor.SCROBBLE_HEALTH_CONFIG_FILENAME, default_env_filename=monitor.SCROBBLE_HEALTH_DOTENV_FILENAME)


# Confirms scrobble health config discovery does not select the Friend Activity file
def test_scrobble_health_config_discovery_uses_isolated_default(monkeypatch):
    artifact_root = PROJECT_ROOT / "local"
    artifact_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=artifact_root) as directory_name:
        directory = Path(directory_name)
        friend_config = directory / monitor.DEFAULT_CONFIG_FILENAME
        scrobble_config = directory / monitor.SCROBBLE_HEALTH_CONFIG_FILENAME
        friend_config.write_text('MONITOR_MODE = "friend_activity"\n', encoding="utf-8")
        scrobble_config.write_text('MONITOR_MODE = "scrobble_health"\n', encoding="utf-8")
        monkeypatch.chdir(directory)
        assert monitor.find_config_file() == str(friend_config)
        assert monitor.find_scrobble_health_config_file() == str(scrobble_config)


# Confirms the scrobble health CLI selects isolated config and dotenv discovery
def test_scrobble_health_cli_selects_isolated_default_files(monkeypatch):
    scrobble_config_finder = Mock(return_value=None)
    friend_config_finder = Mock(side_effect=AssertionError("Friend Activity config discovery used"))
    dotenv_finder = Mock(return_value="")
    doctor_mock = Mock(return_value=0)
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--monitor-mode", "scrobble_health", "--doctor"])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled: None)
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor, "find_config_file", friend_config_finder)
    monkeypatch.setattr(monitor, "find_scrobble_health_config_file", scrobble_config_finder)
    monkeypatch.setattr(dotenv, "find_dotenv", dotenv_finder)
    monkeypatch.setattr(monitor, "run_scrobble_health_doctor", doctor_mock)
    monkeypatch.setattr(monitor, "MONITOR_MODE", "friend_activity")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "LASTFM_USERNAME", "lastfm-user")
    with pytest.raises(SystemExit) as error:
        monitor.main()
    assert error.value.code == 0
    scrobble_config_finder.assert_called_once_with(None)
    friend_config_finder.assert_not_called()
    dotenv_finder.assert_called_once_with(filename=monitor.SCROBBLE_HEALTH_DOTENV_FILENAME)
    doctor_mock.assert_called_once()


# Confirms every core scrobble health value can be supplied without config or dotenv files
def test_scrobble_health_cli_supports_file_free_runtime_configuration(monkeypatch):
    config_finder = Mock(side_effect=AssertionError("Config discovery should be disabled"))
    dotenv_finder = Mock(side_effect=AssertionError("Dotenv discovery should be disabled"))
    captured = {}
    monkeypatch.setenv("LASTFM_API_KEY", "ignored-environment-api-key")
    monkeypatch.setenv("SPOTIFY_SCROBBLE_REFRESH_TOKEN", "ignored-environment-refresh-token")

    # Captures effective runtime values after all command-line overrides
    def run_doctor(username, config_path=None, env_path=None, startup_checks=()):
        captured.update({"username": username, "config_path": config_path, "env_path": env_path, "api_key": monitor.LASTFM_API_KEY, "client_id": monitor.SPOTIFY_SCROBBLE_CLIENT_ID, "redirect_uri": monitor.SPOTIFY_SCROBBLE_REDIRECT_URI, "refresh_token": monitor.SPOTIFY_SCROBBLE_REFRESH_TOKEN, "check_interval": monitor.SCROBBLE_HEALTH_CHECK_INTERVAL, "dead_period": monitor.SCROBBLE_HEALTH_DEAD_PERIOD, "min_unmatched": monitor.SCROBBLE_HEALTH_MIN_UNMATCHED, "match_window": monitor.SCROBBLE_HEALTH_MATCH_WINDOW, "lookback": monitor.SCROBBLE_HEALTH_LOOKBACK, "repeat_interval": monitor.SCROBBLE_HEALTH_REPEAT_INTERVAL, "state_file": monitor.SCROBBLE_HEALTH_STATE_FILE})
        return 0

    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--monitor-mode", "scrobble_health", "--config-file", "none", "--env-file", "none", "--lastfm-username", "lastfm-user", "--lastfm-api-key", "private-api-key", "--scrobble-client-id", "a" * 32, "--scrobble-redirect-uri", "http://127.0.0.1:8888/callback", "--scrobble-refresh-token", "private-refresh-token", "--scrobble-check-interval", "180", "--scrobble-dead-period", "1500", "--scrobble-min-unmatched", "7", "--scrobble-match-window", "240", "--scrobble-lookback", "18000", "--scrobble-repeat-interval", "0", "--scrobble-state-file", "local/health-state.json", "--doctor"])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled: None)
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor, "find_config_file", config_finder)
    monkeypatch.setattr(monitor, "find_scrobble_health_config_file", config_finder)
    monkeypatch.setattr(dotenv, "find_dotenv", dotenv_finder)
    monkeypatch.setattr(monitor, "run_scrobble_health_doctor", run_doctor)
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "MONITOR_MODE", "friend_activity")
    monkeypatch.setattr(monitor, "LASTFM_USERNAME", "")
    monkeypatch.setattr(monitor, "LASTFM_API_KEY", "")
    with pytest.raises(SystemExit) as error:
        monitor.main()
    assert error.value.code == 0
    assert captured == {"username": "lastfm-user", "config_path": None, "env_path": None, "api_key": "private-api-key", "client_id": "a" * 32, "redirect_uri": "http://127.0.0.1:8888/callback", "refresh_token": "private-refresh-token", "check_interval": 180, "dead_period": 1500, "min_unmatched": 7, "match_window": 240, "lookback": 18000, "repeat_interval": 0, "state_file": "local/health-state.json"}
    config_finder.assert_not_called()
    dotenv_finder.assert_not_called()


# Confirms process environment secrets work when dotenv discovery is disabled
def test_scrobble_health_cli_loads_environment_without_dotenv(monkeypatch):
    captured = {}
    monkeypatch.setenv("LASTFM_API_KEY", "environment-api-key")
    monkeypatch.setenv("SPOTIFY_SCROBBLE_CLIENT_ID", "b" * 32)
    monkeypatch.setenv("SPOTIFY_SCROBBLE_REDIRECT_URI", "http://127.0.0.1:9999/callback")
    monkeypatch.setenv("SPOTIFY_SCROBBLE_REFRESH_TOKEN", "environment-refresh-token")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--monitor-mode", "scrobble_health", "--config-file", "none", "--env-file", "none", "--lastfm-username", "lastfm-user", "--doctor"])
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled: None)
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor, "run_scrobble_health_doctor", lambda username, config_path=None, env_path=None, startup_checks=(): (captured.update({"api_key": monitor.LASTFM_API_KEY, "client_id": monitor.SPOTIFY_SCROBBLE_CLIENT_ID, "redirect_uri": monitor.SPOTIFY_SCROBBLE_REDIRECT_URI, "refresh_token": monitor.SPOTIFY_SCROBBLE_REFRESH_TOKEN}) or 0))
    monkeypatch.setattr(monitor, "CLI_CONFIG_PATH", None)
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "MONITOR_MODE", "friend_activity")
    monkeypatch.setattr(monitor, "LASTFM_USERNAME", "")
    monkeypatch.setattr(monitor, "LASTFM_API_KEY", "")
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_CLIENT_ID", "")
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_REDIRECT_URI", "")
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_REFRESH_TOKEN", "")
    with pytest.raises(SystemExit) as error:
        monitor.main()
    assert error.value.code == 0
    assert captured == {"api_key": "environment-api-key", "client_id": "b" * 32, "redirect_uri": "http://127.0.0.1:9999/callback", "refresh_token": "environment-refresh-token"}


@pytest.mark.parametrize(("option", "value", "message"), [("--scrobble-match-window", "0", "must be greater than zero"), ("--scrobble-lookback", "-1", "must be greater than zero"), ("--scrobble-repeat-interval", "-1", "must be zero or greater")])
# Confirms new scrobble timing options reject unsafe bounds
def test_scrobble_health_cli_rejects_invalid_extended_timers(option, value, message):
    result = run_cli("--monitor-mode", "scrobble_health", "--config-file", "none", "--env-file", "none", "--lastfm-username", "lastfm-user", "--lastfm-api-key", "api-key", "--scrobble-client-id", "a" * 32, "--scrobble-refresh-token", "refresh-token", option, value, "--doctor")
    assert result.returncode == 2
    assert f"{option} {message}" in result.stderr


# Confirms scrobble health secret reload keeps using the isolated dotenv default
def test_scrobble_health_secret_reload_uses_isolated_default(monkeypatch):
    if not hasattr(monitor.signal, "SIGHUP"):
        pytest.skip("SIGHUP is unavailable on Windows")
    dotenv_finder = Mock(return_value="")
    monkeypatch.setattr(monitor, "MONITOR_MODE", "scrobble_health")
    monkeypatch.setattr(monitor, "DOTENV_FILE", "")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(dotenv, "find_dotenv", dotenv_finder)
    monitor.reload_secrets_signal_handler(monitor.signal.SIGHUP, None)
    dotenv_finder.assert_called_once_with(filename=monitor.SCROBBLE_HEALTH_DOTENV_FILENAME)


# Confirms focused email setup enables only scrobble-relevant notification flags
def test_scrobble_health_setup_collects_focused_email_flags(monkeypatch):
    config_values = {}
    secret_updates = {}
    answers = iter((True, True, True, False))
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=False: next(answers))
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, required=False: "value@example.test")
    monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda question, default: 587)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: "private-password")
    monkeypatch.setattr(monitor, "_wizard_validate_smtp", lambda values, password: None)
    monkeypatch.setattr(monitor, "_wizard_queue_secret", lambda updates, path, key, value: (updates.update({key: value}) or True))
    enabled = monitor._wizard_collect_email(config_values, secret_updates, PROJECT_ROOT / "local" / "unused.env", scrobble_health=True)
    assert enabled == ["scrobble outage and recovery"]
    assert config_values["SCROBBLE_HEALTH_NOTIFICATION"] is True
    assert config_values["ERROR_NOTIFICATION"] is False
    assert config_values["ACTIVE_NOTIFICATION"] is False
    assert secret_updates["SMTP_PASSWORD"] == "private-password"


# Confirms focused setup guides API entry without asking for the configured redirect URI
def test_scrobble_health_setup_guides_lastfm_api_key_entry(monkeypatch, capsys):
    redirect_uri = "http://127.0.0.1:9999/callback"
    state = monitor.ScrobbleHealthSetupState(Path("config.conf"), Path(".env"), {}, {"SPOTIFY_SCROBBLE_REDIRECT_URI": redirect_uri}, {}, "lastfm-user", {}, [], [])
    guidance_before_prompt = []
    text_questions = []

    # Captures wizard output at the moment hidden key entry begins
    def ask_secret(question):
        guidance_before_prompt.append(capsys.readouterr().out)
        return "private-api-key"

    secret_prompt = Mock(side_effect=ask_secret)
    authorize = Mock(return_value={"access_token": "access-token", "refresh_token": "refresh-token", "expires_in": 3600})
    monkeypatch.setattr(monitor, "_wizard_existing_secret", lambda key, path: False)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", secret_prompt)
    monkeypatch.setattr(monitor, "_wizard_queue_secret", lambda updates, path, key, value: updates.update({key: value}))
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: (text_questions.append(question) or "a" * 32))
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: True)
    monkeypatch.setattr(monitor, "spotify_authorize_scrobble_health", authorize)
    monitor._wizard_collect_scrobble_health_auth_section(state, "manual")
    assert guidance_before_prompt == [f"\nCreate or view your Last.fm API account: {monitor.LASTFM_API_ACCOUNTS_URL}\n"]
    secret_prompt.assert_called_once_with("Last.fm API key")
    assert text_questions == ["Spotify app Client ID"]
    assert authorize.call_args.args[:2] == ("a" * 32, redirect_uri)
    output = capsys.readouterr().out
    assert "2. Create an app or open an existing app." in output
    assert f"3. Add this exact Redirect URI in the app settings: {redirect_uri}" in output
    assert "4. Select Web API in API/SDKs section, click Save." in output
    assert "5. Copy the Client ID. A Client Secret is not needed and should not be entered here." in output
    assert state.secret_updates["LASTFM_API_KEY"] == "private-api-key"


# Confirms focused setup separates profile, duration prompts and missing-play evidence
def test_scrobble_health_setup_spaces_profile_duration_and_evidence_prompts(monkeypatch, capsys):
    state = monitor.ScrobbleHealthSetupState(Path("config.conf"), Path(".env"), {}, {}, {}, "lastfm-user", {}, [], [])
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: (print(question) or "lastfm-user"))
    monkeypatch.setattr(monitor, "_wizard_ask_duration", lambda question, default: (print(question) or default))
    monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda question, default: (print(question) or default))
    monitor._wizard_collect_scrobble_health_profile_section(state)
    monitor._wizard_collect_scrobble_health_threshold_section(state)
    assert capsys.readouterr().out == "Last.fm username\n\nComparison interval (seconds or use s/m/h/d)\nDead period before an alert\n\nConsecutive missing completed plays required for an alert\n"


# Confirms focused webhook setup enables only scrobble-relevant alert flags
def test_scrobble_health_setup_collects_focused_webhook_flags(monkeypatch):
    config_values = {}
    secret_updates = {}
    answers = iter((True, True, False))
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=False: next(answers))
    monkeypatch.setattr(monitor, "_wizard_ask_choice", lambda question, options: 0)
    monkeypatch.setattr(monitor, "_wizard_existing_secret", lambda key, path, placeholders=(): False)
    monkeypatch.setattr(monitor, "_wizard_ask_secret", lambda question: "https://discord.example.test/private")
    monkeypatch.setattr(monitor, "validate_webhook_url", lambda value: True)
    monkeypatch.setattr(monitor, "_wizard_queue_secret", lambda updates, path, key, value: (updates.update({key: value}) or True))
    enabled = monitor._wizard_collect_webhook(config_values, secret_updates, PROJECT_ROOT / "local" / "unused.env", scrobble_health=True)
    assert enabled == ["scrobble outage and recovery"]
    assert config_values["WEBHOOK_SCROBBLE_HEALTH_NOTIFICATION"] is True
    assert config_values["WEBHOOK_ERROR_NOTIFICATION"] is False
    assert config_values["WEBHOOK_ACTIVE_NOTIFICATION"] is False
    assert secret_updates["WEBHOOK_URL"] == "https://discord.example.test/private"


# Confirms the focused summary reports outage and operational flags independently
def test_scrobble_health_setup_summary_distinguishes_notification_flags(capsys):
    config_values = {"SCROBBLE_HEALTH_MIN_UNMATCHED": 5, "SCROBBLE_HEALTH_DEAD_PERIOD": 1200, "SCROBBLE_HEALTH_CHECK_INTERVAL": 300, "SCROBBLE_HEALTH_NOTIFICATION": False, "ERROR_NOTIFICATION": True, "WEBHOOK_SCROBBLE_HEALTH_NOTIFICATION": True, "WEBHOOK_ERROR_NOTIFICATION": False, "SPOTIFY_SCROBBLE_REDIRECT_URI": "http://127.0.0.1:8888/callback"}
    auth = {"complete": True, "source": "user-owned Spotify app with PKCE", "mount_required": False, "host_os": None}
    state = monitor.ScrobbleHealthSetupState(Path("config.conf"), Path(".env"), {}, config_values, {}, "lastfm-user", auth, ["operational errors"], ["scrobble outage and recovery"])
    monitor._wizard_print_scrobble_health_setup_summary(state, "manual")
    output = capsys.readouterr().out
    assert "Dead period: 1200s - 20m" in output
    assert "Comparison interval: 300s - 5m" in output
    assert "Email outage and recovery alerts: disabled" in output
    assert "Email operational error alerts: enabled" in output
    assert "Webhook outage and recovery alerts: enabled" in output
    assert "Webhook operational error alerts: disabled" in output
    assert "Config destination: config.conf" in output
    assert "Dotenv destination: .env" in output
    assert "Install method: manual" in output


# Confirms focused setup reports when dotenv failure leaves the config saved
def test_scrobble_health_setup_reports_partial_persistence(monkeypatch, capsys):
    config_path = PROJECT_ROOT / "local" / f"test-scrobble-health-partial-{os.getpid()}.conf"
    env_path = PROJECT_ROOT / "local" / f"test-scrobble-health-partial-{os.getpid()}.env"
    auth = {"complete": True, "validated": False, "browser": None, "source": "private manual entry", "mount_required": False, "host_os": None}
    install_scrobble_setup_flow(monkeypatch, config_path, env_path, auth, (False,))
    monkeypatch.setattr(monitor, "update_dotenv_file", Mock(side_effect=OSError("write failed")))
    try:
        with pytest.raises(SystemExit) as error:
            monitor.run_scrobble_health_setup_wizard()
        assert error.value.code == 1
        assert config_path.is_file()
        output = capsys.readouterr().out
        assert "Configuration was saved but dotenv destination" in output
        assert "Setup remains incomplete" in output
        assert "Press Enter to accept the shown default. Ctrl+C cancels." in output
        assert "Secrets go to the dotenv file. Non-secret settings go to the config file." in output
        assert f"Detected install method: manual\nConfiguration:          {config_path}\nDotenv:                 {env_path}\n" in output
        assert "private-refresh-token" not in output
    finally:
        if config_path.exists():
            config_path.unlink()


# Confirms incomplete focused setup prints authentication before Doctor and monitoring
def test_scrobble_health_setup_orders_incomplete_authentication_steps(monkeypatch, capsys):
    config_path = PROJECT_ROOT / "local" / f"test-scrobble-health-incomplete-{os.getpid()}.conf"
    env_path = PROJECT_ROOT / "local" / f"test-scrobble-health-incomplete-{os.getpid()}.env"
    auth = {"complete": False, "validated": False, "browser": None, "source": "not configured", "mount_required": False, "host_os": None}
    install_scrobble_setup_flow(monkeypatch, config_path, env_path, auth, (False,))
    try:
        with pytest.raises(SystemExit) as error:
            monitor.run_scrobble_health_setup_wizard()
        assert error.value.code == 0
        output = capsys.readouterr().out
        auth_index = output.index("Authorize the user-owned Spotify app:")
        doctor_index = output.index("After authentication succeeds, verify scrobble health setup:")
        monitor_index = output.index("After Doctor passes, start scrobble health monitoring:")
        assert auth_index < doctor_index < monitor_index
        assert f"Guide: {monitor.SCROBBLE_AUTH_GUIDE_URL}" in output
    finally:
        for path in (config_path, env_path):
            if path.exists():
                path.unlink()


# Confirms successful focused Doctor can launch local scrobble monitoring
def test_scrobble_health_setup_offers_local_start_after_doctor(monkeypatch):
    config_path = PROJECT_ROOT / "local" / f"test-scrobble-health-start-{os.getpid()}.conf"
    env_path = PROJECT_ROOT / "local" / f"test-scrobble-health-start-{os.getpid()}.env"
    auth = {"complete": True, "validated": False, "source": "user-owned Spotify app with PKCE"}
    install_scrobble_setup_flow(monkeypatch, config_path, env_path, auth, (True, True))
    doctor_mock = Mock(return_value=0)
    launch_mock = Mock(return_value=0)
    monkeypatch.setattr(monitor, "_wizard_load_effective_setup", Mock(return_value=True))
    monkeypatch.setattr(monitor, "run_scrobble_health_doctor", doctor_mock)
    monkeypatch.setattr(monitor, "_wizard_launch_monitor", launch_mock)
    try:
        with pytest.raises(SystemExit) as error:
            monitor.run_scrobble_health_setup_wizard()
        assert error.value.code == 0
        doctor_mock.assert_called_once_with("lastfm-user", str(config_path), str(env_path))
        launch_mock.assert_called_once()
        arguments = launch_mock.call_args.args[0]
        mode_index = arguments.index("--monitor-mode")
        assert arguments[mode_index:mode_index + 2] == ["--monitor-mode", "scrobble_health"]
        assert arguments[-4:] == ["--config-file", str(config_path), "--env-file", str(env_path)]
    finally:
        for path in (config_path, env_path):
            if path.exists():
                path.unlink()


# Confirms focused setup can edit thresholds before saving
def test_scrobble_health_setup_review_edits_thresholds(monkeypatch):
    config_path = PROJECT_ROOT / "local" / f"test-scrobble-health-review-{os.getpid()}.conf"
    env_path = PROJECT_ROOT / "local" / f"test-scrobble-health-review-{os.getpid()}.env"
    auth = {"complete": True, "validated": False, "source": "user-owned Spotify app with PKCE"}
    install_scrobble_setup_flow(monkeypatch, config_path, env_path, auth, (False, False), choice_answers=(1, 1, 0), positive_answers=(120, 1200, 5, 180, 1800, 7))
    try:
        with pytest.raises(SystemExit) as error:
            monitor.run_scrobble_health_setup_wizard()
        assert error.value.code == 0
        content = config_path.read_text(encoding="utf-8")
        assert "SCROBBLE_HEALTH_CHECK_INTERVAL = 180" in content
        assert "SCROBBLE_HEALTH_DEAD_PERIOD = 1800" in content
        assert "SCROBBLE_HEALTH_MIN_UNMATCHED = 7" in content
    finally:
        for path in (config_path, env_path):
            if path.exists():
                path.unlink()


# Confirms explicit monitoring mode selection overrides either saved direction
def test_select_monitor_mode_supports_both_runtime_directions():
    assert monitor.select_monitor_mode("friend_activity") == "friend_activity"
    assert monitor.select_monitor_mode("scrobble_health", cli_mode="friend_activity") == "friend_activity"
    assert monitor.select_monitor_mode("friend_activity", cli_mode="scrobble_health") == "scrobble_health"


# Confirms an unknown saved monitoring mode fails clearly
def test_select_monitor_mode_rejects_unknown_value():
    with pytest.raises(ValueError, match="MONITOR_MODE must be"):
        monitor.select_monitor_mode("unknown")


# Confirms the removed scrobble health shortcut is rejected
def test_scrobble_health_shortcut_is_not_accepted():
    result = run_cli("--scrobble-health")
    assert result.returncode == 2
    assert "unrecognized arguments: --scrobble-health" in result.stderr


# Confirms the first check is visible while later routine checks require verbose mode
def test_scrobble_health_monitor_prints_first_check_and_hides_normal_repeats(monkeypatch, capsys):
    state = {"status": "healthy", "last_notification_at": 0.0, "broken_since": 0.0, "broken_latest_spotify_at": 0.0}
    evaluation = monitor.ScrobbleHealthEvaluation("healthy", latest_match_at=1000, latest_spotify_at=1000, latest_lastfm_at=1000)
    monkeypatch.setattr(monitor, "load_scrobble_health_state", lambda path: dict(state))
    monkeypatch.setattr(monitor, "spotify_get_recent_plays", lambda: [spotify_play(1000)])
    monkeypatch.setattr(monitor, "lastfm_get_recent_scrobbles", lambda username, api_key: [lastfm_scrobble(1000)])
    monkeypatch.setattr(monitor, "evaluate_scrobble_health", lambda spotify_plays, lastfm_scrobbles: evaluation)
    monkeypatch.setattr(monitor, "transition_scrobble_health_state", lambda current_state, current_evaluation: (dict(state), ""))
    monkeypatch.setattr(monitor, "SCROBBLE_HEALTH_CHECK_INTERVAL", 120)
    monkeypatch.setattr(monitor, "SCROBBLE_HEALTH_LOOKBACK", 21600)
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_REFRESH_TOKEN", "private-refresh-token")
    monkeypatch.setattr(monitor, "LASTFM_API_KEY", "private-api-key")
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor.time, "sleep", Mock(side_effect=[None, KeyboardInterrupt]))
    with pytest.raises(KeyboardInterrupt):
        monitor.spotify_monitor_scrobble_health("lastfm-user", Path("state.json"))
    output = capsys.readouterr().out
    assert "Scrobble health monitoring started for Last.fm profile lastfm-user" in output
    assert output.count("Running scrobble health check") == 1
    assert output.count("Scrobble health result: Healthy") == 1
    assert "Next check in 2 minutes" in output
    assert output.count("Timestamp:") == 2
    assert "Press Ctrl+C to stop.\n\nTimestamp:" in output
    assert "Next check in 2 minutes.\n\nTimestamp:" in output
    assert "private-refresh-token" not in output
    assert "private-api-key" not in output


# Confirms verbose mode displays routine checks after the first comparison
def test_scrobble_health_monitor_prints_repeated_checks_in_verbose_mode(monkeypatch, capsys):
    state = {"status": "idle", "last_notification_at": 0.0, "broken_since": 0.0, "broken_latest_spotify_at": 0.0}
    evaluation = monitor.ScrobbleHealthEvaluation("idle")
    monkeypatch.setattr(monitor, "load_scrobble_health_state", lambda path: dict(state))
    monkeypatch.setattr(monitor, "spotify_get_recent_plays", lambda: [])
    monkeypatch.setattr(monitor, "lastfm_get_recent_scrobbles", lambda username, api_key: [])
    monkeypatch.setattr(monitor, "evaluate_scrobble_health", lambda spotify_plays, lastfm_scrobbles: evaluation)
    monkeypatch.setattr(monitor, "transition_scrobble_health_state", lambda current_state, current_evaluation: (dict(state), ""))
    monkeypatch.setattr(monitor, "SCROBBLE_HEALTH_CHECK_INTERVAL", 120)
    monkeypatch.setattr(monitor, "SCROBBLE_HEALTH_LOOKBACK", 21600)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor.time, "sleep", Mock(side_effect=[None, KeyboardInterrupt]))
    with pytest.raises(KeyboardInterrupt):
        monitor.spotify_monitor_scrobble_health("lastfm-user", Path("state.json"))
    output = capsys.readouterr().out
    assert output.count("Running scrobble health check") == 2
    assert output.count("Scrobble health result: Idle") == 2
    assert output.count("Timestamp:") == 3
    assert "Spotify reported no completed plays from the last 6 hours" in output
    assert "nothing to compare with Last.fm yet" in output


# Confirms scrobble alerts format play dates and deliver notifications before the console timestamp
def test_scrobble_health_notification_matches_regular_alert_format(monkeypatch, capsys):
    timestamp_mock = Mock(side_effect=lambda prefix: print(f"{prefix}CONSOLE-TIMESTAMP"))
    delivery_mock = Mock(side_effect=lambda *args, **kwargs: print("Sending webhook notification"))
    monkeypatch.setattr(monitor, "get_cur_ts", lambda prefix="": f"{prefix}ALERT-TIMESTAMP")
    monkeypatch.setattr(monitor, "get_date_from_ts", lambda timestamp: f"PLAYED-{int(timestamp)}")
    monkeypatch.setattr(monitor, "print_cur_ts", timestamp_mock)
    monkeypatch.setattr(monitor, "send_notification_channels", delivery_mock)
    evaluation = monitor.ScrobbleHealthEvaluation("broken", (spotify_play(1000, "First"), spotify_play(1100, "Second")))
    monitor.send_scrobble_health_notification("lastfm-user", evaluation, "outage")
    outage_output = capsys.readouterr().out
    outage_body = delivery_mock.call_args.args[2]
    assert "oldest missing play was recorded by Spotify at PLAYED-1000" in outage_body
    assert "- PLAYED-1000 | Artist - First" in outage_body
    assert "- PLAYED-1100 | Artist - Second" in outage_body
    assert outage_body.endswith("Timestamp: ALERT-TIMESTAMP")
    assert "Timestamp: ALERT-TIMESTAMP" not in outage_output
    assert outage_output.index("Sending webhook notification") < outage_output.index("CONSOLE-TIMESTAMP")
    assert "Last.fm profile: https://www.last.fm/user/lastfm-user\nSending webhook notification\n\nTimestamp:" in outage_output

    delivery_mock.side_effect = None
    monitor.send_scrobble_health_notification("lastfm-user", monitor.ScrobbleHealthEvaluation("healthy"), "recovery")
    recovery_output = capsys.readouterr().out
    recovery_body = delivery_mock.call_args.args[2]
    assert "Spotify scrobbling is working again. A recent Spotify play was found on the Last.fm profile." in recovery_body
    assert recovery_body.endswith("Timestamp: ALERT-TIMESTAMP")
    assert "Profile: https://www.last.fm/user/lastfm-user\n\nTimestamp:" in recovery_output
    assert "\n\n\nTimestamp:" not in recovery_output
    assert [item.args for item in timestamp_mock.call_args_list] == [("\nTimestamp:\t\t\t",), ("\nTimestamp:\t\t\t",)]


# Confirms operational alerts include a timestamp and send before the console timestamp
def test_scrobble_health_monitor_formats_operational_error_notifications(monkeypatch, capsys):
    timestamp_mock = Mock(side_effect=lambda prefix: print(f"{prefix}CONSOLE-TIMESTAMP"))
    delivery_mock = Mock(side_effect=lambda *args, **kwargs: print("Sending webhook notification"))
    monkeypatch.setattr(monitor, "load_scrobble_health_state", lambda path: {})
    monkeypatch.setattr(monitor, "spotify_get_recent_plays", Mock(side_effect=RuntimeError("temporary failure")))
    monkeypatch.setattr(monitor, "get_cur_ts", lambda prefix="": f"{prefix}ALERT-TIMESTAMP")
    monkeypatch.setattr(monitor, "print_cur_ts", timestamp_mock)
    monkeypatch.setattr(monitor, "send_notification_channels", delivery_mock)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "webhook_event_enabled", lambda event: True)
    monkeypatch.setattr(monitor.time, "sleep", Mock(side_effect=[None, None, KeyboardInterrupt]))
    with pytest.raises(KeyboardInterrupt):
        monitor.spotify_monitor_scrobble_health("lastfm-user", Path("state.json"))
    output = capsys.readouterr().out
    assert delivery_mock.call_args.args[2].endswith("\n\nTimestamp: ALERT-TIMESTAMP")
    assert "comparison failed 3 consecutive times" in delivery_mock.call_args.args[2]
    assert output.count("Operational alert deferred until 3 consecutive check failures.") == 2
    assert delivery_mock.call_count == 1
    assert output.rindex("Sending webhook notification") < output.rindex("CONSOLE-TIMESTAMP")
    assert timestamp_mock.call_count == 4


# Confirms a successful comparison resets the operational alert failure counter
def test_scrobble_health_monitor_resets_operational_error_failures_after_success(monkeypatch, capsys):
    spotify_mock = Mock(side_effect=[RuntimeError("failure 1"), [], RuntimeError("failure 2"), RuntimeError("failure 3"), RuntimeError("failure 4")])
    delivery_mock = Mock()
    monkeypatch.setattr(monitor, "load_scrobble_health_state", lambda path: {})
    monkeypatch.setattr(monitor, "spotify_get_recent_plays", spotify_mock)
    monkeypatch.setattr(monitor, "lastfm_get_recent_scrobbles", lambda username, api_key: [])
    monkeypatch.setattr(monitor, "get_cur_ts", lambda prefix="": f"{prefix}ALERT-TIMESTAMP")
    monkeypatch.setattr(monitor, "print_cur_ts", Mock())
    monkeypatch.setattr(monitor, "send_notification_channels", delivery_mock)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "webhook_event_enabled", lambda event: True)
    monkeypatch.setattr(monitor.time, "sleep", Mock(side_effect=[None, None, None, None, KeyboardInterrupt]))
    with pytest.raises(KeyboardInterrupt):
        monitor.spotify_monitor_scrobble_health("lastfm-user", Path("state.json"))
    output = capsys.readouterr().out
    assert output.count("Scrobble health has 1 consecutive check failure.") == 2
    assert "Scrobble health has 3 consecutive check failures." in output
    assert delivery_mock.call_count == 1
    assert "comparison failed 3 consecutive times" in delivery_mock.call_args.args[2]


# Confirms scrobble health uses a smaller capped retry budget than Friend Activity
def test_scrobble_health_http_retries_are_bounded():
    assert monitor.retry.total == 5
    assert monitor.scrobble_health_retry.total == 1
    assert 429 not in monitor.scrobble_health_retry.status_forcelist


# Confirms Spotify's structured quota response preserves a bounded diagnostic delay
def test_scrobble_health_recognizes_spotify_quota_exhaustion():
    response = Mock(status_code=429, headers={"Retry-After": "7200"})
    response.json.return_value = {"error": {"status": 429, "message": "Too many requests", "reason": "QUOTA_EXCEEDED"}}
    with pytest.raises(monitor.SpotifyQuotaExceededError) as error:
        monitor.spotify_raise_scrobble_http_error(response)
    assert error.value.retry_after == 7200
    advice = monitor.classify_recovery_error(error.value, "scrobble_health")
    assert "increase --scrobble-check-interval" in advice.fix
    assert monitor.SPOTIFY_QUOTA_GUIDE_URL in advice.fix


# Confirms rate-limit guidance names the scrobble health interval option
def test_scrobble_health_rate_limit_guidance_uses_mode_specific_interval():
    response = Mock(status_code=429)
    error = monitor.req.HTTPError("429 Client Error", response=response)
    advice = monitor.classify_recovery_error(error, "scrobble_health")
    assert "--scrobble-check-interval" in advice.fix
    assert "-c or --check-interval" not in advice.fix


# Confirms a matched recent play produces a healthy comparison
def test_evaluate_scrobble_health_matches_metadata_and_timestamp():
    evaluation = monitor.evaluate_scrobble_health([spotify_play(900)], [lastfm_scrobble(905)], now=1000, dead_period=100, min_unmatched=5, match_window=30, lookback=1000)

    assert evaluation.status == "healthy"
    assert evaluation.unmatched == ()
    assert evaluation.latest_match_at == 900
    assert [(play.track, scrobble.track) for play, scrobble in evaluation.matches] == [("Track", "Track")]


# Confirms verbose history output identifies matched and unmatched Spotify plays
def test_render_scrobble_history_comparison_shows_both_sources(monkeypatch):
    matched_play = spotify_play(900, "Matched")
    missing_play = spotify_play(950, "Missing")
    matching_scrobble = lastfm_scrobble(905, "Matched")
    extra_scrobble = lastfm_scrobble(960, "Lastfm Only")
    monkeypatch.setattr(monitor, "SCROBBLE_HEALTH_LOOKBACK", 1000)
    monkeypatch.setattr(monitor, "SCROBBLE_HEALTH_MATCH_WINDOW", 30)
    evaluation = monitor.evaluate_scrobble_health([matched_play, missing_play], [matching_scrobble, extra_scrobble], now=1000, dead_period=100, min_unmatched=5, match_window=30, lookback=1000)
    output = monitor.render_scrobble_history_comparison([matched_play, missing_play], [matching_scrobble, extra_scrobble], evaluation, now=1000)
    assert "Comparison period: last" in output
    assert "may record different points in the same track's playback" in output
    assert "[MATCHED]" in output
    assert "Artist - Matched" in output
    assert "[NOT MATCHED]" in output
    assert "Artist - Missing" in output
    assert "Artist - Lastfm Only" in output
    assert monitor.format_scrobble_history_timestamp(float("inf")) == "timestamp inf"


# Confirms focused Doctor exposes listening history only when verbose output is selected
def test_scrobble_health_doctor_verbose_lists_recent_history(monkeypatch, capsys):
    current_time = time.time()
    spotify_plays = [spotify_play(current_time, "Diagnostic Track")]
    lastfm_scrobbles = [lastfm_scrobble(current_time, "Diagnostic Track")]
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_CLIENT_ID", "a" * 32)
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_REFRESH_TOKEN", "private-refresh-token")
    monkeypatch.setattr(monitor, "LASTFM_API_KEY", "private-api-key")
    monkeypatch.setattr(monitor, "doctor_check_environment", lambda: [])
    monkeypatch.setattr(monitor, "doctor_check_configuration", lambda config_path=None, env_path=None, startup_checks=(): [])
    monkeypatch.setattr(monitor, "doctor_check_notifications", lambda: [])
    monkeypatch.setattr(monitor, "doctor_check_webhook_notifications", lambda: [])
    monkeypatch.setattr(monitor, "spotify_get_recent_plays", lambda: spotify_plays)
    monkeypatch.setattr(monitor, "lastfm_get_recent_scrobbles", lambda username, api_key: lastfm_scrobbles)
    monkeypatch.setattr(monitor, "_doctor_offer_notification_tests", lambda report: [])
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    assert monitor.run_scrobble_health_doctor("lastfm-user") == 0
    concise_output = capsys.readouterr().out
    assert "Diagnostic Track" not in concise_output
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    assert monitor.run_scrobble_health_doctor("lastfm-user") == 0
    verbose_output = capsys.readouterr().out
    assert "Recent history comparison" in verbose_output
    assert "[MATCHED]" in verbose_output
    assert "Artist - Diagnostic Track" in verbose_output


# Confirms focused Doctor reports each live check while an interactive user waits
def test_scrobble_health_doctor_reports_interactive_progress(monkeypatch):
    stream = Mock()
    stream.isatty.return_value = True
    progress = Mock()
    clear_progress = Mock()
    monkeypatch.setattr(monitor.sys, "stdout", stream)
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_CLIENT_ID", "a" * 32)
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    monkeypatch.setattr(monitor, "SPOTIFY_SCROBBLE_REFRESH_TOKEN", "private-refresh-token")
    monkeypatch.setattr(monitor, "LASTFM_API_KEY", "private-api-key")
    monkeypatch.setattr(monitor, "doctor_check_environment", lambda: [])
    monkeypatch.setattr(monitor, "doctor_check_configuration", lambda config_path=None, env_path=None, startup_checks=(): [])
    monkeypatch.setattr(monitor, "doctor_check_notifications", lambda: [])
    monkeypatch.setattr(monitor, "doctor_check_webhook_notifications", lambda: [])
    monkeypatch.setattr(monitor, "spotify_get_recent_plays", lambda: [])
    monkeypatch.setattr(monitor, "lastfm_get_recent_scrobbles", lambda username, api_key: [])
    monkeypatch.setattr(monitor, "_doctor_offer_notification_tests", lambda report: [])
    monkeypatch.setattr(monitor, "_doctor_progress", progress)
    monkeypatch.setattr(monitor, "_doctor_progress_clear", clear_progress)
    assert monitor.run_scrobble_health_doctor("lastfm-user") == 0
    assert [call.args[0] for call in progress.call_args_list] == ["environment", "configuration", "Spotify recent plays", "Last.fm scrobbles", "notifications"]
    clear_progress.assert_called_once_with()


# Confirms matching tolerates Last.fm using an estimated track-start timestamp
def test_evaluate_scrobble_health_matches_estimated_track_start():
    evaluation = monitor.evaluate_scrobble_health([spotify_play(900)], [lastfm_scrobble(720)], now=1000, dead_period=100, min_unmatched=5, match_window=10, lookback=1000)

    assert evaluation.status == "healthy"


# Confirms isolated older misses stop counting after a newer confirmed match
def test_evaluate_scrobble_health_only_counts_trailing_unmatched_plays():
    plays = [spotify_play(500, "Missed"), spotify_play(600, "Matched"), spotify_play(700, "New")]
    scrobbles = [lastfm_scrobble(605, "Matched")]

    evaluation = monitor.evaluate_scrobble_health(plays, scrobbles, now=1000, dead_period=100, min_unmatched=2, match_window=30, lookback=1000)

    assert evaluation.status == "suspect"
    assert [play.track for play in evaluation.unmatched] == ["New"]


# Confirms the conservative default evidence count avoids a four-play outage alert
def test_evaluate_scrobble_health_requires_five_old_unmatched_plays():
    four_plays = [spotify_play(100 + index * 10, f"Track {index}") for index in range(4)]
    five_plays = [*four_plays, spotify_play(140, "Track 4")]

    suspect = monitor.evaluate_scrobble_health(four_plays, [], now=1000, dead_period=100, min_unmatched=5, match_window=30, lookback=1000)
    broken = monitor.evaluate_scrobble_health(five_plays, [], now=1000, dead_period=100, min_unmatched=5, match_window=30, lookback=1000)

    assert suspect.status == "suspect"
    assert broken.status == "broken"
    assert len(broken.unmatched) == 5


# Confirms a suspected outage remains below the alert threshold until its dead period passes
def test_evaluate_scrobble_health_requires_dead_period():
    plays = [spotify_play(900 + index * 10, f"Track {index}") for index in range(5)]

    evaluation = monitor.evaluate_scrobble_health(plays, [], now=950, dead_period=100, min_unmatched=5, match_window=30, lookback=1000)

    assert evaluation.status == "suspect"


# Confirms recovery needs a match newer than the last Spotify evidence from the outage
def test_transition_scrobble_health_state_requires_newer_confirmed_match():
    state = {"status": "broken", "last_notification_at": 1000.0, "broken_since": 1000.0, "broken_latest_spotify_at": 900.0}
    stale_healthy = monitor.ScrobbleHealthEvaluation("healthy", latest_match_at=800, latest_spotify_at=900)
    recovered = monitor.ScrobbleHealthEvaluation("healthy", latest_match_at=950, latest_spotify_at=950)

    unchanged, stale_action = monitor.transition_scrobble_health_state(state, stale_healthy, now=1100, repeat_interval=86400)
    next_state, recovery_action = monitor.transition_scrobble_health_state(state, recovered, now=1200, repeat_interval=86400)

    assert unchanged["status"] == "broken"
    assert stale_action == ""
    assert next_state["status"] == "healthy"
    assert recovery_action == "recovery"


# Confirms persisted outage state survives a restart without exposing secrets
def test_scrobble_health_state_round_trip():
    state_path = Path(__file__).resolve().parents[1] / "local" / f"test-scrobble-health-state-{os.getpid()}.json"
    state = {"status": "broken", "last_notification_at": 1000.0, "broken_since": 900.0, "broken_latest_spotify_at": 850.0}

    try:
        monitor.save_scrobble_health_state(state_path, state)
        assert monitor.load_scrobble_health_state(state_path) == state
        assert state_path.stat().st_mode & 0o777 == 0o600
    finally:
        if state_path.exists():
            state_path.unlink()
