import ast
import inspect

import pytest

import spotify_monitor as monitor


HOSTILE_NAME = '<img src=x onerror="alert(1)">'
HOSTILE_ESCAPED = "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"

# Interpolations that are safe without escape() because the value is a counter or a flag this tool
# computes itself, never text Spotify returns. Listed explicitly so a new unescaped name cannot slip
# in behind a blanket exemption
ALLOWED_UNESCAPED = frozenset({"listened_songs", "looped_songs", "song_on_loop", "played_for", "playlist_suffix", "completed_pauses", "paused_percentage", "invisible_periods"})

# Helpers that emit their own markup or render only dates, durations and numbers. None of them can carry
# Spotify-supplied text, so escaping their output would only mangle the timestamps users read
SAFE_HELPERS = frozenset({"get_cur_ts", "display_time", "get_date_from_ts", "get_short_date_from_ts", "calculate_timespan", "get_range_of_dates_from_tss", "songs_played_text"})

# Helpers that only wrap markup around HTML that was already escaped, so their argument decides the verdict
PASSTHROUGH_HELPERS = frozenset({"html_autolink_urls", "html_bold_outage_fields", "html_email_body"})


# Collects every HTML notification body the module builds, as (function, source line, expression) triples
def html_body_interpolations():
    tree = ast.parse(inspect.getsource(monitor))
    enclosing = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                enclosing[id(child)] = node.name

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if not any("body_html" in name for name in targets):
            continue
        for part in ast.walk(node.value):
            if isinstance(part, ast.FormattedValue):
                yield enclosing.get(id(node), "<module>"), node.lineno, ast.unparse(part.value)


# Reports whether one interpolated expression is neutralized before it reaches the HTML body
def interpolation_is_safe(expression):
    parsed = ast.parse(expression, mode="eval").body

    if isinstance(parsed, ast.Name):
        # A value already built as escaped HTML, or an allowlisted locally computed value
        return parsed.id.endswith("_html") or "body_html" in parsed.id or parsed.id in ALLOWED_UNESCAPED

    if isinstance(parsed, ast.Call):
        function = parsed.func
        name = function.id if isinstance(function, ast.Name) else getattr(function, "attr", "")
        if name in PASSTHROUGH_HELPERS:
            return bool(parsed.args) and interpolation_is_safe(ast.unparse(parsed.args[0]))
        return name in {"escape", "escape_html_attr", "html_text", *SAFE_HELPERS}

    return False


# Confirms every value interpolated into an HTML notification body is escaped at the point it is built
def test_every_html_body_interpolation_is_escaped():
    unsafe = [f"{function}:{line} -> {{{expression}}}" for function, line, expression in html_body_interpolations() if not interpolation_is_safe(expression)]

    assert not unsafe, "unescaped Spotify-supplied text can reach an HTML email body:\n" + "\n".join(unsafe)


# Confirms the sweep above is actually looking at the notification bodies rather than silently finding none
def test_html_body_sweep_covers_every_notification():
    interpolations = list(html_body_interpolations())

    assert len(interpolations) >= 100, "the HTML body sweep stopped finding notification bodies, update its matching"
    assert any(function == "spotify_monitor_friend_uri" for function, _, _ in interpolations)


# Confirms an unescaped interpolation would actually be reported, so the sweep cannot pass vacuously
@pytest.mark.parametrize("expression,expected", [("escape(sp_username)", True), ("html_text(advice.fix)", True), ("escape_html_attr(sp_track_url)", True), ("music_section_html", True), ("listened_songs", True), ("sp_username", False), ("sp_track", False), ("sp_track_url", False), ("spotify_convert_uri_to_url(uri)", False)])
def test_interpolation_safety_rule(expression, expected):
    assert interpolation_is_safe(expression) is expected


# Confirms every link address in an HTML body is attribute-escaped, not only the link text
def test_every_html_attribute_is_escaped():
    source = inspect.getsource(monitor)
    raw_attributes = [line.strip() for line in source.splitlines() if ('href=\\"{' in line or 'href="{' in line) and "escape_html_attr(" not in line]

    assert not raw_attributes, "an unescaped href can be broken out of by a crafted value:\n" + "\n".join(raw_attributes)


@pytest.mark.parametrize("value,expected", [('x" onmouseover="alert(1)', "x&quot; onmouseover=&quot;alert(1)"), ("a&b", "a&amp;b"), ("<script>", "&lt;script&gt;"), (None, ""), ("", "")])
# Confirms attribute values cannot break out of a quoted href or src
def test_escape_html_attr(value, expected):
    assert monitor.escape_html_attr(value) == expected


# Confirms a hostile display name is neutralized rather than passed through as markup
def test_hostile_display_name_is_escaped():
    from html import escape

    assert escape(HOSTILE_NAME) == HOSTILE_ESCAPED
    assert "<img" not in escape(HOSTILE_NAME)
