"""Terminal colour contract tests for the coloured output layer."""

import re
from io import StringIO
from pathlib import Path

import pytest

import spotify_monitor as monitor


CHANGE_REPORT_LINES = ("*** Friend got INACTIVE after listening to music for 45 minutes", "*** Friend played music from Sat 22 Nov 16:54 to 17:58", "User plays song on LOOP (3 times)")


# Enables colour with a known style map so assertions do not depend on the shipped theme
@pytest.fixture
def colored(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    return styles


# Reads a block the template ships commented out, as the parser would see it once uncommented
def uncomment_block(first_line):
    lines = monitor.CONFIG_BLOCK.split("\n")
    start = next(index for index, line in enumerate(lines) if line.startswith(first_line))
    end = next(index for index in range(start, len(lines)) if lines[index].rstrip() == "# }")
    return "\n".join(line[2:] if line.startswith("# ") else line[1:] for line in lines[start:end + 1])


# Verifies the shipped config template and the built-in theme describe exactly the same keys
def test_config_template_theme_matches_the_built_in_theme():
    values = monitor.parse_config_content(monitor.CONFIG_BLOCK, "<built-in-config>")
    commented = monitor.parse_config_content(uncomment_block("# COLOR_THEME = {"), "<built-in-config>")

    assert values["COLORED_OUTPUT"] is True
    assert "COLOR_THEME" not in values
    assert commented["COLOR_THEME"] == monitor.DEFAULT_COLOR_THEME


# Verifies a configuration that sets the commented-out theme is still accepted, since older files all set it
def test_a_config_setting_the_theme_is_still_accepted(tmp_path):
    config = tmp_path / "monitor.conf"
    config.write_text('COLOR_THEME = { "username": "green" }\n', encoding="utf-8")

    assert monitor.parse_config_content(config.read_text(encoding="utf-8"), str(config)) == {"COLOR_THEME": {"username": "green"}}


# Verifies every style word used by the shipped theme resolves, allowing a deliberately uncoloured part
def test_default_theme_styles_all_resolve():
    for name, value in monitor.DEFAULT_COLOR_THEME.items():
        assert monitor._build_ansi_sequence(value) or value == "", name


# Verifies the Timestamp label is left uncoloured, matching the sibling monitors
def test_timestamp_label_is_uncolored(colored):
    assert monitor.DEFAULT_COLOR_THEME["timestamp_label"] == ""
    assert "timestamp_label" not in colored
    assert monitor._colorize_line("Timestamp:\t\t\tWed 26 Aug 2026, 20:23:03") == f"Timestamp:\t\t\t{colored['timestamp_value']}Wed 26 Aug 2026, 20:23:03{monitor.ANSI_RESET}"


# Verifies a startup summary row is not block-coloured just because it names a mode
def test_startup_summary_rows_are_not_block_colored(colored):
    for line in ("* Mode:                         Spotify-to-Last.fm scrobble health", "* Target:                       misiektoja", "* Polling interval:             1 minute"):
        assert monitor.ANSI_ESCAPE_RE.sub("", monitor._colorize_line(line)) == line
        assert colored["info"] not in monitor._colorize_line(line)


# Verifies the timer rows whose label names a problem word report a setting, so they keep the plain label and
# green duration of every other summary row instead of turning red
def test_startup_summary_timer_rows_are_not_error_colored(colored):
    for line in ("* Disappeared timer:            3 minutes", "* Error retry timer:            3 minutes"):
        result = monitor._colorize_line(line)

        assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
        assert colored["error"] not in result
        assert f"{colored['duration']}3 minutes{monitor.ANSI_RESET}" in result


# Verifies a debug trace line and a fallback notice are not painted red, while a real problem still is. A debug
# line records an attempt the tool then handles, and a backend switch reports a recovery that worked
@pytest.mark.parametrize("line", [
    "[DEBUG 15:57:30] HTTP GET https://api.spotify.com/v1 [connectivity check], timeout=5, verify_ssl=True",
    "[DEBUG 15:57:30] HTTP HEAD https://open.spotify.com/ [server time] timeout=15",
    "[DEBUG 16:05:53] _spotify_get_track_info_api(): failed for uri=spotify:track:64038SKKJNi7GIAh16NlRr: 403 Client Error: Forbidden for url",
    "* Track metadata switched to the web-player backend after legacy API failures",
])
def test_diagnostic_details_and_fallback_notices_are_not_error_colored(colored, line):
    assert colored["error"] not in monitor._colorize_line(line)


# Verifies the same words still paint a line that really reports a problem
@pytest.mark.parametrize("line", ["Spotify follow verification failed: bad token", "* Error: request timeout after 15 seconds"])
def test_real_problem_lines_stay_error_colored(colored, line):
    assert monitor._colorize_line(line).startswith(colored["error"])


# Verifies a static count stays plain and only a reported change colours its numbers
def test_static_counts_stay_plain_and_changes_are_colored(colored):
    for line in ("Followers:\t\t\t98", "Followings:\t\t\t302", "Public playlists:\t\t41", "Number of friends:\t\t7"):
        assert monitor._colorize_line(line) == line

    changed = monitor._colorize_line("* Followers number changed for user john from 98 to 100 (+2)")
    assert colored["count_up"] in changed


# Verifies colouring only inserts escape sequences and never changes the text itself
@pytest.mark.parametrize("line", [
    "Username:\t\t\tJohn Doe",
    "User URI ID:\t\t\t31nnv6eqt4qswvjhcnknimtxqife",
    "Last played:\t\t\tDaft Punk - Around the World",
    "Played for:\t\t\t2 minutes, 3 seconds - SKIPPED (28%)",
    "Track URL:\t\t\thttps://open.spotify.com/track/abc",
    "*** Friend got ACTIVE after being offline for 1 hour, 2 minutes (Sun 21 Apr 2024, 15:08:45)",
    "* Signal SIGUSR1 received",
    "Timestamp:\t\t\tSun 21 Apr 2024, 15:08:45",
])
def test_colorize_line_never_rewrites_the_text(colored, line):
    assert monitor.ANSI_ESCAPE_RE.sub("", monitor._colorize_line(line)) == line


# Verifies the ASCII startup banner reaches the terminal in one colour. The art contains apostrophes, slashes
# and underscores, so a line rule reading part of it as a name would leave the logo patchy
def test_startup_banner_uses_only_its_own_colours(colored, capsys):
    monitor.print_startup_banner()
    printed = capsys.readouterr().out

    rendered = monitor.apply_color_to_text(printed)

    assert monitor.ANSI_ESCAPE_RE.sub("", rendered) == monitor.ANSI_ESCAPE_RE.sub("", printed)
    assert set(monitor.SGR_SEQUENCE_RE.findall(rendered)) <= {colored["header"], colored["info"], monitor.ANSI_RESET}
    for art_line in monitor.STARTUP_BANNER.splitlines():
        if art_line:
            assert f"{colored['header']}{art_line}{monitor.ANSI_RESET}" in rendered


# Verifies colouring the banner does not change the characters it draws
def test_startup_banner_art_is_unchanged(colored):
    colored_banner = monitor.apply_color_to_text(monitor.STARTUP_BANNER)

    assert monitor.ANSI_ESCAPE_RE.sub("", colored_banner) == monitor.STARTUP_BANNER


# Verifies labelled Spotify rows colour the value with the expected theme part
@pytest.mark.parametrize("line,part", [
    ("Username:\t\t\tJohn Doe", "username"),
    ("User URI ID:\t\t\tsq58", "id"),
    ("Last played:\t\t\tDaft Punk - Around the World", "track"),
    ("Playlist:\t\t\tDiscover Weekly", "playlist"),
    ("Album:\t\t\t\tHomework", "album"),
    ("Duration:\t\t\t7 minutes", "duration"),
])
def test_labelled_rows_use_the_expected_theme_part(colored, line, part):
    assert colored[part] in monitor._colorize_line(line)


# Verifies Doctor status markers are coloured while the rest of the line stays plain
@pytest.mark.parametrize("marker,part", [("PASS", "boolean_true"), ("WARN", "warning"), ("FAIL", "error"), ("SKIP", "info")])
def test_doctor_status_markers_are_colored(colored, marker, part):
    line = f"[{marker}] SP_DC_COOKIE is missing or still a placeholder"

    result = monitor._colorize_line(line)

    assert result == f"{colored[part]}[{marker}]{monitor.ANSI_RESET} SP_DC_COOKIE is missing or still a placeholder"


# Verifies presence keywords pick the active and inactive styles apart
def test_presence_keywords_pick_the_matching_style(colored):
    assert colored["status_active"] in monitor._colorize_line("*** Friend is currently ACTIVE !")
    assert colored["status_inactive"] in monitor._colorize_line("*** Friend got INACTIVE after listening to music for 45 minutes")
    assert colored["status_inactive"] in monitor._colorize_line("*** Friend is OFFLINE for: 3 hours")


# Verifies time highlighting accepts valid clock values without matching numeric port mappings
@pytest.mark.parametrize("value", ["00:00", "23:59", "21:07:39", "~21:07:39", "09:15 PM"])
def test_time_color_regex_accepts_only_complete_clock_values(value):
    assert monitor._TIME_ONLY_RE.fullmatch(value)
    for invalid in ("24:00", "12:60", "8000:8000", "abc12:30", "1:12:30"):
        assert monitor._TIME_ONLY_RE.search(invalid) is None


# Verifies hostile terminal control sequences in Spotify text cannot drive the operator's terminal
@pytest.mark.parametrize("hostile,expected", [
    ("track\x1b[2Jcleared", "track[2Jcleared"),
    ("track\x1b]0;stolen title\x07", "track]0;stolen title"),
    ("visible\rhidden", "visiblehidden"),
    ("bell\x07 and null\x00", "bell and null"),
    ("delete\x7f and c1\x9b[3J", "delete and c1[3J"),
])
def test_sanitize_terminal_text_removes_control_sequences(hostile, expected):
    assert monitor.sanitize_terminal_text(hostile) == expected


# Verifies the tool's own colour codes and ordinary whitespace survive sanitization
def test_sanitize_terminal_text_keeps_colours_and_layout():
    coloured = "\033[36mInfo\033[0m\tvalue\nnext line"

    assert monitor.sanitize_terminal_text(coloured) == coloured


# Verifies Spotify text cannot smuggle an escape sequence between the tool's own colour codes
def test_sanitize_terminal_text_cleans_between_colour_codes():
    smuggled = "\033[36mlabel\033[0m \x1b[2J\033[31mvalue\033[0m"

    assert monitor.sanitize_terminal_text(smuggled) == "\033[36mlabel\033[0m [2J\033[31mvalue\033[0m"


# Builds a Logger writing into two in-memory buffers and returns it with both buffers
def make_logger():
    terminal = StringIO()
    logfile = StringIO()
    logger = monitor.Logger.__new__(monitor.Logger)
    logger.__dict__["terminal"] = terminal
    logger.__dict__["logfile"] = logfile
    return logger, terminal, logfile


# Verifies the log file stays plain text while the terminal receives the coloured version
def test_logger_colors_the_terminal_and_keeps_the_log_plain(colored, monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    logger, terminal, logfile = make_logger()

    logger.write("Username:\t\t\tJohn Doe\n")

    assert colored["username"] in terminal.getvalue()
    assert "\x1b" not in logfile.getvalue()
    assert logfile.getvalue().startswith("Username:")


# Verifies truncation measures plain text so escape sequences never consume the visible width
def test_truncation_runs_before_colour_is_applied(colored, monkeypatch):
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 20)
    logger, terminal, _logfile = make_logger()

    logger.write("Username:\tJohn Doe The Very Long Display Name\n")

    plain = monitor.ANSI_ESCAPE_RE.sub("", terminal.getvalue()).rstrip("\n")
    assert len(plain.expandtabs(8)) == 20
    assert colored["username"] in terminal.getvalue()


# Verifies the terminal-only stream colours output while still neutralizing hostile text
def test_terminal_stream_colors_and_sanitizes(colored):
    terminal = StringIO()

    monitor.TerminalStream(terminal).write("Username:\tJohn\x1b[2JDoe\n")

    assert colored["username"] in terminal.getvalue()
    assert "\x1b[2J" not in terminal.getvalue()


# Verifies the transient Doctor progress line stays uncoloured so its erase width remains correct
def test_doctor_progress_line_is_never_colored(colored, monkeypatch):
    written = []
    terminal = type("Stream", (), {"isatty": lambda self: True, "write": lambda self, text: written.append(text), "flush": lambda self: None})()
    monkeypatch.setattr(monitor, "_doctor_terminal_stream", lambda: terminal)
    monkeypatch.setattr(monitor._doctor_progress, "width", 0, raising=False)

    monitor._doctor_progress("Spotify authentication")
    progress_line = written[-1]
    monitor._doctor_progress_clear()

    assert "\x1b" not in "".join(written)
    assert written[-1] == "\r" + (" " * (len(progress_line) - 1)) + "\r"


# Verifies the doctor progress stream unwraps every output wrapper down to the real terminal
def test_doctor_terminal_stream_unwraps_output_wrappers(monkeypatch):
    real_terminal = StringIO()
    logger, _terminal, _logfile = make_logger()
    logger.__dict__["terminal"] = monitor.TerminalStream(real_terminal)
    monkeypatch.setattr(monitor.sys, "stdout", logger)

    assert monitor._doctor_terminal_stream() is real_terminal


# Verifies colour stays off unless the stream is an interactive terminal that allows it
def test_stream_support_detection_honours_environment(monkeypatch):
    monkeypatch.setattr(monitor.sys, "stdin", type("Stdin", (), {"isatty": lambda self: True})())
    interactive = type("Stream", (), {"isatty": lambda self: True})()
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)

    assert monitor._stream_supports_color(interactive) is True
    assert monitor._stream_supports_color(type("Stream", (), {"isatty": lambda self: False})()) is False

    monkeypatch.setenv("NO_COLOR", "1")
    assert monitor._stream_supports_color(interactive) is False
    monkeypatch.delenv("NO_COLOR")

    monkeypatch.setenv("TERM", "dumb")
    assert monitor._stream_supports_color(interactive) is False


# Verifies a piped stdin disables colour so redirected output never carries escape sequences
def test_piped_stdin_disables_color(monkeypatch):
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(monitor.sys, "stdin", type("Stdin", (), {"isatty": lambda self: False})())

    assert monitor._stream_supports_color(type("Stream", (), {"isatty": lambda self: True})()) is False


# Verifies a configured theme overrides only the parts it names and leaves the rest built in
def test_config_theme_overrides_only_named_parts(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"username": "red bold"})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    monitor.init_color_output(StringIO())

    assert monitor.COLOR_ENABLED is True
    assert monitor._COLOR_STYLES["username"] == "\033[31;1m"
    assert monitor._COLOR_STYLES["track"] == monitor._build_ansi_sequence(monitor.DEFAULT_COLOR_THEME["track"])


# Verifies a disabled setting clears the style map so colorize becomes a no-op
def test_disabled_color_output_clears_the_style_map(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    monitor.init_color_output(StringIO())

    assert monitor.COLOR_ENABLED is False
    assert monitor._COLOR_STYLES == {}
    assert monitor.colorize("username", "John") == "John"
    assert monitor.apply_color_to_text("Username:\tJohn\n") == "Username:\tJohn\n"


# Verifies the early config peek applies terminal appearance before arguments are parsed
def test_early_output_config_reads_terminal_appearance(monkeypatch, tmp_path):
    config_file = tmp_path / "spotify_monitor.conf"
    config_file.write_text("CLEAR_SCREEN = False\nCOLORED_OUTPUT = False\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--config-file", str(config_file)])
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)

    monitor.apply_early_output_config()

    assert monitor.CLEAR_SCREEN is False
    assert monitor.COLORED_OUTPUT is False


# Verifies a broken config leaves the early defaults alone so the later load reports the error
def test_early_output_config_ignores_a_broken_config(monkeypatch, tmp_path):
    config_file = tmp_path / "spotify_monitor.conf"
    config_file.write_text("import os\n", encoding="utf-8")
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--config-file", str(config_file)])
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)

    monitor.apply_early_output_config()

    assert monitor.COLORED_OUTPUT is True


# Verifies disabled config discovery skips the early peek entirely
def test_early_output_config_skips_disabled_discovery(monkeypatch):
    calls = []
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--config-file", "none"])
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: calls.append(path))

    monitor.apply_early_output_config()

    assert calls == []


# Verifies the raw argument scan finds the config path in both accepted spellings
@pytest.mark.parametrize("arguments,expected", [
    (["--config-file", "/tmp/one.conf"], "/tmp/one.conf"),
    (["--config-file=/tmp/two.conf"], "/tmp/two.conf"),
    (["--verbose"], None),
    (["--config-file"], None),
])
def test_early_config_file_argument_scan(arguments, expected):
    assert monitor.early_config_file_argument(arguments) == expected


# Verifies --no-color turns colour off even when the config file enables it
def test_no_color_flag_disables_colored_output(monkeypatch):
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--no-color"])
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)

    if "--no-color" in monitor.sys.argv:
        monitor.COLORED_OUTPUT = False
    monitor.init_color_output(StringIO())

    assert monitor.COLOR_ENABLED is False


# Verifies the logger writes past the early sanitizing stream so no line is colourised twice
def test_logger_unwraps_the_early_terminal_stream(colored, monkeypatch, tmp_path):
    raw_terminal = StringIO()
    monkeypatch.setattr(monitor.sys, "stdout", monitor.TerminalStream(raw_terminal))
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 0)
    logger = monitor.Logger(str(tmp_path / "monitor.log"))
    try:
        logger.write("Timestamp:\t\t\tWed 26 Aug 2026, 20:23:03\n")
    finally:
        logger.logfile.close()

    assert logger.terminal is raw_terminal
    # A second colour pass would no longer see the label and would recolour the value as a date
    assert raw_terminal.getvalue() == f"Timestamp:\t\t\t{colored['timestamp_value']}Wed 26 Aug 2026, 20:23:03{monitor.ANSI_RESET}\n"


# Verifies the unwrapper reaches the real terminal through any depth of sanitizing wrappers
def test_unwrap_terminal_stream_reaches_the_real_terminal():
    raw_terminal = StringIO()

    assert monitor.unwrap_terminal_stream(raw_terminal) is raw_terminal
    assert monitor.unwrap_terminal_stream(monitor.TerminalStream(monitor.TerminalStream(raw_terminal))) is raw_terminal


# Verifies a rule cannot reclaim text an earlier rule already coloured, so each value gets one clean span
def test_inline_rules_do_not_reclaim_already_colored_text(colored):
    result = monitor._colorize_line("[ date: Sun 16 Feb 2025, 14:34:06 - 1 year ago ]")

    assert result.count(colored["date"]) == 1
    assert result == f"[ date: {colored['date']}Sun 16 Feb 2025, 14:34:06{monitor.ANSI_RESET} - {colored['duration']}1 year{monitor.ANSI_RESET} ago ]"


# Verifies a name is coloured whatever punctuation it contains, so listings do not colour only some rows
@pytest.mark.parametrize("name", ["3 AM Sessions", "BDSM (dark techno/electronica)", "Hypnotic Trance / Techno / House", "Tomorrowland (TML) Festival Music", "Nocturne Rewired"])
def test_names_with_slashes_and_brackets_are_still_colored(colored, name):
    assert colored["playlist"] in monitor._colorize_line(f"- '{name}'")


# Verifies a name's own apostrophe does not end it early, which left most of the name uncoloured
@pytest.mark.parametrize("name", ["Don't Stop Me Now", "Ain't No Mountain High Enough"])
def test_a_name_containing_an_apostrophe_is_coloured_whole(colored, name):
    assert f"{colored['playlist']}{name}{monitor.ANSI_RESET}" in monitor._colorize_line(f"- '{name}'")


# Verifies two quoted names on one line stay two names, since the closing quote rule could have joined them
def test_two_quoted_names_on_one_line_stay_separate(colored):
    result = monitor._colorize_line("- 'Deep Focus' and 'Peaceful Piano'")

    assert f"{colored['playlist']}Deep Focus{monitor.ANSI_RESET}" in result
    assert f"{colored['playlist']}Peaceful Piano{monitor.ANSI_RESET}" in result


# Verifies a quoted placeholder inside a printed command stays plain, since it is text to replace rather than a name
@pytest.mark.parametrize("line", ["Run: spotify_monitor '<user_uri_id>'", "Replace '<topic>' with your own ntfy topic"])
def test_quoted_command_placeholders_stay_plain(colored, line):
    assert colored["playlist"] not in monitor._colorize_line(line)


# Verifies a quoted command-line option is left plain, since it is text to retype rather than a name
def test_quoted_command_options_stay_plain(colored):
    assert colored["playlist"] not in monitor._colorize_line("Replace '--env-file none' with a writable path")


# Verifies a quoted fragment of a URL stays plain, since it is a piece of an address rather than a name
@pytest.mark.parametrize("value", ["?code=", "&state="])
def test_quoted_url_fragments_stay_plain(colored, value):
    line = f"Copy everything after '{value}' from the address bar."

    assert monitor._colorize_line(line) == line


# Verifies quoted values shaped like a file name or a path stay plain
@pytest.mark.parametrize("value", ["monitor_state.json", "/data/spotify.log", "~/logs/output.txt", "C:\\Users\\me\\state.json"])
def test_quoted_file_and_path_values_stay_plain(colored, value):
    line = f"* State loaded from '{value}'"

    assert monitor._colorize_line(line) == line


# Verifies a standalone quoted description is left plain instead of being read as a name
def test_standalone_quoted_description_stays_plain(colored):
    line = "'Dark, dirty, underground, cyberpunk techno / electronica for consensual sessions.'"

    assert monitor._colorize_line(line) == line


# Verifies a change report is not painted end to end, so every value it names keeps its own colour
@pytest.mark.parametrize("line", CHANGE_REPORT_LINES)
def test_change_reports_are_not_painted_end_to_end(colored, line):
    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert not result.startswith("\x1b")


# Verifies a whole-line style is only ever applied to lines that report a problem, never to a change report
def test_only_problem_lines_are_painted_end_to_end(colored):
    for line, part in (("* Error: could not reach Spotify", "error"), ("* Warning: something odd", "warning")):
        assert monitor._colorize_line(line).startswith(colored[part])


# Verifies every part the shipped theme offers is actually looked up somewhere, so the theme documents only
# colours a user can really change
def test_every_theme_part_is_used():
    source = Path(monitor.__file__).read_text(encoding="utf-8")
    looked_up = set(re.findall(r"""colorize\(\s*["\']([a-z_]+)["\']""", source))
    looked_up |= set(re.findall(r"""_apply_style_nested\([^,]+,\s*["\']([a-z_]+)["\']""", source))
    looked_up |= set(re.findall(r"""_COLOR_STYLES\.get\(["\']([a-z_]+)["\']""", source))
    looked_up |= set(re.findall(r"""(?:style_name|quoted_style|key) = ["\']([a-z_]+)["\']""", source))
    looked_up |= set(re.findall(r""",\s*["\']([a-z_]+)["\']\),?\s*$""", source, re.M))
    doctor_marks = re.search(r"_DOCTOR_MARK_STYLES = \{(.*?)\}", source, re.S)
    assert doctor_marks is not None
    looked_up |= set(re.findall(r""":\s*["\']([a-z_]+)["\']""", doctor_marks.group(1)))

    assert not set(monitor.DEFAULT_COLOR_THEME) - looked_up


# Verifies the monitored target renders as an ID everywhere it is named, quoted or not, since this tool
# identifies a friend by URI ID rather than by display name
@pytest.mark.parametrize("line", [
    "Monitoring user 31nnv6eqt4qswvjhcnknimtxqife",
    "User '31nnv6eqt4qswvjhcnknimtxqife' not found - make sure your friend is followed",
    "Spotify user '31nnv6eqt4qswvjhcnknimtxqife' (John Doe) has disappeared",
    "User URI ID:\t\t\t31nnv6eqt4qswvjhcnknimtxqife",
    "* Target:                       31nnv6eqt4qswvjhcnknimtxqife",
])
def test_target_id_uses_the_id_colour_everywhere(colored, line):
    result = monitor._colorize_line(line)

    assert monitor.ANSI_ESCAPE_RE.sub("", result) == line
    assert f"{colored['id']}31nnv6eqt4qswvjhcnknimtxqife{monitor.ANSI_RESET}" in result
    assert colored["track"] not in result


# Verifies a display name still renders as a name, so the two identifiers stay distinguishable
def test_display_name_still_uses_the_name_colour(colored):
    assert colored["username"] in monitor._colorize_line("Username:\t\t\tJohn Doe")


# Verifies a config written against the pre-rename 'user_uri_id' key still colours identifiers
def test_legacy_theme_key_still_applies(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"user_uri_id": "red"})
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)
    monitor.init_color_output(StringIO())
    assert monitor._COLOR_STYLES["id"] == monitor._build_ansi_sequence("red")


# Verifies the current key name wins when a config sets both the old and the new name
def test_current_theme_key_wins_over_the_legacy_name(monkeypatch):
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", True)
    monkeypatch.setattr(monitor, "COLOR_THEME", {"user_uri_id": "red", "id": "green"})
    monkeypatch.setattr(monitor, "COLOR_ENABLED", False)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {})
    monkeypatch.setattr(monitor, "_stream_supports_color", lambda stream: True)
    monitor.init_color_output(StringIO())
    assert monitor._COLOR_STYLES["id"] == monitor._build_ansi_sequence("green")


# Verifies the guided setup surface is coloured, not only the monitoring output. The install method decides
# every command shown afterwards, and the commands themselves are what the user has to copy
def test_setup_surface_is_coloured(colored, capsys, monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_install_method", lambda: "pip")

    monitor._wizard_print_setup_destinations("pip", Path("monitor.conf"), Path(".env"))
    monitor._wizard_print_command("Check setup before monitoring:", "spotify_monitor --doctor <target>")
    output = capsys.readouterr().out

    assert f"Detected install method: {colored['username']}pip{monitor.ANSI_RESET}" in output
    assert f"{colored['section']}spotify_monitor --doctor <target>{monitor.ANSI_RESET}" in output


# Verifies a wizard prompt and its menu are coloured so the question and the number to type stand out
def test_wizard_prompt_and_menu_are_coloured(colored, capsys, monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_input", lambda prompt: "1")

    monitor._wizard_ask_choice("Pick one", [("First", ""), ("Second", "")], default_index=1)
    output = capsys.readouterr().out

    assert f"{colored['username']}1{monitor.ANSI_RESET}. First" in output
    assert f"{colored['info']} (default){monitor.ANSI_RESET}" in output


# Verifies the Doctor report headings and verdict are coloured, matching the sibling monitors
def test_doctor_report_headings_are_coloured(colored):
    built = monitor.build_doctor_report(None, None, "none")
    report = monitor.render_doctor_sections(built) + monitor.render_doctor_summary(built.checks)

    assert f"{colored['header']}Doctor{monitor.ANSI_RESET}" in report
    assert f"{colored['header']}Summary{monitor.ANSI_RESET}" in report
    assert f"{colored['section']}Environment{monitor.ANSI_RESET}" in report
    assert monitor.ANSI_ESCAPE_RE.sub("", report).splitlines()[0] == "Doctor"


# Verifies recovery guidance reads as advice rather than inheriting the colour of the failure it explains
def test_recovery_guidance_uses_the_info_colour(colored):
    line = "To fix: Verify the --config-file path then retry"

    assert monitor._colorize_line(line).startswith(colored["info"])


# Verifies truncation measures what is displayed, so colour codes do not eat into the visible width
def test_truncation_measures_display_width_not_escape_sequences():
    pytest.importorskip("wcwidth")

    truncated = monitor.truncate_string_per_line("\x1b[31m0123456789ABCDEF\x1b[0m", 10)

    assert re.sub(r"\x1b\[[0-9;]*m", "", truncated) == "0123456789"


# Verifies a double-width character costs two columns, so a CJK title does not wrap past the limit
def test_truncation_counts_double_width_characters():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("原神原神原神", 4) == "原神"


# Verifies each line is measured on its own rather than the whole message being cut at one offset
def test_truncation_applies_to_every_line():
    pytest.importorskip("wcwidth")

    assert monitor.truncate_string_per_line("abcdef\nabcdef", 3) == "abc\nabc"
