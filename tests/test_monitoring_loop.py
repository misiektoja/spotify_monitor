"""Offline tests for the Friend Activity monitoring loop's error, auth and state handling."""

import time
from unittest.mock import Mock

import pytest

import spotify_monitor as monitor


# Raised by the patched sleep to end one monitoring iteration deterministically
class LoopStopped(Exception):
    pass


# Builds one buddy-list payload describing the monitored friend playing one track
def buddy_list(user_uri_id: str = "watched-user", timestamp_ms: int = 1_700_000_000_000) -> dict:
    return {"friends": [{
        "user": {"uri": f"spotify:user:{user_uri_id}", "name": "Watched Friend"},
        "track": {
            "name": "Track Name",
            "uri": "spotify:track:4cOdK2wGLETKBW3PvgPWqT",
            "artist": {"name": "Artist Name"},
            "album": {"name": "Album Name", "uri": "spotify:album:1234567890abcdefghijkl"},
            "context": {"name": "Playlist Name", "uri": "spotify:playlist:1234567890abcdefghijkl"},
        },
        "timestamp": timestamp_ms,
    }]}


# Builds the track metadata the loop expects from the configured backend
def track_metadata(duration: int = 210) -> dict:
    return {"sp_track_duration": duration, "sp_track_url": "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT", "sp_artist_url": "https://open.spotify.com/artist/1", "sp_album_url": "https://open.spotify.com/album/1", "sp_album_image_url": ""}


# Records the loop's sleeps and ends the run once the requested number of them has happened
class LoopHarness:
    def __init__(self):
        self.sleeps: list = []
        self.stop_after = 1

    # Stands in for time.sleep so each completed loop step is observable and bounded
    def sleep(self, seconds):
        self.sleeps.append(seconds)
        if len(self.sleeps) >= self.stop_after:
            raise LoopStopped


# Silences output, disables side effects and stops the loop after a chosen number of sleeps
@pytest.fixture
def loop_environment(monkeypatch, tmp_path):
    harness = LoopHarness()

    monkeypatch.setattr(monitor.time, "sleep", harness.sleep)
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "SPOTIFY_ERROR_INTERVAL", 180)
    monkeypatch.setattr(monitor, "ALARM_RETRY", 15)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_COUNTER", 0)
    monkeypatch.setattr(monitor, "FLAG_FILE", "")
    monkeypatch.setattr(monitor, "TRACK_SONGS", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "INACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "TRACK_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "SONG_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "SONG_ON_LOOP_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    monkeypatch.setattr(monitor, "_start_timeout_alarm", lambda timeout: None)
    monkeypatch.setattr(monitor, "_restore_timeout_alarm", lambda state: None)
    monkeypatch.setattr(monitor, "retry_pending_activity_notifications", Mock())
    monkeypatch.setattr(monitor, "send_notification_channels", Mock(return_value=(False, False)))
    return harness


# Runs the monitoring loop until the harness stops it and returns the recorded sleep durations
def run_one_iteration(harness, user_uri_id: str = "watched-user", csv_file_name: str = "") -> list:
    with pytest.raises(LoopStopped):
        monitor.spotify_monitor_friend_uri(user_uri_id, set(), csv_file_name)
    return harness.sleeps


# Builds the HTTP error requests raises for one rejected status, carrying the status the classifier reads
def http_error(status: int) -> Exception:
    response = Mock()
    response.status_code = status
    return monitor.req.exceptions.HTTPError(f"{status} Client Error", response=response)


# Verifies a rejected token is dropped so the next cycle refreshes instead of replaying a dead token
@pytest.mark.parametrize("token_source,error", [
    ("cookie", Exception("401 Unauthorized for url: https://guc-spclient.spotify.com/presence-view/v1/buddylist")),
    ("client", Exception("401 Unauthorized for url: https://guc-spclient.spotify.com/presence-view/v1/buddylist")),
    ("cookie", http_error(403)),
    ("client", http_error(403)),
    ("client", http_error(401)),
])
def test_rejected_authentication_clears_cached_token(loop_environment, monkeypatch, token_source, error):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", token_source)
    monkeypatch.setattr(monitor, "SP_CACHED_ACCESS_TOKEN", "dead-token")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "dead-token")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_client_auto", lambda *arguments: "dead-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=error))

    run_one_iteration(loop_environment)

    assert monitor.SP_CACHED_ACCESS_TOKEN is None


# Verifies a transient upstream failure keeps the cached token and retries after the error interval
def test_transient_failure_retries_without_discarding_the_token(loop_environment, monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "SP_CACHED_ACCESS_TOKEN", "live-token")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=Exception("503 Server Error: Service Unavailable")))

    sleeps = run_one_iteration(loop_environment)

    assert sleeps == [monitor.SPOTIFY_ERROR_INTERVAL]
    assert monitor.SP_CACHED_ACCESS_TOKEN == "live-token"


# Verifies a wedged request hits the loop watchdog and retries on the shorter alarm delay
def test_timed_out_request_retries_on_the_alarm_delay(loop_environment, monkeypatch):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=monitor.TimeoutException()))

    sleeps = run_one_iteration(loop_environment)

    assert sleeps == [monitor.ALARM_RETRY]


# Verifies retained activity alerts are retried once per monitoring check, before any network work
def test_pending_notifications_are_retried_each_tick(loop_environment, monkeypatch):
    retry = Mock()
    monkeypatch.setattr(monitor, "retry_pending_activity_notifications", retry)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", Mock(side_effect=Exception("network unreachable")))

    run_one_iteration(loop_environment)

    retry.assert_called_once_with()


# Verifies an active friend raises the configured activity flag for external automation
def test_active_friend_creates_the_activity_flag(loop_environment, monkeypatch, tmp_path):
    flag_path = tmp_path / "active.flag"
    monkeypatch.setattr(monitor, "FLAG_FILE", str(flag_path))
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: buddy_list(timestamp_ms=int(time.time()) * 1000))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))

    run_one_iteration(loop_environment)

    assert flag_path.is_file()


# Verifies the inner poll detects a new track and records it alongside the first one
def test_track_change_is_recorded_for_an_active_friend(loop_environment, monkeypatch, tmp_path):
    csv_path = tmp_path / "tracks.csv"
    started_at = int(time.time())
    payloads = [buddy_list(timestamp_ms=started_at * 1000), buddy_list(timestamp_ms=(started_at + 120) * 1000)]
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=payloads + [Exception("no more polls")]))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))
    loop_environment.stop_after = 2

    run_one_iteration(loop_environment, csv_file_name=str(csv_path))

    rows = [line for line in csv_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 3, rows
    assert all("Track Name" in row for row in rows[1:])


# Verifies verbose stays quiet on an uneventful cycle instead of printing one line per check
def test_a_quiet_cycle_stays_silent_in_verbose(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: buddy_list(timestamp_ms=int(time.time()) * 1000))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))

    run_one_iteration(loop_environment)

    assert "Monitoring check #" not in capsys.readouterr().out


# Verifies a verbose notice closes with the shared timestamp trailer instead of floating between blocks
def test_a_verbose_notice_closes_with_a_timestamp(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "REMOVED_DISAPPEARED_COUNTER", 3)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    # The target has to be found once before the loop that reports it missing is reached
    first_response = iter([buddy_list(timestamp_ms=int(time.time()) * 1000)])
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: next(first_response, {"friends": []}))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))
    loop_environment.stop_after = 2

    run_one_iteration(loop_environment)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    notice = next(index for index, line in enumerate(lines) if "was absent from one buddy-list response" in line)
    assert lines[notice + 1].startswith("Timestamp:")
    assert set(lines[notice + 2]) == {"\u2500"}


# Verifies a repeated operational notice such as a token refresh closes its own block once monitoring runs,
# and stays a bare line on the startup screen, where the monitoring header closes the block instead
def test_a_token_refresh_notice_closes_its_own_block_only_while_monitoring(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "HORIZONTAL_LINE", 10)
    monkeypatch.setattr(monitor, "MONITORING_ACTIVE", False)

    monitor.verbose_notice("Authentication token refreshed (cookie mode)")

    assert capsys.readouterr().out == "* Authentication token refreshed (cookie mode)\n"

    monitor.mark_monitoring_started()
    monitor.verbose_notice("Authentication token refreshed (cookie mode)")

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines[0] == "* Authentication token refreshed (cookie mode)"
    assert lines[1].startswith("Timestamp:")
    assert set(lines[2]) == {"─"}


# Verifies a target missing from the buddy list does not raise the activity flag
def test_absent_friend_leaves_the_activity_flag_unset(loop_environment, monkeypatch, tmp_path):
    flag_path = tmp_path / "active.flag"
    monkeypatch.setattr(monitor, "FLAG_FILE", str(flag_path))
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: buddy_list(user_uri_id="someone-else"))

    run_one_iteration(loop_environment, user_uri_id="watched-user")

    assert not flag_path.exists()
