"""Offline tests for the Friend Activity monitoring loop's error, auth and state handling."""

import time
from unittest.mock import Mock

import pytest

import spotify_monitor as monitor

# Captured before any fixture replaces it, so a test can put the real delivery path back
REAL_SEND_NOTIFICATION_CHANNELS = monitor.send_notification_channels


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
        # A fake clock advanced by each sleep, so the timed liveness reminder is deterministic
        self.now = float(int(time.time()))

    # Stands in for time.sleep so each completed loop step is observable and bounded
    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds
        if len(self.sleeps) >= self.stop_after:
            raise LoopStopped


# Silences output, disables side effects and stops the loop after a chosen number of sleeps
@pytest.fixture
def loop_environment(monkeypatch, tmp_path):
    harness = LoopHarness()

    monkeypatch.setattr(monitor.time, "sleep", harness.sleep)
    monkeypatch.setattr(monitor.time, "time", lambda: harness.now)
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "SPOTIFY_ERROR_INTERVAL", 180)
    # Both backends share one cadence here so the loop tests read the same timings whichever backend is selected
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_ACTIVE_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_ERROR_INTERVAL", 180)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_DISAPPEARED_COUNTER", 4)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_DISAPPEARED_CHECK_INTERVAL", 180)
    monkeypatch.setattr(monitor, "ALARM_RETRY", 15)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 0)
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


# Verifies each wait a failed check leads into says how long it is and what it is waiting for, since the two
# paths wait for different reasons and a trace that stops at the failure leaves the pause unexplained
def test_every_wait_after_a_failed_check_says_how_long_it_is_and_why(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=Exception("503 Server Error: Service Unavailable")))

    run_one_iteration(loop_environment)
    assert f"Retry wait: due_in={monitor.display_time(monitor.SPOTIFY_ERROR_INTERVAL)}, reason=waiting the error interval after a failed check" in capsys.readouterr().out

    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=monitor.TimeoutException()))

    run_one_iteration(loop_environment)
    assert f"Retry wait: due_in={monitor.display_time(monitor.ALARM_RETRY)}, reason=a Spotify request timed out" in capsys.readouterr().out


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
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_DISAPPEARED_COUNTER", 3)
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
    notice = next(index for index, line in enumerate(lines) if "was absent from one activity response" in line)
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


# Verifies a legacy disappearance names its possible causes, keeps the follow advice and times the return
def test_a_legacy_disappearance_names_its_causes_and_times_the_return(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "REMOVED_DISAPPEARED_COUNTER", 2)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_DISAPPEARED_COUNTER", 2)
    monkeypatch.setattr(monitor, "SPOTIFY_DISAPPEARED_CHECK_INTERVAL", 180)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_DISAPPEARED_CHECK_INTERVAL", 180)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "is_user_removed", lambda *arguments, **keywords: False)
    now_ms = int(loop_environment.now) * 1000
    responses = iter([buddy_list(timestamp_ms=now_ms), buddy_list(timestamp_ms=now_ms), {"friends": []}, {"friends": []}, buddy_list(timestamp_ms=now_ms)])
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: next(responses))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))
    loop_environment.stop_after = 4

    run_one_iteration(loop_environment)

    output = capsys.readouterr().out
    assert "Spotify user 'watched-user' (Watched Friend) has disappeared from Friend Activity (sharing turned off, unfollowed or blocked). Checking every 3 minutes\nTo fix:" in output
    assert "Spotify user watched-user (Watched Friend) has reappeared after 4 minutes\nTimestamp:" in output
    assert "no longer visible" not in output


# Verifies a target missing at startup but listed by the other backend gets the switch hint instead of the follow advice
def test_startup_names_the_other_backend_when_it_lists_the_target(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", "listening_activity")
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "is_user_removed", lambda *arguments, **keywords: False)
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token, backend=None: buddy_list("watched-user") if backend == "buddylist" else buddy_list("someone-else"))

    run_one_iteration(loop_environment, user_uri_id="watched-user")

    output = capsys.readouterr().out
    assert "User 'watched-user' not found" in output
    assert 'The target is visible through the buddylist backend. Run with --friend-activity-backend buddylist or save FRIEND_ACTIVITY_BACKEND = "buddylist" in the configuration file\nTimestamp:' in output
    assert "To fix:" not in output


# Verifies a target missing at startup keeps the follow advice when the other backend does not list it either
def test_startup_keeps_the_follow_advice_when_no_backend_lists_the_target(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "is_user_removed", lambda *arguments, **keywords: False)
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token, backend=None: buddy_list("someone-else"))

    run_one_iteration(loop_environment, user_uri_id="watched-user")

    output = capsys.readouterr().out
    assert "visible through" not in output
    assert "To fix: Follow this profile" in output


# Verifies a target missing from the buddy list does not raise the activity flag
def test_absent_friend_leaves_the_activity_flag_unset(loop_environment, monkeypatch, tmp_path):
    flag_path = tmp_path / "active.flag"
    monkeypatch.setattr(monitor, "FLAG_FILE", str(flag_path))
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: buddy_list(user_uri_id="someone-else"))

    run_one_iteration(loop_environment, user_uri_id="watched-user")

    assert not flag_path.exists()


# Verifies the first failure while the friend is active is reported in full rather than waiting for a repeat threshold
def test_the_first_failure_while_active_is_reported_in_full(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    responses = [buddy_list(timestamp_ms=int(time.time()) * 1000), Exception("503 Server Error: Service Unavailable")]
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=responses))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))
    loop_environment.stop_after = 2

    run_one_iteration(loop_environment)

    output = capsys.readouterr().out
    assert f"* Error: Spotify is temporarily unavailable (retrying in {monitor.display_time(monitor.SPOTIFY_ERROR_INTERVAL)})" in output
    assert "To fix: " in output


# Verifies a failure that keeps repeating is reported once and then carried by the hourly reminder with a count,
# on a clock of its own, so the liveness banner being off does not silence it or bring back a block per check
def test_a_lasting_outage_is_carried_by_the_hourly_reminder(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 2 * monitor.SPOTIFY_ERROR_INTERVAL)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=Exception("503 Server Error: Service Unavailable")))
    loop_environment.stop_after = 6

    run_one_iteration(loop_environment)

    output = capsys.readouterr().out
    assert monitor.LIVENESS_REMINDER_SECONDS == 0
    assert output.count("* Error:") == 1
    assert output.count("To fix: ") == 1
    assert "* Monitoring degraded for watched-user. Spotify is temporarily unavailable since " in output
    assert ", 3 failed checks\n" in output and ", 5 failed checks\n" in output
    assert output.count("Liveness check, timestamp:") == 2


# Records every alert the loop hands to the delivery helper and answers with the outcome each call is given
def recording_channels(monkeypatch, outcomes):
    calls = []

    def record(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, **kwargs):
        calls.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "email": bool(email_enabled), "webhook": bool(webhook_enabled), "webhook_body": kwargs.get("webhook_body", ""), "webhook_body_html": kwargs.get("webhook_body_html", "")})
        return outcomes[min(len(calls), len(outcomes)) - 1]

    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "send_notification_channels", record)
    return calls


# Drives the loop with a cookie token and the given buddy-list outcomes, returning every alert on the error channel
def error_channel_alerts_for(loop_environment, monkeypatch, responses, outcomes, stop_after):
    calls = recording_channels(monkeypatch, outcomes)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 100 * monitor.SPOTIFY_ERROR_INTERVAL)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    pending = list(responses)

    # The last outcome repeats for as long as the loop keeps asking, so an exhausted list cannot become a failure of its own
    def respond(*arguments, **keywords):
        response = pending.pop(0) if len(pending) > 1 else pending[0]
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(monitor, "spotify_get_friends_json", respond)
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))
    loop_environment.stop_after = stop_after
    run_one_iteration(loop_environment)
    return [call for call in calls if call["type"] == "error"]


# Keeps the failure alerts of one run, so a test about them is not disturbed by the recovery alert that closes one
def error_alerts_for(loop_environment, monkeypatch, responses, outcomes, stop_after):
    return [call for call in error_channel_alerts_for(loop_environment, monkeypatch, responses, outcomes, stop_after) if call["subject"].startswith("Spotify Monitor error:")]


# An outage used to be printed and never delivered, since only a rejected token earned an alert
def test_any_failure_alerts_both_channels_once(loop_environment, monkeypatch):
    errors = error_alerts_for(loop_environment, monkeypatch, [Exception("503 Server Error: Service Unavailable")] * 6, [(True, True)], 6)

    assert [(call["email"], call["webhook"]) for call in errors] == [(True, True)]
    assert errors[0]["subject"] == "Spotify Monitor error: Spotify is temporarily unavailable (user: watched-user)"
    assert errors[0]["body"].startswith("Spotify is temporarily unavailable\n\nTo fix: ")
    assert f"Next retry in: {monitor.display_time(monitor.SPOTIFY_ERROR_INTERVAL)}" in errors[0]["body"]


# The guide link sits under the fix in the HTML body too, since HTML renders the newline the fix carries as a space
def test_the_guide_link_keeps_its_own_line_in_the_html_body(loop_environment, monkeypatch):
    errors = error_alerts_for(loop_environment, monkeypatch, [Exception("503 Server Error: Service Unavailable")] * 6, [(True, True)], 6)

    parts = errors[0]["body_html"].split("<br>")
    fix_index = next(index for index, part in enumerate(parts) if part.startswith("To fix: "))
    assert parts[fix_index + 1].startswith("Guide: https://")
    assert "\n" not in parts[fix_index]


# One outage earns one alert per channel, however the failure changes, until a check succeeds again
def test_a_changed_failure_category_does_not_earn_a_second_alert(loop_environment, monkeypatch):
    responses = [Exception("503 Server Error: Service Unavailable")] * 3 + [http_error(401)] * 3
    errors = error_alerts_for(loop_environment, monkeypatch, responses, [(True, True)], 6)

    assert [call["subject"] for call in errors] == ["Spotify Monitor error: Spotify is temporarily unavailable (user: watched-user)"]


# Alternating categories used to forget the delivered alert on every transition, so one outage sent one per check
def test_alternating_failure_categories_deliver_one_alert(loop_environment, monkeypatch):
    responses = [http_error(401), http_error(403), http_error(401), http_error(403)]
    errors = error_alerts_for(loop_environment, monkeypatch, responses, [(True, True)], 4)

    assert len(errors) == 1


# A watchdog timeout is a failed check, so it reaches the alert channels instead of only printing a retry line.
# It retries on the shorter watchdog wait, so it needs more checks than the error interval to last five minutes
def test_a_stalled_request_earns_the_same_single_alert(loop_environment, monkeypatch):
    checks = 2 * (monitor.ERROR_ALERT_AFTER_SECONDS // monitor.ALARM_RETRY)
    errors = error_alerts_for(loop_environment, monkeypatch, [monitor.TimeoutException("stalled")] * checks, [(True, True)], checks)

    assert [call["subject"] for call in errors] == ["Spotify Monitor error: Spotify did not answer in time (user: watched-user)"]


# Each channel is tracked on its own, so the one that failed is retried while the one that landed is left alone
def test_a_failed_channel_is_retried_and_a_delivered_one_is_not(loop_environment, monkeypatch):
    errors = error_alerts_for(loop_environment, monkeypatch, [Exception("503 Server Error: Service Unavailable")] * 6, [(True, False), (False, True)], 6)

    assert [(call["email"], call["webhook"]) for call in errors] == [(True, True), (False, True)]


# A run that recovered and fails again is in a new outage, which deserves its own alert
def test_a_new_outage_after_a_recovery_alerts_again(loop_environment, monkeypatch):
    failure = Exception("503 Server Error: Service Unavailable")
    responses = [failure, failure, failure, buddy_list(timestamp_ms=int(time.time()) * 1000), failure, failure, failure]
    alerts = error_channel_alerts_for(loop_environment, monkeypatch, responses, [(True, True)], 7)

    assert [(call["email"], call["webhook"]) for call in alerts] == [(True, True)] * 3
    assert [call["subject"].split(":")[0] for call in alerts] == ["Spotify Monitor error", "Spotify Monitor recovered", "Spotify Monitor error"]


# The recovery alert closes the failure alert on the channels it reached, so a channel that never heard stays quiet
def test_the_recovery_alert_follows_the_channels_the_failure_alert_reached(loop_environment, monkeypatch):
    failure = Exception("503 Server Error: Service Unavailable")
    responses = [failure, failure, failure, buddy_list(timestamp_ms=int(time.time()) * 1000)]
    alerts = error_channel_alerts_for(loop_environment, monkeypatch, responses, [(False, True)], 5)
    recoveries = [call for call in alerts if call["subject"].startswith("Spotify Monitor recovered:")]

    assert len(recoveries) == 1
    assert (recoveries[0]["email"], recoveries[0]["webhook"]) == (False, True)
    assert recoveries[0]["subject"].startswith("Spotify Monitor recovered: monitoring watched-user resumed after ")
    assert recoveries[0]["body"].startswith("Monitoring recovered for watched-user after ")
    assert "The failure was: Spotify is temporarily unavailable" in recoveries[0]["body"]
    assert "Timestamp: " not in recoveries[0]["webhook_body"]


# A failure too short to earn an alert has nothing to close, so its recovery stays on the console
def test_a_recovery_without_a_delivered_failure_alert_sends_nothing(loop_environment, monkeypatch, capsys):
    responses = [Exception("503 Server Error: Service Unavailable"), buddy_list(timestamp_ms=int(time.time()) * 1000)]
    alerts = error_channel_alerts_for(loop_environment, monkeypatch, responses, [(True, True)], 3)

    assert alerts == []
    assert "* Monitoring recovered for watched-user after " in capsys.readouterr().out


# The subject names the tool, the failure and the target, so an inbox fed by several monitors sorts them by tool
def test_the_failure_alert_subject_names_the_tool_and_the_target():
    advice = monitor.make_recovery_advice("network.timeout", "Spotify did not answer in time", "a fix", True)

    assert monitor.recovery_alert_subject(advice, "watched-user") == "Spotify Monitor error: Spotify did not answer in time (user: watched-user)"


# A first failure has no run to count, so the alert leaves out the count and the outage start
def test_the_failure_alert_body_leaves_out_a_run_of_one(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    advice = monitor.make_recovery_advice("network.timeout", "Spotify did not answer in time", "a fix", True)

    body = monitor.recovery_alert_body(advice, 180, 1, 0, timestamp=False)

    assert body == "Spotify did not answer in time\n\nTo fix: a fix\n\nNext retry in: 3 minutes"


# A lasting outage says how many checks failed and since when, so the reader sees how bad it is
def test_the_failure_alert_body_counts_a_lasting_outage(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monkeypatch.setattr(monitor, "get_date_from_ts", lambda timestamp: "FAILING-SINCE")
    advice = monitor.make_recovery_advice("network.timeout", "Spotify did not answer in time", "a fix", True)

    body = monitor.recovery_alert_body(advice, 180, 4, 1000, timestamp=False)

    assert body == "Spotify did not answer in time\n\nTo fix: a fix\n\nFailed checks in a row: 4\nFailing since: FAILING-SINCE\nNext retry in: 3 minutes"


# The technical detail is a debug aid, so it reaches the alert only when the run asked for diagnostics
@pytest.mark.parametrize("debug,carried", [(False, False), (True, True)])
def test_the_failure_alert_body_carries_the_detail_only_in_debug(monkeypatch, debug, carried):
    monkeypatch.setattr(monitor, "DEBUG_MODE", debug)
    advice = monitor.make_recovery_advice("network.timeout", "Spotify did not answer in time", "a fix", True, "the raw error")

    assert ("Technical detail: the raw error" in monitor.recovery_alert_body(advice, 180, 1, 0, timestamp=False)) is carried


# The HTML alert repeats the plain text with the summary in bold, so both formats say the same thing
def test_the_html_failure_alert_matches_the_plain_body(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monkeypatch.setattr(monitor, "get_date_from_ts", lambda timestamp: "FAILING-SINCE")
    advice = monitor.make_recovery_advice("network.timeout", "Spotify did not answer in time", "a fix", True)

    body_html = monitor.recovery_alert_body_html(advice, 180, 4, 1000, timestamp=False)

    assert body_html == "<html><head></head><body><b>Spotify did not answer in time</b><br><br>To fix: a fix<br><br>Failed checks in a row: 4<br>Failing since: FAILING-SINCE<br>Next retry in: 3 minutes</body></html>"


# A webhook provider stamps its own time, so the timestamp line belongs to the email alone
def test_the_webhook_body_leaves_the_timestamp_to_the_provider(loop_environment, monkeypatch):
    errors = error_alerts_for(loop_environment, monkeypatch, [Exception("503 Server Error: Service Unavailable")] * 6, [(True, True)], 6)

    assert "\n\nTimestamp: " in errors[0]["body"]
    assert "Timestamp: " not in errors[0]["webhook_body"]
    assert "Timestamp: " not in errors[0]["webhook_body_html"]
    assert errors[0]["body"].startswith(errors[0]["webhook_body"])


# A failure the loop can retry away is alerted only once the outage has lasted the alert delay, so a blip of a
# check or two reaches nobody while a real outage still does
@pytest.mark.parametrize("stop_after,expected", [(2, []), (3, [(True, True)])])
def test_a_retryable_failure_is_alerted_once_the_outage_has_lasted(loop_environment, monkeypatch, stop_after, expected):
    errors = error_alerts_for(loop_environment, monkeypatch, [Exception("503 Server Error: Service Unavailable")], [(True, True)], stop_after)

    assert [(call["email"], call["webhook"]) for call in errors] == expected


# A failure nothing here can retry away is alerted on the first check, since waiting would change nothing
def test_a_failure_that_cannot_clear_itself_is_alerted_at_once(loop_environment, monkeypatch):
    errors = error_alerts_for(loop_environment, monkeypatch, [http_error(401)], [(True, True)], 1)

    assert [call["subject"] for call in errors] == ["Spotify Monitor error: Spotify rejected the sp_dc cookie (user: watched-user)"]


# The loop that follows an active listener reports its failures through the same alert as the outer one
def test_a_failure_while_active_alerts_both_channels_too(loop_environment, monkeypatch):
    responses = [buddy_list(timestamp_ms=int(time.time()) * 1000)] + [Exception("503 Server Error: Service Unavailable")] * 5
    errors = error_alerts_for(loop_environment, monkeypatch, responses, [(True, True)], 6)

    assert [(call["email"], call["webhook"]) for call in errors] == [(True, True)]
    assert errors[0]["subject"] == "Spotify Monitor error: Spotify is temporarily unavailable (user: watched-user)"


# Verifies a retry that reaches the screen on a quiet check still ends with a timestamp
def test_a_delivery_retry_on_a_quiet_check_ends_with_a_timestamp(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 10 * monitor.SPOTIFY_ERROR_INTERVAL)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "send_notification_channels", REAL_SEND_NOTIFICATION_CHANNELS)
    monkeypatch.setattr(monitor, "webhook_event_enabled", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(monitor, "send_email", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=http_error(401)))
    loop_environment.stop_after = 3

    run_one_iteration(loop_environment)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    deliveries = [index for index, line in enumerate(lines) if line.startswith("Sending email notification")]

    assert len(deliveries) > 1, lines
    for index in deliveries:
        assert any(line.startswith("Timestamp:") for line in lines[index + 1:index + 3]), lines[index:index + 3]


# Verifies the reminder follows the clock, so a run that retries faster than it polls does not remind more often
def test_the_outage_reminder_follows_the_clock_not_the_check_count(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    advice = monitor.classify_recovery_error(Exception("503 Server Error: Service Unavailable"), "cookie_auth")

    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 900)
    assert reporter.failed(advice) == "full"
    outcomes = []
    for _ in range(60):
        clock[0] += 15
        outcomes.append(reporter.failed(advice))

    assert outcomes.count("reminder") == 1


# Verifies a category change mid-outage keeps the outage start, so the alert delay and the reminder still elapse
def test_an_outage_that_changes_category_keeps_its_start(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    first = monitor.classify_recovery_error(Exception("503 Server Error: Service Unavailable"), "cookie_auth")
    second = monitor.classify_recovery_error(Exception("Connection timed out"), "cookie_auth")
    assert first.code != second.code

    assert reporter.failed(first) == "full"
    outcomes = []
    for index in range(60):
        clock[0] += 15
        outcomes.append(reporter.failed(second if index % 2 else first))

    assert reporter.since == 1000000
    assert reporter.recovered() == 900


# Verifies a failure that clears is reported as recovered, since a throttled failure stops printing while it lasts
def test_a_cleared_outage_reports_its_recovery(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    responses = [Exception("503 Server Error: Service Unavailable"), buddy_list(timestamp_ms=int(time.time()) * 1000)]
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=responses))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))
    loop_environment.stop_after = 2

    run_one_iteration(loop_environment)

    assert "* Monitoring recovered for watched-user after " in capsys.readouterr().out


# Verifies a named aggregate summary keeps the shared line shape rather than inventing its own
def test_a_labelled_failure_keeps_the_shared_shape(loop_environment, capsys):
    error = Exception("503 Server Error: Service Unavailable")

    monitor.print_recovery_error(error, "cookie_auth", retry_note="retrying in 3 minutes", label="Error 50x (6x times in the last 30 minutes)", tracker=None)

    first_line = capsys.readouterr().out.splitlines()[0]
    assert first_line == "* Error 50x (6x times in the last 30 minutes): Spotify is temporarily unavailable (retrying in 3 minutes)"


# Verifies a check that reported the end of an outage restarts the quiet clock, since the banner speaks for a
# check that said nothing and would otherwise contradict the recovery line above it
def test_a_check_that_reported_a_recovery_does_not_claim_it_was_quiet(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 2 * monitor.SPOTIFY_CHECK_INTERVAL)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    started_at = int(time.time())
    # The outage lands after the run has reached the primary loop, which is the loop the banner belongs to
    responses = [buddy_list(timestamp_ms=started_at * 1000), *[Exception("503 Server Error: Service Unavailable")] * 4, *[buddy_list(timestamp_ms=started_at * 1000)] * 3]
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=responses))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))
    loop_environment.stop_after = 6

    run_one_iteration(loop_environment)

    output = capsys.readouterr().out
    assert "* Monitoring recovered for watched-user after " in output, "the check under test reported no recovery"
    assert "Monitoring healthy for" not in output


# Verifies the banner follows the clock rather than the number of checks behind it
def test_the_liveness_banner_follows_the_clock_not_the_check_count(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 3 * monitor.SPOTIFY_CHECK_INTERVAL)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    started_at = int(time.time())
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: buddy_list(timestamp_ms=started_at * 1000))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))
    loop_environment.stop_after = 5

    run_one_iteration(loop_environment)

    assert capsys.readouterr().out.count("Monitoring healthy for") == 1


# Verifies the liveness banner explains itself without --verbose, so a plain run never prints a bare timestamp
def test_the_liveness_banner_explains_itself_without_diagnostics(loop_environment, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", monitor.SPOTIFY_CHECK_INTERVAL)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    started_at = int(time.time())
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda token: buddy_list(timestamp_ms=started_at * 1000))
    monkeypatch.setattr(monitor, "spotify_get_track_info", lambda *arguments, **keywords: track_metadata())
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *arguments, **keywords: ("Playlist Owner", ""))
    loop_environment.stop_after = 4

    run_one_iteration(loop_environment)

    output = capsys.readouterr().out
    assert "* Monitoring healthy for watched-user. The target is visible with no activity change since the last check" in output
    assert "Liveness check, timestamp:" in output


# Verifies an internet outage that classifies as a timeout on one check and as unreachable on the next is one
# outage, so it is reported once on screen and alerted once
def test_an_internet_outage_that_flaps_is_one_outage(loop_environment, monkeypatch, capsys):
    flapping = [Exception("Connection timed out"), monitor.req.exceptions.ConnectionError("connection refused")] * 6
    errors = error_alerts_for(loop_environment, monkeypatch, flapping, [(True, True)], 12)

    output = capsys.readouterr().out
    assert output.count("* Error:") == 1
    assert output.count("To fix: ") == 1
    assert "Monitoring failure changed" not in output
    assert len(errors) == 1


# Verifies a reported outage that starts failing differently is still one outage, so the change is one line
# rather than a second report
def test_a_second_failure_category_is_noted_in_one_line(loop_environment, monkeypatch, capsys):
    responses = [Exception("503 Server Error: Service Unavailable")] * 3 + [Exception("Connection timed out")]
    error_alerts_for(loop_environment, monkeypatch, responses, [(True, True)], 8)

    lines = capsys.readouterr().out.splitlines()
    reports = [line for line in lines if line.startswith("* Error:")]
    changes = [number for number, line in enumerate(lines) if line.startswith("* Monitoring failure changed for watched-user. ")]
    assert len(reports) == 1 and "temporarily unavailable" in reports[0]
    assert len(changes) == 1 and lines[changes[0]].endswith("Spotify did not answer in time")
    assert lines[changes[0] + 1].startswith("Timestamp:")
    assert "\n".join(lines).count("To fix: ") == 1


# Verifies the reporter treats every network code as one outage and any other change as a one-line note
def test_the_outage_reporter_merges_network_codes_and_notes_other_changes(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    timeout = monitor.classify_recovery_error(Exception("Connection timed out"), "cookie_auth")
    unreachable = monitor.classify_recovery_error(monitor.req.exceptions.ConnectionError("connection refused"), "cookie_auth")
    unavailable = monitor.classify_recovery_error(Exception("503 Server Error: Service Unavailable"), "cookie_auth")
    rejected = monitor.classify_recovery_error(http_error(401), "cookie_auth")
    assert (monitor.outage_family(timeout.code), monitor.outage_family(unreachable.code)) == ("network", "network")

    assert reporter.failed(timeout) == "full"
    assert reporter.failed(unreachable) == ""
    assert reporter.failed(timeout) == ""
    assert reporter.failed(unavailable) == "changed"
    assert reporter.failed(unavailable) == ""
    assert reporter.failed(rejected) == "full"
    assert reporter.since == 1000000


# Verifies the counted thresholds the reminder replaces are read from an old config file and ignored with a note
def test_the_aggregation_thresholds_are_retired():
    retired = {"ERROR_500_NUMBER_LIMIT", "ERROR_500_TIME_LIMIT", "ERROR_NETWORK_ISSUES_NUMBER_LIMIT", "ERROR_NETWORK_ISSUES_TIME_LIMIT"}

    assert retired <= set(monitor.RETIRED_CONFIG_SETTINGS)
    assert not any(hasattr(monitor, name) for name in retired)
