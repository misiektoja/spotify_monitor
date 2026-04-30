import time
import unittest
from unittest.mock import Mock, call, patch

import requests

import spotify_monitor as monitor


TRACK_URI = "spotify:track:4N1MFKjziFHH4IS3RYYUrU"
PLAYLIST_URI = "spotify:playlist:1yjvJQztEdo7pKTpIsIdOa"


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
    return {"__typename": "Track", "uri": TRACK_URI, "name": "My Love", "duration": {"totalMilliseconds": 259933}, "sharingInfo": {"shareUrl": "https://open.spotify.com/track/4N1MFKjziFHH4IS3RYYUrU?si=track"}, "firstArtist": {"items": [{"uri": "spotify:artist:1dgdvbogmctybPrGEcnYf6", "profile": {"name": "Route 94"}}]}, "albumOfTrack": {"uri": "spotify:album:4ZD1KnBqghtSAEyqrZAkU4", "name": "My Love", "sharingInfo": {"shareUrl": "https://open.spotify.com/album/4ZD1KnBqghtSAEyqrZAkU4?si=album"}}}


# Returns representative current Pathfinder playlist metadata
def web_playlist_fixture():
    return {"uri": PLAYLIST_URI, "name": "Cordas", "revisionId": "revision-1", "sharingInfo": {"shareUrl": "https://open.spotify.com/playlist/1yjvJQztEdo7pKTpIsIdOa?si=playlist"}, "ownerV2": {"data": {"uri": "spotify:user:brenda.juris", "name": "Agnes Hali", "username": "brenda.juris"}}}


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
        monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED = False
        monitor.SP_WEB_TRACK_BACKEND_PREFERRED = False

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

    # Verifies successful legacy track and playlist requests retain their existing shapes
    def test_legacy_web_api_success(self):
        track_response = FakeResponse(json_data={"duration_ms": 259933, "uri": TRACK_URI, "name": "My Love", "external_urls": {"spotify": "https://open.spotify.com/track/4N1MFKjziFHH4IS3RYYUrU"}, "artists": [{"uri": "spotify:artist:1dgdvbogmctybPrGEcnYf6", "name": "Route 94", "external_urls": {"spotify": "https://open.spotify.com/artist/1dgdvbogmctybPrGEcnYf6"}}], "album": {"uri": "spotify:album:4ZD1KnBqghtSAEyqrZAkU4", "name": "My Love", "external_urls": {"spotify": "https://open.spotify.com/album/4ZD1KnBqghtSAEyqrZAkU4"}}})
        playlist_response = FakeResponse(json_data={"name": "Cordas", "owner": {"display_name": "Agnes Hali"}})
        with patch.object(monitor.SESSION, "get", side_effect=[track_response, playlist_response]):
            track = monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            owner = monitor.spotify_get_playlist_owner("legacy-token", PLAYLIST_URI, oauth_app=True)
        self.assertEqual(track["sp_track_duration"], 259)
        self.assertEqual(track["sp_artist_name"], "Route 94")
        self.assertEqual(owner, "Agnes Hali")

    # Verifies one track 403 switches current and later requests to Pathfinder
    def test_track_403_falls_back_and_caches_backend_decision(self):
        normalized = monitor.spotify_normalize_web_track(web_track_fixture())
        with patch.object(monitor, "_spotify_get_track_info_api", side_effect=make_http_error(403)) as legacy, patch.object(monitor, "spotify_get_track_info_web", return_value=normalized) as web:
            first = monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
            second = monitor.spotify_get_track_info("legacy-token", TRACK_URI, oauth_app=True)
        self.assertEqual(first, normalized)
        self.assertEqual(second, normalized)
        self.assertEqual(legacy.call_count, 1)
        self.assertEqual(web.call_count, 2)
        self.assertTrue(monitor.SP_WEB_TRACK_BACKEND_PREFERRED)

    # Verifies one playlist 403 switches current and later requests to Pathfinder
    def test_playlist_403_falls_back_and_caches_backend_decision(self):
        normalized = monitor.spotify_normalize_web_playlist(web_playlist_fixture())
        with patch.object(monitor, "_spotify_get_playlist_owner_api", side_effect=make_http_error(403)) as legacy, patch.object(monitor, "spotify_get_playlist_info_web", return_value=normalized) as web:
            first = monitor.spotify_get_playlist_owner("legacy-token", PLAYLIST_URI, oauth_app=True)
            second = monitor.spotify_get_playlist_owner("legacy-token", PLAYLIST_URI, oauth_app=True)
        self.assertEqual(first, "Agnes Hali")
        self.assertEqual(second, "Agnes Hali")
        self.assertEqual(legacy.call_count, 1)
        self.assertEqual(web.call_count, 2)
        self.assertTrue(monitor.SP_WEB_PLAYLIST_BACKEND_PREFERRED)

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
        self.assertIn("open.spotify.com/track/4N1MFKjziFHH4IS3RYYUrU", result["sp_track_url"])
        self.assertIn("open.spotify.com/album/4ZD1KnBqghtSAEyqrZAkU4", result["sp_album_url"])

    # Verifies Pathfinder playlist owner and name fields normalize for friend listing
    def test_playlist_response_normalization(self):
        result = monitor.spotify_normalize_web_playlist(web_playlist_fixture())
        self.assertEqual(result["sp_playlist_name"], "Cordas")
        self.assertEqual(result["sp_playlist_owner"], "Agnes Hali")
        self.assertEqual(result["sp_playlist_owner_uri"], "spotify:user:brenda.juris")
        self.assertEqual(result["sp_playlist_owner_url"], "https://open.spotify.com/user/brenda.juris?si=1")
        self.assertEqual(result["sp_playlist_revision_id"], "revision-1")

    # Verifies anonymous token data is reused until its expiration window
    def test_anonymous_token_caching(self):
        token_data = {"access_token": "anonymous-token", "expires_at": int(time.time()) + 3600, "client_id": "web-client"}
        with patch.object(monitor, "refresh_access_token_from_sp_dc", return_value=token_data) as refresh:
            first = monitor.spotify_get_web_access_token_data()
            second = monitor.spotify_get_web_access_token_data()
        self.assertEqual(first, second)
        self.assertEqual(refresh.call_count, 1)

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
