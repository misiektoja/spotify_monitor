"""Verify that optional network work stops on local descriptor exhaustion."""

import errno

import pytest
import requests
from requests.adapters import HTTPAdapter

import spotify_monitor as monitor


# Stops optional fallback requests when the transport reports a local resource limit
def test_optional_network_work_stops_on_resource_exhaustion(monkeypatch, capsys):
    calls = []

    # Injects the real requests exception chain at its transport boundary
    def exhausted_requests(self, request, **kwargs):
        calls.append(str(request.url))
        raise requests.ConnectionError("Connection failed") from OSError(errno.EMFILE, "Too many open files")


    monkeypatch.setattr(HTTPAdapter, "send", exhausted_requests)
    monkeypatch.setattr(monitor, "SESSION", requests.Session())
    monkeypatch.setattr(monitor, "SP_WEB_TRACK_BACKEND_PREFERRED", False)
    with pytest.raises(SystemExit) as stopped:
        monitor.spotify_get_track_info("synthetic-token", "spotify:track:0123456789012345678901", oauth_app=True)
    assert stopped.value.code == 1
    assert len(calls) == 1
    assert "file descriptors" in capsys.readouterr().out
