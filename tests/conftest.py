"""Shared fixtures keeping module-level monitor state from leaking between tests."""

import pytest

import spotify_monitor as monitor


# Module globals the dotenv and secret-precedence code mutates in place, so one test cannot bias the next
_SHARED_STATE_NAMES = (
    "SECRET_SOURCES",
    "DOTENV_MANAGED_KEYS",
    "DOTENV_BASE_VALUES",
    "DOTENV_RELOAD_STATE",
    "EXPORTED_SECRET_KEYS",
    "EXPORTED_ENVIRONMENT_KEYS",
    "COMMAND_LINE_SECRET_KEYS",
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


@pytest.fixture(autouse=True)
# Resets the shared dotenv and secret state after every test, since these are mutated rather than reassigned
def reset_shared_monitor_state():
    saved = {name: _snapshot(getattr(monitor, name)) for name in _SHARED_STATE_NAMES if hasattr(monitor, name)}
    yield
    for name, value in saved.items():
        setattr(monitor, name, _restore(getattr(monitor, name, None), value))
