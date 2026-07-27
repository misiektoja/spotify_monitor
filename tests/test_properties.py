"""Property-based tests for parsing, serialization and secret safety."""

from io import StringIO
from urllib.parse import quote
from unittest.mock import patch

import pytest
from dotenv import dotenv_values
from hypothesis import given
from hypothesis import strategies as st

import spotify_monitor as monitor


USER_ID_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
SAFE_TEXT = st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"), max_size=200)
BMP_TEXT = st.text(alphabet=st.characters(max_codepoint=0xFFFF, blacklist_categories=("Cs",), blacklist_characters="\x00"), max_size=200)


# Verifies every supported target representation normalizes to the same user ID
@given(st.text(alphabet=USER_ID_ALPHABET, min_size=1, max_size=80).filter(lambda value: value not in (".", "..")))
def test_target_forms_round_trip(user_id: str):
    encoded = quote(user_id, safe="")
    forms = (user_id, f"spotify:user:{encoded}", f"https://open.spotify.com/user/{encoded}", f"https://open.spotify.com/user/{encoded}?si=property")
    for value in forms:
        assert monitor.normalize_spotify_user_id(value) == user_id


# Verifies whitespace and control characters cannot survive target normalization
@given(st.text(alphabet=USER_ID_ALPHABET, min_size=1, max_size=40), st.sampled_from([" ", "\t", "\n", "\r", "\x00", "\x7f", "\x81"]))
def test_target_controls_are_rejected(prefix: str, forbidden: str):
    with pytest.raises(ValueError):
        monitor.normalize_spotify_user_id(f"{prefix}{forbidden}suffix")


# Verifies generated Python config literals preserve supported string values
@given(BMP_TEXT, st.booleans())
def test_config_string_format_round_trip(value: str, prefer_double_quotes: bool):
    namespace: dict[str, object] = {}
    literal = monitor._format_config_value(value, prefer_double_quotes)
    exec(f"VALUE = {literal}", {}, namespace)
    assert namespace["VALUE"] == value


# Records the deferred supplementary-Unicode config serialization limitation
@pytest.mark.xfail(reason="Main config serialization needs a release change for supplementary Unicode", strict=True)
def test_config_double_quote_supplementary_unicode_round_trip():
    value = "\U00010000"
    namespace: dict[str, object] = {}
    exec(f"VALUE = {monitor._format_config_value(value, True)}", {}, namespace)
    assert namespace["VALUE"] == value


# Verifies dotenv quoting preserves arbitrary non-NUL secret values
@given(SAFE_TEXT)
def test_dotenv_secret_format_round_trip(value: str):
    rendered = f"SP_DC_COOKIE={monitor._format_dotenv_value(value)}\n"
    parsed = dotenv_values(stream=StringIO(rendered), interpolate=False)
    assert parsed["SP_DC_COOKIE"] == value


# Verifies UTF-8 truncation is bounded, valid and prefix-preserving
@given(SAFE_TEXT, st.integers(min_value=0, max_value=300))
def test_utf8_truncation_preserves_valid_prefix(value: str, max_bytes: int):
    result = monitor.truncate_utf8_bytes(value, max_bytes)
    assert len(result.encode("utf-8")) <= max_bytes
    assert value.startswith(result)


# Verifies configured secrets are always removed from diagnostic text
@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", min_size=8, max_size=80), SAFE_TEXT, SAFE_TEXT)
def test_error_sanitization_removes_configured_secret(secret: str, prefix: str, suffix: str):
    with patch.object(monitor, "SP_DC_COOKIE", secret):
        sanitized = monitor.sanitize_error_text(f"{prefix}{secret}{suffix}")
    assert secret not in sanitized
    assert "<redacted>" in sanitized
