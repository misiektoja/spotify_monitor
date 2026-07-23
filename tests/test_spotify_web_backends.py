import io
import os
import subprocess
import sys
import time
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, call, patch

import requests

import spotify_monitor as monitor


TRACK_URI = "spotify:track:4N1MFKjziFHH4IS3RYYUrU"
PLAYLIST_URI = "spotify:playlist:1yjvJQztEdo7pKTpIsIdOa"
OTHER_PLAYLIST_URI = "spotify:playlist:3cEYpjA9oz9GiPac4AsH4n"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "spotify_monitor.py"
ISOLATED_PRELUDE = "import builtins, requests, runpy, socket, sys; _real_import = builtins.__import__; builtins.__import__ = lambda name, *args, **kwargs: (_ for _ in ()).throw(ModuleNotFoundError('blocked Spotipy import')) if name == 'spotipy' or name.startswith('spotipy.') else _real_import(name, *args, **kwargs); requests.sessions.Session.request = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network request attempted')); socket.create_connection = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network connection attempted')); "


# Runs isolated Python source with network access and Spotipy imports blocked
def run_isolated(source):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-c", ISOLATED_PRELUDE + source], cwd=PROJECT_ROOT, capture_output=True, text=True, env=env, timeout=30, check=False)


# Runs the command-line entry point with network access and Spotipy imports blocked
def run_cli(*arguments):
    source = f"sys.argv = {[str(CLI_PATH), *arguments]!r}; runpy.run_path({str(CLI_PATH)!r}, run_name='__main__')"
    return run_isolated(source)


class FakeResponse:
    # Stores a minimal requests-compatible response for backend tests
    def __init__(self, status_code=200, json_data=None, text="", url="https://example.test"):
        self.status_code = status_code
        self._json_data = json_data if json_data is not None else {}
        self.text = text
        self.url = url

    # Returns the configured JSON response body
    def json(self):
        return self._json_data

    # Raises an HTTPError for configured error status codes
    def raise_for_status(self):
        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            response.url = self.url
            raise requests.HTTPError(f"HTTP {self.status_code}", response=response)


# Creates a requests HTTPError carrying the selected status code
def make_http_error(status_code):
    response = requests.Response()
    response.status_code = status_code
    response.url = "https://api.spotify.com/test"
    return requests.HTTPError(f"HTTP {status_code}", response=response)


# Returns representative current Pathfinder track metadata
def web_track_fixture():
    return {"__typename": "Track", "uri": TRACK_URI, "name": "My Love", "duration": {"totalMilliseconds": 259933}, "sharingInfo": {"shareUrl": "https://open.spotify.com/track/4N1MFKjziFHH4IS3RYYUrU?si=track"}, "firstArtist": {"items": [{"uri": "spotify:artist:1dgdvbogmctybPrGEcnYf6", "profile": {"name": "Route 94"}}]}, "albumOfTrack": {"uri": "spotify:album:4ZD1KnBqghtSAEyqrZAkU4", "name": "My Love", "sharingInfo": {"shareUrl": "https://open.spotify.com/album/4ZD1KnBqghtSAEyqrZAkU4?si=album"}, "coverArt": {"sources": [{"url": "https://i.scdn.co/image/track-small.jpg", "width": 64, "height": 64}, {"url": "https://i.scdn.co/image/track-large.jpg", "width": 640, "height": 640}]}}}


# Returns representative current Pathfinder playlist metadata
def web_playlist_fixture():
    return {"uri": PLAYLIST_URI, "name": "Cordas", "revisionId": "revision-1", "sharingInfo": {"shareUrl": "https://open.spotify.com/playlist/1yjvJQztEdo7pKTpIsIdOa?si=playlist"}, "ownerV2": {"data": {"uri": "spotify:user:brenda.juris", "name": "Agnes Hali", "username": "brenda.juris"}},
        "images": {
            "items": [
                {
                    "sources": [
                        {"url": "https://i.scdn.co/image/small.jpg", "width": 64, "height": 64},
                        {"url": "https://i.scdn.co/image/large.jpg", "width": 640, "height": 640},
                    ]
                }
            ]
        },
    }


class SpotifyWebBackendTests(unittest.TestCase):
    # Resets shared backend state before each focused test
    def setUp(self):
        monitor.TOKEN_SOURCE = "cookie"
        monitor.SP_APP_CLIENT_ID = "your_spotify_app_client_id"
        monitor.SP_APP_CLIENT_SECRET = "your_spotify_app_client_secret"
        monitor.SP_CACHED_WEB_ACCESS_TOKEN = None
        monitor.SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 0
        monitor.SP_CACHED_WEB_CLIENT_ID = ""
        monitor.SP_CACHED_PLAYLIST_QUERY_HASH = ""
        monitor.SP_CACHED_TRACK_QUERY_HASH = ""
        monitor.SP_CACHED_FOLLOW_QUERY_HASHES.clear()
        monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED = False
        monitor.SP_WEB_TRACK_BACKEND_PREFERRED = False
        monitor.SP_WEB_PLAYLIST_API_FAILURES = 0
        monitor.SP_WEB_TRACK_API_FAILURES = 0
        monitor.SP_WEB_PLAYLIST_URIS.clear()
        monitor.SP_CACHED_OAUTH_APP_TOKEN = None
        monitor.SPOTIPY_AVAILABLE = None
        monitor.SPOTIPY_IMPORT_WARNING_SHOWN = False
        monitor.VERBOSE_MODE = False
        monitor.DEBUG_MODE = False

    # Verifies the embedded v61 cipher generates the expected TOTP
    def test_generates_expected_v61_totp(self):
        self.assertEqual(monitor.TOTP_VERSION, 61)
        self.assertEqual(monitor.generate_totp().at(1700000000), "371599")

    # Verifies anonymous token retrieval skips the authenticated validity probe
    def test_anonymous_token_skips_authenticated_validity_probe(self):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {"accessToken": "anonymous-token", "accessTokenExpirationTimestampMs": 1700003600000, "clientId": "web-client"}
        session = Mock()
        session.get.return_value = response

        with patch.object(monitor.req, "Session", return_value=session), patch.object(monitor, "fetch_server_time", return_value=1700000000), patch.object(monitor, "check_token_validity") as validity_check:
            token_data = monitor.refresh_access_token_from_sp_dc("")

        self.assertEqual(token_data["access_token"], "anonymous-token")
        self.assertEqual(session.get.call_count, 1)
        self.assertEqual(session.get.call_args.kwargs["params"]["totpVer"], 61)
        validity_check.assert_not_called()

    # Verifies startup output describes only metadata backends available from configuration
    def test_describes_configured_metadata_backend(self):
        self.assertEqual(monitor.spotify_get_metadata_backend_description(), "web player")
        monitor.SP_APP_CLIENT_ID = "legacy-client"
        monitor.SP_APP_CLIENT_SECRET = "legacy-secret"
        with patch.object(monitor.importlib.util, "find_spec", return_value=Mock()):
            self.assertEqual(monitor.spotify_get_metadata_backend_description(), "automatic (legacy Web API + web player)")
        with patch.object(monitor.importlib.util, "find_spec", return_value=None):
            self.assertEqual(monitor.spotify_get_metadata_backend_description(), "web player (legacy OAuth unavailable: Spotipy missing)")

    # Verifies module execution does not import Spotipy when legacy credentials are absent
    def test_module_runs_without_spotipy(self):
        source = f"module = runpy.run_path({str(CLI_PATH)!r}, run_name='spotify_monitor_import_test'); print(module['spotify_get_metadata_backend_description']())"
        result = run_isolated(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "web player")

    # Verifies cookie-mode CLI startup reaches monitoring without Spotipy or network access
    def test_cookie_cli_startup_runs_without_spotipy(self):
        argv = [str(CLI_PATH), "spotify-user", "--spotify-dc-cookie", "cookie-value", "--env-file", "none", "--disable-logging"]
        source = f"module = runpy.run_path({str(CLI_PATH)!r}, run_name='spotify_monitor_runtime_test'); runtime = module['main'].__globals__; runtime['sys'].argv = {argv!r}; runtime['CLEAR_SCREEN'] = False; runtime['find_config_file'] = lambda path: None; runtime['check_internet'] = lambda: True; runtime['spotify_monitor_friend_uri'] = lambda *args, **kwargs: None; runtime['signal'].signal = lambda *args, **kwargs: None; module['main']()"
        result = run_isolated(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"\* Metadata backend:\s+web player")
        self.assertNotIn("Spotipy is unavailable", result.stdout)

    # Verifies a missing Spotipy dependency returns no token and warns only once
    def test_missing_spotipy_returns_none_and_warns_once(self):
        missing_modules = {"spotipy": None, "spotipy.oauth2": None, "spotipy.cache_handler": None}
        output = io.StringIO()
        with patch.dict(sys.modules, missing_modules), redirect_stdout(output):
            first = monitor.spotify_get_access_token_from_oauth_app("legacy-client", "legacy-secret")
            second = monitor.spotify_get_access_token_from_oauth_app("legacy-client", "legacy-secret")
        self.assertIsNone(first)
        self.assertIsNone(second)
        self.assertEqual(output.getvalue().count("* Warning: Spotipy is unavailable."), 1)
        self.assertIn("spotify_monitor[legacy-oauth]", output.getvalue())

    # Verifies missing Spotipy falls through to anonymous web-player metadata
    def test_missing_spotipy_falls_back_to_web_metadata(self):
        monitor.SP_APP_CLIENT_ID = "legacy-client"
        monitor.SP_APP_CLIENT_SECRET = "legacy-secret"
        normalized = monitor.spotify_normalize_web_track(web_track_fixture())
        missing_modules = {"spotipy": None, "spotipy.oauth2": None, "spotipy.cache_handler": None}
        with patch.dict(sys.modules, missing_modules), patch.object(monitor, "spotify_get_track_info_web", return_value=normalized) as web, redirect_stdout(io.StringIO()):
            result = monitor.spotify_get_track_info("cookie-token", TRACK_URI)
        self.assertEqual(result, normalized)
        web.assert_called_once_with(TRACK_URI)

    # Verifies mocked Spotipy keeps the legacy OAuth token flow working
    def test_mocked_spotipy_legacy_oauth_success(self):
        auth_manager = Mock()
        auth_manager.get_access_token.return_value = "legacy-token"
        credentials_factory = Mock(return_value=auth_manager)
        spotipy_module = types.ModuleType("spotipy")
        oauth_module = types.ModuleType("spotipy.oauth2")
        cache_module = types.ModuleType("spotipy.cache_handler")
        setattr(oauth_module, "SpotifyClientCredentials", credentials_factory)
        setattr(cache_module, "CacheFileHandler", Mock())
        setattr(cache_module, "MemoryCacheHandler", Mock())
        setattr(spotipy_module, "oauth2", oauth_module)
        setattr(spotipy_module, "cache_handler", cache_module)
        modules = {"spotipy": spotipy_module, "spotipy.oauth2": oauth_module, "spotipy.cache_handler": cache_module}
        with patch.object(monitor, "SP_APP_TOKENS_FILE", ""), patch.dict(sys.modules, modules):
            result = monitor.spotify_get_access_token_from_oauth_app("legacy-client", "legacy-secret")
        self.assertEqual(result, "legacy-token")
        credentials_factory.assert_called_once()
        auth_manager.get_access_token.assert_called_once_with(as_dict=False)

    # Verifies memory-only OAuth mode ignores a configured cache file
    def test_oauth_memory_mode_never_constructs_file_cache(self):
        auth_manager = Mock()
        auth_manager.get_access_token.return_value = "legacy-token"
        credentials_factory = Mock(return_value=auth_manager)
        file_cache_factory = Mock()
        memory_cache = Mock()
        memory_cache_factory = Mock(return_value=memory_cache)
        spotipy_module = types.ModuleType("spotipy")
        oauth_module = types.ModuleType("spotipy.oauth2")
        cache_module = types.ModuleType("spotipy.cache_handler")
        setattr(oauth_module, "SpotifyClientCredentials", credentials_factory)
        setattr(cache_module, "CacheFileHandler", file_cache_factory)
        setattr(cache_module, "MemoryCacheHandler", memory_cache_factory)
        setattr(spotipy_module, "oauth2", oauth_module)
        setattr(spotipy_module, "cache_handler", cache_module)
        modules = {"spotipy": spotipy_module, "spotipy.oauth2": oauth_module, "spotipy.cache_handler": cache_module}
        with patch.object(monitor, "SP_APP_TOKENS_FILE", ".spotify-monitor-oauth-app.json"), patch.dict(sys.modules, modules):
            result = monitor.spotify_get_access_token_from_oauth_app("legacy-client", "legacy-secret", use_file_cache=False)
        self.assertEqual(result, "legacy-token")
        file_cache_factory.assert_not_called()
        memory_cache_factory.assert_called_once_with()
        self.assertIs(credentials_factory.call_args.kwargs["cache_handler"], memory_cache)


    # Verifies help exits successfully without network access or Spotipy
    def test_help_is_offline(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: spotify_monitor", result.stdout)

    # Verifies version output exits successfully without network access or Spotipy
    def test_version_is_offline(self):
        result = run_cli("--version")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("spotify_monitor.py v3.0.2", result.stdout)

    # Verifies config generation emits valid Python without network access or Spotipy
    def test_generate_config_is_offline(self):
        result = run_cli("--generate-config")
        self.assertEqual(result.returncode, 0, result.stderr)
        compile(result.stdout, "<generated-config>", "exec")
        self.assertIn('TOKEN_SOURCE = "cookie"', result.stdout)

    # Verifies successful legacy track and playlist requests retain their existing shapes
    def test_legacy_web_api_success(self):
        track_response = FakeResponse(json_data={"duration_ms": 259933, "uri": TRACK_URI, "name": "My Love", "external_urls": {"spotify": "https://open.spotify.com/track/4N1MFKjziFHH4IS3RYYUrU"}, "artists": [{"uri": "spotify:artist:1dgdvbogmctybPrGEcnYf6", "name": "Route 94", "external_urls": {"spotify": "https://open.spotify.com/artist/1dgdvbogmctybPrGEcnYf6"}}], "album": {"uri": "spotify:album:4ZD1KnBqghtSAEyqrZAkU4", "name": "My Love", "external_urls": {"spotify": "https://open.spotify.com/album/4ZD1KnBqghtSAEyqrZAkU4"}, "images": [{"url": "https://i.scdn.co/image/track-small.jpg", "width": 64}, {"url": "https://i.scdn.co/image/track-large.jpg", "width": 640}]}})
        playlist_response = FakeResponse(json_data={"name": "Cordas", "owner": {"display_name": "Agnes Hali"},
            "images": [
                {"url": "https://i.scdn.co/image/small.jpg", "width": 64, "height": 64},
                {"url": "https://i.scdn.co/image/large.jpg", "width": 640, "height": 640},
            ],
        })
        with patch.object(monitor.SESSION, "get", side_effect=[track_response, playlist_response]):
            track = monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            owner, owner_image = monitor.spotify_get_playlist_owner_and_image("legacy-token", PLAYLIST_URI, oauth_app=True)
        self.assertEqual(track["sp_track_duration"], 259)
        self.assertEqual(track["sp_artist_name"], "Route 94")
        self.assertEqual(track["sp_album_image_url"], "https://i.scdn.co/image/track-large.jpg")
        self.assertEqual(owner, "Agnes Hali")
        self.assertEqual(owner_image, "https://i.scdn.co/image/large.jpg")

    # Verifies one track 403 switches current and later requests to Pathfinder
    def test_track_403_falls_back_and_caches_backend_decision(self):
        normalized = monitor.spotify_normalize_web_track(web_track_fixture())
        output = io.StringIO()
        with patch.object(monitor, "_spotify_get_track_info_api", side_effect=make_http_error(403)) as legacy, patch.object(monitor, "spotify_get_track_info_web", return_value=normalized) as web, patch.object(monitor, "VERBOSE_MODE", True), redirect_stdout(output):
            first = monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            second = monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
        self.assertEqual(first, normalized)
        self.assertEqual(second, normalized)
        self.assertEqual(legacy.call_count, 1)
        self.assertEqual(web.call_count, 2)
        self.assertTrue(monitor.SP_WEB_TRACK_BACKEND_PREFERRED)
        self.assertEqual(output.getvalue().count("Track metadata switched to the web-player backend"), 1)

    # Verifies one playlist 403 switches current and later requests to Pathfinder
    def test_playlist_403_falls_back_and_caches_backend_decision(self):
        normalized = monitor.spotify_normalize_web_playlist(web_playlist_fixture())
        output = io.StringIO()
        with patch.object(monitor, "_spotify_get_playlist_owner_and_image_api", side_effect=make_http_error(403)) as legacy, patch.object(monitor, "spotify_get_playlist_info_web", return_value=normalized) as web, patch.object(monitor, "VERBOSE_MODE", True), redirect_stdout(output):
            first, first_image = monitor.spotify_get_playlist_owner_and_image("legacy-token", PLAYLIST_URI, oauth_app=True)
            second, second_image = monitor.spotify_get_playlist_owner_and_image("legacy-token", PLAYLIST_URI, oauth_app=True)
        self.assertEqual(first, "Agnes Hali")
        self.assertEqual(second, "Agnes Hali")
        self.assertEqual(first_image, "https://i.scdn.co/image/large.jpg")
        self.assertEqual(second_image, "https://i.scdn.co/image/large.jpg")
        self.assertEqual(legacy.call_count, 1)
        self.assertEqual(web.call_count, 2)
        self.assertTrue(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)
        self.assertEqual(output.getvalue().count("Playlist metadata switched to the web-player backend"), 1)

    # Verifies a curated-playlist 404 uses web metadata only for that URI and preserves legacy access elsewhere
    def test_playlist_404_detects_curated_owner_and_caches_only_that_uri(self):
        curated_fixture = web_playlist_fixture()
        curated_fixture["ownerV2"]["data"] = {"uri": "spotify:user:spotify", "name": "Spotify", "username": "spotify"}
        normalized = monitor.spotify_normalize_web_playlist(curated_fixture)
        legacy_image = "https://i.scdn.co/image/legacy.jpg"
        with patch.object(monitor, "_spotify_get_playlist_owner_and_image_api", side_effect=[make_http_error(404), ("Agnes Hali", legacy_image)]) as legacy, patch.object(monitor, "spotify_get_playlist_info_web", return_value=normalized) as web, redirect_stdout(io.StringIO()):
            first = monitor.spotify_get_playlist_owner_and_image("legacy-token", PLAYLIST_URI, oauth_app=True)
            second = monitor.spotify_get_playlist_owner_and_image("legacy-token", PLAYLIST_URI, oauth_app=True)
            third = monitor.spotify_get_playlist_owner_and_image("legacy-token", OTHER_PLAYLIST_URI, oauth_app=True)
        self.assertEqual(first, ("Spotify", "https://i.scdn.co/image/large.jpg"))
        self.assertEqual(second, first)
        self.assertEqual(third, ("Agnes Hali", legacy_image))
        self.assertEqual(legacy.call_args_list, [call("legacy-token", PLAYLIST_URI, True), call("legacy-token", OTHER_PLAYLIST_URI, True)])
        self.assertEqual(web.call_args_list, [call(PLAYLIST_URI), call(PLAYLIST_URI)])
        self.assertEqual(monitor.SP_WEB_PLAYLIST_URIS, {PLAYLIST_URI})
        self.assertEqual(monitor.SP_WEB_PLAYLIST_API_FAILURES, 0)
        self.assertFalse(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)

    # Verifies a normal-playlist 404 identifies an app-wide legacy restriction and latches the web backend
    def test_playlist_404_for_normal_owner_latches_web_backend(self):
        normalized = monitor.spotify_normalize_web_playlist(web_playlist_fixture())
        with patch.object(monitor, "_spotify_get_playlist_owner_and_image_api", side_effect=make_http_error(404)) as legacy, patch.object(monitor, "spotify_get_playlist_info_web", return_value=normalized) as web, redirect_stdout(io.StringIO()):
            first = monitor.spotify_get_playlist_owner_and_image("legacy-token", PLAYLIST_URI, oauth_app=True)
            second = monitor.spotify_get_playlist_owner_and_image("legacy-token", OTHER_PLAYLIST_URI, oauth_app=True)
        self.assertEqual(first, ("Agnes Hali", "https://i.scdn.co/image/large.jpg"))
        self.assertEqual(second, first)
        legacy.assert_called_once_with("legacy-token", PLAYLIST_URI, True)
        self.assertEqual(web.call_args_list, [call(PLAYLIST_URI), call(OTHER_PLAYLIST_URI)])
        self.assertEqual(monitor.SP_WEB_PLAYLIST_URIS, {PLAYLIST_URI})
        self.assertEqual(monitor.SP_WEB_PLAYLIST_API_FAILURES, 1)
        self.assertTrue(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)

    # Verifies an unresolved playlist 404 remains unclassified and reports both backend failures
    def test_playlist_404_with_web_failure_does_not_cache_or_latch(self):
        with patch.object(monitor, "_spotify_get_playlist_owner_and_image_api", side_effect=make_http_error(404)) as legacy, patch.object(monitor, "spotify_get_playlist_info_web", side_effect=RuntimeError("web unavailable")) as web, redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, "Both Spotify playlist metadata backends failed"):
                monitor.spotify_get_playlist_owner_and_image("legacy-token", PLAYLIST_URI, oauth_app=True)
        legacy.assert_called_once_with("legacy-token", PLAYLIST_URI, True)
        web.assert_called_once_with(PLAYLIST_URI)
        self.assertEqual(monitor.SP_WEB_PLAYLIST_URIS, set())
        self.assertEqual(monitor.SP_WEB_PLAYLIST_API_FAILURES, 0)
        self.assertFalse(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)

    # Verifies a single 404 falls back per call to Pathfinder without latching the whole backend
    def test_track_404_falls_back_per_call_without_latching(self):
        normalized = monitor.spotify_normalize_web_track(web_track_fixture())
        with patch.object(monitor, "_spotify_get_track_info_api", side_effect=make_http_error(404)) as legacy, patch.object(monitor, "spotify_get_track_info_web", return_value=normalized) as web, redirect_stdout(io.StringIO()):
            first = monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            second = monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
        self.assertEqual(first, normalized)
        self.assertEqual(second, normalized)
        self.assertEqual(legacy.call_count, 2)
        self.assertEqual(web.call_count, 2)
        self.assertFalse(monitor.SP_WEB_TRACK_BACKEND_PREFERRED)

    # Verifies repeated non-restricted legacy track failures latch the web backend after the threshold
    def test_track_non_restricted_failures_latch_after_threshold(self):
        normalized = monitor.spotify_normalize_web_track(web_track_fixture())
        with patch.object(monitor, "_spotify_get_track_info_api", side_effect=make_http_error(401)) as legacy, patch.object(monitor, "spotify_get_track_info_web", return_value=normalized) as web, redirect_stdout(io.StringIO()):
            for _ in range(monitor.METADATA_API_FAILURE_LATCH_THRESHOLD - 1):
                monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            self.assertFalse(monitor.SP_WEB_TRACK_BACKEND_PREFERRED)
            monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            self.assertTrue(monitor.SP_WEB_TRACK_BACKEND_PREFERRED)
            monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
        self.assertEqual(legacy.call_count, monitor.METADATA_API_FAILURE_LATCH_THRESHOLD)
        self.assertEqual(web.call_count, monitor.METADATA_API_FAILURE_LATCH_THRESHOLD + 1)

    # Verifies a successful legacy track request resets the consecutive-failure counter
    def test_track_success_resets_failure_counter(self):
        normalized = monitor.spotify_normalize_web_track(web_track_fixture())
        legacy_result = {"sp_track_name": "My Love"}
        side_effects = [make_http_error(500), legacy_result, make_http_error(500), make_http_error(500)]
        with patch.object(monitor, "_spotify_get_track_info_api", side_effect=side_effects), patch.object(monitor, "spotify_get_track_info_web", return_value=normalized), redirect_stdout(io.StringIO()):
            monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            self.assertEqual(monitor.SP_WEB_TRACK_API_FAILURES, 0)
            monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
        self.assertFalse(monitor.SP_WEB_TRACK_BACKEND_PREFERRED)
        self.assertEqual(monitor.SP_WEB_TRACK_API_FAILURES, 2)

    # Verifies repeated non-restricted legacy playlist failures latch the web backend after the threshold
    def test_playlist_non_restricted_failures_latch_after_threshold(self):
        normalized = monitor.spotify_normalize_web_playlist(web_playlist_fixture())
        with patch.object(monitor, "_spotify_get_playlist_owner_and_image_api", side_effect=make_http_error(401)) as legacy, patch.object(monitor, "spotify_get_playlist_info_web", return_value=normalized) as web, redirect_stdout(io.StringIO()):
            for _ in range(monitor.METADATA_API_FAILURE_LATCH_THRESHOLD - 1):
                monitor.spotify_get_playlist_owner_and_image("legacy-token", PLAYLIST_URI, oauth_app=True)
            self.assertFalse(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)
            monitor.spotify_get_playlist_owner_and_image("legacy-token", PLAYLIST_URI, oauth_app=True)
            self.assertTrue(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)
        self.assertEqual(legacy.call_count, monitor.METADATA_API_FAILURE_LATCH_THRESHOLD)

    # Verifies a token response without an expiry field reports an actionable error instead of KeyError
    def test_token_refresh_missing_expiry_is_actionable(self):
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {"accessToken": "anonymous-token", "clientId": "web-client"}
        session = Mock()
        session.get.return_value = response
        with patch.object(monitor.req, "Session", return_value=session), patch.object(monitor, "fetch_server_time", return_value=1700000000):
            with self.assertRaises(Exception) as caught:
                monitor.refresh_access_token_from_sp_dc("")
        self.assertNotIsInstance(caught.exception, KeyError)
        self.assertIn("missing expiry", str(caught.exception))

    # Verifies invalid configured TOTP parameters raise an actionable error
    def test_generate_totp_rejects_invalid_config(self):
        with patch.object(monitor, "TOTP_SECRET_CIPHER_BYTES", ()):
            with self.assertRaises(ValueError):
                monitor.generate_totp()
        with patch.object(monitor, "TOTP_SECRET_CIPHER_BYTES", ("bad", 55)):
            with self.assertRaises(ValueError):
                monitor.generate_totp()
        with patch.object(monitor, "TOTP_VERSION", 0):
            with self.assertRaises(ValueError):
                monitor.generate_totp()

    # Verifies cookie mode without app credentials goes directly to the web backend
    def test_missing_oauth_credentials_uses_web_backend(self):
        normalized = monitor.spotify_normalize_web_track(web_track_fixture())
        with patch.object(monitor, "_spotify_get_track_info_api") as legacy, patch.object(monitor, "spotify_get_track_info_web", return_value=normalized) as web:
            result = monitor.spotify_get_track_info("cookie-token", TRACK_URI)
        self.assertEqual(result, normalized)
        legacy.assert_not_called()
        web.assert_called_once_with(TRACK_URI)

    # Verifies Pathfinder track fields normalize to every value consumed by monitoring
    def test_track_response_normalization(self):
        result = monitor.spotify_normalize_web_track(web_track_fixture())
        self.assertEqual(result["sp_track_duration"], 259)
        self.assertEqual(result["sp_track_name"], "My Love")
        self.assertEqual(result["sp_track_uri"], TRACK_URI)
        self.assertEqual(result["sp_artist_name"], "Route 94")
        self.assertEqual(result["sp_artist_uri"], "spotify:artist:1dgdvbogmctybPrGEcnYf6")
        self.assertEqual(result["sp_artist_url"], "https://open.spotify.com/artist/1dgdvbogmctybPrGEcnYf6?si=1")
        self.assertEqual(result["sp_album_name"], "My Love")
        self.assertEqual(result["sp_album_uri"], "spotify:album:4ZD1KnBqghtSAEyqrZAkU4")
        self.assertEqual(result["sp_album_image_url"], "https://i.scdn.co/image/track-large.jpg")
        self.assertIn("open.spotify.com/track/4N1MFKjziFHH4IS3RYYUrU", result["sp_track_url"])
        self.assertIn("open.spotify.com/album/4ZD1KnBqghtSAEyqrZAkU4", result["sp_album_url"])

    # Verifies Pathfinder playlist owner and name fields normalize for friend listing
    def test_playlist_response_normalization(self):
        result = monitor.spotify_normalize_web_playlist(web_playlist_fixture())
        self.assertEqual(result["sp_playlist_name"], "Cordas")
        self.assertEqual(result["sp_playlist_owner"], "Agnes Hali")
        self.assertEqual(result["sp_playlist_owner_uri"], "spotify:user:brenda.juris")
        self.assertEqual(result["sp_playlist_owner_url"], "https://open.spotify.com/user/brenda.juris?si=1")
        self.assertEqual(result["sp_playlist_image_url"], "https://i.scdn.co/image/large.jpg")

    # Verifies malformed image metadata cannot break otherwise usable Spotify metadata
    def test_malformed_image_metadata_falls_back_to_empty_url(self):
        track = web_track_fixture()
        track["albumOfTrack"]["coverArt"] = {"sources": ["bad", {"url": 7, "width": "wide"}, {"width": 640}]}
        playlist = web_playlist_fixture()
        playlist["images"] = {"items": [{"sources": [None, {"url": [], "width": 640}]}]}
        self.assertEqual(monitor.spotify_normalize_web_track(track)["sp_album_image_url"], "")
        self.assertEqual(monitor.spotify_normalize_web_playlist(playlist)["sp_playlist_image_url"], "")

    # Verifies valid image URLs remain usable when width metadata is absent or malformed
    def test_image_selection_tolerates_missing_widths(self):
        sources = [{"url": "https://i.scdn.co/image/no-width.jpg"}, {"url": "https://i.scdn.co/image/bad-width.jpg", "width": "large"}, {"url": "https://i.scdn.co/image/large.jpg", "width": 640}]
        self.assertEqual(monitor.spotify_select_largest_image_url(sources), "https://i.scdn.co/image/large.jpg")

    # Verifies the previous owner-only helper remains compatible with existing callers
    def test_playlist_owner_compatibility_wrapper(self):
        with patch.object(monitor, "spotify_get_playlist_owner_and_image", return_value=("Agnes Hali", "https://i.scdn.co/image/large.jpg")) as owner_and_image:
            result = monitor.spotify_get_playlist_owner("token", PLAYLIST_URI, oauth_app=True)
        self.assertEqual(result, "Agnes Hali")
        owner_and_image.assert_called_once_with("token", PLAYLIST_URI, True)

    # Verifies the idempotent web-player GraphQL POST is retried while other POSTs are not
    def test_web_player_adapter_retries_post(self):
        self.assertIs(monitor.SESSION.get_adapter(monitor.WEB_PLAYER_QUERY_URL), monitor.web_player_adapter)
        web_player_methods = getattr(monitor.SESSION.get_adapter(monitor.WEB_PLAYER_QUERY_URL), "max_retries").allowed_methods
        default_methods = getattr(monitor.SESSION.get_adapter("https://api.spotify.com/v1/tracks/abc"), "max_retries").allowed_methods
        self.assertIn("POST", web_player_methods)
        self.assertNotIn("POST", default_methods)

    # Verifies anonymous token data is reused until its expiration window
    def test_anonymous_token_caching(self):
        token_data = {"access_token": "anonymous-token", "expires_at": int(time.time()) + 3600, "client_id": "web-client"}
        output = io.StringIO()
        with patch.object(monitor, "refresh_access_token_from_sp_dc", return_value=token_data) as refresh, patch.object(monitor, "VERBOSE_MODE", True), redirect_stdout(output):
            first = monitor.spotify_get_web_access_token_data()
            second = monitor.spotify_get_web_access_token_data()
        self.assertEqual(first, second)
        self.assertEqual(refresh.call_count, 1)
        self.assertEqual(output.getvalue().count("Web-player metadata token refreshed"), 1)

    # Verifies current desktop bundles provide dynamically discovered operation hashes
    def test_persisted_query_discovery_and_cache(self):
        query_hash = "a" * 64
        html = '<script src="https://open.spotifycdn.com/cdn/build/web-player/web-player.test.js"></script>'
        bundle = f'new Query("getTrack","query","{query_hash}",null)'
        with patch.object(monitor.SESSION, "get", side_effect=[FakeResponse(text=html), FakeResponse(text=bundle)]) as get:
            first = monitor.spotify_discover_track_query_hash()
            second = monitor.spotify_discover_track_query_hash()
        self.assertEqual(first, query_hash)
        self.assertEqual(second, query_hash)
        self.assertEqual(get.call_count, 2)

    # Verifies one bundle discovery caches both private follow operation hashes
    def test_follow_query_discovery_caches_query_and_mutation(self):
        query_hash = "c" * 64
        html = '<script src="https://open.spotifycdn.com/cdn/build/web-player/web-player.test.js"></script>'
        bundle = f'new Query("isFollowingUsers","query","{query_hash}",null),new Query("followUsers","mutation","{query_hash}",null)'
        with patch.object(monitor.SESSION, "get", side_effect=[FakeResponse(text=html), FakeResponse(text=bundle)]) as get:
            check_hash = monitor.spotify_discover_follow_query_hash("isFollowingUsers")
            follow_hash = monitor.spotify_discover_follow_query_hash("followUsers")
        self.assertEqual(check_hash, query_hash)
        self.assertEqual(follow_hash, query_hash)
        self.assertEqual(get.call_count, 2)

    # Verifies cookie follow checks send the authenticated client ID and normalize the result
    def test_cookie_follow_check_uses_authenticated_pathfinder_headers(self):
        monitor.SP_CACHED_CLIENT_ID = "cookie-client"
        response = FakeResponse(json_data={"data": {"users": [{"__typename": "User", "uri": "spotify:user:target.user", "following": True}]}})
        with patch.object(monitor, "spotify_discover_follow_query_hash", return_value="c" * 64), patch.object(monitor.SESSION, "post", return_value=response) as post:
            followed = monitor.spotify_user_is_followed("cookie-token", "target.user")
        self.assertTrue(followed)
        request = post.call_args.kwargs
        self.assertEqual(request["headers"]["Client-Id"], "cookie-client")
        self.assertEqual(request["json"]["operationName"], "isFollowingUsers")
        self.assertEqual(request["json"]["variables"], {"uris": ["spotify:user:target.user"]})

    # Verifies client follow checks omit the web-player client ID header
    def test_client_follow_check_uses_desktop_access_token_without_client_id(self):
        monitor.TOKEN_SOURCE = "client"
        monitor.SP_CACHED_CLIENT_ID = "unrelated-web-client"
        response = FakeResponse(json_data={"data": {"users": [{"__typename": "User", "uri": "spotify:user:target.user", "following": False}]}})
        with patch.object(monitor, "spotify_discover_follow_query_hash", return_value="c" * 64), patch.object(monitor.SESSION, "post", return_value=response) as post:
            followed = monitor.spotify_user_is_followed("client-token", "spotify:user:target.user")
        self.assertFalse(followed)
        self.assertNotIn("Client-Id", post.call_args.kwargs["headers"])

    # Verifies follow mutations submit one username and accept a matching success result
    def test_follow_user_submits_private_mutation(self):
        response = FakeResponse(json_data={"data": {"followUsers": {"responses": [{"__typename": "FollowUserResult", "username": "target.user", "result": True}]}}})
        with patch.object(monitor, "spotify_discover_follow_query_hash", return_value="c" * 64), patch.object(monitor.SESSION, "post", return_value=response) as post:
            accepted = monitor.spotify_follow_user("cookie-token", "https://open.spotify.com/user/target.user")
        self.assertTrue(accepted)
        self.assertEqual(post.call_args.kwargs["json"]["operationName"], "followUsers")
        self.assertEqual(post.call_args.kwargs["json"]["variables"], {"usernames": ["target.user"]})

    # Verifies a rejected follow-operation hash triggers one forced rediscovery
    def test_follow_query_error_refreshes_hash(self):
        monitor.SP_CACHED_FOLLOW_QUERY_HASHES["isFollowingUsers"] = "a" * 64
        responses = [FakeResponse(json_data={"errors": [{"message": "PersistedQueryNotFound"}]}), FakeResponse(json_data={"data": {"users": [{"__typename": "User", "uri": "spotify:user:target.user", "following": True}]}})]
        with patch.object(monitor, "spotify_discover_follow_query_hash", side_effect=["a" * 64, "b" * 64]) as discover, patch.object(monitor.SESSION, "post", side_effect=responses):
            followed = monitor.spotify_user_is_followed("cookie-token", "target.user")
        self.assertTrue(followed)
        self.assertEqual(discover.call_args_list, [call("isFollowingUsers", force=False), call("isFollowingUsers", force=True)])

    # Verifies a rejected persisted query triggers one forced hash rediscovery
    def test_persisted_query_error_refreshes_hash(self):
        monitor.SP_CACHED_TRACK_QUERY_HASH = "a" * 64
        token_data = {"access_token": "anonymous-token", "expires_at": int(time.time()) + 3600, "client_id": "web-client"}
        responses = [FakeResponse(json_data={"errors": [{"message": "PersistedQueryNotFound"}]}), FakeResponse(json_data={"data": {"trackUnion": web_track_fixture()}})]
        with patch.object(monitor, "spotify_get_web_access_token_data", return_value=token_data), patch.object(monitor, "spotify_discover_track_query_hash", side_effect=["a" * 64, "b" * 64]) as discover, patch.object(monitor.SESSION, "post", side_effect=responses):
            result = monitor.spotify_web_track_query("getTrack", {"uri": TRACK_URI})
        self.assertEqual(result["trackUnion"]["uri"], TRACK_URI)
        self.assertEqual(discover.call_args_list, [call(force=False), call(force=True)])

    # Verifies a 401 clears the anonymous token and retries the query once
    def test_web_query_401_refreshes_token(self):
        monitor.SP_CACHED_WEB_ACCESS_TOKEN = "expired-token"
        monitor.SP_WEB_ACCESS_TOKEN_EXPIRES_AT = int(time.time()) + 3600
        monitor.SP_CACHED_WEB_CLIENT_ID = "web-client"
        token_data = [{"access_token": "expired-token", "expires_at": int(time.time()) + 3600, "client_id": "web-client"}, {"access_token": "fresh-token", "expires_at": int(time.time()) + 3600, "client_id": "web-client"}]
        responses = [FakeResponse(status_code=401), FakeResponse(json_data={"data": {"playlistV2": web_playlist_fixture()}})]
        with patch.object(monitor, "spotify_get_web_access_token_data", side_effect=token_data) as token, patch.object(monitor, "spotify_discover_playlist_query_hash", return_value="a" * 64), patch.object(monitor.SESSION, "post", side_effect=responses):
            result = monitor.spotify_web_playlist_query("fetchPlaylistMetadata", {"uri": PLAYLIST_URI})
        self.assertEqual(result["playlistV2"]["uri"], PLAYLIST_URI)
        self.assertEqual(token.call_count, 2)
        self.assertIsNone(monitor.SP_CACHED_WEB_ACCESS_TOKEN)


if __name__ == "__main__":
    unittest.main()
