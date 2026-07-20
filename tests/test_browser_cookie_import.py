import json
import os
import sqlite3
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from dotenv import dotenv_values

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "spotify_monitor.py"
ISOLATED_PRELUDE = "import requests, runpy, socket, sys; requests.sessions.Session.request = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network request attempted')); socket.create_connection = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('network connection attempted')); "


# Creates a synthetic Firefox cookie database with a selected schema and rows
def create_firefox_database(path, rows, reduced=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        if reduced:
            connection.execute("CREATE TABLE moz_cookies (baseDomain TEXT, name TEXT, value TEXT)")
            connection.executemany("INSERT INTO moz_cookies VALUES (?, ?, ?)", rows)
        else:
            connection.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT, expiry INTEGER, lastAccessed INTEGER)")
            connection.executemany("INSERT INTO moz_cookies VALUES (?, ?, ?, ?, ?)", rows)


# Runs one isolated CLI scenario with browser and network access mocked by setup source
def run_cli(arguments, runtime_setup=""):
    source = f"module = runpy.run_path({str(CLI_PATH)!r}, run_name='spotify_monitor_phase2_test'); runtime = module['main'].__globals__; runtime['sys'].argv = {[str(CLI_PATH), *arguments]!r}; runtime['CLEAR_SCREEN'] = False; runtime['signal'].signal = lambda *args, **kwargs: None; runtime['find_config_file'] = lambda path=None: None; {runtime_setup} module['main']()"
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-c", ISOLATED_PRELUDE + source], cwd=PROJECT_ROOT, capture_output=True, text=True, env=environment, timeout=30, check=False)


# Returns two synthetic profile records for selection tests
def sample_profiles(tmp_path):
    return [
        {"dir": "abc.default-release", "name": "Personal", "path": str(tmp_path / "abc.default-release"), "cookie_file": str(tmp_path / "abc.default-release/cookies.sqlite")},
        {"dir": "xyz.work", "name": "Work", "path": str(tmp_path / "xyz.work"), "cookie_file": str(tmp_path / "xyz.work/cookies.sqlite")},
    ]


# Verifies profiles.ini metadata supplies the friendly Firefox profile name
def test_firefox_profiles_ini_discovery(tmp_path):
    root = tmp_path / ".mozilla/firefox"
    profile_dir = root / "Profiles/abc.default-release"
    create_firefox_database(profile_dir / "cookies.sqlite", [(".spotify.com", "sp_dc", "cookie", 4102444800, 10)])
    root.mkdir(parents=True, exist_ok=True)
    (root / "profiles.ini").write_text("[Profile0]\nName=Personal Spotify\nIsRelative=1\nPath=Profiles/abc.default-release\n", encoding="utf-8")

    profiles = monitor.discover_firefox_profiles(system_name="Linux", home=tmp_path)

    assert len(profiles) == 1
    assert profiles[0]["name"] == "Personal Spotify"
    assert profiles[0]["dir"] == "abc.default-release"


# Verifies Firefox scanning finds a profile when profiles.ini is absent
def test_firefox_fallback_directory_discovery(tmp_path):
    cookie_file = tmp_path / ".mozilla/firefox/scan.default-release/cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "cookie", 4102444800, 10)])

    profiles = monitor.discover_firefox_profiles(system_name="Linux", home=tmp_path)

    assert [(profile["dir"], profile["name"]) for profile in profiles] == [("scan.default-release", "default-release")]


# Verifies Linux standard, Snap and Flatpak Firefox locations are scanned
def test_firefox_linux_location_discovery(tmp_path):
    relative_roots = [".mozilla/firefox", "snap/firefox/common/.mozilla/firefox", ".var/app/org.mozilla.firefox/.mozilla/firefox"]
    for index, relative_root in enumerate(relative_roots):
        create_firefox_database(tmp_path / relative_root / f"p{index}.default/cookies.sqlite", [("spotify.com", "sp_dc", f"cookie-{index}", 4102444800, index)])

    profiles = monitor.discover_firefox_profiles(system_name="Linux", home=tmp_path)

    assert {profile["dir"] for profile in profiles} == {"p0.default", "p1.default", "p2.default"}


# Verifies macOS and Windows Firefox roots match their normal platform locations
def test_firefox_macos_and_windows_roots(tmp_path):
    mac_roots = monitor._firefox_profile_roots(system_name="Darwin", home=tmp_path)
    windows_roots = monitor._firefox_profile_roots(system_name="Windows", home=tmp_path, environ={"APPDATA": str(tmp_path / "Roaming")})

    assert mac_roots == [tmp_path / "Library/Application Support/Firefox"]
    assert windows_roots == [tmp_path / "Roaming/Mozilla/Firefox"]


# Verifies a Firefox friendly name selects the intended profile
def test_profile_selection_by_friendly_name(tmp_path):
    selected = monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", requested_profile="work", interactive=False)
    assert selected["dir"] == "xyz.work"


# Verifies a Firefox directory basename selects the intended profile
def test_profile_selection_by_directory_basename(tmp_path):
    selected = monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", requested_profile="ABC.DEFAULT-RELEASE", interactive=False)
    assert selected["name"] == "Personal"


# Verifies an explicit cookie database bypasses Firefox profile discovery
def test_explicit_firefox_cookie_file_takes_precedence(tmp_path, monkeypatch, capsys):
    cookie_file = tmp_path / "explicit.sqlite"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    monkeypatch.setattr(monitor, "discover_firefox_profiles", Mock(side_effect=AssertionError("profile discovery called")))
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))

    monitor.run_browser_cookie_import(browser="firefox", browser_profile="ignored", cookie_file=str(cookie_file), env_file=str(destination), interactive=False)

    assert dotenv_values(destination, interpolate=False)["SP_DC_COOKIE"] == "secret-cookie"
    assert monitor.SPOTIFY_WEB_LOGIN_URL in capsys.readouterr().out


# Verifies modern Firefox schemas prefer the newest nonexpired Spotify cookie
def test_firefox_modern_schema_selects_newest_nonexpired_cookie(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    rows = [
        (".spotify.com", "sp_dc", "expired-newer-access", 50, 500),
        ("open.spotify.com", "sp_dc", "current-old", 5000, 100),
        ("accounts.spotify.com", "sp_dc", "current-new", 5000, 200),
    ]
    create_firefox_database(cookie_file, rows)

    assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "current-new"


# Verifies immutable SQLite access reads a Firefox database held under an exclusive browser-style lock
def test_firefox_immutable_access_bypasses_exclusive_lock(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "locked-cookie", 5000, 10)])

    with sqlite3.connect(cookie_file) as locking_connection:
        locking_connection.execute("PRAGMA locking_mode=EXCLUSIVE")
        locking_connection.execute("BEGIN EXCLUSIVE")

        assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "locked-cookie"


# Verifies reduced Firefox schemas using baseDomain remain supported
def test_firefox_reduced_schema_is_supported(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "reduced-cookie")], reduced=True)

    assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "reduced-cookie"


# Verifies exact Spotify domains and true subdomains are accepted
def test_firefox_spotify_domain_filter_accepts_true_domains(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "root", 5000, 10), ("open.spotify.com", "sp_dc", "subdomain", 5000, 20)])

    assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "subdomain"


# Verifies deceptive notspotify.com cookies are rejected
def test_firefox_spotify_domain_filter_rejects_deceptive_hosts(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("notspotify.com", "sp_dc", "deceptive-secret", 5000, 20), ("spotify.com.example.org", "sp_dc", "also-deceptive", 5000, 30)])

    with pytest.raises(monitor.BrowserCookieImportError, match="No sp_dc cookie") as error:
        monitor.read_firefox_sp_dc(cookie_file, now=1000)
    assert "deceptive-secret" not in str(error.value)


# Verifies a Firefox profile without sp_dc gets a clear error
def test_firefox_missing_sp_dc(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "other", "not-secret", 5000, 20)])

    with pytest.raises(monitor.BrowserCookieImportError, match="No sp_dc cookie"):
        monitor.read_firefox_sp_dc(cookie_file)


# Verifies invalid Firefox SQLite data gets a secret-safe recovery hint
def test_firefox_invalid_sqlite_database(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.write_text("not a SQLite database", encoding="utf-8")

    with pytest.raises(monitor.BrowserCookieImportError, match="Close Firefox") as error:
        monitor.read_firefox_sp_dc(cookie_file)
    assert "--cookie-file" in str(error.value)


# Verifies locked or unreadable Firefox databases get the same recovery guidance
def test_firefox_unreadable_sqlite_database(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    monkeypatch.setattr(monitor.sqlite3, "connect", Mock(side_effect=sqlite3.OperationalError("database is locked")))

    with pytest.raises(monitor.BrowserCookieImportError, match="Close Firefox") as error:
        monitor.read_firefox_sp_dc(cookie_file)
    assert "database is locked" not in str(error.value)


# Verifies Chrome, Brave and Chromium paths on macOS and Linux
def test_chromium_user_data_path_resolution(tmp_path):
    expected = {
        ("Darwin", "chrome"): "Library/Application Support/Google/Chrome",
        ("Darwin", "brave"): "Library/Application Support/BraveSoftware/Brave-Browser",
        ("Darwin", "chromium"): "Library/Application Support/Chromium",
        ("Linux", "chrome"): ".config/google-chrome",
        ("Linux", "brave"): ".config/BraveSoftware/Brave-Browser",
        ("Linux", "chromium"): ".config/chromium",
    }
    for (system_name, browser), relative_path in expected.items():
        assert monitor.get_chromium_user_data_dir(browser, system_name=system_name, home=tmp_path) == tmp_path / relative_path


# Verifies Chromium discovery uses supported directories and Local State names
def test_chromium_profile_discovery_and_local_state_names(tmp_path):
    base_path = tmp_path / "user-data"
    (base_path / "Default/Network").mkdir(parents=True)
    (base_path / "Default/Network/Cookies").touch()
    (base_path / "Profile 1").mkdir()
    (base_path / "Profile 1/Cookies").touch()
    (base_path / "Guest Profile").mkdir()
    (base_path / "Guest Profile/Cookies").touch()
    local_state = {"profile": {"info_cache": {"Default": {"name": "Personal"}, "Profile 1": {"name": "Work"}}}}
    (base_path / "Local State").write_text(json.dumps(local_state), encoding="utf-8")

    profiles = monitor.discover_chromium_profiles("chrome", user_data_dir=base_path)

    assert [(profile["dir"], profile["name"]) for profile in profiles] == [("Default", "Personal"), ("Profile 1", "Work")]
    assert profiles[0]["cookie_file"].endswith("Default/Network/Cookies")
    assert profiles[1]["cookie_file"].endswith("Profile 1/Cookies")


# Verifies Network/Cookies is preferred over the legacy Cookies path
def test_chromium_cookie_resolution_prefers_network_layout(tmp_path):
    profile_dir = tmp_path / "Default"
    (profile_dir / "Network").mkdir(parents=True)
    (profile_dir / "Network/Cookies").touch()
    (profile_dir / "Cookies").touch()

    assert monitor.resolve_chromium_cookie_file(tmp_path, "Default") == profile_dir / "Network/Cookies"


# Verifies an explicit cookie database bypasses Chromium discovery
def test_explicit_chromium_cookie_file_takes_precedence(tmp_path, monkeypatch):
    cookie_file = tmp_path / "Cookies"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    monkeypatch.setattr(monitor, "discover_chromium_profiles", Mock(side_effect=AssertionError("profile discovery called")))
    monkeypatch.setattr(monitor, "read_chromium_sp_dc", Mock(return_value="secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))

    monitor.run_browser_cookie_import(browser="chrome", browser_profile="ignored", cookie_file=str(cookie_file), env_file=str(destination), interactive=False)

    assert dotenv_values(destination, interpolate=False)["SP_DC_COOKIE"] == "secret-cookie"


# Verifies missing pycookiecheat explains the optional extra and Firefox fallback
def test_missing_pycookiecheat_is_actionable(tmp_path):
    cookie_file = tmp_path / "Cookies"
    cookie_file.touch()
    with patch.dict(sys.modules, {"pycookiecheat": None}):
        with pytest.raises(monitor.BrowserCookieImportError, match=r"spotify_monitor\[browser\]") as error:
            monitor.read_chromium_sp_dc("chrome", cookie_file, system_name="Linux")
    assert "Firefox needs no extra dependency" in str(error.value)


# Verifies Windows rejection happens before the pycookiecheat adapter is called
def test_chromium_windows_rejection_precedes_dependency_import(tmp_path):
    cookie_file = tmp_path / "Cookies"
    cookie_file.touch()
    adapter = Mock(side_effect=AssertionError("adapter called"))

    with pytest.raises(monitor.BrowserCookieImportError, match="app-bound"):
        monitor.read_chromium_sp_dc("chrome", cookie_file, cookie_adapter=adapter, system_name="Windows")
    adapter.assert_not_called()


# Verifies the pycookiecheat adapter requests only open.spotify.com with an explicit database
def test_pycookiecheat_adapter_call_shape(tmp_path):
    cookie_file = tmp_path / "Cookies"
    cookie_file.touch()
    get_cookies = Mock(return_value={"sp_dc": "secret-cookie"})
    browser_types = types.SimpleNamespace(CHROME="chrome-type", BRAVE="brave-type", CHROMIUM="chromium-type")
    module = types.ModuleType("pycookiecheat")
    setattr(module, "BrowserType", browser_types)
    setattr(module, "get_cookies", get_cookies)

    with patch.dict(sys.modules, {"pycookiecheat": module}):
        result = monitor.read_chromium_sp_dc("brave", cookie_file, system_name="Linux")

    assert result == "secret-cookie"
    get_cookies.assert_called_once_with("https://open.spotify.com", browser="brave-type", cookie_file=str(cookie_file))


# Verifies Chromium collections without sp_dc get a clear error
def test_chromium_collection_without_sp_dc(tmp_path):
    cookie_file = tmp_path / "Cookies"
    cookie_file.touch()

    with pytest.raises(monitor.BrowserCookieImportError, match="No sp_dc cookie"):
        monitor.read_chromium_sp_dc("chromium", cookie_file, cookie_adapter=lambda browser, path: {"other": "value"}, system_name="Linux")


# Verifies pycookiecheat failures become safe actionable messages
def test_chromium_errors_are_secret_safe(tmp_path):
    cookie_file = tmp_path / "Cookies"
    cookie_file.touch()
    cases = [("keyring password SECRET", "keyring"), ("decrypt SECRET", "decrypt"), ("permission denied SECRET", "access")]
    for failure_text, expected_text in cases:
        with pytest.raises(monitor.BrowserCookieImportError) as error:
            monitor.read_chromium_sp_dc("chrome", cookie_file, cookie_adapter=Mock(side_effect=RuntimeError(failure_text)), system_name="Linux")
        assert expected_text in str(error.value).lower()
        assert "SECRET" not in str(error.value)


# Verifies one available profile is selected automatically
def test_single_profile_is_selected_automatically(tmp_path):
    profiles = sample_profiles(tmp_path)[:1]
    assert monitor.select_browser_profile(profiles, "firefox", interactive=False) is profiles[0]


# Verifies several profiles can be selected through an interactive prompt
def test_multiple_profiles_support_interactive_selection(tmp_path):
    selected = monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", interactive=True, input_func=lambda prompt: "2")
    assert selected["name"] == "Work"


# Verifies several profiles fail actionably in a noninteractive environment
def test_multiple_profiles_fail_noninteractively(tmp_path):
    with pytest.raises(monitor.BrowserCookieImportError, match="--browser-profile") as error:
        monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", interactive=False)
    assert "abc.default-release" in str(error.value)
    assert "xyz.work" in str(error.value)


# Verifies explicit selection works without an interactive terminal
def test_explicit_profile_selection_works_noninteractively(tmp_path):
    selected = monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", requested_profile="Personal", interactive=False)
    assert selected["dir"] == "abc.default-release"


# Verifies an unknown profile lists safe available choices
def test_unknown_profile_lists_choices(tmp_path):
    with pytest.raises(monitor.BrowserCookieImportError, match="Unknown Firefox profile") as error:
        monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", requested_profile="Missing", interactive=False)
    assert "Personal" in str(error.value)
    assert "Work" in str(error.value)


# Verifies no usable profiles gets a clear recovery message
def test_no_profiles_found_is_actionable():
    with pytest.raises(monitor.BrowserCookieImportError, match="No usable Firefox profiles") as error:
        monitor.select_browser_profile([], "firefox", interactive=False)
    assert "--cookie-file" in str(error.value)


# Verifies import mode reaches its runner without any monitoring target
def test_cli_import_mode_does_not_require_target():
    setup = "runtime['run_browser_cookie_import'] = lambda **kwargs: print(f'IMPORTED={kwargs[\"browser\"]}');"
    result = run_cli(["--import-browser-cookie"], setup)
    assert result.returncode == 0, result.stderr
    assert "IMPORTED=firefox" in result.stdout
    assert "target is required" not in result.stdout


# Verifies browser-only flags are rejected without import mode
def test_cli_rejects_import_only_flags_without_import():
    cases = [["--browser", "firefox"], ["--browser-profile", "Work"], ["--cookie-file", "Cookies"], ["--force"]]
    for arguments in cases:
        result = run_cli(arguments)
        assert result.returncode != 0
        assert "require --import-browser-cookie" in result.stderr


# Verifies import rejects a disabled dotenv destination
def test_import_env_none_is_rejected():
    with pytest.raises(monitor.BrowserCookieImportError, match="requires a dotenv destination"):
        monitor.resolve_import_env_path("none")


# Verifies the CLI rejects --env-file none before browser discovery
def test_cli_import_env_none_is_rejected():
    result = run_cli(["--import-browser-cookie", "--env-file", "none"])
    assert result.returncode == 1
    assert "requires a dotenv destination" in result.stdout


# Verifies the default import destination is cwd/.env without parent discovery
def test_default_import_destination_is_current_directory(tmp_path):
    assert monitor.resolve_import_env_path(cwd=tmp_path) == (tmp_path / ".env").resolve()


# Verifies an explicit dotenv destination is resolved directly
def test_explicit_import_destination(tmp_path):
    destination = tmp_path / "secrets/import.env"
    assert monitor.resolve_import_env_path(str(destination), cwd=tmp_path) == destination.resolve()


# Verifies CLI runner failures return a nonzero exit code
def test_cli_import_failure_exit_code():
    setup = "runtime['run_browser_cookie_import'] = lambda **kwargs: (_ for _ in ()).throw(runtime['BrowserCookieImportError']('safe failure'));"
    result = run_cli(["--import-browser-cookie"], setup)
    assert result.returncode == 1
    assert "safe failure" in result.stdout


# Verifies interactive profile cancellation is reported as a failure
def test_profile_selection_cancellation_is_failure(tmp_path):
    with pytest.raises(monitor.BrowserCookieImportError, match="cancelled"):
        monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", interactive=True, input_func=lambda prompt: "0")


# Verifies CLI cancellation returns a nonzero exit code
def test_cli_import_cancellation_exit_code():
    setup = "runtime['run_browser_cookie_import'] = lambda **kwargs: (_ for _ in ()).throw(runtime['BrowserCookieImportError']('Browser cookie import cancelled.'));"
    result = run_cli(["--import-browser-cookie"], setup)
    assert result.returncode == 1
    assert "cancelled" in result.stdout


# Verifies Spotify validation uses token acquisition and the authenticated buddy list
def test_spotify_cookie_validation_uses_existing_authentication_path(monkeypatch):
    refresh = Mock(return_value={"access_token": "access-token", "client_id": "client-id"})
    friends = Mock(return_value={"friends": []})
    monkeypatch.setattr(monitor, "refresh_access_token_from_sp_dc", refresh)
    monkeypatch.setattr(monitor, "spotify_get_friends_json", friends)

    assert monitor.validate_imported_sp_dc("secret-cookie") is True
    refresh.assert_called_once_with("secret-cookie")
    friends.assert_called_once_with("access-token")


# Verifies validation suppresses secret-bearing debug output then restores debug mode
def test_validation_suppresses_secret_debug_output(monkeypatch, capsys):
    secret = "DEBUG-COOKIE-SECRET-SENTINEL"
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    refresh = Mock(side_effect=lambda cookie: (monitor.debug_print(f"cookie={cookie}"), {"access_token": "access-token", "client_id": "client-id"})[1])
    friends = Mock(side_effect=lambda token: (monitor.debug_print(f"token={token}"), {"friends": []})[1])
    monkeypatch.setattr(monitor, "refresh_access_token_from_sp_dc", refresh)
    monkeypatch.setattr(monitor, "spotify_get_friends_json", friends)

    monitor.validate_imported_sp_dc(secret)

    captured = capsys.readouterr()
    assert secret not in captured.out
    assert "access-token" not in captured.out
    assert monitor.DEBUG_MODE is True


# Verifies failed validation leaves a missing dotenv destination untouched
def test_failed_validation_does_not_create_dotenv(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(side_effect=monitor.BrowserCookieImportError("invalid or expired cookie")))

    with pytest.raises(monitor.BrowserCookieImportError, match="invalid or expired"):
        monitor.run_browser_cookie_import(cookie_file=str(cookie_file), env_file=str(destination), interactive=False)
    assert not destination.exists()


# Verifies successful persistence updates only SP_DC_COOKIE and preserves unrelated content
def test_successful_validation_preserves_unrelated_dotenv_content(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    destination.write_text("# keep\nUNRELATED=stay\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))

    result = monitor.run_browser_cookie_import(cookie_file=str(cookie_file), env_file=str(destination), interactive=False)

    assert result == str(destination.resolve())
    assert destination.read_text(encoding="utf-8").startswith("# keep\nUNRELATED=stay\n")
    assert dotenv_values(destination, interpolate=False) == {"UNRELATED": "stay", "SP_DC_COOKIE": "secret-cookie"}


# Verifies overwrite decline leaves the dotenv file byte-for-byte unchanged
def test_overwrite_decline_preserves_dotenv_bytes(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    original = b"# keep\nSP_DC_COOKIE=old\nUNRELATED=stay\n"
    destination.write_bytes(original)
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="new-secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))

    with pytest.raises(monitor.BrowserCookieImportError, match="not changed"):
        monitor.run_browser_cookie_import(cookie_file=str(cookie_file), env_file=str(destination), interactive=True, input_func=lambda prompt: "n")
    assert destination.read_bytes() == original


# Verifies noninteractive overwrite requires force
def test_noninteractive_overwrite_requires_force(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    destination.write_text("SP_DC_COOKIE=old\n", encoding="utf-8")
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="new-secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))

    with pytest.raises(monitor.BrowserCookieImportError, match="--force"):
        monitor.run_browser_cookie_import(cookie_file=str(cookie_file), env_file=str(destination), interactive=False)
    assert dotenv_values(destination, interpolate=False)["SP_DC_COOKIE"] == "old"


# Verifies force bypasses only confirmation and still runs validation
def test_force_still_performs_validation(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    destination.write_text("SP_DC_COOKIE=old\n", encoding="utf-8")
    validate = Mock(return_value=True)
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="new-secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", validate)

    monitor.run_browser_cookie_import(cookie_file=str(cookie_file), env_file=str(destination), force=True, interactive=False)

    validate.assert_called_once_with("new-secret-cookie")
    assert dotenv_values(destination, interpolate=False)["SP_DC_COOKIE"] == "new-secret-cookie"


# Verifies imported secrets never appear in captured output or log records
def test_import_output_never_exposes_secrets(tmp_path, monkeypatch, capsys, caplog):
    secret = "PHASE2-COOKIE-SECRET-SENTINEL"
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value=secret))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))

    monitor.run_browser_cookie_import(cookie_file=str(cookie_file), env_file=str(destination), interactive=False)

    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err
    assert secret not in caplog.text


# Verifies a client token source is not rewritten during cookie import
def test_client_token_source_gets_nonsecret_note(tmp_path, monkeypatch, capsys):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    monkeypatch.setattr(monitor, "TOKEN_SOURCE", "client")
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))

    monitor.run_browser_cookie_import(cookie_file=str(cookie_file), env_file=str(destination), interactive=False)

    assert "TOKEN_SOURCE is set to client" in capsys.readouterr().out
    assert monitor.TOKEN_SOURCE == "client"


# Verifies validation network failures remain distinct and secret-safe
def test_validation_network_failure_is_distinct(monkeypatch):
    secret = "NETWORK-SECRET-SENTINEL"
    monkeypatch.setattr(monitor, "refresh_access_token_from_sp_dc", Mock(side_effect=RuntimeError(f"connection timeout {secret}")))

    with pytest.raises(monitor.BrowserCookieImportError, match="network or connectivity") as error:
        monitor.validate_imported_sp_dc(secret)
    assert secret not in str(error.value)


# Verifies token acquisition rejection is classified as invalid or expired
def test_validation_invalid_cookie_is_distinct(monkeypatch):
    monkeypatch.setattr(monitor, "refresh_access_token_from_sp_dc", Mock(side_effect=RuntimeError("401 Unauthorized")))

    with pytest.raises(monitor.BrowserCookieImportError, match="invalid or expired"):
        monitor.validate_imported_sp_dc("secret-cookie")


# Verifies buddy-list rejection is classified as Spotify authentication rejection
def test_validation_buddy_list_rejection_is_distinct(monkeypatch):
    monkeypatch.setattr(monitor, "refresh_access_token_from_sp_dc", Mock(return_value={"access_token": "access-token", "client_id": "client-id"}))
    monkeypatch.setattr(monitor, "spotify_get_friends_json", Mock(side_effect=RuntimeError("401 Unauthorized")))

    with pytest.raises(monitor.BrowserCookieImportError, match="Spotify authentication rejected"):
        monitor.validate_imported_sp_dc("secret-cookie")
