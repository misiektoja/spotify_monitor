"""Offline coverage for selectable Spotify activity sources and live playback state."""

import copy
import errno
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
import requests
from requests.adapters import HTTPAdapter

import spotify_monitor as monitor
from test_monitoring_loop import LoopStopped, loop_environment as loop_environment
from test_doctor import run_cli


TRACK_URI = "spotify:track:4cOdK2wGLETKBW3PvgPWqT"
OTHER_TRACK_URI = "spotify:track:4N1MFKjziFHH4IS3RYYUrU"
THIRD_TRACK_URI = "spotify:track:0123456789abcdefghijkl"
USER_URI = "spotify:user:watched-user"


# Verifies the CLI overrides saved activity sources without modifying the configuration
@pytest.mark.parametrize("saved,override,expected", [("buddylist", None, "buddylist"), ("buddylist", "listening_activity", "listening_activity"), ("listening_activity", "buddylist", "buddylist"), ("invalid", "buddylist", "buddylist")])
def test_backend_cli_precedence(tmp_path, saved, override, expected):
    config = tmp_path / "monitor.conf"
    content = f'FRIEND_ACTIVITY_BACKEND = "{saved}"\n'
    config.write_text(content, encoding="utf-8")
    arguments = ["--config-file", str(config), "--env-file", "none", "--doctor"]
    if override is not None:
        arguments.extend(["--friend-activity-backend", override])
    result = run_cli(arguments, "runtime['run_doctor'] = lambda *args, **kwargs: (print('SELECTED_BACKEND=' + runtime['FRIEND_ACTIVITY_BACKEND']), 0)[1];")
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"SELECTED_BACKEND={expected}" in result.stdout
    assert config.read_text(encoding="utf-8") == content


# Rejects unsupported activity source names before startup
def test_backend_cli_invalid_choice():
    result = run_cli(["--friend-activity-backend", "invalid"])
    assert result.returncode == 2
    assert "invalid choice" in result.stderr


# Rejects runtime backend overrides in early commands that do not apply them
@pytest.mark.parametrize("command", ["--setup", "--set-sp-dc", "--set-webhook-url"])
def test_backend_cli_early_command_conflict(command):
    result = run_cli([command, "--friend-activity-backend", "buddylist"])
    assert result.returncode == 2
    assert f"{command} cannot be combined with --friend-activity-backend" in result.stderr


# Builds the sparse entity shape returned by the listening activity feed
def feed_entity(timestamp: float = 1_700_000_000, playing=True, track=TRACK_URI, kind="followEntity", user=USER_URI):
    return {kind: {"uri": user, "activity": {"entityUri": track, "isPlaying": playing, "timestamp": datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")}}}


# Builds a successful HTTP response carrying one selected payload
def response_for(payload, status=200):
    response = Mock(status_code=status)
    response.json.return_value = payload
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}", response=response)
    return response


# Selects live activity with fresh metadata state for every test
@pytest.fixture(autouse=True)
def live_backend(monkeypatch):
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", "listening_activity")
    monkeypatch.setattr(monitor, "SP_ACTIVITY_METADATA_CACHE", {})


# Confirms old configuration files inherit the live default and an explicit legacy choice survives rendering
def test_backend_configuration_default_and_round_trip():
    defaults = monitor.parse_config_content(monitor.CONFIG_BLOCK)
    assert defaults["FRIEND_ACTIVITY_BACKEND"] == "listening_activity"
    defaults.update(monitor.parse_config_content('TOKEN_SOURCE = "cookie"'))
    assert defaults["FRIEND_ACTIVITY_BACKEND"] == "listening_activity"
    defaults["FRIEND_ACTIVITY_BACKEND"] = "buddylist"
    rendered = monitor.generate_config_with_current_values(defaults)
    assert monitor.parse_config_content(rendered)["FRIEND_ACTIVITY_BACKEND"] == "buddylist"


# Verifies activity requests and token checks share the selected method and request policy
@pytest.mark.parametrize("backend,method", [("listening_activity", "post"), ("buddylist", "get")])
@pytest.mark.parametrize("token_source", ["cookie", "client"])
def test_selected_endpoint_is_used_for_activity_and_token_validation(monkeypatch, backend, method, token_source):
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", backend)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", token_source)
    monkeypatch.setattr(monitor, "VERIFY_SSL", False)
    monkeypatch.setattr(monitor, "SP_CACHED_CLIENT_ID", "client-id")
    monkeypatch.setattr(monitor, "USER_AGENT", "test-agent")
    transport = Mock()
    result = {"entities": []} if backend == "listening_activity" else {"friends": []}
    getattr(transport, method).return_value = response_for(result)
    monkeypatch.setattr(monitor, "SESSION", transport)
    assert monitor.spotify_get_friends_json("test-token") == {"friends": []}
    call = getattr(transport, method).call_args
    assert call.args == (monitor.spotify_activity_endpoint()[0],)
    assert call.kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert ("Client-Id" in call.kwargs["headers"]) == (token_source == "cookie")
    assert call.kwargs["timeout"] == monitor.FUNCTION_TIMEOUT
    assert call.kwargs["verify"] is False
    assert call.kwargs["allow_redirects"] is False
    if method == "post":
        assert call.kwargs["json"] == {"unused": True, "resultLimit": 100}
        transport.get.assert_not_called()
    else:
        assert "json" not in call.kwargs
        transport.post.assert_not_called()
    token_request = Mock(return_value=response_for({}))
    other_request = Mock(side_effect=AssertionError("wrong activity method"))
    monkeypatch.setattr(monitor.req, method, token_request)
    monkeypatch.setattr(monitor.req, "get" if method == "post" else "post", other_request)
    assert monitor.check_token_validity("test-token", "client-id", "test-agent")
    assert token_request.call_args == call


# Keeps OAuth metadata token validation independent of the activity selection
def test_oauth_validation_keeps_its_get_endpoint(monkeypatch):
    get = Mock(return_value=response_for({}, 403))
    monkeypatch.setattr(monitor.req, "get", get)
    monkeypatch.setattr(monitor.req, "post", Mock(side_effect=AssertionError("activity request")))
    assert monitor.check_token_validity("token", oauth_app=True)
    assert get.call_args.args[0].startswith("https://api.spotify.com/v1/tracks/")


# An anonymous token cannot validate a cookie even when the selected feed accepts it
def test_cookie_refresh_rejects_anonymous_tokens(monkeypatch):
    session = Mock()
    session.get.return_value = response_for({"accessToken": "anonymous-token", "isAnonymous": True, "clientId": "client", "accessTokenExpirationTimestampMs": 1_800_000_000_000})
    monkeypatch.setattr(monitor.req, "Session", Mock(return_value=session))
    monkeypatch.setattr(monitor, "fetch_server_time", Mock(return_value=1_700_000_000))
    monkeypatch.setattr(monitor, "check_token_validity", Mock(return_value=True))
    with pytest.raises(ValueError, match="anonymous token"):
        monitor.refresh_access_token_from_sp_dc("invalid-cookie")
    assert session.get.call_count == 2


# The init fallback may still authenticate a cookie after an anonymous transport response
def test_cookie_init_fallback_can_replace_anonymous_transport(monkeypatch):
    session = Mock()
    common = {"clientId": "client", "accessTokenExpirationTimestampMs": 1_800_000_000_000}
    session.get.side_effect = [response_for({**common, "accessToken": "anonymous-token", "isAnonymous": True}), response_for({**common, "accessToken": "authenticated-token", "isAnonymous": False})]
    monkeypatch.setattr(monitor.req, "Session", Mock(return_value=session))
    monkeypatch.setattr(monitor, "fetch_server_time", Mock(return_value=1_700_000_000))
    monkeypatch.setattr(monitor, "check_token_validity", Mock(return_value=True))
    assert monitor.refresh_access_token_from_sp_dc("valid-cookie")["access_token"] == "authenticated-token"


# Public metadata can continue obtaining anonymous tokens without supplying a cookie
def test_anonymous_metadata_tokens_remain_supported(monkeypatch):
    session = Mock()
    session.get.return_value = response_for({"accessToken": "anonymous-token", "isAnonymous": True, "accessTokenExpirationTimestampMs": 1_800_000_000_000})
    monkeypatch.setattr(monitor.req, "Session", Mock(return_value=session))
    monkeypatch.setattr(monitor, "fetch_server_time", Mock(return_value=1_700_000_000))
    assert monitor.refresh_access_token_from_sp_dc("")["access_token"] == "anonymous-token"
    assert session.get.call_count == 1


# Rejects invalid source selections before sending an authenticated request
@pytest.mark.parametrize("backend", ["", "auto", None, [], "https://example.test/feed"])
def test_invalid_backend_does_not_send_credentials(monkeypatch, backend):
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", backend)
    transport = Mock()
    monkeypatch.setattr(monitor, "SESSION", transport)
    with pytest.raises(ValueError, match="FRIEND_ACTIVITY_BACKEND"):
        monitor.spotify_get_friends_json("token")
    assert not transport.mock_calls
    checks = monitor.doctor_check_authentication(monitor.DoctorReport([]))
    assert checks[0].status == "SKIP"


# Normalizes both entity variants without losing timezone precision or optional playback fields
def test_normalization_merges_duplicate_users_and_keeps_newest_activity():
    older = feed_entity(1_700_000_000)
    newer = feed_entity(1_700_000_030.125, kind="userEntity")
    payload = {"entities": [older, newer, feed_entity(user="spotify:artist:ignored"), {"recommendationEntity": {}}]}
    original = copy.deepcopy(payload)
    result = monitor.spotify_normalize_listening_activity(payload)
    assert payload == original
    assert len(result["friends"]) == 1
    friend = result["friends"][0]
    assert friend["timestamp"] == 1_700_000_030_125
    assert friend["isPlaying"] is True
    assert friend["track"]["context"] == {"uri": "", "name": ""}
    found, info = monitor.spotify_get_friend_info(result, "watched-user")
    assert found
    assert info["sp_is_playing"] is True
    assert info["sp_ts"] == 1_700_000_030
    assert info["sp_track_uri"] == TRACK_URI


# Treats unsupported media and users without shared activity as absent music activity
def test_nonmusic_and_missing_activity_are_skipped():
    result = monitor.spotify_normalize_listening_activity({"entities": [feed_entity(track="spotify:episode:example"), {"userEntity": {"uri": USER_URI}}]})
    assert result == {"friends": []}


# Reports malformed feed responses instead of turning them into apparent target disappearance
@pytest.mark.parametrize("payload", [None, [], {}, {"entities": None}, {"entities": [None]}, {"entities": [{"followEntity": []}]}])
def test_malformed_feed_is_not_an_empty_success(payload):
    with pytest.raises(ValueError, match="Spotify listening activity"):
        monitor.spotify_normalize_listening_activity(payload)


# Rejects unusable activity values before monitoring or date rendering consumes them
@pytest.mark.parametrize("key,value", [("timestamp", None), ("timestamp", "2026-09-15T12:00:00"), ("timestamp", "invalid"), ("timestamp", "0001-01-01T00:00:00Z"), ("isPlaying", "false"), ("entityUri", "spotify:track:bad"), ("contextUri", [])])
def test_malformed_activity_fields_are_rejected(key, value):
    entity = feed_entity()
    entity["followEntity"]["activity"][key] = value
    with pytest.raises(ValueError, match="malformed"):
        monitor.spotify_normalize_listening_activity({"entities": [entity]})


# Leaves endpoint failures visible without silently switching to legacy activity
@pytest.mark.parametrize("status", [302, 401, 403, 429, 500])
def test_feed_errors_do_not_fall_back(monkeypatch, status):
    transport = Mock()
    transport.post.return_value = response_for({}, status)
    monkeypatch.setattr(monitor, "SESSION", transport)
    with pytest.raises(Exception, match="HTTP|401 Unauthorized"):
        monitor.spotify_get_friends_json("token")
    transport.get.assert_not_called()


# Keeps POST retries restricted to the read-only feed path
def test_feed_has_bounded_post_retries():
    adapter = monitor.SESSION.get_adapter(monitor.SPOTIFY_LISTENING_ACTIVITY_URL)
    assert isinstance(adapter, HTTPAdapter)
    assert adapter.max_retries.allowed_methods is not None
    assert "POST" in adapter.max_retries.allowed_methods
    assert adapter.max_retries.total == 5
    other_adapter = monitor.SESSION.get_adapter("https://spclient.wg.spotify.com/unrelated")
    assert isinstance(other_adapter, HTTPAdapter)
    assert other_adapter.max_retries.allowed_methods is not None
    assert "POST" not in other_adapter.max_retries.allowed_methods


# Resolves missing names once and keeps track metadata separate from activity visibility
def test_metadata_enrichment_uses_profile_and_playlist_cache(monkeypatch):
    profile = Mock(return_value=response_for({"name": "Visible Friend"}))
    playlist = Mock(return_value={"sp_playlist_name": "Visible Playlist"})
    monkeypatch.setattr(monitor.SESSION, "get", profile)
    monkeypatch.setattr(monitor, "spotify_get_playlist_info_web", playlist)
    entity = feed_entity()
    entity["followEntity"]["activity"]["contextUri"] = "spotify:playlist:1234567890abcdefghijkl"
    result = monitor.spotify_normalize_listening_activity({"entities": [entity]})
    _, info = monitor.spotify_get_friend_info(result, "watched-user")
    track = {"sp_track_name": "Track", "sp_artist_name": "Artist", "sp_album_name": "Album", "sp_album_uri": "spotify:album:example"}
    monitor.spotify_complete_live_activity(info, "token", track)
    monitor.spotify_complete_live_activity(info, "token", track)
    assert info["sp_username"] == "Visible Friend"
    assert info["sp_playlist"] == "Visible Playlist"
    assert info["sp_track"] == "Track"
    assert profile.call_count == playlist.call_count == 1
    assert profile.call_args.kwargs["allow_redirects"] is False


# A missing profile name keeps the known Spotify user ID usable
def test_optional_profile_failure_keeps_user_visible(monkeypatch):
    monkeypatch.setattr(monitor.SESSION, "get", Mock(side_effect=requests.Timeout()))
    assert monitor.spotify_activity_metadata("user", USER_URI, "token") == ""
    assert monitor.SP_ACTIVITY_METADATA_CACHE == {}


# Optional metadata cannot hide an exhausted local descriptor limit
def test_optional_profile_resource_exhaustion_stops(monkeypatch):
    monkeypatch.setattr(monitor.SESSION, "get", Mock(side_effect=OSError(errno.EMFILE, "Too many open files")))
    with pytest.raises(SystemExit) as error:
        monitor.spotify_activity_metadata("user", USER_URI, "token")
    assert error.value.code == 1


# Listing resolves live metadata and reports playback state without relying on the legacy feed
def test_list_live_friends_resolves_names_and_now_playing(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "spotify_get_track_info", live_track_info)
    monkeypatch.setattr(monitor, "spotify_activity_metadata", lambda kind, uri, token: "Visible Friend")
    feed = monitor.spotify_normalize_listening_activity({"entities": [feed_entity()]})
    monitor.spotify_list_friends(feed, "token")
    output = capsys.readouterr().out
    assert "Visible Friend" in output
    assert "Now playing:" in output
    assert "Artist - First" in output
    assert "Album" in output


# Doctor validates the live feed without requiring metadata access
def test_doctor_reuses_live_feed_for_target_visibility(monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", "test-cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", Mock(return_value="token"))
    post = Mock(return_value=response_for({"entities": [feed_entity()]}))
    monkeypatch.setattr(monitor.SESSION, "post", post)
    monkeypatch.setattr(monitor.SESSION, "get", Mock(side_effect=AssertionError("metadata should not be needed")))
    report = monitor.DoctorReport([])
    checks = monitor.doctor_check_authentication(report)
    assert checks[-1].status == "PASS"
    assert "listening_activity" in checks[-1].detail
    assert monitor.doctor_check_target(report, "watched-user")[0].status == "PASS"
    assert post.call_count == 1


# Supplies complete public track details without contacting Spotify
def live_track_info(token, uri):
    return {"sp_track_duration": 1000 if uri == THIRD_TRACK_URI else 200, "sp_track_name": {TRACK_URI: "First", OTHER_TRACK_URI: "Second", THIRD_TRACK_URI: "Third"}[uri], "sp_track_uri": uri, "sp_track_url": "https://open.spotify.com/track/example", "sp_artist_name": "Artist", "sp_artist_uri": "spotify:artist:example", "sp_artist_url": "https://open.spotify.com/artist/example", "sp_album_name": "Album", "sp_album_uri": "spotify:album:example", "sp_album_url": "https://open.spotify.com/album/example", "sp_album_image_url": ""}


# Runs selected live snapshots through the real monitoring loop
def run_live_snapshots(monkeypatch, harness, snapshots, csv_file_name=""):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SPOTIFY_INACTIVITY_CHECK", 45)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", Mock(return_value="token"))
    monkeypatch.setattr(monitor, "spotify_get_track_info", live_track_info)
    monkeypatch.setattr(monitor, "spotify_activity_metadata", lambda kind, uri, token: "Friend")
    payloads = [monitor.spotify_normalize_listening_activity({"entities": [snapshot]}) for snapshot in snapshots]
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=payloads))
    harness.stop_after = len(snapshots) - 1
    with pytest.raises(LoopStopped):
        monitor.spotify_monitor_friend_uri("watched-user", set(), csv_file_name)


# Same-track playing and pause updates neither add songs nor expire an ongoing long track
def test_live_pause_resume_and_timestamps_do_not_duplicate_tracks(loop_environment, monkeypatch, capsys):
    now = loop_environment.now
    snapshots = [feed_entity(now - 600), feed_entity(now), feed_entity(now + 30, playing=False), feed_entity(now + 60)]
    run_live_snapshots(monkeypatch, loop_environment, snapshots)
    output = capsys.readouterr().out
    assert "Now playing:" in output
    assert output.count("Songs played:") == 1
    assert f"User PAUSED playing after 30 seconds\nLast activity:\t\t\t{monitor.get_date_from_ts(now + 30)}\n\nTimestamp:" in output
    assert "User RESUMED playing after 30 seconds\n\nTimestamp:" in output
    assert "(estimated)" not in output
    assert "Songs played:\t\t\t1 (0 seconds)" in output
    assert "INACTIVE" not in output
    assert "Played for:" not in output


# A paused startup must not produce activity events or start local playback
@pytest.mark.parametrize("age", [0, 30, 300])
def test_live_paused_startup_has_no_activity_side_effects(loop_environment, monkeypatch, tmp_path, capsys, age):
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    delivery = Mock()
    monkeypatch.setattr(monitor, "send_notification_channels", delivery)
    monkeypatch.setattr(monitor, "TRACK_SONGS", True)
    playback = Mock()
    for name in ("spotify_macos_play_song", "spotify_win_play_song", "spotify_linux_play_song"):
        monkeypatch.setattr(monitor, name, playback)
    timestamp = loop_environment.now - age
    destination = tmp_path / "observed.csv"
    run_live_snapshots(monkeypatch, loop_environment, [feed_entity(timestamp, playing=False), feed_entity(timestamp, playing=False)], str(destination))
    output = capsys.readouterr().out
    assert "Playback:\t\t\tNot playing" in output
    assert "currently ACTIVE" not in output
    assert "Friend got ACTIVE" not in output
    assert "Songs played:" not in output
    delivery.assert_not_called()
    playback.assert_not_called()
    assert len(destination.read_text().splitlines()) == 1


# First observed playback of a paused startup track must open a session even with an unchanged timestamp
def test_live_first_playback_after_paused_startup_opens_session(loop_environment, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    delivery = Mock(return_value=(True, False))
    monkeypatch.setattr(monitor, "send_notification_channels", delivery)
    timestamp = loop_environment.now - 30
    destination = tmp_path / "observed.csv"
    snapshots = [feed_entity(timestamp, playing=False), feed_entity(timestamp, playing=False), feed_entity(timestamp)]
    run_live_snapshots(monkeypatch, loop_environment, snapshots, str(destination))
    output = capsys.readouterr().out
    assert "currently ACTIVE" not in output
    assert output.count("Friend got ACTIVE") == 1
    assert "Now playing:" in output
    # The stale paused timestamp is not evidence of when playback resumed, so the session starts at the sample
    assert "Songs played:\t\t\t1 (0 seconds)" in output
    delivery.assert_called_once()
    assert delivery.call_args.args[0] == "active"
    assert "Now playing:" in delivery.call_args.args[2]
    assert len(destination.read_text().splitlines()) == 2


# A track first seen at startup reports its played time without a skip label
def test_live_track_change_reports_partial_startup_track_without_skip(loop_environment, monkeypatch, capsys):
    now = loop_environment.now
    snapshots = [feed_entity(now), feed_entity(now), feed_entity(now + 1, track=OTHER_TRACK_URI)]
    run_live_snapshots(monkeypatch, loop_environment, snapshots)
    output = capsys.readouterr().out
    assert "Artist - Second" in output
    assert "Songs played:\t\t\t2 (1 second)" in output
    assert "SKIPPED" not in output
    assert "Played for:" not in output
    assert "User played the previous track for: 1 second (out of 3 minutes, 20 seconds) (0%)\n─" in output
    assert output.index("User played the previous track for:") < output.index("Spotify user:")


# Stopped playback ends after the inactivity timer and a same-track restart opens one session
def test_live_inactivity_and_same_track_restart(loop_environment, monkeypatch, capsys):
    now = loop_environment.now
    snapshots = [feed_entity(now), feed_entity(now, playing=False), feed_entity(now, playing=False), feed_entity(now, playing=False), feed_entity(now)]
    run_live_snapshots(monkeypatch, loop_environment, snapshots)
    output = capsys.readouterr().out
    assert output.count("Friend got INACTIVE") == 1
    assert output.count("Friend got ACTIVE") == 1
    assert "User played the last track for: 0 seconds (out of 3 minutes, 20 seconds) (0%)\n─" in output
    assert "*** User played 1 songs" in output
    assert "User paused music" not in output
    assert "Songs played:\t\t\t2" not in output


# Fresh paused timestamps and track changes cannot open a session without observed playback
def test_recent_stopped_activity_does_not_start_a_session(loop_environment, monkeypatch, capsys):
    now = loop_environment.now
    snapshots = [feed_entity(now - 300, playing=False), feed_entity(now, playing=False, track=OTHER_TRACK_URI)]
    run_live_snapshots(monkeypatch, loop_environment, snapshots)
    output = capsys.readouterr().out
    assert "Friend got ACTIVE" not in output
    assert "Last played:" in output
    assert "Now playing:" not in output
    assert "Songs played:" not in output


# Feed timestamps time the pause, resume and next-track boundaries while pauses are excluded from played time
def test_live_timing_uses_feed_timestamps_and_subtracts_pauses():
    timing = monitor.LivePlaybackTiming()
    timing.observe(1000, True, 60, 990)
    timing.start_track(1000, False, new_session=True, source_ts=990, duration=200, max_gap=60)
    assert timing.track_started_at == timing.session_started_at == 990
    timing.observe(1030, True, 60, 990)
    assert timing.observe(1060, False, 60, 1050) == ("paused", 60)
    timing.observe(1090, False, 60, 1050)
    assert timing.observe(1120, True, 60, 1110) == ("resumed", 60)
    timing.observe(1150, True, 60, 1110)
    assert timing.played_seconds(1150) == 100
    assert (timing.pauses, timing.paused_seconds) == (1, 60)
    timing.observe(1180, True, 60, 1170, track_changed=True)
    assert timing.track_seconds == 120
    assert timing.played_for(200, 1, allow_skip=True) == ("2 minutes (out of 3 minutes, 20 seconds) (60%)", False, True)
    timing.start_track(1180, True, source_ts=1170, duration=200, max_gap=60)
    assert timing.precise and timing.track_started_at == 1170
    timing.observe(1210, True, 60, 1170)
    timing.observe(1240, True, 60, 1230, track_changed=True)
    assert timing.track_seconds == 60
    assert timing.played_for(200, 1, allow_skip=True) == ("1 minute (out of 3 minutes, 20 seconds) - SKIPPED (30%)", True, True)
    timing.start_track(1240, True, source_ts=1230, duration=200, max_gap=60)
    for sample in range(1270, 1441, 30):
        timing.observe(sample, True, 60, 1230)
    assert timing.played_seconds(1440) == 210
    timing.observe(1470, True, 60, 1431, track_changed=True)
    assert timing.played_for(200, 1) == ("3 minutes, 21 seconds", False, False)


# Unchanged or future feed timestamps fall back to local sample times and mark the track imprecise
def test_live_timing_ignores_untrusted_feed_timestamps():
    timing = monitor.LivePlaybackTiming()
    timing.observe(1000, True, 60, 1000)
    timing.start_track(1000, False, new_session=True, source_ts=1000, duration=200, max_gap=60)
    assert timing.observe(1030, False, 60, 1000) == ("paused", 0)
    assert timing.observe(1060, True, 60, 1000) == ("resumed", 60)
    timing.observe(1090, True, 60, 1160, track_changed=True)
    assert timing.track_seconds == 30
    assert not timing.precise


# Missing observations and backward clock changes invalidate skip classification without inventing playback time
@pytest.mark.parametrize("next_sample", [1300, 1040])
def test_live_timing_gaps_disable_skip_estimates(next_sample):
    timing = monitor.LivePlaybackTiming()
    timing.observe(1000, True, 60, 990)
    timing.start_track(1000, False, new_session=True, source_ts=990, duration=200, max_gap=60)
    timing.observe(1030, True, 60, 1020, track_changed=True)
    timing.start_track(1030, True, source_ts=1020, duration=200, max_gap=60)
    assert timing.start_observed and timing.precise
    timing.observe(1060, True, 60, 1020)
    timing.observe(next_sample, True, 60, 1020)
    assert timing.played_seconds(next_sample) == 40
    assert not timing.start_observed and not timing.precise
    timing.observe(next_sample + 30, True, 60, next_sample + 20, track_changed=True)
    assert timing.track_seconds == 60
    assert timing.played_for(200, 31, allow_skip=True) == ("1 minute (out of 3 minutes, 20 seconds) (30%)", False, True)


# Supplies track durations matching a real three-track listening session
def session_track_info(token, uri):
    info = live_track_info(token, uri)
    info["sp_track_duration"] = {TRACK_URI: 202, OTHER_TRACK_URI: 239, THIRD_TRACK_URI: 268}[uri]
    return info


# Played time follows the feed's track-start timestamps rather than polling moments, so fully played tracks are not reported as cut short
def test_live_full_tracks_follow_feed_timestamps(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "spotify_get_track_info", session_track_info)
    now = loop_environment.now
    starts = [(now - 5, TRACK_URI), (now + 198, OTHER_TRACK_URI), (now + 438, THIRD_TRACK_URI)]
    snapshots = []
    # The loop processes the first two snapshots at the same moment, then one per polling interval
    for sample in range(17):
        sampled_at = now if sample == 0 else now + 30 * (sample - 1)
        started, track = [entry for entry in starts if entry[0] <= sampled_at][-1]
        snapshots.append(feed_entity(started, track=track))
    run_live_snapshots(monkeypatch, loop_environment, snapshots)
    output = capsys.readouterr().out
    assert "User played the previous track for" not in output
    assert "Songs played:\t\t\t2 (3 minutes, 23 seconds)" in output
    assert "Songs played:\t\t\t3 (7 minutes, 23 seconds)" in output


# Cut-short tracks are measured between feed timestamps and only observed starts can be skipped
def test_live_cut_short_tracks_use_feed_timestamps(loop_environment, monkeypatch, capsys):
    now = loop_environment.now
    # Track changes are noticed 20 and 5 seconds after the feed timestamps, so local sample times alone would report 60 and 90 seconds
    snapshots = [feed_entity(now - 5), feed_entity(now - 5), feed_entity(now - 5), feed_entity(now + 40, track=OTHER_TRACK_URI), feed_entity(now + 40, track=OTHER_TRACK_URI), feed_entity(now + 40, track=OTHER_TRACK_URI), feed_entity(now + 145, track=THIRD_TRACK_URI)]
    run_live_snapshots(monkeypatch, loop_environment, snapshots)
    output = capsys.readouterr().out
    assert "User played the previous track for: 45 seconds (out of 3 minutes, 20 seconds) (22%)" in output
    assert "User played the previous track for: 1 minute, 45 seconds (out of 3 minutes, 20 seconds) - SKIPPED (52%)" in output
    assert "Songs played:\t\t\t2 (45 seconds)" in output
    assert "Songs played:\t\t\t3 (2 minutes, 30 seconds)" in output


# Skips belong to the previous track and inactive reports summarize the last track, pauses and skips
def test_live_skips_follow_previous_track_and_inactive_report_summarizes_session(loop_environment, monkeypatch, tmp_path, capsys):
    for setting in ("ACTIVE_NOTIFICATION", "SONG_NOTIFICATION", "INACTIVE_NOTIFICATION"):
        monkeypatch.setattr(monitor, setting, True)
    delivery = Mock(return_value=(True, False))
    monkeypatch.setattr(monitor, "send_notification_channels", delivery)
    now = loop_environment.now
    snapshots = [
        feed_entity(now),
        feed_entity(now),
        feed_entity(now, track=OTHER_TRACK_URI),
        feed_entity(now, track=OTHER_TRACK_URI),
        feed_entity(now, playing=False, track=OTHER_TRACK_URI),
        feed_entity(now, track=OTHER_TRACK_URI),
        feed_entity(now, track=THIRD_TRACK_URI),
        feed_entity(now, playing=False, track=THIRD_TRACK_URI),
        feed_entity(now, playing=False, track=THIRD_TRACK_URI),
        feed_entity(now, playing=False, track=THIRD_TRACK_URI),
    ]
    destination = tmp_path / "observed.csv"
    run_live_snapshots(monkeypatch, loop_environment, snapshots, str(destination))
    output = capsys.readouterr().out
    assert "User played the previous track for: 30 seconds (out of 3 minutes, 20 seconds) (15%)\n─" in output
    assert "User played the previous track for: 1 minute (out of 3 minutes, 20 seconds) - SKIPPED (30%)\n─" in output
    assert output.count("SKIPPED") == 1
    assert "User PAUSED playing after 1 minute\nLast activity:\t\t\t" in output
    assert "User RESUMED playing after 1 minute\n\nTimestamp:" in output
    assert "User played the last track for: 0 seconds (out of 16 minutes, 40 seconds) (0%)\n─" in output
    assert "*** User paused music 1 times for 1 minute (40%)" in output
    assert "*** User played 3 songs, skipped 1 songs (33%)" in output
    assert "estimated" not in output
    assert output.count("Friend got INACTIVE") == 1
    assert len(destination.read_text().splitlines()) == 4
    assert [call.args[0] for call in delivery.call_args_list] == ["active", "song", "song", "inactive"]
    assert "User played the previous track (Artist - First) for: 30 seconds (out of 3 minutes, 20 seconds) (15%)" in delivery.call_args_list[1].args[2]
    body = delivery.call_args.args[2]
    assert "User paused music 1 times for 1 minute (40%)" in body
    assert "User played 3 songs, skipped 1 songs (33%)" in body
    assert "Second" in body.split("Recently listened songs in this session:", 1)[1].split("SKIPPED", 1)[0]
    assert "Third" not in body.split("Recently listened songs in this session:", 1)[1].split("SKIPPED", 1)[0]


# Local playback mirrors pause and resume without restarting the current track
@pytest.mark.parametrize("system,function", [("Darwin", "spotify_macos_play_pause"), ("Linux", "spotify_linux_play_pause")])
def test_live_pause_resume_controls_local_playback(loop_environment, monkeypatch, system, function):
    monkeypatch.setattr(monitor, "TRACK_SONGS", True)
    monkeypatch.setattr(monitor.platform, "system", lambda: system)
    start = Mock()
    for name in ("spotify_macos_play_song", "spotify_linux_play_song"):
        monkeypatch.setattr(monitor, name, start)
    control = Mock()
    monkeypatch.setattr(monitor, function, control)
    now = loop_environment.now
    run_live_snapshots(monkeypatch, loop_environment, [feed_entity(now), feed_entity(now), feed_entity(now, playing=False), feed_entity(now)])
    start.assert_called_once()
    assert [call.args[0] for call in control.call_args_list] == ["pause", "play"]


# Resuming with a different track reports the resume before settling the previous track and starting the new one
def test_live_resume_with_a_different_track_reports_resume_first(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "TRACK_SONGS", True)
    monkeypatch.setattr(monitor.platform, "system", lambda: "Darwin")
    start = Mock()
    monkeypatch.setattr(monitor, "spotify_macos_play_song", start)
    control = Mock()
    monkeypatch.setattr(monitor, "spotify_macos_play_pause", control)
    now = loop_environment.now
    run_live_snapshots(monkeypatch, loop_environment, [feed_entity(now), feed_entity(now, playing=False), feed_entity(now + 25, track=OTHER_TRACK_URI)])
    output = capsys.readouterr().out
    assert "User RESUMED playing after 25 seconds\n\nTimestamp:" in output
    assert output.index("User RESUMED playing") < output.index("User played the previous track for: 0 seconds (out of 3 minutes, 20 seconds) (0%)") < output.index("Spotify user:")
    assert "Songs played:\t\t\t2 (25 seconds)" in output
    assert start.call_count == 2
    assert [call.args[0] for call in control.call_args_list] == ["pause", "play"]


# Pause updates leave CSV and notification counts unchanged while one new track adds one event
def test_live_csv_and_notifications_count_track_changes(loop_environment, monkeypatch, tmp_path):
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "SONG_NOTIFICATION", True)
    delivery = Mock(return_value=(True, False))
    monkeypatch.setattr(monitor, "send_notification_channels", delivery)
    now = loop_environment.now
    snapshots = [feed_entity(now), feed_entity(now + 1, playing=False), feed_entity(now + 30), feed_entity(now + 60, track=OTHER_TRACK_URI)]
    destination = tmp_path / "observed.csv"
    run_live_snapshots(monkeypatch, loop_environment, snapshots, str(destination))
    assert len(destination.read_text().splitlines()) == 3
    assert delivery.call_count == 2
    assert "Now playing:" in delivery.call_args.args[2]
    assert "Songs played: 2 (1 minute)" in delivery.call_args.args[2]
    assert "User played the previous track (Artist - First) for: 30 seconds (out of 3 minutes, 20 seconds) (15%)" in delivery.call_args.args[2]
    assert "SKIPPED" not in delivery.call_args.args[2]
