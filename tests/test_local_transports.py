"""Integration tests that exercise real HTTP and SMTP transports on loopback."""

import json
import socketserver
import threading
from collections.abc import Iterator
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

import spotify_monitor as monitor


# Captures webhook requests and returns configured HTTP response codes
class WebhookRequestHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, Any]] = []
    response_codes: list[int] = [204]

    # Stores one POST request and returns the next configured response
    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        type(self).requests.append({"path": self.path, "headers": dict(self.headers.items()), "body": body})
        response_code = type(self).response_codes.pop(0) if type(self).response_codes else 204
        self.send_response(response_code)
        self.end_headers()

    # Suppresses default request logging during tests
    def log_message(self, format: str, *args: Any) -> None:
        return None


# Runs a webhook capture server on one ephemeral loopback port
@pytest.fixture
def webhook_server() -> Iterator[tuple[str, type[WebhookRequestHandler]]]:
    WebhookRequestHandler.requests = []
    WebhookRequestHandler.response_codes = [204]
    server = ThreadingHTTPServer(("127.0.0.1", 0), WebhookRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/webhook", WebhookRequestHandler
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


# Captures SMTP transactions from smtplib without delivering external email
class SMTPRequestHandler(socketserver.StreamRequestHandler):
    messages: list[bytes] = []
    commands: list[str] = []

    # Implements the SMTP commands used by the production email sender
    def handle(self) -> None:
        self.wfile.write(b"220 localhost test SMTP\r\n")
        self.wfile.flush()
        while True:
            line = self.rfile.readline()
            if not line:
                break
            command = line.decode("utf-8", errors="replace").rstrip("\r\n")
            type(self).commands.append(command)
            upper_command = command.upper()
            if upper_command.startswith(("EHLO ", "HELO ")):
                self.wfile.write(b"250-localhost\r\n250-AUTH PLAIN\r\n250 SIZE 1048576\r\n")
            elif upper_command.startswith("AUTH PLAIN"):
                self.wfile.write(b"235 2.7.0 authentication accepted\r\n")
            elif upper_command.startswith(("MAIL FROM:", "RCPT TO:")):
                self.wfile.write(b"250 2.1.0 accepted\r\n")
            elif upper_command == "DATA":
                self.wfile.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
                self.wfile.flush()
                message_lines = []
                while True:
                    data_line = self.rfile.readline()
                    if data_line == b".\r\n" or not data_line:
                        break
                    message_lines.append(data_line[1:] if data_line.startswith(b"..") else data_line)
                type(self).messages.append(b"".join(message_lines))
                self.wfile.write(b"250 2.0.0 queued\r\n")
            elif upper_command == "QUIT":
                self.wfile.write(b"221 2.0.0 goodbye\r\n")
                self.wfile.flush()
                break
            else:
                self.wfile.write(b"250 2.0.0 accepted\r\n")
            self.wfile.flush()


# Allows the local SMTP server to release its port immediately
class LocalSMTPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


# Runs an SMTP capture server on one ephemeral loopback port
@pytest.fixture
def smtp_server() -> Iterator[tuple[int, type[SMTPRequestHandler]]]:
    SMTPRequestHandler.messages = []
    SMTPRequestHandler.commands = []
    server = LocalSMTPServer(("127.0.0.1", 0), SMTPRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield int(server.server_address[1]), SMTPRequestHandler
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


# Configures Discord delivery to the local HTTP capture server
def configure_local_webhook(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_PROVIDER", "discord")
    monkeypatch.setattr(monitor, "WEBHOOK_URL", url)
    monkeypatch.setattr(monitor, "WEBHOOK_USERNAME", "Local Test")
    monkeypatch.setattr(monitor, "WEBHOOK_HEADERS", {"X-Test-Run": "loopback"})
    monkeypatch.setattr(monitor, "WEBHOOK_SESSION", monitor.req.Session())
    monkeypatch.setattr(monitor, "validate_webhook_url", lambda selected_url=None: True)


# Verifies Discord delivery crosses a real HTTP connection with safe JSON
@pytest.mark.integration
def test_discord_webhook_delivery_over_loopback(monkeypatch: pytest.MonkeyPatch, webhook_server: tuple[str, type[WebhookRequestHandler]]):
    url, handler = webhook_server
    configure_local_webhook(monkeypatch, url)
    result = monitor.send_webhook("Local title", "Local body", "song", force=True, sleeper=lambda _delay: None)
    assert result == 0
    assert len(handler.requests) == 1
    request = handler.requests[0]
    payload = json.loads(request["body"].decode("utf-8"))
    assert request["path"] == "/webhook"
    assert request["headers"]["X-Test-Run"] == "loopback"
    assert payload["username"] == "Local Test"
    assert payload["allowed_mentions"] == {"parse": []}
    assert payload["embeds"][0]["title"] == "Local title"
    assert payload["embeds"][0]["description"] == "Local body"


# Verifies retryable HTTP failures cross the transport twice before success
@pytest.mark.integration
def test_webhook_retry_over_loopback(monkeypatch: pytest.MonkeyPatch, webhook_server: tuple[str, type[WebhookRequestHandler]]):
    url, handler = webhook_server
    handler.response_codes = [503, 204]
    configure_local_webhook(monkeypatch, url)
    delays = []
    result = monitor.send_webhook("Retry title", "Retry body", "error", force=True, sleeper=delays.append)
    assert result == 0
    assert len(handler.requests) == 2
    assert delays == [monitor.WEBHOOK_FALLBACK_RETRY_SECONDS]


# Verifies email delivery crosses a real authenticated SMTP conversation
@pytest.mark.integration
def test_email_delivery_over_loopback(monkeypatch: pytest.MonkeyPatch, smtp_server: tuple[int, type[SMTPRequestHandler]]):
    port, handler = smtp_server
    monkeypatch.setattr(monitor, "SMTP_HOST", "127.0.0.1")
    monkeypatch.setattr(monitor, "SMTP_PORT", port)
    monkeypatch.setattr(monitor, "SMTP_USER", "local-user")
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "local-password")
    monkeypatch.setattr(monitor, "SENDER_EMAIL", "sender@example.test")
    monkeypatch.setattr(monitor, "RECEIVER_EMAIL", "receiver@example.test")
    result = monitor.send_email("Local subject", "Plain body", "<strong>HTML body</strong>", False, smtp_timeout=5)
    assert result == 0
    assert len(handler.messages) == 1
    message = BytesParser(policy=policy.default).parsebytes(handler.messages[0])
    assert message["From"] == "sender@example.test"
    assert message["To"] == "receiver@example.test"
    assert message["Subject"] == "Local subject"
    plain_body = message.get_body(preferencelist=("plain",))
    html_body = message.get_body(preferencelist=("html",))
    assert plain_body is not None
    assert html_body is not None
    assert plain_body.get_content().strip() == "Plain body"
    assert html_body.get_content().strip() == "<strong>HTML body</strong>"
    assert any(command.startswith("AUTH PLAIN ") for command in handler.commands)
