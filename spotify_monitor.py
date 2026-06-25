#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v3.0

Tool implementing real-time tracking of Spotify friends music activity:
https://github.com/misiektoja/spotify_monitor/

Python pip3 requirements:

requests
python-dateutil
urllib3
pyotp (needed for web-player token generation)
python-dotenv (optional)
wcwidth (optional, needed by TRUNCATE_CHARS feature)
spotipy (optional, used when legacy OAuth app credentials are configured)
pycookiecheat (optional, used for Chrome, Brave and Chromium cookie import)
"""

VERSION = "3.0"

PROJECT_URL = "https://github.com/misiektoja/spotify_monitor"
QUICK_START_GUIDE_URL = PROJECT_URL + "#quick-start"
INSTALLATION_GUIDE_URL = PROJECT_URL + "#installation"
CONFIG_GUIDE_URL = PROJECT_URL + "#configuration"
COOKIE_GUIDE_URL = PROJECT_URL + "#spotify-sp_dc-cookie"
CLIENT_GUIDE_URL = PROJECT_URL + "#spotify-desktop-client"
TARGET_GUIDE_URL = PROJECT_URL + "#how-to-get-a-friends-user-uri-id"
FOLLOWING_GUIDE_URL = PROJECT_URL + "#following-the-monitored-user"
SMTP_GUIDE_URL = PROJECT_URL + "#smtp-settings"
WEBHOOK_GUIDE_URL = PROJECT_URL + "#discord-webhook-notifications"
SECRETS_GUIDE_URL = PROJECT_URL + "#storing-secrets"
INTERVALS_GUIDE_URL = PROJECT_URL + "#check-intervals"
DOCTOR_GUIDE_URL = PROJECT_URL + "#doctor-preflight"
OAUTH_GUIDE_URL = PROJECT_URL + "#spotify-oauth-app"
SPOTIFY_WEB_LOGIN_URL = "https://open.spotify.com/"
COOKIE_IMPORT_FIX = f"Open {SPOTIFY_WEB_LOGIN_URL} in Firefox. Sign in to the Spotify account used for monitoring then run: spotify_monitor --import-browser-cookie --browser firefox"
CONTAINER_PLAYBACK_WARNING = "Host Spotify auto-play is unavailable by default inside the container because the container cannot control the Spotify client running on the host. Run Spotify Monitor locally if you need TRACK_SONGS or --track-in-spotify."

STARTUP_BANNER = r""" .---------------.    ____              _   _  __
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

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
# Select the method used to obtain the Spotify access token
# Available options:
#   cookie - uses the sp_dc cookie to retrieve a token via the Spotify web endpoint (recommended)
#   client - uses captured credentials from the Spotify desktop client and a Protobuf-based login flow (for advanced users)
TOKEN_SOURCE = "cookie"

# Spotify user to monitor by raw ID, Spotify user URI or Spotify profile URL
# A positional command-line target overrides this value
TARGET_USER_URI_ID = ""

# Token refresh settings used by cookie mode and the anonymous metadata backend
# (to configure the alternative 'client' method, see the section at the end of this config block)
#
# - Log in to Spotify web client (https://open.spotify.com/) and retrieve your sp_dc cookie
#   (use your web browser's dev console or "Cookie-Editor" by cgagnier to extract it easily: https://cookie-editor.com/)
# - Provide the SP_DC_COOKIE secret using one of the following methods:
#   - Pass it at runtime with -u / --spotify-dc-cookie
#   - Set it as an environment variable (e.g. export SP_DC_COOKIE=...)
#   - Add it to ".env" file (SP_DC_COOKIE=...) for persistent use
#   - Fallback: hard-code it in the code or config file
SP_DC_COOKIE = "your_sp_dc_cookie_value"

# ---------------------------------------------------------------------

# The optional section below enables the legacy Web API path for track and playlist metadata
# Restricted apps fall back automatically to the anonymous Spotify web-player backend
#
# To obtain the credentials:
#   - Log in to Spotify Developer dashboard: https://developer.spotify.com/dashboard
#   - Create a new app
#   - For 'Redirect URL', use: http://127.0.0.1:1234
#   - Select 'Web API' as the intended API
#   - Copy the 'Client ID' and 'Client Secret'
#
# Provide the SP_APP_CLIENT_ID and SP_APP_CLIENT_SECRET secrets using one of the following methods:
#   - Pass it at runtime with -r / --oauth-app-creds (use SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET format - note the colon separator)
#   - Set it as an environment variable (e.g. export SP_APP_CLIENT_ID=...; export SP_APP_CLIENT_SECRET=...)
#   - Add it to ".env" file (SP_APP_CLIENT_ID=... and SP_APP_CLIENT_SECRET=...) for persistent use
#   - Fallback: hard-code it in the code or config file
#
# The tool automatically refreshes the access token, so it remains valid indefinitely
SP_APP_CLIENT_ID = "your_spotify_app_client_id"
SP_APP_CLIENT_SECRET = "your_spotify_app_client_secret"

# Path to cache file used to store OAuth app access tokens across tool restarts
# Set to empty to use in-memory cache only
SP_APP_TOKENS_FILE = ".spotify-monitor-oauth-app.json"

# ---------------------------------------------------------------------

# SMTP settings for sending email notifications
# If left as-is, no notifications will be sent
#
# Provide the SMTP_PASSWORD secret using one of the following methods:
#   - Set it as an environment variable (e.g. export SMTP_PASSWORD=...)
#   - Add it to ".env" file (SMTP_PASSWORD=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# Whether to send an email when user becomes active
# Can also be enabled via the -a flag
ACTIVE_NOTIFICATION = False

# Whether to send an email when user goes inactive
# Can also be enabled via the -i flag
INACTIVE_NOTIFICATION = False

# Whether to send an email when a monitored track/playlist/album plays
# Can also be enabled via the -t flag
TRACK_NOTIFICATION = False

# Whether to send an email on every song change
# Can also be enabled via the -j flag
SONG_NOTIFICATION = False

# Whether to send an email when user plays a song on loop
# Triggered if the same song is played more than SONG_ON_LOOP_VALUE times
# Can also be enabled via the -x flag
SONG_ON_LOOP_NOTIFICATION = False

# Whether to send an email on errors
# Can also be disabled via the -e flag
ERROR_NOTIFICATION = True

# ---------------------------------------------------------------------

# Discord-compatible webhook settings
# Store WEBHOOK_URL in an environment variable or dotenv file because the URL contains a secret token
WEBHOOK_ENABLED = False
WEBHOOK_URL = "your_discord_webhook_url"
WEBHOOK_USERNAME = "Spotify Monitor"

# Whether to send a webhook when the user becomes active
WEBHOOK_ACTIVE_NOTIFICATION = False

# Whether to send a webhook when the user goes inactive
WEBHOOK_INACTIVE_NOTIFICATION = False

# Whether to send a webhook when a monitored track, playlist or album plays
WEBHOOK_TRACK_NOTIFICATION = False

# Whether to send a webhook on every song change
WEBHOOK_SONG_NOTIFICATION = False

# Whether to send a webhook when the user plays a song on loop
WEBHOOK_SONG_ON_LOOP_NOTIFICATION = False

# Whether to send a webhook on monitoring errors
WEBHOOK_ERROR_NOTIFICATION = True

# How often to check for user activity; in seconds
# Can also be set using the -c flag
SPOTIFY_CHECK_INTERVAL = 30  # 30 seconds

# Time to wait before retrying after an error; in seconds
SPOTIFY_ERROR_INTERVAL = 180  # 3 mins

# Time after which a user is considered inactive (based on last activity); in seconds
# Can also be set using the -o flag
# Note: If the user listens to songs longer than this value, they may be marked as inactive
SPOTIFY_INACTIVITY_CHECK = 660  # 11 mins

# How many recently listened songs to display in the inactive notification email
# Set to 0 to disable the recently listened songs list
INACTIVE_EMAIL_RECENT_SONGS_COUNT = 5

# Tolerance in seconds for "Played for" display when comparing actual playback time to track duration
# If the difference is within +-PLAYED_FOR_DURATION_TOLERANCE seconds, "Played for" is suppressed
# (treats as if song was played for its full duration to account for timestamp jitter)
PLAYED_FOR_DURATION_TOLERANCE = 1

# Whether to detect and annotate crossfaded songs (songs played with transition timing)
# When enabled, songs played within the crossfade detection thresholds will be marked as
# "(X% - crossfade enabled)" to indicate that the song likely ended early due to crossfade transitions
DETECT_CROSSFADED_SONGS = True

# Thresholds for crossfade detection (as percentage of track duration)
# Songs played between CROSSFADE_DETECTION_MIN and CROSSFADE_DETECTION_MAX will be annotated
# as crossfaded if DETECT_CROSSFADED_SONGS is enabled
CROSSFADE_DETECTION_MIN = 0.96  # 96% - minimum percentage to consider crossfade
CROSSFADE_DETECTION_MAX = 0.99  # 99% - maximum percentage to consider crossfade

# Interval for checking if a user who disappeared from the list of recently active friends has reappeared; in seconds
# Can happen due to:
#   - unfollowing the user
#   - Spotify service issues
#   - private session bugs
#   - user inactivity for over a week
# In such a case, the tool will continuously check for the user's reappearance using the time interval specified below
# Can also be set using the -m flag
SPOTIFY_DISAPPEARED_CHECK_INTERVAL = 180  # 3 mins

# Whether to auto-play each listened song in your Spotify client
# Host Spotify auto-play is unavailable by default inside Docker and Docker Compose containers
# Can also be set using the -g flag
TRACK_SONGS = False

# Method used to play the song listened by the tracked user in local Spotify client under macOS
# (i.e. when TRACK_SONGS / -g functionality is enabled)
# Methods:
#       "apple-script" (recommended)
#       "trigger-url"
SPOTIFY_MACOS_PLAYING_METHOD = "apple-script"

# Method used to play the song listened by the tracked user in local Spotify client under Linux OS
# (i.e. when TRACK_SONGS / -g functionality is enabled)
# Methods:
#       "dbus-send" (most common one)
#       "qdbus"
#       "trigger-url"
SPOTIFY_LINUX_PLAYING_METHOD = "dbus-send"

# Method used to play the song listened by the tracked user in local Spotify client under Windows OS
# (if TRACK_SONGS / -g functionality is enabled)
# Methods:
#       "start-uri" (recommended)
#       "spotify-cmd"
#       "trigger-url"
SPOTIFY_WINDOWS_PLAYING_METHOD = "start-uri"

# Number of consecutive plays of the same song considered to be on loop
SONG_ON_LOOP_VALUE = 3

# Threshold for considering a song as skipped (fraction of duration)
SKIPPED_SONG_THRESHOLD = 0.55  # song is treated as skipped if played for <= 55% of its total length

# Spotify track ID to play when the user goes offline (used when TRACK_SONGS / -g functionality is enabled)
# Leave empty to simply pause
# SP_USER_GOT_OFFLINE_TRACK_ID = "5wCjNjnugSUqGDBrmQhn0e"
SP_USER_GOT_OFFLINE_TRACK_ID = ""

# Delay before pausing the above track after the user goes offline; in seconds
# Set to 0 to keep playing indefinitely until manually paused
SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE = 5  # 5 seconds

# Occasionally, the Spotify API glitches and reports that the user has disappeared from the list of friends
# To avoid false alarms, we delay alerts until this happens REMOVED_DISAPPEARED_COUNTER times in a row
REMOVED_DISAPPEARED_COUNTER = 4

# Optional: specify user agent manually
#
# When the token source is 'cookie' - set it to web browser user agent, some examples:
# Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0
# Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:139.0) Gecko/20100101 Firefox/139.0
#
# When the token source is 'client' - set it to Spotify desktop client user agent, some examples:
# Spotify/126200580 Win32_x86_64/0 (PC desktop)
# Spotify/126400408 OSX_ARM64/OS X 15.5.0 [arm 2]
#
# Leave empty to auto-generate it randomly for specific token source
USER_AGENT = ""

# How often to print a "liveness check" message to the output; in seconds
# Set to 0 to disable
LIVENESS_CHECK_INTERVAL = 43200  # 12 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://api.spotify.com/v1'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# Whether to enable / disable SSL certificate verification while sending https requests
VERIFY_SSL = True

# Threshold for displaying Spotify 50x errors - it is to suppress sporadic issues with Spotify API endpoint
# Adjust the values according to the SPOTIFY_CHECK_INTERVAL timer
# If more than 6 Spotify API related errors in 4 minutes, show an alert
ERROR_500_NUMBER_LIMIT = 6
ERROR_500_TIME_LIMIT = 240  # 4 min

# Threshold for displaying network errors - it is to suppress sporadic issues with internet connectivity
# Adjust the values according to the SPOTIFY_CHECK_INTERVAL timer
# If more than 6 network related errors in 4 minutes, show an alert
ERROR_NETWORK_ISSUES_NUMBER_LIMIT = 6
ERROR_NETWORK_ISSUES_TIME_LIMIT = 240  # 4 min

# CSV file to write every listened track
# Can also be set using the -b flag
CSV_FILE = ""

# Filename with Spotify tracks/playlists/albums to alert on
# Can also be set using the -s flag
MONITOR_LIST_FILE = ""

# Location of the optional dotenv file which can keep secrets
# If not specified it will try to auto-search for .env files
# To disable auto-search, set this to the literal string "none"
# Can also be set using the --env-file flag
DOTENV_FILE = ""

# Suffix to append to the output filenames instead of default user URI ID
# Can also be set using the -y flag
FILE_SUFFIX = ""

# Base name for the log file. Output will be saved to spotify_monitor_<user_uri_id/file_suffix>.log
# Can include a directory path to specify the location, e.g. ~/some_dir/spotify_monitor
SP_LOGFILE = "spotify_monitor"

# Whether to disable logging to spotify_monitor_<user_uri_id/file_suffix>.log
# Can also be disabled via the -d flag
DISABLE_LOGGING = False

# Enable debug mode for technical logging (can also be enabled via --debug flag)
# Shows request flow, selected params and internal state changes (with sensitive values redacted)
DEBUG_MODE = False

# Enable verbose operational events and the complete startup summary
# Shows rare state changes and recoveries without per-poll or debug HTTP noise
VERBOSE_MODE = False

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Path to a file that is created when the user is active and deleted when inactive
# Useful for external tools to detect streaming status
# Can also be set via the --flag-file flag
FLAG_FILE = ""

# Max characters per line when printing to screen to avoid line wrapping
# Does not affect log file output
# Set to 999 to auto-detect terminal width
# Applies only when DISABLE_LOGGING is False
# Can also be set via the --truncate flag
TRUNCATE_CHARS = 0

# Value added/subtracted via signal handlers to adjust inactivity timeout (SPOTIFY_INACTIVITY_CHECK); in seconds
SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# Whether to show Apple Music URL in console and emails
ENABLE_APPLE_MUSIC_URL = True

# Whether to show YouTube Music URL in console and emails
ENABLE_YOUTUBE_MUSIC_URL = True

# Whether to show Amazon Music URL in console and emails
ENABLE_AMAZON_MUSIC_URL = False

# Whether to show Deezer URL in console and emails
ENABLE_DEEZER_URL = False

# Whether to show Tidal URL in console and emails
# Note: Tidal requires users to be logged in to their account in the web browser to use the search functionality
ENABLE_TIDAL_URL = False

# Whether to show Genius lyrics URL in console and emails
ENABLE_GENIUS_LYRICS_URL = True

# Whether to show AZLyrics URL in console and emails
ENABLE_AZLYRICS_URL = False

# Whether to show Tekstowo.pl lyrics URL in console and emails
ENABLE_TEKSTOWO_URL = False

# Whether to show Musixmatch lyrics URL in console and emails
# Note: Musixmatch requires users to be logged in to their account in the web browser to use the search functionality
ENABLE_MUSIXMATCH_URL = False

# Whether to show Lyrics.com lyrics URL in console and emails
ENABLE_LYRICS_COM_URL = False

# String to add after playlist name to indicate it's a Spotify public curated and customized playlist
# The distinction may be important because the songs will vary by account due to listening habits.
# This will be used for messages on console and emails
# The string should include all desired characters, including a preceding space and parenthesis, if desired
#
# Example:
#   For: 90s Pop (by Spotify), SPOTIFY_SUFFIX = " (by Spotify)"
#
# Leave empty to disable
SPOTIFY_SUFFIX = ""

# ---------------------------------------------------------------------

# The section below is used when the token source is set to 'cookie'

# Maximum number of attempts to get a valid access token in a single run of the spotify_get_access_token_from_sp_dc() function
TOKEN_MAX_RETRIES = 3

# Interval between access token retry attempts; in seconds
TOKEN_RETRY_TIMEOUT = 0.5  # 0.5 second

# ---------------------------------------------------------------------

# The section below is used when the token source is set to 'client'
#
# - Run an intercepting proxy of your choice (like Proxyman)
# - Launch the Spotify desktop client and look for requests to: https://login{n}.spotify.com/v3/login
#   (the 'login' part is suffixed with one or more digits)
# - Export the login request body (a binary Protobuf payload) to a file
#   (e.g. in Proxyman: right click the request -> Export -> Request Body -> Save File -> <login-request-body-file>)
#
# To automatically extract DEVICE_ID, SYSTEM_ID, USER_URI_ID and REFRESH_TOKEN from the exported binary login
# request Protobuf file:
#
# - Run the tool with the -w flag to indicate an exported file or specify its file name below
LOGIN_REQUEST_BODY_FILE = ""

# Alternatively, you can manually set the DEVICE_ID, SYSTEM_ID, USER_URI_ID and REFRESH_TOKEN options
# (however, using the automated method described above is recommended)
#
# These values can be extracted using one of the following methods:
#
# - Run spotify_profile_monitor with the -w flag without specifying SPOTIFY_USER_URI_ID - it will decode the file and
#   print the values to stdout, example:
#       spotify_profile_monitor --token-source client -w <path-to-login-request-body-file>
#
# - Use the protoc tool (part of protobuf pip package):
#       pip install protobuf
#       protoc --decode_raw < <path-to-login-request-body-file>
#
# - Use the built-in Protobuf decoder in your intercepting proxy (if supported)
#
# The Protobuf structure is as follows:
#
#    {
#      1: {
#           1: "DEVICE_ID",
#           2: "SYSTEM_ID"
#         },
#      100: {
#           1: "USER_URI_ID",
#           2: "REFRESH_TOKEN"
#         }
#    }
#
# Provide the extracted values below (DEVICE_ID, SYSTEM_ID, USER_URI_ID). The REFRESH_TOKEN secret can be
# supplied using one of the following methods:
#   - Set it as an environment variable (e.g. export REFRESH_TOKEN=...)
#   - Add it to ".env" file (REFRESH_TOKEN=...) for persistent use
#   - Fallback: hard-code it in the code or config file
DEVICE_ID = "your_spotify_app_device_id"
SYSTEM_ID = "your_spotify_app_system_id"
USER_URI_ID = "your_spotify_user_uri_id"
REFRESH_TOKEN = "your_spotify_app_refresh_token"

# ----------------------------------------------
# Advanced options for 'client' token source
# Modifying the values below is NOT recommended!
# ----------------------------------------------

# Spotify login URL
LOGIN_URL = "https://login5.spotify.com/v3/login"

# Spotify client token URL
CLIENTTOKEN_URL = "https://clienttoken.spotify.com/v1/clienttoken"

# Platform-specific values for token generation so the Spotify client token requests match your exact Spotify desktop
# client build (arch, OS build, app version etc.)
#
# - Run an intercepting proxy of your choice (like Proxyman)
# - Launch the Spotify desktop client and look for requests to: https://clienttoken.spotify.com/v1/clienttoken
#   (these requests are sent every time client token expires, usually every 2 weeks)
# - Export the client token request body (a binary Protobuf payload) to a file
#   (e.g. in Proxyman: right click the request -> Export -> Request Body -> Save File -> <clienttoken-request-body-file>)
#
# To automatically extract APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR and CLIENT_MODEL from the
# exported binary client token request Protobuf file:
#
# - Run the tool with the hidden -z flag to indicate an exported file or specify its file name below
CLIENTTOKEN_REQUEST_BODY_FILE = ""

# Alternatively, you can manually set the APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR and
# CLIENT_MODEL options
#
# These values can be extracted using one of the following methods:
#
# - run spotify_profile_monitor with the hidden -z flag without specifying SPOTIFY_USER_URI_ID - it will decode the file
#   and print the values to stdout, example:
#       spotify_profile_monitor --token-source client -z <path-to-clienttoken-request-body-file>
#
# - use the protoc tool (part of protobuf pip package):
#       pip install protobuf
#       protoc --decode_raw < <path-to-clienttoken-request-body-file>
#
# - use the built-in Protobuf decoder in your intercepting proxy (if supported)
#
# The Protobuf structure is as follows:
#
# 1: 1
# 2 {
#   1: "APP_VERSION"
#   2: "DEVICE_ID"
#   3 {
#     1 {
#       4 {
#         1: "CPU_ARCH"
#         3: "OS_BUILD"
#         4: "PLATFORM"
#         5: "OS_MAJOR"
#         6: "OS_MINOR"
#         8: "CLIENT_MODEL"
#       }
#     }
#     2: "SYSTEM_ID"
#   }
# }
#
# Provide the extracted values below (except for DEVICE_ID and SYSTEM_ID as it was already provided via -w)
CPU_ARCH = 10
OS_BUILD = 19045
PLATFORM = 2
OS_MAJOR = 9
OS_MINOR = 9
CLIENT_MODEL = 34404

# App version (e.g. '1.2.62.580.g7e3d9a4f')
# Leave empty to auto-generate from USER_AGENT
APP_VERSION = ""

# ---------------------------------------------------------------------
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default dummy values so linters shut up
# Do not change values below - modify them in the configuration section or config file instead
TOKEN_SOURCE = ""
TARGET_USER_URI_ID = ""
SP_DC_COOKIE = ""
SP_APP_CLIENT_ID = ""
SP_APP_CLIENT_SECRET = ""
SP_APP_TOKENS_FILE = ""
LOGIN_REQUEST_BODY_FILE = ""
CLIENTTOKEN_REQUEST_BODY_FILE = ""
LOGIN_URL = ""
DEVICE_ID = ""
SYSTEM_ID = ""
USER_URI_ID = ""
REFRESH_TOKEN = ""
CLIENTTOKEN_URL = ""
APP_VERSION = ""
CPU_ARCH = 0
OS_BUILD = 0
PLATFORM = 0
OS_MAJOR = 0
OS_MINOR = 0
CLIENT_MODEL = 0
SMTP_HOST = ""
SMTP_PORT = 0
SMTP_USER = ""
SMTP_PASSWORD = ""
SMTP_SSL = False
SENDER_EMAIL = ""
RECEIVER_EMAIL = ""
ACTIVE_NOTIFICATION = False
INACTIVE_NOTIFICATION = False
TRACK_NOTIFICATION = False
SONG_NOTIFICATION = False
SONG_ON_LOOP_NOTIFICATION = False
ERROR_NOTIFICATION = False
WEBHOOK_ENABLED = False
WEBHOOK_URL = ""
WEBHOOK_USERNAME = ""
WEBHOOK_ACTIVE_NOTIFICATION = False
WEBHOOK_INACTIVE_NOTIFICATION = False
WEBHOOK_TRACK_NOTIFICATION = False
WEBHOOK_SONG_NOTIFICATION = False
WEBHOOK_SONG_ON_LOOP_NOTIFICATION = False
WEBHOOK_ERROR_NOTIFICATION = False
SPOTIFY_CHECK_INTERVAL = 0
SPOTIFY_ERROR_INTERVAL = 0
SPOTIFY_INACTIVITY_CHECK = 0
INACTIVE_EMAIL_RECENT_SONGS_COUNT = 0
PLAYED_FOR_DURATION_TOLERANCE = 0
DETECT_CROSSFADED_SONGS = False
CROSSFADE_DETECTION_MIN = 0.0
CROSSFADE_DETECTION_MAX = 0.0
SPOTIFY_DISAPPEARED_CHECK_INTERVAL = 0
TRACK_SONGS = False
SPOTIFY_MACOS_PLAYING_METHOD = ""
SPOTIFY_LINUX_PLAYING_METHOD = ""
SPOTIFY_WINDOWS_PLAYING_METHOD = ""
SONG_ON_LOOP_VALUE = 0
SKIPPED_SONG_THRESHOLD = 0
SP_USER_GOT_OFFLINE_TRACK_ID = ""
SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE = 0
REMOVED_DISAPPEARED_COUNTER = 0
USER_AGENT = ""
LIVENESS_CHECK_INTERVAL = 0
CHECK_INTERNET_URL = ""
CHECK_INTERNET_TIMEOUT = 0
VERIFY_SSL = False
ERROR_500_NUMBER_LIMIT = 0
ERROR_500_TIME_LIMIT = 0
ERROR_NETWORK_ISSUES_NUMBER_LIMIT = 0
ERROR_NETWORK_ISSUES_TIME_LIMIT = 0
CSV_FILE = ""
MONITOR_LIST_FILE = ""
DOTENV_FILE = ""
FILE_SUFFIX = ""
SP_LOGFILE = ""
DISABLE_LOGGING = False
DEBUG_MODE = False
VERBOSE_MODE = False
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE = 0
ENABLE_GENIUS_LYRICS_URL = False
ENABLE_AZLYRICS_URL = False
ENABLE_TEKSTOWO_URL = False
ENABLE_MUSIXMATCH_URL = False
ENABLE_LYRICS_COM_URL = False
ENABLE_APPLE_MUSIC_URL = False
ENABLE_YOUTUBE_MUSIC_URL = False
ENABLE_AMAZON_MUSIC_URL = False
ENABLE_DEEZER_URL = False
ENABLE_TIDAL_URL = False
TOKEN_MAX_RETRIES = 0
TOKEN_RETRY_TIMEOUT = 0.0
FLAG_FILE = ""
TRUNCATE_CHARS = 0
SPOTIFY_SUFFIX = ""

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "spotify_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("REFRESH_TOKEN", "SP_DC_COOKIE", "SMTP_PASSWORD", "SP_APP_CLIENT_ID", "SP_APP_CLIENT_SECRET", "WEBHOOK_URL")

# Strings removed from track names for generating proper Genius search URLs
re_search_str = r'remaster|extended|original mix|remix|original soundtrack|radio( |-)edit|\(feat\.|( \(.*version\))|( - .*version)'
re_replace_str = r'( - (\d*)( )*remaster$)|( - (\d*)( )*remastered( version)*( \d*)*.*$)|( \((\d*)( )*remaster\)$)|( - (\d+) - remaster$)|( - extended$)|( - extended mix$)|( - (.*); extended mix$)|( - extended version$)|( - (.*) remix$)|( - remix$)|( - remixed by .*$)|( - original mix$)|( - .*original soundtrack$)|( - .*radio( |-)edit$)|( \(feat\. .*\)$)|( \(\d+.*Remaster.*\)$)|( \(.*Version\))|( - .*version)'

# Default value for network-related timeouts in functions; in seconds
FUNCTION_TIMEOUT = 15

# Default value for alarm signal handler timeout; in seconds
ALARM_TIMEOUT = 15
ALARM_RETRY = 10

# Variables for caching functionality of the Spotify 'cookie' access token and 'client' refresh token to avoid unnecessary refreshing
SP_CACHED_ACCESS_TOKEN = None
SP_CACHED_REFRESH_TOKEN = None
SP_ACCESS_TOKEN_EXPIRES_AT = 0
SP_CACHED_CLIENT_ID = ""

# Separate cache for the optional OAuth app access token used by the legacy metadata path
SP_CACHED_OAUTH_APP_TOKEN = None

# Tracks whether Spotipy was loaded and whether its missing dependency warning was shown
SPOTIPY_AVAILABLE = None
SPOTIPY_IMPORT_WARNING_SHOWN = False

# Separate cache for the anonymous token used by the public web-player metadata backend
SP_CACHED_WEB_ACCESS_TOKEN = None
SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 0
SP_CACHED_WEB_CLIENT_ID = ""

# Caches dynamically discovered persisted-query hashes for public metadata
SP_CACHED_PLAYLIST_QUERY_HASH = ""
SP_CACHED_TRACK_QUERY_HASH = ""

# Switches each metadata type to the web backend after a restricted legacy response
SP_WEB_PLAYLIST_BACKEND_PREFERRED = False
SP_WEB_TRACK_BACKEND_PREFERRED = False

# URL of the Spotify Web Player endpoint to get access token
TOKEN_URL = "https://open.spotify.com/api/token"

# TOTP version and cipher bytes currently selected by the Spotify web player
TOTP_VERSION = 61
TOTP_SECRET_CIPHER_BYTES = (44, 55, 47, 42, 70, 40, 34, 114, 76, 74, 50, 111, 120, 97, 75, 76, 94, 102, 43, 69, 49, 120, 118, 80, 64, 78)

# URLs and user agent used by the public web-player metadata backend
WEB_PLAYER_URL = "https://open.spotify.com/"
WEB_PLAYER_QUERY_URL = "https://api-partner.spotify.com/pathfinder/v2/query"
WEB_PLAYER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"

# URL of the endpoint to get server time needed to create TOTP object
SERVER_TIME_URL = "https://open.spotify.com/"

# Variables for caching functionality of the Spotify client token to avoid unnecessary refreshing
SP_CACHED_CLIENT_TOKEN = None
SP_CLIENT_TOKEN_EXPIRES_AT = 0

LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / SPOTIFY_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Artist', 'Track', 'Playlist', 'Album', 'Last activity']

CLI_CONFIG_PATH = None

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"


import sys

if sys.version_info < (3, 9):
    print("* Error: Python version 3.9 or higher required !")
    sys.exit(1)

import importlib.util
import time
import string
import json
import os
import configparser
import sqlite3
from datetime import datetime, timedelta
from dateutil import relativedelta
import calendar
import requests as req
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import getpass
from urllib.parse import quote_plus, quote, unquote, urljoin, urlparse, urlsplit
import subprocess
import platform
import re
import ipaddress
from html import escape
import base64
import random
import shutil
import shlex
import tempfile
import socket
from dataclasses import dataclass, field
from pathlib import Path
import secrets
from typing import Any, Callable, List, Optional, Sequence, cast
from email.utils import parseaddr, parsedate_to_datetime

import urllib3
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SESSION = req.Session()
WEBHOOK_SESSION = req.Session()

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Cap server-provided Retry-After to avoid long blocking sleeps on 429 responses
MAX_RETRY_AFTER_SECONDS = 60

# Keep webhook delivery independent from Spotify API retries and long server timers
WEBHOOK_MAX_ATTEMPTS = 2
WEBHOOK_MAX_RETRY_AFTER_SECONDS = 5.0
WEBHOOK_FALLBACK_RETRY_SECONDS = 1.0
WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_EMBED_TITLE_LIMIT = 256
WEBHOOK_EMBED_DESCRIPTION_LIMIT = 4096

# Browsers supported by the sp_dc cookie importer
IMPORT_BROWSERS = ("firefox", "chrome", "brave", "chromium")
CHROMIUM_IMPORT_BROWSERS = ("chrome", "brave", "chromium")


# Returns whether Spotify Monitor is running in a Docker or Docker Compose container
def is_container_environment() -> bool:
    return os.path.exists("/.dockerenv") or bool(os.environ.get("SPOTIFY_MONITOR_DOCKER"))

# Chromium user-data directories
CHROMIUM_USER_DATA_DIRS = {
    "Darwin": {
        "chrome": "Library/Application Support/Google/Chrome",
        "brave": "Library/Application Support/BraveSoftware/Brave-Browser",
        "chromium": "Library/Application Support/Chromium",
    },
    "Linux": {
        "chrome": ".config/google-chrome",
        "brave": ".config/BraveSoftware/Brave-Browser",
        "chromium": ".config/chromium",
    },
}

# Error text shared by all rejected Spotify target forms
TARGET_INPUT_ERROR = "Invalid Spotify target. Use a raw user ID, spotify:user:USER_ID or https://open.spotify.com/user/USER_ID."

# Stable machine-readable recovery categories exposed to tests and future renderers
RECOVERY_CODES = frozenset({"config.missing", "config.invalid", "dependency.missing", "secret.missing", "auth.cookie_invalid", "auth.client_invalid", "auth.rejected", "network.unavailable", "network.timeout", "spotify.rate_limited", "spotify.unavailable", "target.invalid", "target.not_found", "target.not_visible", "smtp.invalid", "smtp.authentication", "smtp.connection", "webhook.invalid", "webhook.rejected", "webhook.rate_limited", "webhook.connection", "file.unreadable", "file.unwritable", "unknown"})


# Stores one stable recovery category with safe user-facing guidance
@dataclass(frozen=True)
class RecoveryAdvice:
    code: str
    summary: str
    fix: str
    retryable: bool
    detail: str = ""


# Carries structured recovery advice through exception boundaries
class RecoveryError(Exception):
    # Initializes a structured recovery exception without exposing technical detail
    def __init__(self, advice: RecoveryAdvice, cause: Optional[BaseException] = None):
        self.advice = advice
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause
        super().__init__(advice.summary)


# Stores one doctor result before the report is rendered
@dataclass(frozen=True)
class DoctorCheck:
    section: str
    status: str
    label: str
    detail: str = ""
    advice: Optional[RecoveryAdvice] = None


# Collects doctor checks and shared authenticated data for dependent checks
@dataclass
class DoctorReport:
    checks: List[DoctorCheck] = field(default_factory=list)
    access_token: Optional[str] = field(default=None, repr=False)
    buddy_list: Optional[dict] = None
    authentication_advice: Optional[RecoveryAdvice] = None


# Stores one startup setting and its output routing
@dataclass(frozen=True)
class StartupSummaryRow:
    label: str
    value: str
    concise: bool = False
    full: bool = True
    log: bool = True


# Prints the selected ASCII startup banner with a separately aligned version
def print_startup_banner() -> None:
    print(STARTUP_BANNER)
    print(f"{'':21}v{VERSION}\n")


# Returns True when a configured value is empty or still uses its shipped placeholder
def is_missing_or_placeholder(value: Any, placeholders: Sequence[str] = ()) -> bool:
    return not isinstance(value, str) or not value.strip() or value in placeholders


# Returns all complete secret values currently known to the process
def known_secret_values(extra_values: Sequence[Any] = ()) -> List[str]:
    values: List[str] = []
    for key in SECRET_KEYS:
        value = globals().get(key)
        if isinstance(value, str) and value and not value.startswith("your_"):
            values.append(value)
    for key in ("SP_CACHED_ACCESS_TOKEN", "SP_CACHED_REFRESH_TOKEN", "SP_CACHED_CLIENT_TOKEN", "SP_CACHED_OAUTH_APP_TOKEN", "SP_CACHED_WEB_ACCESS_TOKEN"):
        value = globals().get(key)
        if isinstance(value, str) and value:
            values.append(value)
    for value in extra_values:
        if isinstance(value, str) and value:
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


# Redacts credentials and serialized secret fields from arbitrary error text
def sanitize_error_text(value: Any, extra_secrets: Sequence[Any] = ()) -> str:
    text = str(value or "")
    for secret in known_secret_values(extra_secrets):
        text = text.replace(secret, "<redacted>")
    patterns = (
        (r"(?m)(\b(?:SP_DC_COOKIE|REFRESH_TOKEN|SP_APP_CLIENT_ID|SP_APP_CLIENT_SECRET|SMTP_PASSWORD|WEBHOOK_URL)\b\s*=\s*).*$", r"\1<redacted>"),
        (r"(?i)(authorization['\"]?\s*[:=]\s*['\"]?bearer\s+)[^\s,;'\"}]+", r"\1<redacted>"),
        (r"(?i)(cookie\s*[:=][^\r\n]*?sp_dc\s*=\s*)[^\s;,;'\"}]+", r"\1<redacted>"),
        (r"(?i)(\bsp_dc\s*=\s*)[^\s;,;'\"}]+", r"\1<redacted>"),
        (r"(?i)(['\"]?(?:access_token|refresh_token|client-token|client_token|smtp_password|webhook_url)['\"]?\s*[:=]\s*['\"]?)[^\s,;'\"}]+", r"\1<redacted>"),
    )
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    return text


# Extracts an HTTP status code from requests-style exceptions or response objects
def recovery_http_status(error: Any) -> Optional[int]:
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    if status is None:
        status = getattr(error, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


# Creates one validated recovery advice value
def make_recovery_advice(code: str, summary: str, fix: str, retryable: bool, detail: Any = "") -> RecoveryAdvice:
    if code not in RECOVERY_CODES:
        raise ValueError(f"Unsupported recovery code: {code}")
    return RecoveryAdvice(code, sanitize_error_text(summary), sanitize_error_text(fix), retryable, sanitize_error_text(detail))


# Adds a directly relevant documentation link on its own indented line
def recovery_fix_with_guide(fix: str, guide_url: str) -> str:
    return f"{fix}\n  Guide: {guide_url}"


# Returns install-aware cookie recovery guidance with private entry preferred in containers
def cookie_auth_recovery_fix() -> str:
    if not is_container_environment():
        return COOKIE_IMPORT_FIX
    method = _wizard_install_method()
    private_command = _wizard_set_sp_dc_cmd(method, Path.cwd() / ".env")
    firefox_command = _wizard_firefox_import_cmd(method, Path.cwd() / ".env")
    return f"Run the hidden private entry command: {private_command}\n  Advanced Firefox alternative with a read-only host profile mount: {firefox_command}"


# Classifies a user-facing failure using typed errors, HTTP status and explicit context
def classify_recovery_error(error: Any = None, context: str = "runtime", detail: Any = "") -> RecoveryAdvice:
    if isinstance(error, RecoveryError):
        return error.advice
    raw_message = str(detail or error or "").lower()
    safe_detail = sanitize_error_text(detail or error)
    message = raw_message
    status = recovery_http_status(error)

    if context == "browser_import":
        if any(term in message for term in ("network", "connectivity", "timed out", "name resolution")):
            return make_recovery_advice("network.unavailable", safe_detail or "Browser cookie validation could not reach Spotify", recovery_fix_with_guide("Check connectivity then retry the selected authentication command", COOKIE_GUIDE_URL), True, safe_detail)
        if any(term in message for term in ("invalid or expired", "authentication rejected", "no sp_dc", "nonempty sp_dc")):
            return make_recovery_advice("auth.cookie_invalid", safe_detail or "No valid sp_dc cookie was found", recovery_fix_with_guide(cookie_auth_recovery_fix(), COOKIE_GUIDE_URL), False, safe_detail)
        if any(term in message for term in ("database", "cookie file", "cookies.sqlite", "could not read dotenv")):
            return make_recovery_advice("file.unreadable", safe_detail or "The browser cookie database could not be read", "Close the browser, verify the selected profile or cookie database path then retry", False, safe_detail)
        if any(term in message for term in ("update dotenv", "dotenv destination", "file permissions")):
            return make_recovery_advice("file.unwritable", safe_detail or "The dotenv destination could not be updated", "Choose a writable --env-file path then retry", False, safe_detail)
        return make_recovery_advice("unknown", safe_detail or "Browser cookie import failed", recovery_fix_with_guide(cookie_auth_recovery_fix(), COOKIE_GUIDE_URL), False, safe_detail)

    if context == "set_sp_dc":
        if "interactive terminal" in message:
            return make_recovery_advice("unknown", "--set-sp-dc requires an interactive terminal", "Run --set-sp-dc from an interactive shell so getpass can hide the cookie", False, safe_detail)
        if any(term in message for term in ("network", "connectivity", "timed out", "name resolution")):
            return make_recovery_advice("network.unavailable", "Spotify cookie validation could not reach Spotify", recovery_fix_with_guide("Check connectivity then run the private entry command again", COOKIE_GUIDE_URL), True, safe_detail)
        if any(term in message for term in ("invalid or expired", "authentication rejected", "no nonempty", "rejected")):
            return make_recovery_advice("auth.cookie_invalid", "Spotify rejected the entered sp_dc cookie", recovery_fix_with_guide("Sign in at https://open.spotify.com/ then run the private entry command again", COOKIE_GUIDE_URL), False, safe_detail)
        if any(term in message for term in ("dotenv", "file permissions", "writable path")):
            return make_recovery_advice("file.unwritable", "The dotenv destination could not be updated", "Choose a writable --env-file path then retry", False, safe_detail)
        return make_recovery_advice("unknown", "SP_DC_COOKIE was not changed", recovery_fix_with_guide("Run the private entry command again or use the advanced Firefox import path", COOKIE_GUIDE_URL), False, safe_detail)

    if context == "set_webhook_url":
        if "interactive terminal" in message:
            return make_recovery_advice("webhook.invalid", "--set-webhook-url requires an interactive terminal", "Run --set-webhook-url from an interactive shell so the URL can be entered through a hidden prompt", False, safe_detail)
        if any(term in message for term in ("dotenv", "file permissions", "writable path")):
            return make_recovery_advice("file.unwritable", "The dotenv destination could not be updated", "Choose a writable --env-file path then retry", False, safe_detail)
        return make_recovery_advice("webhook.invalid", "WEBHOOK_URL was not changed", recovery_fix_with_guide("Enter a complete HTTPS Discord-compatible webhook URL then retry", WEBHOOK_GUIDE_URL), False, safe_detail)

    if context == "config_missing":
        summary = "The requested configuration file was not found"
        if safe_detail:
            summary += f": {safe_detail.removeprefix('Configuration file not found: ')}"
        return make_recovery_advice("config.missing", summary, recovery_fix_with_guide("Verify the --config-file path or generate a new config at that path", CONFIG_GUIDE_URL), False, safe_detail)
    if context == "config_invalid":
        return make_recovery_advice("config.invalid", "The configuration file could not be loaded", recovery_fix_with_guide("Correct the reported config line or generate a fresh config at another path then retry", CONFIG_GUIDE_URL), False, safe_detail)
    if context == "dependency":
        dependency = getattr(error, "name", None) or safe_detail or "required package"
        return make_recovery_advice("dependency.missing", f"A required dependency is missing: {dependency}", recovery_fix_with_guide("Install the project requirements then retry", INSTALLATION_GUIDE_URL), False, safe_detail)
    if context == "secret":
        return make_recovery_advice("secret.missing", safe_detail or "A required secret is missing", recovery_fix_with_guide("Provide the required secret through a dotenv file, environment variable or supported command-line option", SECRETS_GUIDE_URL), False)
    if context == "target_missing":
        return make_recovery_advice("target.invalid", "No Spotify target was provided", recovery_fix_with_guide("Provide a positional user ID, spotify:user URI or Spotify profile URL or set TARGET_USER_URI_ID", QUICK_START_GUIDE_URL), False)
    if context == "target_invalid":
        return make_recovery_advice("target.invalid", "Invalid Spotify target", recovery_fix_with_guide("Pass a raw user ID, spotify:user:USER_ID or https://open.spotify.com/user/USER_ID", TARGET_GUIDE_URL), False, safe_detail)
    if context == "target_not_visible":
        return make_recovery_advice("target.not_visible", "The target is not visible in Spotify Friend Activity", recovery_fix_with_guide("Confirm the account appears in Spotify Friend Activity for the account represented by these credentials. The target may need to share listening activity", FOLLOWING_GUIDE_URL), False, safe_detail)
    if context == "file_read":
        return make_recovery_advice("file.unreadable", "A required file could not be read", "Verify the path, file format and read permissions then retry", False, safe_detail)
    if context == "file_write":
        return make_recovery_advice("file.unwritable", "An output destination is not writable", "Choose a writable path and verify its parent directory permissions then retry", False, safe_detail)
    if context == "smtp_config":
        return make_recovery_advice("smtp.invalid", "The SMTP configuration is incomplete or invalid", recovery_fix_with_guide("Correct SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL and RECEIVER_EMAIL then run --send-test-email", SMTP_GUIDE_URL), False, safe_detail)
    if context == "webhook_config":
        return make_recovery_advice("webhook.invalid", "The webhook configuration is incomplete or invalid", recovery_fix_with_guide("Set a complete HTTPS WEBHOOK_URL then run --send-test-webhook", WEBHOOK_GUIDE_URL), False, safe_detail)

    if context.startswith("webhook"):
        if status == 429 or any(term in message for term in ("429", "too many requests", "rate limit")):
            return make_recovery_advice("webhook.rate_limited", "The webhook endpoint is rate limiting notifications", recovery_fix_with_guide("Wait briefly then run --send-test-webhook. Spotify polling continues independently", WEBHOOK_GUIDE_URL), True, safe_detail)
        if status is not None and 400 <= status <= 499:
            return make_recovery_advice("webhook.rejected", "The webhook endpoint rejected the notification", recovery_fix_with_guide("Verify that WEBHOOK_URL is current then run --send-test-webhook", WEBHOOK_GUIDE_URL), False, safe_detail)
        if status is not None and 500 <= status <= 599:
            return make_recovery_advice("webhook.connection", "The webhook endpoint is temporarily unavailable", recovery_fix_with_guide("Wait briefly then run --send-test-webhook", WEBHOOK_GUIDE_URL), True, safe_detail)
        if isinstance(error, (req.Timeout, TimeoutException, socket.timeout)) or "timed out" in message or " timeout" in message:
            return make_recovery_advice("webhook.connection", "The webhook request timed out", recovery_fix_with_guide("Check network access then run --send-test-webhook", WEBHOOK_GUIDE_URL), True, safe_detail)
        if isinstance(error, (req.RequestException, ConnectionError, socket.gaierror)) or any(term in message for term in ("name resolution", "failed to resolve", "network is unreachable", "connection refused", "connection aborted", "max retries exceeded")):
            return make_recovery_advice("webhook.connection", "The webhook endpoint could not be reached", recovery_fix_with_guide("Check DNS, internet access and firewall rules then run --send-test-webhook", WEBHOOK_GUIDE_URL), True, safe_detail)
        return make_recovery_advice("webhook.connection", "The webhook notification could not be delivered", recovery_fix_with_guide("Run --send-test-webhook and retry with --debug if the failure continues", WEBHOOK_GUIDE_URL), True, safe_detail)

    if isinstance(error, smtplib.SMTPAuthenticationError) or status == 535:
        return make_recovery_advice("smtp.authentication", "SMTP authentication was rejected", recovery_fix_with_guide("Verify SMTP_USER and SMTP_PASSWORD. Providers such as Gmail may require an app password then run --send-test-email", SMTP_GUIDE_URL), False, safe_detail)
    if isinstance(error, (smtplib.SMTPException, ConnectionError)) and context.startswith("smtp"):
        return make_recovery_advice("smtp.connection", "The SMTP server connection failed", recovery_fix_with_guide("Verify SMTP_HOST, SMTP_PORT and SMTP_SSL then run --send-test-email", SMTP_GUIDE_URL), True, safe_detail)
    if isinstance(error, (req.Timeout, TimeoutException, socket.timeout)) or "timed out" in message or " timeout" in message:
        code = "smtp.connection" if context.startswith("smtp") else "network.timeout"
        summary = "The SMTP connection timed out" if context.startswith("smtp") else "The Spotify request timed out"
        fix = recovery_fix_with_guide("Verify SMTP_HOST, SMTP_PORT and network access then run --send-test-email", SMTP_GUIDE_URL) if context.startswith("smtp") else "Check connectivity and retry. If timeouts continue run --doctor --debug"
        return make_recovery_advice(code, summary, fix, True, safe_detail)
    if isinstance(error, req.exceptions.SSLError) or any(term in message for term in ("certificate verify failed", "tls", "ssl error")):
        if context.startswith("smtp"):
            return make_recovery_advice("smtp.connection", "A secure SMTP connection could not be established", recovery_fix_with_guide("Verify SMTP_HOST, SMTP_PORT and SMTP_SSL plus the system CA certificates then run --send-test-email", SMTP_GUIDE_URL), True, safe_detail)
        return make_recovery_advice("network.unavailable", "A secure connection to Spotify could not be established", "Check the system clock, CA certificates, firewall and TLS-inspecting proxy settings then retry", True, safe_detail)
    if isinstance(error, (req.ConnectionError, socket.gaierror)) or any(term in message for term in ("name resolution", "failed to resolve", "network is unreachable", "connection refused", "connection aborted", "max retries exceeded")):
        code = "smtp.connection" if context.startswith("smtp") else "network.unavailable"
        summary = "The SMTP server could not be reached" if context.startswith("smtp") else "Spotify could not be reached"
        fix = recovery_fix_with_guide("Verify SMTP_HOST, SMTP_PORT and network access then run --send-test-email", SMTP_GUIDE_URL) if context.startswith("smtp") else "Check DNS, internet access, firewall and proxy settings then retry"
        return make_recovery_advice(code, summary, fix, True, safe_detail)

    if status == 429 or any(term in message for term in ("429", "too many requests", "rate limit")):
        return make_recovery_advice("spotify.rate_limited", "Spotify is rate limiting requests", recovery_fix_with_guide("Wait before retrying and increase -c or --check-interval to reduce request frequency", INTERVALS_GUIDE_URL), True, safe_detail)
    if status is not None and 500 <= status <= 599 or any(term in message for term in ("500 server", "502 server", "503 server", "504 server")):
        return make_recovery_advice("spotify.unavailable", "Spotify is temporarily unavailable", "Wait and retry later. Run --doctor if the failure continues", True, safe_detail)
    if status == 404 and context.startswith("target"):
        return make_recovery_advice("target.not_found", "The Spotify target was not found", recovery_fix_with_guide("Check the target ID, URI or profile URL then retry", TARGET_GUIDE_URL), False, safe_detail)
    if status == 401 or "401 unauthorized" in message or "unauthorized" in message:
        if context.startswith("cookie"):
            return make_recovery_advice("auth.cookie_invalid", "Spotify rejected the sp_dc cookie", recovery_fix_with_guide(cookie_auth_recovery_fix(), COOKIE_GUIDE_URL), False, safe_detail)
        if context.startswith("client"):
            return make_recovery_advice("auth.client_invalid", "Spotify rejected the client credentials", recovery_fix_with_guide("Re-export the Spotify Desktop Client login request", CLIENT_GUIDE_URL), False, safe_detail)
        return make_recovery_advice("auth.rejected", "Spotify rejected authentication", "Refresh the configured credentials then run --doctor", False, safe_detail)
    if status == 403 and context == "metadata":
        return make_recovery_advice("spotify.unavailable", "The legacy Spotify metadata path is restricted", recovery_fix_with_guide("Remove incompatible legacy OAuth credentials and use the automatic web-player metadata fallback", OAUTH_GUIDE_URL), False, safe_detail)
    if status == 403:
        if context.startswith("cookie"):
            return make_recovery_advice("auth.rejected", "Spotify rejected the authenticated cookie request", recovery_fix_with_guide(cookie_auth_recovery_fix(), COOKIE_GUIDE_URL), False, safe_detail)
        return make_recovery_advice("auth.rejected", "Spotify rejected the authenticated request", "Refresh the configured credentials then run --doctor", False, safe_detail)
    if context.startswith("cookie") and any(term in message for term in ("sp_dc", "unsuccessful token request", "valid spotify access token", "access token after")):
        return make_recovery_advice("auth.cookie_invalid", "The sp_dc cookie is invalid, expired or was rejected", recovery_fix_with_guide(cookie_auth_recovery_fix(), COOKIE_GUIDE_URL), False, safe_detail)
    if context.startswith("client") and any(term in message for term in ("refresh token", "client token", "invalid grant", "access token not found")):
        return make_recovery_advice("auth.client_invalid", "The Spotify desktop client credentials are invalid or expired", recovery_fix_with_guide("Re-export the relevant Spotify Desktop Client login or client-token request", CLIENT_GUIDE_URL), False, safe_detail)
    if isinstance(error, ModuleNotFoundError):
        return classify_recovery_error(error, "dependency", safe_detail)
    if isinstance(error, FileNotFoundError):
        return classify_recovery_error(error, "file_read", safe_detail)
    if isinstance(error, (PermissionError, OSError)) and context.startswith("file"):
        return classify_recovery_error(error, context, safe_detail)
    return make_recovery_advice("unknown", "An unexpected error occurred", recovery_fix_with_guide("Run --doctor. If the issue continues retry with --debug and review the sanitized technical detail", DOCTOR_GUIDE_URL), True, safe_detail)


# Renders structured recovery advice without exposing secret-bearing exception text
def render_recovery_error(error: Any = None, context: str = "runtime", debug: Optional[bool] = None, detail: Any = "") -> str:
    advice = classify_recovery_error(error, context, detail)
    lines = [f"* Error: {advice.summary}", f"  To fix: {advice.fix}"]
    show_debug = DEBUG_MODE if debug is None else debug
    if show_debug and advice.detail:
        lines.append(f"  Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Prints one structured recovery error and returns its stable advice
def print_recovery_error(error: Any = None, context: str = "runtime", debug: Optional[bool] = None, detail: Any = "") -> RecoveryAdvice:
    advice = classify_recovery_error(error, context, detail)
    print(render_recovery_error(RecoveryError(advice), debug=debug))
    return advice


# Tracks the last uninterrupted recovery category to suppress duplicate hints
@dataclass
class RecoveryHintTracker:
    last_code: Optional[str] = None

    # Returns True for the first category or after the failure category changes
    def should_render(self, advice: RecoveryAdvice) -> bool:
        if advice.code == self.last_code:
            return False
        self.last_code = advice.code
        return True

    # Clears suppression after a successful request cycle
    def reset(self) -> None:
        self.last_code = None


# Normalizes a raw Spotify user ID, user URI or profile URL into one user ID
def normalize_spotify_user_id(value):
    if not isinstance(value, str):
        raise ValueError(TARGET_INPUT_ERROR)

    target = value.strip()
    if not target or any(character.isspace() or ord(character) < 32 or 127 <= ord(character) <= 159 for character in target):
        raise ValueError(TARGET_INPUT_ERROR)

    encoded_user_id = target
    if target.lower().startswith("spotify:"):
        parts = target.split(":")
        if len(parts) != 3 or parts[0].lower() != "spotify" or parts[1].lower() != "user":
            raise ValueError(TARGET_INPUT_ERROR)
        encoded_user_id = parts[2]
    elif "://" in target or target.lower().startswith(("http:", "https:")):
        try:
            parsed = urlsplit(target)
            parsed_port = parsed.port
        except ValueError as exc:
            raise ValueError(TARGET_INPUT_ERROR) from exc
        if parsed.scheme.lower() not in ("http", "https") or parsed.hostname is None or parsed.hostname.lower() != "open.spotify.com":
            raise ValueError(TARGET_INPUT_ERROR)
        if parsed.username is not None or parsed.password is not None or parsed_port is not None or parsed.fragment:
            raise ValueError(TARGET_INPUT_ERROR)
        path_parts = parsed.path.split("/")
        if path_parts and path_parts[-1] == "":
            path_parts = path_parts[:-1]
        if len(path_parts) != 3 or path_parts[0] != "" or path_parts[1].lower() != "user":
            raise ValueError(TARGET_INPUT_ERROR)
        encoded_user_id = path_parts[2]
    elif any(character in target for character in (":", "?", "#")):
        raise ValueError(TARGET_INPUT_ERROR)

    if re.search(r"%(?![0-9A-Fa-f]{2})", encoded_user_id):
        raise ValueError(TARGET_INPUT_ERROR)
    try:
        user_id = unquote(encoded_user_id, encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(TARGET_INPUT_ERROR) from exc

    if not user_id or user_id in (".", "..") or any(character in user_id for character in ("/", "\\", "?", "#")):
        raise ValueError(TARGET_INPUT_ERROR)
    if any(character.isspace() or ord(character) < 32 or 127 <= ord(character) <= 159 for character in user_id):
        raise ValueError(TARGET_INPUT_ERROR)
    return user_id


# Resolves CLI and configured targets with CLI precedence then normalizes the selected value
def resolve_target_user_id(cli_value, configured_value):
    if cli_value is not None:
        return normalize_spotify_user_id(cli_value)
    if configured_value is None or configured_value == "":
        return None
    return normalize_spotify_user_id(configured_value)


# Splits an assignment value from an inline comment while ignoring hashes inside strings
def _split_inline_comment_preserving_strings(rhs: str) -> tuple[str, str]:
    in_single = False
    in_double = False
    escaped = False
    for index, character in enumerate(rhs):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character == "'" and not in_double:
            in_single = not in_single
            continue
        if character == '"' and not in_single:
            in_double = not in_double
            continue
        if character == "#" and not in_single and not in_double:
            return rhs[:index].rstrip(), rhs[index:].rstrip()
    return rhs.rstrip(), ""


# Formats a supported runtime value as a valid Python config literal
def _format_config_value(value, prefer_double_quotes: bool) -> str:
    if isinstance(value, str):
        if prefer_double_quotes:
            return json.dumps(value, ensure_ascii=True)
        escaped = value.encode("unicode_escape").decode("ascii").replace("'", "\\'")
        return f"'{escaped}'"
    if value is None or isinstance(value, (bool, int, float, list, tuple, dict)):
        return repr(value)
    raise TypeError(f"Unsupported config value type: {type(value).__name__}")


# Validates Python config content without executing it
def validate_config_content(content: str, filename: str = "<generated-config>") -> None:
    compile(content, filename, "exec")


# Renders CONFIG_BLOCK with current non-secret runtime values and preserved template secrets
def generate_config_with_current_values(values=None) -> str:
    current_values = globals() if values is None else values
    assignment_pattern = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=\s*(.*)$")
    output_lines = []

    for line in CONFIG_BLOCK.strip("\n").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            output_lines.append(line)
            continue

        match = assignment_pattern.match(line)
        if not match:
            output_lines.append(line)
            continue

        variable = match.group(1)
        expression, comment = _split_inline_comment_preserving_strings(match.group(2))
        expression_stripped = expression.strip()
        if expression_stripped.endswith(("{", "[", "(")) and not any(character in expression_stripped for character in ("}", "]", ")")):
            output_lines.append(line)
            continue
        try:
            compile(f"{variable} = {expression}\n", "<config-template-line>", "exec")
        except SyntaxError:
            output_lines.append(line)
            continue
        if variable in SECRET_KEYS or variable not in current_values:
            output_lines.append(line)
            continue

        rendered_value = _format_config_value(current_values[variable], prefer_double_quotes=expression_stripped.startswith('"'))
        rendered_line = f"{variable} = {rendered_value}"
        if comment:
            rendered_line = f"{rendered_line}  {comment}"
        output_lines.append(rendered_line)

    rendered = "\n".join(output_lines) + "\n"
    validate_config_content(rendered)
    return rendered


# Writes validated config content atomically and backs up an existing destination
def write_config_file(destination, content: str):
    destination_path = Path(destination).expanduser()
    validate_config_content(content, str(destination_path))
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    backup_path = None

    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        if destination_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            for collision_index in range(1000):
                collision_suffix = "" if collision_index == 0 else f"-{collision_index:02d}"
                candidate = destination_path.with_name(f"{destination_path.name}.{timestamp}{collision_suffix}.bak")
                try:
                    with destination_path.open("rb") as source_file, candidate.open("xb") as backup_file:
                        shutil.copyfileobj(source_file, backup_file)
                        backup_file.flush()
                        os.fsync(backup_file.fileno())
                    backup_path = candidate
                    break
                except FileExistsError:
                    continue
                except Exception:
                    if candidate.exists():
                        candidate.unlink()
                    raise
            if backup_path is None:
                raise FileExistsError(f"Could not create a unique backup for '{destination_path}'")

        os.replace(temporary_path, destination_path)
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return {"path": str(destination_path), "backup_path": str(backup_path) if backup_path is not None else None}


# Quotes one secret value for lossless parsing by python-dotenv
def _format_dotenv_value(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Dotenv secret values must be strings")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    return f'"{escaped}"'


# Updates allowed secrets in a dotenv file through an atomic replacement
def update_dotenv_file(destination, updates):
    if not hasattr(updates, "items"):
        raise TypeError("Dotenv updates must be a mapping")
    update_items = list(updates.items())
    for key, value in update_items:
        if not isinstance(key, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key not in SECRET_KEYS:
            raise ValueError(f"Unsupported dotenv key: {key!r}")
        if not isinstance(value, str):
            raise TypeError(f"Dotenv value for {key} must be a string")

    destination_path = Path(destination).expanduser()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        existing_lines = destination_path.read_text(encoding="utf-8").splitlines()
    else:
        existing_lines = []

    update_keys = {key for key, _ in update_items}
    values_by_key = dict(update_items)
    seen_keys = set()
    output_lines = []
    assignment_pattern = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
    for line in existing_lines:
        match = assignment_pattern.match(line)
        key = match.group(1) if match else None
        if key not in update_keys:
            output_lines.append(line)
            continue
        if key in seen_keys:
            continue
        output_lines.append(f"{key}={_format_dotenv_value(values_by_key[key])}")
        seen_keys.add(key)

    for key, value in update_items:
        if key not in seen_keys:
            output_lines.append(f"{key}={_format_dotenv_value(value)}")
            seen_keys.add(key)

    content = "\n".join(output_lines)
    if output_lines:
        content += "\n"

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if os.name == "posix":
            os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, destination_path)
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return {"path": str(destination_path), "updated_keys": tuple(key for key, _ in update_items)}


# Raised when a browser cookie cannot be extracted, validated or persisted safely
class BrowserCookieImportError(Exception):
    pass


# Raised when a webhook secret cannot be validated or persisted safely
class WebhookConfigurationError(Exception):
    pass


# Returns a user-facing label for one supported browser
def browser_label(browser):
    return "Firefox" if browser == "firefox" else browser.capitalize()


# Returns normal Firefox profile roots for the selected platform
def _firefox_profile_roots(system_name=None, home=None, environ=None):
    selected_system = platform.system() if system_name is None else system_name
    home_path = Path.home() if home is None else Path(home)
    environment = os.environ if environ is None else environ
    if selected_system == "Darwin":
        return [home_path / "Library/Application Support/Firefox"]
    if selected_system == "Windows":
        appdata = environment.get("APPDATA")
        return [Path(appdata) / "Mozilla/Firefox"] if appdata else [home_path / "AppData/Roaming/Mozilla/Firefox"]
    if selected_system == "Linux":
        return [home_path / ".mozilla/firefox", home_path / "snap/firefox/common/.mozilla/firefox", home_path / ".var/app/org.mozilla.firefox/.mozilla/firefox"]
    return []


# Builds one normalized browser profile record
def _browser_profile_record(profile_dir, friendly_name, cookie_file):
    return {"dir": profile_dir.name, "name": friendly_name or profile_dir.name, "path": str(profile_dir), "cookie_file": str(cookie_file)}


# Adds one usable profile record without duplicating its cookie database
def _add_browser_profile(profiles_by_cookie, profile_dir, friendly_name):
    cookie_file = profile_dir / "cookies.sqlite"
    if not cookie_file.is_file():
        return
    cookie_key = str(cookie_file.resolve())
    profiles_by_cookie.setdefault(cookie_key, _browser_profile_record(profile_dir, friendly_name, cookie_file))


# Discovers usable Firefox profiles from profiles.ini metadata plus directory scans
def discover_firefox_profiles(system_name=None, home=None, environ=None):
    profiles_by_cookie = {}
    for root in _firefox_profile_roots(system_name=system_name, home=home, environ=environ):
        profiles_ini = root / "profiles.ini"
        if profiles_ini.is_file():
            parser = configparser.RawConfigParser()
            try:
                with profiles_ini.open("r", encoding="utf-8") as profiles_file:
                    parser.read_file(profiles_file)
                for section in parser.sections():
                    if not section.lower().startswith("profile") or not parser.has_option(section, "Path"):
                        continue
                    configured_path = os.path.expandvars(os.path.expanduser(parser.get(section, "Path")))
                    profile_dir = Path(configured_path)
                    if parser.get(section, "IsRelative", fallback="1") != "0":
                        profile_dir = root / profile_dir
                    _add_browser_profile(profiles_by_cookie, profile_dir, parser.get(section, "Name", fallback=profile_dir.name))
            except (OSError, UnicodeError, configparser.Error):
                pass

        for profile_parent in (root, root / "Profiles"):
            if not profile_parent.is_dir():
                continue
            try:
                profile_dirs = sorted((entry for entry in profile_parent.iterdir() if entry.is_dir()), key=lambda entry: entry.name.lower())
            except OSError:
                continue
            for profile_dir in profile_dirs:
                friendly_name = profile_dir.name.split(".", 1)[1] if "." in profile_dir.name else profile_dir.name
                _add_browser_profile(profiles_by_cookie, profile_dir, friendly_name)

    return sorted(profiles_by_cookie.values(), key=lambda profile: (profile["name"].lower(), profile["dir"].lower(), profile["cookie_file"]))


# Formats profile choices without exposing any cookie values
def _format_profile_choices(profiles):
    return ", ".join(f"{profile['dir']} ({profile['name']})" if profile["name"] != profile["dir"] else profile["dir"] for profile in profiles)


# Selects one browser profile explicitly, automatically or through a terminal prompt
def select_browser_profile(profiles, browser, requested_profile=None, interactive=None, input_func=None):
    label = browser_label(browser)
    if not profiles:
        raise BrowserCookieImportError(f"No usable {label} profiles found. Sign in to Spotify in {label} or pass --cookie-file PATH.")

    if requested_profile:
        requested = requested_profile.casefold()
        directory_matches = [profile for profile in profiles if profile["dir"].casefold() == requested]
        friendly_matches = [profile for profile in profiles if profile["name"].casefold() == requested]
        matches = directory_matches or friendly_matches
        if len(matches) == 1:
            return matches[0]
        choices = _format_profile_choices(profiles)
        if len(matches) > 1:
            raise BrowserCookieImportError(f"{label} profile name '{requested_profile}' is ambiguous. Pass one profile directory with --browser-profile. Choices: {choices}")
        raise BrowserCookieImportError(f"Unknown {label} profile '{requested_profile}'. Choices: {choices}")

    if len(profiles) == 1:
        return profiles[0]

    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    choices = _format_profile_choices(profiles)
    if not terminal_is_interactive:
        raise BrowserCookieImportError(f"Multiple {label} profiles found: {choices}. Pass --browser-profile PROFILE to select one in a noninteractive environment.")

    print(f"Multiple {label} profiles found:")
    for index, profile in enumerate(profiles, start=1):
        print(f"  {index}) {profile['name']} [{profile['dir']}] - {profile['cookie_file']}")
    prompt = input if input_func is None else input_func
    try:
        choice = int(prompt("Select profile number (0 to cancel): "))
    except (EOFError, ValueError):
        raise BrowserCookieImportError("Browser cookie import cancelled because the profile selection was invalid.") from None
    if choice == 0:
        raise BrowserCookieImportError("Browser cookie import cancelled.")
    if choice < 1 or choice > len(profiles):
        raise BrowserCookieImportError("Browser cookie import cancelled because the profile selection was invalid.")
    return profiles[choice - 1]


# Quotes a SQLite identifier obtained from database schema metadata
def _sqlite_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


# Converts an optional SQLite cookie field into a comparable number
def _numeric_cookie_field(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


# Reads the best Spotify sp_dc cookie from a Firefox SQLite database
def read_firefox_sp_dc(cookie_file, now=None):
    cookie_path = Path(cookie_file).expanduser()
    if not cookie_path.is_file():
        raise BrowserCookieImportError(f"Firefox cookie database '{cookie_path}' was not found. Pass a valid cookies.sqlite path with --cookie-file.")

    try:
        with sqlite3.connect(cookie_path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
            columns = connection.execute("PRAGMA table_info(moz_cookies)").fetchall()
            column_names = {str(row[1]).lower(): str(row[1]) for row in columns}
            if "name" not in column_names or "value" not in column_names:
                raise sqlite3.DatabaseError("missing required cookie columns")
            domain_key = "host" if "host" in column_names else "basedomain" if "basedomain" in column_names else None
            if domain_key is None:
                raise sqlite3.DatabaseError("missing cookie domain column")

            selected_keys = ["value", domain_key]
            last_access_key = "lastaccessed" if "lastaccessed" in column_names else "last_accessed" if "last_accessed" in column_names else None
            expiry_key = next((key for key in ("expiry", "expires", "expirationdate") if key in column_names), None)
            if last_access_key:
                selected_keys.append(last_access_key)
            if expiry_key:
                selected_keys.append(expiry_key)

            selected_columns = ", ".join(_sqlite_identifier(column_names[key]) for key in selected_keys)
            name_column = _sqlite_identifier(column_names["name"])
            value_column = _sqlite_identifier(column_names["value"])
            domain_column = _sqlite_identifier(column_names[domain_key])
            query = f"SELECT {selected_columns} FROM moz_cookies WHERE {name_column} = ? AND {value_column} IS NOT NULL AND {value_column} != '' AND (lower(ltrim({domain_column}, '.')) = ? OR lower(ltrim({domain_column}, '.')) LIKE ?)"
            rows = connection.execute(query, ("sp_dc", "spotify.com", "%.spotify.com")).fetchall()
    except (sqlite3.DatabaseError, sqlite3.OperationalError, OSError):
        raise BrowserCookieImportError("Could not read the Firefox cookie database. Close Firefox then retry or pass --cookie-file with a readable cookies.sqlite copy.") from None

    if not rows:
        raise BrowserCookieImportError("No sp_dc cookie for spotify.com was found in the selected Firefox profile. Sign in to Spotify in Firefox then retry.")

    now_value = time.time() if now is None else now
    last_access_index = selected_keys.index(last_access_key) if last_access_key else None
    expiry_index = selected_keys.index(expiry_key) if expiry_key else None

    # Ranks nonexpired cookies first then uses last access and stable fields for deterministic selection
    def cookie_rank(row):
        last_accessed = _numeric_cookie_field(row[last_access_index]) if last_access_index is not None else 0.0
        expiry = _numeric_cookie_field(row[expiry_index]) if expiry_index is not None else 0.0
        nonexpired = 1 if expiry <= 0 or expiry > now_value else 0
        return nonexpired, last_accessed, expiry, str(row[1]).lower(), str(row[0])

    return str(max(rows, key=cookie_rank)[0])


# Returns the standard Chromium user-data directory for one browser and platform
def get_chromium_user_data_dir(browser, system_name=None, home=None):
    selected_system = platform.system() if system_name is None else system_name
    relative_path = CHROMIUM_USER_DATA_DIRS.get(selected_system, {}).get(browser)
    if relative_path is None:
        return None
    home_path = Path.home() if home is None else Path(home)
    return home_path / relative_path


# Resolves a Chromium profile cookie database with modern layout preference
def resolve_chromium_cookie_file(user_data_dir, profile_dir):
    profile_path = Path(user_data_dir) / profile_dir
    for relative_path in (Path("Network") / "Cookies", Path("Cookies")):
        candidate = profile_path / relative_path
        if candidate.is_file():
            return candidate
    return None


# Discovers usable Chrome, Brave or Chromium profiles and Local State names
def discover_chromium_profiles(browser, system_name=None, home=None, user_data_dir=None):
    base_path = Path(user_data_dir) if user_data_dir is not None else get_chromium_user_data_dir(browser, system_name=system_name, home=home)
    if base_path is None or not base_path.is_dir():
        return []

    friendly_names = {}
    try:
        with (base_path / "Local State").open("r", encoding="utf-8") as local_state_file:
            info_cache = json.load(local_state_file).get("profile", {}).get("info_cache", {})
        friendly_names = {directory: details.get("name") or directory for directory, details in info_cache.items() if isinstance(details, dict)}
    except (OSError, UnicodeError, ValueError, AttributeError):
        pass

    profiles = []
    try:
        entries = sorted(base_path.iterdir(), key=lambda entry: entry.name.lower())
    except OSError:
        return []
    for entry in entries:
        if not entry.is_dir() or (entry.name != "Default" and not entry.name.startswith("Profile ")):
            continue
        cookie_file = resolve_chromium_cookie_file(base_path, entry.name)
        if cookie_file is not None:
            profiles.append({"dir": entry.name, "name": friendly_names.get(entry.name, entry.name), "path": str(entry), "cookie_file": str(cookie_file)})
    return profiles


# Calls pycookiecheat for Spotify through a narrow dynamically imported adapter
def _pycookiecheat_spotify_cookies(browser, cookie_file):
    try:
        from pycookiecheat import BrowserType, get_cookies
    except (ImportError, ModuleNotFoundError):
        raise BrowserCookieImportError("Chromium browser import requires the optional pycookiecheat dependency. Firefox needs no extra dependency. Install it with:\n\n    pip install \"spotify_monitor[browser]\"") from None

    browser_type = {"chrome": BrowserType.CHROME, "brave": BrowserType.BRAVE, "chromium": BrowserType.CHROMIUM}[browser]
    return get_cookies("https://open.spotify.com", browser=browser_type, cookie_file=str(cookie_file))


# Converts a pycookiecheat failure into a secret-safe actionable message
def _safe_chromium_cookie_error(browser, error):
    label = browser_label(browser)
    error_text = str(error).lower()
    if any(term in error_text for term in ("keyring", "secretservice", "secret service", "password")):
        return f"Could not access the OS keyring needed to decrypt {label} cookies. Unlock the keyring then retry or use Firefox."
    if any(term in error_text for term in ("decrypt", "invalidtag", "encryption")):
        return f"Could not decrypt {label} cookies. Close {label} then retry or import from Firefox."
    if any(term in error_text for term in ("permission", "denied", "locked", "readonly", "unable to open")):
        return f"Could not access the {label} cookie database. Close {label}, check file permissions then retry or use Firefox."
    return f"Could not read {label} cookies. Confirm Spotify is signed in, close {label} then retry or use Firefox."


# Reads only the Spotify sp_dc value from a Chromium cookie collection
def read_chromium_sp_dc(browser, cookie_file, cookie_adapter=None, system_name=None):
    selected_system = platform.system() if system_name is None else system_name
    label = browser_label(browser)
    if selected_system == "Windows":
        raise BrowserCookieImportError(f"Importing {label} cookies is unavailable on Windows because current Chromium app-bound cookie encryption prevents reliable external access. Use Firefox instead.")

    cookie_path = Path(cookie_file).expanduser()
    if not cookie_path.is_file():
        raise BrowserCookieImportError(f"{label} cookie database '{cookie_path}' was not found. Pass a valid path with --cookie-file.")
    adapter = _pycookiecheat_spotify_cookies if cookie_adapter is None else cookie_adapter
    try:
        cookies = adapter(browser, cookie_path)
    except BrowserCookieImportError:
        raise
    except Exception as exc:
        raise BrowserCookieImportError(_safe_chromium_cookie_error(browser, exc)) from None

    sp_dc = cookies.get("sp_dc") if isinstance(cookies, dict) else next((getattr(cookie, "value", None) for cookie in cookies if getattr(cookie, "name", None) == "sp_dc"), None)
    if not isinstance(sp_dc, str) or not sp_dc:
        raise BrowserCookieImportError(f"No sp_dc cookie for spotify.com was found in the selected {label} profile. Sign in to Spotify in {label} then retry.")
    return sp_dc


# Resolves the browser import dotenv destination without parent discovery
def resolve_import_env_path(env_file=None, cwd=None):
    if env_file is not None and str(env_file).casefold() == "none":
        raise BrowserCookieImportError("Browser cookie import requires a dotenv destination. Replace '--env-file none' with a writable path.")
    base_directory = Path.cwd() if cwd is None else Path(cwd)
    destination = base_directory / ".env" if env_file is None else Path(env_file).expanduser()
    return destination.resolve()


# Checks whether a dotenv file already contains one named assignment
def _dotenv_contains_key(destination, key):
    destination_path = Path(destination)
    if not destination_path.exists():
        return False
    try:
        lines = destination_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise BrowserCookieImportError(f"Could not read dotenv destination '{destination_path}'. Check that it is a readable UTF-8 file.") from None
    assignment_pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
    return any(assignment_pattern.match(line) for line in lines)


# Identifies network-shaped authentication failures without returning raw exception text
def _looks_like_network_failure(error):
    if isinstance(error, req.RequestException):
        return True
    error_text = str(error).lower()
    return any(term in error_text for term in ("connection", "connectivity", "timeout", "timed out", "name resolution", "dns", "proxy", "ssl", "500", "502", "503", "504"))


# Validates one imported sp_dc through token acquisition and the buddy-list endpoint
def validate_imported_sp_dc(sp_dc):
    global TOKEN_SOURCE, USER_AGENT, SP_CACHED_CLIENT_ID, DEBUG_MODE
    if not isinstance(sp_dc, str) or not sp_dc:
        raise BrowserCookieImportError("No nonempty sp_dc cookie was extracted.")

    previous_token_source = TOKEN_SOURCE
    previous_user_agent = USER_AGENT
    previous_client_id = SP_CACHED_CLIENT_ID
    previous_debug_mode = DEBUG_MODE
    TOKEN_SOURCE = "cookie"
    DEBUG_MODE = False
    if not USER_AGENT:
        USER_AGENT = get_random_user_agent()
    try:
        try:
            token_data = refresh_access_token_from_sp_dc(sp_dc)
        except Exception as exc:
            if _looks_like_network_failure(exc):
                raise BrowserCookieImportError("A network or connectivity failure prevented Spotify cookie validation. Check connectivity then retry.") from None
            raise BrowserCookieImportError("The imported sp_dc cookie is invalid or expired. Sign in to Spotify in the browser then retry.") from None

        access_token = token_data.get("access_token") if isinstance(token_data, dict) else None
        client_id = token_data.get("client_id", "") if isinstance(token_data, dict) else ""
        if not isinstance(access_token, str) or not access_token:
            raise BrowserCookieImportError("The imported sp_dc cookie is invalid or expired. Sign in to Spotify in the browser then retry.")
        SP_CACHED_CLIENT_ID = client_id
        try:
            spotify_get_friends_json(access_token)
        except Exception as exc:
            if _looks_like_network_failure(exc):
                raise BrowserCookieImportError("A network or connectivity failure prevented the authenticated Spotify request. Check connectivity then retry.") from None
            raise BrowserCookieImportError("Spotify authentication rejected the imported sp_dc cookie. Sign in to Spotify in the browser then retry.") from None
    finally:
        TOKEN_SOURCE = previous_token_source
        USER_AGENT = previous_user_agent
        SP_CACHED_CLIENT_ID = previous_client_id
        DEBUG_MODE = previous_debug_mode
    return True


# Runs extraction, validation, overwrite handling and atomic dotenv persistence
def run_browser_cookie_import(browser="firefox", browser_profile=None, cookie_file=None, env_file=None, force=False, interactive=None, input_func=None):
    destination = resolve_import_env_path(env_file)
    print(f"* Browser prerequisite: open {SPOTIFY_WEB_LOGIN_URL} in {browser_label(browser)} and sign in to the Spotify account used for monitoring")
    print(f"* Dotenv destination: {destination}")

    selected_system = platform.system()
    if browser in CHROMIUM_IMPORT_BROWSERS and selected_system == "Windows":
        raise BrowserCookieImportError(f"Importing {browser_label(browser)} cookies is unavailable on Windows because current Chromium app-bound cookie encryption prevents reliable external access. Use Firefox instead.")

    selected_profile = None
    if cookie_file is not None:
        selected_cookie_file = Path(cookie_file).expanduser()
        if browser_profile:
            print("* Note: --cookie-file takes precedence over --browser-profile")
    elif browser == "firefox":
        selected_profile = select_browser_profile(discover_firefox_profiles(), browser, requested_profile=browser_profile, interactive=interactive, input_func=input_func)
        selected_cookie_file = Path(selected_profile["cookie_file"])
    else:
        selected_profile = select_browser_profile(discover_chromium_profiles(browser), browser, requested_profile=browser_profile, interactive=interactive, input_func=input_func)
        selected_cookie_file = Path(selected_profile["cookie_file"])

    if selected_profile is not None:
        print(f"* Browser profile: {selected_profile['name']} [{selected_profile['dir']}]")
    print(f"* Cookie database: {selected_cookie_file}")

    sp_dc = read_firefox_sp_dc(selected_cookie_file) if browser == "firefox" else read_chromium_sp_dc(browser, selected_cookie_file)
    print("* Cookie extracted. Validating it with Spotify ...")
    validate_imported_sp_dc(sp_dc)
    print("* Spotify cookie validation succeeded")

    if _dotenv_contains_key(destination, "SP_DC_COOKIE") and not force:
        terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
        if not terminal_is_interactive:
            raise BrowserCookieImportError(f"Dotenv destination '{destination}' already contains SP_DC_COOKIE. Re-run with --force to replace it in a noninteractive environment.")
        prompt = input if input_func is None else input_func
        try:
            confirmed = prompt(f"Replace SP_DC_COOKIE in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except EOFError:
            confirmed = False
        if not confirmed:
            raise BrowserCookieImportError("Browser cookie import cancelled. The dotenv file was not changed.")

    print(f"* Writing SP_DC_COOKIE to: {destination}")
    try:
        update_dotenv_file(destination, {"SP_DC_COOKIE": sp_dc})
    except Exception:
        raise BrowserCookieImportError(f"Could not update dotenv destination '{destination}'. Check the path and file permissions.") from None
    print("* Browser cookie import completed successfully")
    if TOKEN_SOURCE == "client":
        print("* Note: TOKEN_SOURCE is set to client. Set it to cookie before the imported value will be used.")
    return str(destination)


# Validates and atomically stores one privately entered sp_dc cookie
def run_set_sp_dc(env_file=None, interactive=None, input_func=None, getpass_func=None, config_path=None) -> str:
    destination = resolve_import_env_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise BrowserCookieImportError("--set-sp-dc requires an interactive terminal. Run it from an interactive shell so the cookie can be entered through a hidden prompt.")

    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "SP_DC_COOKIE"):
        try:
            confirmed = prompt(f"Replace SP_DC_COOKIE in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            confirmed = False
        if not confirmed:
            raise BrowserCookieImportError("SP_DC_COOKIE replacement was cancelled. The dotenv file was not changed.")

    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        sp_dc = hidden_prompt("Enter sp_dc privately: ")
    except (EOFError, KeyboardInterrupt):
        raise BrowserCookieImportError("SP_DC_COOKIE entry was cancelled. The dotenv file was not changed.") from None
    if not isinstance(sp_dc, str) or not sp_dc:
        raise BrowserCookieImportError("No nonempty sp_dc cookie was entered. The dotenv file was not changed.")

    print("* Validating the entered Spotify cookie before changing the dotenv file ...")
    try:
        validate_imported_sp_dc(sp_dc)
    except Exception as exc:
        if _looks_like_network_failure(exc):
            raise BrowserCookieImportError("A network or connectivity failure prevented Spotify cookie validation. The dotenv file was not changed.") from None
        raise BrowserCookieImportError("The entered sp_dc cookie is invalid or expired. The dotenv file was not changed.") from None
    try:
        update_dotenv_file(destination, {"SP_DC_COOKIE": sp_dc})
    except Exception:
        raise BrowserCookieImportError(f"Could not update dotenv destination '{destination}'. Choose a writable path and check file permissions.") from None

    selected_config = config_path or find_config_file()
    method = _wizard_install_method()
    doctor_command = _wizard_action_command(method, "--doctor", selected_config, destination)
    monitor_command = _wizard_action_command(method, "", selected_config, destination, "SPOTIFY_USER_URI_ID")
    print("* SP_DC_COOKIE validation succeeded")
    print(f"* Updated dotenv: {destination}")
    _wizard_print_command("Check authentication:", doctor_command)
    _wizard_print_command("Start monitoring after replacing SPOTIFY_USER_URI_ID:", monitor_command)
    return str(destination)


# Validates and atomically stores one privately entered webhook URL
def run_set_webhook_url(env_file=None, interactive=None, input_func=None, getpass_func=None, config_path=None) -> str:
    try:
        destination = resolve_import_env_path(env_file)
    except BrowserCookieImportError as exc:
        raise WebhookConfigurationError(str(exc).replace("Browser cookie import", "Webhook setup")) from None
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise WebhookConfigurationError("--set-webhook-url requires an interactive terminal. Run it from an interactive shell so the URL can be entered through a hidden prompt.")
    prompt = input if input_func is None else input_func
    try:
        existing_assignment = _dotenv_contains_key(destination, "WEBHOOK_URL")
    except BrowserCookieImportError as exc:
        raise WebhookConfigurationError(str(exc)) from None
    if existing_assignment:
        try:
            confirmed = prompt(f"Replace WEBHOOK_URL in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            confirmed = False
        if not confirmed:
            raise WebhookConfigurationError("WEBHOOK_URL replacement was cancelled. The dotenv file was not changed.")
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        webhook_url = hidden_prompt("Enter webhook URL privately: ").strip()
    except (EOFError, KeyboardInterrupt):
        raise WebhookConfigurationError("WEBHOOK_URL entry was cancelled. The dotenv file was not changed.") from None
    if not validate_webhook_url(webhook_url):
        raise WebhookConfigurationError("The entered webhook URL is incomplete or is not HTTPS. The dotenv file was not changed.")
    try:
        update_dotenv_file(destination, {"WEBHOOK_URL": webhook_url})
    except Exception:
        raise WebhookConfigurationError(f"Could not update dotenv destination '{destination}'. Choose a writable path and check file permissions.") from None
    selected_config = config_path or find_config_file()
    method = _wizard_install_method()
    test_command = _wizard_action_command(method, "--send-test-webhook", selected_config, destination)
    doctor_command = _wizard_action_command(method, "--doctor", selected_config, destination)
    print("* WEBHOOK_URL format validation succeeded")
    print(f"* Updated dotenv: {destination}")
    _wizard_print_command("Send a test notification:", test_command)
    _wizard_print_command("Check the complete setup:", doctor_command)
    return str(destination)


class CappedRetry(Retry):
    def get_retry_after(self, response):
        retry_after = super().get_retry_after(response)
        if retry_after is None:
            return None
        return min(retry_after, MAX_RETRY_AFTER_SECONDS)


retry = CappedRetry(
    total=5,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "HEAD", "OPTIONS"],
    raise_on_status=False,
    respect_retry_after_header=True
)

adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)


# Truncates each line of a string to a specified number of characters including tab expansion and multi-line support
def truncate_string_per_line(message, truncate_width, tabsize=8):
    try:
        from wcwidth import wcwidth
    except ImportError:
        return message

    lines = message.split('\n')
    truncated_lines = []

    for line in lines:
        expanded_line = line.expandtabs(tabsize)
        current_width = 0
        truncated = ''

        for char in expanded_line:
            char_width = wcwidth(char)
            if char_width < 0:
                char_width = 0  # Non-printable or unknown width
            if current_width + char_width > truncate_width:
                break
            truncated += char
            current_width += char_width

        truncated_lines.append(truncated)

    return '\n'.join(truncated_lines)


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        # Expand tabs for file output (stdout remains untouched)
        self.logfile.write(message.expandtabs(8))
        if (TRUNCATE_CHARS):
            message = truncate_string_per_line(message, TRUNCATE_CHARS)
        self.terminal.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def terminal_only(self, message):
        if TRUNCATE_CHARS:
            message = truncate_string_per_line(message, TRUNCATE_CHARS)
        self.terminal.write(message)
        self.terminal.flush()

    def log_only(self, message):
        self.logfile.write(message.expandtabs(8))
        self.logfile.flush()

    def flush(self):
        self.terminal.flush()
        self.logfile.flush()


def flag_file_create():
    try:
        with open(FLAG_FILE, "w") as f:
            f.write("This indicates active streaming by monitored user")
    except Exception:
        pass


def flag_file_delete():
    try:
        if os.path.exists(FLAG_FILE):
            os.remove(FLAG_FILE)
    except Exception:
        pass


# Class used to generate timeout exceptions
class TimeoutException(Exception):
    pass


# Signal handler for SIGALRM when the operation times out
def timeout_handler(sig, frame):
    raise TimeoutException


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    if FLAG_FILE:
        flag_file_delete()
    sys.exit(0)


# Checks internet connectivity
def check_internet(url=CHECK_INTERNET_URL, timeout=CHECK_INTERNET_TIMEOUT, verify=VERIFY_SSL):
    try:
        debug_print(f"HTTP GET {url} [connectivity check], timeout={timeout}, verify_ssl={verify}")
        _ = req.get(url, headers={'User-Agent': USER_AGENT}, timeout=timeout, verify=verify)
        debug_print(f"HTTP GET {url} -> OK")
        return True
    except req.RequestException as e:
        debug_print(f"HTTP GET {url} -> failed: {e}")
        print_recovery_error(e, "connectivity")
        return False


# Clears the terminal screen
def clear_screen(enabled=True):
    if not enabled:
        return
    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        print("* Cannot clear the screen contents")


# Debug print helper - only prints when DEBUG_MODE is enabled
def debug_print(message):
    if DEBUG_MODE:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[DEBUG {timestamp}] {sanitize_error_text(message)}")


# Redacts a secret value for diagnostic output
def mask_secret(value, prefix=4, suffix=2):
    if value is None:
        return None
    if not str(value):
        return ""
    return "<redacted>"


# Redacts secret-bearing request parameters before debug output
def sanitize_debug_params(params):
    if not isinstance(params, dict):
        return params
    redacted_keys = {"totp", "totpServer", "refresh_token", "access_token"}
    out = {}
    for k, v in params.items():
        if k in redacted_keys:
            out[k] = mask_secret(v)
        else:
            out[k] = v
    return out


# Redacts secret-bearing request headers before debug output
def sanitize_debug_headers(headers):
    if not isinstance(headers, dict):
        return headers
    sensitive = {"authorization", "cookie", "client-token"}
    out = {}
    for k, v in headers.items():
        if str(k).lower() in sensitive:
            out[k] = mask_secret(v)
        else:
            out[k] = v
    return out


# Converts absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952),  # approximation
        ('months', 2629746),  # approximation
        ('weeks', 604800),    # 60 * 60 * 24 * 7
        ('days', 86400),      # 60 * 60 * 24
        ('hours', 3600),      # 60 * 60
        ('minutes', 60),
        ('seconds', 1),
    )
    result = []

    if seconds > 0:
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append(f"{value} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Calculates time span between two timestamps, accepts timestamp integers, floats and datetime objects
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if type(timestamp1) is int:
        dt1 = datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is float:
        ts1 = int(round(ts1))
        dt1 = datetime.fromtimestamp(ts1)
    elif type(timestamp1) is datetime:
        dt1 = timestamp1
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2 = datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is float:
        ts2 = int(round(ts2))
        dt2 = datetime.fromtimestamp(ts2)
    elif type(timestamp2) is datetime:
        dt2 = timestamp2
        ts2 = int(round(dt2.timestamp()))
    else:
        return ""

    if ts1 >= ts2:
        ts_diff = ts1 - ts2
    else:
        ts_diff = ts2 - ts1
        dt1, dt2 = dt2, dt1

    if ts_diff > 0:
        date_diff = relativedelta.relativedelta(dt1, dt2)
        years = date_diff.years
        months = date_diff.months
        weeks = date_diff.weeks
        if not show_weeks:
            weeks = 0
        days = date_diff.days
        if weeks > 0:
            days = days - (weeks * 7)
        hours = date_diff.hours
        if (not show_hours and ts_diff > 86400):
            hours = 0
        minutes = date_diff.minutes
        if (not show_minutes and ts_diff > 3600):
            minutes = 0
        seconds = date_diff.seconds
        if (not show_seconds and ts_diff > 60):
            seconds = 0
        date_list = [years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval > 0:
                name = intervals[index]
                if interval == 1:
                    name = name.rstrip('s')
                result.append(f"{interval} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Validates shared SMTP settings without opening a network connection
def validate_smtp_configuration() -> Optional[RecoveryAdvice]:
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            return classify_recovery_error(context="smtp_config", detail="SMTP_HOST is not a valid IP address or fully qualified domain name")

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except (TypeError, ValueError):
        return classify_recovery_error(context="smtp_config", detail="SMTP_PORT must be an integer from 1 through 65535")

    sender = parseaddr(str(SENDER_EMAIL))[1]
    receiver = parseaddr(str(RECEIVER_EMAIL))[1]
    if sender != str(SENDER_EMAIL) or receiver != str(RECEIVER_EMAIL) or "@" not in sender or "@" not in receiver:
        return classify_recovery_error(context="smtp_config", detail="SENDER_EMAIL or RECEIVER_EMAIL is invalid")

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        return classify_recovery_error(context="smtp_config", detail="SMTP_USER or SMTP_PASSWORD is missing or still a placeholder")
    return None


# Opens and authenticates one SMTP connection without sending an email
def smtp_connect_and_login(use_ssl, smtp_timeout=15):
    smtp_object = smtplib.SMTP(SMTP_HOST, int(SMTP_PORT), timeout=smtp_timeout)
    try:
        if use_ssl:
            smtp_object.starttls(context=ssl.create_default_context())
        smtp_object.login(SMTP_USER, SMTP_PASSWORD)
        return smtp_object
    except Exception:
        try:
            smtp_object.quit()
        except Exception:
            pass
        raise


# Sends email notification through the shared SMTP validation and login path
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    validation_error = validate_smtp_configuration()
    if validation_error is not None:
        print(render_recovery_error(RecoveryError(validation_error)))
        return 1

    if not subject or not isinstance(subject, str):
        print_recovery_error(context="smtp_config", detail="Email subject must be a nonempty string")
        return 1

    if not body and not body_html:
        print_recovery_error(context="smtp_config", detail="Email body and body_html cannot both be empty")
        return 1

    smtp_object = None
    try:
        smtp_object = smtp_connect_and_login(use_ssl, smtp_timeout)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = str(Header(subject, 'utf-8'))

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            email_msg.attach(part2)

        smtp_object.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtp_object.quit()
    except Exception as e:
        print_recovery_error(e, "smtp")
        return 1
    return 0


# Returns whether a webhook URL is a complete HTTPS endpoint without embedded credentials
def validate_webhook_url(url: Any = None) -> bool:
    selected_url = WEBHOOK_URL if url is None else url
    if not isinstance(selected_url, str) or not selected_url.strip():
        return False
    try:
        parsed = urlsplit(selected_url.strip())
    except ValueError:
        return False
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and bool(parsed.path.strip("/"))


# Returns whether one configured webhook event is enabled independently of email settings
def webhook_event_enabled(notification_type: str) -> bool:
    settings = {
        "active": WEBHOOK_ACTIVE_NOTIFICATION,
        "inactive": WEBHOOK_INACTIVE_NOTIFICATION,
        "track": WEBHOOK_TRACK_NOTIFICATION,
        "song": WEBHOOK_SONG_NOTIFICATION,
        "loop": WEBHOOK_SONG_ON_LOOP_NOTIFICATION,
        "error": WEBHOOK_ERROR_NOTIFICATION,
    }
    return bool(WEBHOOK_ENABLED and settings.get(notification_type, False))


# Parses a webhook rate-limit delay and caps untrusted server values to a short wait
def webhook_retry_after_seconds(response: Any) -> float:
    candidates: List[Any] = []
    headers = getattr(response, "headers", {}) or {}
    if hasattr(headers, "get"):
        candidates.append(headers.get("Retry-After"))
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        candidates.append(payload.get("retry_after"))
    for candidate in candidates:
        if candidate is None or candidate == "":
            continue
        try:
            seconds = float(candidate)
        except (TypeError, ValueError):
            try:
                retry_at = parsedate_to_datetime(str(candidate))
                seconds = (retry_at - datetime.now(retry_at.tzinfo)).total_seconds()
            except Exception:
                continue
        return max(0.0, min(seconds, WEBHOOK_MAX_RETRY_AFTER_SECONDS))
    return WEBHOOK_FALLBACK_RETRY_SECONDS


# Builds one bounded Discord embed without allowing notification text to trigger mentions
def build_webhook_payload(title: str, description: str, notification_type: str) -> dict:
    colors = {"active": 0x1DB954, "inactive": 0x747F8D, "track": 0x1DB954, "song": 0x3498DB, "loop": 0x9B59B6, "error": 0xE74C3C}
    safe_title = sanitize_error_text(title)[:WEBHOOK_EMBED_TITLE_LIMIT] or "Spotify Monitor"
    safe_description = sanitize_error_text(description)[:WEBHOOK_EMBED_DESCRIPTION_LIMIT]
    embed = {"title": safe_title, "description": safe_description, "color": colors.get(notification_type, 0x1DB954), "footer": {"text": f"Spotify Monitor v{VERSION}"}, "timestamp": datetime.now().astimezone().isoformat()}
    payload = {"allowed_mentions": {"parse": []}, "embeds": [embed]}
    if isinstance(WEBHOOK_USERNAME, str) and WEBHOOK_USERNAME.strip():
        payload["username"] = WEBHOOK_USERNAME.strip()[:80]
    return payload


# Sends one webhook through an isolated bounded retry path that never uses Spotify retries
def send_webhook(title: str, description: str, notification_type: str = "song", force: bool = False, sleeper: Optional[Callable[[float], None]] = None) -> int:
    if not force and not webhook_event_enabled(notification_type):
        return 1
    if not validate_webhook_url():
        print_recovery_error(context="webhook_config", detail="WEBHOOK_URL must be a complete HTTPS endpoint")
        return 1
    sleep_func = time.sleep if sleeper is None else sleeper
    payload = build_webhook_payload(title, description, notification_type)
    last_error: Any = None
    for attempt in range(WEBHOOK_MAX_ATTEMPTS):
        try:
            response = WEBHOOK_SESSION.post(str(WEBHOOK_URL).strip(), json=payload, headers={"User-Agent": f"SpotifyMonitor/{VERSION}"}, timeout=WEBHOOK_TIMEOUT_SECONDS)
            if 200 <= response.status_code <= 299:
                return 0
            last_error = response
            retryable = response.status_code == 429 or 500 <= response.status_code <= 599
            if not retryable or attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                detail = f"HTTP {response.status_code}: {sanitize_error_text(getattr(response, 'text', ''))[:200]}"
                print_recovery_error(response, "webhook", detail=detail)
                return 1
            delay = webhook_retry_after_seconds(response) if response.status_code == 429 else WEBHOOK_FALLBACK_RETRY_SECONDS
            debug_print(f"Webhook delivery returned HTTP {response.status_code}. Retrying once in {delay:g} seconds")
            sleep_func(delay)
        except req.RequestException as exc:
            last_error = exc
            if attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                print_recovery_error(exc, "webhook")
                return 1
            debug_print(f"Webhook delivery failed. Retrying once in {WEBHOOK_FALLBACK_RETRY_SECONDS:g} seconds: {sanitize_error_text(exc)}")
            sleep_func(WEBHOOK_FALLBACK_RETRY_SECONDS)
    print_recovery_error(last_error, "webhook")
    return 1


# Delivers one semantic notification to enabled email and webhook channels independently
def send_notification_channels(notification_type: str, subject: str, body: str, body_html: str = "", email_enabled: bool = False, webhook_enabled: Optional[bool] = None) -> tuple[bool, bool]:
    email_attempted = bool(email_enabled)
    webhook_attempted = webhook_event_enabled(notification_type) if webhook_enabled is None else bool(webhook_enabled)
    if email_attempted:
        print(f"Sending email notification to {RECEIVER_EMAIL}")
        send_email(subject, body, body_html, SMTP_SSL)
    if webhook_attempted:
        print("Sending Discord-compatible webhook notification")
        send_webhook(subject, body, notification_type, force=True)
    return email_attempted, webhook_attempted


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")


# Writes CSV entry
def write_csv_entry(csv_file_name, timestamp, artist, track, playlist, album, last_activity_ts):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Date': timestamp, 'Artist': artist, 'Track': track, 'Playlist': playlist, 'Album': album, 'Last activity': last_activity_ts})

    except Exception as e:
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]} {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


# Prints the current date/time in human readable format with separator; eg. Sun 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("─" * HORIZONTAL_LINE)


# Returns the timestamp/datetime object in human readable format (long version); eg. Sun 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime("%d %b %Y, %H:%M:%S")}')


# Prints one sanitized operational event only when verbose mode is enabled
def verbose_print(message: Any) -> None:
    if VERBOSE_MODE:
        print(f"* {sanitize_error_text(message)}")


# Logs the start of one monitoring poll only when debug mode is enabled
def debug_monitor_check_start(check_number: int, user: str, started_at: Optional[datetime] = None) -> datetime:
    check_started_at = started_at or datetime.now()
    debug_print(f"Starting check #{check_number} for {user}")
    return check_started_at


# Logs one completed poll plus its last and next timing details in debug mode
def debug_monitor_check_timing(check_number: int, user: str, started_at: datetime, sleep_time: int, completed_at: Optional[datetime] = None) -> None:
    if not DEBUG_MODE:
        return
    check_completed_at = completed_at or datetime.now()
    next_check = check_completed_at + timedelta(seconds=sleep_time)
    debug_print(f"Check #{check_number} completed for {user}, last={get_date_from_ts(started_at)}, next={get_date_from_ts(next_check)}, interval={display_time(sleep_time)}")


# Logs the exact time of a scheduled target visibility retry in debug mode
def debug_monitor_wait_timing(user: str, sleep_time: int, current_time: Optional[datetime] = None) -> None:
    if not DEBUG_MODE:
        return
    now = current_time or datetime.now()
    next_check = now + timedelta(seconds=sleep_time)
    debug_print(f"Next visibility check for {user}: {get_date_from_ts(next_check)}, interval={display_time(sleep_time)}")


# Returns the timestamp/datetime object in human readable format (short version); eg.
# Sun 21 Apr 15:08
# Sun 21 Apr 24, 15:08 (if show_year == True and current year is different)
# Sun 21 Apr (if show_hour == False)
def get_short_date_from_ts(ts, show_year=False, show_hour=True):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M"
    else:
        hour_strftime = ""

    if show_year and int(datetime.fromtimestamp(ts_new).strftime("%Y")) != int(datetime.now().strftime("%Y")):
        if show_hour:
            hour_prefix = ","
        else:
            hour_prefix = ""
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}')
    else:
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b{hour_strftime}")}')


# Returns the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_seconds:
        out_strf = "%H:%M:%S"
    else:
        out_strf = "%H:%M"
    return (str(datetime.fromtimestamp(ts_new).strftime(out_strf)))


# Returns the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    if type(ts1) is datetime:
        ts1_new = int(round(ts1.timestamp()))
    elif type(ts1) is int:
        ts1_new = ts1
    elif type(ts1) is float:
        ts1_new = int(round(ts1))
    else:
        return ""

    if type(ts2) is datetime:
        ts2_new = int(round(ts2.timestamp()))
    elif type(ts2) is int:
        ts2_new = ts2
    elif type(ts2) is float:
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_short_date_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_date_from_ts(ts2_new)}"
    return (str(out_str))


# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global ACTIVE_NOTIFICATION
    global INACTIVE_NOTIFICATION
    ACTIVE_NOTIFICATION = not ACTIVE_NOTIFICATION
    INACTIVE_NOTIFICATION = not INACTIVE_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active = {ACTIVE_NOTIFICATION}] [inactive = {INACTIVE_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGUSR2 allowing to switch every song email notifications
def toggle_song_notifications_signal_handler(sig, frame):
    global SONG_NOTIFICATION
    SONG_NOTIFICATION = not SONG_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [every song = {SONG_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGCONT allowing to switch tracked songs email notifications
def toggle_track_notifications_signal_handler(sig, frame):
    global TRACK_NOTIFICATION
    TRACK_NOTIFICATION = not TRACK_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [tracked = {TRACK_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGPIPE allowing to switch songs on loop email notifications
def toggle_songs_on_loop_notifications_signal_handler(sig, frame):
    global SONG_ON_LOOP_NOTIFICATION
    SONG_ON_LOOP_NOTIFICATION = not SONG_ON_LOOP_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [songs on loop = {SONG_ON_LOOP_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGTRAP allowing to increase inactivity check timer by SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE seconds
def increase_inactivity_check_signal_handler(sig, frame):
    global SPOTIFY_INACTIVITY_CHECK
    SPOTIFY_INACTIVITY_CHECK = SPOTIFY_INACTIVITY_CHECK + SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Spotify timers: [inactivity: {display_time(SPOTIFY_INACTIVITY_CHECK)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGABRT allowing to decrease inactivity check timer by SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE seconds
def decrease_inactivity_check_signal_handler(sig, frame):
    global SPOTIFY_INACTIVITY_CHECK
    if SPOTIFY_INACTIVITY_CHECK - SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE > 0:
        SPOTIFY_INACTIVITY_CHECK = SPOTIFY_INACTIVITY_CHECK - SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Spotify timers: [inactivity: {display_time(SPOTIFY_INACTIVITY_CHECK)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGHUP allowing to reload secrets from dotenv files and token source credentials
# from login & client token requests body files
def reload_secrets_signal_handler(sig, frame):
    global DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN, LOGIN_URL, USER_AGENT, APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL

    sig_name = signal.Signals(sig).name

    print(f"* Signal {sig_name} received\n")

    suffix = "\n" if TOKEN_SOURCE == 'client' else ""

    # disable autoscan if DOTENV_FILE set to none
    env_path = None
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        # reload .env if python-dotenv is installed
        try:
            from dotenv import load_dotenv, find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                load_dotenv(env_path, override=True, interpolate=False)
            else:
                print(f"* No .env file found, skipping env-var reload{suffix}")
        except ImportError:
            env_path = None
            print(f"* python-dotenv not installed, skipping env-var reload{suffix}")

    if env_path:
        for secret in SECRET_KEYS:
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                print(f"* Reloaded {secret} from {env_path}{suffix}")

    if TOKEN_SOURCE == 'client':

        # Process the login request body file
        if LOGIN_REQUEST_BODY_FILE:
            if os.path.isfile(LOGIN_REQUEST_BODY_FILE):
                try:
                    DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN = parse_login_request_body_file(LOGIN_REQUEST_BODY_FILE)
                except Exception as e:
                    print_recovery_error(e, "file_read", detail=f"Login Protobuf file '{LOGIN_REQUEST_BODY_FILE}' cannot be processed: {e}")
                else:
                    print(f"* Login data correctly read from Protobuf file ({LOGIN_REQUEST_BODY_FILE}):")
                    print(" - Device ID:\t\t", DEVICE_ID)
                    print(" - System ID:\t\t", SYSTEM_ID)
                    print(" - User URI ID:\t\t", USER_URI_ID)
                    print(" - Refresh Token:\t<<hidden>>\n")
            else:
                print(f"* Error: Protobuf file ({LOGIN_REQUEST_BODY_FILE}) does not exist")

        # Process the client token request body file
        if CLIENTTOKEN_REQUEST_BODY_FILE:
            if os.path.isfile(CLIENTTOKEN_REQUEST_BODY_FILE):
                try:
                    (APP_VERSION, _, _, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL) = parse_clienttoken_request_body_file(CLIENTTOKEN_REQUEST_BODY_FILE)
                except Exception as e:
                    print_recovery_error(e, "file_read", detail=f"Client-token Protobuf file '{CLIENTTOKEN_REQUEST_BODY_FILE}' cannot be processed: {e}")
                else:
                    print(f"* Client token data correctly read from Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}):")
                    print(" - App version:\t\t", APP_VERSION)
                    print(" - CPU arch:\t\t", CPU_ARCH)
                    print(" - OS build:\t\t", OS_BUILD)
                    print(" - Platform:\t\t", PLATFORM)
                    print(" - OS major:\t\t", OS_MAJOR)
                    print(" - OS minor:\t\t", OS_MINOR)
                    print(" - Client model:\t", CLIENT_MODEL, "\n")
            else:
                print(f"* Error: Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}) does not exist")

    print_cur_ts("Timestamp:\t\t\t")


# Returns Apple & lyrics search URLs for specified track
def get_apple_genius_search_urls(artist, track):
    spotify_search_string = f"{artist} {track}"
    youtube_music_search_string = quote_plus(spotify_search_string)
    # Clean search string for lyrics services (remove remaster, extended, etc.)
    lyrics_search_string = spotify_search_string
    if re.search(re_search_str, lyrics_search_string, re.IGNORECASE):
        lyrics_search_string = re.sub(re_replace_str, '', lyrics_search_string, flags=re.IGNORECASE)
    apple_search_string = quote(spotify_search_string)
    apple_search_url = f"https://music.apple.com/pl/search?term={apple_search_string}"
    genius_search_url = f"https://genius.com/search?q={quote_plus(lyrics_search_string)}"
    azlyrics_search_url = f"https://www.azlyrics.com/search/?q={quote_plus(lyrics_search_string)}"
    tekstowo_search_url = f"https://www.tekstowo.pl/szukaj,{quote_plus(lyrics_search_string)}.html"
    musixmatch_search_url = f"https://www.musixmatch.com/search?query={quote_plus(lyrics_search_string)}"
    lyrics_com_search_url = f"https://www.lyrics.com/serp.php?st={quote_plus(lyrics_search_string)}&qtype=1"
    youtube_music_search_url = f"https://music.youtube.com/search?q={youtube_music_search_string}"
    amazon_music_search_url = f"https://music.amazon.com/search/{quote_plus(spotify_search_string)}"
    deezer_search_url = f"https://www.deezer.com/search/{quote_plus(spotify_search_string)}"
    tidal_search_url = f"https://tidal.com/search?q={quote_plus(spotify_search_string)}"
    return apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url


# Formats lyrics URLs for console output based on configuration
def format_lyrics_urls_console(genius_url, azlyrics_url, tekstowo_url, musixmatch_url, lyrics_com_url):
    lines = []
    if ENABLE_GENIUS_LYRICS_URL:
        lines.append(f"Genius lyrics URL:\t\t{genius_url}")
    if ENABLE_AZLYRICS_URL:
        lines.append(f"AZLyrics URL:\t\t\t{azlyrics_url}")
    if ENABLE_TEKSTOWO_URL:
        lines.append(f"Tekstowo.pl URL:\t\t{tekstowo_url}")
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f"Musixmatch URL:\t\t\t{musixmatch_url}")
    if ENABLE_LYRICS_COM_URL:
        lines.append(f"Lyrics.com URL:\t\t\t{lyrics_com_url}")
    return "\n".join(lines) if lines else ""


# Formats lyrics URLs for plain text email body based on configuration
def format_lyrics_urls_email_text(genius_url, azlyrics_url, tekstowo_url, musixmatch_url, lyrics_com_url):
    lines = []
    if ENABLE_GENIUS_LYRICS_URL:
        lines.append(f"Genius lyrics URL: {genius_url}")
    if ENABLE_AZLYRICS_URL:
        lines.append(f"AZLyrics URL: {azlyrics_url}")
    if ENABLE_TEKSTOWO_URL:
        lines.append(f"Tekstowo.pl URL: {tekstowo_url}")
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f"Musixmatch URL: {musixmatch_url}")
    if ENABLE_LYRICS_COM_URL:
        lines.append(f"Lyrics.com URL: {lyrics_com_url}")
    return "\n".join(lines) if lines else ""


# Formats lyrics URLs for HTML email body based on configuration
def format_lyrics_urls_email_html(genius_url, azlyrics_url, tekstowo_url, musixmatch_url, lyrics_com_url, artist, track):
    lines = []
    escaped_artist = escape(artist)
    escaped_track = escape(track)
    if ENABLE_GENIUS_LYRICS_URL:
        lines.append(f'Genius lyrics URL: <a href="{genius_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_AZLYRICS_URL:
        lines.append(f'AZLyrics URL: <a href="{azlyrics_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_TEKSTOWO_URL:
        lines.append(f'Tekstowo.pl URL: <a href="{tekstowo_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_MUSIXMATCH_URL:
        lines.append(f'Musixmatch URL: <a href="{musixmatch_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_LYRICS_COM_URL:
        lines.append(f'Lyrics.com URL: <a href="{lyrics_com_url}">{escaped_artist} - {escaped_track}</a>')
    return "<br>".join(lines) if lines else ""


# Formats music service URLs for console output based on configuration
def format_music_urls_console(apple_music_url, youtube_music_url, amazon_music_url, deezer_url, tidal_url):
    lines = []
    if ENABLE_APPLE_MUSIC_URL:
        lines.append(f"Apple Music URL:\t\t{apple_music_url}")
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f"YouTube Music URL:\t\t{youtube_music_url}")
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f"Amazon Music URL:\t\t{amazon_music_url}")
    if ENABLE_DEEZER_URL:
        lines.append(f"Deezer URL:\t\t\t{deezer_url}")
    if ENABLE_TIDAL_URL:
        lines.append(f"Tidal URL:\t\t\t{tidal_url}")
    return "\n".join(lines) if lines else ""


# Formats music service URLs for plain text email body based on configuration
def format_music_urls_email_text(apple_music_url, youtube_music_url, amazon_music_url, deezer_url, tidal_url):
    lines = []
    if ENABLE_APPLE_MUSIC_URL:
        lines.append(f"Apple Music URL: {apple_music_url}")
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f"YouTube Music URL: {youtube_music_url}")
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f"Amazon Music URL: {amazon_music_url}")
    if ENABLE_DEEZER_URL:
        lines.append(f"Deezer URL: {deezer_url}")
    if ENABLE_TIDAL_URL:
        lines.append(f"Tidal URL: {tidal_url}")
    return "\n".join(lines) if lines else ""


# Formats music service URLs for HTML email body based on configuration
def format_music_urls_email_html(apple_music_url, youtube_music_url, amazon_music_url, deezer_url, tidal_url, artist, track):
    lines = []
    escaped_artist = escape(artist)
    escaped_track = escape(track)
    if ENABLE_APPLE_MUSIC_URL:
        lines.append(f'Apple Music URL: <a href="{apple_music_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_YOUTUBE_MUSIC_URL:
        lines.append(f'YouTube Music URL: <a href="{youtube_music_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_AMAZON_MUSIC_URL:
        lines.append(f'Amazon Music URL: <a href="{amazon_music_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_DEEZER_URL:
        lines.append(f'Deezer URL: <a href="{deezer_url}">{escaped_artist} - {escaped_track}</a>')
    if ENABLE_TIDAL_URL:
        lines.append(f'Tidal URL: <a href="{tidal_url}">{escaped_artist} - {escaped_track}</a>')
    return "<br>".join(lines) if lines else ""


# Sends a lightweight request to check Spotify token validity
def check_token_validity(access_token: str, client_id: Optional[str] = None, user_agent: Optional[str] = None, oauth_app: Optional[bool] = False) -> bool:
    url1 = "https://guc-spclient.spotify.com/presence-view/v1/buddylist"
    # Use a known stable track for validation (Bohemian Rhapsody - Queen)
    url2 = "https://api.spotify.com/v1/tracks/7tFiyTwD0nx5a1eklYtX2J"

    url = url2 if oauth_app else url1
    check_mode = "oauth_app" if oauth_app else f"{TOKEN_SOURCE}_token"

    headers = {"Authorization": f"Bearer {access_token}"}

    if user_agent is not None:
        headers.update({
            "User-Agent": user_agent
        })

    if not oauth_app and TOKEN_SOURCE == "cookie" and client_id is not None:
        headers.update({
            "Client-Id": client_id
        })

    if platform.system() != 'Windows':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT + 2)
    try:
        debug_print(
            f"Token validity check mode={check_mode}, url={url}, "
            f"client_id_header={'yes' if 'Client-Id' in headers else 'no'}"
        )
        debug_print(f"HTTP GET {url} [token validity] headers={sanitize_debug_headers(headers)}")
        response = req.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        valid = response.status_code == 200 or bool(oauth_app and response.status_code == 403)
        debug_print(f"HTTP GET {url} -> {response.status_code} [token validity mode={check_mode}] (valid={valid})")
    except Exception:
        valid = False
        debug_print(f"HTTP GET {url} -> failed during token validity check [mode={check_mode}]")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)
    return valid


# -------------------------------------------------------
# Supporting functions when token source is set to cookie
# -------------------------------------------------------

# Returns random user agent string
def get_random_user_agent() -> str:
    browser = random.choice(['chrome', 'firefox', 'edge', 'safari'])

    if browser == 'chrome':
        os_choice = random.choice(['mac', 'windows'])
        if os_choice == 'mac':
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(4, 9)}) "
                f"AppleWebKit/{random.randrange(530, 537)}.{random.randrange(30, 37)} (KHTML, like Gecko) "
                f"Chrome/{random.randrange(80, 105)}.0.{random.randrange(3000, 4500)}.{random.randrange(60, 125)} "
                f"Safari/{random.randrange(530, 537)}.{random.randrange(30, 36)}"
            )
        else:
            chrome_version = random.randint(80, 105)
            build = random.randint(3000, 4500)
            patch = random.randint(60, 125)
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{chrome_version}.0.{build}.{patch} Safari/537.36"
            )

    elif browser == 'firefox':
        os_choice = random.choice(['windows', 'mac', 'linux'])
        version = random.randint(90, 110)
        if os_choice == 'windows':
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )
        elif os_choice == 'mac':
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(0, 10)}; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )
        else:
            return (
                f"Mozilla/5.0 (X11; Linux x86_64; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )

    elif browser == 'edge':
        os_choice = random.choice(['windows', 'mac'])
        chrome_version = random.randint(80, 105)
        build = random.randint(3000, 4500)
        patch = random.randint(60, 125)
        version_str = f"{chrome_version}.0.{build}.{patch}"
        if os_choice == 'windows':
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{version_str} Safari/537.36 Edg/{version_str}"
            )
        else:
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(0, 10)}) "
                f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"Version/{random.randint(13, 16)}.0 Safari/605.1.15 Edg/{version_str}"
            )

    elif browser == 'safari':
        os_choice = 'mac'
        if os_choice == 'mac':
            mac_major = random.randrange(11, 16)
            mac_minor = random.randrange(0, 10)
            webkit_major = random.randint(600, 610)
            webkit_minor = random.randint(1, 20)
            webkit_patch = random.randint(1, 20)
            safari_version = random.randint(13, 16)
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{mac_major}_{mac_minor}) "
                f"AppleWebKit/{webkit_major}.{webkit_minor}.{webkit_patch} (KHTML, like Gecko) "
                f"Version/{safari_version}.0 Safari/{webkit_major}.{webkit_minor}.{webkit_patch}"
            )
        else:
            return ""
    else:
        return ""


# Returns Spotify edge-server Unix time
def fetch_server_time(session: req.Session, ua: str) -> int:

    headers = {
        "User-Agent": ua,
        "Accept": "*/*",
    }

    try:
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)
        debug_print(f"HTTP HEAD {SERVER_TIME_URL} [server time] timeout={FUNCTION_TIMEOUT}")
        response = session.head(SERVER_TIME_URL, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        debug_print(f"HTTP HEAD {SERVER_TIME_URL} -> {response.status_code}")
    except TimeoutException as e:
        raise Exception(f"fetch_server_time() head network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        raise Exception(f"fetch_server_time() head network request error: {e}")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

    date_hdr = response.headers.get("Date")
    if not date_hdr:
        raise Exception("fetch_server_time() missing 'Date' header")

    return int(parsedate_to_datetime(date_hdr).timestamp())


# Creates a TOTP object using the fixed web-player v61 cipher bytes
def generate_totp():
    import pyotp

    transformed = [value ^ ((index % 33) + 9) for index, value in enumerate(TOTP_SECRET_CIPHER_BYTES)]
    joined = "".join(str(num) for num in transformed)
    hex_str = joined.encode().hex()
    secret = base64.b32encode(bytes.fromhex(hex_str)).decode().rstrip("=")

    return pyotp.TOTP(secret, digits=6, interval=30)


# Refreshes the Spotify access token using the sp_dc cookie, tries first with mode "transport" and if needed with "init"
def refresh_access_token_from_sp_dc(sp_dc: str) -> dict:
    transport = True
    init = True
    session = req.Session()
    data: dict = {}
    token = ""

    server_time = fetch_server_time(session, USER_AGENT)
    totp_obj = generate_totp()
    otp_value = totp_obj.at(server_time)

    params = {
        "reason": "transport",
        "productType": "web-player",
        "totp": otp_value,
        "totpServer": otp_value,
        "totpVer": TOTP_VERSION,
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Referer": "https://open.spotify.com/",
        "App-Platform": "WebPlayer",
        "Cookie": f"sp_dc={sp_dc}",
    }

    last_err = ""

    try:
        if platform.system() != "Windows":
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)

        debug_print(f"HTTP GET {TOKEN_URL} [sp_dc transport] params={sanitize_debug_params(params)} headers={sanitize_debug_headers(headers)}")
        response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        data = response.json()
        token = data.get("accessToken", "")
        debug_print(f"HTTP GET {TOKEN_URL} [sp_dc transport] -> {response.status_code}, token_len={len(token)}")

    except (req.RequestException, TimeoutException, req.HTTPError, ValueError) as e:
        transport = False
        last_err = str(e)
        debug_print(f"HTTP GET {TOKEN_URL} [sp_dc transport] failed: {e}")
    finally:
        if platform.system() != "Windows":
            signal.alarm(0)

    if not transport or (sp_dc and not check_token_validity(token, data.get("clientId", ""), USER_AGENT)):
        params["reason"] = "init"

        try:
            if platform.system() != "Windows":
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(FUNCTION_TIMEOUT + 2)

            debug_print(f"HTTP GET {TOKEN_URL} [sp_dc init] params={sanitize_debug_params(params)} headers={sanitize_debug_headers(headers)}")
            response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            response.raise_for_status()
            data = response.json()
            token = data.get("accessToken", "")
            debug_print(f"HTTP GET {TOKEN_URL} [sp_dc init] -> {response.status_code}, token_len={len(token)}")

        except (req.RequestException, TimeoutException, req.HTTPError, ValueError) as e:
            init = False
            last_err = str(e)
            debug_print(f"HTTP GET {TOKEN_URL} [sp_dc init] failed: {e}")
        finally:
            if platform.system() != "Windows":
                signal.alarm(0)

    if not init or not data or "accessToken" not in data:
        raise Exception(f"refresh_access_token_from_sp_dc(): Unsuccessful token request{': ' + last_err if last_err else ''}")

    return {
        "access_token": token,
        "expires_at": data["accessTokenExpirationTimestampMs"] // 1000,
        "client_id": data.get("clientId", ""),
        "length": len(token)
    }


# Fetches Spotify access token based on provided SP_DC value
def spotify_get_access_token_from_sp_dc(sp_dc: str):
    global SP_CACHED_ACCESS_TOKEN, SP_ACCESS_TOKEN_EXPIRES_AT, SP_CACHED_CLIENT_ID

    now = time.time()

    if SP_CACHED_ACCESS_TOKEN and now < SP_ACCESS_TOKEN_EXPIRES_AT and check_token_validity(SP_CACHED_ACCESS_TOKEN, SP_CACHED_CLIENT_ID, USER_AGENT):
        debug_print("Using cached Spotify access token (sp_dc source)")
        return SP_CACHED_ACCESS_TOKEN

    max_retries = TOKEN_MAX_RETRIES
    retry = 0

    last_error = ""

    while retry < max_retries:
        try:
            debug_print(f"Refreshing Spotify access token via sp_dc (attempt {retry + 1}/{max_retries})")
            token_data = refresh_access_token_from_sp_dc(sp_dc)
            token = token_data["access_token"]
            client_id = token_data.get("client_id", "")
            length = token_data["length"]

            SP_CACHED_ACCESS_TOKEN = token
            SP_ACCESS_TOKEN_EXPIRES_AT = token_data["expires_at"]
            SP_CACHED_CLIENT_ID = client_id

            if SP_CACHED_ACCESS_TOKEN is None or not check_token_validity(SP_CACHED_ACCESS_TOKEN, SP_CACHED_CLIENT_ID, USER_AGENT):
                debug_print("Received token is invalid, retrying")
                retry += 1
                time.sleep(TOKEN_RETRY_TIMEOUT)
            else:
                debug_print(f"Spotify access token obtained successfully, length={length}")
                verbose_print("Authentication token refreshed (cookie mode)")
                break
        except Exception as e:
            last_error = str(e)
            debug_print(f"Token refresh attempt failed: {e}")
            retry += 1
            if retry < max_retries:
                time.sleep(TOKEN_RETRY_TIMEOUT)

    if retry == max_retries:

        error_msg = f"Failed to obtain a valid Spotify access token after {max_retries} attempts"
        if last_error:
            error_msg += f": {last_error}"
        raise RuntimeError(error_msg)

    return SP_CACHED_ACCESS_TOKEN


# -------------------------------------------------------
# Supporting functions when token source is set to client
# -------------------------------------------------------

# Returns random Spotify client user agent string
def get_random_spotify_user_agent() -> str:
    os_choice = random.choice(['windows', 'mac', 'linux'])

    if os_choice == 'windows':
        build = random.randint(120000000, 130000000)
        arch = random.choice(['Win32', 'Win32_x86_64'])
        device = random.choice(['desktop', 'laptop'])
        return f"Spotify/{build} {arch}/0 (PC {device})"

    elif os_choice == 'mac':
        build = random.randint(120000000, 130000000)
        arch = random.choice(['OSX_ARM64', 'OSX_X86_64'])
        major = random.randint(10, 15)
        minor = random.randint(0, 7)
        patch = random.randint(0, 5)
        os_version = f"OS X {major}.{minor}.{patch}"
        if arch == 'OSX_ARM64':
            bracket = f"[arm {random.randint(1, 3)}]"
        else:
            bracket = "[x86_64]"
        return f"Spotify/{build} {arch}/{os_version} {bracket}"

    else:  # linux
        build = random.randint(120000000, 130000000)
        arch = random.choice(['Linux; x86_64', 'Linux; x86'])
        return f"Spotify/{build} ({arch})"


# Encodes an integer using Protobuf varint format
def encode_varint(value):
    result = bytearray()
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value //= 128
    result.append(value)
    return bytes(result)


# Encodes a string field with the given tag
def encode_string_field(tag, value):
    key = encode_varint((tag << 3) | 2)  # wire type 2 (length-delimited)
    value_bytes = value.encode('utf-8')
    length = encode_varint(len(value_bytes))
    return key + length + value_bytes


# Encodes a nested message field with the given tag
def encode_nested_field(tag, nested_bytes):
    key = encode_varint((tag << 3) | 2)
    length = encode_varint(len(nested_bytes))
    return key + length + nested_bytes


# Builds the Spotify Protobuf login request body
def build_spotify_auth_protobuf(device_id, system_id, user_uri_id, refresh_token):
    """
    {
      1: {
           1: "device_id",
           2: "system_id"
         },
      100: {
           1: "user_uri_id",
           2: "refresh_token"
         }
    }
    """
    device_info_msg = encode_string_field(1, device_id) + encode_string_field(2, system_id)
    field_device_info = encode_nested_field(1, device_info_msg)

    user_auth_msg = encode_string_field(1, user_uri_id) + encode_string_field(2, refresh_token)
    field_user_auth = encode_nested_field(100, user_auth_msg)

    return field_device_info + field_user_auth


# Reads a varint from data starting at index
def read_varint(data, index):
    shift = 0
    result = 0
    bytes_read = 0
    while True:
        b = data[index]
        result |= ((b & 0x7F) << shift)
        bytes_read += 1
        index += 1
        if not (b & 0x80):
            break
        shift += 7
    return result, bytes_read


# Parses Spotify Protobuf login response
def parse_protobuf_message(data):
    index = 0
    result = {}
    while index < len(data):
        try:
            key, key_len = read_varint(data, index)
        except IndexError:
            break
        index += key_len
        tag = key >> 3
        wire_type = key & 0x07
        if wire_type == 2:  # length-delimited
            length, len_len = read_varint(data, index)
            index += len_len
            raw_value = data[index:index + length]
            index += length
            # If the first byte is a control character (e.g. 0x0A) assume nested
            if raw_value and raw_value[0] < 0x20:
                value = parse_protobuf_message(raw_value)
            else:
                try:
                    value = raw_value.decode('utf-8')
                except UnicodeDecodeError:
                    value = raw_value
            result[tag] = value
        elif wire_type == 0:  # varint
            value, var_len = read_varint(data, index)
            index += var_len
            result[tag] = value
        else:
            break
    return result  # dictionary mapping tags to values


# Parses the Protobuf-encoded login request body file (as dumped for example by Proxyman) and returns a tuple:
# (device_id, system_id, user_uri_id, refresh_token)
def parse_login_request_body_file(file_path):
    """
    {
      1: {
           1: "device_id",
           2: "system_id"
         },
      100: {
           1: "user_uri_id",
           2: "refresh_token"
         }
    }
    """
    with open(file_path, "rb") as f:
        data = f.read()
    parsed = parse_protobuf_message(data)

    device_id = None
    system_id = None
    user_uri_id = None
    refresh_token = None

    if 1 in parsed:
        device_info = parsed[1]
        if isinstance(device_info, dict):
            device_id = device_info.get(1)
            system_id = device_info.get(2)
        else:
            pass

    if 100 in parsed:
        user_auth = parsed[100]
        if isinstance(user_auth, dict):
            user_uri_id = user_auth.get(1)
            refresh_token = user_auth.get(2)

    protobuf_fields = {
        "device_id": device_id,
        "system_id": system_id,
        "user_uri_id": user_uri_id,
        "refresh_token": refresh_token,
    }

    protobuf_missing_fields = [name for name, value in protobuf_fields.items() if value is None]

    if protobuf_missing_fields:
        missing_str = ", ".join(protobuf_missing_fields)
        raise Exception(f"Following fields could not be extracted: {missing_str}")

    return device_id, system_id, user_uri_id, refresh_token


# Recursively flattens nested dictionaries or lists into a single string
def deep_flatten(value):
    if isinstance(value, dict):
        return "".join(deep_flatten(v) for k, v in sorted(value.items()))
    elif isinstance(value, list):
        return "".join(deep_flatten(item) for item in value)
    else:
        return str(value)


# Returns the input if it's a dict, parses as Protobuf it if it's bytes or returns an empty dict otherwise
def ensure_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            return parse_protobuf_message(value)
        except Exception:
            return {}
    return {}


# Parses the Protobuf-encoded client token request body file (as dumped for example by Proxyman) and returns a tuple:
# (app_version, device_id, system_id, cpu_arch, os_build, platform, os_major, os_minor, client_model)
def parse_clienttoken_request_body_file(file_path):
    """
        1: 1 (const)
        2: {
          1: "app_version"
          2: "device_id"
          3: {
            1: {
              4: {
                1: "cpu_arch"
                3: "os_build"
                4: "platform"
                5: "os_major"
                6: "os_minor"
                8: "client_model"
              }
            }
            2: "system_id"
          }
        }
    """

    with open(file_path, "rb") as f:
        data = f.read()

    root = ensure_dict(parse_protobuf_message(data).get(2))

    app_version = root.get(1)
    device_id = root.get(2)

    nested_3 = ensure_dict(root.get(3))
    nested_1 = ensure_dict(nested_3.get(1))
    nested_4 = ensure_dict(nested_1.get(4))

    cpu_arch = nested_4.get(1)
    os_build = nested_4.get(3)
    platform = nested_4.get(4)
    os_major = nested_4.get(5)
    os_minor = nested_4.get(6)
    client_model = nested_4.get(8)

    system_id = nested_3.get(2)

    required = {
        "app_version": app_version,
        "device_id": device_id,
        "system_id": system_id,
    }
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise Exception(f"Could not extract fields: {', '.join(missing)}")

    return (app_version, device_id, system_id, cpu_arch, os_build, platform, os_major, os_minor, client_model)


# Converts Spotify user agent string to Protobuf app_version string
# For example: 'Spotify/126200580 Win32_x86_64/0 (PC desktop)' to '1.2.62.580.g<random-hex>'
def ua_to_app_version(user_agent: str) -> str:

    m = re.search(r"Spotify/(\d{5,})", user_agent)
    if not m:
        raise ValueError(f"User-Agent missing build number: {user_agent!r}")

    digits = m.group(1)
    if len(digits) < 5:
        raise ValueError(f"Build number too short: {digits}")

    major = digits[0]
    minor = digits[1]
    patch = str(int(digits[2:4]))
    build = str(int(digits[4:]))
    suffix = secrets.token_hex(4)

    return f"{major}.{minor}.{patch}.{build}.g{suffix}"


# Builds the Protobuf client token request body
def build_clienttoken_request_protobuf(app_version, device_id, system_id, cpu_arch=10, os_build=19045, platform=2, os_major=9, os_minor=9, client_model=34404):
    """
        1: 1 (const)
        2: {
          1: "app_version"
          2: "device_id"
          3: {
            1: {
              4: {
                1: "cpu_arch"
                3: "os_build"
                4: "platform"
                5: "os_major"
                6: "os_minor"
                8: "client_model"
              }
            }
            2: "system_id"
          }
        }
    """

    leaf = (
        encode_varint((1 << 3) | 0) + encode_varint(cpu_arch) + encode_varint((3 << 3) | 0) + encode_varint(os_build) + encode_varint((4 << 3) | 0) + encode_varint(platform) + encode_varint((5 << 3) | 0) + encode_varint(os_major) + encode_varint((6 << 3) | 0) + encode_varint(os_minor) + encode_varint((8 << 3) | 0) + encode_varint(client_model))

    msg_4 = encode_nested_field(4, leaf)
    msg_1 = encode_nested_field(1, msg_4)
    msg_3 = msg_1 + encode_string_field(2, system_id)

    payload = (encode_string_field(1, app_version) + encode_string_field(2, device_id) + encode_nested_field(3, msg_3))

    root = (encode_varint((1 << 3) | 0) + encode_varint(1) + encode_nested_field(2, payload))

    return root


# Fetches Spotify access token based on provided device_id, system_id, user_uri_id, refresh_token and client_token value
def spotify_get_access_token_from_client(device_id, system_id, user_uri_id, refresh_token, client_token):
    global SP_CACHED_ACCESS_TOKEN, SP_CACHED_REFRESH_TOKEN, SP_ACCESS_TOKEN_EXPIRES_AT

    if SP_CACHED_ACCESS_TOKEN and time.time() < SP_ACCESS_TOKEN_EXPIRES_AT and check_token_validity(SP_CACHED_ACCESS_TOKEN, user_agent=USER_AGENT):
        debug_print("Using cached Spotify access token (client source)")
        return SP_CACHED_ACCESS_TOKEN

    if not client_token:
        raise Exception("Client token is missing")

    if SP_CACHED_REFRESH_TOKEN:
        debug_print("Using cached refresh token for client auth flow")
        refresh_token = SP_CACHED_REFRESH_TOKEN

    protobuf_body = build_spotify_auth_protobuf(device_id, system_id, user_uri_id, refresh_token)

    parsed_url = urlparse(LOGIN_URL)
    host = parsed_url.netloc
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

    headers = {
        "Host": host,
        "Connection": "keep-alive",
        "Content-Type": "application/x-protobuf",
        "User-Agent": USER_AGENT,
        "X-Retry-Count": "0",
        "Client-Token": client_token,
        "Origin": origin,
        "Accept-Language": "en-Latn-GB,en-GB;q=0.9,en;q=0.8",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Dest": "empty",
        "Accept-Encoding": "gzip, deflate, br, zstd"
    }

    try:
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] headers={sanitize_debug_headers(headers)} payload_len={len(protobuf_body)}")
        response = req.post(LOGIN_URL, headers=headers, data=protobuf_body, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] -> {response.status_code}")
    except TimeoutException as e:
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] timeout: {e}")
        raise Exception(f"spotify_get_access_token_from_client() network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        debug_print(f"HTTP POST {LOGIN_URL} [client auth] failed: {e}")
        raise Exception(f"spotify_get_access_token_from_client() network request error: {e}")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

    if response.status_code != 200:
        if response.headers.get("client-token-error") == "INVALID_CLIENTTOKEN":
            raise Exception(f"Request failed with status {response.status_code}: invalid client token")
        elif response.headers.get("client-token-error") == "EXPIRED_CLIENTTOKEN":
            raise Exception(f"Request failed with status {response.status_code}: expired client token")

        try:
            error_json = response.json()
        except ValueError:
            error_json = {}

        if error_json.get("error") == "invalid_grant":
            desc = error_json.get("error_description", "")
            if "refresh token" in desc.lower() and "revoked" in desc.lower():
                raise Exception(f"Request failed with status {response.status_code}: refresh token has been revoked")
            elif "refresh token" in desc.lower() and "expired" in desc.lower():
                raise Exception(f"Request failed with status {response.status_code}: refresh token has expired")
            elif "invalid refresh token" in desc.lower():
                raise Exception(f"Request failed with status {response.status_code}: refresh token is invalid")
            else:
                raise Exception(f"Request failed with status {response.status_code}: invalid grant during refresh")

        raise req.HTTPError(f"Spotify client login failed with HTTP {response.status_code}", response=response)

    parsed = parse_protobuf_message(response.content)
    # {1: {1: user_uri_id, 2: access_token, 3: refresh_token, 4: expires_in}}
    access_token_raw = None
    expires_in = 3600  # default
    if 1 in parsed and isinstance(parsed[1], dict):
        nested = parsed[1]
        access_token_raw = nested.get(2)
        user_uri_id = parsed[1].get(1)

        if 4 in nested:
            raw_expires = nested.get(4)
            if isinstance(raw_expires, (int, str, bytes)):
                try:
                    expires_in = int(raw_expires)
                except ValueError:
                    expires_in = 3600

    access_token = deep_flatten(access_token_raw) if access_token_raw else None

    if not access_token:
        raise Exception("Access token not found in response")

    SP_CACHED_ACCESS_TOKEN = access_token
    SP_CACHED_REFRESH_TOKEN = parsed[1].get(3)
    SP_ACCESS_TOKEN_EXPIRES_AT = time.time() + expires_in
    verbose_print("Authentication token refreshed (advanced client mode)")
    return access_token


# Fetches fresh client token
def spotify_get_client_token(app_version, device_id, system_id, **device_overrides):
    global SP_CACHED_CLIENT_TOKEN, SP_CLIENT_TOKEN_EXPIRES_AT

    if SP_CACHED_CLIENT_TOKEN and time.time() < SP_CLIENT_TOKEN_EXPIRES_AT:
        debug_print("Using cached client token")
        return SP_CACHED_CLIENT_TOKEN

    body = build_clienttoken_request_protobuf(app_version, device_id, system_id, **device_overrides)

    headers = {
        "Host": "clienttoken.spotify.com",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache, no-store, max-age=0",
        "Accept": "application/x-protobuf",
        "Content-Type": "application/x-protobuf",
        "User-Agent": USER_AGENT,
        "Origin": "https://clienttoken.spotify.com",
        "Accept-Language": "en-Latn-GB,en-GB;q=0.9,en;q=0.8",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Dest": "empty",
        "Accept-Encoding": "gzip, deflate, br, zstd",
    }

    try:
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(FUNCTION_TIMEOUT + 2)
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] app_version={app_version}, device_overrides={device_overrides}, payload_len={len(body)}")
        response = req.post(CLIENTTOKEN_URL, headers=headers, data=body, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] -> {response.status_code}")
    except TimeoutException as e:
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] timeout: {e}")
        raise Exception(f"spotify_get_client_token() network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        debug_print(f"HTTP POST {CLIENTTOKEN_URL} [client token] failed: {e}")
        raise Exception(f"spotify_get_client_token() network request error: {e}")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

    if response.status_code != 200:
        raise req.HTTPError(f"Spotify client-token request failed with HTTP {response.status_code}", response=response)

    parsed = parse_protobuf_message(response.content)
    inner = parsed.get(2, {})
    client_token = deep_flatten(inner.get(1)) if inner.get(1) else None
    ttl = int(inner.get(3, 0)) or 1209600

    if not client_token:
        raise Exception("clienttoken response did not contain a token")

    SP_CACHED_CLIENT_TOKEN = client_token
    SP_CLIENT_TOKEN_EXPIRES_AT = time.time() + ttl
    debug_print(f"Client token refreshed successfully, ttl={ttl}s")
    verbose_print("Spotify client token refreshed")

    return client_token


# Fetches Spotify access token with automatic client token refresh
def spotify_get_access_token_from_client_auto(device_id, system_id, user_uri_id, refresh_token):
    client_token = None

    if all([
        CLIENTTOKEN_URL,
        APP_VERSION,
        CPU_ARCH is not None and CPU_ARCH > 0,
        OS_BUILD is not None and OS_BUILD > 0,
        PLATFORM is not None and PLATFORM > 0,
        OS_MAJOR is not None and OS_MAJOR > 0,
        OS_MINOR is not None and OS_MINOR > 0,
        CLIENT_MODEL is not None and CLIENT_MODEL > 0
    ]):
        debug_print("Attempting to refresh/get client token before client auth")
        client_token = spotify_get_client_token(app_version=APP_VERSION, device_id=device_id, system_id=system_id, cpu_arch=CPU_ARCH, os_build=OS_BUILD, platform=PLATFORM, os_major=OS_MAJOR, os_minor=OS_MINOR, client_model=CLIENT_MODEL)

    try:
        return spotify_get_access_token_from_client(device_id, system_id, user_uri_id, refresh_token, client_token)
    except Exception as e:
        err = str(e).lower()
        debug_print(f"Client auth failed: {e}")
        if all([
            CLIENTTOKEN_URL,
            APP_VERSION,
            CPU_ARCH is not None and CPU_ARCH > 0,
            OS_BUILD is not None and OS_BUILD > 0,
            PLATFORM is not None and PLATFORM > 0,
            OS_MAJOR is not None and OS_MAJOR > 0,
            OS_MINOR is not None and OS_MINOR > 0,
            CLIENT_MODEL is not None and CLIENT_MODEL > 0
        ]) and ("invalid client token" in err or "expired client token" in err):
            global SP_CLIENT_TOKEN_EXPIRES_AT
            SP_CLIENT_TOKEN_EXPIRES_AT = 0
            debug_print("Client token invalid/expired, forcing refresh and retry")

            client_token = spotify_get_client_token(app_version=APP_VERSION, device_id=DEVICE_ID, system_id=SYSTEM_ID, cpu_arch=CPU_ARCH, os_build=OS_BUILD, platform=PLATFORM, os_major=OS_MAJOR, os_minor=OS_MINOR, client_model=CLIENT_MODEL)

            return spotify_get_access_token_from_client(device_id, system_id, user_uri_id, refresh_token, client_token)
        raise


# --------------------------------------------------------

# Fetches Spotify access token based on provided sp_client_id & sp_client_secret values (Client Credentials OAuth Flow)
def spotify_get_access_token_from_oauth_app(sp_client_id, sp_client_secret):
    global SP_CACHED_OAUTH_APP_TOKEN, SPOTIPY_AVAILABLE, SPOTIPY_IMPORT_WARNING_SHOWN

    if not sp_client_id or not sp_client_secret:
        return None

    if SPOTIPY_AVAILABLE is False:
        if not SPOTIPY_IMPORT_WARNING_SHOWN:
            print("* Warning: Spotipy is unavailable. Install legacy OAuth support with `pip install 'spotify_monitor[legacy-oauth]'`")
            SPOTIPY_IMPORT_WARNING_SHOWN = True
        return None

    try:
        from spotipy.oauth2 import SpotifyClientCredentials
        from spotipy.cache_handler import CacheFileHandler, MemoryCacheHandler
    except ImportError:
        SPOTIPY_AVAILABLE = False
        if not SPOTIPY_IMPORT_WARNING_SHOWN:
            print("* Warning: Spotipy is unavailable. Install legacy OAuth support with `pip install 'spotify_monitor[legacy-oauth]'`")
            SPOTIPY_IMPORT_WARNING_SHOWN = True
        return None
    SPOTIPY_AVAILABLE = True

    if SP_CACHED_OAUTH_APP_TOKEN and check_token_validity(SP_CACHED_OAUTH_APP_TOKEN, oauth_app=True):
        debug_print("Using cached OAuth app access token")
        return SP_CACHED_OAUTH_APP_TOKEN

    if SP_APP_TOKENS_FILE:
        cache_handler = CacheFileHandler(cache_path=SP_APP_TOKENS_FILE)
    else:
        cache_handler = MemoryCacheHandler()

    session = req.Session()
    session.headers.update({'User-Agent': USER_AGENT})

    auth_manager = SpotifyClientCredentials(client_id=sp_client_id, client_secret=sp_client_secret, cache_handler=cache_handler, requests_session=session)  # type: ignore[arg-type]

    SP_CACHED_OAUTH_APP_TOKEN = auth_manager.get_access_token(as_dict=False)
    debug_print("OAuth app access token refreshed successfully")
    verbose_print("Legacy OAuth metadata token refreshed")

    return SP_CACHED_OAUTH_APP_TOKEN


# Fetches list of Spotify friends
def spotify_get_friends_json(access_token):
    url = "https://guc-spclient.spotify.com/presence-view/v1/buddylist"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    debug_print(f"HTTP GET {url} [buddylist] headers={sanitize_debug_headers(headers)}")
    response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print(f"HTTP GET {url} [buddylist] -> {response.status_code}")
    if response.status_code == 401:
        raise Exception("401 Unauthorized for url: " + url)
    response.raise_for_status()
    friends_json = response.json()
    error_str = friends_json.get("error")
    if error_str:
        raise ValueError(error_str)

    return friends_json


# Converts Spotify URI (e.g. spotify:user:username) to URL (e.g. https://open.spotify.com/user/username)
def spotify_convert_uri_to_url(uri):
    # add si parameter so link opens in native Spotify app after clicking
    si = "?si=1"
    # si=""

    uri = uri or ''
    url = ""
    if not isinstance(uri, str):
        return url
    if "spotify:user:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/user/{s_id}{si}"
    elif "spotify:artist:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/artist/{s_id}{si}"
    elif "spotify:track:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/track/{s_id}{si}"
    elif "spotify:album:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/album/{s_id}{si}"
    elif "spotify:playlist:" in uri:
        s_id = uri.split(':', 2)[2]
        url = f"https://open.spotify.com/playlist/{s_id}{si}"

    return url


# Returns list of Spotify friends with normalized playlist owner metadata
def spotify_list_friends(friend_activity, access_token):

    print(f"Number of friends:\t\t{len(friend_activity['friends'])}\n")

    for index, friend in enumerate(friend_activity["friends"]):
        sp_uri = friend["user"].get("uri").split("spotify:user:", 1)[1]
        sp_username = friend["user"].get("name")
        sp_artist = friend["track"]["artist"].get("name")
        sp_album = friend["track"]["album"].get("name")
        sp_playlist = friend["track"]["context"].get("name")
        sp_track = friend["track"].get("name")
        sp_ts = friend.get("timestamp")
        sp_album_uri = friend["track"]["album"].get("uri")
        sp_playlist_uri = friend["track"]["context"].get("uri")
        sp_track_uri = friend["track"].get("uri")

        sp_playlist_owner = ""
        if 'spotify:playlist:' in sp_playlist_uri:
            sp_playlist_owner = spotify_get_playlist_owner(access_token, sp_playlist_uri)
        playlist_suffix = SPOTIFY_SUFFIX if sp_playlist_owner == "Spotify" else ""

        print("─" * HORIZONTAL_LINE)
        print(f"Username:\t\t\t{sp_username}")
        print(f"User URI ID:\t\t\t{sp_uri}")
        print(f"User URL:\t\t\t{spotify_convert_uri_to_url('spotify:user:' + sp_uri)}")
        print(f"\nLast played:\t\t\t{sp_artist} - {sp_track}\n")
        if 'spotify:playlist:' in sp_playlist_uri:
            print(f"Playlist:\t\t\t{sp_playlist}{playlist_suffix}")
        print(f"Album:\t\t\t\t{sp_album}")

        if 'spotify:album:' in sp_playlist_uri and sp_playlist != sp_album:
            print(f"\nContext (Album):\t\t{sp_playlist}")

        if 'spotify:artist:' in sp_playlist_uri:
            print(f"\nContext (Artist):\t\t{sp_playlist}")

        print(f"\nTrack URL:\t\t\t{spotify_convert_uri_to_url(sp_track_uri)}")
        if 'spotify:playlist:' in sp_playlist_uri:
            print(f"Playlist URL:\t\t\t{spotify_convert_uri_to_url(sp_playlist_uri)}")
        print(f"Album URL:\t\t\t{spotify_convert_uri_to_url(sp_album_uri)}")

        if 'spotify:album:' in sp_playlist_uri and sp_playlist != sp_album:
            print(f"Context (Album) URL:\t\t{spotify_convert_uri_to_url(sp_playlist_uri)}")

        if 'spotify:artist:' in sp_playlist_uri:
            print(f"Context (Artist) URL:\t\t{spotify_convert_uri_to_url(sp_playlist_uri)}")

        apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url = get_apple_genius_search_urls(str(sp_artist), str(sp_track))

        music_urls_output = format_music_urls_console(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
        if music_urls_output:
            print(music_urls_output)
        lyrics_output = format_lyrics_urls_console(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
        if lyrics_output:
            print(lyrics_output)

        print(f"\nLast activity:\t\t\t{get_date_from_ts(float(str(sp_ts)[0:-3]))} ({calculate_timespan(int(time.time()), datetime.fromtimestamp(float(str(sp_ts)[0:-3])))} ago)")


# Returns information for specific Spotify friend's user URI id
def spotify_get_friend_info(friend_activity, uri):
    for friend in friend_activity["friends"]:
        sp_uri = friend["user"]["uri"].split("spotify:user:", 1)[1]
        if sp_uri == uri:
            sp_username = friend["user"].get("name")
            sp_artist = friend["track"]["artist"].get("name")
            sp_album = friend["track"]["album"].get("name")
            sp_album_uri = friend["track"]["album"].get("uri")
            sp_playlist = friend["track"]["context"].get("name")
            sp_playlist_uri = friend["track"]["context"].get("uri")
            sp_track = friend["track"].get("name")
            sp_track_uri = str(friend["track"].get("uri"))
            if "spotify:track:" in sp_track_uri:
                sp_track_uri_id = sp_track_uri.split(':', 2)[2]
            else:
                sp_track_uri_id = ""
            sp_ts = int(str(friend.get("timestamp"))[0:-3])
            return True, {"sp_uri": sp_uri, "sp_username": sp_username, "sp_artist": sp_artist, "sp_track": sp_track, "sp_track_uri": sp_track_uri, "sp_track_uri_id": sp_track_uri_id, "sp_album": sp_album, "sp_album_uri": sp_album_uri, "sp_playlist": sp_playlist, "sp_playlist_uri": sp_playlist_uri, "sp_ts": sp_ts}
    return False, {}


# Returns True when complete non-placeholder OAuth app credentials are configured
def spotify_has_oauth_app_credentials():
    return not any([not SP_APP_CLIENT_ID, SP_APP_CLIENT_ID == "your_spotify_app_client_id", not SP_APP_CLIENT_SECRET, SP_APP_CLIENT_SECRET == "your_spotify_app_client_secret"])


# Describes the configured metadata backend policy for startup output
def spotify_get_metadata_backend_description():
    if not spotify_has_oauth_app_credentials():
        return "web player"
    try:
        spotipy_available = SPOTIPY_AVAILABLE is not False and importlib.util.find_spec("spotipy") is not None
    except (ImportError, ValueError):
        spotipy_available = False
    if not spotipy_available:
        return "web player (legacy OAuth unavailable: Spotipy missing)"
    return "automatic (legacy Web API + web player)"


# Returns enabled email notification category names in display order
def _startup_notification_categories() -> List[str]:
    settings = (
        (ACTIVE_NOTIFICATION, "active"),
        (INACTIVE_NOTIFICATION, "inactive"),
        (TRACK_NOTIFICATION, "monitored tracks"),
        (SONG_NOTIFICATION, "every song"),
        (SONG_ON_LOOP_NOTIFICATION, "songs on loop"),
        (ERROR_NOTIFICATION, "errors"),
    )
    return [label for enabled, label in settings if enabled]


# Returns enabled webhook notification category names in display order
def _startup_webhook_notification_categories() -> List[str]:
    settings = (
        (WEBHOOK_ACTIVE_NOTIFICATION, "active"),
        (WEBHOOK_INACTIVE_NOTIFICATION, "inactive"),
        (WEBHOOK_TRACK_NOTIFICATION, "monitored tracks"),
        (WEBHOOK_SONG_NOTIFICATION, "every song"),
        (WEBHOOK_SONG_ON_LOOP_NOTIFICATION, "songs on loop"),
        (WEBHOOK_ERROR_NOTIFICATION, "errors"),
    )
    return [label for enabled, label in settings if WEBHOOK_ENABLED and enabled]


# Builds the concise and complete non-secret startup summary rows
def build_startup_summary(target: str, config_path, env_path, output_path) -> List[StartupSummaryRow]:
    authentication = "Client mode, advanced" if TOKEN_SOURCE == "client" else "Cookie mode"
    enabled_notifications = _startup_notification_categories()
    enabled_webhooks = _startup_webhook_notification_categories()
    if enabled_notifications and enabled_webhooks:
        notification_state = "On (email: " + ", ".join(enabled_notifications) + " | webhook: " + ", ".join(enabled_webhooks) + ")"
    elif enabled_webhooks:
        notification_state = "On (webhook: " + ", ".join(enabled_webhooks) + ")"
    else:
        notification_state = "Off" if not enabled_notifications else "On (" + ", ".join(enabled_notifications) + ")"
    output_state = str(output_path) if output_path else "Terminal only (logging disabled)"
    rows = [
        StartupSummaryRow("Target", str(target), concise=True),
        StartupSummaryRow("Authentication", authentication, concise=True),
        StartupSummaryRow("Token source", TOKEN_SOURCE, concise=False),
        StartupSummaryRow("Polling interval", display_time(SPOTIFY_CHECK_INTERVAL), concise=True),
        StartupSummaryRow("Inactivity timer", display_time(SPOTIFY_INACTIVITY_CHECK), concise=False),
        StartupSummaryRow("Disappeared timer", display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL), concise=False),
        StartupSummaryRow("Error retry timer", display_time(SPOTIFY_ERROR_INTERVAL), concise=False),
        StartupSummaryRow("Notifications", notification_state, concise=True, full=False, log=False),
        StartupSummaryRow("Notify active", str(ACTIVE_NOTIFICATION), concise=False),
        StartupSummaryRow("Notify inactive", str(INACTIVE_NOTIFICATION), concise=False),
        StartupSummaryRow("Notify monitored tracks", str(TRACK_NOTIFICATION), concise=False),
        StartupSummaryRow("Notify every song", str(SONG_NOTIFICATION), concise=False),
        StartupSummaryRow("Notify songs on loop", str(SONG_ON_LOOP_NOTIFICATION), concise=False),
        StartupSummaryRow("Notify errors", str(ERROR_NOTIFICATION), concise=False),
        StartupSummaryRow("Webhook enabled", str(WEBHOOK_ENABLED), concise=False),
        StartupSummaryRow("Webhook categories", ", ".join(enabled_webhooks) if enabled_webhooks else "None", concise=False),
        StartupSummaryRow("Output", output_state, concise=True, full=False, log=False),
        StartupSummaryRow("Output logging", str(output_path) if output_path else "Disabled", concise=False),
        StartupSummaryRow("Config", str(config_path) if config_path else "None", concise=True),
        StartupSummaryRow("Dotenv", str(env_path) if env_path else "None", concise=True),
        StartupSummaryRow("Metadata backend", spotify_get_metadata_backend_description(), concise=True),
        StartupSummaryRow("Spotify playback control", str(TRACK_SONGS), concise=bool(TRACK_SONGS)),
        StartupSummaryRow("Liveness output", display_time(LIVENESS_CHECK_INTERVAL) if LIVENESS_CHECK_INTERVAL else "Disabled", concise=bool(LIVENESS_CHECK_INTERVAL)),
        StartupSummaryRow("CSV output", CSV_FILE or "Disabled", concise=bool(CSV_FILE)),
        StartupSummaryRow("Monitored-track alerts", MONITOR_LIST_FILE or "Disabled", concise=bool(MONITOR_LIST_FILE)),
        StartupSummaryRow("Flag file", FLAG_FILE or "None", concise=bool(FLAG_FILE)),
        StartupSummaryRow("Terminal truncation", f"{TRUNCATE_CHARS} chars" if TRUNCATE_CHARS else "Disabled", concise=bool(TRUNCATE_CHARS)),
        StartupSummaryRow("Verbose mode", str(VERBOSE_MODE), concise=bool(VERBOSE_MODE)),
        StartupSummaryRow("Debug mode", str(DEBUG_MODE), concise=bool(DEBUG_MODE)),
    ]
    if spotify_has_oauth_app_credentials():
        oauth_cache = SP_APP_TOKENS_FILE or "None (memory only)"
        rows.append(StartupSummaryRow("Legacy OAuth cache", oauth_cache, concise=True))
    else:
        rows.append(StartupSummaryRow("Legacy OAuth cache", "Not used", concise=False))
    rows.append(StartupSummaryRow("More details", "use --verbose or --debug", concise=True, full=False, log=False))
    return rows


# Formats one startup summary row with aligned plain ASCII columns
def _format_startup_summary_row(row: StartupSummaryRow) -> str:
    return f"* {(row.label + ':'):<27}{row.value}\n"


# Routes concise or complete startup rows independently to terminal and log destinations
def emit_startup_summary(rows: Sequence[StartupSummaryRow], show_full: bool, stream=None) -> None:
    destination: Any = stream or sys.stdout
    routed = hasattr(destination, "terminal_only") and hasattr(destination, "log_only")
    for row in rows:
        line = _format_startup_summary_row(row)
        if routed and row.full and row.log:
            destination.log_only(line)
        show_in_terminal = row.full if show_full else row.concise
        if show_in_terminal:
            if routed:
                destination.terminal_only(line)
            else:
                destination.write(line)
    if routed:
        destination.log_only("\n")
        destination.terminal_only("\n")
    else:
        destination.write("\n")
        destination.flush()


# Returns a cached or freshly generated anonymous Spotify web-player token
def spotify_get_web_access_token_data():
    global SP_CACHED_WEB_ACCESS_TOKEN, SP_WEB_ACCESS_TOKEN_EXPIRES_AT, SP_CACHED_WEB_CLIENT_ID

    now = time.time()
    if SP_CACHED_WEB_ACCESS_TOKEN and now < SP_WEB_ACCESS_TOKEN_EXPIRES_AT - 60:
        debug_print("Using cached anonymous Spotify web-player access token")
        return {"access_token": SP_CACHED_WEB_ACCESS_TOKEN, "expires_at": SP_WEB_ACCESS_TOKEN_EXPIRES_AT, "client_id": SP_CACHED_WEB_CLIENT_ID}

    token_data = refresh_access_token_from_sp_dc("")
    access_token = token_data.get("access_token", "")
    expires_at = token_data.get("expires_at", 0)
    client_id = token_data.get("client_id", "")
    if not access_token or not expires_at or not client_id:
        raise RuntimeError("Spotify returned incomplete anonymous web-player token data")

    SP_CACHED_WEB_ACCESS_TOKEN = access_token
    SP_WEB_ACCESS_TOKEN_EXPIRES_AT = expires_at
    SP_CACHED_WEB_CLIENT_ID = client_id
    debug_print(f"Anonymous Spotify web-player token obtained successfully, token_len={len(access_token)}")
    verbose_print("Web-player metadata token refreshed")
    return {"access_token": access_token, "expires_at": expires_at, "client_id": client_id}


# Discovers and caches a metadata persisted-query hash from the current web-player bundle
def spotify_discover_web_query_hash(operation_name, force=False):
    global SP_CACHED_PLAYLIST_QUERY_HASH, SP_CACHED_TRACK_QUERY_HASH

    if operation_name == "fetchPlaylistMetadata":
        cached_hash = SP_CACHED_PLAYLIST_QUERY_HASH
    elif operation_name == "getTrack":
        cached_hash = SP_CACHED_TRACK_QUERY_HASH
    else:
        raise ValueError(f"Unsupported Spotify web-player operation: {operation_name}")

    if cached_hash and not force:
        return cached_hash

    headers = {"Accept": "text/html,application/xhtml+xml", "User-Agent": WEB_PLAYER_USER_AGENT}
    debug_print(f"HTTP GET {WEB_PLAYER_URL} [query discovery operation={operation_name}] headers={sanitize_debug_headers(headers)}")
    response = SESSION.get(WEB_PLAYER_URL, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print(f"HTTP GET {WEB_PLAYER_URL} [query discovery operation={operation_name}] -> {response.status_code}")
    response.raise_for_status()

    script_urls = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', response.text, flags=re.IGNORECASE)
    bundle_url = ""
    for script_url in script_urls:
        if re.search(r'/(?:mobile-)?web-player/(?:mobile-)?web-player\.[^/?]+\.js(?:\?|$)', script_url):
            bundle_url = urljoin(WEB_PLAYER_URL, script_url)
            break
    if not bundle_url:
        raise RuntimeError("Cannot find the Spotify web-player JavaScript bundle")

    debug_print(f"HTTP GET {bundle_url} [query bundle operation={operation_name}]")
    bundle_response = SESSION.get(bundle_url, headers={"User-Agent": WEB_PLAYER_USER_AGENT}, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print(f"HTTP GET {bundle_url} [query bundle operation={operation_name}] -> {bundle_response.status_code}")
    bundle_response.raise_for_status()

    hash_match = re.search(rf'["\']{re.escape(operation_name)}["\']\s*,\s*["\']query["\']\s*,\s*["\']([0-9a-f]{{64}})["\']', bundle_response.text)
    if not hash_match:
        raise RuntimeError(f"Cannot find the {operation_name} persisted-query hash in the Spotify web-player bundle")

    query_hash = hash_match.group(1)
    if operation_name == "fetchPlaylistMetadata":
        SP_CACHED_PLAYLIST_QUERY_HASH = query_hash
    else:
        SP_CACHED_TRACK_QUERY_HASH = query_hash
    debug_print(f"Discovered Spotify {operation_name} persisted-query hash from {bundle_url}")
    return query_hash


# Discovers and caches the playlist metadata persisted-query hash
def spotify_discover_playlist_query_hash(force=False):
    return spotify_discover_web_query_hash("fetchPlaylistMetadata", force)


# Discovers and caches the track metadata persisted-query hash
def spotify_discover_track_query_hash(force=False):
    return spotify_discover_web_query_hash("getTrack", force)


# Executes a Spotify web-player metadata query with automatic token and hash refresh
def spotify_web_metadata_query(operation_name, variables, metadata_type):
    global SP_CACHED_WEB_ACCESS_TOKEN, SP_WEB_ACCESS_TOKEN_EXPIRES_AT, SP_CACHED_WEB_CLIENT_ID, SP_CACHED_PLAYLIST_QUERY_HASH, SP_CACHED_TRACK_QUERY_HASH

    last_error = ""
    for attempt in range(2):
        token_data = spotify_get_web_access_token_data()
        if metadata_type == "playlist":
            query_hash = spotify_discover_playlist_query_hash(force=attempt > 0 and not SP_CACHED_PLAYLIST_QUERY_HASH)
        elif metadata_type == "track":
            query_hash = spotify_discover_track_query_hash(force=attempt > 0 and not SP_CACHED_TRACK_QUERY_HASH)
        else:
            raise ValueError(f"Unsupported Spotify metadata type: {metadata_type}")

        headers = {"Accept": "application/json", "App-Platform": "WebPlayer", "Authorization": f"Bearer {token_data['access_token']}", "Client-Id": token_data["client_id"], "Content-Type": "application/json", "User-Agent": WEB_PLAYER_USER_AGENT}
        payload = {"extensions": {"persistedQuery": {"sha256Hash": query_hash, "version": 1}}, "operationName": operation_name, "variables": variables}

        debug_print(f"HTTP POST {WEB_PLAYER_QUERY_URL} [web metadata operation={operation_name}] headers={sanitize_debug_headers(headers)}")
        response = SESSION.post(WEB_PLAYER_QUERY_URL, headers=headers, json=payload, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP POST {WEB_PLAYER_QUERY_URL} [web metadata operation={operation_name}] -> {response.status_code}")

        try:
            json_response = response.json()
        except ValueError:
            response.raise_for_status()
            raise RuntimeError(f"Spotify web-player operation '{operation_name}' returned invalid JSON")

        errors = json_response.get("errors") if isinstance(json_response, dict) else None
        error_message = " | ".join(str(error.get("message", error)) if isinstance(error, dict) else str(error) for error in (errors or []))
        last_error = error_message or f"HTTP {response.status_code}"

        if response.status_code == 401 and attempt == 0:
            SP_CACHED_WEB_ACCESS_TOKEN = None
            SP_WEB_ACCESS_TOKEN_EXPIRES_AT = 0
            SP_CACHED_WEB_CLIENT_ID = ""
            debug_print("Anonymous web-player token was rejected, refreshing it once")
            continue

        if errors and attempt == 0 and any(marker in error_message.lower() for marker in ("persistedquery", "persisted query", "sha256")):
            if metadata_type == "playlist":
                SP_CACHED_PLAYLIST_QUERY_HASH = ""
            else:
                SP_CACHED_TRACK_QUERY_HASH = ""
            debug_print(f"{operation_name} persisted query was rejected, rediscovering its hash once")
            continue

        if errors:
            raise RuntimeError(f"Spotify web-player operation '{operation_name}' failed: {error_message}")

        response.raise_for_status()
        data = json_response.get("data") if isinstance(json_response, dict) else None
        if not isinstance(data, dict):
            raise RuntimeError(f"Spotify web-player operation '{operation_name}' returned no data")
        return data

    raise RuntimeError(f"Spotify web-player operation '{operation_name}' failed after refresh: {last_error}")


# Executes the Spotify web-player playlist metadata query
def spotify_web_playlist_query(operation_name, variables):
    return spotify_web_metadata_query(operation_name, variables, "playlist")


# Executes the Spotify web-player track metadata query
def spotify_web_track_query(operation_name, variables):
    return spotify_web_metadata_query(operation_name, variables, "track")


# Builds a Spotify share URL from web-player data or an entity URI
def spotify_get_web_entity_url(entity, uri):
    sharing_info = entity.get("sharingInfo") or {} if isinstance(entity, dict) else {}
    share_url = sharing_info.get("shareUrl", "") if isinstance(sharing_info, dict) else ""
    return share_url or spotify_convert_uri_to_url(uri)


# Normalizes Spotify web-player track metadata to the existing monitoring shape
def spotify_normalize_web_track(track):
    if not isinstance(track, dict) or track.get("__typename") != "Track":
        raise ValueError("Spotify web-player track data is missing or malformed")

    duration_data = track.get("duration") or track.get("trackDuration") or {}
    duration_ms = duration_data.get("totalMilliseconds") if isinstance(duration_data, dict) else None
    if duration_ms is None:
        raise ValueError("Spotify web-player track duration is missing or malformed")

    artist_items = (track.get("firstArtist") or {}).get("items") or []
    artist = artist_items[0] if artist_items and isinstance(artist_items[0], dict) else {}
    artist_profile = artist.get("profile") or {}
    album = track.get("albumOfTrack") or {}
    if not isinstance(album, dict):
        album = {}

    track_uri = track.get("uri", "")
    artist_uri = artist.get("uri", "")
    album_uri = album.get("uri", "")
    return {"sp_track_duration": int(int(duration_ms) / 1000), "sp_track_url": spotify_get_web_entity_url(track, track_uri), "sp_track_uri": track_uri, "sp_track_name": track.get("name"), "sp_artist_url": spotify_get_web_entity_url(artist, artist_uri), "sp_artist_uri": artist_uri, "sp_artist_name": artist_profile.get("name") if isinstance(artist_profile, dict) else None, "sp_album_url": spotify_get_web_entity_url(album, album_uri), "sp_album_uri": album_uri, "sp_album_name": album.get("name")}


# Fetches and normalizes public track metadata from the Spotify web-player service
def spotify_get_track_info_web(track_uri):
    data = spotify_web_track_query("getTrack", {"uri": track_uri})
    return spotify_normalize_web_track(data.get("trackUnion"))


# Fetches public playlist metadata from the Spotify web-player service
def spotify_get_web_playlist_metadata(playlist_uri):
    data = spotify_web_playlist_query("fetchPlaylistMetadata", {"enableWatchFeedEntrypoint": False, "uri": playlist_uri})
    playlist = data.get("playlistV2")
    if not isinstance(playlist, dict):
        raise RuntimeError(f"Playlist is unavailable from the Spotify web-player service: {playlist_uri}")
    return playlist


# Normalizes Spotify web-player playlist metadata to the existing owner shape
def spotify_normalize_web_playlist(playlist):
    if not isinstance(playlist, dict):
        raise ValueError("Spotify web-player playlist data is missing or malformed")
    owner_data = (playlist.get("ownerV2") or {}).get("data") or {}
    if not isinstance(owner_data, dict):
        raise ValueError("Spotify web-player playlist owner data is missing or malformed")
    owner_uri = owner_data.get("uri", "")
    playlist_uri = playlist.get("uri", "")
    return {"sp_playlist_name": playlist.get("name", ""), "sp_playlist_owner": owner_data.get("name", "") or owner_data.get("username", ""), "sp_playlist_owner_uri": owner_uri, "sp_playlist_owner_url": spotify_get_web_entity_url(owner_data, owner_uri), "sp_playlist_url": spotify_get_web_entity_url(playlist, playlist_uri), "sp_playlist_revision_id": playlist.get("revisionId", "")}


# Returns normalized public playlist metadata through Spotify's web-player service
def spotify_get_playlist_info_web(playlist_uri):
    return spotify_normalize_web_playlist(spotify_get_web_playlist_metadata(playlist_uri))


# Returns the HTTP status code attached to a requests exception when available
def spotify_get_error_status_code(error):
    return error.response.status_code if isinstance(error, req.HTTPError) and error.response is not None else None


# Returns playlist owner metadata through the legacy Spotify Web API path
def _spotify_get_playlist_owner_api(access_token, playlist_uri, oauth_app=False):
    if TOKEN_SOURCE in {"cookie", "client"} and not oauth_app:
        access_token = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
        oauth_app = True
    if not access_token:
        raise Exception("_spotify_get_playlist_owner_api(): OAuth app token is empty")

    playlist_id = playlist_uri.split(':', 2)[2]
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}?fields=name,owner"
    headers = {"Authorization": f"Bearer {access_token}", "User-Agent": USER_AGENT}
    if TOKEN_SOURCE == "cookie" and not oauth_app:
        headers["Client-Id"] = SP_CACHED_CLIENT_ID

    debug_print(f"HTTP GET {url} [legacy playlist owner] headers={sanitize_debug_headers(headers)}")
    response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print(f"HTTP GET {url} [legacy playlist owner] -> {response.status_code}")
    response.raise_for_status()
    json_response = response.json()
    owner_data = json_response.get("owner")
    if not isinstance(owner_data, dict):
        raise ValueError("Playlist owner data is missing or malformed")
    return owner_data.get("display_name", "")


# Selects the legacy or web-player playlist owner backend and falls back automatically
def spotify_get_playlist_owner(access_token, playlist_uri, oauth_app=False):
    global SP_WEB_PLAYLIST_BACKEND_PREFERRED

    api_error = None
    api_available = bool(oauth_app and access_token) or spotify_has_oauth_app_credentials()
    if api_available and not SP_WEB_PLAYLIST_BACKEND_PREFERRED:
        try:
            return _spotify_get_playlist_owner_api(access_token, playlist_uri, oauth_app)
        except Exception as error:
            api_error = error
            if spotify_get_error_status_code(error) in {403, 404}:
                SP_WEB_PLAYLIST_BACKEND_PREFERRED = True
                debug_print("spotify_get_playlist_owner(): restricted Web API response, preferring the web-player backend for remaining playlists")
                verbose_print("Playlist metadata switched to the web-player backend after a restricted legacy API response")
            else:
                debug_print(f"spotify_get_playlist_owner(): legacy Web API backend failed for uri={playlist_uri}: {error}")

    try:
        return spotify_get_playlist_info_web(playlist_uri)["sp_playlist_owner"]
    except Exception as web_error:
        debug_print(f"spotify_get_playlist_owner(): web-player backend failed for uri={playlist_uri}: {web_error}")
        if api_error is not None:
            raise RuntimeError(f"Both Spotify playlist metadata backends failed for {playlist_uri}: Web API: {api_error}. Web player: {web_error}")
        raise


# Returns track metadata through the legacy Spotify Web API path
def _spotify_get_track_info_api(access_token, track_uri, oauth_app=False):
    if TOKEN_SOURCE in {"cookie", "client"} and not oauth_app:
        access_token = spotify_get_access_token_from_oauth_app(SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET)
        oauth_app = True
    if not access_token:
        raise Exception("_spotify_get_track_info_api(): OAuth app token is empty")

    track_id = track_uri.split(':', 2)[2]
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    headers = {"Authorization": f"Bearer {access_token}", "User-Agent": USER_AGENT}
    if TOKEN_SOURCE == "cookie" and not oauth_app:
        headers["Client-Id"] = SP_CACHED_CLIENT_ID

    debug_print(f"HTTP GET {url} [legacy track info] headers={sanitize_debug_headers(headers)}")
    response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    debug_print(f"HTTP GET {url} [legacy track info] -> {response.status_code}")
    response.raise_for_status()
    json_response = response.json()
    duration_ms = json_response.get("duration_ms")
    artists = json_response.get("artists") or []
    artist = artists[0] if artists and isinstance(artists[0], dict) else {}
    album = json_response.get("album") or {}
    if duration_ms is None or not isinstance(album, dict):
        raise ValueError("Spotify Web API track data is missing or malformed")

    track_uri_value = json_response.get("uri", track_uri)
    artist_uri = artist.get("uri", "")
    album_uri = album.get("uri", "")
    return {"sp_track_duration": int(int(duration_ms) / 1000), "sp_track_url": ((json_response.get("external_urls") or {}).get("spotify") or spotify_convert_uri_to_url(track_uri_value)), "sp_track_uri": track_uri_value, "sp_track_name": json_response.get("name"), "sp_artist_url": ((artist.get("external_urls") or {}).get("spotify") or spotify_convert_uri_to_url(artist_uri)), "sp_artist_uri": artist_uri, "sp_artist_name": artist.get("name"), "sp_album_url": ((album.get("external_urls") or {}).get("spotify") or spotify_convert_uri_to_url(album_uri)), "sp_album_uri": album_uri, "sp_album_name": album.get("name")}


# Selects the legacy or web-player track backend and falls back automatically
def spotify_get_track_info(access_token, track_uri, oauth_app=False):
    global SP_WEB_TRACK_BACKEND_PREFERRED

    api_error = None
    api_available = bool(oauth_app and access_token) or spotify_has_oauth_app_credentials()
    if api_available and not SP_WEB_TRACK_BACKEND_PREFERRED:
        try:
            return _spotify_get_track_info_api(access_token, track_uri, oauth_app)
        except Exception as error:
            api_error = error
            if spotify_get_error_status_code(error) == 403:
                SP_WEB_TRACK_BACKEND_PREFERRED = True
                debug_print("spotify_get_track_info(): Web API returned 403, preferring the web-player backend for remaining tracks")
                verbose_print("Track metadata switched to the web-player backend after a restricted legacy API response")
            else:
                debug_print(f"spotify_get_track_info(): legacy Web API backend failed for uri={track_uri}: {error}")

    try:
        return spotify_get_track_info_web(track_uri)
    except Exception as web_error:
        debug_print(f"spotify_get_track_info(): web-player backend failed for uri={track_uri}: {web_error}")
        if api_error is not None:
            raise RuntimeError(f"Both Spotify track metadata backends failed for {track_uri}: Web API: {api_error}. Web player: {web_error}")
        raise


# Checks if a Spotify user URI ID has been deleted
def is_user_removed(access_token, user_uri_id, oauth_app=False):
    # Use internal Spotify API (official /users/{id} endpoint was removed in Feb 2026)
    url = f"https://spclient.wg.spotify.com/user-profile-view/v3/profile/{user_uri_id}?playlist_limit=0&artist_limit=0&episode_limit=0&market=from_token"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie" and not oauth_app:
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    if platform.system() != 'Windows':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT + 2)

    try:
        temp_session = req.Session()
        temp_session.headers.update(headers)

        debug_print(f"HTTP GET {url} [user removed check] headers={sanitize_debug_headers(headers)}")
        response = temp_session.get(url, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        debug_print(f"HTTP GET {url} [user removed check] -> {response.status_code}")

        if response.status_code == 429:
            return False

        if response.status_code == 404:
            return True
        return False
    except TimeoutException:
        return False
    except req.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            return False
        elif e.response is not None and e.response.status_code == 404:
            return True
        return False
    except Exception:
        return False
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)


def spotify_macos_play_song(sp_track_uri_id, method=SPOTIFY_MACOS_PLAYING_METHOD):
    if method == "apple-script":   # apple-script
        script = f'tell app "Spotify" to play track "spotify:track:{sp_track_uri_id}"'
        proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        stdout, stderr = proc.communicate(script)
    else:                          # trigger-url - just trigger track URL in the client
        subprocess.call(('open', spotify_convert_uri_to_url(f"spotify:track:{sp_track_uri_id}")))


def spotify_macos_play_pause(action, method=SPOTIFY_MACOS_PLAYING_METHOD):
    if method == "apple-script":   # apple-script
        if str(action).lower() == "pause":
            script = 'tell app "Spotify" to pause'
            proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            stdout, stderr = proc.communicate(script)
        elif str(action).lower() == "play":
            script = 'tell app "Spotify" to play'
            proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            stdout, stderr = proc.communicate(script)


def spotify_linux_play_song(sp_track_uri_id, method=SPOTIFY_LINUX_PLAYING_METHOD):
    if method == "dbus-send":      # dbus-send
        subprocess.call((f"dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.OpenUri string:'spotify:track:{sp_track_uri_id}'"), shell=True)
    elif method == "qdbus":        # qdbus
        subprocess.call((f"qdbus org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.OpenUri spotify:track:{sp_track_uri_id}"), shell=True)
    else:                          # trigger-url - just trigger track URL in the client
        subprocess.call(('xdg-open', spotify_convert_uri_to_url(f"spotify:track:{sp_track_uri_id}")), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def spotify_linux_play_pause(action, method=SPOTIFY_LINUX_PLAYING_METHOD):
    if method == "dbus-send":      # dbus-send
        if str(action).lower() == "pause":
            subprocess.call((f"dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Pause"), shell=True)
        elif str(action).lower() == "play":
            subprocess.call((f"dbus-send --type=method_call --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Play"), shell=True)
    elif method == "qdbus":        # qdbus
        if str(action).lower() == "pause":
            subprocess.call((f"qdbus org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Pause"), shell=True)
        elif str(action).lower() == "play":
            subprocess.call((f"qdbus org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.mpris.MediaPlayer2.Player.Play"), shell=True)


def spotify_win_play_song(sp_track_uri_id, method=SPOTIFY_WINDOWS_PLAYING_METHOD):
    WIN_SPOTIFY_APP_PATH = r'%APPDATA%\Spotify\Spotify.exe'

    if method == "start-uri":      # start-uri
        subprocess.call((f"start spotify:track:{sp_track_uri_id}"), shell=True)
    elif method == "spotify-cmd":  # spotify-cmd
        subprocess.call((f"{WIN_SPOTIFY_APP_PATH} --uri=spotify:track:{sp_track_uri_id}"), shell=True)
    else:                          # trigger-url - just trigger track URL in the client
        getattr(os, "startfile")(spotify_convert_uri_to_url(f"spotify:track:{sp_track_uri_id}"))


# Finds an optional config file
def find_config_file(cli_path=None):
    """
    Search for an optional config file in:
      1) CLI-provided path (must exist if given)
      2) ./{DEFAULT_CONFIG_FILENAME}
      3) ~/.{DEFAULT_CONFIG_FILENAME}
      4) script-directory/{DEFAULT_CONFIG_FILENAME}
    """

    if cli_path:
        p = Path(os.path.expanduser(cli_path))
        return str(p) if p.is_file() else None

    candidates = [
        Path.cwd() / DEFAULT_CONFIG_FILENAME,
        Path.home() / f".{DEFAULT_CONFIG_FILENAME}",
        Path(__file__).parent / DEFAULT_CONFIG_FILENAME,
    ]

    for p in candidates:
        if p.is_file():
            return str(p)
    return None


# Loads one UTF-8 Python config atomically and optionally collects structured failures
def load_config_file(config_path, namespace=None, error_out=None, report_errors=True):
    target_namespace = globals() if namespace is None else namespace
    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            source = config_file.read()
        compiled = compile(source, str(config_path), "exec")
        candidate_namespace = dict(target_namespace)
        exec(compiled, candidate_namespace)
        candidate_namespace.pop("__builtins__", None)
        target_namespace.update(candidate_namespace)
        return True
    except SyntaxError as exc:
        details = [f"Config file '{config_path}' has invalid Python syntax"]
        if exc.lineno is not None:
            details.append(f"Line: {exc.lineno}")
        if exc.text:
            details.append(f"Source: {exc.text.rstrip()}")
        details.append(f"Parser: {exc.msg}")
        advice = classify_recovery_error(exc, "config_invalid", " | ".join(details))
        if error_out is not None:
            error_out.append(advice)
        if report_errors:
            print(f"* Error: {details[0]}")
            for item in details[1:]:
                print(f"* {item}")
            print("To fix: Correct the line and matching quotes. For Windows paths use forward slashes or doubled backslashes then retry.")
            print(f"Guide: {CONFIG_GUIDE_URL}")
        return False
    except UnicodeDecodeError as exc:
        advice = classify_recovery_error(exc, "config_invalid", f"Config file '{config_path}' is not valid UTF-8")
        if error_out is not None:
            error_out.append(advice)
        if report_errors:
            print(f"* Error: Config file '{config_path}' is not valid UTF-8")
            print("To fix: Save the file as UTF-8 then retry.")
            print(f"Guide: {CONFIG_GUIDE_URL}")
        return False
    except Exception as exc:
        advice = classify_recovery_error(exc, "config_invalid", f"Config file '{config_path}' failed with {type(exc).__name__}: {exc}")
        if error_out is not None:
            error_out.append(advice)
        if report_errors:
            print(render_recovery_error(RecoveryError(advice)))
        return False


# Creates one doctor result while ensuring all displayed fields are secret-safe
def make_doctor_check(section: str, status: str, label: str, detail: Any = "", advice: Optional[RecoveryAdvice] = None) -> DoctorCheck:
    if status not in ("PASS", "WARN", "FAIL"):
        raise ValueError(f"Unsupported doctor status: {status}")
    return DoctorCheck(section, status, sanitize_error_text(label), sanitize_error_text(detail), advice)


# Checks the active Python version and required or optional runtime dependencies
def doctor_check_environment(version_info=None, spec_finder: Optional[Callable[[str], Any]] = None) -> List[DoctorCheck]:
    checks: List[DoctorCheck] = []
    selected_version = sys.version_info if version_info is None else version_info
    version_text = ".".join(str(part) for part in tuple(selected_version)[:3])
    if tuple(selected_version)[:2] >= (3, 9):
        checks.append(make_doctor_check("Environment", "PASS", f"Python {version_text} is supported"))
    else:
        advice = make_recovery_advice("dependency.missing", f"Python {version_text} is unsupported", "Install Python 3.9 or newer then retry", False)
        checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    find_spec = importlib.util.find_spec if spec_finder is None else spec_finder
    required = (("requests", "requests"), ("dateutil", "python-dateutil"), ("urllib3", "urllib3"), ("dotenv", "python-dotenv"), ("wcwidth", "wcwidth"), ("pyotp", "pyotp"))
    for module_name, package_name in required:
        try:
            present = find_spec(module_name) is not None
        except (ImportError, ValueError):
            present = False
        if present:
            checks.append(make_doctor_check("Environment", "PASS", f"Required dependency {package_name} is installed"))
        else:
            advice = make_recovery_advice("dependency.missing", f"Required dependency {package_name} is missing", f"Install {package_name} then retry", False)
            checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    optional = (("spotipy", "Spotipy", "legacy OAuth metadata only"), ("pycookiecheat", "pycookiecheat", "Chromium browser import only"))
    for module_name, package_name, purpose in optional:
        try:
            present = find_spec(module_name) is not None
        except (ImportError, ValueError):
            present = False
        if present:
            checks.append(make_doctor_check("Environment", "PASS", f"Optional dependency {package_name} is installed", purpose))
        else:
            checks.append(make_doctor_check("Environment", "WARN", f"Optional dependency {package_name} is not installed", f"Optional: {purpose}. Normal monitoring is unaffected when this feature is unused"))
    return checks


# Returns the container playback warning only when host auto-play was requested
def container_playback_warning() -> Optional[str]:
    if is_container_environment() and TRACK_SONGS:
        return CONTAINER_PLAYBACK_WARNING
    return None


# Reports the default container host playback limitation without failing the doctor
def doctor_check_container_playback() -> List[DoctorCheck]:
    warning = container_playback_warning()
    if warning is None:
        return []
    return [make_doctor_check("Environment", "WARN", "Container host Spotify auto-play is unavailable by default", warning)]


# Returns the nearest existing parent for a path without creating directories
def nearest_existing_parent(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.exists():
        return candidate if candidate.is_dir() else candidate.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


# Validates effective config values and configured file destinations without writing them
def doctor_check_configuration(config_path=None, env_path=None, startup_checks: Sequence[DoctorCheck] = ()) -> List[DoctorCheck]:
    checks = list(startup_checks)
    if not any(check.section == "Configuration" and "configuration file" in check.label.lower() for check in checks):
        if config_path:
            checks.append(make_doctor_check("Configuration", "PASS", "Configuration file loaded", str(config_path)))
        else:
            checks.append(make_doctor_check("Configuration", "PASS", "No configuration file selected", "Using built-in defaults and command-line overrides"))
    if not any(check.section == "Configuration" and "dotenv" in check.label.lower() for check in checks):
        if env_path:
            checks.append(make_doctor_check("Configuration", "PASS", "Dotenv file loaded", str(env_path)))
        else:
            checks.append(make_doctor_check("Configuration", "PASS", "No dotenv file selected", "Using environment variables and other configured sources"))

    if TOKEN_SOURCE not in ("cookie", "client"):
        advice = classify_recovery_error(context="config_invalid", detail=f"TOKEN_SOURCE must be cookie or client, not {TOKEN_SOURCE!r}")
        checks.append(make_doctor_check("Configuration", "FAIL", "TOKEN_SOURCE is invalid", advice.detail, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", f"TOKEN_SOURCE is {TOKEN_SOURCE}"))

    numeric_values = (("SPOTIFY_CHECK_INTERVAL", SPOTIFY_CHECK_INTERVAL, 1, None), ("SPOTIFY_ERROR_INTERVAL", SPOTIFY_ERROR_INTERVAL, 0, None), ("SPOTIFY_INACTIVITY_CHECK", SPOTIFY_INACTIVITY_CHECK, 0, None), ("SPOTIFY_DISAPPEARED_CHECK_INTERVAL", SPOTIFY_DISAPPEARED_CHECK_INTERVAL, 0, None), ("SMTP_PORT", SMTP_PORT, 1, 65535))
    invalid_numeric = []
    for name, value, minimum, maximum in numeric_values:
        valid = isinstance(value, (int, float)) and not isinstance(value, bool) and value >= minimum and (maximum is None or value <= maximum)
        if not valid:
            invalid_numeric.append(f"{name}={value!r}")
    if invalid_numeric:
        advice = classify_recovery_error(context="config_invalid", detail="Invalid numeric settings: " + ", ".join(invalid_numeric))
        checks.append(make_doctor_check("Configuration", "FAIL", "One or more numeric settings are invalid", advice.detail, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "Numeric intervals and ports are valid"))

    if MONITOR_LIST_FILE:
        monitor_path = Path(MONITOR_LIST_FILE).expanduser()
        if monitor_path.is_file() and os.access(monitor_path, os.R_OK):
            checks.append(make_doctor_check("Configuration", "PASS", "Monitored-track list is readable", str(monitor_path)))
        else:
            advice = classify_recovery_error(context="file_read", detail=f"Monitored-track list is unreadable: {monitor_path}")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice))

    destinations = []
    if CSV_FILE:
        destinations.append(("CSV destination", Path(CSV_FILE)))
    if not DISABLE_LOGGING and SP_LOGFILE:
        destinations.append(("Log destination", Path(SP_LOGFILE)))
    for label, destination in destinations:
        parent = nearest_existing_parent(destination)
        if parent.is_dir() and os.access(parent, os.W_OK):
            checks.append(make_doctor_check("Configuration", "PASS", f"{label} appears writable", str(destination.expanduser())))
        else:
            advice = classify_recovery_error(context="file_write", detail=f"{label} is not writable: {destination.expanduser()}")
            checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice))
    return checks


# Validates configured Spotify credentials and returns reusable buddy-list data
def doctor_check_authentication(report: DoctorReport) -> List[DoctorCheck]:
    checks: List[DoctorCheck] = []
    context = "cookie_auth" if TOKEN_SOURCE == "cookie" else "client_auth"
    try:
        if TOKEN_SOURCE == "cookie":
            if is_missing_or_placeholder(SP_DC_COOKIE, ("your_sp_dc_cookie_value",)):
                advice = classify_recovery_error(context="secret", detail="SP_DC_COOKIE is missing or still a placeholder")
                advice = make_recovery_advice("secret.missing", "SP_DC_COOKIE is missing or still a placeholder", recovery_fix_with_guide(cookie_auth_recovery_fix(), COOKIE_GUIDE_URL), False)
                report.authentication_advice = advice
                return [make_doctor_check("Authentication", "FAIL", advice.summary, advice=advice)]
            access_token = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
        elif TOKEN_SOURCE == "client":
            values = {"DEVICE_ID": DEVICE_ID, "SYSTEM_ID": SYSTEM_ID, "USER_URI_ID": USER_URI_ID, "REFRESH_TOKEN": REFRESH_TOKEN}
            client_settings = {"APP_VERSION": APP_VERSION, "CPU_ARCH": CPU_ARCH, "OS_BUILD": OS_BUILD, "PLATFORM": PLATFORM, "OS_MAJOR": OS_MAJOR, "OS_MINOR": OS_MINOR, "CLIENT_MODEL": CLIENT_MODEL}
            placeholders = {"DEVICE_ID": "your_spotify_app_device_id", "SYSTEM_ID": "your_spotify_app_system_id", "USER_URI_ID": "your_spotify_user_uri_id", "REFRESH_TOKEN": "your_spotify_app_refresh_token"}
            if LOGIN_REQUEST_BODY_FILE:
                try:
                    parsed_values = parse_login_request_body_file(Path(LOGIN_REQUEST_BODY_FILE).expanduser())
                    values.update(dict(zip(("DEVICE_ID", "SYSTEM_ID", "USER_URI_ID", "REFRESH_TOKEN"), parsed_values)))
                    checks.append(make_doctor_check("Authentication", "PASS", "Login Protobuf file parsed read-only", str(Path(LOGIN_REQUEST_BODY_FILE).expanduser())))
                except Exception as exc:
                    advice = classify_recovery_error(exc, "file_read", f"Login Protobuf file could not be parsed: {exc}")
                    report.authentication_advice = advice
                    return checks + [make_doctor_check("Authentication", "FAIL", "Login Protobuf file is unreadable or malformed", advice.detail, advice)]
            missing = [name for name, value in values.items() if is_missing_or_placeholder(value, (placeholders[name],))]
            if missing:
                advice = make_recovery_advice("secret.missing", "Client mode is missing required values", "Provide " + ", ".join(missing) + " or re-export the Spotify desktop login request as documented", False)
                report.authentication_advice = advice
                return checks + [make_doctor_check("Authentication", "FAIL", advice.summary, "Missing: " + ", ".join(missing), advice)]
            if CLIENTTOKEN_REQUEST_BODY_FILE:
                try:
                    parsed_client_values = parse_clienttoken_request_body_file(Path(CLIENTTOKEN_REQUEST_BODY_FILE).expanduser())
                    client_settings.update(dict(zip(("APP_VERSION", "_DEVICE_ID", "_SYSTEM_ID", "CPU_ARCH", "OS_BUILD", "PLATFORM", "OS_MAJOR", "OS_MINOR", "CLIENT_MODEL"), parsed_client_values)))
                    checks.append(make_doctor_check("Authentication", "PASS", "Client-token Protobuf file parsed read-only", str(Path(CLIENTTOKEN_REQUEST_BODY_FILE).expanduser())))
                except Exception as exc:
                    advice = classify_recovery_error(exc, "file_read", f"Client-token Protobuf file could not be parsed: {exc}")
                    report.authentication_advice = advice
                    return checks + [make_doctor_check("Authentication", "FAIL", "Client-token Protobuf file is unreadable or malformed", advice.detail, advice)]
            if not client_settings["APP_VERSION"]:
                try:
                    client_settings["APP_VERSION"] = ua_to_app_version(USER_AGENT)
                except Exception:
                    client_settings["APP_VERSION"] = "1.2.62.580.g7e3d9a4f"
            temporary_values = {**values, **{key: value for key, value in client_settings.items() if not key.startswith("_")}}
            saved_values = {key: globals().get(key) for key in temporary_values}
            try:
                globals().update(temporary_values)
                access_token = spotify_get_access_token_from_client_auto(values["DEVICE_ID"], values["SYSTEM_ID"], values["USER_URI_ID"], values["REFRESH_TOKEN"])
            finally:
                globals().update(saved_values)
        else:
            advice = classify_recovery_error(context="config_invalid", detail=f"Unsupported TOKEN_SOURCE: {TOKEN_SOURCE}")
            report.authentication_advice = advice
            return [make_doctor_check("Authentication", "FAIL", advice.summary, advice.detail, advice)]

        buddy_list = spotify_get_friends_json(access_token)
        report.access_token = access_token
        report.buddy_list = buddy_list
        checks.append(make_doctor_check("Authentication", "PASS", f"Spotify {TOKEN_SOURCE} authentication succeeded", "Access token validated through the buddy-list endpoint"))
    except Exception as exc:
        advice = classify_recovery_error(exc, context)
        report.authentication_advice = advice
        checks.append(make_doctor_check("Authentication", "FAIL", advice.summary, advice.detail, advice))
    return checks


# Reports Spotify connectivity using the authenticated request already performed
def doctor_check_connectivity(report: DoctorReport) -> List[DoctorCheck]:
    if report.buddy_list is not None:
        return [make_doctor_check("Connectivity", "PASS", "Spotify is reachable", "Confirmed through the authenticated buddy-list request")]
    advice = report.authentication_advice
    if advice is not None and advice.code in ("network.unavailable", "network.timeout", "spotify.rate_limited", "spotify.unavailable"):
        return [make_doctor_check("Connectivity", "FAIL", advice.summary, advice.detail, advice)]
    skip_advice = make_recovery_advice("unknown", "Spotify connectivity could not be checked", "Fix the authentication or configuration failure above then run --doctor again", True)
    return [make_doctor_check("Connectivity", "WARN", "Spotify connectivity check was skipped", "Authentication did not produce a reusable buddy-list response", skip_advice)]


# Validates an optional target and checks whether buddy-list data can currently observe it
def doctor_check_target(report: DoctorReport, target_value=None) -> List[DoctorCheck]:
    if target_value is None or target_value == "":
        advice = classify_recovery_error(context="target_missing")
        return [make_doctor_check("Target", "WARN", "No Spotify target was provided", "Authentication-only preflight completed", advice)]
    try:
        target_id = resolve_target_user_id(target_value, None)
    except ValueError as exc:
        advice = classify_recovery_error(exc, "target_invalid")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]
    if report.buddy_list is None:
        advice = make_recovery_advice("unknown", "Live target visibility could not be checked", "Fix the authentication or connectivity failure above then run --doctor again", True)
        return [make_doctor_check("Target", "WARN", f"Target '{target_id}' live check was skipped", "No authenticated buddy-list response is available", advice)]
    try:
        found, _ = spotify_get_friend_info(report.buddy_list, target_id)
    except Exception as exc:
        advice = classify_recovery_error(exc, "target")
        return [make_doctor_check("Target", "FAIL", "The buddy-list response could not be inspected", advice.detail, advice)]
    if found:
        return [make_doctor_check("Target", "PASS", f"Target '{target_id}' can be monitored", "The target is visible in the authenticated buddy list")]
    advice = classify_recovery_error(context="target_not_visible", detail=f"Target '{target_id}' was absent from the authenticated buddy list")
    return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]


# Checks optional OAuth metadata configuration without creating an OAuth cache
def doctor_check_optional_oauth() -> List[DoctorCheck]:
    client_present = not is_missing_or_placeholder(SP_APP_CLIENT_ID, ("your_spotify_app_client_id",))
    secret_present = not is_missing_or_placeholder(SP_APP_CLIENT_SECRET, ("your_spotify_app_client_secret",))
    if not client_present and not secret_present:
        return [make_doctor_check("Authentication", "PASS", "Legacy OAuth metadata credentials are not configured", "The web-player metadata backend remains available")]
    if client_present != secret_present:
        advice = make_recovery_advice("secret.missing", "Legacy OAuth metadata credentials are incomplete", "Set both SP_APP_CLIENT_ID and SP_APP_CLIENT_SECRET or remove both to use the web-player backend", False)
        return [make_doctor_check("Authentication", "WARN", advice.summary, "The web-player metadata backend remains available", advice)]
    try:
        spotipy_present = importlib.util.find_spec("spotipy") is not None
    except (ImportError, ValueError):
        spotipy_present = False
    if not spotipy_present:
        advice = make_recovery_advice("dependency.missing", "Spotipy is missing for configured legacy OAuth metadata credentials", "Install spotify_monitor[legacy-oauth] or remove the optional credentials. The web-player fallback remains available", False)
        return [make_doctor_check("Authentication", "WARN", advice.summary, advice=advice)]
    return [make_doctor_check("Authentication", "PASS", "Optional legacy OAuth metadata configuration is complete", "No OAuth token was requested and no cache was written")]


# Determines whether email notifications are effectively enabled
def email_notifications_enabled() -> bool:
    event_notifications = any((ACTIVE_NOTIFICATION, INACTIVE_NOTIFICATION, TRACK_NOTIFICATION, SONG_NOTIFICATION, SONG_ON_LOOP_NOTIFICATION))
    configured_host = bool(SMTP_HOST) and not str(SMTP_HOST).startswith("your_smtp_server_")
    return bool(event_notifications or (ERROR_NOTIFICATION and configured_host))


# Determines whether Discord-compatible webhook notifications are effectively enabled
def webhook_notifications_enabled() -> bool:
    event_notifications = any((WEBHOOK_ACTIVE_NOTIFICATION, WEBHOOK_INACTIVE_NOTIFICATION, WEBHOOK_TRACK_NOTIFICATION, WEBHOOK_SONG_NOTIFICATION, WEBHOOK_SONG_ON_LOOP_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION))
    return bool(WEBHOOK_ENABLED and event_notifications)


# Validates SMTP configuration and login without sending an email
def doctor_check_notifications() -> List[DoctorCheck]:
    if not email_notifications_enabled():
        return [make_doctor_check("Notifications", "PASS", "Email notifications are disabled", "No SMTP connection was attempted and no email was sent")]
    validation_error = validate_smtp_configuration()
    if validation_error is not None:
        return [make_doctor_check("Notifications", "FAIL", validation_error.summary, validation_error.detail, validation_error)]
    smtp_object = None
    try:
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=5)
        try:
            smtp_object.quit()
        finally:
            smtp_object = None
        return [make_doctor_check("Notifications", "PASS", "SMTP connection and login succeeded", "No email was sent")]
    except Exception as exc:
        advice = classify_recovery_error(exc, "smtp")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception:
                pass


# Validates webhook settings locally without contacting the endpoint
def doctor_check_webhook_notifications() -> List[DoctorCheck]:
    if not WEBHOOK_ENABLED:
        return [make_doctor_check("Notifications", "PASS", "Webhook notifications are disabled", "No webhook request was attempted")]
    if not validate_webhook_url():
        advice = classify_recovery_error(context="webhook_config", detail="WEBHOOK_URL must be a complete HTTPS endpoint")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not webhook_notifications_enabled():
        advice = make_recovery_advice("webhook.invalid", "Webhook delivery is enabled but no event categories are selected", "Enable at least one WEBHOOK_*_NOTIFICATION setting or disable WEBHOOK_ENABLED", False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "No webhook request was attempted", advice)]
    return [make_doctor_check("Notifications", "PASS", "Webhook URL format and event settings are valid", "The secret URL was not displayed and no webhook request was attempted")]


# Builds all independent and dependent doctor checks before rendering
def build_doctor_report(target_value=None, config_path=None, env_path=None, startup_checks: Sequence[DoctorCheck] = (), version_info=None, spec_finder: Optional[Callable[[str], Any]] = None, progress: Optional[Callable[[str], None]] = None) -> DoctorReport:
    report = DoctorReport()
    if progress is not None:
        progress("environment")
    report.checks.extend(doctor_check_environment(version_info, spec_finder))
    report.checks.extend(doctor_check_container_playback())
    if progress is not None:
        progress("configuration")
    report.checks.extend(doctor_check_configuration(config_path, env_path, startup_checks))
    if progress is not None:
        progress("authentication")
    report.checks.extend(doctor_check_authentication(report))
    report.checks.extend(doctor_check_optional_oauth())
    if progress is not None:
        progress("connectivity")
    report.checks.extend(doctor_check_connectivity(report))
    if progress is not None:
        progress("target")
    report.checks.extend(doctor_check_target(report, target_value))
    if progress is not None:
        progress("notifications")
    report.checks.extend(doctor_check_notifications())
    report.checks.extend(doctor_check_webhook_notifications())
    return report


# Renders one sectioned ASCII doctor report with action lines for failures
def render_doctor_report(report: DoctorReport) -> str:
    lines = ["Doctor", "", "Read-only preflight. No email or webhook will be sent and no files will be written."]
    sections = ("Environment", "Configuration", "Authentication", "Connectivity", "Target", "Notifications")
    for section in sections:
        lines.extend(("", section))
        for check in (item for item in report.checks if item.section == section):
            lines.append(f"[{'PASS' if check.status == 'PASS' else check.status}] {check.label}")
            if check.detail:
                lines.append(f"  {check.detail}")
            rendered_advice = check.advice
            if check.status == "FAIL" and rendered_advice is None:
                rendered_advice = classify_recovery_error()
            if rendered_advice is not None and check.status in ("FAIL", "WARN"):
                lines.append(f"  To fix: {rendered_advice.fix}")
    failures = sum(check.status == "FAIL" for check in report.checks)
    warnings = sum(check.status == "WARN" for check in report.checks)
    lines.extend(("", "Summary", f"{failures} failure(s), {warnings} warning(s)", "", f"Guide: {DOCTOR_GUIDE_URL}"))
    return sanitize_error_text("\n".join(lines))


# Shows one transient doctor step only on an interactive terminal
def _doctor_progress(label: str) -> None:
    if sys.stdout.isatty():
        sys.stdout.write((f"\r* Checking {label} ...").ljust(79))
        sys.stdout.flush()


# Clears the transient doctor progress line on an interactive terminal
def _doctor_progress_clear() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\r" + (" " * 79) + "\r")
        sys.stdout.flush()


# Runs the read-only doctor preflight and returns zero unless at least one check fails
def run_doctor(target_value=None, config_path=None, env_path=None, startup_checks: Sequence[DoctorCheck] = ()) -> int:
    progress = _doctor_progress if sys.stdout.isatty() else None
    try:
        report = build_doctor_report(target_value, config_path, env_path, startup_checks, progress=progress)
    finally:
        _doctor_progress_clear()
    print(render_doctor_report(report))
    return 1 if any(check.status == "FAIL" for check in report.checks) else 0


# Resolves an executable path by checking if it's a valid file or searching in $PATH
def resolve_executable(path):
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path

    found = shutil.which(path)
    if found:
        return found

    raise FileNotFoundError(f"Could not find executable '{path}'")


# Prints a safe monitoring error while suppressing repeated equivalent fix hints
def print_monitor_recovery(error: Any, context: str, tracker: RecoveryHintTracker, prefix: str) -> RecoveryAdvice:
    advice = classify_recovery_error(error, context)
    print(prefix + advice.summary)
    if tracker.should_render(advice):
        print(f"  To fix: {advice.fix}")
        if DEBUG_MODE and advice.detail:
            print(f"  Technical detail: {sanitize_error_text(advice.detail)}")
    return advice


# Detects how Spotify Monitor was launched so setup can show matching commands
def _wizard_install_method() -> str:
    if is_container_environment():
        return "compose" if os.environ.get("SPOTIFY_MONITOR_COMPOSE") else "docker"
    return "manual" if os.path.basename(sys.argv[0] or "").endswith(".py") else "pip"


# Returns the portable command prefix for one supported installation method
def _wizard_cmd_prefix(method: str) -> str:
    if method == "compose":
        return "docker compose run --rm spotify_monitor"
    if method == "docker":
        return 'docker run --rm -it --init -v "$PWD:/data" misiektoja/spotify-monitor'
    if method == "manual":
        return "python3 spotify_monitor.py"
    return "spotify_monitor"


# Prints one labelled command with sibling-style indentation and spacing
def _wizard_print_command(label: str, command: str, suffix: str = "") -> None:
    print(label)
    print(f"    {command}{suffix}\n")


# Converts a wizard destination into the matching path inside the /data container mount
def _wizard_container_path(path) -> str:
    resolved = Path(path).expanduser().resolve()
    try:
        relative = resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        relative = Path(resolved.name)
    return str(Path("/data") / relative)


# Builds a Spotify Monitor action command using install-aware paths and an optional target
def _wizard_action_command(method: str, action: str, config_path, env_path, target: Optional[str] = None) -> str:
    parts = [_wizard_cmd_prefix(method)]
    if action:
        parts.append(action)
    if target:
        parts.append(shlex.quote(target))
    if config_path is not None:
        selected_config = _wizard_container_path(config_path) if method in ("docker", "compose") else str(Path(config_path).expanduser().resolve())
        parts.extend(("--config-file", shlex.quote(selected_config)))
    if env_path is not None:
        selected_env = _wizard_container_path(env_path) if method in ("docker", "compose") else str(Path(env_path).expanduser().resolve())
        parts.extend(("--env-file", shlex.quote(selected_env)))
    return " ".join(parts)


# Returns the Firefox import command with a read-only Linux host profile mount for containers
def _wizard_firefox_import_cmd(method: str, env_path=None) -> str:
    prefix = _wizard_cmd_prefix(method)
    if method == "docker":
        prefix = prefix.replace("misiektoja/spotify-monitor", '-v "$HOME/.mozilla/firefox:/home/spotify/.mozilla/firefox:ro" misiektoja/spotify-monitor')
    elif method == "compose":
        prefix = 'docker compose run --rm -v "$HOME/.mozilla/firefox:/home/spotify/.mozilla/firefox:ro" spotify_monitor'
    command = f"{prefix} --import-browser-cookie --browser firefox"
    if env_path is not None:
        selected_env = _wizard_container_path(env_path) if method in ("docker", "compose") else str(Path(env_path).expanduser().resolve())
        command += f" --env-file {shlex.quote(selected_env)}"
    return command


# Returns the hidden manual sp_dc entry command for one installation method
def _wizard_set_sp_dc_cmd(method: str, env_path=None) -> str:
    command = f"{_wizard_cmd_prefix(method)} --set-sp-dc"
    if env_path is not None:
        selected_env = _wizard_container_path(env_path) if method in ("docker", "compose") else str(Path(env_path).expanduser().resolve())
        command += f" --env-file {shlex.quote(selected_env)}"
    return command


# Returns the hidden webhook URL entry command for one installation method
def _wizard_set_webhook_url_cmd(method: str, env_path=None) -> str:
    command = f"{_wizard_cmd_prefix(method)} --set-webhook-url"
    if env_path is not None:
        selected_env = _wizard_container_path(env_path) if method in ("docker", "compose") else str(Path(env_path).expanduser().resolve())
        command += f" --env-file {shlex.quote(selected_env)}"
    return command


# Builds install-aware examples for argparse help output
def _build_help_epilog() -> str:
    method = _wizard_install_method()
    prefix = _wizard_cmd_prefix(method)
    protobuf_file = "/data/login.protobuf" if method in ("docker", "compose") else "<protobuf_file>"
    sections = [
        "Examples:",
        "  # Guided setup, recommended for the first run",
        f"  {prefix} --setup",
        "",
    ]
    if method in ("docker", "compose"):
        sections.extend((
            "  # Enter the Spotify cookie through a hidden prompt (recommended for Docker)",
            f"  {_wizard_set_sp_dc_cmd(method, Path.cwd() / '.env')}",
            "",
            "  # Advanced Linux host example: mount a Firefox profile read-only",
            "  # Open https://open.spotify.com/ in Firefox on the host and sign in first",
            f"  {_wizard_firefox_import_cmd(method)}",
            "",
            "  # Host Spotify auto-play is unavailable by default inside containers",
            "  # Run Spotify Monitor locally for TRACK_SONGS or --track-in-spotify",
            "",
        ))
    else:
        sections.extend((
            "  # Open https://open.spotify.com/ in Firefox and sign in first",
            "  # Then import Spotify login from Firefox (recommended for local installs)",
            f"  {_wizard_firefox_import_cmd(method)}",
            "",
            "  # Or enter the Spotify cookie through a hidden prompt",
            f"  {_wizard_set_sp_dc_cmd(method)}",
            "",
        ))
    webhook_env = Path.cwd() / ".env" if method in ("docker", "compose") else None
    sections.extend((
        "  # Store a Discord-compatible webhook URL through a hidden prompt",
        f"  {_wizard_set_webhook_url_cmd(method, webhook_env)}",
        "",
        "  # Send one test webhook without starting monitoring",
        f"  {prefix} --send-test-webhook",
        "",
    ))
    sections.extend((
        "  # Monitor one Spotify user",
        "  # A spotify:user URI or profile URL is also accepted",
        f"  {prefix} <spotify_user_id>",
        "",
        "  # Check authentication, connectivity and one target",
        f"  {prefix} --doctor <spotify_user_id>",
        "",
        "  # List friends visible to the configured Spotify account",
        f"  {prefix} --list-friends",
        "",
        "  # Advanced Spotify desktop client mode",
        f"  {prefix} <spotify_user_id> --token-source client --login-request-body-file {protobuf_file}",
    ))
    if method == "compose":
        sections.extend(("", "  # Start from the target saved by setup", "  docker compose up"))
    sections.extend(("", f"Guide: {QUICK_START_GUIDE_URL}"))
    return "\n".join(sections) + "\n"


# Lists browsers supported by the setup wizard in the active environment
def _wizard_import_browsers(method: str) -> List[str]:
    if platform.system() == "Windows" or method in ("docker", "compose"):
        return ["firefox"]
    return list(IMPORT_BROWSERS)


# Describes one browser import choice without exposing browser data
def _wizard_browser_description(browser: str) -> str:
    if browser == "firefox":
        return "Built-in reader for macOS, Linux and Windows with no extra package."
    return f"{browser_label(browser)} needs the browser extra and works on macOS or Linux only."


# Reads one setup line and exits cleanly when Ctrl+C or Ctrl+D cancels input
def _wizard_input(prompt_text: str) -> str:
    try:
        return input(prompt_text)
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        raise SystemExit(1) from None


# Prompts for optional or required text while applying an Enter default safely
def _wizard_ask_text(question: str, default: str = "", required: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = _wizard_input(f"{question}{suffix}: ").strip()
        if not value:
            value = default
        if value or not required:
            return value
        print("  This value is required.")


# Prompts until the user provides a valid yes or no response
def _wizard_ask_yes_no(question: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        value = _wizard_input(f"{question} {hint}: ").strip().casefold()
        if not value:
            return default
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Displays numbered choices and returns the selected zero-based index
def _wizard_ask_choice(question: str, options, default_index: int = 0) -> int:
    print(question)
    for index, option in enumerate(options, start=1):
        label, description = option
        marker = " (default)" if index - 1 == default_index else ""
        print(f"  {index}. {label}{marker}")
        if description:
            for line in description.splitlines():
                print(f"     {line}")
    while True:
        value = _wizard_input(f"Choose [1-{len(options)}]: ").strip()
        if not value:
            return default_index
        if value.isdigit() and 1 <= int(value) <= len(options):
            return int(value) - 1
        print(f"  Enter a number between 1 and {len(options)}.")


# Prompts until the user provides a positive integer or accepts the default
def _wizard_ask_positive_int(question: str, default: int) -> int:
    while True:
        value = _wizard_ask_text(question, default=str(default), required=True)
        try:
            parsed = int(value)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed
        print("  Enter a positive whole number.")


# Reads a required secret through getpass without echoing the entered value
def _wizard_ask_secret(question: str) -> str:
    while True:
        try:
            value = getpass.getpass(f"{question}: ")
        except (EOFError, KeyboardInterrupt):
            print("\nSetup cancelled.")
            raise SystemExit(1) from None
        if value:
            return value
        print("  This secret is required and cannot be empty.")


# Resolves setup destinations without searching parent directories
def _wizard_destinations(config_file=None, env_file=None):
    if env_file is not None and str(env_file).casefold() == "none":
        raise ValueError("--setup requires a dotenv destination. Replace '--env-file none' with a writable path.")
    config_path = Path(config_file or DEFAULT_CONFIG_FILENAME).expanduser().resolve()
    env_path = Path(env_file or ".env").expanduser().resolve()
    return config_path, env_path


# Confirms replacement or selects another config destination before secrets are collected
def _wizard_choose_config_destination(config_path: Path) -> Path:
    selected = config_path
    while selected.exists() and not _wizard_ask_yes_no(f"Configuration file '{selected}' exists. Replace it and create a timestamped backup?", default=False):
        alternative = _wizard_ask_text("Another config destination or leave empty to cancel")
        if not alternative:
            print("Setup cancelled. Destination files were not changed.")
            raise SystemExit(1)
        selected = Path(alternative).expanduser().resolve()
    return selected


# Returns whether a non-placeholder secret exists in the selected dotenv file or environment
def _wizard_existing_secret(key: str, env_path: Path, placeholders: Sequence[str] = ()) -> bool:
    value = None
    if env_path.is_file():
        try:
            from dotenv import dotenv_values
            value = dotenv_values(env_path, interpolate=False).get(key)
        except Exception:
            value = None
    if value is None:
        value = os.environ.get(key)
    return not is_missing_or_placeholder(value, placeholders)


# Queues one secret update after confirming replacement of an existing dotenv assignment
def _wizard_queue_secret(updates: dict, env_path: Path, key: str, value: str) -> bool:
    try:
        existing_assignment = _dotenv_contains_key(env_path, key)
    except BrowserCookieImportError as exc:
        print(render_recovery_error(exc, "config_invalid"))
        raise SystemExit(1) from None
    if existing_assignment and not _wizard_ask_yes_no(f"The dotenv file already contains {key}. Replace that value?", default=False):
        print(f"  Existing {key} will be retained without being displayed or rewritten.")
        return False
    updates[key] = value
    return True


# Prompts for one valid Spotify target and returns its normalized user ID
def _wizard_target(initial_target: Optional[str] = None) -> str:
    default = initial_target or ""
    while True:
        raw_target = _wizard_ask_text("Spotify user to monitor", default=default, required=True)
        try:
            return normalize_spotify_user_id(raw_target)
        except ValueError:
            print("  Use a raw user ID, spotify:user:USER_ID or https://open.spotify.com/user/USER_ID.")
            default = ""


# Validates proposed SMTP values through the shared validator without connecting
def _wizard_validate_smtp(values: dict, password: str) -> Optional[RecoveryAdvice]:
    names = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL", "RECEIVER_EMAIL")
    previous = {name: globals()[name] for name in names}
    try:
        globals().update(values)
        globals()["SMTP_PASSWORD"] = password
        return validate_smtp_configuration()
    finally:
        globals().update(previous)


# Collects SMTP settings and notification flags without opening a connection
def _wizard_collect_email(config_values: dict, secret_updates: dict, env_path: Path) -> List[str]:
    notification_names = ("ACTIVE_NOTIFICATION", "INACTIVE_NOTIFICATION", "TRACK_NOTIFICATION", "SONG_NOTIFICATION", "SONG_ON_LOOP_NOTIFICATION", "ERROR_NOTIFICATION")
    if not _wizard_ask_yes_no("Configure email notifications?", default=False):
        config_values.update({name: False for name in notification_names})
        return []
    while True:
        smtp_values = {
            "SMTP_HOST": _wizard_ask_text("SMTP host", required=True),
            "SMTP_PORT": _wizard_ask_positive_int("SMTP port", 587),
            "SMTP_SSL": _wizard_ask_yes_no("Use STARTTLS?", default=True),
            "SMTP_USER": _wizard_ask_text("SMTP username", required=True),
            "SENDER_EMAIL": _wizard_ask_text("Sender email", required=True),
            "RECEIVER_EMAIL": _wizard_ask_text("Receiver email", required=True),
        }
        smtp_password = _wizard_ask_secret("SMTP password")
        advice = _wizard_validate_smtp(smtp_values, smtp_password)
        if advice is None:
            break
        print(f"  {advice.summary}: {advice.detail}")
        print("  Re-enter the SMTP settings.")
    _wizard_queue_secret(secret_updates, env_path, "SMTP_PASSWORD", smtp_password)
    config_values.update(smtp_values)
    preset = _wizard_ask_choice("Which email notifications should be enabled?", [("Status and errors, recommended", "Active, inactive and error notifications."), ("Every supported event", "Enables all email notification types."), ("Custom", "Choose each notification type separately.")])
    if preset == 0:
        selected = {"ACTIVE_NOTIFICATION": True, "INACTIVE_NOTIFICATION": True, "TRACK_NOTIFICATION": False, "SONG_NOTIFICATION": False, "SONG_ON_LOOP_NOTIFICATION": False, "ERROR_NOTIFICATION": True}
    elif preset == 1:
        selected = {name: True for name in notification_names}
    else:
        questions = (("ACTIVE_NOTIFICATION", "Email when the user becomes active?"), ("INACTIVE_NOTIFICATION", "Email when the user becomes inactive?"), ("TRACK_NOTIFICATION", "Email when a tracked song plays?"), ("SONG_NOTIFICATION", "Email for every song change?"), ("SONG_ON_LOOP_NOTIFICATION", "Email when a song loops?"), ("ERROR_NOTIFICATION", "Email on monitoring errors?"))
        selected = {name: _wizard_ask_yes_no(question, default=False) for name, question in questions}
    config_values.update(selected)
    labels = {"ACTIVE_NOTIFICATION": "active", "INACTIVE_NOTIFICATION": "inactive", "TRACK_NOTIFICATION": "tracked song", "SONG_NOTIFICATION": "every song", "SONG_ON_LOOP_NOTIFICATION": "loop detection", "ERROR_NOTIFICATION": "errors"}
    return [labels[name] for name in notification_names if selected[name]]


# Collects one hidden webhook secret and independent event settings without making a request
def _wizard_collect_webhook(config_values: dict, secret_updates: dict, env_path: Path) -> List[str]:
    notification_names = ("WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_TRACK_NOTIFICATION", "WEBHOOK_SONG_NOTIFICATION", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION")
    if not _wizard_ask_yes_no("Configure Discord-compatible webhook notifications?", default=False):
        config_values["WEBHOOK_ENABLED"] = False
        config_values.update({name: False for name in notification_names})
        return []
    existing_webhook = _wizard_existing_secret("WEBHOOK_URL", env_path, ("your_discord_webhook_url",))
    replace_webhook = True
    if existing_webhook:
        choice = _wizard_ask_choice("How should the webhook secret be configured?", [("Retain the existing WEBHOOK_URL", "Keeps the non-placeholder value without displaying or rewriting it."), ("Enter a replacement privately", "Uses a hidden prompt and saves only after local format validation.")])
        replace_webhook = choice == 1
    if replace_webhook:
        while True:
            webhook_url = _wizard_ask_secret("Discord-compatible webhook URL")
            if validate_webhook_url(webhook_url):
                break
            print("  Enter a complete HTTPS webhook URL.")
        if existing_webhook:
            secret_updates["WEBHOOK_URL"] = webhook_url
        else:
            _wizard_queue_secret(secret_updates, env_path, "WEBHOOK_URL", webhook_url)
    config_values["WEBHOOK_ENABLED"] = True
    config_values["WEBHOOK_USERNAME"] = "Spotify Monitor"
    preset = _wizard_ask_choice("Which webhook notifications should be enabled?", [("Status and errors, recommended", "Active, inactive and error notifications."), ("Every supported event", "Enables all webhook notification types."), ("Custom", "Choose each webhook notification type separately.")])
    if preset == 0:
        selected = {"WEBHOOK_ACTIVE_NOTIFICATION": True, "WEBHOOK_INACTIVE_NOTIFICATION": True, "WEBHOOK_TRACK_NOTIFICATION": False, "WEBHOOK_SONG_NOTIFICATION": False, "WEBHOOK_SONG_ON_LOOP_NOTIFICATION": False, "WEBHOOK_ERROR_NOTIFICATION": True}
    elif preset == 1:
        selected = {name: True for name in notification_names}
    else:
        questions = (("WEBHOOK_ACTIVE_NOTIFICATION", "Webhook when the user becomes active?"), ("WEBHOOK_INACTIVE_NOTIFICATION", "Webhook when the user becomes inactive?"), ("WEBHOOK_TRACK_NOTIFICATION", "Webhook when a tracked song plays?"), ("WEBHOOK_SONG_NOTIFICATION", "Webhook for every song change?"), ("WEBHOOK_SONG_ON_LOOP_NOTIFICATION", "Webhook when a song loops?"), ("WEBHOOK_ERROR_NOTIFICATION", "Webhook on monitoring errors?"))
        selected = {name: _wizard_ask_yes_no(question, default=False) for name, question in questions}
    config_values.update(selected)
    labels = {"WEBHOOK_ACTIVE_NOTIFICATION": "active", "WEBHOOK_INACTIVE_NOTIFICATION": "inactive", "WEBHOOK_TRACK_NOTIFICATION": "tracked song", "WEBHOOK_SONG_NOTIFICATION": "every song", "WEBHOOK_SONG_ON_LOOP_NOTIFICATION": "loop detection", "WEBHOOK_ERROR_NOTIFICATION": "errors"}
    return [labels[name] for name in notification_names if selected[name]]


# Collects cookie-mode choices while keeping all secret values out of output
def _wizard_collect_cookie_auth(method: str, env_path: Path, secret_updates: dict) -> dict:
    result = {"complete": False, "validated": False, "browser": None, "source": "not configured", "mount_required": False}
    container_method = method in ("docker", "compose")
    existing_cookie = _wizard_existing_secret("SP_DC_COOKIE", env_path, ("your_sp_dc_cookie_value",))
    while True:
        if container_method:
            if existing_cookie:
                options = [("Retain the existing SP_DC_COOKIE", "Keep the non-placeholder value without displaying or rewriting it."), ("Enter sp_dc privately (recommended for Docker)", "Uses a hidden getpass prompt and stores the value only in the selected dotenv file."), ("Import from Firefox (advanced)", "Requires the host Firefox profile mounted read-only into this container."), ("Finish without credentials", "Save an incomplete setup and configure authentication later.")]
                actions = ("existing", "manual", "browser", "finish")
            else:
                options = [("Enter sp_dc privately (recommended for Docker)", "Uses a hidden getpass prompt and stores the value only in the selected dotenv file."), ("Import from Firefox (advanced)", "Requires the host Firefox profile mounted read-only into this container."), ("Finish without credentials", "Save an incomplete setup and configure authentication later.")]
                actions = ("manual", "browser", "finish")
        else:
            options = [("Import from a browser, recommended", "Sign in at https://open.spotify.com/ in that browser first. Firefox is the default. Chromium-family imports need the browser extra."), ("Use an existing SP_DC_COOKIE", "Retain a non-placeholder value from the selected dotenv file or environment."), ("Paste an existing sp_dc value privately", "The value is read through getpass and saved only after confirmation."), ("Finish without credentials", "Save an incomplete setup and import later.")]
            actions = ("browser", "existing", "manual", "finish")
        action = actions[_wizard_ask_choice("How should cookie authentication be configured?", options)]
        if action == "browser":
            browsers = _wizard_import_browsers(method)
            browser_index = 0
            if len(browsers) > 1:
                browser_index = _wizard_ask_choice("Which browser should be imported?", [(browser_label(browser), _wizard_browser_description(browser)) for browser in browsers])
            result.update({"browser": browsers[browser_index], "source": f"browser import ({browser_label(browsers[browser_index])})"})
            browser_location = f"{browser_label(browsers[browser_index])} on the host" if method in ("docker", "compose") else browser_label(browsers[browser_index])
            print(f"  Before import, open {SPOTIFY_WEB_LOGIN_URL} in {browser_location} and sign in to the Spotify account used for monitoring.")
            if method in ("docker", "compose"):
                result.update({"source": "advanced Firefox import pending a read-only host profile mount", "mount_required": True})
                print("  This advanced container path requires the host Firefox profile mounted read-only.")
                print("  Chromium cookie import is unavailable inside containers.")
            return result
        if action == "existing":
            if not existing_cookie:
                print("  No non-placeholder SP_DC_COOKIE was found.")
                continue
            if _wizard_ask_yes_no("Retain the existing SP_DC_COOKIE without displaying or rewriting it?", default=True):
                result.update({"complete": True, "source": "existing SP_DC_COOKIE"})
                return result
            continue
        if action == "manual":
            cookie = _wizard_ask_secret("Existing sp_dc value")
            replaced = _wizard_queue_secret(secret_updates, env_path, "SP_DC_COOKIE", cookie)
            result.update({"complete": replaced or _wizard_existing_secret("SP_DC_COOKIE", env_path, ("your_sp_dc_cookie_value",)), "source": "private manual entry" if replaced else "existing SP_DC_COOKIE"})
            return result
        return result


# Collects advanced client-mode Protobuf values through read-only parsers
def _wizard_collect_client_auth(config_values: dict, env_path: Path, secret_updates: dict) -> dict:
    print("Client mode is advanced.")
    print(f"Guide: {CLIENT_GUIDE_URL}\n")
    result = {"complete": False, "validated": False, "browser": None, "source": "advanced client mode without credentials"}
    if not _wizard_ask_yes_no("Use an exported login request Protobuf file?", default=True):
        return result
    while True:
        login_path_text = _wizard_ask_text("Login request Protobuf path or leave empty to finish incomplete")
        if not login_path_text:
            return result
        login_path = Path(login_path_text).expanduser().resolve()
        try:
            device_id, system_id, user_uri_id, refresh_token = parse_login_request_body_file(login_path)
        except Exception:
            print(render_recovery_error(context="file_read", detail=f"Login Protobuf file '{login_path}' could not be parsed read-only"))
            if not _wizard_ask_yes_no("Try another login Protobuf file?", default=True):
                return result
            continue
        if not all(isinstance(value, str) and value for value in (device_id, system_id, user_uri_id, refresh_token)):
            print("The login Protobuf did not contain all required text values.")
            if not _wizard_ask_yes_no("Try another login Protobuf file?", default=True):
                return result
            continue
        config_values.update({"LOGIN_REQUEST_BODY_FILE": str(login_path), "DEVICE_ID": device_id, "SYSTEM_ID": system_id, "USER_URI_ID": user_uri_id})
        _wizard_queue_secret(secret_updates, env_path, "REFRESH_TOKEN", cast(str, refresh_token))
        result.update({"complete": True, "source": "login request Protobuf"})
        break
    if _wizard_ask_yes_no("Use an optional client-token request Protobuf file?", default=False):
        while True:
            client_path_text = _wizard_ask_text("Client-token request Protobuf path or leave empty to skip")
            if not client_path_text:
                break
            client_path = Path(client_path_text).expanduser().resolve()
            try:
                parsed = parse_clienttoken_request_body_file(client_path)
            except Exception:
                print(render_recovery_error(context="file_read", detail=f"Client-token Protobuf file '{client_path}' could not be parsed read-only"))
                if _wizard_ask_yes_no("Try another client-token Protobuf file?", default=True):
                    continue
                break
            names = ("APP_VERSION", "_DEVICE_ID", "_SYSTEM_ID", "CPU_ARCH", "OS_BUILD", "PLATFORM", "OS_MAJOR", "OS_MINOR", "CLIENT_MODEL")
            config_values.update({name: value for name, value in zip(names, parsed) if not name.startswith("_") and value is not None})
            config_values["CLIENTTOKEN_REQUEST_BODY_FILE"] = str(client_path)
            break
    return result


# Loads the generated config and only allowlisted dotenv secrets for the doctor offer
def _wizard_load_effective_setup(config_path: Path, env_path: Path) -> bool:
    if not load_config_file(config_path):
        return False
    selected_secrets = {key: os.environ.get(key) for key in SECRET_KEYS}
    if env_path.is_file():
        try:
            from dotenv import dotenv_values
            parsed = dotenv_values(env_path, interpolate=False)
            selected_secrets.update({key: parsed.get(key) for key in SECRET_KEYS if parsed.get(key) is not None})
        except Exception:
            print(render_recovery_error(context="config_invalid", detail=f"Dotenv file '{env_path}' could not be loaded"))
            return False
    for key, value in selected_secrets.items():
        if value is not None:
            globals()[key] = value
    return True


# Completes a deferred browser import with retry, private entry or incomplete recovery choices
def _wizard_finish_browser_import(auth: dict, env_path: Path) -> dict:
    browser = auth.get("browser")
    if not browser:
        return auth
    while True:
        try:
            run_browser_cookie_import(browser=browser, env_file=str(env_path), interactive=True, input_func=_wizard_input)
            auth.update({"complete": True, "validated": True})
            return auth
        except BrowserCookieImportError as exc:
            print(render_recovery_error(exc, "browser_import"))
        recovery = _wizard_ask_choice("Browser import did not complete. What next?", [("Retry browser import", "Try discovery, extraction and validation again."), ("Enter sp_dc privately", "Save a manually extracted value through getpass."), ("Finish without authentication", "Keep the generated config and import later.")])
        if recovery == 0:
            continue
        if recovery == 1:
            cookie = _wizard_ask_secret("Existing sp_dc value")
            try:
                if _wizard_queue_secret({}, env_path, "SP_DC_COOKIE", cookie):
                    update_dotenv_file(env_path, {"SP_DC_COOKIE": cookie})
                    auth.update({"complete": True, "validated": False, "source": "private manual entry"})
            except Exception:
                print(f"Config was saved but dotenv destination '{env_path}' could not be updated.")
                auth.update({"complete": False, "validated": False})
            return auth
        auth.update({"complete": False, "validated": False})
        return auth


# Prints a short no-argument welcome and optionally launches guided setup
def _wizard_welcome() -> None:
    method = _wizard_install_method()
    prefix = _wizard_cmd_prefix(method)
    interactive = sys.stdin.isatty()
    _wizard_print_command("Quickest start (already configured):", f"{prefix} <spotify_user_id>")
    setup_suffix = "   (or just answer Y below)" if interactive else ""
    _wizard_print_command("Easiest start (guided setup wizard):", f"{prefix} --setup", setup_suffix)
    _wizard_print_command("Check setup before monitoring:", f"{prefix} --doctor <spotify_user_id>")
    print(f"Full options: {prefix} --help")
    print(f"\nGuide:        {QUICK_START_GUIDE_URL}\n")
    if interactive and _wizard_ask_yes_no("Run the guided setup wizard now?", default=True):
        run_setup_wizard()


# Runs the interactive Phase 4 wizard and persists confirmed settings through safe writers
def run_setup_wizard(initial_target: Optional[str] = None, config_file=None, env_file=None) -> None:
    if not sys.stdin.isatty():
        print("The setup wizard needs an interactive terminal (TTY).")
        print("Run --setup from an interactive shell or use --generate-config and edit the files manually.")
        print(f"Guide: {QUICK_START_GUIDE_URL}")
        raise SystemExit(1)
    try:
        config_path, env_path = _wizard_destinations(config_file, env_file)
    except ValueError as exc:
        print(f"Setup cannot start: {exc}")
        raise SystemExit(1) from None
    method = _wizard_install_method()
    print("\nSetup Wizard\n")
    print("This asks a few questions and writes a ready-to-run configuration.")
    print("Press Enter to accept the shown default. Ctrl+C cancels.\n")
    print("Secrets go to the dotenv file. Non-secret settings go to the config file.")
    print("Cookie mode is recommended. Client mode is advanced.\n")
    print(f"Detected install method: {method}")
    print(f"Configuration:          {config_path}")
    print(f"Dotenv:                 {env_path}\n")
    config_path = _wizard_choose_config_destination(config_path)
    target = _wizard_target(initial_target)
    persist_target = _wizard_ask_yes_no("Persist this target in the generated config?", default=True)
    config_values = dict(globals())
    config_values["TARGET_USER_URI_ID"] = target if persist_target else ""
    secret_updates = {}
    print()
    cookie_onboarding = "Private hidden sp_dc entry is recommended for Docker and Docker Compose." if method in ("docker", "compose") else "Browser import is the recommended local onboarding path and Firefox is the easiest source."
    auth_mode = _wizard_ask_choice("Choose an authentication mode", [("Cookie mode using sp_dc, recommended", cookie_onboarding), ("Client mode using Spotify desktop credentials, advanced", "Uses exported Protobuf request bodies.")])
    if auth_mode == 0:
        config_values["TOKEN_SOURCE"] = "cookie"
        auth = _wizard_collect_cookie_auth(method, env_path, secret_updates)
    else:
        config_values["TOKEN_SOURCE"] = "client"
        auth = _wizard_collect_client_auth(config_values, env_path, secret_updates)
    print()
    config_values["SPOTIFY_CHECK_INTERVAL"] = _wizard_ask_positive_int("Spotify polling interval in seconds", SPOTIFY_CHECK_INTERVAL)
    print()
    enabled_notifications = _wizard_collect_email(config_values, secret_updates, env_path)
    print()
    enabled_webhooks = _wizard_collect_webhook(config_values, secret_updates, env_path)
    print("\nSetup summary\n")
    print(f"  Target: {target}")
    print(f"  Persist target: {'yes' if persist_target else 'no'}")
    print(f"  Token source: {auth['source']}")
    print(f"  Authentication status: {'complete' if auth['complete'] else 'incomplete'}")
    if auth.get("mount_required"):
        print("  Required action: mount the host Firefox profile read-only and run the separate import command shown below")
    if auth.get("browser"):
        print(f"  Browser: {browser_label(auth['browser'])}")
    print(f"  Polling interval: {config_values['SPOTIFY_CHECK_INTERVAL']} seconds")
    print(f"  Email: {'enabled' if enabled_notifications else 'disabled'}")
    print(f"  Email notifications: {', '.join(enabled_notifications) if enabled_notifications else 'none'}")
    print(f"  Webhook: {'enabled' if enabled_webhooks else 'disabled'}")
    print(f"  Webhook notifications: {', '.join(enabled_webhooks) if enabled_webhooks else 'none'}")
    print(f"  Config destination: {config_path}")
    print(f"  Dotenv destination: {env_path}")
    print(f"  Install method: {method}")
    if not _wizard_ask_yes_no("Write these settings now?", default=True):
        print("Setup cancelled. Destination files were not changed.")
        raise SystemExit(1)
    config_content = generate_config_with_current_values(config_values)
    try:
        write_status = write_config_file(config_path, config_content)
    except Exception:
        print(f"Setup could not write configuration file '{config_path}'. No dotenv changes were attempted.")
        raise SystemExit(1) from None
    print("\nSaved files\n")
    print(f"  Configuration: {write_status['path']}")
    if write_status["backup_path"]:
        print(f"  Backup:        {write_status['backup_path']}")
    if secret_updates:
        try:
            update_status = update_dotenv_file(env_path, secret_updates)
            print(f"  Secrets:       {update_status['path']}")
        except Exception:
            print(f"Configuration was saved but dotenv destination '{env_path}' could not be updated.")
            print("Setup remains incomplete.")
            raise SystemExit(1) from None
    if auth.get("browser") and method not in ("docker", "compose"):
        auth = _wizard_finish_browser_import(auth, env_path)
    doctor_failed = False
    doctor_ran = False
    print()
    if _wizard_ask_yes_no("Run the read-only doctor now?", default=True):
        doctor_ran = True
        if _wizard_load_effective_setup(config_path, env_path):
            try:
                report = build_doctor_report(target, str(config_path), str(env_path), progress=_doctor_progress)
            finally:
                _doctor_progress_clear()
            print(render_doctor_report(report))
            doctor_failed = any(check.status == "FAIL" for check in report.checks)
            if not doctor_failed:
                auth["validated"] = True
        else:
            doctor_failed = True
    doctor_target = None if persist_target else target
    doctor_command = _wizard_action_command(method, "--doctor", config_path, env_path, doctor_target)
    monitor_target = None if persist_target else target
    monitor_command = _wizard_action_command(method, "", config_path, env_path, monitor_target)
    print("\nNext steps\n")
    _wizard_print_command("Check setup again:", doctor_command)
    if not auth["complete"]:
        print("Setup was saved but authentication is incomplete.")
        if method in ("docker", "compose"):
            _wizard_print_command("Enter sp_dc privately (recommended for Docker):", _wizard_set_sp_dc_cmd(method, env_path))
            _wizard_print_command("Advanced Firefox alternative with a read-only Linux host profile mount:", _wizard_firefox_import_cmd(method, env_path))
        else:
            _wizard_print_command("Import Spotify login from Firefox (recommended locally):", _wizard_firefox_import_cmd(method, env_path))
            _wizard_print_command("Or enter sp_dc privately:", _wizard_set_sp_dc_cmd(method, env_path))
        print(f"Cookie guide: {COOKIE_GUIDE_URL}\n")
    if method == "compose" and persist_target and auth["complete"] and not doctor_failed:
        _wizard_print_command("Start monitoring:", "docker compose up")
    else:
        if method == "compose" and not persist_target:
            print("docker compose up requires a persisted target. Use this direct command instead:")
        else:
            print("Start monitoring:")
        print(f"    {monitor_command}\n")
    print(f"Guide: {QUICK_START_GUIDE_URL}\n")
    local_ready = method in ("manual", "pip") and auth["complete"] and not doctor_failed and (auth["validated"] or doctor_ran)
    if local_ready and _wizard_ask_yes_no("Start monitoring now?", default=True):
        exec_args = [sys.executable, str(Path(__file__).resolve())]
        if not persist_target:
            exec_args.append(target)
        exec_args.extend(("--config-file", str(config_path), "--env-file", str(env_path)))
        sys.stdout.flush()
        os.execv(sys.executable, exec_args)
    elif method in ("manual", "pip") and auth["complete"] and not auth["validated"]:
        print("Monitoring was not offered because authentication has not been validated. Run the doctor command first.")
    if doctor_failed:
        print("Setup was saved but is not ready. Fix the doctor failures then rerun the doctor command.")
    raise SystemExit(0)


# Monitors music activity of the specified Spotify friend's user URI ID
def spotify_monitor_friend_uri(user_uri_id, tracks, csv_file_name):
    global SP_CACHED_ACCESS_TOKEN
    sp_active_ts_start = 0
    sp_active_ts_stop = 0
    sp_active_ts_start_old = 0
    user_not_found = False
    listened_songs = 0
    listened_songs_old = 0
    looped_songs = 0
    looped_songs_old = 0
    skipped_songs = 0
    skipped_songs_old = 0
    sp_artist_old = ""
    sp_track_old = ""
    song_on_loop = 0
    recent_songs_session = []
    error_500_counter = 0
    error_500_start_ts = 0
    error_network_issue_counter = 0
    error_network_issue_start_ts = 0
    sp_accessToken = ""
    recovery_hint_tracker = RecoveryHintTracker()
    transient_request_failure_active = False

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print_recovery_error(e, "file_write", detail=f"CSV destination '{csv_file_name}' could not be initialized: {e}")

    email_sent = False
    webhook_sent = False

    out = f"Monitoring user {user_uri_id}"
    print(out)
    # print("─" * len(out))
    print("─" * HORIZONTAL_LINE)

    tracks_upper = {t.upper() for t in tracks}

    # Start loop
    while True:
        debug_print(f"Loop tick: token_source={TOKEN_SOURCE}, check_interval={SPOTIFY_CHECK_INTERVAL}, error_interval={SPOTIFY_ERROR_INTERVAL}")

        # Sometimes Spotify network functions halt even though we specified the timeout
        # To overcome this we use alarm signal functionality to kill it inevitably, not available on Windows
        if platform.system() != 'Windows':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(ALARM_TIMEOUT)
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)

            sp_friends = spotify_get_friends_json(sp_accessToken)
            sp_found, sp_data = spotify_get_friend_info(sp_friends, user_uri_id)
            recovery_hint_tracker.reset()
            debug_print(f"Friend lookup result: found={sp_found}")
            email_sent = False
            webhook_sent = False
            if platform.system() != 'Windows':
                signal.alarm(0)
        except TimeoutException:
            if platform.system() != 'Windows':
                signal.alarm(0)
            print_monitor_recovery(TimeoutException(f"Spotify request timed out after {display_time(ALARM_TIMEOUT)}"), "runtime", recovery_hint_tracker, f"* Error, retrying in {display_time(ALARM_RETRY)}: ")
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(ALARM_RETRY)
            continue
        except Exception as e:
            if platform.system() != 'Windows':
                signal.alarm(0)

            debug_print(f"Main monitor loop error: {e}")

            auth_context = "client_auth" if TOKEN_SOURCE == "client" else "cookie_auth"
            advice = print_monitor_recovery(e, auth_context, recovery_hint_tracker, f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: ")

            if TOKEN_SOURCE == 'cookie' and advice.code in ("auth.cookie_invalid", "auth.rejected"):
                SP_CACHED_ACCESS_TOKEN = None

            if TOKEN_SOURCE == 'client' and advice.code == "auth.client_invalid":
                if (ERROR_NOTIFICATION and not email_sent) or (webhook_event_enabled("error") and not webhook_sent):
                    safe_error = sanitize_error_text(e)
                    m_subject = f"spotify_monitor: client or refresh token may be invalid or expired! (uri: {user_uri_id})"
                    m_body = f"Client or refresh token may be invalid or expired!\n{safe_error}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>Client or refresh token may be invalid or expired!<br>{escape(safe_error)}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    email_attempted, webhook_attempted = send_notification_channels("error", m_subject, m_body, m_body_html, ERROR_NOTIFICATION and not email_sent, webhook_event_enabled("error") and not webhook_sent)
                    email_sent = email_sent or email_attempted
                    webhook_sent = webhook_sent or webhook_attempted

            elif TOKEN_SOURCE == 'cookie' and advice.code == "auth.cookie_invalid":
                if (ERROR_NOTIFICATION and not email_sent) or (webhook_event_enabled("error") and not webhook_sent):
                    safe_error = sanitize_error_text(e)
                    m_subject = f"spotify_monitor: sp_dc may be invalid/expired or Spotify has broken sth again! (uri: {user_uri_id})"
                    m_body = f"sp_dc may be invalid/expired or Spotify has broken sth again!\n{safe_error}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>sp_dc may be invalid/expired or Spotify has broken sth again!<br>{escape(safe_error)}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    email_attempted, webhook_attempted = send_notification_channels("error", m_subject, m_body, m_body_html, ERROR_NOTIFICATION and not email_sent, webhook_event_enabled("error") and not webhook_sent)
                    email_sent = email_sent or email_attempted
                    webhook_sent = webhook_sent or webhook_attempted

            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(SPOTIFY_ERROR_INTERVAL)
            continue

        playlist_m_body = ""
        playlist_m_body_html = ""
        played_for_m_body = ""
        played_for_m_body_html = ""
        is_playlist = False
        sp_playlist_owner = ""
        playlist_suffix = ""

        # User is found in the Spotify's friend list just after starting the tool
        if sp_found:
            user_not_found = False

            sp_track_uri = sp_data["sp_track_uri"]
            sp_track_uri_id = sp_data["sp_track_uri_id"]
            sp_album_uri = sp_data["sp_album_uri"]
            sp_playlist_uri = sp_data["sp_playlist_uri"]

            sp_playlist_data = {}
            try:
                sp_track_data = spotify_get_track_info(sp_accessToken, sp_track_uri)
                is_playlist = 'spotify:playlist:' in sp_playlist_uri
                if is_playlist:
                    sp_playlist_owner = spotify_get_playlist_owner(sp_accessToken, sp_playlist_uri)
                    playlist_suffix = SPOTIFY_SUFFIX if sp_playlist_owner == "Spotify" else ""

            except Exception as e:
                print_monitor_recovery(e, "metadata", recovery_hint_tracker, f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: ")
                print_cur_ts("Timestamp:\t\t\t")
                time.sleep(SPOTIFY_ERROR_INTERVAL)
                continue

            sp_username = sp_data["sp_username"]

            sp_artist = sp_data["sp_artist"]
            if not sp_artist:
                sp_artist = sp_track_data["sp_artist_name"]

            sp_track = sp_data["sp_track"]
            if not sp_track:
                sp_track = sp_track_data["sp_track_name"]

            sp_playlist = sp_data["sp_playlist"]

            sp_album = sp_data["sp_album"]
            if not sp_album:
                sp_album = sp_track_data["sp_album_name"]

            sp_ts = sp_data["sp_ts"]
            cur_ts = int(time.time())

            sp_track_duration = sp_track_data["sp_track_duration"]
            sp_track_url = sp_track_data["sp_track_url"]
            sp_artist_url = sp_track_data["sp_artist_url"]
            sp_album_url = sp_track_data["sp_album_url"]

            sp_playlist_url = ""
            if is_playlist:
                sp_playlist_url = spotify_convert_uri_to_url(sp_playlist_uri)
                playlist_m_body = f"\nPlaylist: {sp_playlist}{playlist_suffix}"
                playlist_m_body_html = f"<br>Playlist: <a href=\"{sp_playlist_url}\">{escape(sp_playlist)}{playlist_suffix}</a>"

            print(f"Username:\t\t\t{sp_username}")
            print(f"User URI ID:\t\t\t{sp_data['sp_uri']}")
            print(f"\nLast played:\t\t\t{sp_artist} - {sp_track}")
            print(f"Duration:\t\t\t{display_time(sp_track_duration)}\n")
            if is_playlist:
                print(f"Playlist:\t\t\t{sp_playlist}{playlist_suffix}")

            print(f"Album:\t\t\t\t{sp_album}")

            context_m_body = ""
            context_m_body_html = ""

            if 'spotify:album:' in sp_playlist_uri and sp_playlist != sp_album:
                print(f"\nContext (Album):\t\t{sp_playlist}")
                context_m_body += f"\nContext (Album): {sp_playlist}"
                context_m_body_html += f"<br>Context (Album): <a href=\"{spotify_convert_uri_to_url(sp_playlist_uri)}\">{escape(sp_playlist)}</a>"

            if 'spotify:artist:' in sp_playlist_uri:
                print(f"\nContext (Artist):\t\t{sp_playlist}")
                context_m_body += f"\nContext (Artist): {sp_playlist}"
                context_m_body_html += f"<br>Context (Artist): <a href=\"{spotify_convert_uri_to_url(sp_playlist_uri)}\">{escape(sp_playlist)}</a>"

            print(f"\nTrack URL:\t\t\t{sp_track_url}")
            if is_playlist:
                print(f"Playlist URL:\t\t\t{sp_playlist_url}")
            print(f"Album URL:\t\t\t{sp_album_url}")

            if 'spotify:album:' in sp_playlist_uri and sp_playlist != sp_album:
                print(f"Context (Album) URL:\t\t{spotify_convert_uri_to_url(sp_playlist_uri)}")

            if 'spotify:artist:' in sp_playlist_uri:
                print(f"Context (Artist) URL:\t\t{spotify_convert_uri_to_url(sp_playlist_uri)}")

            apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url = get_apple_genius_search_urls(str(sp_artist), str(sp_track))

            music_urls_output = format_music_urls_console(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
            if music_urls_output:
                print(music_urls_output)
            lyrics_output = format_lyrics_urls_console(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
            if lyrics_output:
                print(lyrics_output)

            if not is_playlist:
                sp_playlist = ""

            print(f"\nLast activity:\t\t\t{get_date_from_ts(sp_ts)} ({calculate_timespan(int(time.time()), sp_ts)} ago)")

            # Friend is currently active (listens to music)
            if (cur_ts - sp_ts) <= SPOTIFY_INACTIVITY_CHECK:
                sp_active_ts_start = sp_ts - sp_track_duration
                sp_active_ts_stop = 0
                listened_songs = 1
                song_on_loop = 1
                recent_songs_session = [{'artist': sp_artist, 'track': sp_track, 'timestamp': sp_ts, 'skipped': False}]
                print("\n*** Friend is currently ACTIVE !")

                if FLAG_FILE:
                    flag_file_create()

                if sp_track.upper() in tracks_upper or sp_playlist.upper() in tracks_upper or sp_album.upper() in tracks_upper:
                    print("*** Track/playlist/album matched with the list!")

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, datetime.fromtimestamp(int(cur_ts)), sp_artist, sp_track, sp_playlist, sp_album, datetime.fromtimestamp(int(sp_ts)))
                except Exception as e:
                    print_recovery_error(e, "file_write", detail=f"CSV destination '{csv_file_name}' could not be written: {e}")

                if ACTIVE_NOTIFICATION or webhook_event_enabled("active"):
                    music_urls_text = format_music_urls_email_text(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                    music_urls_html = format_music_urls_email_html(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, sp_artist, sp_track)
                    lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                    lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, sp_artist, sp_track)
                    if music_urls_text:
                        music_section_text = f"\n\n{music_urls_text}"
                        music_section_html = f"<br><br>{music_urls_html}"
                        lyrics_section_text = f"\n{lyrics_urls_text}\n\n" if lyrics_urls_text else "\n\n"
                        lyrics_section_html = f"<br>{lyrics_urls_html}<br><br>" if lyrics_urls_html else "<br><br>"
                    else:
                        if lyrics_urls_text:
                            music_section_text = "\n\n"
                            music_section_html = "<br><br>"
                            lyrics_section_text = f"{lyrics_urls_text}\n\n"
                            lyrics_section_html = f"{lyrics_urls_html}<br><br>"
                        else:
                            music_section_text = "\n\n"
                            music_section_html = "<br><br>"
                            lyrics_section_text = ""
                            lyrics_section_html = ""
                    m_subject = f"Spotify user {sp_username} is active: '{sp_artist} - {sp_track}'"
                    m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}{music_section_text}{lyrics_section_text}Songs played: {listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})\n\nLast activity: {get_date_from_ts(sp_ts)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}{music_section_html}{lyrics_section_html}Songs played: {listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})<br><br>Last activity: {get_date_from_ts(sp_ts)}{get_cur_ts('<br>Timestamp: ')}</body></html>"
                    send_notification_channels("active", m_subject, m_body, m_body_html, ACTIVE_NOTIFICATION)

                if TRACK_SONGS and sp_track_uri_id:
                    if platform.system() == 'Darwin':       # macOS
                        spotify_macos_play_song(sp_track_uri_id)
                    elif platform.system() == 'Windows':    # Windows
                        spotify_win_play_song(sp_track_uri_id)
                    else:                                   # Linux variants
                        spotify_linux_play_song(sp_track_uri_id)

            # Friend is currently offline (does not play music)
            else:
                sp_active_ts_stop = sp_ts
                print(f"\n*** Friend is OFFLINE for: {calculate_timespan(int(cur_ts), int(sp_ts))}")

            if listened_songs:
                print(f"\nSongs played:\t\t\t{listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})")

            print(f"\nTracks/playlists/albums to monitor: {tracks}")
            print_cur_ts("\nTimestamp:\t\t\t")

            sp_ts_old = sp_ts
            alive_counter = 0

            email_sent = False

            disappeared_counter = 0

            playlist_suffix = ""
            check_count = 0

            # Primary loop
            while True:
                check_count += 1
                check_started_at = debug_monitor_check_start(check_count, user_uri_id)

                while True:
                    # Sometimes Spotify network functions halt even though we specified the timeout
                    # To overcome this we use alarm signal functionality to kill it inevitably, not available on Windows
                    if platform.system() != 'Windows':
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(ALARM_TIMEOUT)
                    try:
                        if TOKEN_SOURCE == "client":
                            sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
                        else:
                            sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)

                        sp_friends = spotify_get_friends_json(sp_accessToken)
                        sp_found, sp_data = spotify_get_friend_info(sp_friends, user_uri_id)
                        if transient_request_failure_active:
                            verbose_print("Spotify requests recovered after a transient failure")
                            transient_request_failure_active = False
                        recovery_hint_tracker.reset()
                        email_sent = False
                        if platform.system() != 'Windows':
                            signal.alarm(0)
                        break
                    except TimeoutException:
                        if platform.system() != 'Windows':
                            signal.alarm(0)
                        print_monitor_recovery(TimeoutException(f"Spotify request timed out after {display_time(ALARM_TIMEOUT)}"), "runtime", recovery_hint_tracker, f"* Error, retrying in {display_time(ALARM_RETRY)}: ")
                        print_cur_ts("Timestamp:\t\t\t")
                        time.sleep(ALARM_RETRY)
                    except Exception as e:
                        if platform.system() != 'Windows':
                            signal.alarm(0)

                        auth_context = "client_auth" if TOKEN_SOURCE == "client" else "cookie_auth"
                        advice = classify_recovery_error(e, auth_context)

                        if (advice.code in ("spotify.unavailable", "network.unavailable", "network.timeout", "spotify.rate_limited") or str(e) == '') and not transient_request_failure_active:
                            verbose_print(f"{advice.summary}. Automatic retries are active")
                            transient_request_failure_active = True

                        if TOKEN_SOURCE == 'cookie' and advice.code in ("auth.cookie_invalid", "auth.rejected"):
                            SP_CACHED_ACCESS_TOKEN = None

                        if advice.code == "spotify.unavailable":
                            if not error_500_start_ts:
                                error_500_start_ts = int(time.time())
                                error_500_counter = 1
                            else:
                                error_500_counter += 1

                        if advice.code in ("network.unavailable", "network.timeout", "spotify.rate_limited") or str(e) == '':
                            if not error_network_issue_start_ts:
                                error_network_issue_start_ts = int(time.time())
                                error_network_issue_counter = 1
                            else:
                                error_network_issue_counter += 1

                        if error_500_start_ts and (error_500_counter >= ERROR_500_NUMBER_LIMIT and (int(time.time()) - error_500_start_ts) >= ERROR_500_TIME_LIMIT):
                            print_monitor_recovery(e, auth_context, recovery_hint_tracker, f"* Error 50x ({error_500_counter}x times in the last {display_time((int(time.time()) - error_500_start_ts))}): ")
                            print_cur_ts("Timestamp:\t\t\t")
                            error_500_start_ts = 0
                            error_500_counter = 0

                        elif error_network_issue_start_ts and (error_network_issue_counter >= ERROR_NETWORK_ISSUES_NUMBER_LIMIT and (int(time.time()) - error_network_issue_start_ts) >= ERROR_NETWORK_ISSUES_TIME_LIMIT):
                            print_monitor_recovery(e, auth_context, recovery_hint_tracker, f"* Error with network ({error_network_issue_counter}x times in the last {display_time((int(time.time()) - error_network_issue_start_ts))}): ")
                            print_cur_ts("Timestamp:\t\t\t")
                            error_network_issue_start_ts = 0
                            error_network_issue_counter = 0

                        elif not error_500_start_ts and not error_network_issue_start_ts:
                            print_monitor_recovery(e, auth_context, recovery_hint_tracker, f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: ")

                            if TOKEN_SOURCE == 'client' and advice.code == "auth.client_invalid":
                                if (ERROR_NOTIFICATION and not email_sent) or (webhook_event_enabled("error") and not webhook_sent):
                                    safe_error = sanitize_error_text(e)
                                    m_subject = f"spotify_monitor: client or refresh token may be invalid or expired! (uri: {user_uri_id})"
                                    m_body = f"Client or refresh token may be invalid or expired!\n{safe_error}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Client or refresh token may be invalid or expired!<br>{escape(safe_error)}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                                    email_attempted, webhook_attempted = send_notification_channels("error", m_subject, m_body, m_body_html, ERROR_NOTIFICATION and not email_sent, webhook_event_enabled("error") and not webhook_sent)
                                    email_sent = email_sent or email_attempted
                                    webhook_sent = webhook_sent or webhook_attempted

                            elif TOKEN_SOURCE == 'cookie' and advice.code == "auth.cookie_invalid":
                                if (ERROR_NOTIFICATION and not email_sent) or (webhook_event_enabled("error") and not webhook_sent):
                                    safe_error = sanitize_error_text(e)
                                    m_subject = f"spotify_monitor: sp_dc may be invalid/expired or Spotify has broken sth again! (uri: {user_uri_id})"
                                    m_body = f"sp_dc may be invalid/expired or Spotify has broken sth again!\n{safe_error}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>sp_dc may be invalid/expired or Spotify has broken sth again!<br>{escape(safe_error)}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                                    email_attempted, webhook_attempted = send_notification_channels("error", m_subject, m_body, m_body_html, ERROR_NOTIFICATION and not email_sent, webhook_event_enabled("error") and not webhook_sent)
                                    email_sent = email_sent or email_attempted
                                    webhook_sent = webhook_sent or webhook_attempted

                            print_cur_ts("Timestamp:\t\t\t")
                        time.sleep(SPOTIFY_ERROR_INTERVAL)

                if sp_found is False:
                    # User has disappeared from the Spotify's friend list or account has been removed
                    disappeared_counter += 1
                    if disappeared_counter == 1:
                        verbose_print(f"Target {user_uri_id} was absent from one buddy-list response. Waiting for confirmation before reporting disappearance")
                    if disappeared_counter < REMOVED_DISAPPEARED_COUNTER:
                        debug_monitor_check_timing(check_count, user_uri_id, check_started_at, SPOTIFY_CHECK_INTERVAL)
                        time.sleep(SPOTIFY_CHECK_INTERVAL)
                        continue
                    if user_not_found is False:
                        if is_user_removed(sp_accessToken, user_uri_id):
                            print(f"Spotify user '{user_uri_id}' ({sp_username}) was probably removed! Retrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals")
                            not_found_advice = make_recovery_advice("target.not_found", "The Spotify target profile returned HTTP 404", "Check the target ID, URI or profile URL then retry", False)
                            if recovery_hint_tracker.should_render(not_found_advice):
                                print(f"  To fix: {not_found_advice.fix}")
                            if ERROR_NOTIFICATION or webhook_event_enabled("error"):
                                m_subject = f"Spotify user {user_uri_id} ({sp_username}) was probably removed!"
                                m_body = f"Spotify user {user_uri_id} ({sp_username}) was probably removed\nRetrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                                m_body_html = f"<html><head></head><body>Spotify user {user_uri_id} (<b>{sp_username}</b>) was probably removed<br>Retrying in <b>{display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)}</b> intervals{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                                send_notification_channels("error", m_subject, m_body, m_body_html, ERROR_NOTIFICATION)
                        else:
                            print(f"Spotify user '{user_uri_id}' ({sp_username}) has disappeared - make sure your friend is followed and has activity sharing enabled. Retrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals")
                            not_visible_advice = classify_recovery_error(context="target_not_visible")
                            if recovery_hint_tracker.should_render(not_visible_advice):
                                print(f"  To fix: {not_visible_advice.fix}")
                            if ERROR_NOTIFICATION or webhook_event_enabled("error"):
                                m_subject = f"Spotify user {user_uri_id} ({sp_username}) has disappeared!"
                                m_body = f"Spotify user {user_uri_id} ({sp_username}) has disappeared - make sure your friend is followed and has activity sharing enabled\nRetrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                                m_body_html = f"<html><head></head><body>Spotify user {user_uri_id} (<b>{sp_username}</b>) has disappeared - make sure your friend is followed and has activity sharing enabled<br>Retrying in <b>{display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)}</b> intervals{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                                send_notification_channels("error", m_subject, m_body, m_body_html, ERROR_NOTIFICATION)
                        print_cur_ts("Timestamp:\t\t\t")
                        user_not_found = True
                    debug_monitor_check_timing(check_count, user_uri_id, check_started_at, SPOTIFY_DISAPPEARED_CHECK_INTERVAL)
                    time.sleep(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)
                    continue
                else:
                    # User reappeared in the Spotify's friend list
                    transient_visibility_misses = disappeared_counter
                    disappeared_counter = 0
                    if transient_visibility_misses and user_not_found is False:
                        verbose_print("Target visibility recovered before disappearance was confirmed")
                    if user_not_found is True:
                        print(f"Spotify user {user_uri_id} ({sp_username}) has reappeared!")
                        if ERROR_NOTIFICATION or webhook_event_enabled("error"):
                            m_subject = f"Spotify user {user_uri_id} ({sp_username}) has reappeared!"
                            m_body = f"Spotify user {user_uri_id} ({sp_username}) has reappeared!{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                            m_body_html = f"<html><head></head><body>Spotify user {user_uri_id} (<b>{sp_username}</b>) has reappeared!{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                            send_notification_channels("error", m_subject, m_body, m_body_html, ERROR_NOTIFICATION)
                        print_cur_ts("Timestamp:\t\t\t")

                user_not_found = False
                sp_ts = sp_data["sp_ts"]
                cur_ts = int(time.time())
                # Track has changed
                if sp_ts != sp_ts_old:
                    sp_artist_old = sp_artist
                    sp_track_old = sp_track
                    alive_counter = 0
                    sp_playlist = sp_data["sp_playlist"]
                    sp_track_uri = sp_data["sp_track_uri"]
                    sp_track_uri_id = sp_data["sp_track_uri_id"]
                    sp_album_uri = sp_data["sp_album_uri"]
                    sp_playlist_uri = sp_data["sp_playlist_uri"]
                    try:
                        sp_track_data = spotify_get_track_info(sp_accessToken, sp_track_uri)
                        is_playlist = 'spotify:playlist:' in sp_playlist_uri
                        if is_playlist:
                            sp_playlist_owner = spotify_get_playlist_owner(sp_accessToken, sp_playlist_uri)
                            playlist_suffix = SPOTIFY_SUFFIX if sp_playlist_owner == "Spotify" else ""
                    except Exception as e:
                        print_monitor_recovery(e, "metadata", recovery_hint_tracker, f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: ")
                        print_cur_ts("Timestamp:\t\t\t")
                        time.sleep(SPOTIFY_ERROR_INTERVAL)
                        continue

                    sp_username = sp_data["sp_username"]

                    sp_artist = sp_data["sp_artist"]
                    if not sp_artist:
                        sp_artist = sp_track_data["sp_artist_name"]

                    sp_track = sp_data["sp_track"]
                    if not sp_track:
                        sp_track = sp_track_data["sp_track_name"]

                    sp_album = sp_data["sp_album"]
                    if not sp_album:
                        sp_album = sp_track_data["sp_album_name"]

                    sp_track_duration = sp_track_data["sp_track_duration"]
                    sp_track_url = sp_track_data["sp_track_url"]
                    sp_artist_url = sp_track_data["sp_artist_url"]
                    sp_album_url = sp_track_data["sp_album_url"]

                    # If tracking functionality is enabled then play the current song via Spotify client

                    if TRACK_SONGS and sp_track_uri_id:
                        if platform.system() == 'Darwin':       # macOS
                            spotify_macos_play_song(sp_track_uri_id)
                        elif platform.system() == 'Windows':    # Windows
                            spotify_win_play_song(sp_track_uri_id)
                        else:                                   # Linux variants
                            spotify_linux_play_song(sp_track_uri_id)

                    if is_playlist:
                        sp_playlist_url = spotify_convert_uri_to_url(sp_playlist_uri)
                        playlist_m_body = f"\nPlaylist: {sp_playlist}{playlist_suffix}"
                        playlist_m_body_html = f"<br>Playlist: <a href=\"{sp_playlist_url}\">{escape(sp_playlist)}{playlist_suffix}</a>"
                    else:
                        playlist_m_body = ""
                        playlist_m_body_html = ""

                    if sp_artist == sp_artist_old and sp_track == sp_track_old:
                        song_on_loop += 1
                        if song_on_loop == SONG_ON_LOOP_VALUE:
                            looped_songs += 1
                    else:
                        song_on_loop = 1

                    print(f"Spotify user:\t\t\t{sp_username}")
                    print(f"\nLast played:\t\t\t{sp_artist} - {sp_track}")
                    print(f"Duration:\t\t\t{display_time(sp_track_duration)}")

                    listened_songs += 1

                    # Suppress "Played for" if this track is the first after inactivity
                    cur_ts = int(time.time())
                    resumed_after_offline = (sp_active_ts_stop > 0) and ((cur_ts - sp_ts_old) > SPOTIFY_INACTIVITY_CHECK)
                    song_skipped = False
                    if not resumed_after_offline and (sp_ts - sp_ts_old) < (sp_track_duration - 1):
                        played_for_time = sp_ts - sp_ts_old
                        listened_percentage = (played_for_time) / (sp_track_duration - 1)
                        played_for = display_time(played_for_time)
                        percentage_display = int(listened_percentage * 100)

                        if listened_percentage <= SKIPPED_SONG_THRESHOLD:
                            played_for += f" - SKIPPED ({percentage_display}%)"
                            skipped_songs += 1
                            song_skipped = True
                        else:
                            # Check for potential crossfade (within detection thresholds, not skipped)
                            # Use displayed percentage for comparison to match what user sees
                            crossfade_note = ""
                            if DETECT_CROSSFADED_SONGS:
                                percentage_for_check = percentage_display / 100.0
                                if CROSSFADE_DETECTION_MIN <= percentage_for_check <= CROSSFADE_DETECTION_MAX:
                                    crossfade_note = " - crossfade enabled"
                            played_for += f" ({percentage_display}%{crossfade_note})"
                        print(f"Played for:\t\t\t{played_for}")
                        played_for_m_body = f"\nPlayed for: {played_for}"
                        played_for_m_body_html = f"<br>Played for: {played_for}"
                    elif not resumed_after_offline:
                        # Song played for full duration or longer (e.g. pause, ad etc.)
                        played_for_time = sp_ts - sp_ts_old
                        time_diff = abs(played_for_time - sp_track_duration)
                        if time_diff > PLAYED_FOR_DURATION_TOLERANCE:
                            # Song was played significantly longer or shorter than its duration
                            played_for = display_time(played_for_time)
                            print(f"Played for:\t\t\t{played_for}")
                            played_for_m_body = f"\nPlayed for: {played_for}"
                            played_for_m_body_html = f"<br>Played for: {played_for}"
                        else:
                            # Song played within tolerance of its duration (treat as full duration, suppress "Played for")
                            played_for_m_body = ""
                            played_for_m_body_html = ""
                    else:
                        # First track after inactivity: do not show "Played for" and never mark as skipped
                        played_for_m_body = ""
                        played_for_m_body_html = ""

                    # Add current song to recent songs session list
                    recent_songs_session.append({
                        'artist': sp_artist,
                        'track': sp_track,
                        'timestamp': sp_ts,
                        'skipped': song_skipped
                    })
                    # Keep only last INACTIVE_EMAIL_RECENT_SONGS_COUNT songs (or 5 if not set)
                    max_songs = INACTIVE_EMAIL_RECENT_SONGS_COUNT if INACTIVE_EMAIL_RECENT_SONGS_COUNT > 0 else 5
                    if len(recent_songs_session) > max_songs:
                        recent_songs_session.pop(0)

                    if is_playlist:
                        print(f"Playlist:\t\t\t{sp_playlist}{playlist_suffix}")

                    print(f"Album:\t\t\t\t{sp_album}")

                    context_m_body = ""
                    context_m_body_html = ""

                    if 'spotify:album:' in sp_playlist_uri and sp_playlist != sp_album:
                        print(f"\nContext (Album):\t\t{sp_playlist}")
                        context_m_body += f"\nContext (Album): {sp_playlist}"
                        context_m_body_html += f"<br>Context (Album): <a href=\"{spotify_convert_uri_to_url(sp_playlist_uri)}\">{escape(sp_playlist)}</a>"

                    if 'spotify:artist:' in sp_playlist_uri:
                        print(f"\nContext (Artist):\t\t{sp_playlist}")
                        context_m_body += f"\nContext (Artist): {sp_playlist}"
                        context_m_body_html += f"<br>Context (Artist): <a href=\"{spotify_convert_uri_to_url(sp_playlist_uri)}\">{escape(sp_playlist)}</a>"

                    print(f"Last activity:\t\t\t{get_date_from_ts(sp_ts)}")

                    print(f"\nTrack URL:\t\t\t{sp_track_url}")
                    if is_playlist:
                        print(f"Playlist URL:\t\t\t{sp_playlist_url}")
                    print(f"Album URL:\t\t\t{sp_album_url}")

                    if 'spotify:album:' in sp_playlist_uri and sp_playlist != sp_album:
                        print(f"Context (Album) URL:\t\t{spotify_convert_uri_to_url(sp_playlist_uri)}")

                    if 'spotify:artist:' in sp_playlist_uri:
                        print(f"Context (Artist) URL:\t\t{spotify_convert_uri_to_url(sp_playlist_uri)}")

                    apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url = get_apple_genius_search_urls(str(sp_artist), str(sp_track))

                    music_urls_output = format_music_urls_console(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                    if music_urls_output:
                        print(music_urls_output)
                    lyrics_output = format_lyrics_urls_console(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                    if lyrics_output:
                        print(lyrics_output)

                    if not is_playlist:
                        sp_playlist = ""

                    if song_on_loop == SONG_ON_LOOP_VALUE:
                        print("─" * HORIZONTAL_LINE)
                        print(f"User plays song on LOOP ({song_on_loop} times)")
                        print("─" * HORIZONTAL_LINE)

                    # Friend got active after being offline
                    if (cur_ts - sp_ts_old) > SPOTIFY_INACTIVITY_CHECK and sp_active_ts_stop > 0:

                        sp_active_ts_start = sp_ts - sp_track_duration

                        listened_songs = 1
                        skipped_songs = 0
                        looped_songs = 0
                        song_on_loop = 1
                        recent_songs_session = [{'artist': sp_artist, 'track': sp_track, 'timestamp': sp_ts, 'skipped': False}]

                        if FLAG_FILE:
                            flag_file_create()

                        print(f"\n*** Friend got ACTIVE after being offline for {calculate_timespan(int(sp_active_ts_start), int(sp_active_ts_stop))} ({get_date_from_ts(sp_active_ts_stop)})")
                        m_subject = f"Spotify user {sp_username} is active: '{sp_artist} - {sp_track}' (after {calculate_timespan(int(sp_active_ts_start), int(sp_active_ts_stop), show_seconds=False)} - {get_short_date_from_ts(sp_active_ts_stop)})"
                        friend_active_m_body = f"Friend got active after being offline for {calculate_timespan(int(sp_active_ts_start), int(sp_active_ts_stop))}\nLast activity (before getting offline): {get_date_from_ts(sp_active_ts_stop)}"
                        friend_active_m_body_html = f"Friend got active after being offline for <b>{calculate_timespan(int(sp_active_ts_start), int(sp_active_ts_stop))}</b><br>Last activity (before getting offline): <b>{get_date_from_ts(sp_active_ts_stop)}</b>"
                        if (sp_active_ts_start - sp_active_ts_stop) < 30:
                            listened_songs = listened_songs_old
                            skipped_songs = skipped_songs_old
                            looped_songs = looped_songs_old
                            print(f"*** Inactivity timer ({display_time(SPOTIFY_INACTIVITY_CHECK)}) value might be too low, readjusting session start back to {get_short_date_from_ts(sp_active_ts_start_old)}")
                            friend_active_m_body += f"\nInactivity timer ({display_time(SPOTIFY_INACTIVITY_CHECK)}) value might be too low, readjusting session start back to {get_short_date_from_ts(sp_active_ts_start_old)}"
                            friend_active_m_body_html += f"<br>Inactivity timer (<b>{display_time(SPOTIFY_INACTIVITY_CHECK)}</b>) value might be <b>too low</b>, readjusting session start back to <b>{get_short_date_from_ts(sp_active_ts_start_old)}</b>"
                            if sp_active_ts_start_old > 0:
                                sp_active_ts_start = sp_active_ts_start_old
                        sp_active_ts_stop = 0

                        music_urls_text = format_music_urls_email_text(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                        music_urls_html = format_music_urls_email_html(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, sp_artist, sp_track)
                        lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                        lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, sp_artist, sp_track)
                        if music_urls_text:
                            music_section_text = f"\n\n{music_urls_text}"
                            music_section_html = f"<br><br>{music_urls_html}"
                            lyrics_section_text = f"\n{lyrics_urls_text}\n\n" if lyrics_urls_text else "\n\n"
                            lyrics_section_html = f"<br>{lyrics_urls_html}<br><br>" if lyrics_urls_html else "<br><br>"
                        else:
                            if lyrics_urls_text:
                                music_section_text = "\n\n"
                                music_section_html = "<br><br>"
                                lyrics_section_text = f"{lyrics_urls_text}\n\n"
                                lyrics_section_html = f"{lyrics_urls_html}<br><br>"
                            else:
                                music_section_text = "\n\n"
                                music_section_html = "<br><br>"
                                lyrics_section_text = ""
                                lyrics_section_html = ""
                        m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{played_for_m_body}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}{music_section_text}{lyrics_section_text}{friend_active_m_body}\n\nSongs played: {listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})\n\nLast activity: {get_date_from_ts(sp_ts)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{played_for_m_body_html}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}{music_section_html}{lyrics_section_html}{friend_active_m_body_html}<br><br>Songs played: {listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})<br><br>Last activity: {get_date_from_ts(sp_ts)}{get_cur_ts('<br>Timestamp: ')}</body></html>"

                        if ACTIVE_NOTIFICATION or webhook_event_enabled("active"):
                            email_attempted, webhook_attempted = send_notification_channels("active", m_subject, m_body, m_body_html, ACTIVE_NOTIFICATION)
                            email_sent = email_sent or email_attempted
                            webhook_sent = webhook_sent or webhook_attempted

                    on_the_list = False
                    if sp_track.upper() in tracks_upper or sp_playlist.upper() in tracks_upper or sp_album.upper() in tracks_upper:
                        print("\n*** Track/playlist/album matched with the list!")
                        on_the_list = True

                    # Check for loop notification first so each channel can suppress its lower-priority song alert
                    if song_on_loop == SONG_ON_LOOP_VALUE and ((SONG_ON_LOOP_NOTIFICATION and not email_sent) or (webhook_event_enabled("loop") and not webhook_sent)):
                        music_urls_text = format_music_urls_email_text(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                        music_urls_html = format_music_urls_email_html(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, sp_artist, sp_track)
                        lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                        lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, sp_artist, sp_track)
                        if music_urls_text:
                            music_section_text = f"\n\n{music_urls_text}"
                            music_section_html = f"<br><br>{music_urls_html}"
                            lyrics_section_text = f"\n{lyrics_urls_text}\n\n" if lyrics_urls_text else "\n\n"
                            lyrics_section_html = f"<br>{lyrics_urls_html}<br><br>" if lyrics_urls_html else "<br><br>"
                        else:
                            if lyrics_urls_text:
                                music_section_text = "\n\n"
                                music_section_html = "<br><br>"
                                lyrics_section_text = f"{lyrics_urls_text}\n\n"
                                lyrics_section_html = f"{lyrics_urls_html}<br><br>"
                            else:
                                music_section_text = "\n\n"
                                music_section_html = "<br><br>"
                                lyrics_section_text = ""
                                lyrics_section_html = ""
                        m_subject = f"Spotify user {sp_username} plays song on loop: '{sp_artist} - {sp_track}'"
                        m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{played_for_m_body}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}{music_section_text}{lyrics_section_text}User plays song on LOOP ({song_on_loop} times)\n\nSongs played: {listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})\n\nLast activity: {get_date_from_ts(sp_ts)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{played_for_m_body_html}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}{music_section_html}{lyrics_section_html}User plays song on LOOP (<b>{song_on_loop}</b> times)<br><br>Songs played: {listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})<br><br>Last activity: {get_date_from_ts(sp_ts)}{get_cur_ts('<br>Timestamp: ')}</body></html>"
                        email_attempted, webhook_attempted = send_notification_channels("loop", m_subject, m_body, m_body_html, SONG_ON_LOOP_NOTIFICATION and not email_sent, webhook_event_enabled("loop") and not webhook_sent)
                        email_sent = email_sent or email_attempted
                        webhook_sent = webhook_sent or webhook_attempted

                    email_song_enabled = ((TRACK_NOTIFICATION and on_the_list) or SONG_NOTIFICATION) and not email_sent
                    webhook_song_enabled = ((webhook_event_enabled("track") and on_the_list) or webhook_event_enabled("song")) and not webhook_sent
                    if email_song_enabled or webhook_song_enabled:
                        music_urls_text = format_music_urls_email_text(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                        music_urls_html = format_music_urls_email_html(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, sp_artist, sp_track)
                        lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                        lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, sp_artist, sp_track)
                        if music_urls_text:
                            music_section_text = f"\n\n{music_urls_text}"
                            music_section_html = f"<br><br>{music_urls_html}"
                            lyrics_section_text = f"\n{lyrics_urls_text}\n\n" if lyrics_urls_text else "\n\n"
                            lyrics_section_html = f"<br>{lyrics_urls_html}<br><br>" if lyrics_urls_html else "<br><br>"
                        else:
                            if lyrics_urls_text:
                                music_section_text = "\n\n"
                                music_section_html = "<br><br>"
                                lyrics_section_text = f"{lyrics_urls_text}\n\n"
                                lyrics_section_html = f"{lyrics_urls_html}<br><br>"
                            else:
                                music_section_text = "\n\n"
                                music_section_html = "<br><br>"
                                lyrics_section_text = ""
                                lyrics_section_html = ""
                        m_subject = f"Spotify user {sp_username}: '{sp_artist} - {sp_track}'"
                        m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{played_for_m_body}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}{music_section_text}{lyrics_section_text}Songs played: {listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})\n\nLast activity: {get_date_from_ts(sp_ts)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{played_for_m_body_html}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}{music_section_html}{lyrics_section_html}Songs played: {listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})<br><br>Last activity: {get_date_from_ts(sp_ts)}{get_cur_ts('<br>Timestamp: ')}</body></html>"
                        notification_type = "track" if on_the_list and ((TRACK_NOTIFICATION and email_song_enabled) or webhook_event_enabled("track")) else "song"
                        email_attempted, webhook_attempted = send_notification_channels(notification_type, m_subject, m_body, m_body_html, email_song_enabled, webhook_song_enabled)
                        email_sent = email_sent or email_attempted
                        webhook_sent = webhook_sent or webhook_attempted

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(cur_ts)), sp_artist, sp_track, sp_playlist, sp_album, datetime.fromtimestamp(int(sp_ts)))
                    except Exception as e:
                        print_recovery_error(e, "file_write", detail=f"CSV destination '{csv_file_name}' could not be written: {e}")

                    if listened_songs:
                        print(f"\nSongs played:\t\t\t{listened_songs} ({calculate_timespan(int(sp_ts), int(sp_active_ts_start))})")

                    print_cur_ts("\nTimestamp:\t\t\t")
                    sp_ts_old = sp_ts
                # Track has not changed
                else:
                    alive_counter += 1
                    # Friend got inactive
                    if (cur_ts - sp_ts) > SPOTIFY_INACTIVITY_CHECK and sp_active_ts_start > 0:
                        sp_active_ts_stop = sp_ts
                        print(f"*** Friend got INACTIVE after listening to music for {calculate_timespan(int(sp_active_ts_stop), int(sp_active_ts_start))}")
                        print(f"*** Friend played music from {get_range_of_dates_from_tss(sp_active_ts_start, sp_active_ts_stop, short=True, between_sep=' to ')}")

                        if FLAG_FILE:
                            flag_file_delete()

                        listened_songs_text = f"*** User played {listened_songs} songs"
                        listened_songs_mbody = f"\n\nUser played {listened_songs} songs"
                        listened_songs_mbody_html = f"<br><br>User played <b>{listened_songs}</b> songs"

                        if skipped_songs > 0:
                            skipped_songs_text = f", skipped {skipped_songs} songs ({int((skipped_songs / listened_songs) * 100)}%)"
                            listened_songs_text += skipped_songs_text
                            listened_songs_mbody += skipped_songs_text
                            listened_songs_mbody_html += f", skipped <b>{skipped_songs}</b> songs <b>({int((skipped_songs / listened_songs) * 100)}%)</b>"

                        if looped_songs > 0:
                            looped_songs_text = f"\n*** User played {looped_songs} songs on loop"
                            looped_songs_mbody = f"\nUser played {looped_songs} songs on loop"
                            looped_songs_mbody_html = f"<br>User played <b>{looped_songs}</b> songs on loop"
                            listened_songs_text += looped_songs_text
                            listened_songs_mbody += looped_songs_mbody
                            listened_songs_mbody_html += looped_songs_mbody_html

                        if is_playlist:
                            playlist_suffix = SPOTIFY_SUFFIX if sp_playlist_owner == "Spotify" else ""

                        print(listened_songs_text)

                        print(f"*** Last activity:\t\t{get_date_from_ts(sp_active_ts_stop)} (inactive timer: {display_time(SPOTIFY_INACTIVITY_CHECK)})")
                        # If tracking functionality is enabled then either pause the current song via Spotify client or play the indicated SP_USER_GOT_OFFLINE_TRACK_ID "finishing" song
                        if TRACK_SONGS:
                            if SP_USER_GOT_OFFLINE_TRACK_ID:
                                if platform.system() == 'Darwin':       # macOS
                                    spotify_macos_play_song(SP_USER_GOT_OFFLINE_TRACK_ID)
                                    if SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE > 0:
                                        time.sleep(SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE)
                                        spotify_macos_play_pause("pause")
                                elif platform.system() == 'Windows':    # Windows
                                    pass
                                else:                                   # Linux variants
                                    spotify_linux_play_song(SP_USER_GOT_OFFLINE_TRACK_ID)
                                    if SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE > 0:
                                        time.sleep(SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE)
                                        spotify_linux_play_pause("pause")
                            else:
                                if platform.system() == 'Darwin':       # macOS
                                    spotify_macos_play_pause("pause")
                                elif platform.system() == 'Windows':    # Windows
                                    pass
                                else:                                   # Linux variants
                                    spotify_linux_play_pause("pause")
                        if INACTIVE_NOTIFICATION or webhook_event_enabled("inactive"):
                            # Format recently listened songs list for email (skip if only 1 song)
                            recent_songs_mbody = ""
                            recent_songs_mbody_html = ""
                            if listened_songs > 1 and len(recent_songs_session) > 0 and INACTIVE_EMAIL_RECENT_SONGS_COUNT > 0:
                                # Get last up to INACTIVE_EMAIL_RECENT_SONGS_COUNT songs
                                songs_to_show = recent_songs_session[-min(INACTIVE_EMAIL_RECENT_SONGS_COUNT, len(recent_songs_session)):]
                                recent_songs_list = []
                                recent_songs_list_html = []
                                for song in songs_to_show:
                                    song_date = get_date_from_ts(song['timestamp'])
                                    skipped_text = ", SKIPPED" if song.get('skipped', False) else ""
                                    recent_songs_list.append(f"{song['artist']} - {song['track']} ({song_date}{skipped_text})")
                                    skipped_html = ", <b>SKIPPED</b>" if song.get('skipped', False) else ""
                                    recent_songs_list_html.append(f"<b>{escape(song['artist'])} - {escape(song['track'])}</b> ({song_date}{skipped_html})")
                                if recent_songs_list:
                                    recent_songs_mbody = f"\n\nRecently listened songs in this session:\n" + "\n".join(recent_songs_list)
                                    recent_songs_mbody_html = f"<br><br>Recently listened songs in this session:<br>" + "<br>".join(recent_songs_list_html)

                            # Get URLs for the last played track
                            apple_search_url, genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url = get_apple_genius_search_urls(str(sp_artist), str(sp_track))
                            music_urls_text = format_music_urls_email_text(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url)
                            music_urls_html = format_music_urls_email_html(apple_search_url, youtube_music_search_url, amazon_music_search_url, deezer_search_url, tidal_search_url, sp_artist, sp_track)
                            lyrics_urls_text = format_lyrics_urls_email_text(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url)
                            lyrics_urls_html = format_lyrics_urls_email_html(genius_search_url, azlyrics_search_url, tekstowo_search_url, musixmatch_search_url, lyrics_com_search_url, sp_artist, sp_track)
                            if music_urls_text:
                                music_section_text = f"\n\n{music_urls_text}"
                                music_section_html = f"<br><br>{music_urls_html}"
                                lyrics_section_text = f"\n{lyrics_urls_text}\n\n" if lyrics_urls_text else "\n\n"
                                lyrics_section_html = f"<br>{lyrics_urls_html}<br><br>" if lyrics_urls_html else "<br><br>"
                            else:
                                if lyrics_urls_text:
                                    music_section_text = "\n\n"
                                    music_section_html = "<br><br>"
                                    lyrics_section_text = f"{lyrics_urls_text}\n\n"
                                    lyrics_section_html = f"{lyrics_urls_html}<br><br>"
                                else:
                                    music_section_text = "\n\n"
                                    music_section_html = "<br><br>"
                                    lyrics_section_text = ""
                                    lyrics_section_html = ""
                            m_subject = f"Spotify user {sp_username} is inactive: '{sp_artist} - {sp_track}' (after {calculate_timespan(int(sp_active_ts_stop), int(sp_active_ts_start), show_seconds=False)}: {get_range_of_dates_from_tss(sp_active_ts_start, sp_active_ts_stop, short=True)})"
                            m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{played_for_m_body}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}{music_section_text}{lyrics_section_text}Friend got inactive after listening to music for {calculate_timespan(int(sp_active_ts_stop), int(sp_active_ts_start))}\nFriend played music from {get_range_of_dates_from_tss(sp_active_ts_start, sp_active_ts_stop, short=True, between_sep=' to ')}{listened_songs_mbody}{recent_songs_mbody}\n\nLast activity: {get_date_from_ts(sp_active_ts_stop)}\nInactivity timer: {display_time(SPOTIFY_INACTIVITY_CHECK)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                            m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{played_for_m_body_html}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}{music_section_html}{lyrics_section_html}Friend got inactive after listening to music for <b>{calculate_timespan(int(sp_active_ts_stop), int(sp_active_ts_start))}</b><br>Friend played music from <b>{get_range_of_dates_from_tss(sp_active_ts_start, sp_active_ts_stop, short=True, between_sep='</b> to <b>')}</b>{listened_songs_mbody_html}{recent_songs_mbody_html}<br><br>Last activity: <b>{get_date_from_ts(sp_active_ts_stop)}</b><br>Inactivity timer: {display_time(SPOTIFY_INACTIVITY_CHECK)}{get_cur_ts('<br>Timestamp: ')}</body></html>"
                            email_attempted, webhook_attempted = send_notification_channels("inactive", m_subject, m_body, m_body_html, INACTIVE_NOTIFICATION)
                            email_sent = email_sent or email_attempted
                            webhook_sent = webhook_sent or webhook_attempted
                        sp_active_ts_start_old = sp_active_ts_start
                        sp_active_ts_start = 0
                        listened_songs_old = listened_songs
                        skipped_songs_old = skipped_songs
                        looped_songs_old = looped_songs
                        listened_songs = 0
                        looped_songs = 0
                        skipped_songs = 0
                        song_on_loop = 0
                        recent_songs_session = []
                        print_cur_ts("\nTimestamp:\t\t\t")

                    if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER:
                        verbose_print(f"Monitoring healthy for {user_uri_id}. Target remains visible with no activity change")
                        print_cur_ts("Liveness check, timestamp:\t")
                        alive_counter = 0

                debug_monitor_check_timing(check_count, user_uri_id, check_started_at, SPOTIFY_CHECK_INTERVAL)
                time.sleep(SPOTIFY_CHECK_INTERVAL)

                ERROR_500_ZERO_TIME_LIMIT = ERROR_500_TIME_LIMIT + SPOTIFY_CHECK_INTERVAL
                if SPOTIFY_CHECK_INTERVAL * ERROR_500_NUMBER_LIMIT > ERROR_500_ZERO_TIME_LIMIT:
                    ERROR_500_ZERO_TIME_LIMIT = SPOTIFY_CHECK_INTERVAL * (ERROR_500_NUMBER_LIMIT + 1)

                if error_500_start_ts and ((int(time.time()) - error_500_start_ts) >= ERROR_500_ZERO_TIME_LIMIT):
                    error_500_start_ts = 0
                    error_500_counter = 0

                ERROR_NETWORK_ZERO_TIME_LIMIT = ERROR_NETWORK_ISSUES_TIME_LIMIT + SPOTIFY_CHECK_INTERVAL
                if SPOTIFY_CHECK_INTERVAL * ERROR_NETWORK_ISSUES_NUMBER_LIMIT > ERROR_NETWORK_ZERO_TIME_LIMIT:
                    ERROR_NETWORK_ZERO_TIME_LIMIT = SPOTIFY_CHECK_INTERVAL * (ERROR_NETWORK_ISSUES_NUMBER_LIMIT + 1)

                if error_network_issue_start_ts and ((int(time.time()) - error_network_issue_start_ts) >= ERROR_NETWORK_ZERO_TIME_LIMIT):
                    error_network_issue_start_ts = 0
                    error_network_issue_counter = 0

        # User is not found in the Spotify's friend list just after starting the tool
        else:
            if user_not_found is False:
                if is_user_removed(sp_accessToken, user_uri_id):
                    print(f"User '{user_uri_id}' does not exist! Retrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals")
                    not_found_advice = make_recovery_advice("target.not_found", "The Spotify target profile returned HTTP 404", "Check the target ID, URI or profile URL then retry", False)
                    if recovery_hint_tracker.should_render(not_found_advice):
                        print(f"  To fix: {not_found_advice.fix}")
                else:
                    print(f"User '{user_uri_id}' not found - make sure your friend is followed and has activity sharing enabled. Retrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals")
                    not_visible_advice = classify_recovery_error(context="target_not_visible")
                    if recovery_hint_tracker.should_render(not_visible_advice):
                        print(f"  To fix: {not_visible_advice.fix}")
                print_cur_ts("Timestamp:\t\t\t")
                user_not_found = True
            debug_monitor_wait_timing(user_uri_id, SPOTIFY_DISAPPEARED_CHECK_INTERVAL)
            time.sleep(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)
            continue


def main():
    global CLI_CONFIG_PATH, DOTENV_FILE, LIVENESS_CHECK_COUNTER, LOGIN_REQUEST_BODY_FILE, CLIENTTOKEN_REQUEST_BODY_FILE, REFRESH_TOKEN, LOGIN_URL, USER_AGENT, DEVICE_ID, SYSTEM_ID, USER_URI_ID, SP_DC_COOKIE, CSV_FILE, MONITOR_LIST_FILE, FILE_SUFFIX, DISABLE_LOGGING, DEBUG_MODE, VERBOSE_MODE, SP_LOGFILE, ACTIVE_NOTIFICATION, INACTIVE_NOTIFICATION, TRACK_NOTIFICATION, SONG_NOTIFICATION, SONG_ON_LOOP_NOTIFICATION, ERROR_NOTIFICATION, WEBHOOK_ENABLED, WEBHOOK_URL, WEBHOOK_ACTIVE_NOTIFICATION, WEBHOOK_INACTIVE_NOTIFICATION, WEBHOOK_TRACK_NOTIFICATION, WEBHOOK_SONG_NOTIFICATION, WEBHOOK_SONG_ON_LOOP_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION, SPOTIFY_CHECK_INTERVAL, SPOTIFY_INACTIVITY_CHECK, SPOTIFY_ERROR_INTERVAL, SPOTIFY_DISAPPEARED_CHECK_INTERVAL, TRACK_SONGS, SMTP_PASSWORD, stdout_bck, APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL, TOKEN_SOURCE, ALARM_TIMEOUT, pyotp, USER_AGENT, FLAG_FILE, TRUNCATE_CHARS, SP_APP_TOKENS_FILE, SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET

    if "--generate-config" in sys.argv and "--setup" not in sys.argv and "--set-sp-dc" not in sys.argv and "--set-webhook-url" not in sys.argv:
        config_content = generate_config_with_current_values()
        # Check if a filename was provided after --generate-config
        try:
            idx = sys.argv.index("--generate-config")
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
                # Write directly to file (bypasses PowerShell UTF-16 encoding issue on Windows)
                output_file = sys.argv[idx + 1]
                try:
                    write_status = write_config_file(output_file, config_content)
                except Exception as exc:
                    print(f"* Error: Could not write config file '{output_file}': {type(exc).__name__}: {exc}")
                    sys.exit(1)
                print(f"Config written to: {write_status['path']}")
                if write_status["backup_path"]:
                    print(f"Backup written to: {write_status['backup_path']}")
                sys.exit(0)
        except (ValueError, IndexError):
            pass
        # No filename provided - write to stdout using buffer to ensure UTF-8
        sys.stdout.buffer.write(config_content.encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(0)

    if "--version" in sys.argv and "--setup" not in sys.argv and "--set-sp-dc" not in sys.argv and "--set-webhook-url" not in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    clear_screen(CLEAR_SCREEN and sys.stdout.isatty())

    print_startup_banner()

    parser = argparse.ArgumentParser(
        prog="spotify_monitor",
        description=("Monitor a Spotify friend's activity and send customizable email or webhook alerts [ https://github.com/misiektoja/spotify_monitor/ ]"), formatter_class=argparse.RawTextHelpFormatter,
        epilog=_build_help_epilog()
    )

    # Positional
    parser.add_argument(
        "user_id",
        nargs="?",
        metavar="SPOTIFY_USER_URI_ID",
        help="Spotify user ID, spotify:user URI or open.spotify.com profile URL",
        type=str
    )

    # Version, just to list in help, it is handled earlier
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the Spotify Monitor version and exit"
    )

    # Configuration & dotenv files
    conf = parser.add_argument_group("Configuration & dotenv files")
    conf.add_argument(
        "--setup",
        action="store_true",
        help="Run the interactive first-run setup wizard",
    )
    conf.add_argument(
        "--set-sp-dc",
        dest="set_sp_dc",
        action="store_true",
        help="Privately validate and save SP_DC_COOKIE through a hidden prompt",
    )
    conf.add_argument(
        "--set-webhook-url",
        dest="set_webhook_url",
        action="store_true",
        help="Privately validate and save WEBHOOK_URL through a hidden prompt",
    )
    conf.add_argument(
        "--config-file",
        dest="config_file",
        metavar="PATH",
        help="Location of the optional config file",
    )
    conf.add_argument(
        "--generate-config",
        dest="generate_config",
        nargs="?",
        const=True,
        metavar="FILENAME",
        help="Print default config template and exit (on Windows PowerShell, specify a filename to avoid redirect encoding issues)",
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
    )
    conf.add_argument(
        "--doctor",
        dest="doctor",
        action="store_true",
        help="Run read-only preflight checks then exit",
    )

    # Token source
    parser.add_argument(
        "--token-source",
        dest="token_source",
        choices=["cookie", "client"],
        help="Method to obtain Spotify access token: 'cookie' (via sp_dc cookie) or 'client' (via desktop client login protobuf)"
    )

    # Auth details used when token source is set to cookie
    cookie_auth = parser.add_argument_group("Auth details for 'cookie' token source")
    cookie_auth.add_argument(
        "-u", "--spotify-dc-cookie",
        dest="spotify_dc_cookie",
        metavar="SP_DC_COOKIE",
        type=str,
        help="Spotify sp_dc cookie"
    )

    # Browser cookie import
    browser_import = parser.add_argument_group("Browser sp_dc import")
    browser_import.add_argument(
        "--import-browser-cookie",
        action="store_true",
        help="Import, validate and save Spotify sp_dc from a supported browser"
    )
    browser_import.add_argument(
        "--browser",
        choices=list(IMPORT_BROWSERS),
        default=None,
        help="Browser source: firefox (default), chrome, brave or chromium"
    )
    browser_import.add_argument(
        "--browser-profile",
        metavar="PROFILE",
        help="Firefox friendly profile name or Chromium profile directory"
    )
    browser_import.add_argument(
        "--cookie-file",
        metavar="PATH",
        help="Advanced explicit browser cookie database override"
    )
    browser_import.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing SP_DC_COOKIE without a prompt"
    )

    # Auth details used when token source is set to client
    client_auth = parser.add_argument_group("Auth details for 'client' token source")
    client_auth.add_argument(
        "-w", "--login-request-body-file",
        dest="login_request_body_file",
        metavar="PROTOBUF_FILENAME",
        help="Read device_id, system_id, user_uri_id and refresh_token from binary Protobuf login file"
    )

    client_auth.add_argument(
        "-z", "--clienttoken-request-body-file",
        dest="clienttoken_request_body_file",
        metavar="PROTOBUF_FILENAME",
        # help="Read app_version, cpu_arch, os_build, platform, os_major, os_minor and client_model from binary Protobuf client token file"
        help=argparse.SUPPRESS
    )

    # Optional OAuth app credentials preserve the legacy Web API metadata path when it remains available
    oauth_app_auth = parser.add_argument_group("Optional OAuth app credentials for legacy metadata calls")
    oauth_app_auth.add_argument(
        "-r", "--oauth-app-creds",
        dest="oauth_app_creds",
        metavar='SPOTIFY_APP_CLIENT_ID:SPOTIFY_APP_CLIENT_SECRET',
        help="Optional Spotify OAuth app credentials for legacy metadata calls - specify both values as SPOTIFY_APP_CLIENT_ID:SPOTIFY_APP_CLIENT_SECRET"
    )

    # Notifications
    notify = parser.add_argument_group("Notifications")
    notify.add_argument(
        "-a", "--notify-active",
        dest="notify_active",
        action="store_true",
        default=None,
        help="Email when user becomes active"
    )
    notify.add_argument(
        "-i", "--notify-inactive",
        dest="notify_inactive",
        action="store_true",
        default=None,
        help="Email when user goes inactive"
    )
    notify.add_argument(
        "-t", "--notify-track",
        dest="notify_track",
        action="store_true",
        default=None,
        help="Email when a monitored track/playlist/album plays"
    )
    notify.add_argument(
        "-j", "--notify-song-changes",
        dest="notify_song_changes",
        action="store_true",
        default=None,
        help="Email on every song change"
    )
    notify.add_argument(
        "-x", "--notify-loop",
        dest="notify_loop",
        action="store_true",
        default=None,
        help="Email when user plays a song on loop"
    )
    notify.add_argument(
        "-e", "--no-error-notify",
        dest="notify_errors",
        action="store_false",
        default=None,
        help="Disable emails on errors"
    )
    notify.add_argument(
        "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email to verify SMTP settings"
    )

    webhook_notify = parser.add_argument_group("Discord-compatible webhooks")
    webhook_toggle = webhook_notify.add_mutually_exclusive_group()
    webhook_toggle.add_argument(
        "--webhook",
        dest="webhook_enabled",
        action="store_true",
        default=None,
        help="Enable configured webhook notifications"
    )
    webhook_toggle.add_argument(
        "--no-webhook",
        dest="webhook_enabled",
        action="store_false",
        default=None,
        help="Disable configured webhook notifications"
    )
    webhook_notify.add_argument(
        "--webhook-active",
        dest="webhook_active",
        action="store_true",
        default=None,
        help="Send a webhook when the user becomes active"
    )
    webhook_notify.add_argument(
        "--webhook-inactive",
        dest="webhook_inactive",
        action="store_true",
        default=None,
        help="Send a webhook when the user goes inactive"
    )
    webhook_notify.add_argument(
        "--webhook-track",
        dest="webhook_track",
        action="store_true",
        default=None,
        help="Send a webhook when a monitored track, playlist or album plays"
    )
    webhook_notify.add_argument(
        "--webhook-song-changes",
        dest="webhook_song_changes",
        action="store_true",
        default=None,
        help="Send a webhook on every song change"
    )
    webhook_notify.add_argument(
        "--webhook-loop",
        dest="webhook_loop",
        action="store_true",
        default=None,
        help="Send a webhook when the user plays a song on loop"
    )
    webhook_notify.add_argument(
        "--no-webhook-error-notify",
        dest="webhook_errors",
        action="store_false",
        default=None,
        help="Disable webhook notifications on errors"
    )
    webhook_notify.add_argument(
        "--send-test-webhook",
        dest="send_test_webhook",
        action="store_true",
        help="Send one test webhook without starting monitoring"
    )

    # Intervals & timers
    times = parser.add_argument_group("Intervals & timers")
    times.add_argument(
        "-c", "--check-interval",
        dest="check_interval",
        metavar="SECONDS",
        type=int,
        help="Time between monitoring checks, in seconds"
    )
    times.add_argument(
        "-o", "--offline-timer",
        dest="offline_timer",
        metavar="SECONDS",
        type=int,
        help="Time required to mark inactive user as offline, in seconds"
    )
    times.add_argument(
        "-m", "--disappeared-timer",
        dest="disappeared_timer",
        metavar="SECONDS",
        type=int,
        help="Wait time between checks once the user disappears from friends list, in seconds"
    )

    # Listing
    listing = parser.add_argument_group("Listing")
    listing.add_argument(
        "-l", "--list-friends",
        dest="list_friends",
        action="store_true",
        help="List Spotify friends with their last listened track"
    )

    # Features & output
    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "-g", "--track-in-spotify",
        dest="track_in_spotify",
        action="store_true",
        default=None,
        help="Auto-play each listened song in your Spotify client"
    )
    opts.add_argument(
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILE",
        type=str,
        help="Write every listened track to CSV file"
    )
    opts.add_argument(
        "-s", "--monitor-list",
        dest="monitor_list",
        metavar="TRACKS_FILE",
        type=str,
        help="Filename with Spotify tracks/playlists/albums to alert on"
    )
    opts.add_argument(
        "--flag-file",
        dest="flag_file",
        metavar="PATH",
        help="Path to flag file that is created when the user is active and deleted when inactive",
    )
    opts.add_argument(
        "--user-agent",
        dest="user_agent",
        metavar="USER_AGENT",
        type=str,
        help="Specify a custom user agent for Spotify API requests; leave empty to auto-generate it"
    )
    opts.add_argument(
        "-y", "--file-suffix",
        dest="file_suffix",
        metavar="SUFFIX",
        type=str,
        help="File suffix to append to output filenames instead of Spotify user URI ID"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to spotify_monitor_<user_uri_id/file_suffix>.log"
    )
    opts.add_argument(
        "--debug",
        dest="debug_mode",
        action="store_true",
        default=None,
        help="Enable debug mode for technical logging"
    )
    opts.add_argument(
        "--verbose",
        dest="verbose_mode",
        action="store_true",
        default=None,
        help="Show rare operational events plus the complete startup summary"
    )
    opts.add_argument(
        "--truncate",
        dest="truncate",
        metavar="N",
        type=int,
        help="Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        _wizard_welcome()
        sys.exit(0 if sys.stdin.isatty() else 1)

    if args.set_sp_dc:
        set_sp_dc_conflicts = []
        conflict_values = (
            (args.user_id, "SPOTIFY_USER_URI_ID"),
            (args.setup, "--setup"),
            (args.set_webhook_url, "--set-webhook-url"),
            (args.doctor, "--doctor"),
            (args.version, "--version"),
            (args.generate_config, "--generate-config"),
            (args.config_file, "--config-file"),
            (args.import_browser_cookie, "--import-browser-cookie"),
            (args.send_test_email, "--send-test-email"),
            (args.send_test_webhook, "--send-test-webhook"),
            (args.list_friends, "--list-friends"),
            (args.token_source, "--token-source"),
            (args.spotify_dc_cookie, "--spotify-dc-cookie"),
            (args.login_request_body_file, "--login-request-body-file"),
            (args.clienttoken_request_body_file, "--clienttoken-request-body-file"),
            (args.oauth_app_creds, "--oauth-app-creds"),
            (args.check_interval, "--check-interval"),
            (args.offline_timer, "--offline-timer"),
            (args.disappeared_timer, "--disappeared-timer"),
            (args.monitor_list, "--monitor-list"),
            (args.csv_file, "--csv-file"),
            (args.flag_file, "--flag-file"),
            (args.user_agent, "--user-agent"),
            (args.file_suffix, "--file-suffix"),
            (args.truncate, "--truncate"),
            (args.browser, "--browser"),
            (args.browser_profile, "--browser-profile"),
            (args.cookie_file, "--cookie-file"),
            (args.force, "--force"),
        )
        set_sp_dc_conflicts.extend(flag for value, flag in conflict_values if value is not None and value is not False)
        boolean_conflicts = ((args.notify_active, "--notify-active"), (args.notify_inactive, "--notify-inactive"), (args.notify_track, "--notify-track"), (args.notify_song_changes, "--notify-song-changes"), (args.notify_loop, "--notify-loop"), (args.notify_errors, "--no-error-notify"), (args.webhook_enabled, "--webhook/--no-webhook"), (args.webhook_active, "--webhook-active"), (args.webhook_inactive, "--webhook-inactive"), (args.webhook_track, "--webhook-track"), (args.webhook_song_changes, "--webhook-song-changes"), (args.webhook_loop, "--webhook-loop"), (args.webhook_errors, "--no-webhook-error-notify"), (args.track_in_spotify, "--track-in-spotify"), (args.disable_logging, "--disable-logging"), (args.debug_mode, "--debug"), (args.verbose_mode, "--verbose"))
        set_sp_dc_conflicts.extend(flag for value, flag in boolean_conflicts if value is not None)
        if set_sp_dc_conflicts:
            parser.error("--set-sp-dc cannot be combined with " + ", ".join(set_sp_dc_conflicts))
        if args.env_file is not None and args.env_file.casefold() == "none":
            parser.error("--set-sp-dc requires a writable dotenv destination and cannot use --env-file none")
        try:
            run_set_sp_dc(env_file=args.env_file)
        except BrowserCookieImportError as exc:
            print_recovery_error(exc, "set_sp_dc")
            sys.exit(1)
        sys.exit(0)

    if args.set_webhook_url:
        set_webhook_conflicts = []
        conflict_values = (
            (args.user_id, "SPOTIFY_USER_URI_ID"),
            (args.setup, "--setup"),
            (args.set_sp_dc, "--set-sp-dc"),
            (args.doctor, "--doctor"),
            (args.version, "--version"),
            (args.generate_config, "--generate-config"),
            (args.config_file, "--config-file"),
            (args.import_browser_cookie, "--import-browser-cookie"),
            (args.send_test_email, "--send-test-email"),
            (args.send_test_webhook, "--send-test-webhook"),
            (args.list_friends, "--list-friends"),
            (args.token_source, "--token-source"),
            (args.spotify_dc_cookie, "--spotify-dc-cookie"),
            (args.login_request_body_file, "--login-request-body-file"),
            (args.clienttoken_request_body_file, "--clienttoken-request-body-file"),
            (args.oauth_app_creds, "--oauth-app-creds"),
            (args.check_interval, "--check-interval"),
            (args.offline_timer, "--offline-timer"),
            (args.disappeared_timer, "--disappeared-timer"),
            (args.monitor_list, "--monitor-list"),
            (args.csv_file, "--csv-file"),
            (args.flag_file, "--flag-file"),
            (args.user_agent, "--user-agent"),
            (args.file_suffix, "--file-suffix"),
            (args.truncate, "--truncate"),
            (args.browser, "--browser"),
            (args.browser_profile, "--browser-profile"),
            (args.cookie_file, "--cookie-file"),
            (args.force, "--force"),
        )
        set_webhook_conflicts.extend(flag for value, flag in conflict_values if value is not None and value is not False)
        boolean_conflicts = ((args.notify_active, "--notify-active"), (args.notify_inactive, "--notify-inactive"), (args.notify_track, "--notify-track"), (args.notify_song_changes, "--notify-song-changes"), (args.notify_loop, "--notify-loop"), (args.notify_errors, "--no-error-notify"), (args.webhook_enabled, "--webhook/--no-webhook"), (args.webhook_active, "--webhook-active"), (args.webhook_inactive, "--webhook-inactive"), (args.webhook_track, "--webhook-track"), (args.webhook_song_changes, "--webhook-song-changes"), (args.webhook_loop, "--webhook-loop"), (args.webhook_errors, "--no-webhook-error-notify"), (args.track_in_spotify, "--track-in-spotify"), (args.disable_logging, "--disable-logging"), (args.debug_mode, "--debug"), (args.verbose_mode, "--verbose"))
        set_webhook_conflicts.extend(flag for value, flag in boolean_conflicts if value is not None)
        if set_webhook_conflicts:
            parser.error("--set-webhook-url cannot be combined with " + ", ".join(set_webhook_conflicts))
        if args.env_file is not None and args.env_file.casefold() == "none":
            parser.error("--set-webhook-url requires a writable dotenv destination and cannot use --env-file none")
        try:
            run_set_webhook_url(env_file=args.env_file)
        except WebhookConfigurationError as exc:
            print_recovery_error(exc, "set_webhook_url")
            sys.exit(1)
        sys.exit(0)

    if args.setup:
        setup_conflicts = []
        conflict_values = (
            (args.doctor, "--doctor"),
            (args.version, "--version"),
            (args.generate_config, "--generate-config"),
            (args.import_browser_cookie, "--import-browser-cookie"),
            (args.set_sp_dc, "--set-sp-dc"),
            (args.set_webhook_url, "--set-webhook-url"),
            (args.send_test_email, "--send-test-email"),
            (args.send_test_webhook, "--send-test-webhook"),
            (args.list_friends, "--list-friends"),
            (args.token_source, "--token-source"),
            (args.spotify_dc_cookie, "--spotify-dc-cookie"),
            (args.login_request_body_file, "--login-request-body-file"),
            (args.clienttoken_request_body_file, "--clienttoken-request-body-file"),
            (args.oauth_app_creds, "--oauth-app-creds"),
            (args.check_interval, "--check-interval"),
            (args.offline_timer, "--offline-timer"),
            (args.disappeared_timer, "--disappeared-timer"),
            (args.monitor_list, "--monitor-list"),
            (args.csv_file, "--csv-file"),
            (args.flag_file, "--flag-file"),
            (args.user_agent, "--user-agent"),
            (args.file_suffix, "--file-suffix"),
            (args.truncate, "--truncate"),
        )
        setup_conflicts.extend(flag for value, flag in conflict_values if value is not None and value is not False)
        boolean_conflicts = ((args.notify_active, "--notify-active"), (args.notify_inactive, "--notify-inactive"), (args.notify_track, "--notify-track"), (args.notify_song_changes, "--notify-song-changes"), (args.notify_loop, "--notify-loop"), (args.notify_errors, "--no-error-notify"), (args.webhook_enabled, "--webhook/--no-webhook"), (args.webhook_active, "--webhook-active"), (args.webhook_inactive, "--webhook-inactive"), (args.webhook_track, "--webhook-track"), (args.webhook_song_changes, "--webhook-song-changes"), (args.webhook_loop, "--webhook-loop"), (args.webhook_errors, "--no-webhook-error-notify"), (args.track_in_spotify, "--track-in-spotify"), (args.disable_logging, "--disable-logging"), (args.debug_mode, "--debug"), (args.verbose_mode, "--verbose"))
        setup_conflicts.extend(flag for value, flag in boolean_conflicts if value is not None)
        import_conflicts = ((args.browser, "--browser"), (args.browser_profile, "--browser-profile"), (args.cookie_file, "--cookie-file"), (args.force, "--force"))
        setup_conflicts.extend(flag for value, flag in import_conflicts if value is not None and value is not False)
        if setup_conflicts:
            parser.error("--setup cannot be combined with " + ", ".join(setup_conflicts))
        if args.env_file is not None and args.env_file.casefold() == "none":
            parser.error("--setup requires a dotenv destination and cannot use --env-file none")
        run_setup_wizard(args.user_id, args.config_file, args.env_file)
        sys.exit(0)

    if args.doctor:
        conflicting_actions = []
        if args.import_browser_cookie:
            conflicting_actions.append("--import-browser-cookie")
        if args.send_test_email:
            conflicting_actions.append("--send-test-email")
        if args.send_test_webhook:
            conflicting_actions.append("--send-test-webhook")
        if args.list_friends:
            conflicting_actions.append("--list-friends")
        if conflicting_actions:
            parser.error("--doctor cannot be combined with " + ", ".join(conflicting_actions))

    if not args.import_browser_cookie:
        import_only_flags = []
        if args.browser is not None:
            import_only_flags.append("--browser")
        if args.browser_profile is not None:
            import_only_flags.append("--browser-profile")
        if args.cookie_file is not None:
            import_only_flags.append("--cookie-file")
        if args.force:
            import_only_flags.append("--force")
        if import_only_flags:
            parser.error(f"{', '.join(import_only_flags)} require --import-browser-cookie")

    doctor_startup_checks = []

    if args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = find_config_file(CLI_CONFIG_PATH)

    if not cfg_path and CLI_CONFIG_PATH:
        advice = classify_recovery_error(context="config_missing", detail=f"Configuration file not found: {CLI_CONFIG_PATH}")
        if args.doctor:
            doctor_startup_checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice))
        else:
            print(render_recovery_error(RecoveryError(advice)))
            sys.exit(1)

    if cfg_path:
        config_errors = []
        if not load_config_file(cfg_path, error_out=config_errors, report_errors=not args.doctor):
            if args.doctor:
                for advice in config_errors:
                    doctor_startup_checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice))
            else:
                sys.exit(1)

    if args.import_browser_cookie:
        if args.token_source:
            TOKEN_SOURCE = args.token_source
        if not TOKEN_SOURCE:
            TOKEN_SOURCE = "cookie"
        if args.debug_mode is not None:
            DEBUG_MODE = args.debug_mode
        if args.user_agent:
            USER_AGENT = args.user_agent
        try:
            run_browser_cookie_import(browser=args.browser or "firefox", browser_profile=args.browser_profile, cookie_file=args.cookie_file, env_file=args.env_file, force=args.force)
        except BrowserCookieImportError as exc:
            print_recovery_error(exc, "browser_import")
            sys.exit(1)
        sys.exit(0)

    target_user_id = None
    if not args.list_friends and not args.send_test_email and not args.send_test_webhook and not args.doctor:
        try:
            target_user_id = resolve_target_user_id(args.user_id, TARGET_USER_URI_ID)
        except ValueError as exc:
            print_recovery_error(exc, "target_invalid")
            sys.exit(1)

    if args.debug_mode is not None:
        DEBUG_MODE = args.debug_mode

    if args.verbose_mode is not None:
        VERBOSE_MODE = args.verbose_mode

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    env_path = None
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import find_dotenv, load_dotenv
            from dotenv.parser import parse_stream

            if DOTENV_FILE:
                env_path = DOTENV_FILE
                if not os.path.isfile(env_path):
                    advice = classify_recovery_error(context="config_missing", detail=f"Dotenv file not found: {env_path}")
                    if args.doctor:
                        doctor_startup_checks.append(make_doctor_check("Configuration", "FAIL", "The requested dotenv file was not found", advice.detail, advice))
                    else:
                        print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                    env_path = None
                else:
                    with open(env_path, "r", encoding="utf-8") as dotenv_file:
                        bindings = list(parse_stream(dotenv_file))
                    malformed = [binding for binding in bindings if binding.error]
                    if malformed:
                        line_number = malformed[0].original.line
                        raise ValueError(f"Dotenv syntax error near line {line_number}")
                    load_dotenv(env_path, override=True, interpolate=False)
            else:
                env_path = find_dotenv() or None
                if env_path:
                    with open(env_path, "r", encoding="utf-8") as dotenv_file:
                        bindings = list(parse_stream(dotenv_file))
                    malformed = [binding for binding in bindings if binding.error]
                    if malformed:
                        line_number = malformed[0].original.line
                        raise ValueError(f"Dotenv syntax error near line {line_number}")
                    load_dotenv(env_path, override=True, interpolate=False)
        except ImportError as exc:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            advice = classify_recovery_error(exc, "dependency", "python-dotenv is required to load dotenv files")
            if args.doctor:
                doctor_startup_checks.append(make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice))
            elif env_path:
                print(render_recovery_error(RecoveryError(advice)))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            advice = classify_recovery_error(exc, "config_invalid", f"Dotenv file '{env_path}' could not be loaded: {exc}")
            if args.doctor:
                doctor_startup_checks.append(make_doctor_check("Configuration", "FAIL", "The dotenv file could not be loaded", advice.detail, advice))
            else:
                print(render_recovery_error(RecoveryError(advice)))
                sys.exit(1)

    if env_path:
        for secret in SECRET_KEYS:
            val = os.getenv(secret)
            if val is not None:
                globals()[secret] = val

    if args.token_source:
        TOKEN_SOURCE = args.token_source

    if not TOKEN_SOURCE:
        TOKEN_SOURCE = "cookie"

    if TOKEN_SOURCE == "cookie":
        ALARM_TIMEOUT = int((TOKEN_MAX_RETRIES * TOKEN_RETRY_TIMEOUT) + 5)

    if args.user_agent:
        USER_AGENT = args.user_agent

    if not USER_AGENT:
        if TOKEN_SOURCE == "client":
            USER_AGENT = get_random_spotify_user_agent()
        else:
            USER_AGENT = get_random_user_agent()

    if args.spotify_dc_cookie:
        SP_DC_COOKIE = args.spotify_dc_cookie

    if args.login_request_body_file:
        LOGIN_REQUEST_BODY_FILE = os.path.expanduser(args.login_request_body_file)
    elif LOGIN_REQUEST_BODY_FILE:
        LOGIN_REQUEST_BODY_FILE = os.path.expanduser(LOGIN_REQUEST_BODY_FILE)

    if args.clienttoken_request_body_file:
        CLIENTTOKEN_REQUEST_BODY_FILE = os.path.expanduser(args.clienttoken_request_body_file)
    elif CLIENTTOKEN_REQUEST_BODY_FILE:
        CLIENTTOKEN_REQUEST_BODY_FILE = os.path.expanduser(CLIENTTOKEN_REQUEST_BODY_FILE)

    if args.oauth_app_creds:
        try:
            SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET = args.oauth_app_creds.split(":", 1)
        except ValueError as exc:
            print_recovery_error(exc, "config_invalid", detail="--oauth-app-creds must use SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET format")
            sys.exit(1)

    if args.check_interval is not None:
        SPOTIFY_CHECK_INTERVAL = args.check_interval
    if args.offline_timer is not None:
        SPOTIFY_INACTIVITY_CHECK = args.offline_timer
    if args.disappeared_timer is not None:
        SPOTIFY_DISAPPEARED_CHECK_INTERVAL = args.disappeared_timer
    if args.monitor_list:
        MONITOR_LIST_FILE = os.path.expanduser(args.monitor_list)
    elif MONITOR_LIST_FILE:
        MONITOR_LIST_FILE = os.path.expanduser(MONITOR_LIST_FILE)
    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    elif CSV_FILE:
        CSV_FILE = os.path.expanduser(CSV_FILE)
    if args.disable_logging is True:
        DISABLE_LOGGING = True
    if args.notify_active is True:
        ACTIVE_NOTIFICATION = True
    if args.notify_inactive is True:
        INACTIVE_NOTIFICATION = True
    if args.notify_track is True:
        TRACK_NOTIFICATION = True
    if args.notify_song_changes is True:
        SONG_NOTIFICATION = True
    if args.notify_loop is True:
        SONG_ON_LOOP_NOTIFICATION = True
    if args.notify_errors is False:
        ERROR_NOTIFICATION = False
    if args.webhook_enabled is not None:
        WEBHOOK_ENABLED = args.webhook_enabled
    if args.webhook_active is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_ACTIVE_NOTIFICATION = True
    if args.webhook_inactive is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_INACTIVE_NOTIFICATION = True
    if args.webhook_track is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_TRACK_NOTIFICATION = True
    if args.webhook_song_changes is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_SONG_NOTIFICATION = True
    if args.webhook_loop is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_SONG_ON_LOOP_NOTIFICATION = True
    if args.webhook_errors is False:
        WEBHOOK_ERROR_NOTIFICATION = False
    if args.track_in_spotify is True:
        TRACK_SONGS = True

    if args.doctor:
        doctor_target = args.user_id if args.user_id is not None else TARGET_USER_URI_ID
        sys.exit(run_doctor(doctor_target, cfg_path or CLI_CONFIG_PATH, env_path, doctor_startup_checks))

    if args.send_test_webhook:
        print("* Sending test webhook notification ...\n")
        if send_webhook("spotify_monitor: test webhook", "This is a test webhook. Your Discord-compatible webhook settings appear to be correct.", "song", force=True) == 0:
            print("* Webhook sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    try:
        import pyotp
    except ModuleNotFoundError as exc:
        print_recovery_error(exc, "dependency", detail="pyotp")
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    if not check_internet():
        sys.exit(1)

    if args.flag_file:
        FLAG_FILE = os.path.expanduser(args.flag_file)
        flag_file_delete()
    else:
        if FLAG_FILE:
            FLAG_FILE = os.path.expanduser(FLAG_FILE)
            flag_file_delete()

    if args.send_test_email:
        print("* Sending test email notification ...\n")
        if send_email("spotify_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if args.check_interval:
        SPOTIFY_CHECK_INTERVAL = args.check_interval
        LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / SPOTIFY_CHECK_INTERVAL

    if args.offline_timer:
        SPOTIFY_INACTIVITY_CHECK = args.offline_timer

    if args.disappeared_timer:
        SPOTIFY_DISAPPEARED_CHECK_INTERVAL = args.disappeared_timer

    if TOKEN_SOURCE == "client":
        login_request_body_file_param = False
        if args.login_request_body_file:
            LOGIN_REQUEST_BODY_FILE = os.path.expanduser(args.login_request_body_file)
            login_request_body_file_param = True
        else:
            if LOGIN_REQUEST_BODY_FILE:
                LOGIN_REQUEST_BODY_FILE = os.path.expanduser(LOGIN_REQUEST_BODY_FILE)

        if LOGIN_REQUEST_BODY_FILE:
            if os.path.isfile(LOGIN_REQUEST_BODY_FILE):
                try:
                    DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN = parse_login_request_body_file(LOGIN_REQUEST_BODY_FILE)
                except Exception as e:
                    print_recovery_error(e, "file_read", detail=f"Login Protobuf file '{LOGIN_REQUEST_BODY_FILE}' cannot be processed: {e}")
                    sys.exit(1)
                else:
                    if not target_user_id and not args.list_friends and login_request_body_file_param:
                        print(f"* Login data correctly read from Protobuf file ({LOGIN_REQUEST_BODY_FILE}):")
                        print(" - Device ID:\t\t", DEVICE_ID)
                        print(" - System ID:\t\t", SYSTEM_ID)
                        print(" - User URI ID:\t\t", USER_URI_ID)
                        print(" - Refresh Token:\t", REFRESH_TOKEN, "\n")
                        sys.exit(0)
            else:
                print_recovery_error(FileNotFoundError(LOGIN_REQUEST_BODY_FILE), "file_read", detail=f"Login Protobuf file does not exist: {LOGIN_REQUEST_BODY_FILE}")
                sys.exit(1)

        vals = {
            "LOGIN_URL": LOGIN_URL,
            "USER_AGENT": USER_AGENT,
            "DEVICE_ID": DEVICE_ID,
            "SYSTEM_ID": SYSTEM_ID,
            "USER_URI_ID": USER_URI_ID,
            "REFRESH_TOKEN": REFRESH_TOKEN,
        }
        placeholders = {
            "DEVICE_ID": "your_spotify_app_device_id",
            "SYSTEM_ID": "your_spotify_app_system_id",
            "USER_URI_ID": "your_spotify_user_uri_id",
            "REFRESH_TOKEN": "your_spotify_app_refresh_token",
        }

        bad = [
            f"{k} {'missing' if not v else 'is placeholder'}"
            for k, v in vals.items()
            if not v or placeholders.get(k) == v
        ]
        if bad:
            print_recovery_error(context="secret", detail="Client mode requirements: " + "; ".join(bad))
            sys.exit(1)

        clienttoken_request_body_file_param = False
        if args.clienttoken_request_body_file:
            CLIENTTOKEN_REQUEST_BODY_FILE = os.path.expanduser(args.clienttoken_request_body_file)
            clienttoken_request_body_file_param = True
        else:
            if CLIENTTOKEN_REQUEST_BODY_FILE:
                CLIENTTOKEN_REQUEST_BODY_FILE = os.path.expanduser(CLIENTTOKEN_REQUEST_BODY_FILE)

        if CLIENTTOKEN_REQUEST_BODY_FILE:
            if os.path.isfile(CLIENTTOKEN_REQUEST_BODY_FILE):
                try:

                    (APP_VERSION, _, _, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL) = parse_clienttoken_request_body_file(CLIENTTOKEN_REQUEST_BODY_FILE)
                except Exception as e:
                    print_recovery_error(e, "file_read", detail=f"Client-token Protobuf file '{CLIENTTOKEN_REQUEST_BODY_FILE}' cannot be processed: {e}")
                    sys.exit(1)
                else:
                    if not target_user_id and not args.list_friends and clienttoken_request_body_file_param:
                        print(f"* Client token data correctly read from Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}):")
                        print(" - App version:\t\t", APP_VERSION)
                        print(" - CPU arch:\t\t", CPU_ARCH)
                        print(" - OS build:\t\t", OS_BUILD)
                        print(" - Platform:\t\t", PLATFORM)
                        print(" - OS major:\t\t", OS_MAJOR)
                        print(" - OS minor:\t\t", OS_MINOR)
                        print(" - Client model:\t", CLIENT_MODEL)
                        sys.exit(0)
            else:
                print_recovery_error(FileNotFoundError(CLIENTTOKEN_REQUEST_BODY_FILE), "file_read", detail=f"Client-token Protobuf file does not exist: {CLIENTTOKEN_REQUEST_BODY_FILE}")
                sys.exit(1)

        app_version_default = "1.2.62.580.g7e3d9a4f"
        if USER_AGENT and not APP_VERSION:
            try:
                APP_VERSION = ua_to_app_version(USER_AGENT)
            except Exception as e:
                print(f"Warning: wrong USER_AGENT defined, reverting to the default one for APP_VERSION: {e}")
                APP_VERSION = app_version_default
        else:
            APP_VERSION = app_version_default

    else:
        if args.spotify_dc_cookie:
            SP_DC_COOKIE = args.spotify_dc_cookie

        if not SP_DC_COOKIE or SP_DC_COOKIE == "your_sp_dc_cookie_value":
            advice = make_recovery_advice("secret.missing", "SP_DC_COOKIE is missing or still a placeholder", recovery_fix_with_guide(cookie_auth_recovery_fix(), COOKIE_GUIDE_URL), False)
            print(render_recovery_error(RecoveryError(advice)))
            sys.exit(1)

    if args.oauth_app_creds:
        try:
            SP_APP_CLIENT_ID, SP_APP_CLIENT_SECRET = args.oauth_app_creds.split(":", 1)
        except ValueError:
            print_recovery_error(context="config_invalid", detail="--oauth-app-creds must use SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET format")
            sys.exit(1)

    if SP_APP_TOKENS_FILE:
        SP_APP_TOKENS_FILE = os.path.expanduser(SP_APP_TOKENS_FILE)

    if args.list_friends:
        print("* Listing Spotify friends ...\n")
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            sp_friends = spotify_get_friends_json(sp_accessToken)
            spotify_list_friends(sp_friends, sp_accessToken)
            print("─" * HORIZONTAL_LINE)
        except Exception as e:
            auth_context = "client_auth" if TOKEN_SOURCE == "client" else "cookie_auth"
            print_recovery_error(e, auth_context)
            sys.exit(1)
        sys.exit(0)

    if not target_user_id:
        print_recovery_error(context="target_missing")
        sys.exit(1)

    if args.monitor_list:
        MONITOR_LIST_FILE = os.path.expanduser(args.monitor_list)
    else:
        if MONITOR_LIST_FILE:
            MONITOR_LIST_FILE = os.path.expanduser(MONITOR_LIST_FILE)

    if MONITOR_LIST_FILE:
        try:
            try:
                with open(MONITOR_LIST_FILE, encoding="utf-8") as file:
                    lines = file.read().splitlines()
            except UnicodeDecodeError:
                with open(MONITOR_LIST_FILE, encoding="cp1252") as file:
                    lines = file.read().splitlines()

            sp_tracks = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
        except Exception as e:
            print_recovery_error(e, "file_read", detail=f"Monitored-track file '{MONITOR_LIST_FILE}' cannot be opened: {e}")
            sys.exit(1)
    else:
        sp_tracks = []

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    else:
        if CSV_FILE:
            CSV_FILE = os.path.expanduser(CSV_FILE)

    if CSV_FILE:
        try:
            with open(CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print_recovery_error(e, "file_write", detail=f"CSV destination '{CSV_FILE}' cannot be opened for writing: {e}")
            sys.exit(1)

    if args.file_suffix:
        FILE_SUFFIX = str(args.file_suffix)
    else:
        if not FILE_SUFFIX:
            FILE_SUFFIX = str(target_user_id)

    if args.truncate:
        if args.truncate != 999:
            TRUNCATE_CHARS = args.truncate
        else:
            try:
                terminal_size = shutil.get_terminal_size()
                print(f"The detected terminal screen width is: {terminal_size.columns} characters\n")
                TRUNCATE_CHARS = terminal_size.columns
            except Exception as e:
                print(f"Error: Cannot determine terminal screen width: {e}")
                sys.exit(1)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    if not DISABLE_LOGGING:
        try:
            log_path = Path(os.path.expanduser(SP_LOGFILE))
            if log_path.parent != Path('.'):
                if log_path.suffix == "":
                    log_path = log_path.parent / f"{log_path.name}_{FILE_SUFFIX}.log"
            else:
                if log_path.suffix == "":
                    log_path = Path(f"{log_path.name}_{FILE_SUFFIX}.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            FINAL_LOG_PATH = str(log_path)
            sys.stdout = Logger(FINAL_LOG_PATH)
        except Exception as exc:
            print_recovery_error(exc, "file_write", detail=f"Log destination based on '{SP_LOGFILE}' cannot be opened: {exc}")
            sys.exit(1)
    else:
        FINAL_LOG_PATH = None

    if args.notify_active is True:
        ACTIVE_NOTIFICATION = True

    if args.notify_inactive is True:
        INACTIVE_NOTIFICATION = True

    if args.notify_track is True:
        TRACK_NOTIFICATION = True

    if args.notify_song_changes is True:
        SONG_NOTIFICATION = True

    if args.notify_loop is True:
        SONG_ON_LOOP_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False

    if args.webhook_enabled is not None:
        WEBHOOK_ENABLED = args.webhook_enabled

    if args.webhook_active is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_ACTIVE_NOTIFICATION = True

    if args.webhook_inactive is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_INACTIVE_NOTIFICATION = True

    if args.webhook_track is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_TRACK_NOTIFICATION = True

    if args.webhook_song_changes is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_SONG_NOTIFICATION = True

    if args.webhook_loop is True:
        WEBHOOK_ENABLED = True
        WEBHOOK_SONG_ON_LOOP_NOTIFICATION = True

    if args.webhook_errors is False:
        WEBHOOK_ERROR_NOTIFICATION = False

    if args.track_in_spotify is True:
        TRACK_SONGS = True

    if SMTP_HOST.startswith("your_smtp_server_"):
        ACTIVE_NOTIFICATION = False
        INACTIVE_NOTIFICATION = False
        TRACK_NOTIFICATION = False
        SONG_NOTIFICATION = False
        SONG_ON_LOOP_NOTIFICATION = False
        ERROR_NOTIFICATION = False

    startup_rows = build_startup_summary(target_user_id, cfg_path, env_path, FINAL_LOG_PATH)
    emit_startup_summary(startup_rows, show_full=bool(VERBOSE_MODE or DEBUG_MODE))
    playback_warning = container_playback_warning()
    if playback_warning is not None:
        print(f"* Warning: {playback_warning}\n")

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_song_notifications_signal_handler)
        signal.signal(signal.SIGCONT, toggle_track_notifications_signal_handler)
        signal.signal(signal.SIGPIPE, toggle_songs_on_loop_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_inactivity_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_inactivity_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    spotify_monitor_friend_uri(target_user_id, sp_tracks, CSV_FILE)

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()
