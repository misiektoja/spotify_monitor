import io
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Runs the command-line entry point without allowing a nonzero status to raise
def run_cli(*arguments):
    return subprocess.run([sys.executable, str(PROJECT_ROOT / "spotify_monitor.py"), *arguments], cwd=PROJECT_ROOT, input="", text=True, capture_output=True, check=False)


# Sets deterministic non-secret startup settings plus known secret sentinels
def configure_summary(monkeypatch):
    values = {
        "TOKEN_SOURCE": "cookie",
        "SPOTIFY_CHECK_INTERVAL": 30,
        "SPOTIFY_INACTIVITY_CHECK": 660,
        "SPOTIFY_DISAPPEARED_CHECK_INTERVAL": 180,
        "SPOTIFY_ERROR_INTERVAL": 180,
        "ACTIVE_NOTIFICATION": False,
        "INACTIVE_NOTIFICATION": False,
        "TRACK_NOTIFICATION": False,
        "SONG_NOTIFICATION": False,
        "SONG_ON_LOOP_NOTIFICATION": False,
        "ERROR_NOTIFICATION": False,
        "WEBHOOK_ENABLED": False,
        "WEBHOOK_URL": "known-webhook-secret",
        "WEBHOOK_ACTIVE_NOTIFICATION": False,
        "WEBHOOK_INACTIVE_NOTIFICATION": False,
        "WEBHOOK_TRACK_NOTIFICATION": False,
        "WEBHOOK_SONG_NOTIFICATION": False,
        "WEBHOOK_SONG_ON_LOOP_NOTIFICATION": False,
        "WEBHOOK_ERROR_NOTIFICATION": False,
        "TRACK_SONGS": False,
        "LIVENESS_CHECK_INTERVAL": 0,
        "CSV_FILE": "",
        "MONITOR_LIST_FILE": "",
        "FLAG_FILE": "",
        "TRUNCATE_CHARS": 0,
        "VERBOSE_MODE": False,
        "DEBUG_MODE": False,
        "SP_APP_CLIENT_ID": "your_spotify_app_client_id",
        "SP_APP_CLIENT_SECRET": "your_spotify_app_client_secret",
        "SP_APP_TOKENS_FILE": ".spotify-monitor-oauth-app.json",
        "SP_DC_COOKIE": "known-cookie-secret",
        "REFRESH_TOKEN": "known-refresh-secret",
        "SMTP_PASSWORD": "known-smtp-secret",
        "SP_CACHED_ACCESS_TOKEN": "known-access-secret",
        "SP_CACHED_CLIENT_TOKEN": "known-client-secret",
    }
    for name, value in values.items():
        monkeypatch.setattr(monitor, name, value)


# Returns deterministic startup rows for the standard target and paths
def summary_rows():
    return monitor.build_startup_summary("target.user", "/data/spotify_monitor.conf", "/data/.env", "/data/spotify_monitor_target.user.log")


# Emits rows to a plain in-memory terminal for concise or full assertions
def emit_to_string(rows, show_full=False):
    stream = io.StringIO()
    monitor.emit_startup_summary(rows, show_full=show_full, stream=stream)
    return stream.getvalue()


# Verifies the selected Variant A art remains exact and version independent
def test_selected_banner_exact_content():
    assert monitor.STARTUP_BANNER == r"""
 .---------------.    ____              _   _  __
|  |||  |  ||||  |   / ___| _ __   ___ | |_(_)/ _|_   _
|  ||| ||| ||||| |   \___ \| '_ \ / _ \| __| | |_| | | |
|  || |||||| ||| |    ___) | |_) | (_) | |_| |  _| |_| |
|   |  ||||   |  |   |____/| .__/ \___/ \__|_|_|  \__, |
 '---------------'         |_|                    |___/
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""


# Ensures the lower stroke of the Spotify y stays aligned with its upper stroke
def test_banner_spotify_y_descender_alignment():
    spotify_lines = [line[21:] for line in monitor.STARTUP_BANNER.splitlines()[1:7]]
    assert spotify_lines[4].index(r"\__,") == spotify_lines[5].index("|___/")


# Ensures the visible Spotify top strokes retain the intended one-column curve offset
def test_banner_spotify_top_stroke_alignment():
    spotify_lines = [line[21:] for line in monitor.STARTUP_BANNER.splitlines()[1:7]]
    assert spotify_lines[0] == r" ____              _   _  __"
    assert spotify_lines[0].index("____") == spotify_lines[1].index("/ ___|") + 1


# Verifies the art is ASCII-only, narrow enough and free of trailing whitespace
def test_banner_ascii_width_and_whitespace():
    monitor.STARTUP_BANNER.encode("ascii")
    lines = monitor.STARTUP_BANNER.splitlines()
    assert max(map(len, lines)) <= 90
    assert all(line == line.rstrip() for line in lines)


# Verifies the printed version is dynamic and followed by one blank line
def test_banner_dynamic_version_line(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "VERSION", "9.9-test")
    monitor.print_startup_banner()
    assert capsys.readouterr().out == monitor.STARTUP_BANNER + "\n" + (" " * 21) + "v9.9-test\n\n"


# Verifies Spotify plus Monitor and the version share the same body column
def test_banner_version_alignment():
    banner_lines = monitor.STARTUP_BANNER.splitlines()[1:]
    spotify_body_column = banner_lines[1].index("/ ___|")
    monitor_body_line = banner_lines[7]
    monitor_body_indent = len(monitor_body_line) - len(monitor_body_line.lstrip())
    version_line = (" " * 21) + f"v{monitor.VERSION}"
    version_indent = len(version_line) - len(version_line.lstrip())
    assert spotify_body_column == monitor_body_indent == version_indent


# Verifies help exits cleanly with one banner and exact raw example layout
def test_help_banner_once_and_raw_epilog():
    result = run_cli("--help")
    prefix = monitor._wizard_cmd_prefix("manual")
    assert result.returncode == 0
    assert result.stdout.count(" .---------------.") == 1
    assert "Show rare operational events plus the complete startup summary" in result.stdout
    assert f"Examples:\n  # Guided setup, recommended for the first run\n  {prefix} --setup" in result.stdout
    assert "# Then import Spotify login from Firefox (recommended for local installs)" in result.stdout
    assert f"{prefix} --set-sp-dc" in result.stdout
    assert f"{prefix} --set-webhook-url" in result.stdout
    assert f"{prefix} --send-test-webhook" in result.stdout
    assert "Select the monitoring mode for this run (default: saved mode or friend_activity)" in result.stdout
    assert "Path to a config file (mode-specific auto-search if omitted, disable with 'none')" in result.stdout
    assert "--scrobble-health" not in result.stdout
    assert f"{prefix} --authorize-scrobble-health" in result.stdout
    assert f"{prefix} --monitor-mode scrobble_health" in result.stdout
    assert f"{prefix} --monitor-mode scrobble_health --lastfm-username <lastfm_username>" in result.stdout
    assert "Last.fm API key for this run (may remain in shell history)" in result.stdout
    assert "Spotify Developer app Client ID for scrobble health mode" in result.stdout
    assert "Spotify recent-play refresh token for this run (may remain in shell history)" in result.stdout
    assert "--scrobble-match-window" in result.stdout
    assert "--scrobble-lookback" in result.stdout
    assert "--scrobble-repeat-interval" in result.stdout
    assert "--scrobble-state-file" in result.stdout
    assert f"{prefix} --monitor-mode scrobble_health --doctor --verbose" in result.stdout
    assert f"{prefix} --monitor-mode friend_activity <spotify_user_id>" in result.stdout
    assert f"\n  # Monitor one Spotify user\n  # A spotify:user URI or profile URL is also accepted\n  {prefix} <spotify_user_id>" in result.stdout
    assert f"Guide: {monitor.QUICK_START_GUIDE_URL}" in result.stdout


# Verifies no-argument output matches the sibling-style quick-start hierarchy
def test_no_argument_welcome_uses_spaced_quick_start_blocks():
    result = run_cli()
    prefix = monitor._wizard_cmd_prefix("manual")
    assert result.returncode == 1
    assert "Welcome to Spotify Monitor" not in result.stdout
    assert "For <spotify_target>, use a Spotify user ID or complete profile URL.\n" in result.stdout
    assert f"Quickest start (already configured):\n    {prefix} <spotify_target>\n" in result.stdout
    assert f"Easiest start (guided setup wizard):\n    {prefix} --setup\n" in result.stdout
    assert f"Check setup before monitoring:\n    {prefix} --doctor <spotify_target>\n" in result.stdout
    assert f"Full options: {prefix} --help" in result.stdout
    assert f"Guide:        {monitor.QUICK_START_GUIDE_URL}" in result.stdout


# Verifies version output stays one line and excludes the startup art
def test_version_output_is_machine_friendly():
    result = run_cli("--version")
    assert result.returncode == 0
    assert result.stdout.splitlines() == ["spotify_monitor.py v3.2"]
    assert monitor.STARTUP_BANNER.splitlines()[1] not in result.stdout


# Verifies generated config begins with content and excludes the startup art
def test_generate_config_output_is_machine_friendly():
    result = run_cli("--generate-config")
    assert result.returncode == 0
    assert result.stdout.startswith("# Select one of two independent monitoring modes:")
    assert "#   friend_activity - monitors a followed Spotify user's completed tracks, presence and sessions" in result.stdout
    assert "#                     Run --setup to configure the target, Spotify authentication and notifications" in result.stdout
    assert "#                     Run --setup-scrobble-health to configure Spotify, Last.fm and alerts" in result.stdout
    assert "# Use --monitor-mode to override this value for one run" in result.stdout
    assert "--scrobble-health" not in result.stdout
    assert "# Easiest setup: run --setup-scrobble-health" in result.stdout
    assert "# For Friend Activity monitoring use the regular --setup wizard" in result.stdout
    assert monitor.STARTUP_BANNER.splitlines()[1] not in result.stdout
    assert "VERBOSE_MODE = False" in result.stdout


# Verifies a config file can enable verbose startup detail independently of debug mode
def test_verbose_mode_loads_from_config(tmp_path):
    config_path = tmp_path / "verbose.conf"
    config_path.write_text("VERBOSE_MODE = True\nDEBUG_MODE = False\n", encoding="utf-8")
    namespace = {"VERBOSE_MODE": False, "DEBUG_MODE": False}
    assert monitor.load_config_file(config_path, namespace=namespace)
    assert namespace == {"VERBOSE_MODE": True, "DEBUG_MODE": False}


# Verifies concise startup output leads with target and the required core fields
def test_concise_summary_core_rows(monkeypatch):
    configure_summary(monkeypatch)
    output = emit_to_string(summary_rows())
    lines = output.splitlines()
    assert lines[0].startswith("* Target:")
    assert lines[0].index("target.user") == 32
    assert "target.user" in lines[0]
    assert "* Authentication:" in output and "Cookie mode" in output
    assert "* Polling interval:" in output and "30 seconds" in output
    assert "* Output:" in output and "spotify_monitor_target.user.log" in output
    assert "* Config:" in output and "/data/spotify_monitor.conf" in output
    assert "* Dotenv:" in output and "/data/.env" in output
    assert "* Metadata backend:" in output and "web player" in output


# Verifies concise and complete notification rows keep email and webhook states independent
@pytest.mark.parametrize("email_enabled,webhook_category_enabled,webhook_master_enabled,expected_email,expected_webhook", [(False, False, False, "Off", "Off"), (True, False, False, "On (active, tracked)", "Off"), (False, True, True, "Off", "On (active, errors)"), (True, True, True, "On (active, tracked)", "On (active, errors)"), (False, True, False, "Off", "Off")])
def test_startup_summary_notification_channels(monkeypatch, email_enabled, webhook_category_enabled, webhook_master_enabled, expected_email, expected_webhook):
    configure_summary(monkeypatch)
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", email_enabled)
    monkeypatch.setattr(monitor, "TRACK_NOTIFICATION", email_enabled)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_NOTIFICATION", webhook_category_enabled)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", webhook_category_enabled)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", webhook_master_enabled)
    expected_lines = [f"* Notifications (email):        {expected_email}", f"* Notifications (webhook):      {expected_webhook}"]
    for show_full in (False, True):
        notification_lines = [line for line in emit_to_string(summary_rows(), show_full=show_full).splitlines() if line.startswith("* Notifications (")]
        assert notification_lines == expected_lines


# Verifies long notification rows wrap within 100 columns without starred continuation lines
def test_long_notification_summary_rows_wrap_without_starred_continuations():
    categories = "On (" + ", ".join(f"category-{index}" for index in range(12)) + ")"
    formatted = monitor._format_startup_summary_row(monitor.StartupSummaryRow("Notifications (email)", categories))
    lines = formatted.rstrip("\n").splitlines()
    assert len(lines) > 1
    assert all(len(line) <= 100 for line in lines)
    assert not any(line.startswith("*") for line in lines[1:])


# Verifies disabled advanced defaults stay out of the concise view
def test_concise_summary_hides_disabled_advanced_defaults(monkeypatch):
    configure_summary(monkeypatch)
    output = emit_to_string(summary_rows())
    for hidden in ("Token source", "Inactivity timer", "CSV output", "Monitored-track alerts", "Spotify playback control", "Flag file", "Terminal truncation", "Verbose mode", "Debug mode", "Legacy OAuth cache"):
        assert hidden not in output


# Verifies enabled optional settings appear in the concise view
def test_concise_summary_shows_enabled_optional_settings(monkeypatch):
    configure_summary(monkeypatch)
    monkeypatch.setattr(monitor, "ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "TRACK_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "TRACK_SONGS", True)
    monkeypatch.setattr(monitor, "LIVENESS_CHECK_INTERVAL", 3600)
    monkeypatch.setattr(monitor, "CSV_FILE", "/data/tracks.csv")
    monkeypatch.setattr(monitor, "MONITOR_LIST_FILE", "/data/alerts.txt")
    monkeypatch.setattr(monitor, "FLAG_FILE", "/data/active.flag")
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 80)
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "known-oauth-client-secret")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "known-oauth-secret")
    output = emit_to_string(summary_rows())
    for visible in ("On (active, tracked)", "Spotify playback control", "Liveness output", "/data/tracks.csv", "/data/alerts.txt", "/data/active.flag", "80 chars", "Legacy OAuth cache"):
        assert visible in output


# Verifies webhook alerts appear without exposing the private URL
def test_webhook_summary_is_secret_safe(monkeypatch):
    configure_summary(monkeypatch)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ACTIVE_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", True)
    output = emit_to_string(summary_rows(), show_full=True)
    assert "* Notifications (webhook):      On (active, errors)" in output
    assert "Webhook enabled" not in output
    assert "Webhook provider" not in output
    assert "known-webhook-secret" not in output


# Verifies client authentication uses the advanced intent label
def test_client_mode_is_labelled_advanced(monkeypatch):
    configure_summary(monkeypatch)
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "client")
    assert "Client mode, advanced" in emit_to_string(summary_rows())


# Verifies default routing keeps full-only rows in one log copy
def test_default_terminal_is_concise_and_full_summary_reaches_log(monkeypatch, tmp_path):
    configure_summary(monkeypatch)
    terminal = io.StringIO()
    monkeypatch.setattr(monitor.sys, "stdout", terminal)
    logger = monitor.Logger(tmp_path / "startup.log")
    monitor.emit_startup_summary(summary_rows(), show_full=False, stream=logger)
    logger.flush()
    log_output = (tmp_path / "startup.log").read_text(encoding="utf-8")
    logger.logfile.close()
    terminal_output = terminal.getvalue()
    assert "Error retry timer" not in terminal_output
    assert "Error retry timer" in log_output
    assert "* Notifications (email):" in log_output
    assert "* Notifications (webhook):" in log_output
    assert "Notify active" not in log_output
    assert "Webhook enabled" not in log_output
    assert log_output.count("* Target:") == 1


# Verifies verbose and debug selection display the complete terminal summary
@pytest.mark.parametrize("mode_name", ["VERBOSE_MODE", "DEBUG_MODE"])
def test_verbose_and_debug_terminal_receive_full_summary(monkeypatch, mode_name):
    configure_summary(monkeypatch)
    monkeypatch.setattr(monitor, mode_name, True)
    output = emit_to_string(summary_rows(), show_full=bool(monitor.VERBOSE_MODE or monitor.DEBUG_MODE))
    assert all(line.startswith("* ") for line in output.splitlines() if line)
    error_retry_line = next(line for line in output.splitlines() if "Error retry timer:" in line)
    assert error_retry_line.index("3 minutes") == 32
    assert "Error retry timer" in output
    assert "* Notifications (email):" in output
    assert "* Notifications (webhook):" in output
    assert "Notify active" not in output
    assert "Webhook enabled" not in output
    assert "More details" not in output


# Verifies the verbose flag changes startup detail without enabling debug mode
def test_verbose_flag_does_not_enable_debug(monkeypatch):
    configure_summary(monkeypatch)
    observed = {}
    monkeypatch.setattr(monitor.sys, "argv", ["spotify_monitor.py", "--doctor", "--verbose", "--env-file", "none"])
    clear_mock = Mock()
    monkeypatch.setattr(monitor, "clear_screen", clear_mock)
    monkeypatch.setattr(monitor, "find_config_file", lambda path=None: None)
    monkeypatch.setattr(monitor, "run_doctor", lambda *args, **kwargs: observed.update(verbose=monitor.VERBOSE_MODE, debug=monitor.DEBUG_MODE) or 0)
    with pytest.raises(SystemExit) as error:
        monitor.main()
    assert error.value.code == 0
    assert observed == {"verbose": True, "debug": False}
    clear_mock.assert_called_once_with(False)


# Verifies verbose mode emits rare operational events without per-poll timing noise
def test_verbose_runtime_is_event_driven(monkeypatch, capsys):
    started_at = datetime(2026, 7, 14, 17, 0, 0)
    completed_at = datetime(2026, 7, 14, 17, 0, 5)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    actual_started_at = monitor.debug_monitor_check_start(3, "target.user", started_at)
    monitor.debug_monitor_check_timing(3, "target.user", actual_started_at, 30, completed_at)
    monitor.debug_monitor_wait_timing("target.user", 180, completed_at)
    monitor.verbose_print("Authentication token refreshed (cookie mode)")
    output = capsys.readouterr().out
    assert actual_started_at == started_at
    assert output == "* Authentication token refreshed (cookie mode)\n"
    assert "Starting check" not in output
    assert "Next check" not in output
    assert "[DEBUG" not in output


# Verifies debug mode retains detailed per-poll lifecycle and scheduling output
def test_debug_runtime_check_timing(monkeypatch, capsys):
    started_at = datetime(2026, 7, 14, 17, 0, 0)
    completed_at = datetime(2026, 7, 14, 17, 0, 5)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    actual_started_at = monitor.debug_monitor_check_start(3, "target.user", started_at)
    monitor.debug_monitor_check_timing(3, "target.user", actual_started_at, 30, completed_at)
    monitor.debug_monitor_wait_timing("target.user", 180, completed_at)
    output = capsys.readouterr().out
    assert "Starting check #3 for target.user" in output
    assert f"last={monitor.get_date_from_ts(started_at)}" in output
    assert f"next={monitor.get_date_from_ts(completed_at + monitor.timedelta(seconds=30))}" in output
    assert "interval=30 seconds" in output
    assert f"Next visibility check for target.user: {monitor.get_date_from_ts(completed_at + monitor.timedelta(seconds=180))}" in output


# Verifies normal mode suppresses verbose events and per-poll debug timing
def test_normal_mode_suppresses_runtime_check_status(monkeypatch, capsys):
    started_at = datetime(2026, 7, 14, 17, 0, 0)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    actual_started_at = monitor.debug_monitor_check_start(1, "target.user", started_at)
    monitor.debug_monitor_check_timing(1, "target.user", actual_started_at, 30, started_at)
    monitor.debug_monitor_wait_timing("target.user", 180, started_at)
    monitor.verbose_print("Authentication token refreshed (cookie mode)")
    assert actual_started_at == started_at
    assert capsys.readouterr().out == ""


# Verifies verbose operational events redact configured secrets
def test_verbose_runtime_event_sanitizes_secrets(monkeypatch, capsys):
    secret = "verbose-secret-value"
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "SP_DC_COOKIE", secret)
    monitor.verbose_print(f"Authentication event contained {secret}")
    output = capsys.readouterr().out
    assert secret not in output
    assert output == "* Authentication event contained <redacted>\n"


# Verifies setup rejects verbose as an unrelated runtime flag
def test_setup_rejects_verbose_flag():
    result = run_cli("--setup", "--verbose")
    assert result.returncode == 2
    assert "--setup cannot be combined with --verbose" in result.stderr


# Verifies logging-disabled output never implies that a full summary was logged
def test_logging_disabled_summary_behavior(monkeypatch):
    configure_summary(monkeypatch)
    rows = monitor.build_startup_summary("target.user", None, None, None)
    concise = emit_to_string(rows)
    full = emit_to_string(rows, show_full=True)
    assert "Terminal only (logging disabled)" in concise
    assert "full summary written" not in concise.casefold()
    assert "Output logging:" in full and "Disabled" in full
    assert "Dotenv:" in concise and "None" in concise


# Verifies known secrets never enter concise, full or log-only summary output
def test_startup_summaries_never_include_secrets(monkeypatch, tmp_path):
    configure_summary(monkeypatch)
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_ID", "known-oauth-client-secret")
    monkeypatch.setattr(monitor, "SP_APP_CLIENT_SECRET", "known-oauth-secret")
    rows = summary_rows()
    terminal = io.StringIO()
    monkeypatch.setattr(monitor.sys, "stdout", terminal)
    logger = monitor.Logger(tmp_path / "secret-check.log")
    monitor.emit_startup_summary(rows, show_full=True, stream=logger)
    logger.flush()
    log_output = (tmp_path / "secret-check.log").read_text(encoding="utf-8")
    logger.logfile.close()
    combined = emit_to_string(rows) + emit_to_string(rows, show_full=True) + terminal.getvalue() + log_output
    for secret in monitor.known_secret_values():
        assert secret not in combined


# Verifies configured terminal-width autodetection resolves the sentinel before logging starts
def test_configured_truncation_autodetects_terminal_width(monkeypatch, capsys):
    monkeypatch.setattr(monitor.shutil, "get_terminal_size", lambda: Mock(columns=120))
    assert monitor.resolve_truncate_chars(None, 999, False) == 120
    assert capsys.readouterr().out == "The detected terminal screen width is: 120 characters\n\n"


# Verifies CLI truncation values take precedence including an explicit zero
@pytest.mark.parametrize(("cli_value", "configured_value", "expected"), ((0, 80, 0), (72, 999, 72), (None, 80, 80)))
def test_cli_truncation_overrides_configured_value(cli_value, configured_value, expected):
    assert monitor.resolve_truncate_chars(cli_value, configured_value, False) == expected


# Verifies disabled logging suppresses truncation and terminal-width detection
def test_disabled_logging_skips_truncation_autodetection(monkeypatch, capsys):
    terminal_size = Mock(side_effect=AssertionError("terminal width should not be detected"))
    monkeypatch.setattr(monitor.shutil, "get_terminal_size", terminal_size)
    assert monitor.resolve_truncate_chars(None, 999, True) == 0
    terminal_size.assert_not_called()
    assert capsys.readouterr().out == ""


# Verifies terminal-only and log-only routing retain truncation and tab semantics
def test_logger_terminal_only_and_log_only(monkeypatch, tmp_path):
    terminal = io.StringIO()
    monkeypatch.setattr(monitor.sys, "stdout", terminal)
    monkeypatch.setattr(monitor, "TRUNCATE_CHARS", 5)
    logger = monitor.Logger(tmp_path / "routing.log")
    logger.terminal_only("abcdefgh\n")
    logger.log_only("\tlog-only-value\n")
    logger.write("terminal-and-log\n")
    logger.flush()
    log_output = (tmp_path / "routing.log").read_text(encoding="utf-8")
    logger.logfile.close()
    assert terminal.getvalue() == "abcde\ntermi\n"
    assert "abcdefgh" not in log_output
    assert "        log-only-value\n" in log_output
    assert "terminal-and-log\n" in log_output
