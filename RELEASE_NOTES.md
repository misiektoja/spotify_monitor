# spotify_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 2.8 (07 Feb 2026)

**Features and Improvements**:

- **IMPROVE:** Migrated deprecated `GET /browse/categories` and `GET /users/{id}` endpoints to handle **Spotify API changes** scheduled for **February 11, 2026**; used `GET /tracks/{id}` for oauth_app token validation and `spclient` internal API for user status checks
- **IMPROVE:** Enhanced `--generate-config` to support writing directly to a file (e.g. `spotify_monitor --generate-config spotify_monitor.conf`). This avoids UTF-16 encoding issues on **Windows PowerShell**
- **IMPROVE:** Expanded tabs to spaces in output log files to ensure **consistent alignment across different viewers**
- **IMPROVE:** Enhanced error handling for empty or malformed secret files
- **IMPROVE:** Added `spotify_monitor_secret_grabber` and `spotify_monitor_totp_test` as pip-installed **console scripts**

# Changes in 2.7 (27 Dec 2025)

**Features and Improvements**:

- **NEW:** Implemented **hybrid authentication approach** to support two auth methods: **cookie/client** for friend activity monitoring and **oauth_app** (**Client Credentials OAuth Flow**) for track API calls to address restrictions introduced by Spotify on **22 Dec 2025** (thanks [@tomballgithub](https://github.com/tomballgithub) and [@0xXiHan](https://github.com/0xXiHan), fixes [#27](https://github.com/misiektoja/spotify_monitor/issues/27))
- **NEW:** Added configuration options (`SP_APP_CLIENT_ID`, `SP_APP_CLIENT_SECRET`) and `-r` / `--oauth-app-creds` flag for **Client Credentials OAuth Flow (oauth_app)**
- **NEW:** Added **OAuth app token caching** via `SP_APP_TOKENS_FILE` configuration option
- **NEW:** Added **Spotipy** dependency (required since v2.7 due to new Spotify restrictions)
- **IMPROVE:** Enhanced **email notification formatting**

**Bug fixes**:

- **BUGFIX:** Removed `spotify_get_playlist_info` function to overcome Spotify's client credentials flow limitations and streamline playlist handling (fixes [#31](https://github.com/misiektoja/spotify_monitor/issues/31))
- **BUGFIX:** Removed old **TOTP versions** from `SECRET_CIPHER_DICT` (fixes [#28](https://github.com/misiektoja/spotify_monitor/issues/28))
- **BUGFIX:** Updated **TOTP version handling** in `refresh_access_token_from_sp_dc` function to ensure compatibility with varying **TOTP versions** (fixes [#32](https://github.com/misiektoja/spotify_monitor/issues/32))
- **BUGFIX:** Added missing **OAuth app** support for user removal check and improved error handling in `is_user_removed` function (fixes [#30](https://github.com/misiektoja/spotify_monitor/issues/30))

**Breaking changes**:

- **BREAKING:** Removed **token owner display** at startup due to `/v1/me` endpoint limitations introduced by Spotify on **22 Dec 2025**
- **BREAKING:** **OAuth app credentials** are now required for track information retrieval when using either `cookie` or `client` **token source methods**

# Changes in 2.6 (11 Nov 2025)

**Features and Improvements**:

- **NEW:** Added support for **Amazon Music**, **Deezer** and **Tidal** URLs in console and email outputs
- **NEW:** Added support for **AZLyrics**, **Tekstowo.pl**, **Musixmatch** and **Lyrics.com** lyrics services
- **NEW:** Added detection and annotation for **crossfaded songs** during playback with configurable thresholds (see `DETECT_CROSSFADED_SONGS`, `CROSSFADE_DETECTION_MIN` and `CROSSFADE_DETECTION_MAX` config options)
- **NEW:** Added configuration options to enable/disable music service URLs in console and email outputs (see `ENABLE_APPLE_MUSIC_URL`, `ENABLE_YOUTUBE_MUSIC_URL`, `ENABLE_AMAZON_MUSIC_URL`, `ENABLE_DEEZER_URL` and `ENABLE_TIDAL_URL` config options)
- **NEW:** Added configuration options to enable/disable lyrics service URLs in console and email outputs (see `ENABLE_GENIUS_LYRICS_URL`, `ENABLE_AZLYRICS_URL`, `ENABLE_TEKSTOWO_URL`, `ENABLE_MUSIXMATCH_URL` and `ENABLE_LYRICS_COM_URL` config options)
- **NEW:** Added recent songs tracking in session with inclusion in inactivity emails, including skipped track status (see `INACTIVE_EMAIL_RECENT_SONGS_COUNT` config option)
- **IMPROVE:** Introduced tolerance for "Played for" display to account for playback duration discrepancies (see `PLAYED_FOR_DURATION_TOLERANCE` config option)
- **IMPROVE:** Token owner info is now displayed at startup before the monitoring loop

**Bug fixes**:

- **BUGFIX:** Fixed "Played for" display when songs are played longer than track duration
- **BUGFIX:** Prevented duplicate emails when songs on loop also match track/song alerts

# Changes in 2.5 (12 Oct 2025)

**Features and Improvements**:

- **IMPROVE:** Added support for loading TOTP secrets from local files via file:// URLs
- **IMPROVE:** Updated remote URL in SECRET_CIPHER_DICT_URL
- **IMPROVE:** Updated  [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_secret_grabber.py) to dump secrets in different formats. Choose what you need with the `--secret`,` --secretbytes` and `--secretdict` CLI flags, or go all out with the `--all` mode to write all secret formats to files like `secrets.json`, `secretBytes.json` and `secretDict.json` (thanks [@tomballgithub](https://github.com/tomballgithub))
- **IMPROVE:** Added multi-arch Docker image build and compose support for  [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/dev/debug/spotify_monitor_secret_grabber.py) - more info at [🐳 Secret Key Extraction via Docker](https://github.com/misiektoja/spotify_monitor#-secret-key-extraction-via-docker-recommended-easiest-way)
- **IMPROVE:** Added deletion of flag_file at launch if specified via .conf file. Previously only done when flag_file was specified on command line
- **IMPROVE:** Added info to console output when TOTP secrets are fetched from a remote URL or local file

**Bug fixes**:

- **BUGFIX:** Removed walrus operator to support min python version 3.6 (thanks [@tomballgithub](https://github.com/tomballgithub), fixes [#20](https://github.com/misiektoja/spotify_monitor/issues/20))

# Changes in 2.4 (14 Jul 2025)

**Features and Improvements**:

- **IMPROVE:** Added automatic fetching of secrets used by web-player access token endpoint (`cookie` mode) while generating TOTP; it avoids manual updates since Spotify started rotating them every two days

**Bug fixes**:

- **BUGFIX:** Fixed bugs in retry logic and error handling in spotify_get_access_token_from_sp_dc()

# Changes in 2.3.1 (10 Jul 2025)

**Features and Improvements**:

- **IMPROVE:** Updated secret cipher bytes used by web-player access token endpoint (`cookie` mode) to v11 & v12
- **IMPROVE:** Moved secret cipher bytes for web-player endpoint to configuration section
- **IMPROVE:** Implemented auto-selection of highest cipher version when `TOTP_VER` is set to 0
- **NEW:** Added tool to extract secret keys used for TOTP generation in Spotify Web Player JavaScript bundles (see [Debugging Tools](https://github.com/misiektoja/spotify_monitor#debugging-tools) for more info)

**Bug fixes**:

- **BUGFIX:** Fixed truncation code to handle emojis with an actual width greater than one character (thanks [@tomballgithub](https://github.com/tomballgithub))

# Changes in 2.3 (07 Jul 2025)

**Features and Improvements**:

- **NEW:** Added new config option (`FLAG_FILE`) and flag (`--flag-file`) to create a file when the user is active and delete it when inactive; useful for external tools to detect streaming status (thanks [@tomballgithub](https://github.com/tomballgithub))
- **NEW:** Added new config option (`TRUNCATE_CHARS`) and flag (`--truncate`) to limit screen line length; set to 999 to auto-detect terminal width (thanks [@tomballgithub](https://github.com/tomballgithub))
- **IMPROVE:** Updated secret cipher bytes used by web-player access token endpoint (`cookie` mode) to v9 & v10 (thanks [@Thereallo1026](https://github.com/Thereallo1026) for reverse engineering the current secrets)
- **IMPROVE:** Added number of songs played and elapsed time to session events (thanks [@tomballgithub](https://github.com/tomballgithub))

**Bug fixes**:

- **BUGFIX:** Fixed missing asterisk on startup screen (thanks [@tomballgithub](https://github.com/tomballgithub))

# Changes in 2.2.1 (02 Jul 2025)

**Bug fixes**:

- **BUGFIX:** Fixed web-player access token retrieval via sp_dc cookie by updating secret cipher bytes (thanks [@WurdahMekanik](https://github.com/WurdahMekanik) and [@matthewcamilizer](https://github.com/matthewcamilizer), fixes [#11](https://github.com/misiektoja/spotify_monitor/issues/11))
- **BUGFIX:** Delayed removal/reappearance alerts; see new REMOVED_DISAPPEARED_COUNTER config option (fixes [#10](https://github.com/misiektoja/spotify_monitor/issues/10))
- **BUGFIX:** Fixed missing email alerts for failed token requests when using sp_dc cookie method

# Changes in 2.2 (18 Jun 2025)

**Features and Improvements**:

- **NEW:** Added new config option (`USER_AGENT`) and flag (`--user-agent`) to set Spotify user agent string
- **NEW:** Ensured all Spotify requests now include the appropriate user agent, if not specified - it is randomly generated per session for specific type of token source
- **IMPROVE:** Improved detection when a Spotify user has been removed
- **IMPROVE:** HTTPAdapter now honors the Retry-After header on 429 responses for better Spotify API rate limit handling
- **IMPROVE:** Updated captions shown for Apple and YouTube Music links
- **IMPROVE:** Added more descriptive error messages and covered additional corner cases
- **IMPROVE:** Suppressed -z / --clienttoken-request-body-file from help output to reduce confusion (flag remains functional, but hidden)
- **IMPROVE:** Clarifications in inline comments explaining how to configure Spotify Desktop client method

**Bug fixes**:

- **BUGFIX:** Fixed issue with incorrectly reported songs played on loop

# Changes in 2.1.2 (10 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Fixed web-player access token retrieval via sp_dc cookie (fixes [#8](https://github.com/misiektoja/spotify_monitor/issues/8))

# Changes in 2.1.1 (10 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Ensured all Spotify requests include the custom User-Agent header
- **BUGFIX:** Fixed config file generation to work reliably on Windows systems

# Changes in 2.1 (09 Jun 2025)

**Features and Improvements**:

- **NEW:** Added support for a new method to obtain the Spotify access token. This method uses captured credentials from the Spotify desktop client and a Protobuf-based login flow. It is intended for advanced users who want an indefinitely valid token with the widest scope. Check the [Spotify Desktop Client](https://github.com/misiektoja/spotify_monitor/blob/main/README.md#spotify-desktop-client) for more info.

# Changes in 2.0 (21 May 2025)

**Features and Improvements**:

- **NEW:** The tool can now be installed via pip: `pip install spotify_monitor`
- **NEW:** Added support for external config files, environment-based secrets and dotenv integration with auto-discovery
- **NEW:** Display access token owner information and Spotify friend profile URLs
- **IMPROVE:** Enhanced startup summary to show loaded config, dotenv and monitored tracks file paths
- **IMPROVE:** Simplified and renamed command-line arguments for improved usability
- **NEW:** Implemented SIGHUP handler for dynamic reload of secrets from dotenv files
- **NEW:** Added configuration option to control clearing the terminal screen at startup
- **IMPROVE:** Changed connectivity check to use Spotify API endpoint for reliability
- **IMPROVE:** Added check for missing pip dependencies with install guidance
- **IMPROVE:** Allow disabling liveness check by setting interval to 0 (default changed to 12h)
- **IMPROVE:** Improved handling of log file creation
- **IMPROVE:** Refactored CSV file initialization and processing
- **NEW:** Added support for `~` path expansion across all file paths
- **IMPROVE:** Refactored code structure to support packaging for PyPI
- **IMPROVE:** Enforced configuration option precedence: code defaults < config file < env vars < CLI flags
- **IMPROVE:** Removed short option for `--send-test-email` to avoid ambiguity

**Bug fixes**:

- **BUGFIX:** Fixed edge cases while converting Spotify URIs to URLs

# Changes in 1.9 (07 Apr 2025)

**Features and Improvements**:

- **IMPROVE:** Improved 'track songs' file parsing: now supports comments (lines starting with #) and ignores empty lines
- **IMPROVE:** Refactored comparison logic for file-listed vs. user-played song tracks
- **IMPROVE:** Replaced repeated requests.get calls with a shared SESSION to reuse HTTP connections and improve performance
- **IMPROVE:** Add retry-enabled HTTPAdapter to global SESSION
- **IMPROVE:** Display number of friends sharing listening activity (when using -l parameter)
- **IMPROVE:** Updated horizontal line for improved output aesthetics

**Bug fixes**:

- **BUGFIX:** Fixed issue handling 'track songs' files encoded in Windows-1252/CP1252 (fixes [#5](https://github.com/misiektoja/spotify_monitor/issues/5))

# Changes in 1.8.1 (25 Mar 2025)

**Bug fixes**:

- **BUGFIX:** Fixes occasional None return from get_random_user_agent(), avoiding downstream NoneType error (fixes [#4](https://github.com/misiektoja/spotify_monitor/issues/4))

# Changes in 1.8 (20 Mar 2025)

**Features and Improvements**:

- **NEW:** Added support for TOTP parameters in Spotify Web Player token endpoint, the tool now requires the pyotp pip module (fixes [#1](https://github.com/misiektoja/spotify_monitor/issues/1), [#2](https://github.com/misiektoja/spotify_monitor/issues/2))
- **NEW:** Caching mechanism to avoid unnecessary token refreshes
- **NEW:** Added the possibility to disable SSL certificate verification (VERIFY_SSL global variable)
- **IMPROVE:** Email notification flags are now automatically disabled if the SMTP configuration is invalid
- **IMPROVE:** Better exception handling in network-related functions
- **IMPROVE:** Better overall error handling
- **IMPROVE:** Code cleanup & linting fixes

# Changes in 1.7 (03 Nov 2024)

**Features and Improvements**:

- **NEW:** Support for YouTube Music search URLs

# Changes in 1.6 (15 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new parameter (**-z** / **--send_test_email_notification**) which allows to send test email notification to verify SMTP settings defined in the script
- **IMPROVE:** Possibility to define email sending timeout (default set to 15 secs)

**Bug fixes**:

- **BUGFIX:** Fixed "SyntaxError: f-string: unmatched (" issue in older Python versions
- **BUGFIX:** Fixed "SyntaxError: f-string expression part cannot include a backslash" issue in older Python versions

# Changes in 1.5 (07 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new signal handler for SIGPIPE allowing to switch songs on loop email notifications
- **IMPROVE:** Better way of checking for error strings (without case sensitivity) + some additional ones added to the list
- **NEW:** Support for float type of timestamps added in date/time related functions + get_short_date_from_ts() rewritten to display year if show_year == True and current year is different, also can omit displaying hour and minutes if show_hours == False

**Bug fixes**:

- **BUGFIX:** Escaping of exception error string fixed + some unbound vars corrected

# Changes in 1.4 (24 May 2024)

**Features and Improvements**:

- **NEW:** Possibility to define output log file name suffix (**-y** / **--log_file_suffix**)
- **NEW:** Feature allowing to suppress repeating API or network related errors (check **ERROR_500_NUMBER_LIMIT**, **ERROR_500_TIME_LIMIT**, **ERROR_NETWORK_ISSUES_NUMBER_LIMIT** and **ERROR_NETWORK_ISSUES_TIME_LIMIT** variables)
- **IMPROVE:** Information about log file name visible in the start screen
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime

**Bug fixes**:

- **BUGFIX:** Fixed issues with sporadic broken links in HTML emails (vars with special characters are now escaped properly)

# Changes in 1.3 (18 May 2024)

**Features and Improvements**:

- **NEW:** Full support for real-time playing of tracked songs (**-g**) in Spotify client in **Linux**
- **NEW:** Rewritten code for playing tracked songs (**-g**) in Spotify client in **macOS**
- **NEW:** New way of playing tracked songs (**-g**) in Spotify client in **Windows**
- **IMPROVE:** Improvements for running the code in Python under Windows
- **IMPROVE:** Better checking for wrong command line arguments
- **IMPROVE:** pep8 style convention corrections

**Bug fixes**:

- **BUGFIX:** Improved exception handling for some functions

# Changes in 1.2 (07 May 2024)

**Features and Improvements**:

- **NEW:** Possibility to define SP_DC_COOKIE via command line argument (-u / --spotify_dc_cookie)
- **IMPROVE:** SPOTIFY_ACTIVITY_CHECK and -p / --online_timer parameter have been removed as it only complicated the code with no visible benefit; SPOTIFY_INACTIVITY_CHECK is used in all places now, so user is considered active if the time of last activity is <= SPOTIFY_INACTIVITY_CHECK
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings
- **IMPROVE:** Strings have been converted to f-strings for better code visibility
- **IMPROVE:** Info about CSV file name in the start screen

# Changes in 1.1 (30 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for detection of songs listened on loop; if user plays the same song consecutively SONG_ON_LOOP_VALUE times (3 by default, configurable in the .py file) then there will be proper message on the console + you can get email notification (new -x / --song_on_loop_notification parameter); the alarm is triggered only once, when the SONG_ON_LOOP_VALUE is reached and once the user changes the song the timer is zeroed
- **NEW:** Feature to detect skipped songs; if the user plays the song for <= SKIPPED_SONG_THRESHOLD (0.6 by default = 60%, configurable in the .py file) of track duration, then the song is treated as skipped with proper message on the console & email notifications
- **NEW:** Information about number of listened songs in the session (console + notification emails)
- **IMPROVE:** Adding info about Artist and Album context of listened songs to notification emails
- **IMPROVE:** Adding info about Artist and Album context URLs in the console & email notifications
- **IMPROVE:** Information about readjusting session start due to too low inactivity timer is also in the notification email now

# Changes in 1.0 (23 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for detecting Artist context of listened songs
- **IMPROVE:** Additional search/replace strings to sanitize tracks for Genius URLs

**Bug fixes**:

- **BUGFIX:** Fix for "SyntaxWarning: invalid escape sequence '\d'" in regexps
