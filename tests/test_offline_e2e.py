"""Offline end-to-end test for one complete CLI monitoring iteration."""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "spotify_monitor.py"
ARTIFACT_ROOT = PROJECT_ROOT / "local" / "e2e_test_artifacts"


# Serves deterministic friend activity and track metadata over loopback
class OfflineSpotifyHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, Any]] = []

    # Returns one deterministic JSON response for each offline endpoint
    def do_GET(self) -> None:
        type(self).requests.append({"path": self.path, "headers": dict(self.headers.items())})
        if self.path == "/buddylist":
            payload = {"friends": [{"timestamp": int(time.time() * 1000), "user": {"uri": "spotify:user:offline.friend", "name": "Offline Friend"}, "track": {"artist": {"name": "Local Artist"}, "album": {"name": "Local Album", "uri": "spotify:album:local-album"}, "context": {"name": "Local Album", "uri": "spotify:album:local-album"}, "name": "Local Track", "uri": "spotify:track:local-track"}}]}
        elif self.path == "/track":
            payload = {"sp_album_image_url": "", "sp_artist_name": "Local Artist", "sp_track_name": "Local Track", "sp_album_name": "Local Album", "sp_track_duration": 180, "sp_track_url": "https://open.spotify.com/track/local-track", "sp_artist_url": "https://open.spotify.com/artist/local-artist", "sp_album_url": "https://open.spotify.com/album/local-album"}
        else:
            self.send_error(404)
            return
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # Suppresses default request logging during tests
    def log_message(self, format: str, *args: Any) -> None:
        return None


# Runs the deterministic Spotify fixture server on loopback
@pytest.fixture
def offline_spotify_server() -> Iterator[tuple[str, type[OfflineSpotifyHandler]]]:
    OfflineSpotifyHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), OfflineSpotifyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", OfflineSpotifyHandler
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


# Creates one disposable E2E directory below the project local directory
@pytest.fixture
def e2e_directory() -> Iterator[Path]:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ARTIFACT_ROOT) as directory_name:
        yield Path(directory_name)


# Verifies the CLI loads config, consumes HTTP data and completes one monitoring cycle
@pytest.mark.e2e
def test_cli_monitoring_iteration_against_local_spotify_fixture(offline_spotify_server: tuple[str, type[OfflineSpotifyHandler]], e2e_directory: Path):
    server_url, handler = offline_spotify_server
    config_path = e2e_directory / "spotify_monitor.conf"
    config_path.write_text('TOKEN_SOURCE = "cookie"\nSP_DC_COOKIE = "offline-cookie"\nDOTENV_FILE = "none"\nDISABLE_LOGGING = True\nSPOTIFY_CHECK_INTERVAL = 1\nSPOTIFY_ERROR_INTERVAL = 1\nSPOTIFY_INACTIVITY_CHECK = 660\nSPOTIFY_DISAPPEARED_CHECK_INTERVAL = 1\nACTIVE_NOTIFICATION = False\nINACTIVE_NOTIFICATION = False\nTRACK_NOTIFICATION = False\nSONG_NOTIFICATION = False\nSONG_ON_LOOP_NOTIFICATION = False\nERROR_NOTIFICATION = False\nWEBHOOK_ENABLED = False\nTRACK_SONGS = False\n', encoding="utf-8")
    source = textwrap.dedent(f"""
        import requests
        import runpy
        import sys
        module = runpy.run_path({str(CLI_PATH)!r}, run_name="spotify_monitor_offline_e2e")
        runtime = module["main"].__globals__
        runtime["sys"].argv = [{str(CLI_PATH)!r}, "offline.friend", "--config-file", {str(config_path)!r}, "--env-file", "none"]
        runtime["CLEAR_SCREEN"] = False
        runtime["check_internet"] = lambda *args, **kwargs: True
        runtime["spotify_get_access_token_from_sp_dc"] = lambda cookie: "offline-token"
        friend_calls = []
        # Fetches the initial fixture then exits before the primary polling request
        def offline_get_friends(token):
            if friend_calls:
                raise SystemExit(0)
            friend_calls.append(True)
            return requests.get({f"{server_url}/buddylist"!r}, headers={{"Authorization": f"Bearer {{token}}"}}, timeout=5).json()
        runtime["spotify_get_friends_json"] = offline_get_friends
        runtime["spotify_get_track_info"] = lambda token, uri: requests.get({f"{server_url}/track"!r}, headers={{"Authorization": f"Bearer {{token}}", "X-Track-Uri": uri}}, timeout=5).json()
        runtime["platform"].system = lambda: "Windows"
        runtime["time"].sleep = lambda seconds: (_ for _ in ()).throw(SystemExit(0))
        module["main"]()
    """)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run([sys.executable, "-c", source], cwd=e2e_directory, env=environment, check=False, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Monitoring user offline.friend" in result.stdout
    assert "Offline Friend" in result.stdout
    assert "Local Artist - Local Track" in result.stdout
    assert "Friend is currently ACTIVE" in result.stdout
    assert [request["path"] for request in handler.requests] == ["/buddylist", "/track"]
    assert all(request["headers"]["Authorization"] == "Bearer offline-token" for request in handler.requests)
    assert handler.requests[1]["headers"]["X-Track-Uri"] == "spotify:track:local-track"
