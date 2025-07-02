#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v2.2.1

Tool implementing real-time tracking of Spotify friends music activity:
https://github.com/misiektoja/spotify_monitor/

Python pip3 requirements:

requests
python-dateutil
urllib3
pyotp (optional, needed when the token source is set to cookie)
python-dotenv (optional)
"""

VERSION = "2.2.1"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
# Select the method used to obtain the Spotify access token
# Available options:
#   cookie - uses the sp_dc cookie to retrieve a token via the Spotify web endpoint (recommended)
#   client - uses captured credentials from the Spotify desktop client and a Protobuf-based login flow (for advanced users)
TOKEN_SOURCE = "cookie"

# ---------------------------------------------------------------------

# The section below is used when the token source is set to 'cookie'
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

# How often to check for user activity; in seconds
# Can also be set using the -c flag
SPOTIFY_CHECK_INTERVAL = 30  # 30 seconds

# Time to wait before retrying after an error; in seconds
SPOTIFY_ERROR_INTERVAL = 180  # 3 mins

# Time after which a user is considered inactive (based on last activity); in seconds
# Can also be set using the -o flag
# Note: If the user listens to songs longer than this value, they may be marked as inactive
SPOTIFY_INACTIVITY_CHECK = 660  # 11 mins

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

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Value added/subtracted via signal handlers to adjust inactivity timeout (SPOTIFY_INACTIVITY_CHECK); in seconds
SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# Maximum number of attempts to get a valid access token in a single run of the spotify_get_access_token_from_sp_dc() function
# Used only when the token source is set to 'cookie'
TOKEN_MAX_RETRIES = 10

# Interval between access token retry attempts; in seconds
# Used only when the token source is set to 'cookie'
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
SP_DC_COOKIE = ""
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
SPOTIFY_CHECK_INTERVAL = 0
SPOTIFY_ERROR_INTERVAL = 0
SPOTIFY_INACTIVITY_CHECK = 0
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
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE = 0
TOKEN_MAX_RETRIES = 0
TOKEN_RETRY_TIMEOUT = 0.0

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "spotify_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("REFRESH_TOKEN", "SP_DC_COOKIE", "SMTP_PASSWORD")

# Strings removed from track names for generating proper Genius search URLs
re_search_str = r'remaster|extended|original mix|remix|original soundtrack|radio( |-)edit|\(feat\.|( \(.*version\))|( - .*version)'
re_replace_str = r'( - (\d*)( )*remaster$)|( - (\d*)( )*remastered( version)*( \d*)*.*$)|( \((\d*)( )*remaster\)$)|( - (\d+) - remaster$)|( - extended$)|( - extended mix$)|( - (.*); extended mix$)|( - extended version$)|( - (.*) remix$)|( - remix$)|( - remixed by .*$)|( - original mix$)|( - .*original soundtrack$)|( - .*radio( |-)edit$)|( \(feat\. .*\)$)|( \(\d+.*Remaster.*\)$)|( \(.*Version\))|( - .*version)'

# Default value for network-related timeouts in functions; in seconds
FUNCTION_TIMEOUT = 15

# Default value for alarm signal handler timeout; in seconds
ALARM_TIMEOUT = 15
ALARM_RETRY = 10

# Variables for caching functionality of the Spotify access and refresh token to avoid unnecessary refreshing
SP_CACHED_ACCESS_TOKEN = None
SP_CACHED_REFRESH_TOKEN = None
SP_ACCESS_TOKEN_EXPIRES_AT = 0
SP_CACHED_CLIENT_ID = ""

# URL of the Spotify Web Player endpoint to get access token
TOKEN_URL = "https://open.spotify.com/api/token"

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

if sys.version_info < (3, 6):
    print("* Error: Python version 3.6 or higher required !")
    sys.exit(1)

import time
from time import time_ns
import string
import json
import os
from datetime import datetime
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
from urllib.parse import quote_plus, quote, urlparse
import subprocess
import platform
import re
import ipaddress
from html import escape
import base64
import random
import shutil
from pathlib import Path
import secrets
from typing import Optional
from email.utils import parsedate_to_datetime

import urllib3
if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SESSION = req.Session()

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry = Retry(
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


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.logfile.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
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
    sys.exit(0)


# Checks internet connectivity
def check_internet(url=CHECK_INTERNET_URL, timeout=CHECK_INTERNET_TIMEOUT, verify=VERIFY_SSL):
    try:
        _ = req.get(url, headers={'User-Agent': USER_AGENT}, timeout=timeout, verify=verify)
        return True
    except req.RequestException as e:
        print(f"* No connectivity, please check your network:\n\n{e}")
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


# Sends email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            print("Error sending email - SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("Error sending email - SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        print("Error sending email - SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD configuration options)")
        return 1

    if not subject or not isinstance(subject, str):
        print("Error sending email - SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print("Error sending email - SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
        smtpObj.login(SMTP_USER, SMTP_PASSWORD)
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

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
    except Exception as e:
        print(f"Error sending email: {e}")
        return 1
    return 0


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
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]}, {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


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
                load_dotenv(env_path, override=True)
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
                    print(f"* Error: Protobuf file ({LOGIN_REQUEST_BODY_FILE}) cannot be processed: {e}")
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
                    print(f"* Error: Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}) cannot be processed: {e}")
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


# Returns Apple & Genius search URLs for specified track
def get_apple_genius_search_urls(artist, track):
    genius_search_string = f"{artist} {track}"
    youtube_music_search_string = quote_plus(f"{artist} {track}")
    if re.search(re_search_str, genius_search_string, re.IGNORECASE):
        genius_search_string = re.sub(re_replace_str, '', genius_search_string, flags=re.IGNORECASE)
    apple_search_string = quote(f"{artist} {track}")
    apple_search_url = f"https://music.apple.com/pl/search?term={apple_search_string}"
    genius_search_url = f"https://genius.com/search?q={quote_plus(genius_search_string)}"
    youtube_music_search_url = f"https://music.youtube.com/search?q={youtube_music_search_string}"
    return apple_search_url, genius_search_url, youtube_music_search_url


# Sends a lightweight request to check Spotify token validity
def check_token_validity(access_token: str, client_id: Optional[str] = None, user_agent: Optional[str] = None) -> bool:
    url = "https://api.spotify.com/v1/me"
    headers = {"Authorization": f"Bearer {access_token}"}

    if user_agent is not None:
        headers.update({
            "User-Agent": user_agent
        })

    if TOKEN_SOURCE == "cookie" and client_id is not None:
        headers.update({
            "Client-Id": client_id
        })

    if platform.system() != 'Windows':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT + 2)
    try:
        response = req.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        valid = response.status_code == 200
    except Exception:
        valid = False
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
        response = session.head("https://open.spotify.com/", headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
    except TimeoutException as e:
        raise Exception(f"fetch_server_time() head network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        raise Exception(f"fetch_server_time() head network request error: {e}")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

    return int(parsedate_to_datetime(response.headers["Date"]).timestamp())


# Creates a TOTP object using a secret derived from transformed cipher bytes
def generate_totp():
    import pyotp

    secret_cipher_dict = {
        "8": [37, 84, 32, 76, 87, 90, 87, 47, 13, 75, 48, 54, 44, 28, 19, 21, 22],
        "7": [59, 91, 66, 74, 30, 66, 74, 38, 46, 50, 72, 61, 44, 71, 86, 39, 89],
        "6": [21, 24, 85, 46, 48, 35, 33, 8, 11, 63, 76, 12, 55, 77, 14, 7, 54],
        "5": [12, 56, 76, 33, 88, 44, 88, 33, 78, 78, 11, 66, 22, 22, 55, 69, 54]
    }
    secret_cipher_bytes = secret_cipher_dict["8"]

    transformed = [e ^ ((t % 33) + 9) for t, e in enumerate(secret_cipher_bytes)]
    joined = "".join(str(num) for num in transformed)
    hex_str = joined.encode().hex()
    secret = base64.b32encode(bytes.fromhex(hex_str)).decode().rstrip("=")

    return pyotp.TOTP(secret, digits=6, interval=30)


# Refreshes the Spotify access token using the sp_dc cookie, tries first with mode "transport" and if needed with "init"
def refresh_access_token_from_sp_dc(sp_dc: str) -> dict:
    transport = True
    init = True
    session = req.Session()
    session.cookies.set("sp_dc", sp_dc)
    data: dict = {}
    token = ""

    server_time = fetch_server_time(session, USER_AGENT)
    totp_obj = generate_totp()
    client_time = int(time_ns() / 1000 / 1000)
    otp_value = totp_obj.at(server_time)

    params = {
        "reason": "transport",
        "productType": "web-player",
        "totp": otp_value,
        "totpServer": otp_value,
        "totpVer": 8,
        "sTime": server_time,
        "cTime": client_time,
        "buildDate": time.strftime("%Y-%m-%d", time.gmtime(server_time)),
        "buildVer": f"web-player_{time.strftime('%Y-%m-%d', time.gmtime(server_time))}_{server_time * 1000}_{secrets.token_hex(4)}",
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

        response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        data = response.json()
        token = data.get("accessToken", "")

    except (req.RequestException, TimeoutException, req.HTTPError, ValueError) as e:
        transport = False
        last_err = str(e)
    finally:
        if platform.system() != "Windows":
            signal.alarm(0)

    if not transport or (transport and not check_token_validity(token, data.get("clientId", ""), USER_AGENT)):
        params["reason"] = "init"

        try:
            if platform.system() != "Windows":
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(FUNCTION_TIMEOUT + 2)

            response = session.get(TOKEN_URL, params=params, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
            response.raise_for_status()
            data = response.json()
            token = data.get("accessToken", "")

        except (req.RequestException, TimeoutException, req.HTTPError, ValueError) as e:
            init = False
            last_err = str(e)
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
        return SP_CACHED_ACCESS_TOKEN

    max_retries = TOKEN_MAX_RETRIES
    retry = 0

    while retry < max_retries:
        token_data = refresh_access_token_from_sp_dc(sp_dc)
        token = token_data["access_token"]
        client_id = token_data.get("client_id", "")
        length = token_data["length"]

        SP_CACHED_ACCESS_TOKEN = token
        SP_ACCESS_TOKEN_EXPIRES_AT = token_data["expires_at"]
        SP_CACHED_CLIENT_ID = client_id

        if SP_CACHED_ACCESS_TOKEN is None or not check_token_validity(SP_CACHED_ACCESS_TOKEN, SP_CACHED_CLIENT_ID, USER_AGENT):
            retry += 1
            time.sleep(TOKEN_RETRY_TIMEOUT)
        else:
            break

    if retry == max_retries:
        if SP_CACHED_ACCESS_TOKEN is not None:
            print(f"* Token appears to be still invalid after {max_retries} attempts, returning token anyway")
            print_cur_ts("Timestamp:\t\t\t")
            return SP_CACHED_ACCESS_TOKEN
        else:
            raise RuntimeError(f"Failed to obtain a valid Spotify access token after {max_retries} attempts")

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
        return SP_CACHED_ACCESS_TOKEN

    if not client_token:
        raise Exception("Client token is missing")

    if SP_CACHED_REFRESH_TOKEN:
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
        response = req.post(LOGIN_URL, headers=headers, data=protobuf_body, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    except TimeoutException as e:
        raise Exception(f"spotify_get_access_token_from_client() network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
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
                raise Exception(f"Request failed with status {response.status_code}: invalid grant during refresh ({desc})")

        raise Exception(f"Request failed with status code {response.status_code}\nResponse Headers: {response.headers}\nResponse Content (raw): {response.content}\nResponse text: {response.text}")

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
    return access_token


# Fetches fresh client token
def spotify_get_client_token(app_version, device_id, system_id, **device_overrides):
    global SP_CACHED_CLIENT_TOKEN, SP_CLIENT_TOKEN_EXPIRES_AT

    if SP_CACHED_CLIENT_TOKEN and time.time() < SP_CLIENT_TOKEN_EXPIRES_AT:
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
        response = req.post(CLIENTTOKEN_URL, headers=headers, data=body, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
    except TimeoutException as e:
        raise Exception(f"spotify_get_client_token() network request timeout after {display_time(FUNCTION_TIMEOUT + 2)}: {e}")
    except Exception as e:
        raise Exception(f"spotify_get_client_token() network request error: {e}")
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)

    if response.status_code != 200:
        raise Exception(f"clienttoken request failed - status {response.status_code}\nHeaders: {response.headers}\nBody (raw): {response.content[:120]}...")

    parsed = parse_protobuf_message(response.content)
    inner = parsed.get(2, {})
    client_token = deep_flatten(inner.get(1)) if inner.get(1) else None
    ttl = int(inner.get(3, 0)) or 1209600

    if not client_token:
        raise Exception("clienttoken response did not contain a token")

    SP_CACHED_CLIENT_TOKEN = client_token
    SP_CLIENT_TOKEN_EXPIRES_AT = time.time() + ttl

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
        client_token = spotify_get_client_token(app_version=APP_VERSION, device_id=device_id, system_id=system_id, cpu_arch=CPU_ARCH, os_build=OS_BUILD, platform=PLATFORM, os_major=OS_MAJOR, os_minor=OS_MINOR, client_model=CLIENT_MODEL)

    try:
        return spotify_get_access_token_from_client(device_id, system_id, user_uri_id, refresh_token, client_token)
    except Exception as e:
        err = str(e).lower()
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

            client_token = spotify_get_client_token(app_version=APP_VERSION, device_id=DEVICE_ID, system_id=SYSTEM_ID, cpu_arch=CPU_ARCH, os_build=OS_BUILD, platform=PLATFORM, os_major=OS_MAJOR, os_minor=OS_MINOR, client_model=CLIENT_MODEL)

            return spotify_get_access_token_from_client(device_id, system_id, user_uri_id, refresh_token, client_token)
        raise


# --------------------------------------------------------


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

    response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
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


# Prints the list of Spotify friends with the last listened track (-l flag)
def spotify_list_friends(friend_activity):

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

        print("─" * HORIZONTAL_LINE)
        print(f"Username:\t\t\t{sp_username}")
        print(f"User URI ID:\t\t\t{sp_uri}")
        print(f"User URL:\t\t\t{spotify_convert_uri_to_url('spotify:user:' + sp_uri)}")
        print(f"\nLast played:\t\t\t{sp_artist} - {sp_track}\n")
        if 'spotify:playlist:' in sp_playlist_uri:
            print(f"Playlist:\t\t\t{sp_playlist}")
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

        apple_search_url, genius_search_url, youtube_music_search_url = get_apple_genius_search_urls(str(sp_artist), str(sp_track))

        print(f"Apple Music URL:\t\t{apple_search_url}")
        print(f"YouTube Music URL:\t\t{youtube_music_search_url}")
        print(f"Genius lyrics URL:\t\t{genius_search_url}")

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


# Returns information for specific Spotify track URI
def spotify_get_track_info(access_token, track_uri):
    track_id = track_uri.split(':', 2)[2]
    url = "https://api.spotify.com/v1/tracks/" + track_id
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })
    # add si parameter so link opens in native Spotify app after clicking
    si = "?si=1"

    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        json_response = response.json()
        sp_track_duration = int(json_response.get("duration_ms") / 1000)
        sp_track_url = json_response["external_urls"].get("spotify") + si
        sp_track_name = json_response.get("name")
        sp_artist_url = json_response["artists"][0]["external_urls"].get("spotify") + si
        sp_artist_name = json_response["artists"][0].get("name")
        sp_album_url = json_response["album"]["external_urls"].get("spotify") + si
        sp_album_name = json_response["album"].get("name")
        return {"sp_track_duration": sp_track_duration, "sp_track_url": sp_track_url, "sp_artist_url": sp_artist_url, "sp_album_url": sp_album_url, "sp_track_name": sp_track_name, "sp_artist_name": sp_artist_name, "sp_album_name": sp_album_name}
    except Exception:
        raise


# Returns information for specific Spotify playlist URI
def spotify_get_playlist_info(access_token, playlist_uri):
    playlist_id = playlist_uri.split(':', 2)[2]
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}?fields=name,owner,followers,external_urls"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })
    # add si parameter so link opens in native Spotify app after clicking
    si = "?si=1"

    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        json_response = response.json()
        sp_playlist_name = json_response.get("name")
        sp_playlist_owner = json_response["owner"].get("display_name")
        sp_playlist_owner_url = json_response["owner"]["external_urls"].get("spotify")
        sp_playlist_followers = int(json_response["followers"].get("total"))
        sp_playlist_url = json_response["external_urls"].get("spotify") + si
        return {"sp_playlist_name": sp_playlist_name, "sp_playlist_owner": sp_playlist_owner, "sp_playlist_owner_url": sp_playlist_owner_url, "sp_playlist_followers": sp_playlist_followers, "sp_playlist_url": sp_playlist_url}
    except Exception:
        raise


# Gets basic information about access token owner
def spotify_get_current_user(access_token) -> dict | None:
    url = "https://api.spotify.com/v1/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    if platform.system() != 'Windows':
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT + 2)
    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        response.raise_for_status()
        data = response.json()

        user_info = {
            "display_name": data.get("display_name"),
            "uri": data.get("uri"),
            "is_premium": data.get("product") == "premium",
            "country": data.get("country"),
            "email": data.get("email"),
            "spotify_url": data.get("external_urls", {}).get("spotify") + "?si=1" if data.get("external_urls", {}).get("spotify") else None
        }

        return user_info
    except Exception as e:
        print(f"* Error: {e}")
        return None
    finally:
        if platform.system() != 'Windows':
            signal.alarm(0)


# Checks if a Spotify user URI ID has been deleted
def is_user_removed(access_token, user_uri_id):
    url = f"https://api.spotify.com/v1/users/{user_uri_id}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    if TOKEN_SOURCE == "cookie":
        headers.update({
            "Client-Id": SP_CACHED_CLIENT_ID
        })

    try:
        response = SESSION.get(url, headers=headers, timeout=FUNCTION_TIMEOUT, verify=VERIFY_SSL)
        if response.status_code == 404:
            return True
        return False
    except Exception:
        return False


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
        os.startfile(spotify_convert_uri_to_url(f"spotify:track:{sp_track_uri_id}"))


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


# Resolves an executable path by checking if it's a valid file or searching in $PATH
def resolve_executable(path):
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path

    found = shutil.which(path)
    if found:
        return found

    raise FileNotFoundError(f"Could not find executable '{path}'")


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
    error_500_counter = 0
    error_500_start_ts = 0
    error_network_issue_counter = 0
    error_network_issue_start_ts = 0
    sp_accessToken = ""

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print(f"* Error: {e}")

    email_sent = False

    out = f"Monitoring user {user_uri_id}"
    print(out)
    print("-" * len(out))

    tracks_upper = {t.upper() for t in tracks}

    # Start loop
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
            email_sent = False
            if platform.system() != 'Windows':
                signal.alarm(0)
        except TimeoutException:
            if platform.system() != 'Windows':
                signal.alarm(0)
            print(f"spotify_*() function timeout after {display_time(ALARM_TIMEOUT)}, retrying in {display_time(ALARM_RETRY)}")
            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(ALARM_RETRY)
            continue
        except Exception as e:
            if platform.system() != 'Windows':
                signal.alarm(0)

            err = str(e).lower()

            print(f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: {e}")

            if TOKEN_SOURCE == 'cookie' and '401' in err:
                SP_CACHED_ACCESS_TOKEN = None

            client_errs = ['access token', 'invalid client token', 'expired client token', 'refresh token has been revoked', 'refresh token has expired', 'refresh token is invalid', 'invalid grant during refresh']
            cookie_errs = ['access token', 'unauthorized', 'unsuccessful token request']

            if TOKEN_SOURCE == 'client' and any(k in err for k in client_errs):
                print(f"* Error: client or refresh token may be invalid or expired!")
                if ERROR_NOTIFICATION and not email_sent:
                    m_subject = f"spotify_monitor: client or refresh token may be invalid or expired! (uri: {user_uri_id})"
                    m_body = f"Client or refresh token may be invalid or expired!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>Client or refresh token may be invalid or expired!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                    email_sent = True

            elif TOKEN_SOURCE == 'cookie' and any(k in err for k in cookie_errs):
                print(f"* Error: sp_dc may be invalid/expired or Spotify has broken sth again!")
                if ERROR_NOTIFICATION and not email_sent:
                    m_subject = f"spotify_monitor: sp_dc may be invalid/expired or Spotify has broken sth again! (uri: {user_uri_id})"
                    m_body = f"sp_dc may be invalid/expired or Spotify has broken sth again!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>sp_dc may be invalid/expired or Spotify has broken sth again!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                    email_sent = True

            print_cur_ts("Timestamp:\t\t\t")
            time.sleep(SPOTIFY_ERROR_INTERVAL)
            continue

        playlist_m_body = ""
        playlist_m_body_html = ""
        played_for_m_body = ""
        played_for_m_body_html = ""
        is_playlist = False

        # User is found in the Spotify's friend list just after starting the tool
        if sp_found:
            user_not_found = False

            user_info = spotify_get_current_user(sp_accessToken)
            if user_info:
                print(f"Token belongs to:\t\t{user_info.get('display_name', '')} (via {TOKEN_SOURCE})\n\t\t\t\t[ {user_info.get('spotify_url')} ]")

            sp_track_uri = sp_data["sp_track_uri"]
            sp_track_uri_id = sp_data["sp_track_uri_id"]
            sp_album_uri = sp_data["sp_album_uri"]
            sp_playlist_uri = sp_data["sp_playlist_uri"]

            sp_playlist_data = {}
            try:
                sp_track_data = spotify_get_track_info(sp_accessToken, sp_track_uri)
                if 'spotify:playlist:' in sp_playlist_uri:
                    is_playlist = True
                    sp_playlist_data = spotify_get_playlist_info(sp_accessToken, sp_playlist_uri)
                    if not sp_playlist_data:
                        is_playlist = False
                else:
                    is_playlist = False
            except Exception as e:
                print(f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: {e}")
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
                sp_playlist_url = sp_playlist_data.get("sp_playlist_url")
                playlist_m_body = f"\nPlaylist: {sp_playlist}"
                playlist_m_body_html = f"<br>Playlist: <a href=\"{sp_playlist_url}\">{escape(sp_playlist)}</a>"

            print(f"\nUsername:\t\t\t{sp_username}")
            print(f"User URI ID:\t\t\t{sp_data['sp_uri']}")
            print(f"\nLast played:\t\t\t{sp_artist} - {sp_track}")
            print(f"Duration:\t\t\t{display_time(sp_track_duration)}\n")
            if is_playlist:
                print(f"Playlist:\t\t\t{sp_playlist}")

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

            apple_search_url, genius_search_url, youtube_music_search_url = get_apple_genius_search_urls(str(sp_artist), str(sp_track))

            print(f"Apple Music URL:\t\t{apple_search_url}")
            print(f"YouTube Music URL:\t\t{youtube_music_search_url}")
            print(f"Genius lyrics URL:\t\t{genius_search_url}")

            if not is_playlist:
                sp_playlist = ""

            print(f"\nLast activity:\t\t\t{get_date_from_ts(sp_ts)}")

            # Friend is currently active (listens to music)
            if (cur_ts - sp_ts) <= SPOTIFY_INACTIVITY_CHECK:
                sp_active_ts_start = sp_ts - sp_track_duration
                sp_active_ts_stop = 0
                listened_songs = 1
                song_on_loop = 1
                print("\n*** Friend is currently ACTIVE !")

                if sp_track.upper() in tracks_upper or sp_playlist.upper() in tracks_upper or sp_album.upper() in tracks_upper:
                    print("*** Track/playlist/album matched with the list!")

                try:
                    if csv_file_name:
                        write_csv_entry(csv_file_name, datetime.fromtimestamp(int(cur_ts)), sp_artist, sp_track, sp_playlist, sp_album, datetime.fromtimestamp(int(sp_ts)))
                except Exception as e:
                    print(f"* Error: {e}")

                if ACTIVE_NOTIFICATION:
                    m_subject = f"Spotify user {sp_username} is active: '{sp_artist} - {sp_track}'"
                    m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}\n\nApple Music URL: {apple_search_url}\nYouTube Music URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}\n\nLast activity: {get_date_from_ts(sp_ts)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                    m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}<br><br>Apple Music URL: <a href=\"{apple_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>YouTube Music URL: <a href=\"{youtube_music_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br><br>Last activity: {get_date_from_ts(sp_ts)}{get_cur_ts('<br>Timestamp: ')}</body></html>"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)

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

            print(f"\nTracks/playlists/albums to monitor: {tracks}")
            print_cur_ts("\nTimestamp:\t\t\t")

            sp_ts_old = sp_ts
            alive_counter = 0

            email_sent = False

            disappeared_counter = 0

            # Primary loop
            while True:

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
                        email_sent = False
                        if platform.system() != 'Windows':
                            signal.alarm(0)
                        break
                    except TimeoutException:
                        if platform.system() != 'Windows':
                            signal.alarm(0)
                        print(f"spotify_*() function timeout after {display_time(ALARM_TIMEOUT)}, retrying in {display_time(ALARM_RETRY)}")
                        print_cur_ts("Timestamp:\t\t\t")
                        time.sleep(ALARM_RETRY)
                    except Exception as e:
                        if platform.system() != 'Windows':
                            signal.alarm(0)

                        err = str(e).lower()

                        if TOKEN_SOURCE == 'cookie' and '401' in err:
                            SP_CACHED_ACCESS_TOKEN = None

                        str_matches = ["500 server", "504 server", "502 server", "503 server"]
                        if any(x in err for x in str_matches):
                            if not error_500_start_ts:
                                error_500_start_ts = int(time.time())
                                error_500_counter = 1
                            else:
                                error_500_counter += 1

                        str_matches = ["timed out", "timeout", "name resolution", "failed to resolve", "family not supported", "429 client", "aborted"]
                        if any(x in err for x in str_matches) or str(e) == '':
                            if not error_network_issue_start_ts:
                                error_network_issue_start_ts = int(time.time())
                                error_network_issue_counter = 1
                            else:
                                error_network_issue_counter += 1

                        if error_500_start_ts and (error_500_counter >= ERROR_500_NUMBER_LIMIT and (int(time.time()) - error_500_start_ts) >= ERROR_500_TIME_LIMIT):
                            print(f"* Error 50x ({error_500_counter}x times in the last {display_time((int(time.time()) - error_500_start_ts))}): '{e}'")
                            print_cur_ts("Timestamp:\t\t\t")
                            error_500_start_ts = 0
                            error_500_counter = 0

                        elif error_network_issue_start_ts and (error_network_issue_counter >= ERROR_NETWORK_ISSUES_NUMBER_LIMIT and (int(time.time()) - error_network_issue_start_ts) >= ERROR_NETWORK_ISSUES_TIME_LIMIT):
                            print(f"* Error with network ({error_network_issue_counter}x times in the last {display_time((int(time.time()) - error_network_issue_start_ts))}): '{e}'")
                            print_cur_ts("Timestamp:\t\t\t")
                            error_network_issue_start_ts = 0
                            error_network_issue_counter = 0

                        elif not error_500_start_ts and not error_network_issue_start_ts:
                            print(f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: '{e}'")

                            client_errs = ['access token', 'invalid client token', 'expired client token', 'refresh token has been revoked', 'refresh token has expired', 'refresh token is invalid', 'invalid grant during refresh']
                            cookie_errs = ['access token', 'unauthorized', 'unsuccessful token request']

                            if TOKEN_SOURCE == 'client' and any(k in err for k in client_errs):
                                print(f"* Error: client or refresh token may be invalid or expired!")
                                if ERROR_NOTIFICATION and not email_sent:
                                    m_subject = f"spotify_monitor: client or refresh token may be invalid or expired! (uri: {user_uri_id})"
                                    m_body = f"Client or refresh token may be invalid or expired!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>Client or refresh token may be invalid or expired!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                                    email_sent = True

                            elif TOKEN_SOURCE == 'cookie' and any(k in err for k in cookie_errs):
                                print(f"* Error: sp_dc may be invalid/expired or Spotify has broken sth again!")
                                if ERROR_NOTIFICATION and not email_sent:
                                    m_subject = f"spotify_monitor: sp_dc may be invalid/expired or Spotify has broken sth again! (uri: {user_uri_id})"
                                    m_body = f"sp_dc may be invalid/expired or Spotify has broken sth again!\n{e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                                    m_body_html = f"<html><head></head><body>sp_dc may be invalid/expired or Spotify has broken sth again!<br>{escape(str(e))}{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                                    send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                                    email_sent = True

                            print_cur_ts("Timestamp:\t\t\t")
                        time.sleep(SPOTIFY_ERROR_INTERVAL)

                if sp_found is False:
                    # User has disappeared from the Spotify's friend list or account has been removed
                    disappeared_counter += 1
                    if disappeared_counter < REMOVED_DISAPPEARED_COUNTER:
                        time.sleep(SPOTIFY_CHECK_INTERVAL)
                        continue
                    if user_not_found is False:
                        if is_user_removed(sp_accessToken, user_uri_id):
                            print(f"Spotify user '{user_uri_id}' ({sp_username}) was probably removed! Retrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals")
                            if ERROR_NOTIFICATION:
                                m_subject = f"Spotify user {user_uri_id} ({sp_username}) was probably removed!"
                                m_body = f"Spotify user {user_uri_id} ({sp_username}) was probably removed\nRetrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                                m_body_html = f"<html><head></head><body>Spotify user {user_uri_id} ({sp_username}) was probably removed<br>Retrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                                print(f"Sending email notification to {RECEIVER_EMAIL}")
                                send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                        else:
                            print(f"Spotify user '{user_uri_id}' ({sp_username}) has disappeared - make sure your friend is followed and has activity sharing enabled. Retrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals")
                            if ERROR_NOTIFICATION:
                                m_subject = f"Spotify user {user_uri_id} ({sp_username}) has disappeared!"
                                m_body = f"Spotify user {user_uri_id} ({sp_username}) has disappeared - make sure your friend is followed and has activity sharing enabled\nRetrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                                m_body_html = f"<html><head></head><body>Spotify user {user_uri_id} ({sp_username}) has disappeared - make sure your friend is followed and has activity sharing enabled<br>Retrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                                print(f"Sending email notification to {RECEIVER_EMAIL}")
                                send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                        print_cur_ts("Timestamp:\t\t\t")
                        user_not_found = True
                    time.sleep(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)
                    continue
                else:
                    # User reappeared in the Spotify's friend list
                    disappeared_counter = 0
                    if user_not_found is True:
                        print(f"Spotify user {user_uri_id} ({sp_username}) has reappeared!")
                        if ERROR_NOTIFICATION:
                            m_subject = f"Spotify user {user_uri_id} ({sp_username}) has reappeared!"
                            m_body = f"Spotify user {user_uri_id} ({sp_username}) has reappeared!{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                            m_body_html = f"<html><head></head><body>Spotify user {user_uri_id} ({sp_username}) has reappeared!{get_cur_ts('<br><br>Timestamp: ')}</body></html>"
                            print(f"Sending email notification to {RECEIVER_EMAIL}")
                            send_email(m_subject, m_body, m_body_html, SMTP_SSL)
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
                        if 'spotify:playlist:' in sp_playlist_uri:
                            is_playlist = True
                            sp_playlist_data = spotify_get_playlist_info(sp_accessToken, sp_playlist_uri)
                            if not sp_playlist_data:
                                is_playlist = False
                        else:
                            is_playlist = False
                    except Exception as e:
                        print(f"* Error, retrying in {display_time(SPOTIFY_ERROR_INTERVAL)}: {e}")
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
                        sp_playlist_url = sp_playlist_data.get("sp_playlist_url")
                        playlist_m_body = f"\nPlaylist: {sp_playlist}"
                        playlist_m_body_html = f"<br>Playlist: <a href=\"{sp_playlist_url}\">{escape(sp_playlist)}</a>"
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

                    if (sp_ts - sp_ts_old) < (sp_track_duration - 1):
                        played_for_time = sp_ts - sp_ts_old
                        listened_percentage = (played_for_time) / (sp_track_duration - 1)
                        played_for = display_time(played_for_time)
                        if listened_percentage <= SKIPPED_SONG_THRESHOLD:
                            played_for += f" - SKIPPED ({int(listened_percentage * 100)}%)"
                            skipped_songs += 1
                        else:
                            played_for += f" ({int(listened_percentage * 100)}%)"
                        print(f"Played for:\t\t\t{played_for}")
                        played_for_m_body = f"\nPlayed for: {played_for}"
                        played_for_m_body_html = f"<br>Played for: {played_for}"
                    else:
                        played_for_m_body = ""
                        played_for_m_body_html = ""

                    if is_playlist:
                        print(f"Playlist:\t\t\t{sp_playlist}")

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

                    apple_search_url, genius_search_url, youtube_music_search_url = get_apple_genius_search_urls(str(sp_artist), str(sp_track))

                    print(f"Apple Music URL:\t\t{apple_search_url}")
                    print(f"YouTube Music URL:\t\t{youtube_music_search_url}")
                    print(f"Genius lyrics URL:\t\t{genius_search_url}")

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

                        print(f"\n*** Friend got ACTIVE after being offline for {calculate_timespan(int(sp_active_ts_start), int(sp_active_ts_stop))} ({get_date_from_ts(sp_active_ts_stop)})")
                        m_subject = f"Spotify user {sp_username} is active: '{sp_artist} - {sp_track}' (after {calculate_timespan(int(sp_active_ts_start), int(sp_active_ts_stop), show_seconds=False)} - {get_short_date_from_ts(sp_active_ts_stop)})"
                        friend_active_m_body = f"\n\nFriend got active after being offline for {calculate_timespan(int(sp_active_ts_start), int(sp_active_ts_stop))}\nLast activity (before getting offline): {get_date_from_ts(sp_active_ts_stop)}"
                        friend_active_m_body_html = f"<br><br>Friend got active after being offline for <b>{calculate_timespan(int(sp_active_ts_start), int(sp_active_ts_stop))}</b><br>Last activity (before getting offline): <b>{get_date_from_ts(sp_active_ts_stop)}</b>"
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

                        m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{played_for_m_body}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}\n\nApple Music URL: {apple_search_url}\nYouTube Music URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}{friend_active_m_body}\n\nLast activity: {get_date_from_ts(sp_ts)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{played_for_m_body_html}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}<br><br>Apple Music URL: <a href=\"{apple_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>YouTube Music URL: <a href=\"{youtube_music_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a>{friend_active_m_body_html}<br><br>Last activity: {get_date_from_ts(sp_ts)}{get_cur_ts('<br>Timestamp: ')}</body></html>"

                        if ACTIVE_NOTIFICATION:
                            print(f"Sending email notification to {RECEIVER_EMAIL}")
                            send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                            email_sent = True

                    on_the_list = False
                    if sp_track.upper() in tracks_upper or sp_playlist.upper() in tracks_upper or sp_album.upper() in tracks_upper:
                        print("\n*** Track/playlist/album matched with the list!")
                        on_the_list = True

                    if (TRACK_NOTIFICATION and on_the_list and not email_sent) or (SONG_NOTIFICATION and not email_sent):
                        m_subject = f"Spotify user {sp_username}: '{sp_artist} - {sp_track}'"
                        m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{played_for_m_body}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}\n\nApple Music URL: {apple_search_url}\nYouTube Music URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}\n\nLast activity: {get_date_from_ts(sp_ts)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{played_for_m_body_html}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}<br><br>Apple Music URL: <a href=\"{apple_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>YouTube Music URL: <a href=\"{youtube_music_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br><br>Last activity: {get_date_from_ts(sp_ts)}{get_cur_ts('<br>Timestamp: ')}</body></html>"
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                        email_sent = True

                    if song_on_loop == SONG_ON_LOOP_VALUE and SONG_ON_LOOP_NOTIFICATION:
                        m_subject = f"Spotify user {sp_username} plays song on loop: '{sp_artist} - {sp_track}'"
                        m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{played_for_m_body}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}\n\nApple Music URL: {apple_search_url}\nYouTube Music URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}\n\nUser plays song on LOOP ({song_on_loop} times)\n\nLast activity: {get_date_from_ts(sp_ts)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                        m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{played_for_m_body_html}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}<br><br>Apple Music URL: <a href=\"{apple_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>YouTube Music URL: <a href=\"{youtube_music_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br><br>User plays song on LOOP (<b>{song_on_loop}</b> times)<br><br>Last activity: {get_date_from_ts(sp_ts)}{get_cur_ts('<br>Timestamp: ')}</body></html>"
                        if not email_sent:
                            print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, m_body_html, SMTP_SSL)

                    try:
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(cur_ts)), sp_artist, sp_track, sp_playlist, sp_album, datetime.fromtimestamp(int(sp_ts)))
                    except Exception as e:
                        print(f"* Error: {e}")

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
                        if INACTIVE_NOTIFICATION:
                            m_subject = f"Spotify user {sp_username} is inactive: '{sp_artist} - {sp_track}' (after {calculate_timespan(int(sp_active_ts_stop), int(sp_active_ts_start), show_seconds=False)}: {get_range_of_dates_from_tss(sp_active_ts_start, sp_active_ts_stop, short=True)})"
                            m_body = f"Last played: {sp_artist} - {sp_track}\nDuration: {display_time(sp_track_duration)}{played_for_m_body}{playlist_m_body}\nAlbum: {sp_album}{context_m_body}\n\nApple Music URL: {apple_search_url}\nYouTube Music URL:{youtube_music_search_url}\nGenius lyrics URL: {genius_search_url}\n\nFriend got inactive after listening to music for {calculate_timespan(int(sp_active_ts_stop), int(sp_active_ts_start))}\nFriend played music from {get_range_of_dates_from_tss(sp_active_ts_start, sp_active_ts_stop, short=True, between_sep=' to ')}{listened_songs_mbody}\n\nLast activity: {get_date_from_ts(sp_active_ts_stop)}\nInactivity timer: {display_time(SPOTIFY_INACTIVITY_CHECK)}{get_cur_ts(nl_ch + 'Timestamp: ')}"
                            m_body_html = f"<html><head></head><body>Last played: <b><a href=\"{sp_artist_url}\">{escape(sp_artist)}</a> - <a href=\"{sp_track_url}\">{escape(sp_track)}</a></b><br>Duration: {display_time(sp_track_duration)}{played_for_m_body_html}{playlist_m_body_html}<br>Album: <a href=\"{sp_album_url}\">{escape(sp_album)}</a>{context_m_body_html}<br><br>Apple Music URL: <a href=\"{apple_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>YouTube Music URL: <a href=\"{youtube_music_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br>Genius lyrics URL: <a href=\"{genius_search_url}\">{escape(sp_artist)} - {escape(sp_track)}</a><br><br>Friend got inactive after listening to music for <b>{calculate_timespan(int(sp_active_ts_stop), int(sp_active_ts_start))}</b><br>Friend played music from <b>{get_range_of_dates_from_tss(sp_active_ts_start, sp_active_ts_stop, short=True, between_sep='</b> to <b>')}</b>{listened_songs_mbody_html}<br><br>Last activity: <b>{get_date_from_ts(sp_active_ts_stop)}</b><br>Inactivity timer: {display_time(SPOTIFY_INACTIVITY_CHECK)}{get_cur_ts('<br>Timestamp: ')}</body></html>"
                            print(f"Sending email notification to {RECEIVER_EMAIL}")
                            send_email(m_subject, m_body, m_body_html, SMTP_SSL)
                            email_sent = True
                        sp_active_ts_start_old = sp_active_ts_start
                        sp_active_ts_start = 0
                        listened_songs_old = listened_songs
                        skipped_songs_old = skipped_songs
                        looped_songs_old = looped_songs
                        listened_songs = 0
                        looped_songs = 0
                        skipped_songs = 0
                        song_on_loop = 0
                        print_cur_ts("\nTimestamp:\t\t\t")

                    if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER:
                        print_cur_ts("Liveness check, timestamp:\t")
                        alive_counter = 0

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
                else:
                    print(f"User '{user_uri_id}' not found - make sure your friend is followed and has activity sharing enabled. Retrying in {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)} intervals")
                print_cur_ts("Timestamp:\t\t\t")
                user_not_found = True
            time.sleep(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)
            continue


def main():
    global CLI_CONFIG_PATH, DOTENV_FILE, LIVENESS_CHECK_COUNTER, LOGIN_REQUEST_BODY_FILE, CLIENTTOKEN_REQUEST_BODY_FILE, REFRESH_TOKEN, LOGIN_URL, USER_AGENT, DEVICE_ID, SYSTEM_ID, USER_URI_ID, SP_DC_COOKIE, CSV_FILE, MONITOR_LIST_FILE, FILE_SUFFIX, DISABLE_LOGGING, SP_LOGFILE, ACTIVE_NOTIFICATION, INACTIVE_NOTIFICATION, TRACK_NOTIFICATION, SONG_NOTIFICATION, SONG_ON_LOOP_NOTIFICATION, ERROR_NOTIFICATION, SPOTIFY_CHECK_INTERVAL, SPOTIFY_INACTIVITY_CHECK, SPOTIFY_ERROR_INTERVAL, SPOTIFY_DISAPPEARED_CHECK_INTERVAL, TRACK_SONGS, SMTP_PASSWORD, stdout_bck, APP_VERSION, CPU_ARCH, OS_BUILD, PLATFORM, OS_MAJOR, OS_MINOR, CLIENT_MODEL, TOKEN_SOURCE, ALARM_TIMEOUT, pyotp, USER_AGENT

    if "--generate-config" in sys.argv:
        print(CONFIG_BLOCK.strip("\n"))
        sys.exit(0)

    if "--version" in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    clear_screen(CLEAR_SCREEN)

    print(f"Spotify Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser(
        prog="spotify_monitor",
        description=("Monitor a Spotify friend's activity and send customizable email alerts [ https://github.com/misiektoja/spotify_monitor/ ]"), formatter_class=argparse.RawTextHelpFormatter
    )

    # Positional
    parser.add_argument(
        "user_id",
        nargs="?",
        metavar="SPOTIFY_USER_URI_ID",
        help="Spotify user URI ID",
        type=str
    )

    # Version, just to list in help, it is handled earlier
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{VERSION}"
    )

    # Configuration & dotenv files
    conf = parser.add_argument_group("Configuration & dotenv files")
    conf.add_argument(
        "--config-file",
        dest="config_file",
        metavar="PATH",
        help="Location of the optional config file",
    )
    conf.add_argument(
        "--generate-config",
        action="store_true",
        help="Print default config template and exit",
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
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
    listing.add_argument(
        "-v", "--show-user-info",
        dest="show_user_info",
        action="store_true",
        help="Get basic information about access token owner"
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

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = find_config_file(CLI_CONFIG_PATH)

    if not cfg_path and CLI_CONFIG_PATH:
        print(f"* Error: Config file '{CLI_CONFIG_PATH}' does not exist")
        sys.exit(1)

    if cfg_path:
        try:
            with open(cfg_path, "r") as cf:
                exec(cf.read(), globals())
        except Exception as e:
            print(f"* Error loading config file '{cfg_path}': {e}")
            sys.exit(1)

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import load_dotenv, find_dotenv

            if DOTENV_FILE:
                env_path = DOTENV_FILE
                if not os.path.isfile(env_path):
                    print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                else:
                    load_dotenv(env_path, override=True)
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_dotenv(env_path, override=True)
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                print(f"* Warning: Cannot load dotenv file '{env_path}' because 'python-dotenv' is not installed\n\nTo install it, run:\n    pip install python-dotenv\n\nOnce installed, re-run this tool\n")

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
        try:
            import pyotp
        except ModuleNotFoundError:
            raise SystemExit("Error: Couldn't find the pyotp library !\n\nTo install it, run:\n    pip install pyotp\n\nOnce installed, re-run this tool")

    if args.user_agent:
        USER_AGENT = args.user_agent

    if not USER_AGENT:
        if TOKEN_SOURCE == "client":
            USER_AGENT = get_random_spotify_user_agent()
        else:
            USER_AGENT = get_random_user_agent()

    if not check_internet():
        sys.exit(1)

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
                    print(f"* Error: Protobuf file ({LOGIN_REQUEST_BODY_FILE}) cannot be processed: {e}")
                    sys.exit(1)
                else:
                    if not args.user_id and not args.list_friends and not args.show_user_info and login_request_body_file_param:
                        print(f"* Login data correctly read from Protobuf file ({LOGIN_REQUEST_BODY_FILE}):")
                        print(" - Device ID:\t\t", DEVICE_ID)
                        print(" - System ID:\t\t", SYSTEM_ID)
                        print(" - User URI ID:\t\t", USER_URI_ID)
                        print(" - Refresh Token:\t", REFRESH_TOKEN, "\n")
                        sys.exit(0)
            else:
                print(f"* Error: Protobuf file ({LOGIN_REQUEST_BODY_FILE}) does not exist")
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
            print("* Error:", "; ".join(bad))
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
                    print(f"* Error: Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}) cannot be processed: {e}")
                    sys.exit(1)
                else:
                    if not args.user_id and not args.list_friends and not args.show_user_info and clienttoken_request_body_file_param:
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
                print(f"* Error: Protobuf file ({CLIENTTOKEN_REQUEST_BODY_FILE}) does not exist")
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
            print("* Error: SP_DC_COOKIE (-u / --spotify_dc_cookie) value is empty or incorrect")
            sys.exit(1)

    if args.show_user_info:
        print("* Getting basic information about access token owner ...\n")
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            user_info = spotify_get_current_user(sp_accessToken)

            if user_info:
                print(f"Token fetched via {TOKEN_SOURCE} belongs to:\n")

                print(f"Username:\t\t{user_info.get('display_name', '')}")
                print(f"User URI ID:\t\t{user_info.get('uri', '').split('spotify:user:', 1)[1]}")
                print(f"User URL:\t\t{user_info.get('spotify_url', '')}")
                print(f"User e-mail:\t\t{user_info.get('email', '')}")
                print(f"User country:\t\t{user_info.get('country', '')}")
                print(f"Is Premium?:\t\t{user_info.get('is_premium', '')}")
            else:
                print("Failed to retrieve user info.")

            print("─" * HORIZONTAL_LINE)
        except Exception as e:
            print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if args.list_friends:
        print("* Listing Spotify friends ...\n")
        try:
            if TOKEN_SOURCE == "client":
                sp_accessToken = spotify_get_access_token_from_client_auto(DEVICE_ID, SYSTEM_ID, USER_URI_ID, REFRESH_TOKEN)
            else:
                sp_accessToken = spotify_get_access_token_from_sp_dc(SP_DC_COOKIE)
            user_info = spotify_get_current_user(sp_accessToken)
            if user_info:
                print(f"Token belongs to:\t\t{user_info.get('display_name', '')} (via {TOKEN_SOURCE})\n\t\t\t\t[ {user_info.get('spotify_url')} ]")
            sp_friends = spotify_get_friends_json(sp_accessToken)
            spotify_list_friends(sp_friends)
            print("─" * HORIZONTAL_LINE)
        except Exception as e:
            print(f"* Error: {e}")
            sys.exit(1)
        sys.exit(0)

    if not args.user_id:
        print("* Error: SPOTIFY_USER_URI_ID argument is required !")
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
            print(f"* Error: File with monitored Spotify tracks cannot be opened: {e}")
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
            print(f"* Error: CSV file cannot be opened for writing: {e}")
            sys.exit(1)

    if args.file_suffix:
        FILE_SUFFIX = str(args.file_suffix)
    else:
        if not FILE_SUFFIX:
            FILE_SUFFIX = str(args.user_id)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    if not DISABLE_LOGGING:
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

    if args.track_in_spotify is True:
        TRACK_SONGS = True

    if SMTP_HOST.startswith("your_smtp_server_"):
        ACTIVE_NOTIFICATION = False
        INACTIVE_NOTIFICATION = False
        TRACK_NOTIFICATION = False
        SONG_NOTIFICATION = False
        SONG_ON_LOOP_NOTIFICATION = False
        ERROR_NOTIFICATION = False

    print(f"* Spotify polling intervals:\t[check: {display_time(SPOTIFY_CHECK_INTERVAL)}] [inactivity: {display_time(SPOTIFY_INACTIVITY_CHECK)}]\n\t\t\t\t[disappeared: {display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)}] [error: {display_time(SPOTIFY_ERROR_INTERVAL)}]")
    print(f"* Email notifications:\t\t[active = {ACTIVE_NOTIFICATION}] [inactive = {INACTIVE_NOTIFICATION}] [tracked = {TRACK_NOTIFICATION}]\n*\t\t\t\t[songs on loop = {SONG_ON_LOOP_NOTIFICATION}] [every song = {SONG_NOTIFICATION}] [errors = {ERROR_NOTIFICATION}]")
    print(f"* Token source:\t\t\t{TOKEN_SOURCE}")
    print(f"* Track listened songs:\t\t{TRACK_SONGS}")
    # print(f"* User agent:\t\t\t{USER_AGENT}")
    print(f"* Liveness check:\t\t{bool(LIVENESS_CHECK_INTERVAL)}" + (f" ({display_time(LIVENESS_CHECK_INTERVAL)})" if LIVENESS_CHECK_INTERVAL else ""))
    print(f"* CSV logging enabled:\t\t{bool(CSV_FILE)}" + (f" ({CSV_FILE})" if CSV_FILE else ""))
    print(f"* Alert on monitored tracks:\t{bool(MONITOR_LIST_FILE)}" + (f" ({MONITOR_LIST_FILE})" if MONITOR_LIST_FILE else ""))
    print(f"* Output logging enabled:\t{not DISABLE_LOGGING}" + (f" ({FINAL_LOG_PATH})" if not DISABLE_LOGGING else ""))
    print(f"* Configuration file:\t\t{cfg_path}")
    print(f"* Dotenv file:\t\t\t{env_path or 'None'}\n")

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_song_notifications_signal_handler)
        signal.signal(signal.SIGCONT, toggle_track_notifications_signal_handler)
        signal.signal(signal.SIGPIPE, toggle_songs_on_loop_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_inactivity_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_inactivity_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    spotify_monitor_friend_uri(args.user_id, sp_tracks, CSV_FILE)

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()
