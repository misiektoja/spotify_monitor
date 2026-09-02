"""Tests for VERIFY_SSL: which requests honor it, what is reported while it is off and its shipped default."""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "spotify_monitor.py").read_text(encoding="utf-8")
OUTBOUND_CALLS = sorted(set(re.findall(r"(?:req|requests|SESSION|WEBHOOK_SESSION|session|temp_session|request_session)\.(?:get|post|head)\([^\n]*", SOURCE)))
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/aVeryLongWebhookTokenValue"


# Records the keyword arguments of every request made through it and answers with a success the caller accepts
class RecordingRequests:
    def __init__(self):
        self.calls = []

    # Stands in for requests.get and for Session.post, both called with the destination first
    def __call__(self, url=None, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return SimpleNamespace(status_code=204, headers={}, text="", reason="No Content", json=lambda: {})

    # Returns the TLS setting the single recorded request carried
    def verified(self):
        assert len(self.calls) == 1, f"expected one request, recorded {len(self.calls)}"
        return self.calls[0].get("verify")


@pytest.fixture
# Restores the setting after each test, since it is a module global the whole tool reads
def tls_setting(monkeypatch):
    monkeypatch.setattr(monitor, "VERIFY_SSL", monitor.VERIFY_SSL)
    return monkeypatch


# Verifies the sweep below is looking at real call sites rather than passing on an empty list
def test_the_outbound_request_sweep_finds_the_call_sites():
    assert len(OUTBOUND_CALLS) >= 15, OUTBOUND_CALLS


@pytest.mark.parametrize("call", OUTBOUND_CALLS)
# Verifies every outbound request carries the setting, so no call site can quietly skip the check
def test_every_outbound_request_passes_the_setting(call):
    assert "verify=VERIFY_SSL" in call or "verify=verify" in call, call


@pytest.mark.parametrize("verify", [True, False])
# Verifies the connectivity check carries the configured setting rather than the requests library default
def test_the_connectivity_check_honors_the_setting(tls_setting, verify):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)
    recorder = RecordingRequests()
    tls_setting.setattr(monitor.req, "get", recorder)

    assert monitor.check_internet("https://spotify.example/probe", 5) is True
    assert recorder.verified() is verify


@pytest.mark.parametrize("verify", [True, False])
# Verifies webhook deliveries carry the setting, so one channel cannot skip a check the others make
def test_the_webhook_delivery_honors_the_setting(tls_setting, verify):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)
    tls_setting.setattr(monitor, "WEBHOOK_URL", WEBHOOK_URL)
    recorder = RecordingRequests()
    tls_setting.setattr(monitor.WEBHOOK_SESSION, "post", recorder)

    monitor.post_webhook_request(json={"content": "hello"})

    assert recorder.verified() is verify


@pytest.mark.parametrize("verify, silenced", [(True, False), (False, True)])
# Verifies the certificate warning is silenced only once the reader has chosen to switch verification off
def test_the_certificate_warning_is_silenced_only_while_verification_is_off(tls_setting, verify, silenced):
    disabled = []
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)
    tls_setting.setattr(monitor.urllib3, "disable_warnings", lambda category: disabled.append(category))

    monitor.apply_tls_verification_setting()

    assert bool(disabled) is silenced


# Verifies the doctor passes the setting silently while it is on
def test_the_doctor_passes_while_verification_is_on(tls_setting):
    tls_setting.setattr(monitor, "VERIFY_SSL", True)

    check = next(item for item in monitor.doctor_check_configuration() if "TLS" in item.label)

    assert (check.status, check.advice) == ("PASS", None)


# Verifies the doctor warns while verification is off and names the setting to change and where it is documented
def test_the_doctor_warns_while_verification_is_off(tls_setting):
    tls_setting.setattr(monitor, "VERIFY_SSL", False)

    check = next(item for item in monitor.doctor_check_configuration() if "TLS" in item.label)

    assert check.status == "WARN"
    assert "VERIFY_SSL" in check.detail
    assert check.advice is not None and check.advice.code == "config.insecure"
    assert "VERIFY_SSL" in check.advice.fix
    assert monitor.TLS_GUIDE_URL in check.advice.fix


@pytest.mark.parametrize("monitor_mode", ["friend_activity", "scrobble_health"])
@pytest.mark.parametrize("verify, concise", [(True, False), (False, True)])
# Verifies both monitoring modes record the setting and put it in front of the reader only when it is off
def test_the_summary_promotes_the_row_only_while_verification_is_off(tls_setting, monitor_mode, verify, concise):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)
    tls_setting.setattr(monitor, "MONITOR_MODE", monitor_mode)

    row = next(item for item in monitor.build_startup_summary("target_user", None, None, None) if item.label == "TLS verification")

    assert (row.full, row.concise) == (True, concise)
    assert row.value.startswith("On" if verify else "Off")


# Verifies certificates are verified unless the reader turns that off, in the shipped config and the fallback alike
def test_certificates_are_verified_by_default():
    shipped = monitor.parse_config_content(monitor.CONFIG_BLOCK, "<built-in-config>")

    assert shipped["VERIFY_SSL"] is True
    assert monitor.VERIFY_SSL is True


# Verifies the static-analysis fallback agrees with the shipped default, so a reader of either block sees the same answer
def test_the_static_analysis_fallback_matches_the_shipped_default():
    fallback = re.search(r"^# Do not change values below.*?^exec\(CONFIG_BLOCK", SOURCE, flags=re.MULTILINE | re.DOTALL)

    assert fallback is not None, "the static-analysis default block could not be located"
    assert "VERIFY_SSL = True" in fallback.group(0)
