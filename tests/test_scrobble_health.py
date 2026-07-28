import os
from pathlib import Path
from unittest.mock import Mock

import pytest

import spotify_monitor as monitor


# Builds one completed Spotify play with stable metadata
def spotify_play(timestamp, track="Track", artist="Artist"):
    return monitor.SpotifyPlay(float(timestamp), artist, track, 180000, f"spotify:track:{timestamp}")


# Builds one completed Last.fm scrobble with stable metadata
def lastfm_scrobble(timestamp, track="Track", artist="Artist"):
    return monitor.LastfmScrobble(float(timestamp), artist, track)


# Confirms silent PKCE authorization asks only for recent-play access
def test_spotify_get_scrobble_access_token_uses_cookie_and_minimal_scope(monkeypatch):
    auth_response = Mock(text='{"code":"authorization%2Fcode"}')
    auth_response.raise_for_status.return_value = None
    token_response = Mock()
    token_response.raise_for_status.return_value = None
    token_response.json.return_value = {"access_token": "scoped-token", "expires_in": 3600}
    session = Mock()
    session.get.return_value = auth_response
    session.post.return_value = token_response
    monkeypatch.setattr(monitor, "SP_CACHED_SCROBBLE_ACCESS_TOKEN", None)
    monkeypatch.setattr(monitor, "SP_SCROBBLE_ACCESS_TOKEN_EXPIRES_AT", 0)
    monkeypatch.setattr(monitor, "USER_AGENT", "test-agent")

    token = monitor.spotify_get_scrobble_access_token("private-cookie", session)

    assert token == "scoped-token"
    assert session.get.call_args.kwargs["params"]["scope"] == "user-read-recently-played"
    assert session.get.call_args.kwargs["headers"]["Cookie"] == "sp_dc=private-cookie"
    assert session.post.call_args.kwargs["data"]["code"] == "authorization/code"


# Confirms Spotify recent-play parsing keeps only completed track-shaped records
def test_spotify_get_recent_plays_parses_completed_tracks(monkeypatch):
    response = Mock(status_code=200)
    response.raise_for_status.return_value = None
    response.json.return_value = {"items": [{"played_at": "2026-07-28T10:00:00.000Z", "track": {"name": "Track", "artists": [{"name": "Artist"}], "duration_ms": 123000, "uri": "spotify:track:1"}}, {"played_at": "invalid", "track": {"name": "Ignored", "artists": [{"name": "Artist"}]}}]}
    session = Mock()
    session.get.return_value = response
    monkeypatch.setattr(monitor, "spotify_get_scrobble_access_token", lambda cookie, selected_session: "token")

    plays = monitor.spotify_get_recent_plays("cookie", session)

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
def test_scrobble_health_setup_wizard_writes_mode(monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "local" / f"test-scrobble-health-setup-{os.getpid()}.conf"
    env_path = project_root / "local" / f"test-scrobble-health-setup-{os.getpid()}.env"
    answers = iter((False, True))
    monkeypatch.setattr(monitor.sys, "stdin", Mock(isatty=Mock(return_value=True)))
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "manual")
    monkeypatch.setattr(monitor, "_wizard_destinations", lambda config_file, env_file, method=None: (config_path, env_path))
    monkeypatch.setattr(monitor, "_wizard_choose_config_destination", lambda path: path)
    monkeypatch.setattr(monitor, "_wizard_ask_text", lambda question, default="", required=False: "lastfm-user")
    monkeypatch.setattr(monitor, "_wizard_ask_positive_int", lambda question, default: default)
    monkeypatch.setattr(monitor, "_wizard_existing_secret", lambda key, path: True)
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=True: next(answers))
    monkeypatch.setattr(monitor, "_wizard_collect_cookie_auth", lambda method, path, updates: {"complete": True, "browser": None, "source": "existing SP_DC_COOKIE"})
    monkeypatch.setattr(monitor, "_wizard_collect_email", lambda values, updates, path: [])
    monkeypatch.setattr(monitor, "_wizard_collect_webhook", lambda values, updates, path: [])

    try:
        with pytest.raises(SystemExit) as exc_info:
            monitor.run_scrobble_health_setup_wizard()
        content = config_path.read_text(encoding="utf-8")
        assert exc_info.value.code == 0
        assert 'MONITOR_MODE = "scrobble_health"' in content
        assert 'LASTFM_USERNAME = "lastfm-user"' in content
        assert "SCROBBLE_HEALTH_MIN_UNMATCHED = 5" in content
    finally:
        for path in (config_path, env_path):
            if path.exists():
                path.unlink()


# Confirms a matched recent play produces a healthy comparison
def test_evaluate_scrobble_health_matches_metadata_and_timestamp():
    evaluation = monitor.evaluate_scrobble_health([spotify_play(900)], [lastfm_scrobble(905)], now=1000, dead_period=100, min_unmatched=5, match_window=30, lookback=1000)

    assert evaluation.status == "healthy"
    assert evaluation.unmatched == ()
    assert evaluation.latest_match_at == 900


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
