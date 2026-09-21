"""Shared fixtures keeping module-level monitor state from leaking between tests."""

import pytest

import spotify_monitor as monitor


# Module globals the dotenv, secret-precedence and setup code mutate in place, so one test cannot bias the next.
# A cache left populated here changes what a later test sees and fails only in a full run, never on its own
_SHARED_STATE_NAMES = (
    "SECRET_SOURCES",
    "DOTENV_MANAGED_KEYS",
    "DOTENV_BASE_VALUES",
    "DOTENV_RELOAD_STATE",
    "EXPORTED_SECRET_KEYS",
    "EXPORTED_ENVIRONMENT_KEYS",
    "COMMAND_LINE_SECRET_KEYS",
    "_WIZARD_BROWSER_LOGIN_COUNTS",
)


# Returns a snapshot that survives in-place mutation of the original container
def _snapshot(value):
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (list, set)):
        return type(value)(value)
    return value


# Restores a container's contents in place so references captured elsewhere still see the reset value
def _restore(current, saved):
    if isinstance(current, dict) and isinstance(saved, dict):
        current.clear()
        current.update(saved)
        return current
    if isinstance(current, (list, set)) and isinstance(saved, (list, set)):
        current.clear()
        current.update(saved) if isinstance(current, set) else current.extend(saved)
        return current
    return saved


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


@pytest.fixture(autouse=True)
# Resets the shared dotenv and secret state after every test, since these are mutated rather than reassigned
def reset_shared_monitor_state():
    saved = {name: _snapshot(getattr(monitor, name)) for name in _SHARED_STATE_NAMES if hasattr(monitor, name)}
    yield
    for name, value in saved.items():
        setattr(monitor, name, _restore(getattr(monitor, name, None), value))


@pytest.fixture(autouse=True)
# Runs every test from a private directory, so a relative path a test passes to the monitor cannot write into the checkout
def isolate_working_directory(monkeypatch, tmp_path):
    working = tmp_path / "cwd"
    working.mkdir()
    monkeypatch.chdir(working)
