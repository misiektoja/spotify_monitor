"""Tests for VERIFY_SSL: which requests honor it, what is reported while it is off and its shipped default."""

import re
import ast
import ssl
from pathlib import Path
from types import SimpleNamespace

import pytest

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT_ROOT / "spotify_monitor.py").read_text(encoding="utf-8")
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


@pytest.mark.parametrize("verify", [True, False])
# Verifies the SMTP handshake follows the setting, so email is not the one channel that keeps checking certificates
def test_the_smtp_context_honors_the_setting(tls_setting, verify):
    tls_setting.setattr(monitor, "VERIFY_SSL", verify)

    context = monitor.smtp_ssl_context()

    assert context.check_hostname is verify
    assert (context.verify_mode == ssl.CERT_REQUIRED) is verify


# Verifies no SMTP call site builds its own context, which would keep that one connection verifying while the setting is off
def test_only_the_shared_helper_builds_an_smtp_context():
    assert SOURCE.count("ssl.create_default_context()") == 1


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


# Verifies the session Spotipy owns follows the TLS setting, since Spotipy makes those requests itself
def test_the_spotipy_session_follows_the_tls_setting(monkeypatch):
    pytest.importorskip("spotipy")
    captured = {}

    class RecordingAuth:
        def __init__(self, **keywords):
            captured["session"] = keywords["requests_session"]

        def get_access_token(self, as_dict=False):
            return "token"

    monkeypatch.setattr(monitor, "VERIFY_SSL", False)
    monkeypatch.setattr(monitor, "SP_CACHED_OAUTH_APP_TOKEN", None)
    monkeypatch.setattr(monitor, "SP_APP_TOKENS_FILE", "")
    monkeypatch.setattr("spotipy.oauth2.SpotifyClientCredentials", RecordingAuth)

    monitor.spotify_get_access_token_from_oauth_app("client-id", "client-secret", use_file_cache=False)

    assert captured["session"].verify is False


HTTP_METHODS = frozenset(("get", "post", "put", "patch", "delete", "head", "options", "request"))
# The expressions that carry the TLS decision, so a call passing anything else is a second opinion
VERIFY_ARGUMENTS = frozenset(("VERIFY_SSL", "verify",))
# A guard against the sweep silently matching nothing after a rename: the tool has 18 call sites today
MINIMUM_HTTP_CALL_SITES = 18


# Returns every name the module binds to a requests session, so a session added later is swept without editing this
def session_receivers():
    return {node.targets[0].id for node in ast.walk(ast.parse(SOURCE)) if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call) and ast.unparse(node.value.func).endswith("Session")}


# Returns every outbound HTTP call in the module as a line number paired with its keyword arguments
def http_call_sites():
    receivers = {"req", "requests"} | session_receivers()
    for node in ast.walk(ast.parse(SOURCE)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = node.func.value
        if node.func.attr in HTTP_METHODS and isinstance(receiver, ast.Name) and receiver.id in receivers:
            yield node.lineno, {keyword.arg: keyword.value for keyword in node.keywords}


# Verifies every outbound request passes the setting, so a call site added later cannot keep verifying while it is off
def test_every_outbound_request_passes_the_setting():
    calls = list(http_call_sites())

    assert len(calls) >= MINIMUM_HTTP_CALL_SITES, f"the sweep found {len(calls)} HTTP calls, so it no longer matches how requests are made"
    missing = [line for line, keywords in calls if "verify" not in keywords or ast.unparse(keywords["verify"]) not in VERIFY_ARGUMENTS]
    assert not missing, f"spotify_monitor.py lines {missing} make an HTTP call that does not pass the TLS setting"


# Verifies every outbound request carries a deadline, since a call without one hangs the monitoring loop indefinitely
def test_every_outbound_request_carries_a_deadline():
    # A call forwarding **kwargs takes its deadline from the helper that fills them in, which is not readable here
    missing = [line for line, keywords in http_call_sites() if "timeout" not in keywords and None not in keywords]

    assert not missing, f"spotify_monitor.py lines {missing} make an HTTP call without a timeout"
