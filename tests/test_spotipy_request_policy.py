import pytest
from requests.adapters import HTTPAdapter

import spotify_monitor as monitor


# Observes the real library request at the HTTP adapter rather than inspecting a session attribute
@pytest.mark.parametrize("verify", [False, True])
@pytest.mark.parametrize("flow", ["app", "oauth", "pkce", "oauth_refresh", "pkce_refresh"])
def test_spotipy_requests_follow_tls_policy(monkeypatch, verify, flow):
    oauth = pytest.importorskip("spotipy.oauth2")
    cache = pytest.importorskip("spotipy.cache_handler")
    calls = []
    monkeypatch.setattr(monitor, "VERIFY_SSL", verify)
    # Returns a synthetic token without opening a network connection
    def send(self, request, **kwargs):
        calls.append(kwargs["verify"])
        response = monitor.req.Response()
        response.status_code = 200
        response._content = b'{"access_token":"synthetic-token","refresh_token":"synthetic-refresh","expires_in":3600,"token_type":"Bearer"}'
        response.request = request
        return response
    monkeypatch.setattr(HTTPAdapter, "send", send)
    session = monitor.SpotifyAuthSession()
    common = {"client_id": "synthetic-id", "requests_session": session, "cache_handler": cache.MemoryCacheHandler()}
    if flow == "app":
        manager = oauth.SpotifyClientCredentials(client_secret="synthetic-secret", **common)
        manager.get_access_token(as_dict=False)
    else:
        manager_type = oauth.SpotifyPKCE if flow.startswith("pkce") else oauth.SpotifyOAuth
        kwargs = {} if flow.startswith("pkce") else {"client_secret": "synthetic-secret"}
        manager = manager_type(redirect_uri="http://127.0.0.1:8080/callback", open_browser=False, **common, **kwargs)
        if flow.endswith("refresh"):
            manager.refresh_access_token("synthetic-refresh")
        else:
            manager.get_access_token(code="synthetic-code", check_cache=False)
    assert calls == [verify]


@pytest.mark.parametrize("verify", [False, True])
# Exercises the production token factory through Spotipy to the HTTP adapter
def test_app_token_factory_applies_tls_policy(monkeypatch, verify):
    pytest.importorskip("spotipy")
    calls = []
    monkeypatch.setattr(monitor, "VERIFY_SSL", verify)
    monkeypatch.setattr(monitor, "SP_APP_TOKENS_FILE", "")
    monkeypatch.setattr(monitor, "SP_CACHED_OAUTH_APP_TOKEN", None)
    monkeypatch.setattr(monitor, "SPOTIPY_AVAILABLE", True)
    # Returns an uncached token without making a network request
    def send(self, request, **kwargs):
        calls.append(kwargs["verify"])
        response = monitor.req.Response()
        response.status_code = 200
        response._content = b'{"access_token":"synthetic-token","expires_in":3600,"token_type":"Bearer"}'
        response.request = request
        return response
    monkeypatch.setattr(HTTPAdapter, "send", send)
    assert monitor.spotify_get_access_token_from_oauth_app("synthetic-id", "synthetic-secret") == "synthetic-token"
    assert calls == [verify]
