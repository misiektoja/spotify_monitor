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
def test_firefox_profiles_ini_discovery(tmp_path, real_browser_profiles):
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
def test_firefox_fallback_directory_discovery(tmp_path, real_browser_profiles):
    cookie_file = tmp_path / ".mozilla/firefox/scan.default-release/cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "cookie", 4102444800, 10)])

    profiles = monitor.discover_firefox_profiles(system_name="Linux", home=tmp_path)

    assert [(profile["dir"], profile["name"]) for profile in profiles] == [("scan.default-release", "default-release")]


# Verifies Linux standard, Snap and Flatpak Firefox locations are scanned
def test_firefox_linux_location_discovery(tmp_path, real_browser_profiles):
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
    assert windows_roots == [tmp_path / "Roaming/Mozilla/Firefox", tmp_path / "AppData/Roaming/Mozilla/Firefox"]


# Verifies a redirected application-data directory does not hide the home-relative root, and that the two
# collapse into one entry when they name the same directory
@pytest.mark.parametrize("appdata,expected_roots", [(None, ["AppData/Roaming/Mozilla/Firefox"]), ("AppData/Roaming", ["AppData/Roaming/Mozilla/Firefox"]), ("Redirected", ["Redirected/Mozilla/Firefox", "AppData/Roaming/Mozilla/Firefox"])])
def test_the_windows_roaming_root_covers_a_redirection(tmp_path, appdata, expected_roots):
    environ = {"APPDATA": str(tmp_path / appdata)} if appdata else {}

    roots = monitor._firefox_profile_roots(system_name="Windows", home=tmp_path, environ=environ)

    assert roots == [tmp_path / relative for relative in expected_roots]


# Verifies the Microsoft Store package is searched, since its profiles never appear under the roaming root
def test_the_windows_store_package_is_searched(tmp_path, real_browser_profiles):
    store_root = tmp_path / "AppData/Local/Packages/Mozilla.Firefox_n80bbvh6b1yt2/LocalCache/Roaming/Mozilla/Firefox"
    create_firefox_database(store_root / "Profiles/store.default-release/cookies.sqlite", [("spotify.com", "sp_dc", "cookie", 4102444800, 10)])

    profiles = monitor.discover_firefox_profiles(system_name="Windows", home=tmp_path, environ={})

    assert [(profile["dir"], profile["install"]) for profile in profiles] == [("store.default-release", "Microsoft Store")]


# Verifies a Store profile is told apart from a regular one, since both installs create a default-release
def test_a_store_profile_is_told_apart_from_a_regular_one(tmp_path, real_browser_profiles):
    create_firefox_database(tmp_path / "AppData/Roaming/Mozilla/Firefox/Profiles/abcd1234.default-release/cookies.sqlite", [])
    create_firefox_database(tmp_path / "AppData/Local/Packages/Mozilla.Firefox_n80bbvh6b1yt2/LocalCache/Roaming/Mozilla/Firefox/Profiles/abcd1234.default-release/cookies.sqlite", [])

    # The listing is ordered by name, directory then cookie file, so the package under AppData/Local sorts first
    profiles = monitor.discover_firefox_profiles(system_name="Windows", home=tmp_path, environ={})
    assert [profile["install"] for profile in profiles] == ["Microsoft Store", ""]

    with pytest.raises(monitor.BrowserCookieImportError, match="separate Firefox installs") as error:
        monitor.select_browser_profile(profiles, "firefox", requested_profile="abcd1234.default-release")
    assert "abcd1234.default-release (default-release) [Microsoft Store]" in str(error.value)


# Verifies the packaging is read from the path itself, so a Windows path is classified from any host
@pytest.mark.parametrize("path,expected", [("/home/u/.mozilla/firefox/a.default", ""), ("/home/u/snap/firefox/common/.mozilla/firefox/a.default", "Snap"), ("/home/u/.var/app/org.mozilla.firefox/.mozilla/firefox/a.default", "Flatpak"), (r"C:\Users\u\AppData\Roaming\Mozilla\Firefox\Profiles\a.default", ""), (r"C:\Users\u\AppData\Local\Packages\Mozilla.Firefox_n80bbvh6b1yt2\LocalCache\Roaming\Mozilla\Firefox\Profiles\a.default", "Microsoft Store")])
def test_the_packaging_is_read_from_the_path(path, expected):
    assert monitor.packaging_label(path) == expected


# Verifies a Firefox friendly name selects the intended profile
def test_profile_selection_by_friendly_name(tmp_path):
    selected = monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", requested_profile="work", interactive=False)
    assert selected["dir"] == "xyz.work"


# Verifies a Firefox directory basename selects the intended profile
def test_profile_selection_by_directory_basename(tmp_path):
    selected = monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", requested_profile="ABC.DEFAULT-RELEASE", interactive=False)
    assert selected["name"] == "Personal"


# Verifies an explicit cookie database bypasses Firefox profile discovery
def test_explicit_firefox_cookie_file_takes_precedence_and_prints_followup_commands(tmp_path, monkeypatch, capsys):
    cookie_file = tmp_path / "explicit.sqlite"
    cookie_file.touch()
    destination = tmp_path / "import.env"
    monkeypatch.setattr(monitor, "discover_firefox_profiles", Mock(side_effect=AssertionError("profile discovery called")))
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))

    config_path = tmp_path / "spotify_monitor.conf"
    config_path.write_text("TOKEN_SOURCE = 'cookie'\n", encoding="utf-8")
    monitor.run_browser_cookie_import(browser="firefox", browser_profile="ignored", cookie_file=str(cookie_file), env_file=str(destination), interactive=False, config_path=config_path, target="target.user")

    assert dotenv_values(destination, interpolate=False)["SP_DC_COOKIE"] == "secret-cookie"
    output = capsys.readouterr().out
    assert monitor.SPOTIFY_WEB_LOGIN_URL in output
    assert "* Browser cookie import completed successfully\n\nCheck setup again:" in output
    assert "Check setup again:" in output
    assert "--doctor target.user" in output
    assert f"--config-file {config_path}" in output
    assert "After Doctor passes, start monitoring:" in output


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


# Returns two synthetic Firefox profile records naming the given cookie database as the selected one
def firefox_profile_records(selected_cookie_file):
    return [
        {"dir": "aaaa1111.default-release", "name": "default-release", "path": str(Path(selected_cookie_file).parent), "cookie_file": str(selected_cookie_file)},
        {"dir": "bbbb2222.work", "name": "Work", "path": "/elsewhere/bbbb2222.work", "cookie_file": "/elsewhere/bbbb2222.work/cookies.sqlite"},
    ]


# Verifies the expiry ranking works on current Firefox, which records cookie expiry in milliseconds
@pytest.mark.parametrize("unit", [1, 1000], ids=["seconds", "milliseconds"])
def test_firefox_prefers_the_unexpired_cookie_in_either_expiry_unit(tmp_path, unit):
    now = 1_700_000_000
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [
        ("spotify.com", "sp_dc", "expired-but-touched-recently", (now - 365 * 86400) * unit, 200),
        ("open.spotify.com", "sp_dc", "still-valid", (now + 365 * 86400) * unit, 100),
    ])

    assert monitor.read_firefox_sp_dc(cookie_file, now=now) == "still-valid"


# Verifies a millisecond expiry is not mistaken for a date far in the future
def test_firefox_expiry_unit_is_taken_from_the_magnitude():
    assert monitor._cookie_expiry_seconds(1_819_314_035_557) == 1_819_314_035.557
    assert monitor._cookie_expiry_seconds(1_715_811_780) == 1_715_811_780
    assert monitor._cookie_expiry_seconds(5000) == 5000
    assert monitor._cookie_expiry_seconds(0) == 0


# Verifies a profile whose every sp_dc has lapsed is reported from the database without a Spotify request
def test_firefox_reports_a_wholly_expired_profile_without_a_request(tmp_path, monkeypatch):
    now = 1_700_000_000
    expired_at = now - 400 * 86400
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "lapsed-secret", expired_at * 1000, 200)])
    monkeypatch.setattr(monitor, "discover_firefox_profiles", lambda *arguments, **keywords: firefox_profile_records(cookie_file))

    with pytest.raises(monitor.BrowserCookieImportError, match="expired on") as error:
        monitor.read_firefox_sp_dc(cookie_file, now=now)
    message = str(error.value)
    assert monitor.get_date_from_ts(expired_at) in message
    assert "aaaa1111.default-release" in message
    assert "lapsed-secret" not in message


# Verifies the whole import stops at the expired cookie rather than asking Spotify about it
def test_an_expired_firefox_cookie_never_reaches_validation(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "lapsed-secret", 1_600_000_000 * 1000, 200)])
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(side_effect=AssertionError("Spotify was asked about an expired cookie")))

    with pytest.raises(monitor.BrowserCookieImportError, match="expired on"):
        monitor.run_browser_cookie_import(browser="firefox", cookie_file=str(cookie_file), env_file=str(tmp_path / ".env"), interactive=False)
    assert not (tmp_path / ".env").exists()


# Verifies a failure names the profile that failed and the other profiles a session could be in
def test_firefox_failures_name_the_profile_and_the_alternatives(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "other", "not-secret", 5000, 20)])
    monkeypatch.setattr(monitor, "discover_firefox_profiles", lambda *arguments, **keywords: firefox_profile_records(cookie_file))

    with pytest.raises(monitor.BrowserCookieImportError, match="No sp_dc cookie") as error:
        monitor.read_firefox_sp_dc(cookie_file, now=1000)
    message = str(error.value)
    assert "Firefox profile aaaa1111.default-release (default-release)" in message
    assert "Other Firefox profiles found: bbbb2222.work (Work)." in message


# Verifies a machine carrying many profiles gets a bounded list rather than all of them
def test_firefox_alternatives_are_capped(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "other", "not-secret", 5000, 20)])
    extras = [{"dir": f"p{index}.profile{index}", "name": f"profile{index}", "path": f"/x/p{index}", "cookie_file": f"/x/p{index}/cookies.sqlite"} for index in range(12)]
    monkeypatch.setattr(monitor, "discover_firefox_profiles", lambda *arguments, **keywords: firefox_profile_records(cookie_file)[:1] + extras)

    with pytest.raises(monitor.BrowserCookieImportError) as error:
        monitor.read_firefox_sp_dc(cookie_file, now=1000)
    message = str(error.value)
    assert message.count("cookies.sqlite") == 0
    assert "and 6 more." in message
    assert "p6.profile6" not in message


# Verifies an unreadable database also names the profile and the alternatives
def test_firefox_unreadable_database_names_the_alternatives(tmp_path, monkeypatch):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.write_text("not a SQLite database", encoding="utf-8")
    monkeypatch.setattr(monitor, "discover_firefox_profiles", lambda *arguments, **keywords: firefox_profile_records(cookie_file))

    with pytest.raises(monitor.BrowserCookieImportError, match="Close Firefox") as error:
        monitor.read_firefox_sp_dc(cookie_file)
    assert "Other Firefox profiles found: bbbb2222.work (Work)." in str(error.value)


# Verifies the suite never reaches the browser profiles of the machine running it
def test_browser_profile_discovery_is_stubbed_by_default():
    assert monitor.discover_firefox_profiles() == []
    assert monitor.discover_chromium_profiles("chrome") == []


# Verifies a cookie a running Firefox has written only to its write-ahead log is still found
def test_firefox_reads_a_cookie_left_in_the_write_ahead_log(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "checkpointed-cookie", 5000, 10)])
    with sqlite3.connect(cookie_file) as setup_connection:
        setup_connection.execute("PRAGMA journal_mode=WAL")
        setup_connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    writer = sqlite3.connect(cookie_file)
    try:
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("INSERT INTO moz_cookies VALUES (?, ?, ?, ?, ?)", ("spotify.com", "sp_dc", "log-only-cookie", 5000, 20))
        writer.commit()
        assert (tmp_path / "cookies.sqlite-wal").stat().st_size > 0

        assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "log-only-cookie"
    finally:
        writer.close()


# Verifies a cookie database on read-only media stays readable, which is how the container mounts a Firefox profile
def test_firefox_reads_a_database_on_read_only_media(tmp_path):
    profile_dir = tmp_path / "readonly"
    cookie_file = profile_dir / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "mounted-cookie", 5000, 10)])
    # Firefox keeps its cookie database in write-ahead logging mode, and opening one of those read-only needs to
    # create a shared-memory file, which is exactly what a read-only mount refuses
    with sqlite3.connect(cookie_file) as journal_connection:
        journal_connection.execute("PRAGMA journal_mode=WAL")
        journal_connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    (profile_dir / "cookies.sqlite-wal").unlink(missing_ok=True)
    (profile_dir / "cookies.sqlite-shm").unlink(missing_ok=True)
    cookie_file.chmod(0o444)
    profile_dir.chmod(0o555)
    try:
        assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "mounted-cookie"
    finally:
        profile_dir.chmod(0o755)
        cookie_file.chmod(0o644)


# Verifies a profile with a write-ahead log that a browser holds locked falls back to the immutable open
def test_firefox_falls_back_when_a_logged_database_is_locked(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "locked-log-cookie", 5000, 10)])
    (tmp_path / "cookies.sqlite-wal").write_bytes(b"")
    attempted = []

    real_connect = sqlite3.connect

    # Refuses the read-only open the way a browser holding the database does, leaving the immutable open to answer
    def refuse_read_only(database, *arguments, **keywords):
        attempted.append(database)
        if isinstance(database, str) and database.endswith("?mode=ro"):
            raise sqlite3.OperationalError("database is locked")
        return real_connect(database, *arguments, **keywords)

    with patch.object(monitor.sqlite3, "connect", refuse_read_only):
        assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "locked-log-cookie"
    assert any(database.endswith("?mode=ro") for database in attempted)
    assert any(database.endswith("?immutable=1") for database in attempted)


# Verifies a profile path holding URI punctuation cannot displace the SQLite access parameters
def test_firefox_path_punctuation_cannot_displace_uri_parameters(tmp_path):
    cookie_file = tmp_path / "we?ird#profile" / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "punctuated-cookie", 5000, 10)])

    assert monitor._sqlite_cookie_uri(cookie_file.resolve(), "immutable=1").endswith("we%3Fird%23profile/cookies.sqlite?immutable=1")
    assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "punctuated-cookie"


# Verifies the cookie database connection is closed rather than left to the garbage collector
def test_firefox_closes_the_cookie_database_connection(tmp_path):
    cookie_file = tmp_path / "cookies.sqlite"
    create_firefox_database(cookie_file, [("spotify.com", "sp_dc", "closed-cookie", 5000, 10)])
    opened = []

    real_connect = sqlite3.connect

    # Records every connection the reader opens so the test can assert each one was closed
    def record_connect(*arguments, **keywords):
        connection = real_connect(*arguments, **keywords)
        opened.append(connection)
        return connection

    with patch.object(monitor.sqlite3, "connect", record_connect):
        assert monitor.read_firefox_sp_dc(cookie_file, now=1000) == "closed-cookie"
    assert opened
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


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


# Verifies every configured Chromium root is a usable relative path under the home directory
def test_chromium_roots_are_relative_and_named_per_platform(tmp_path, real_browser_profiles):
    assert set(monitor.CHROMIUM_USER_DATA_DIRS) == {"Darwin", "Linux"}
    for system_name, browsers in monitor.CHROMIUM_USER_DATA_DIRS.items():
        assert set(browsers) == set(monitor.CHROMIUM_IMPORT_BROWSERS)
        for browser, relative_paths in browsers.items():
            assert relative_paths, f"{system_name}/{browser} names no root"
            assert len(set(relative_paths)) == len(relative_paths), f"{system_name}/{browser} repeats a root"
            for relative_path in relative_paths:
                assert not Path(relative_path).is_absolute()
            # With nothing installed the conventional root is still named, so a failure can say where it looked
            assert monitor.get_chromium_user_data_dir(browser, system_name=system_name, home=tmp_path) == tmp_path / relative_paths[0]


# Verifies a packaged install is found and a distribution install still wins when both are present
def test_chromium_packaged_roots_are_searched_in_order(tmp_path, real_browser_profiles):
    for system_name, browsers in monitor.CHROMIUM_USER_DATA_DIRS.items():
        for browser, relative_paths in browsers.items():
            home = tmp_path / f"{system_name}-{browser}"
            packaged = home / relative_paths[-1]
            packaged.mkdir(parents=True)
            assert monitor.get_chromium_user_data_dir(browser, system_name=system_name, home=home) == packaged
            distribution = home / relative_paths[0]
            distribution.mkdir(parents=True, exist_ok=True)
            assert monitor.get_chromium_user_data_dir(browser, system_name=system_name, home=home) == distribution


# Verifies Snap and Flatpak Chromium trees are reachable, which a single configured root per browser is not
def test_chromium_linux_reaches_snap_and_flatpak_trees(real_browser_profiles):
    linux_roots = monitor.CHROMIUM_USER_DATA_DIRS["Linux"]
    assert any("snap/" in root for root in linux_roots["chromium"])
    assert any(".var/app/" in root for root in linux_roots["chromium"])
    assert any("snap/" in root for root in linux_roots["brave"])
    assert any(".var/app/" in root for root in linux_roots["brave"])


# Verifies an unsupported platform is reported as having no known location rather than as a missing directory
def test_chromium_unknown_platform_has_no_root(real_browser_profiles, tmp_path):
    assert monitor.get_chromium_user_data_dir("chrome", system_name="Plan9", home=tmp_path) is None
    assert "no known Chrome profile location" in monitor.chromium_no_profiles_message("chrome", system_name="Plan9", home=tmp_path)


# Verifies each reason a Chromium listing can be empty gets its own fix, since they need different actions
def test_chromium_empty_listing_separates_its_causes(tmp_path, real_browser_profiles):
    (tmp_path / "EmptyRoot").mkdir()
    (tmp_path / "NewProfile" / "Default").mkdir(parents=True)

    not_installed = monitor.chromium_no_profiles_message("chrome", user_data_dir=tmp_path / "missing")
    assert "Install Chrome" in not_installed and "Looked in" in not_installed

    no_profiles = monitor.chromium_no_profiles_message("chrome", user_data_dir=tmp_path / "EmptyRoot")
    assert "Open Chrome once to create a profile" in no_profiles
    assert "Install Chrome" not in no_profiles

    no_cookies = monitor.chromium_no_profiles_message("chrome", user_data_dir=tmp_path / "NewProfile")
    assert "Chrome is installed but none of its profiles (Default) holds a cookie database yet" in no_cookies
    assert "Install Chrome" not in no_cookies


# Verifies the import surfaces the specific reason rather than the generic one
def test_chromium_import_reports_the_specific_empty_reason(tmp_path, monkeypatch, real_browser_profiles):
    user_data_dir = tmp_path / "NewProfile"
    (user_data_dir / "Default").mkdir(parents=True)
    monkeypatch.setattr(monitor, "get_chromium_user_data_dir", lambda *arguments, **keywords: user_data_dir)

    with pytest.raises(monitor.BrowserCookieImportError, match="holds a cookie database yet") as error:
        monitor.run_browser_cookie_import(browser="chrome", env_file=str(tmp_path / ".env"), interactive=False)
    assert "No usable Chrome profiles found" not in str(error.value)


# Verifies each keyring failure the supported backends actually raise gets the fix that matches its cause
@pytest.mark.parametrize("error_text, expected", [
    ("Can't get password from keychain: Keychain Access Denied", "Unlock the keyring"),
    ("Could not find a password for the pair (Chrome Safe Storage, Chrome).", "Unlock the keyring"),
    ("Failed to unlock the collection!", "Unlock the keyring"),
    ("Failed to unlock the item!", "Unlock the keyring"),
    ("Failed to unlock the keyring!", "Unlock the keyring"),
    ("No recommended backend was available. Install a recommended 3rd party backend package", "Install one such as gnome-keyring"),
])
def test_chromium_keyring_failures_name_the_real_fix(error_text, expected):
    message = monitor._safe_chromium_cookie_error("chrome", Exception(error_text))
    assert expected in message
    assert "Confirm Spotify is signed in" not in message


# Verifies Chromium discovery uses supported directories and Local State names
def test_chromium_profile_discovery_and_local_state_names(tmp_path, real_browser_profiles):
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
    # A synthetic module cannot declare these attributes, so setattr keeps the type checker quiet
    setattr(module, "BrowserType", browser_types)  # noqa: B010
    setattr(module, "get_cookies", get_cookies)  # noqa: B010

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
def test_multiple_profiles_support_interactive_selection(tmp_path, capsys):
    supplied = iter(["2"])
    selected = monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", interactive=True, input_func=lambda prompt: next(supplied))
    assert selected["name"] == "Work"
    assert capsys.readouterr().out.startswith("\nMultiple Firefox profiles found:")


# Creates a synthetic Chromium cookie database holding only encrypted values
def create_chromium_database(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, encrypted_value BLOB, expires_utc INTEGER, is_persistent INTEGER)")
        connection.executemany("INSERT INTO cookies VALUES (?, ?, ?, ?, ?)", rows)


# Returns profile records for the picker, marking which ones the probe should call live
def picker_profiles(count, install=""):
    return [{"dir": f"p{index}.name{index}", "name": f"name{index}", "path": f"/p/p{index}", "cookie_file": f"/p/p{index}/cookies.sqlite", "install": install} for index in range(1, count + 1)]


# Verifies invalid input re-asks instead of ending the import, which a typo previously did
@pytest.mark.parametrize("answers, expected", [
    (["abc", "2"], "p2.name2"),
    (["-1", "3"], "p3.name3"),
    (["99", "1"], "p1.name1"),
    (["", "2"], "p2.name2"),
    (["2.5", "1"], "p1.name1"),
])
def test_the_picker_re_asks_on_invalid_input(monkeypatch, capsys, answers, expected):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)
    supplied = iter(answers)

    selected = monitor.select_browser_profile(picker_profiles(3), "firefox", interactive=True, input_func=lambda prompt: next(supplied))

    assert selected["dir"] == expected
    assert "Enter a number between 1 and 3, or 0 to cancel." in capsys.readouterr().out


# Verifies a negative number is refused rather than indexing backwards from the end of the list
def test_the_picker_never_indexes_backwards(monkeypatch):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)
    supplied = iter(["-1", "-3", "1"])

    assert monitor.select_browser_profile(picker_profiles(3), "firefox", interactive=True, input_func=lambda prompt: next(supplied))["dir"] == "p1.name1"


# Verifies a closed input stream cancels rather than looping forever
@pytest.mark.parametrize("interruption", [EOFError, KeyboardInterrupt])
def test_the_picker_cancels_on_a_closed_prompt(monkeypatch, interruption):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)

    with pytest.raises(monitor.BrowserCookieImportError, match="cancelled"):
        monitor.select_browser_profile(picker_profiles(3), "firefox", interactive=True, input_func=Mock(side_effect=interruption))


# Verifies only profiles holding a current login are marked and the single one becomes the Enter default
def test_the_picker_marks_and_preselects_the_only_live_profile(monkeypatch, capsys):
    profiles = picker_profiles(3)
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda cookie_file, **keywords: cookie_file == profiles[1]["cookie_file"])

    prompts = []
    supplied = iter([""])

    selected = monitor.select_browser_profile(profiles, "firefox", interactive=True, input_func=lambda prompt: (prompts.append(prompt), next(supplied))[1])

    assert selected["dir"] == "p2.name2"
    output = capsys.readouterr().out
    assert "* marks a profile holding a current Spotify login" in output
    assert "2) * name2" in output
    assert "(default)" in output
    assert "1) * " not in output
    assert "Enter for default" in prompts[0]


# Verifies nothing is marked or preselected when no profile holds a current login
def test_the_picker_marks_nothing_when_no_profile_is_live(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: False)
    supplied = iter(["", "2"])
    prompts = []

    selected = monitor.select_browser_profile(picker_profiles(3), "firefox", interactive=True, input_func=lambda prompt: (prompts.append(prompt), next(supplied))[1])

    assert selected["dir"] == "p2.name2"
    output = capsys.readouterr().out
    assert "marks a profile" not in output
    assert "(default)" not in output
    assert "Enter for default" not in prompts[0]
    assert "Enter a number between 1 and 3" in output


# Verifies several live profiles are all marked but none is preselected
def test_the_picker_preselects_nothing_when_several_are_live(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: True)
    supplied = iter(["", "3"])

    selected = monitor.select_browser_profile(picker_profiles(3), "firefox", interactive=True, input_func=lambda prompt: next(supplied))

    assert selected["dir"] == "p3.name3"
    output = capsys.readouterr().out
    assert output.count("* name") == 3
    assert "(default)" not in output


# Verifies profile numbers line up once the list reaches double digits
def test_the_picker_right_aligns_its_numbers(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)

    supplied = iter(["1"])
    monitor.select_browser_profile(picker_profiles(12), "firefox", interactive=True, input_func=lambda prompt: next(supplied))

    output = capsys.readouterr().out
    assert "   1) name1" in output
    assert "  12) name12" in output


# Verifies the only profile available is warned about when it holds no current login
def test_a_single_signed_out_profile_is_warned_about(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: False)

    selected = monitor.select_browser_profile(picker_profiles(1), "firefox")

    assert selected["dir"] == "p1.name1"
    assert "holds no current Spotify login" in capsys.readouterr().out


# Verifies an unreadable database leaves the only profile unwarned rather than called signed out
def test_a_single_unreadable_profile_is_not_called_signed_out(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "profile_has_live_spotify_cookie", lambda *arguments, **keywords: None)

    monitor.select_browser_profile(picker_profiles(1), "firefox")

    assert "holds no current Spotify login" not in capsys.readouterr().out


# Verifies two installs sharing one profile directory name are told apart and given advice that works
def test_a_directory_name_shared_by_two_installs_names_the_cookie_file(real_browser_profiles, tmp_path):
    for relative_path in (".mozilla/firefox/abcd1234.default-release", "snap/firefox/common/.mozilla/firefox/abcd1234.default-release"):
        create_firefox_database(tmp_path / relative_path / "cookies.sqlite", [])
    profiles = monitor.discover_firefox_profiles(system_name="Linux", home=tmp_path)
    assert [profile["install"] for profile in profiles] == ["", "Snap"]

    with pytest.raises(monitor.BrowserCookieImportError, match="separate Firefox installs") as error:
        monitor.select_browser_profile(profiles, "firefox", requested_profile="abcd1234.default-release")
    message = str(error.value)
    assert "--cookie-file PATH" in message
    assert "abcd1234.default-release (default-release) [Snap]" in message


# Verifies a live Spotify cookie is recognised on both schemas without any value being decrypted
def test_the_live_cookie_probe_reads_both_schemas(tmp_path):
    now = 1_700_000_000
    live_chromium = int((now + 86400 + monitor.CHROMIUM_EPOCH_OFFSET_SECONDS) * 1_000_000)
    dead_chromium = int((now - 86400 + monitor.CHROMIUM_EPOCH_OFFSET_SECONDS) * 1_000_000)

    create_firefox_database(tmp_path / "ff-live.sqlite", [("spotify.com", "sp_dc", "x", (now + 86400) * 1000, 10)])
    create_firefox_database(tmp_path / "ff-dead.sqlite", [("spotify.com", "sp_dc", "x", (now - 86400) * 1000, 10)])
    create_firefox_database(tmp_path / "ff-legacy.sqlite", [("spotify.com", "sp_dc", "x", now + 86400, 10)])
    create_firefox_database(tmp_path / "ff-none.sqlite", [("spotify.com", "other", "x", (now + 86400) * 1000, 10)])
    create_firefox_database(tmp_path / "ff-foreign.sqlite", [("notspotify.com", "sp_dc", "x", (now + 86400) * 1000, 10)])
    create_chromium_database(tmp_path / "cr-live.sqlite", [(".spotify.com", "sp_dc", b"encrypted", live_chromium, 1)])
    create_chromium_database(tmp_path / "cr-dead.sqlite", [(".spotify.com", "sp_dc", b"encrypted", dead_chromium, 1)])
    create_chromium_database(tmp_path / "cr-session.sqlite", [(".spotify.com", "sp_dc", b"encrypted", 0, 0)])
    (tmp_path / "broken.sqlite").write_text("not a database", encoding="utf-8")

    assert monitor.profile_has_live_spotify_cookie(tmp_path / "ff-live.sqlite", firefox=True, now=now) is True
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "ff-legacy.sqlite", firefox=True, now=now) is True
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "ff-dead.sqlite", firefox=True, now=now) is False
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "ff-none.sqlite", firefox=True, now=now) is False
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "ff-foreign.sqlite", firefox=True, now=now) is False
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "cr-live.sqlite", now=now) is True
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "cr-dead.sqlite", now=now) is False
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "cr-session.sqlite", now=now) is True
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "broken.sqlite", now=now) is None
    assert monitor.profile_has_live_spotify_cookie(tmp_path / "absent.sqlite", now=now) is None
    assert monitor.profile_has_live_spotify_cookie("", now=now) is None


# Verifies each reason a Firefox listing can be empty gets its own fix
def test_firefox_empty_listing_separates_its_causes(tmp_path, real_browser_profiles):
    assert "no known Firefox profile location" in monitor.firefox_no_profiles_message(system_name="Plan9", home=tmp_path)

    not_installed = monitor.firefox_no_profiles_message(system_name="Darwin", home=tmp_path)
    assert "Install Firefox" in not_installed and "Looked in" in not_installed

    (tmp_path / "Library/Application Support/Firefox").mkdir(parents=True)
    no_cookies = monitor.firefox_no_profiles_message(system_name="Darwin", home=tmp_path)
    assert "holds a cookie database yet" in no_cookies
    assert "Install Firefox" not in no_cookies


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
    supplied = iter(["0"])
    with pytest.raises(monitor.BrowserCookieImportError, match="cancelled"):
        monitor.select_browser_profile(sample_profiles(tmp_path), "firefox", interactive=True, input_func=lambda prompt: next(supplied))


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


# Runs one successful import and returns the printed next-steps output
def import_and_capture(tmp_path, monkeypatch, capsys, **keywords):
    cookie_file = tmp_path / "cookies.sqlite"
    cookie_file.touch()
    monkeypatch.setattr(monitor, "read_firefox_sp_dc", Mock(return_value="secret-cookie"))
    monkeypatch.setattr(monitor, "validate_imported_sp_dc", Mock(return_value=True))
    monitor.run_browser_cookie_import(cookie_file=str(cookie_file), env_file=str(tmp_path / "import.env"), interactive=False, **keywords)
    return capsys.readouterr().out


# Verifies a target the config will not supply is printed in both next-steps commands
def test_a_target_the_config_does_not_hold_is_printed_in_both_commands(tmp_path, monkeypatch, capsys):
    output = import_and_capture(tmp_path, monkeypatch, capsys, target="friend.user", saved_target="")
    assert output.count("friend.user") == 2
    assert "<spotify_target>" not in output


# Verifies the caller can leave the next-steps commands out and the output then ends with the completion line
def test_the_next_steps_can_be_left_out(tmp_path, monkeypatch, capsys):
    output = import_and_capture(tmp_path, monkeypatch, capsys, print_next_steps=False)
    assert output.endswith("* Browser cookie import completed successfully\n")
    assert "Check setup again:" not in output


# Verifies a target already saved in the config is left out of both next-steps commands
def test_a_target_saved_in_the_config_is_left_out_of_both_commands(tmp_path, monkeypatch, capsys):
    output = import_and_capture(tmp_path, monkeypatch, capsys, target="friend.user", saved_target="friend.user")
    assert "friend.user" not in output
    assert "<spotify_target>" not in output


# Verifies only the monitoring command carries the placeholder when no target is known at all
def test_no_known_target_places_the_placeholder_in_the_monitoring_command_only(tmp_path, monkeypatch, capsys):
    output = import_and_capture(tmp_path, monkeypatch, capsys, saved_target="")
    doctor_line, monitor_line = output.split("Check setup again:", 1)[1].split("After Doctor passes, start monitoring:", 1)
    assert "<spotify_target>" not in doctor_line
    assert "<spotify_target>" in monitor_line


# Verifies the persisted target is read from the config file when the caller knows no target
def test_a_config_file_target_is_read_when_the_caller_knows_no_target(tmp_path, monkeypatch, capsys):
    with_target = tmp_path / "with_target.conf"
    with_target.write_text('TARGET_USER_URI_ID = "saved.user"\n', encoding="utf-8")
    without_target = tmp_path / "without_target.conf"
    without_target.write_text('TARGET_USER_URI_ID = ""\n', encoding="utf-8")
    saved_output = import_and_capture(tmp_path, monkeypatch, capsys, config_path=str(with_target))
    unsaved_output = import_and_capture(tmp_path, monkeypatch, capsys, config_path=str(without_target), force=True)
    assert "<spotify_target>" not in saved_output
    assert "saved.user" not in saved_output
    assert "<spotify_target>" in unsaved_output


PROGRESS_LINES = (
    "* Cookie extracted. Checking it with Spotify ...",
    "* Checking the entered Spotify cookie before changing the dotenv file ...",
)


# Verifies each wait on a remote service is announced with the wording every sibling monitor uses
@pytest.mark.parametrize("line", PROGRESS_LINES)
def test_the_progress_lines_use_the_shared_checking_wording(line):
    assert line in (PROJECT_ROOT / "spotify_monitor.py").read_text(encoding="utf-8"), line
