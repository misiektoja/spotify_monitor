"""Tests the --help screen: the shared argument group names, the task-grouped examples, the palette and the startup banner."""

import argparse
import re
import subprocess
import sys
from io import StringIO
from pathlib import Path

import pytest

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Returns the rendered help screen of the working-tree script
@pytest.fixture(scope="module")
def help_screen():
    result = subprocess.run([sys.executable, str(PROJECT_ROOT / "spotify_monitor.py"), "--help"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    return result.stdout


# Verifies the argument groups carry the names and the order shared with the sibling monitors
def test_the_argument_groups_use_the_shared_names_in_order(help_screen):
    titles = ['Configuration & dotenv files', 'Monitoring mode', "Auth details for 'cookie' token source", 'Browser sp_dc import', 'Email notifications', 'Webhook notifications', 'Intervals & timers', 'User information & listing', 'Features & output']

    positions = []
    for title in titles:
        marker = f"\n{title}:\n"
        assert marker in help_screen, f"the '{title}' group is missing"
        positions.append(help_screen.index(marker))

    assert positions == sorted(positions), "the argument groups are not in the shared order"


# Verifies email and webhook alerts are named apart rather than sharing one 'Notifications' group
def test_the_notification_groups_are_named_apart(help_screen):
    assert "\nEmail notifications:\n" in help_screen
    assert "\nWebhook notifications:\n" in help_screen
    assert "\nNotifications:\n" not in help_screen.split("Examples:")[0]


# Verifies the examples are grouped by what the reader is trying to do and end with the guide link
def test_the_examples_are_grouped_by_task(help_screen):
    examples = help_screen.split("Examples:", 1)[1]
    headings = ['Getting started', 'Notifications', 'Information and diagnostics', 'Scrobble health mode']

    positions = []
    for heading in headings:
        marker = f"\n{heading}:\n"
        assert marker in examples, f"the '{heading}' example group is missing"
        positions.append(examples.index(marker))

    assert positions == sorted(positions), "the example groups are not in the intended order"
    assert examples.rstrip().endswith(f"Guide: {monitor.QUICK_START_GUIDE_URL}")


# Verifies the one-line description carries the repository link in the form the sibling monitors print
def test_the_description_links_the_repository(help_screen):
    header = help_screen.split("positional arguments:", 1)[0]

    assert f"[ {monitor.PROJECT_URL}/ ]" in header


# Verifies every example command is introduced by a comment saying what it is for
def test_every_example_command_has_a_comment(help_screen):
    lines = [line for line in help_screen.split("Examples:", 1)[1].splitlines() if line.startswith("  ")]

    assert lines, "no example lines were rendered"
    for index, line in enumerate(lines):
        if not line.startswith("  #"):
            assert lines[index - 1].startswith("  #"), f"the example '{line.strip()}' has no comment above it"


# Verifies the help screen shows exactly one startup banner
def test_help_shows_one_startup_banner(help_screen):
    assert help_screen.count(" .---------------.") == 1


# Verifies the terminal truncation width is settable from the command line, as in the sibling monitors
def test_the_truncate_flag_is_offered(help_screen):
    assert "--truncate N" in help_screen
    assert "use 999 to auto-detect terminal width" in help_screen


# Verifies argparse never adds a palette of its own, which from Python 3.14 would survive --no-color
def test_argparse_adds_no_palette_of_its_own():
    expected = {"color": False} if sys.version_info >= (3, 14) else {}

    assert monitor.argparse_color_kwargs() == expected


# Verifies the switch is actually passed to the parser, since the helper alone colours nothing
def test_the_parser_is_built_with_the_argparse_colour_switch():
    source = Path(monitor.__file__).read_text(encoding="utf-8")
    construction = re.search(r"\n    parser = \w+\(\n(.*?)\n\n", source, re.S)

    assert construction is not None, "the parser construction could not be found"
    assert "**argparse_color_kwargs()" in construction.group(1)


# The one sentence each shared one-shot flag uses across the sibling monitors
SHARED_FLAG_HELP = {
    "--setup": "Run the guided setup and write a ready-to-run configuration",
    "--doctor": "Run read-only preflight checks and report what is ready and what is not",
    "--set-webhook-url": "Save a Discord or ntfy webhook URL through a hidden prompt",
    "--set-smtp-password": "Enter the SMTP password privately, check it against the mail server and save it to the dotenv file",
    "--send-test-email": "Send test email to verify SMTP settings",
    "--send-test-webhook": "Send one test webhook without starting monitoring",
}


# Verifies each shared one-shot flag describes itself with the sentence the sibling monitors use
def test_the_shared_flags_use_the_shared_help_sentences(help_screen):
    compact = " ".join(help_screen.split())

    for flag, sentence in SHARED_FLAG_HELP.items():
        assert f"{flag} {sentence}" in compact, f"the '{flag}' help sentence has drifted from the shared wording"


SAMPLE_HELP = """usage: spotify_monitor [-h] [--config-file PATH] [SPOTIFY_USER_URI_ID]

positional arguments:
  SPOTIFY_USER_URI_ID   Spotify user ID

Configuration & dotenv files:
  --config-file PATH    Path to a config file
  -m, --disappeared-timer SECONDS
                        Wait time between checks (default: 60)

Examples:

Getting started:
  # Guided setup, see https://example.invalid/guide/
  python3 spotify_monitor.py --setup <spotify_target>

Guide: https://example.invalid/guide/
"""

SAMPLE_EPILOG = SAMPLE_HELP[SAMPLE_HELP.index("Examples:"):]


# Enables colour with a known style map so assertions do not depend on the shipped theme
@pytest.fixture
def colored(monkeypatch):
    styles = {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)}
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", styles)
    return styles


# Returns the sample help screen with the help palette applied
@pytest.fixture
def colored_help(colored):
    return monitor.colorize_help_text(SAMPLE_HELP, SAMPLE_EPILOG)


# Verifies colouring changes no character of the screen, since argparse laid out its columns on the plain text
def test_the_coloured_help_keeps_the_plain_layout(colored_help):
    assert monitor.ANSI_ESCAPE_RE.sub("", colored_help) == SAMPLE_HELP


# Verifies the argument groups and the example tasks share one heading colour, the anchors the reader scans for
def test_the_headings_carry_the_heading_colour(colored, colored_help):
    for heading in ("positional arguments:", "Configuration & dotenv files:", "Examples:", "Getting started:"):
        assert f"{colored['help_heading']}{heading}{monitor.ANSI_RESET}" in colored_help


# Verifies an option name and the value it takes are coloured apart, in the usage block and in the option rows
def test_the_option_names_and_their_values_are_coloured_apart(colored, colored_help):
    option = f"{colored['help_option']}--config-file{monitor.ANSI_RESET}"
    metavar = f"{colored['help_metavar']}PATH{monitor.ANSI_RESET}"

    assert f"{option} {metavar}" in colored_help
    assert f"[{option} {metavar}]" in colored_help
    assert f"{colored['help_usage']}usage:{monitor.ANSI_RESET}" in colored_help
    assert f"{colored['help_metavar']}SPOTIFY_USER_URI_ID{monitor.ANSI_RESET}   Spotify user ID" in colored_help


# Verifies the examples separate the comment from the command and mark the value the reader has to replace
def test_the_examples_mark_comments_commands_and_placeholders(colored, colored_help):
    assert f"{colored['help_comment']}  # Guided setup" in colored_help
    assert f"{colored['help_command']}  python3 spotify_monitor.py --setup" in colored_help
    assert f"{colored['help_placeholder']}<spotify_target>{monitor.ANSI_RESET}" in colored_help


# Verifies a default note is dimmed and a documentation link keeps the shared link colour
def test_the_default_notes_and_links_stay_secondary(colored, colored_help):
    assert f"{colored['help_default']}(default: 60){monitor.ANSI_RESET}" in colored_help
    assert f"{colored['link']}https://example.invalid/guide/{monitor.ANSI_RESET}" in colored_help


# Verifies the help screen stays plain while colour is switched off, so --no-color and NO_COLOR clear all of it
def test_the_help_palette_switches_off_with_colour():
    assert monitor.colorize_help_text(SAMPLE_HELP, SAMPLE_EPILOG) == SAMPLE_HELP


# Verifies the help screen is written past the output colouriser, which paints a row naming a problem word red
def test_the_help_screen_is_not_repainted_by_the_monitoring_rules(colored):
    buffer = StringIO()
    parser = monitor.ColoredHelpParser(prog="spotify_monitor", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-m", "--disappeared-timer", metavar="SECONDS", help="Wait time between checks once the user disappears")
    parser.print_help(monitor.TerminalStream(buffer))

    written = buffer.getvalue()
    assert written == parser.format_help()
    assert colored["error"] not in written
