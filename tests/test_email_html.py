"""Tests for the HTML notification body, its Discord markdown form and its match with the plain text."""

import difflib
import html as html_module
import json
import os
import re
import time
from pathlib import Path

import pytest

import spotify_monitor as monitor

USER_URI_ID = "watched-user"


# Ends a bounded monitoring run once the scripted timeline is exhausted
class LoopStopped(BaseException):
    pass


# Reduces one HTML body back to the text it represents, independently of the module's own converter
def html_to_text(body_html):
    text = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or ""))
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    return html_module.unescape(text)


# Replaces every anchor with its destination, which is what the plain body prints on a bare URL line
def links_as_destinations(line):
    return re.sub(r'(?is)<a\s[^>]*?href="([^"]*)"[^>]*>.*?</a>', r"\1", line)


# Reports whether one HTML line says what its plain counterpart says, whether it links a name or a bare URL
def line_agrees(plain_line, html_line):
    return plain_line in (html_to_text(html_line), html_to_text(links_as_destinations(html_line)))


# Returns what differs between the plain body and the HTML body, empty when their lines and blank lines match
def structural_diff(body, body_html):
    plain_lines = body.split("\n")
    html_lines = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or "")).split("<br>")
    if len(plain_lines) == len(html_lines) and all(line_agrees(*pair) for pair in zip(plain_lines, html_lines)):
        return ""
    return "\n".join(difflib.unified_diff(plain_lines, [html_to_text(line) for line in html_lines], fromfile="plain", tofile="html-reduced", lineterm=""))


TRACK_URIS = ("spotify:track:4cOdK2wGLETKBW3PvgPWqT", "spotify:track:1a2b3c4d5e6f7g8h9i0jkl")
TRACK_NAMES = {TRACK_URIS[0]: ("Artist Name", "Track Name"), TRACK_URIS[1]: ("Second Artist", "Second Track")}
ALBUM_URI = "spotify:album:1234567890abcdefghijkl"
PLAYLIST_URI = "spotify:playlist:1234567890abcdefghijkl"


# Builds one activity answer in the shape the loop reads it, carrying isPlaying only on the live feed
def activity_response(track_uri, timestamp_ms, is_playing=None):
    artist, track = TRACK_NAMES[track_uri]
    friend = {"user": {"uri": f"spotify:user:{USER_URI_ID}", "name": "Watched Friend"}, "track": {"name": track, "uri": track_uri, "artist": {"name": artist}, "album": {"name": "Album Name", "uri": ALBUM_URI}, "context": {"name": "Playlist Name", "uri": PLAYLIST_URI}}, "timestamp": timestamp_ms}
    if is_playing is not None:
        friend["isPlaying"] = is_playing
    return {"friends": [friend]}


# Returns the track metadata the loop reads, in the shape both backends expect
def track_metadata(access_token, track_uri, oauth_app=False):
    artist, track = TRACK_NAMES.get(str(track_uri), TRACK_NAMES[TRACK_URIS[0]])
    return {"sp_track_duration": 210, "sp_track_url": f"https://open.spotify.com/track/{str(track_uri).split(':')[-1]}", "sp_artist_url": "https://open.spotify.com/artist/1", "sp_album_url": "https://open.spotify.com/album/1", "sp_album_image_url": "", "sp_artist_name": artist, "sp_track_name": track, "sp_album_name": "Album Name", "sp_album_uri": ALBUM_URI, "sp_artist_uri": "spotify:artist:1"}


# Returns the scripted activity answers of one backend, ending on a run of samples the inactivity timer can expire on
def scripted_responses(base_ms, live):
    if not live:
        return [activity_response(TRACK_URIS[0], base_ms), *[activity_response(TRACK_URIS[1], base_ms + 30_000) for _ in range(4)]]
    return [activity_response(TRACK_URIS[0], base_ms, True), *[activity_response(TRACK_URIS[1], base_ms + 30_000, True) for _ in range(2)], *[activity_response(TRACK_URIS[1], base_ms + 30_000, False) for _ in range(5)]]


# Records the loop's sleeps and ends the run once the requested number of them has happened
class LoopHarness:
    def __init__(self):
        self.sleeps = []
        self.stop_after = 1
        self.now = float(int(time.time()))

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds
        if len(self.sleeps) >= self.stop_after:
            raise LoopStopped


# Runs one bounded monitoring timeline on the named backend and returns the alerts it tried to send
def run_timeline(monkeypatch, tmp_path, capsys, backend):
    captured = []
    live = backend == "listening_activity"

    def fake_send(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, **kwargs):
        captured.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "webhook_body": kwargs.get("webhook_body") or body, "discord": monitor.html_body_to_discord_markdown(kwargs.get("webhook_body_html") or body_html)})
        return True, True

    harness = LoopHarness()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(monitor.time, "sleep", harness.sleep)
    monkeypatch.setattr(monitor.time, "time", lambda: harness.now)
    monkeypatch.setattr(monitor, "FRIEND_ACTIVITY_BACKEND", backend)
    monkeypatch.setattr(monitor, "SPOTIFY_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "SPOTIFY_ERROR_INTERVAL", 180)
    monkeypatch.setattr(monitor, "SPOTIFY_INACTIVITY_CHECK", 60)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_ACTIVE_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_ERROR_INTERVAL", 180)
    monkeypatch.setattr(monitor, "SPOTIFY_LIVE_INACTIVITY_CHECK", 60)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", 0)
    monkeypatch.setattr(monitor, "FLAG_FILE", "")
    monkeypatch.setattr(monitor, "TRACK_SONGS", False)
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "INACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "SONG_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "cookie")
    monkeypatch.setattr(monitor, "_start_timeout_alarm", lambda timeout: None)
    monkeypatch.setattr(monitor, "_restore_timeout_alarm", lambda state: None)
    monkeypatch.setattr(monitor, "spotify_get_access_token_from_sp_dc", lambda cookie: "live-token")
    monkeypatch.setattr(monitor, "spotify_get_track_info", track_metadata)
    monkeypatch.setattr(monitor, "spotify_activity_metadata", lambda kind, uri, access_token: {"user": "Watched Friend", "playlist": "Playlist Name"}.get(kind, ""))
    monkeypatch.setattr(monitor, "spotify_get_playlist_owner_and_image", lambda *args, **kwargs: ("Playlist Owner", ""))
    monkeypatch.setattr(monitor, "send_notification_channels", fake_send)

    responses = scripted_responses(int(harness.now) * 1000, live)
    monkeypatch.setattr(monitor, "spotify_get_friends_json", lambda *args, **kwargs: responses.pop(0) if len(responses) > 1 else responses[0])
    harness.stop_after = 8
    capsys.readouterr()
    with pytest.raises(LoopStopped):
        monitor.spotify_monitor_friend_uri(USER_URI_ID, set(), "")
    capsys.readouterr()
    return captured


@pytest.fixture(params=["buddylist", "listening_activity"])
# Every alert a timeline covering one play, a song change and the inactivity that follows produces, on each backend
def timeline_alerts(request, monkeypatch, tmp_path, capsys):
    return run_timeline(monkeypatch, tmp_path, capsys, request.param)


@pytest.fixture
# The alerts of both backends together, so one preview shows everything either of them sends
def every_backend_alerts(monkeypatch, tmp_path, capsys):
    return [alert for backend in ("buddylist", "listening_activity") for alert in run_timeline(monkeypatch, tmp_path, capsys, backend)]


# Verifies a value taken from Spotify is escaped before it reaches the HTML body
def test_untrusted_text_is_escaped():
    assert monitor.html_text("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert monitor.html_text("line\nbreak") == "line<br>break"
    assert monitor.escape_html_attr('" onload="x') == "&quot; onload=&quot;x"


# Verifies a bare URL in an alert becomes a link while one already inside an attribute is left alone
def test_bare_urls_are_linked_once():
    assert monitor.html_autolink_urls("Guide: https://example.test/a") == 'Guide: <a href="https://example.test/a">https://example.test/a</a>'
    assert monitor.html_autolink_urls('<a href="https://example.test/a">x</a>') == '<a href="https://example.test/a">x</a>'


# Verifies the Discord body carries the email's emphasis and links instead of raw markup
def test_discord_markdown_mirrors_the_html_body():
    body_html = monitor.html_email_body('Track: <b>Artist - Track</b><br><br>Guide: <a href="https://example.test/a">docs</a>')

    assert monitor.html_body_to_discord_markdown(body_html) == "Track: **Artist - Track**\n\nGuide: [docs](https://example.test/a)"


# Verifies the failure alert bolds its summary and the two values that say how bad the outage is
def test_the_failure_alert_bolds_its_summary_and_outage_fields(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    advice = monitor.make_recovery_advice("network.timeout", "Spotify did not answer in time", "Retry later", True)

    rendered = monitor.recovery_alert_body_html(advice, 60, failed_checks=2, failing_since=1700000000)

    assert rendered.startswith("<html><head></head><body><b>Spotify did not answer in time</b><br><br>")
    assert "Failed checks in a row: <b>2</b>" in rendered
    assert "Failing since: <b>" in rendered
    # The retry delay is configured rather than observed, so it carries no emphasis
    assert "Next retry in: 1 minute" in rendered
    assert rendered.endswith("</body></html>")


# Verifies the scrobble health alert names its missing plays in bold and links the pages it points at
def test_the_scrobble_health_alert_is_sent_as_html(monkeypatch):
    captured = {}
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *args, **kwargs: captured.update(subject=args[1], body=args[2], body_html=args[3]) or (True, True))
    monkeypatch.setattr(monitor, "SCROBBLE_HEALTH_NOTIFICATION", True)
    play = monitor.SpotifyPlay(played_at=1700000000, artist="Artist Name", track="Track Name", duration_ms=210000, uri="spotify:track:1")
    evaluation = monitor.ScrobbleHealthEvaluation(status="missing", unmatched=(play,), latest_match_at=0, latest_spotify_at=1700000000, latest_lastfm_at=0, matches=())

    monitor.send_scrobble_health_notification("someuser", evaluation, "outage", selected_channels=(True, False), report_event=False)

    assert captured["body_html"].startswith("<html><head></head><body>")
    assert "<b>Track Name</b>" not in captured["body_html"]
    assert "<b>Artist Name - Track Name</b>" in captured["body_html"]
    assert '<a href="https://www.last.fm/user/someuser">' in captured["body_html"]
    assert structural_diff(captured["body"], captured["body_html"]) == ""


# Verifies the timeline reaches several alert types, so the structural check is not silently narrow
def test_the_timeline_covers_several_alert_types(timeline_alerts):
    assert {"active", "song", "inactive"} <= {alert["type"] for alert in timeline_alerts}


# Verifies every alert carries an HTML body next to its plain one
def test_every_alert_has_an_html_body(timeline_alerts):
    assert [alert["subject"] for alert in timeline_alerts if not alert["body_html"]] == []


# Verifies each HTML body reduces back to its plain body, so no line break was added or lost
def test_html_bodies_match_the_plain_text(timeline_alerts):
    mismatches = [f"{alert['type']}: {alert['subject']}\n{structural_diff(alert['body'], alert['body_html'])}" for alert in timeline_alerts if structural_diff(alert["body"], alert["body_html"])]

    assert mismatches == []


# Verifies every HTML body is one complete document, so no fragment reaches a mail client unwrapped
def test_html_bodies_are_complete_documents(timeline_alerts):
    for alert in timeline_alerts:
        assert alert["body_html"].startswith("<html><head></head><body>")
        assert alert["body_html"].endswith("</body></html>")


# Writes the captured alerts as JSON when PREVIEW_ALERTS_JSON names a destination, so a preview tool can render them
@pytest.mark.skipif(not os.environ.get("PREVIEW_ALERTS_JSON"), reason="set PREVIEW_ALERTS_JSON to dump the alerts")
def test_dump_the_alerts_for_a_preview(every_backend_alerts):
    Path(os.environ["PREVIEW_ALERTS_JSON"]).write_text(json.dumps(every_backend_alerts, indent=2), encoding="utf-8")
