"""Shared fixtures keeping module-level monitor state from leaking between tests."""

import copy
import ipaddress
import os
import signal
import socket
import types
import webbrowser

import pytest

import spotify_monitor as monitor


# Every module global as the import left it. main(), the config loader and the dotenv code rebind or mutate
# settings and caches outside monkeypatch, and a test that relies on such a leftover passes or fails depending
# on what ran before it on the same worker. Recording every name rather than a list cannot miss a new global
_BASELINE_GLOBALS = {name: value for name, value in vars(monitor).items() if not name.startswith("__")}
_BASELINE_CONTENTS = {name: copy.deepcopy(value) for name, value in _BASELINE_GLOBALS.items() if type(value) in (dict, list, set)}

# Attributes the module's functions carry, since some of them keep state there between calls
_BASELINE_FUNCTION_ATTRIBUTES = {name: dict(value.__dict__) for name, value in _BASELINE_GLOBALS.items() if isinstance(value, types.FunctionType)}

# The variables the dotenv loader and main() write to the process environment. Only these are restored,
# because pytest keeps its own entries such as PYTEST_CURRENT_TEST there and expects to find them
_MONITOR_ENVIRONMENT_KEYS = (*monitor.SECRET_KEYS, *monitor.ENVIRONMENT_SETTING_KEYS)
_BASELINE_ENVIRONMENT = {key: os.environ.get(key) for key in _MONITOR_ENVIRONMENT_KEYS}

# Signals main() binds to the monitor's own handlers, which outlive the call that installed them
_MONITOR_SIGNALS = tuple(getattr(signal, name) for name in ("SIGINT", "SIGTERM", "SIGHUP", "SIGUSR1", "SIGUSR2", "SIGCONT", "SIGPIPE", "SIGTRAP", "SIGABRT", "SIGALRM") if hasattr(signal, name))


# Puts a container's import-time contents back in place so references captured elsewhere agree with the module
def _refill(container, saved):
    if container == saved:
        return
    container.clear()
    restored = copy.deepcopy(saved)
    container.extend(restored) if isinstance(container, list) else container.update(restored)


# Returns the module globals and function attributes to their import-time state and drops globals created since
def _restore_module_state():
    for name in [name for name in vars(monitor) if not name.startswith("__") and name not in _BASELINE_GLOBALS]:
        delattr(monitor, name)
    for name, value in _BASELINE_GLOBALS.items():
        if name in _BASELINE_CONTENTS:
            _refill(value, _BASELINE_CONTENTS[name])
        setattr(monitor, name, value)
    for name, attributes in _BASELINE_FUNCTION_ATTRIBUTES.items():
        function = _BASELINE_GLOBALS[name]
        if function.__dict__ != attributes:
            function.__dict__.clear()
            function.__dict__.update(attributes)


# Returns the monitor's environment variables to the values the suite started with
def _restore_environment():
    for key, value in _BASELINE_ENVIRONMENT.items():
        if value is None:
            os.environ.pop(key, None)
        elif os.environ.get(key) != value:
            os.environ[key] = value


# Enumerators that read whichever browsers are installed on the machine running the suite
_BROWSER_PROFILE_ENUMERATORS = ("discover_firefox_profiles", "discover_chromium_profiles")
_REAL_BROWSER_PROFILE_ENUMERATORS = {name: getattr(monitor, name) for name in _BROWSER_PROFILE_ENUMERATORS}


@pytest.fixture(autouse=True)
# Keeps the suite away from the real browser profiles of whoever runs it, which are slow to reach and differ per machine
def stub_browser_profile_discovery(monkeypatch):
    for name in _BROWSER_PROFILE_ENUMERATORS:
        monkeypatch.setattr(monitor, name, lambda *arguments, **keywords: [])


@pytest.fixture
# Restores the real enumerators for the tests that exercise them against their own synthetic browser roots
def real_browser_profiles(monkeypatch):
    for name, enumerator in _REAL_BROWSER_PROFILE_ENUMERATORS.items():
        monkeypatch.setattr(monitor, name, enumerator)


# Openers the monitor reaches through the webbrowser module when it hands out a Spotify authorization URL
_BROWSER_OPENER_NAMES = ("open", "open_new", "open_new_tab")


@pytest.fixture(autouse=True)
# Fails any test that reaches a browser opener, so no test run can open a Spotify authorization page on the machine running it
def refuse_browser_opening(monkeypatch):
    attempts = []

    # Records the attempt and raises, so a caller that swallows the error is still caught at teardown
    def refuse(url, *arguments, **keywords):
        attempts.append(str(url))
        raise AssertionError(f"A test reached webbrowser and would have opened {url}")

    for name in _BROWSER_OPENER_NAMES:
        monkeypatch.setattr(webbrowser, name, refuse)
    yield
    assert not attempts, f"A test reached webbrowser and would have opened {attempts}"


# Forward lookups the socket module offers. requests, smtplib, http.client and asyncio all resolve through getaddrinfo
_NAME_LOOKUP_NAMES = ("getaddrinfo", "gethostbyname", "gethostbyname_ex")

# Address families whose connections leave the machine unless the peer is loopback
_INTERNET_FAMILIES = tuple(getattr(socket, name) for name in ("AF_INET", "AF_INET6") if hasattr(socket, name))


# Returns a host as lowercase text without the trailing dot of a fully qualified name
def _host_text(host) -> str:
    if isinstance(host, (bytes, bytearray)):
        host = bytes(host).decode("ascii", "replace")
    return str(host).rstrip(".").lower()


# smtplib resolves the machine's own name for its greeting when that name has no domain, even for a loopback server
_OWN_HOST_NAME = _host_text(socket.gethostname())


# Reports whether a host is a loopback address or localhost, the only peers the suite's own servers listen on
def _is_loopback(host) -> bool:
    text = _host_text(host)
    try:
        address = ipaddress.ip_address(text.split("%", 1)[0])
    except ValueError:
        return text == "localhost"
    mapped = getattr(address, "ipv4_mapped", None)
    return (mapped or address).is_loopback


@pytest.fixture(autouse=True)
# Fails any test that resolves or connects to a host outside loopback, so no test run depends on or contacts a real service
def refuse_network_access(monkeypatch):
    attempts = []

    # Records the attempt and raises, so a caller that swallows the error is still caught at teardown
    def refuse(action, host):
        attempts.append(f"{action} {host}")
        raise AssertionError(f"A test tried to {action} {host}, tests must stay offline")

    # Wraps one lookup function so it only answers for loopback names and the machine's own name
    def guard_lookup(name):
        lookup = getattr(socket, name)

        # Refuses a lookup of any other host before a DNS query is sent
        def guarded(host, *arguments, **keywords):
            if host is not None and not _is_loopback(host) and _host_text(host) != _OWN_HOST_NAME:
                refuse("resolve", host)
            return lookup(host, *arguments, **keywords)
        return guarded

    # Wraps one socket connect method so Internet sockets only reach loopback peers
    def guard_connect(name):
        connect = getattr(socket.socket, name)

        # Refuses a connection to any other host, including one given by address that skips the lookup
        def guarded(sock, address):
            if sock.family in _INTERNET_FAMILIES and isinstance(address, tuple) and len(address) >= 2 and not _is_loopback(address[0]):
                refuse("connect to", f"{address[0]}:{address[1]}")
            return connect(sock, address)
        return guarded

    for name in _NAME_LOOKUP_NAMES:
        monkeypatch.setattr(socket, name, guard_lookup(name))
    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, guard_connect(name))
    yield
    assert not attempts, f"A test tried to reach the network outside loopback: {attempts}"


@pytest.fixture(autouse=True)
# Returns the monitor module, its environment variables and its signal handlers to their starting state after every test
def reset_shared_monitor_state(monkeypatch):
    handlers = {number: signal.getsignal(number) for number in _MONITOR_SIGNALS}
    yield
    # Undone first, because monkeypatch deletes the globals it created and would fail on one the restore already dropped
    monkeypatch.undo()
    _restore_module_state()
    _restore_environment()
    for number, handler in handlers.items():
        if handler is not None and signal.getsignal(number) != handler:
            signal.signal(number, handler)


@pytest.fixture(autouse=True)
# Runs every test from a private directory, so a relative path a test passes to the monitor cannot write into the checkout
def isolate_working_directory(monkeypatch, tmp_path):
    working = tmp_path / "cwd"
    working.mkdir()
    monkeypatch.chdir(working)
