"""OAuth validation and retry boundaries using real Requests and Spotipy objects."""

import errno
import json
import time

import pytest
import requests
from requests.adapters import HTTPAdapter
from spotipy.cache_handler import CacheFileHandler

import spotify_monitor as monitor


@pytest.mark.parametrize("accepted", [False, True])
# Checks the candidate through Spotify without reading or replacing either runtime cache
def test_oauth_validation_bypasses_runtime_caches(monkeypatch, tmp_path, accepted):
    cache = tmp_path / "oauth.json"
    old = {"access_token": "old-app-token", "expires_at": int(time.time()) + 3600, "token_type": "Bearer"}
    CacheFileHandler(cache_path=str(cache)).save_token_to_cache(old)
    original = cache.read_bytes()
    monkeypatch.setattr(monitor, "SP_APP_TOKENS_FILE", str(cache))
    monkeypatch.setattr(monitor, "SP_CACHED_OAUTH_APP_TOKEN", "old-app-token")
    requests_seen = []

    # Responds only to the credential exchange so an old-token probe cannot satisfy validation
    def respond(adapter, request, **kwargs):
        requests_seen.append(request)
        assert request.url == "https://accounts.spotify.com/api/token"
        response = requests.Response()
        response.request = request
        response.status_code = 200 if accepted else 400
        response._content = json.dumps({"access_token": "new-app-token", "expires_in": 3600, "token_type": "Bearer"} if accepted else {"error": "invalid_client"}).encode()
        return response

    monkeypatch.setattr(HTTPAdapter, "send", respond)
    if accepted:
        assert monitor.spotify_get_access_token_from_oauth_app("new-id", "new-secret", use_file_cache=False) == "new-app-token"
    else:
        from spotipy.oauth2 import SpotifyOauthError
        with pytest.raises(SpotifyOauthError):
            monitor.spotify_get_access_token_from_oauth_app("new-id", "new-secret", use_file_cache=False)
    assert len(requests_seen) == 1
    assert cache.read_bytes() == original
    assert monitor.SP_CACHED_OAUTH_APP_TOKEN == "old-app-token"


# Stops cookie refresh at the first local socket failure without trying the init fallback
def test_cookie_resource_failure_does_not_retry(monkeypatch):
    requests_seen = []

    # Supplies Spotify's server time before failing the token request at the transport boundary
    def respond(adapter, request, **kwargs):
        requests_seen.append(request)
        if request.method == "HEAD":
            response = requests.Response()
            response.request = request
            response.status_code = 200
            response.headers["Date"] = "Tue, 15 Sep 2026 12:00:00 GMT"
            return response
        raise requests.ConnectionError("Socket allocation failed") from OSError(errno.EMFILE, "Too many open files")

    monkeypatch.setattr(HTTPAdapter, "send", respond)
    with pytest.raises(SystemExit) as error:
        monitor.refresh_access_token_from_sp_dc("test-cookie")
    assert error.value.code == 1
    assert len([request for request in requests_seen if request.method != "HEAD"]) == 1
