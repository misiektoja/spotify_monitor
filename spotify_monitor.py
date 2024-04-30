#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.1

Script implementing real-time monitoring of Spotify friends music activity:
https://github.com/misiektoja/spotify_monitor/

Python pip3 requirements:

python-dateutil
requests
urllib3
"""

VERSION=1.1

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Log in to Spotify web client (https://open.spotify.com/) and put the value of sp_dc cookie below
# Newly generated Spotify's sp_dc cookie should be valid for 1 year
# You can use Cookie-Editor by cgagnier to get it easily (available for all major web browsers): https://cookie-editor.com/
SP_DC_COOKIE = "your_sp_dc_cookie_value"

# Type Spotify ID of the "finishing" track to play when user gets offline, only needed for track_songs functionality; 
# leave empty to simply pause
#SP_USER_GOT_OFFLINE_TRACK_ID="5wCjNjnugSUqGDBrmQhn0e"
SP_USER_GOT_OFFLINE_TRACK_ID=""

# Delay after which the above track gets paused, type 0 to play infinitely until user pauses manually; in seconds
SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE=5 # 5 seconds

# How often do we perform checks for user activity; in seconds
SPOTIFY_CHECK_INTERVAL=30 # 30 seconds

# After which time do we consider user as inactive (after last activity); in seconds
# Keep in mind if the user listens to songs longer than below timer then the tool will mark the user as inactive
SPOTIFY_INACTIVITY_CHECK=660 # 11 mins

# How many consecutive plays of the same song is considered as being on loop
SONG_ON_LOOP_VALUE=3

# When do we consider the song as being skipped; fraction 
SKIPPED_SONG_THRESHOLD=0.6 # song is treated as skipped if played for <=60% of track duration

# When the tool is started what is the time from last activity to consider the user as being active; in seconds
# Might be the same value as SPOTIFY_INACTIVITY_CHECK
SPOTIFY_ACTIVITY_CHECK=360 # 6 mins

# Sometimes the monitored Spotify user disappears from the list of recently active friends/buddies; it happens on few occasions:
#   - you unfollowed the monitored user
#   - issue with Spotify services
#   - Spotify user listens on private mode and sometimes the Spotify client messes some things up
#   - Spotify user was inactive for more than a week
# In such case we will continuously check for the user to reappear using the time interval below; in seconds
SPOTIFY_DISAPPEARED_CHECK_INTERVAL=120 # 2 mins

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL=21600 # 6 hours

# Default value for network-related timeouts in functions + alarm signal handler; in seconds
FUNCTION_TIMEOUT=15

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL='http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT=5

# SMTP settings for sending email notifications
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
#SMTP_HOST = "your_smtp_server_plaintext"
#SMTP_PORT = 25
#SMTP_USER = "your_smtp_user"
#SMTP_PASSWORD = "your_smtp_password"
#SMTP_SSL = False
#SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# Strings removed from track names for generating proper Genius search URLs
re_search_str=r'remaster|extended|original mix|remix|original soundtrack|radio( |-)edit|\(feat\.|( \(.*version\))|( - .*version)'
re_replace_str=r'( - (\d*)( )*remaster$)|( - (\d*)( )*remastered( version)*( \d*)*.*$)|( \((\d*)( )*remaster\)$)|( - (\d+) - remaster$)|( - extended$)|( - extended mix$)|( - (.*); extended mix$)|( - extended version$)|( - (.*) remix$)|( - remix$)|( - remixed by .*$)|( - original mix$)|( - .*original soundtrack$)|( - .*radio( |-)edit$)|( \(feat\. .*\)$)|( \(\d+.*Remaster.*\)$)|( \(.*Version\))|( - .*version)'

# The name of the .log file; the tool by default will output its messages to spotify_monitor_userid.log file
sp_logfile="spotify_monitor"

# Value used by signal handlers increasing/decreasing the inactivity check (SPOTIFY_INACTIVITY_CHECK); in seconds
SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE=30 # 30 seconds

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/SPOTIFY_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Artist', 'Track', 'Playlist', 'Album', 'Last activity']
active_notification=False
inactive_notification=False
song_notification=False
track_notification=False
song_on_loop_notification=False

import sys
import time
import string
import json
import os
from datetime import datetime
from dateutil import relativedelta
import calendar
import requests as req
import signal
import smtplib, ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import traceback
import argparse
import csv
import urllib
import subprocess
import platform
import re

# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1)

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

# Function to check internet connectivity
def check_internet():
    url=CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print("No connectivity, please check your network -", e)
        sys.exit(1)
    return False

# Function to convert absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952), # approximation
        ('months', 2629746), # approximation
        ('weeks', 604800),  # 60 * 60 * 24 * 7
        ('days', 86400),    # 60 * 60 * 24
        ('hours', 3600),    # 60 * 60
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
                result.append("{} {}".format(value, name))
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals=['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1=timestamp1
    ts2=timestamp2

    if type(timestamp1) is int:
        dt1=datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is datetime:
        dt1=timestamp1
        ts1=int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2=datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is datetime:
        dt2=timestamp2
        ts2=int(round(dt2.timestamp()))
    else:
        return ""

    if ts1>=ts2:
        ts_diff=ts1-ts2
    else:
        ts_diff=ts2-ts1
        dt1, dt2 = dt2, dt1

    if ts_diff>0:
        date_diff=relativedelta.relativedelta(dt1, dt2)
        years=date_diff.years
        months=date_diff.months
        weeks=date_diff.weeks
        if not show_weeks:
            weeks=0
        days=date_diff.days
        if weeks > 0:
            days=days-(weeks*7)
        hours=date_diff.hours
        if (not show_hours and ts_diff>86400):
            hours=0
        minutes=date_diff.minutes
        if (not show_minutes and ts_diff>3600):
            minutes=0
        seconds=date_diff.seconds
        if (not show_seconds and ts_diff>60):
            seconds=0
        date_list=[years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval>0:
                name=intervals[index]
                if interval==1:
                    name = name.rstrip('s')
                result.append("{} {}".format(interval, name))
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'

# Function to send email notification
def send_email(subject,body,body_html,use_ssl):

    try:     
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST,SMTP_PORT)
        smtpObj.login(SMTP_USER,SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] =  Header(subject, 'utf-8')

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
        print("Error sending email -", e)
        return 1
    return 0

# Function to write CSV entry
def write_csv_entry(csv_file_name, timestamp, artist, track, playlist, album, last_activity_ts):
    try:
        csv_file=open(csv_file_name, 'a', newline='', buffering=1)
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Date': timestamp, 'Artist': artist, 'Track': track, 'Playlist': playlist, 'Album': album, 'Last activity': last_activity_ts})
        csv_file.close()
    except Exception as e:
        raise

# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (str(ts_str) + str(calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]) + ", " + str(datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")))

# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("-----------------------------------------------------------------------------------")

# Function to return the timestamp in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %Y, %H:%M:%S")))

# Function to return the timestamp in human readable format (short version); eg. Sun 21 Apr 15:08
def get_short_date_from_ts(ts):
    return (str(calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]) + " " + str(datetime.fromtimestamp(ts).strftime("%d %b %H:%M")))

# Function to return the timestamp in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts,show_seconds=False):
    if show_seconds:
        out_strf="%H:%M:%S"
    else:
        out_strf="%H:%M"
    return (str(datetime.fromtimestamp(ts).strftime(out_strf)))

# Function to return the range between two timestamps; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1,ts2,between_sep=" - ", short=False):
    ts1_strf=datetime.fromtimestamp(ts1).strftime("%Y%m%d")
    ts2_strf=datetime.fromtimestamp(ts2).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_hour_min_from_ts(ts2,show_seconds=True)
    else:
        if short:
            out_str=get_short_date_from_ts(ts1) + between_sep + get_short_date_from_ts(ts2)
        else:
            out_str=get_date_from_ts(ts1) + between_sep + get_date_from_ts(ts2)       
    return (str(out_str))

# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global active_notification
    global inactive_notification
    active_notification=not active_notification
    inactive_notification=not inactive_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active = {active_notification}] [inactive = {inactive_notification}]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGUSR2 allowing to switch every song email notifications
def toggle_song_notifications_signal_handler(sig, frame):
    global song_notification
    song_notification=not song_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [every song = {song_notification}]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGCONT allowing to switch tracked songs email notifications
def toggle_track_notifications_signal_handler(sig, frame):
    global track_notification
    track_notification=not track_notification
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [tracked = " + str(track_notification) + "]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGTRAP allowing to increase inactivity check timer by SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE seconds
def increase_inactivity_check_signal_handler(sig, frame):
    global SPOTIFY_INACTIVITY_CHECK
    SPOTIFY_INACTIVITY_CHECK=SPOTIFY_INACTIVITY_CHECK+SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* Spotify timers: [inactivity: " + display_time(SPOTIFY_INACTIVITY_CHECK) + "]")
    print_cur_ts("Timestamp:\t\t")

# Signal handler for SIGABRT allowing to decrease inactivity check timer by SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE seconds
def decrease_inactivity_check_signal_handler(sig, frame):
    global SPOTIFY_INACTIVITY_CHECK
    if SPOTIFY_INACTIVITY_CHECK-SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE>0:
        SPOTIFY_INACTIVITY_CHECK=SPOTIFY_INACTIVITY_CHECK-SPOTIFY_INACTIVITY_CHECK_SIGNAL_VALUE
    sig_name=signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print("* Spotify timers: [inactivity: " + display_time(SPOTIFY_INACTIVITY_CHECK) + "]")
    print_cur_ts("Timestamp:\t\t")

# Function preparing Apple & Genius search URLs for specified track
def get_apple_genius_search_urls(artist,track):
    genius_search_string=str(artist) + " " + str(track)
    if re.search(re_search_str, genius_search_string, re.IGNORECASE):
        genius_search_string=re.sub(re_replace_str, '', genius_search_string, flags=re.IGNORECASE)        
    apple_search_string=urllib.parse.quote(str(artist) + " " + str(track))
    apple_search_url="https://music.apple.com/pl/search?term=" + apple_search_string
    genius_search_url="https://genius.com/search?q=" + urllib.parse.quote_plus(genius_search_string)
    return apple_search_url,genius_search_url

# Function getting Spotify access token based on provided sp_dc cookie value
def spotify_get_access_token(sp_dc):
    url = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"
    cookies = {"sp_dc": sp_dc}
    try:
        response = req.get(url, cookies=cookies, timeout=FUNCTION_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        print("spotify_get_access_token error -", e)
        if hasattr(e, 'response'):
            if hasattr(e.response, 'text'):
                print (e.response.text)
        raise
    return response.json()["accessToken"]

# Function getting list of Spotify friends
def spotify_get_friends_json(access_token):
    url = "https://guc-spclient.spotify.com/presence-view/v1/buddylist"
    headers = {"Authorization": "Bearer " + access_token}
    try:
        response = req.get(url, headers=headers, timeout=FUNCTION_TIMEOUT)
        response.raise_for_status()
        error_str=response.json().get("error")
        if error_str:
            raise ValueError(error_str) 
    except Exception as e:
        print("spotify_get_friends_json error -", e)
        if hasattr(e, 'response'):
            if hasattr(e.response, 'text'):
                print (e.response.text)
        raise
    return response.json()

# Function converting Spotify URI (e.g. spotify:user:username) to URL (e.g. https://open.spotify.com/user/username)
def spotify_convert_uri_to_url(uri):
    # add si parameter so link opens in native Spotify app after clicking
    si="?si=1"
#    si=""

    url=""
    if "spotify:user:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/user/" + s_id + si
    elif "spotify:artist:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/artist/" + s_id + si
    elif "spotify:track:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/track/" + s_id + si
    elif "spotify:album:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/album/" + s_id + si           
    elif "spotify:playlist:" in uri:
        s_id=uri.split(':', 2)[2]
        url="https://open.spotify.com/playlist/" + s_id + si

    return url

# Function printing the list of Spotify friends with the last listened track
def spotify_list_friends(friend_activity):
    #print(json.dumps(friend_activity))
    for friend in friend_activity["friends"]:
        sp_uri = friend["user"].get("uri").split("spotify:user:",1)[1]
        sp_username = friend["user"].get("name")
        sp_artist = friend["track"]["artist"].get("name")
        sp_album = friend["track"]["album"].get("name")
        sp_playlist = friend["track"]["context"].get("name")
        sp_track = friend["track"].get("name")
        sp_ts = friend.get("timestamp")
        sp_album_uri = friend["track"]["album"].get("uri")
        sp_playlist_uri = friend["track"]["context"].get("uri")
        sp_track_uri = friend["track"].get("uri")

        print("-----------------------------------------------------------------------------------")
        print("Username:\t\t" + sp_username)
        print("User URI ID:\t\t" + sp_uri)
        print("\nLast played:\t\t" + sp_artist + " - " + sp_track + "\n")
        if 'spotify:playlist:' in sp_playlist_uri:
            print("Playlist:\t\t" + sp_playlist)
        print("Album:\t\t\t" + sp_album)

        if 'spotify:album:' in sp_playlist_uri and sp_playlist!=sp_album:
            print("\nContext (Album):\t" + sp_playlist)

        if 'spotify:artist:' in sp_playlist_uri:
            print("\nContext (Artist):\t" + sp_playlist)

        print("\nTrack URL:\t\t" + spotify_convert_uri_to_url(sp_track_uri))
        if 'spotify:playlist:' in sp_playlist_uri:
            print("Playlist URL:\t\t" + spotify_convert_uri_to_url(sp_playlist_uri))
        print("Album URL:\t\t" + spotify_convert_uri_to_url(sp_album_uri))

        if 'spotify:album:' in sp_playlist_uri and sp_playlist!=sp_album:
            print("Context (Album) URL:\t" + spotify_convert_uri_to_url(sp_playlist_uri))

        if 'spotify:artist:' in sp_playlist_uri:
            print("Context (Artist) URL:\t" + spotify_convert_uri_to_url(sp_playlist_uri))

        apple_search_url,genius_search_url=get_apple_genius_search_urls(str(sp_artist),str(sp_track))

        print("Apple search URL:\t" + apple_search_url)
        print("Genius lyrics URL:\t" + genius_search_url)            

        print("\nLast activity:\t\t" + get_date_from_ts(float(str(sp_ts)[0:-3])) + " (" + calculate_timespan(int(time.time()),datetime.fromtimestamp(float(str(sp_ts)[0:-3]))) + " ago)")

# Function returning information for specific Spotify friend's user URI id
def spotify_get_friend_info(friend_activity,uri):
#    print(json.dumps(friend_activity))
    for friend in friend_activity["friends"]:
        sp_uri = friend["user"]["uri"].split("spotify:user:",1)[1]
        if sp_uri == uri:
            sp_username = friend["user"].get("name")
            sp_artist = friend["track"]["artist"].get("name")
            sp_album = friend["track"]["album"].get("name")
            sp_album_uri = friend["track"]["album"].get("uri")
            sp_playlist = friend["track"]["context"].get("name")
            sp_playlist_uri = friend["track"]["context"].get("uri")
            sp_track = friend["track"].get("name")
            sp_track_uri = friend["track"].get("uri")
            sp_ts = int(str(friend.get("timestamp"))[0:-3])
            return True, {"sp_uri": sp_uri, "sp_username": sp_username, "sp_artist": sp_artist, "sp_track": sp_track, "sp_track_uri": sp_track_uri, "sp_album": sp_album, "sp_album_uri": sp_album_uri, "sp_playlist": sp_playlist, "sp_playlist_uri": sp_playlist_uri, "sp_ts": sp_ts}
    return False, {}

# Function returning information for specific Spotify track URI
def spotify_get_track_info(access_token,track_uri):
    track_id=track_uri.split(':', 2)[2]
    url = "https://api.spotify.com/v1/tracks/" + track_id
    headers = {"Authorization": "Bearer " + access_token}
    # add si parameter so link opens in native Spotify app after clicking
    si="?si=1"

    try:
        response = req.get(url, headers=headers, timeout=FUNCTION_TIMEOUT)
        response.raise_for_status()
        json_response=response.json()
        sp_track_duration = int(json_response.get("duration_ms")/1000)
        sp_track_url = json_response["external_urls"].get("spotify") + si
        sp_track_name = json_response.get("name")
        sp_artist_url = json_response["artists"][0]["external_urls"].get("spotify") + si
        sp_artist_name = json_response["artists"][0].get("name")
        sp_album_url = json_response["album"]["external_urls"].get("spotify") + si
        sp_album_name = json_response["album"].get("name")
        return {"sp_track_duration": sp_track_duration, "sp_track_url": sp_track_url, "sp_artist_url": sp_artist_url, "sp_album_url": sp_album_url, "sp_track_name": sp_track_name, "sp_artist_name": sp_artist_name, "sp_album_name": sp_album_name}
    except Exception as e:
        print("spotify_get_track_info error -", e)
        if hasattr(e, 'response'):
            if hasattr(e.response, 'text'):
                print (e.response.text)
        raise

# Function returning information for specific Spotify playlist URI
def spotify_get_playlist_info(access_token,playlist_uri):
    playlist_id=playlist_uri.split(':', 2)[2]
    url = "https://api.spotify.com/v1/playlists/" + playlist_id + "?fields=name,owner,followers,external_urls"
    headers = {"Authorization": "Bearer " + access_token}
    # add si parameter so link opens in native Spotify app after clicking
    si="?si=1"

    try:
        response = req.get(url, headers=headers, timeout=FUNCTION_TIMEOUT)
        json_response=response.json()
        response.raise_for_status()
        sp_playlist_name = json_response.get("name")
        sp_playlist_owner = json_response["owner"].get("display_name")
        sp_playlist_owner_url = json_response["owner"]["external_urls"].get("spotify")
        sp_playlist_followers = int(json_response["followers"].get("total"))
        sp_playlist_url = json_response["external_urls"].get("spotify") + si
        return {"sp_playlist_name": sp_playlist_name, "sp_playlist_owner": sp_playlist_owner, "sp_playlist_owner_url": sp_playlist_owner_url, "sp_playlist_followers": sp_playlist_followers, "sp_playlist_url": sp_playlist_url}
    except Exception as e:
        print("spotify_get_playlist_info error -", e)
        if hasattr(e, 'response'):
            if hasattr(e.response, 'text'):
                print (e.response.text)
        raise

# Main function monitoring activity of the specified Spotify friend's user URI ID
def spotify_monitor_friend_uri(user_uri_id,tracks,error_notification,csv_file_name,csv_exists):

    sp_active_ts_start=0
    sp_active_ts_stop=0
    sp_active_ts_start_old=0
    user_not_found=False
    listened_songs=0
    listened_songs_old=0    
    looped_songs=0
    looped_songs_old=0    
    skipped_songs=0
    skipped_songs_old=0
    sp_artist_old=""
    sp_track_old=""
    sp_track_url_old=""
    song_on_loop=0

    try:
        if csv_file_name:
            csv_file=open(csv_file_name, 'a', newline='', buffering=1)
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print("* Error -", e)

    # Main loop
    while True:

        email_sent=False

        # Sometimes Spotify network functions halt even though we specified the timeout
        # To overcome this we use alarm signal functionality to kill it inevitably
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(FUNCTION_TIMEOUT)        
        try:
            sp_accessToken=spotify_get_access_token(SP_DC_COOKIE)
            sp_friends=spotify_get_friends_json(sp_accessToken)
            sp_found, sp_data = spotify_get_friend_info(sp_friends,user_uri_id)
            signal.alarm(0)
        except TimeoutException:
            signal.alarm(0)
            print("spotify_*() timeout, retrying in", display_time(FUNCTION_TIMEOUT))
            print_cur_ts("Timestamp:\t\t")
            time.sleep(FUNCTION_TIMEOUT)
            continue
        except Exception as e:
            signal.alarm(0)
            print("Retrying in " + str(display_time(SPOTIFY_CHECK_INTERVAL)) + ", error - " + str(e))
            if ('access token' in str(e)) or ('Unauthorized' in str(e)):
                print("* sp_dc might have expired!")
                if error_notification and not email_sent:
                    m_subject="spotify_monitor: sp_dc might have expired! (uri: " + str(user_uri_id) + ")"
                    m_body="sp_dc might have expired: " + str(e) + get_cur_ts("\n\nTimestamp: ")
                    m_body_html="<html><head></head><body>sp_dc might have expired: " + str(e) + get_cur_ts("<br><br>Timestamp: ") + "</body></html>"
                    print("Sending email notification to",RECEIVER_EMAIL)
                    send_email(m_subject,m_body, m_body_html, SMTP_SSL)
                    email_sent=True
            print_cur_ts("Timestamp:\t\t")
            time.sleep(SPOTIFY_CHECK_INTERVAL)
            continue

        playlist_m_body=""
        playlist_m_body_html=""
        played_for_m_body=""
        played_for_m_body_html=""         
        is_playlist=False
        
        # User is found in the Spotify's friend list just after starting the tool
        if sp_found:
            user_not_found=False
            print("* User found, starting monitoring ....")

            sp_track_uri = sp_data["sp_track_uri"]
            sp_album_uri = sp_data["sp_album_uri"]
            sp_playlist_uri = sp_data["sp_playlist_uri"]

            try:
                sp_track_data=spotify_get_track_info(sp_accessToken, sp_track_uri)
                if 'spotify:playlist:' in sp_playlist_uri:
                    is_playlist=True
                    sp_playlist_data=spotify_get_playlist_info(sp_accessToken, sp_playlist_uri)
                    if not sp_playlist_data:
                        is_playlist=False
                else:
                    is_playlist=False
            except Exception as e:
                print("Retrying in", display_time(SPOTIFY_CHECK_INTERVAL), ", error -", e)
                print_cur_ts("Timestamp:\t\t")
                time.sleep(SPOTIFY_CHECK_INTERVAL)
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

            sp_track_duration=sp_track_data["sp_track_duration"]
            sp_track_url=sp_track_data["sp_track_url"]
            sp_artist_url=sp_track_data["sp_artist_url"]
            sp_album_url=sp_track_data["sp_album_url"]

            if is_playlist:
                sp_playlist_url=sp_playlist_data.get("sp_playlist_url")
                playlist_m_body="\nPlaylist: " + sp_playlist
                playlist_m_body_html="<br>Playlist: <a href=\"" + sp_playlist_url + "\">" + sp_playlist + "</a>"

            print("\nUsername:\t\t" + sp_username)
            print("User URI ID:\t\t" + sp_data["sp_uri"])
            print("\nLast played:\t\t" + sp_artist + " - " + sp_track)
            print("Duration:\t\t" + display_time(sp_track_duration) + "\n")
            if is_playlist:
                print("Playlist:\t\t" + sp_playlist)

            print("Album:\t\t\t" + sp_album)

            context_m_body=""
            context_m_body_html=""

            if 'spotify:album:' in sp_playlist_uri and sp_playlist!=sp_album:
                print("\nContext (Album):\t" + sp_playlist)
                context_m_body+="\nContext (Album): " + sp_playlist
                context_m_body_html+="<br>Context (Album): <a href=\"" + spotify_convert_uri_to_url(sp_playlist_uri) + "\">" + sp_playlist + "</a>"

            if 'spotify:artist:' in sp_playlist_uri:
                print("\nContext (Artist):\t" + sp_playlist)
                context_m_body+="\nContext (Artist): " + sp_playlist
                context_m_body_html+="<br>Context (Artist): <a href=\"" + spotify_convert_uri_to_url(sp_playlist_uri) + "\">" + sp_playlist + "</a>"

            print("\nTrack URL:\t\t" + sp_track_url)
            if is_playlist:
                print("Playlist URL:\t\t" + sp_playlist_url)
            print("Album URL:\t\t" + sp_album_url)

            if 'spotify:album:' in sp_playlist_uri and sp_playlist!=sp_album:
                print("Context (Album) URL:\t" + spotify_convert_uri_to_url(sp_playlist_uri))

            if 'spotify:artist:' in sp_playlist_uri:
                print("Context (Artist) URL:\t" + spotify_convert_uri_to_url(sp_playlist_uri))

            apple_search_url,genius_search_url=get_apple_genius_search_urls(str(sp_artist),str(sp_track))

            print("Apple search URL:\t" + apple_search_url)
            print("Genius lyrics URL:\t" + genius_search_url)     

            if not is_playlist:
                sp_playlist=""

            print("\nLast activity:\t\t" + get_date_from_ts(sp_ts))

            # Friend is currently active (listens to music)
            if (cur_ts-sp_ts) <= SPOTIFY_ACTIVITY_CHECK:
                sp_active_ts_start=sp_ts-sp_track_duration
                sp_active_ts_stop=0
                listened_songs=1
                song_on_loop=1
                print("\n*** Friend is currently ACTIVE !")

                if sp_track.upper() in map(str.upper, tracks) or sp_playlist.upper() in map(str.upper, tracks) or sp_album.upper() in map(str.upper, tracks): 
                    print("*** Track/playlist/album matched with the list!")

                try: 
                    if csv_file_name:
                        write_csv_entry(csv_file_name, datetime.fromtimestamp(int(cur_ts)), sp_artist, sp_track, sp_playlist, sp_album, datetime.fromtimestamp(int(sp_ts)))
                except Exception as e:
                    print("* Cannot write CSV entry -", e)

                if active_notification:                
                    m_subject="Spotify user " + sp_username + ": '" + sp_artist + " - " + sp_track + "'"
                    m_body="Last played: " + sp_artist + " - " + sp_track + "\nDuration: " + display_time(sp_track_duration) + playlist_m_body + "\nAlbum: " + sp_album + context_m_body + "\n\nApple search URL: " + apple_search_url + "\nGenius lyrics URL: " + genius_search_url + "\n\nLast activity: " + get_date_from_ts(sp_ts) + get_cur_ts("\nTimestamp: ")
                    m_body_html="<html><head></head><body>Last played: <b><a href=\"" + sp_artist_url + "\">" + sp_artist + "</a> - <a href=\"" + sp_track_url + "\">" + sp_track + "</a></b><br>Duration: " + display_time(sp_track_duration) + playlist_m_body_html + "<br>Album: <a href=\"" + sp_album_url + "\">" + sp_album + "</a>" + context_m_body_html + "<br><br>Apple search URL: <a href=\"" + apple_search_url + "\">" + str(sp_artist) + " - " + str(sp_track) + "</a>" + "<br>Genius lyrics URL: <a href=\"" + genius_search_url + "\">" + sp_artist + " - " + sp_track + "</a><br><br>Last activity: " + get_date_from_ts(sp_ts) + get_cur_ts("<br>Timestamp: ") + "</body></html>"                   
                    print("Sending email notification to",RECEIVER_EMAIL)
                    send_email(m_subject,m_body, m_body_html, SMTP_SSL)

                if track_songs:                                     
                    if platform.system() == 'Darwin':       # macOS
                        # subprocess.call(('open', sp_track_url))
                        script = 'tell app "Spotify" to play track "' + sp_track_uri + '"'
                        proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                        stdout, stderr = proc.communicate(script)
                    elif platform.system() == 'Windows':    # Windows
                        os.startfile(sp_track_url)
                    else:                                   # linux variants
                        subprocess.call(('xdg-open', sp_track_url))

            # Friend is currently offline (does not play music)
            else:
                sp_active_ts_stop=sp_ts
                print("\n*** Friend is OFFLINE for:", calculate_timespan(int(cur_ts),int(sp_ts)),"!")

            print("\nTracks/playlists/albums to monitor:", tracks)
            print_cur_ts("\nTimestamp:\t\t")

            sp_ts_old=sp_ts
            alive_counter=0 

            while True:
                email_sent = False
                while True:
                    # Sometimes Spotify network functions halt even though we specified the timeout
                    # To overcome this we use alarm signal functionality to kill it inevitably                    
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(FUNCTION_TIMEOUT)
                    try:
                        sp_accessToken=spotify_get_access_token(SP_DC_COOKIE)
                        sp_friends=spotify_get_friends_json(sp_accessToken)
                        sp_found, sp_data = spotify_get_friend_info(sp_friends,user_uri_id)                       
                        signal.alarm(0)
                        break
                    except TimeoutException:
                        signal.alarm(0)
                        print("spotify_*() timeout, retrying in", display_time(FUNCTION_TIMEOUT))
                        print_cur_ts("Timestamp:\t\t")
                        time.sleep(FUNCTION_TIMEOUT)           
                    except Exception as e:
                        signal.alarm(0)
                        print("Retrying in", display_time(SPOTIFY_CHECK_INTERVAL), ", error -", e)
                        if ('access token' in str(e)) or ('Unauthorized' in str(e)):
                            print("* sp_dc might have expired!")
                            if error_notification and not email_sent:
                                m_subject="spotify_monitor: sp_dc might have expired! (uri: " + str(user_uri_id) + ")"
                                m_body="sp_dc might have expired: " + str(e) + get_cur_ts("\n\nTimestamp: ")
                                m_body_html="<html><head></head><body>sp_dc might have expired: " + str(e) + get_cur_ts("<br><br>Timestamp: ") + "</body></html>"
                                print("Sending email notification to",RECEIVER_EMAIL)
                                send_email(m_subject,m_body, m_body_html, SMTP_SSL)
                                email_sent=True
                        print_cur_ts("Timestamp:\t\t")
                        time.sleep(SPOTIFY_CHECK_INTERVAL)

                if sp_found is False:
                    # User disappeared from the Spotify's friend list
                    if user_not_found is False:
                        print("Spotify user " + user_uri_id + " (" + sp_username + ") disappeared, retrying in " + display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL) + " intervals")
                        if error_notification:
                            m_subject="Spotify user " + str(user_uri_id) + " (" + str(sp_username) + ") disappeared!"
                            m_body="Spotify user " + str(user_uri_id) + " (" + str(sp_username) + ") disappeared, retrying in " + display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL) + " intervals" + get_cur_ts("\n\nTimestamp: ")
                            m_body_html="<html><head></head><body>Spotify user " + str(user_uri_id) + " (" + str(sp_username) + ") disappeared, retrying in " + display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL) + " intervals" + get_cur_ts("<br><br>Timestamp: ") + "</body></html>"
                            print("Sending email notification to",RECEIVER_EMAIL)
                            send_email(m_subject,m_body, m_body_html, SMTP_SSL)                      
                        print_cur_ts("Timestamp:\t\t")
                        user_not_found=True
                    time.sleep(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)
                    continue
                else:
                    # User reappeared in the Spotify's friend list
                    if user_not_found is True:
                        print("Spotify user " + user_uri_id + " (" + sp_username + ") appeared again!")
                        if error_notification:
                            m_subject="Spotify user " + str(user_uri_id) + " (" + str(sp_username) + ") appeared!"
                            m_body="Spotify user " + str(user_uri_id) + " appeared again!" + get_cur_ts("\n\nTimestamp: ")
                            m_body_html="<html><head></head><body>Spotify user " + str(user_uri_id) + " (" + str(sp_username) + ") appeared again!" + get_cur_ts("<br><br>Timestamp: ") + "</body></html>"
                            print("Sending email notification to",RECEIVER_EMAIL)
                            send_email(m_subject,m_body, m_body_html, SMTP_SSL)                             
                        print_cur_ts("Timestamp:\t\t")

                user_not_found=False
                sp_ts = sp_data["sp_ts"]
                cur_ts = int(time.time())
           
                # Track has changed
                if sp_ts != sp_ts_old:
                    sp_artist_old=sp_artist
                    sp_track_old=sp_track
                    sp_track_url_old=sp_track_url
                    alive_counter = 0
                    sp_playlist = sp_data["sp_playlist"]               
                    sp_track_uri = sp_data["sp_track_uri"]
                    sp_album_uri = sp_data["sp_album_uri"]
                    sp_playlist_uri = sp_data["sp_playlist_uri"]
                    try:
                        sp_track_data=spotify_get_track_info(sp_accessToken, sp_track_uri)
                        if 'spotify:playlist:' in sp_playlist_uri:
                            is_playlist=True
                            sp_playlist_data=spotify_get_playlist_info(sp_accessToken, sp_playlist_uri)
                            if not sp_playlist_data:
                                is_playlist=False
                        else:
                           is_playlist=False
                    except Exception as e:
                        print("Retrying in", display_time(SPOTIFY_CHECK_INTERVAL), ", error -", e)
                        print_cur_ts("Timestamp:\t\t")
                        time.sleep(SPOTIFY_CHECK_INTERVAL)
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

                    sp_track_duration=sp_track_data["sp_track_duration"]
                    sp_track_url=sp_track_data["sp_track_url"]
                    sp_artist_url=sp_track_data["sp_artist_url"]
                    sp_album_url=sp_track_data["sp_album_url"]

                    # If tracking functionality is enabled then play the current song via Spotify client
                    if track_songs:                                     
                        if platform.system() == 'Darwin':       # macOS
                            # subprocess.call(('open', sp_track_url))
                            script = 'tell app "Spotify" to play track "' + sp_track_uri + '"'
                            proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                            stdout, stderr = proc.communicate(script)
                        elif platform.system() == 'Windows':    # Windows
                            os.startfile(sp_track_url)
                        else:                                   # linux variants
                            subprocess.call(('xdg-open', sp_track_url))

                    if is_playlist:
                        sp_playlist_url=sp_playlist_data.get("sp_playlist_url")
                        playlist_m_body="\nPlaylist: " + sp_playlist
                        playlist_m_body_html="<br>Playlist: <a href=\"" + sp_playlist_url + "\">" + sp_playlist + "</a>"
                    else:
                        playlist_m_body=""
                        playlist_m_body_html=""

                    if sp_artist == sp_artist_old and sp_track == sp_track_old:
                        song_on_loop+=1
                        if song_on_loop==SONG_ON_LOOP_VALUE:
                            looped_songs+=1                   
                    else:
                        song_on_loop=1                        

                    print("Spotify user:\t\t" + sp_username)
                    print("\nLast played:\t\t" + sp_artist + " - " + sp_track)
                    print("Duration:\t\t" + display_time(sp_track_duration))

                    listened_songs+=1

                    if (sp_ts-sp_ts_old) < (sp_track_duration-1):
                        played_for_time=sp_ts-sp_ts_old
                        listened_percentage=(played_for_time) / (sp_track_duration-1)
                        played_for=display_time(played_for_time)
                        if listened_percentage <= SKIPPED_SONG_THRESHOLD:
                            played_for+=" - SKIPPED (" + str(int(listened_percentage*100)) + "%)"
                            skipped_songs+=1
                        else:
                            played_for+=" (" + str(int(listened_percentage*100)) + "%)"
                        print("Played for:\t\t" + played_for)
                        played_for_m_body="\nPlayed for: " + played_for
                        played_for_m_body_html="<br>Played for: " + played_for
                    else:
                        played_for_m_body=""
                        played_for_m_body_html=""                      

                    if is_playlist:
                        print("Playlist:\t\t" + sp_playlist)

                    print("Album:\t\t\t" + sp_album)

                    context_m_body=""
                    context_m_body_html=""

                    if 'spotify:album:' in sp_playlist_uri and sp_playlist!=sp_album:
                        print("\nContext (Album):\t" + sp_playlist)
                        context_m_body+="\nContext (Album): " + sp_playlist
                        context_m_body_html+="<br>Context (Album): <a href=\"" + spotify_convert_uri_to_url(sp_playlist_uri) + "\">" + sp_playlist + "</a>"

                    if 'spotify:artist:' in sp_playlist_uri:
                        print("\nContext (Artist):\t" + sp_playlist)
                        context_m_body+="\nContext (Artist): " + sp_playlist
                        context_m_body_html+="<br>Context (Artist): <a href=\"" + spotify_convert_uri_to_url(sp_playlist_uri) + "\">" + sp_playlist + "</a>"

                    print("Last activity:\t\t" + get_date_from_ts(sp_ts))

                    print("\nTrack URL:\t\t" + sp_track_url)

                    if is_playlist:
                        print("Playlist URL:\t\t" + sp_playlist_url)
                    print("Album URL:\t\t" + sp_album_url)

                    if 'spotify:album:' in sp_playlist_uri and sp_playlist!=sp_album:
                        print("Context (Album) URL:\t" + spotify_convert_uri_to_url(sp_playlist_uri))

                    if 'spotify:artist:' in sp_playlist_uri:
                        print("Context (Artist) URL:\t" + spotify_convert_uri_to_url(sp_playlist_uri))

                    apple_search_url,genius_search_url=get_apple_genius_search_urls(str(sp_artist),str(sp_track))

                    print("Apple search URL:\t" + apple_search_url)
                    print("Genius lyrics URL:\t" + genius_search_url)                       

                    if not is_playlist:
                        sp_playlist=""

                    if song_on_loop==SONG_ON_LOOP_VALUE:
                        print("---------------------------------------------------------------------------------------------------------")                        
                        print(f"User plays song on LOOP ({song_on_loop} times)")
                        print("---------------------------------------------------------------------------------------------------------")   

                    # Friend is active
                    if (cur_ts-sp_ts_old) > (SPOTIFY_INACTIVITY_CHECK+SPOTIFY_CHECK_INTERVAL):
                        m_subject="Spotify user " + sp_username + " is active: '" + sp_artist + " - " + sp_track + "'"
                        friend_active_m_body="\n\nFriend got active"
                        friend_active_m_body_html="<br><br>Friend got active"

                        sp_active_ts_start=sp_ts-sp_track_duration

                        listened_songs=1
                        skipped_songs=0
                        looped_songs=0

                        # Friend got active after being offline, sp_active_ts_stop>0 (user got offline earlier)
                        if sp_active_ts_stop > 0:

                            print("\n*** Friend got ACTIVE after being offline for " + calculate_timespan(int(sp_active_ts_start),int(sp_active_ts_stop)) + " (" + get_date_from_ts(sp_active_ts_stop) + ")")
                            m_subject="Spotify user " + sp_username + " is active: '" + sp_artist + " - " + sp_track + "' (after " + calculate_timespan(int(sp_active_ts_start),int(sp_active_ts_stop),show_seconds=False) + " - " + get_short_date_from_ts(sp_active_ts_stop) + ")"
                            friend_active_m_body="\n\nFriend got active after being offline for " + calculate_timespan(int(sp_active_ts_start),int(sp_active_ts_stop)) + "\nLast activity (before getting offline): " + get_date_from_ts(sp_active_ts_stop)
                            friend_active_m_body_html="<br><br>Friend got active after being offline for <b>" + calculate_timespan(int(sp_active_ts_start),int(sp_active_ts_stop)) + "</b><br>Last activity (before getting offline): <b>" + get_date_from_ts(sp_active_ts_stop) + "</b>"
                            if sp_active_ts_start-sp_active_ts_stop<30:
                                listened_songs=listened_songs_old
                                skipped_songs=skipped_songs_old
                                looped_songs=looped_songs_old
                                print("*** Inactivity timer (" + display_time(SPOTIFY_INACTIVITY_CHECK) + ") value might be too low, readjusting session start back to " + get_short_date_from_ts(sp_active_ts_start_old))
                                friend_active_m_body+="\nInactivity timer (" + display_time(SPOTIFY_INACTIVITY_CHECK) + ") value might be too low, readjusting session start back to " + get_short_date_from_ts(sp_active_ts_start_old)
                                friend_active_m_body_html+="\n<br>Inactivity timer (<b>" + display_time(SPOTIFY_INACTIVITY_CHECK) + "</b>) value might be <b>too low</b>, readjusting session start back to <b>" + get_short_date_from_ts(sp_active_ts_start_old) + "</b>"
                                if sp_active_ts_start_old>0:
                                    sp_active_ts_start=sp_active_ts_start_old
                            sp_active_ts_stop=0
                        
                        # Friend got active after being offline, sp_active_ts_stop==0 (user did not get offline earlier, for example is active right after starting the tool)
                        else:
                            print("\n*** Friend just got ACTIVE!")

                        m_body="Last played: " + sp_artist + " - " + sp_track + "\nDuration: " + display_time(sp_track_duration) + played_for_m_body + playlist_m_body + "\nAlbum: " + sp_album + context_m_body + "\n\nApple search URL: " + apple_search_url + "\nGenius lyrics URL: " + genius_search_url + friend_active_m_body + "\n\nLast activity: " + get_date_from_ts(sp_ts) + get_cur_ts("\nTimestamp: ")
                        m_body_html="<html><head></head><body>Last played: <b><a href=\"" + sp_artist_url + "\">" + sp_artist + "</a> - <a href=\"" + sp_track_url + "\">" + sp_track + "</a></b><br>Duration: " + display_time(sp_track_duration) + played_for_m_body_html + playlist_m_body_html + "<br>Album: <a href=\"" + sp_album_url + "\">" + sp_album + "</a>" + context_m_body_html + "<br><br>Apple search URL: <a href=\"" + apple_search_url + "\">" + str(sp_artist) + " - " + str(sp_track) + "</a>" + "<br>Genius lyrics URL: <a href=\"" + genius_search_url + "\">" + sp_artist + " - " + sp_track + "</a>" + friend_active_m_body_html + "<br><br>Last activity: " + get_date_from_ts(sp_ts) + get_cur_ts("<br>Timestamp: ") + "</body></html>"

                        if active_notification:
                            print("Sending email notification to",RECEIVER_EMAIL)
                            send_email(m_subject,m_body, m_body_html, SMTP_SSL)
                            email_sent = True                          

                    on_the_list=False
                    if sp_track.upper() in map(str.upper, tracks) or sp_playlist.upper() in map(str.upper, tracks) or sp_album.upper() in map(str.upper, tracks):
                        print("\n*** Track/playlist/album matched with the list!")
                        on_the_list=True

                    if (track_notification and on_the_list and not email_sent) or (song_notification and not email_sent):
                        m_subject="Spotify user " + sp_username + ": '" + sp_artist + " - " + sp_track + "'"
                        m_body="Last played: " + sp_artist + " - " + sp_track + "\nDuration: " + display_time(sp_track_duration) + played_for_m_body + playlist_m_body + "\nAlbum: " + sp_album + context_m_body + "\n\nApple search URL: " + apple_search_url + "\nGenius lyrics URL: " + genius_search_url + "\n\nLast activity: " + get_date_from_ts(sp_ts) + get_cur_ts("\nTimestamp: ")
                        m_body_html="<html><head></head><body>Last played: <b><a href=\"" + sp_artist_url + "\">" + sp_artist + "</a> - <a href=\"" + sp_track_url + "\">" + sp_track + "</a></b><br>Duration: " + display_time(sp_track_duration) + played_for_m_body_html + playlist_m_body_html + "<br>Album: <a href=\"" + sp_album_url + "\">" + sp_album + "</a>" + context_m_body_html + "<br><br>Apple search URL: <a href=\"" + apple_search_url + "\">" + str(sp_artist) + " - " + str(sp_track) + "</a>" + "<br>Genius lyrics URL: <a href=\"" + genius_search_url + "\">" + sp_artist + " - " + sp_track + "</a>" + "<br><br>Last activity: " + get_date_from_ts(sp_ts) + get_cur_ts("<br>Timestamp: ") + "</body></html>"  
                        print("Sending email notification to",RECEIVER_EMAIL)
                        send_email(m_subject,m_body, m_body_html, SMTP_SSL)
                        email_sent = True                     

                    if song_on_loop==SONG_ON_LOOP_VALUE and song_on_loop_notification:
                            m_subject="Spotify user " + sp_username + " plays song on loop: '" + sp_artist + " - " + sp_track + "'"
                            m_body="Last played: " + sp_artist + " - " + sp_track + "\nDuration: " + display_time(sp_track_duration) + played_for_m_body + playlist_m_body + "\nAlbum: " + sp_album + context_m_body + "\n\nApple search URL: " + apple_search_url + "\nGenius lyrics URL: " + genius_search_url + "\n\nUser plays song on LOOP (" + str(song_on_loop) + " times)" + "\n\nLast activity: " + get_date_from_ts(sp_ts) + get_cur_ts("\nTimestamp: ")
                            m_body_html="<html><head></head><body>Last played: <b><a href=\"" + sp_artist_url + "\">" + sp_artist + "</a> - <a href=\"" + sp_track_url + "\">" + sp_track + "</a></b><br>Duration: " + display_time(sp_track_duration) + played_for_m_body_html + playlist_m_body_html + "<br>Album: <a href=\"" + sp_album_url + "\">" + sp_album + "</a>" + context_m_body_html + "<br><br>Apple search URL: <a href=\"" + apple_search_url + "\">" + str(sp_artist) + " - " + str(sp_track) + "</a>" + "<br>Genius lyrics URL: <a href=\"" + genius_search_url + "\">" + sp_artist + " - " + sp_track + "</a>" + "<br><br>User plays song on LOOP (<b>" + str(song_on_loop) + "</b> times)" + "<br><br>Last activity: " + get_date_from_ts(sp_ts) + get_cur_ts("<br>Timestamp: ") + "</body></html>"
                            if not email_sent:
                                print("Sending email notification to",RECEIVER_EMAIL)
                            send_email(m_subject,m_body,m_body_html,SMTP_SSL)    

                    try: 
                        if csv_file_name:
                            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(cur_ts)), sp_artist, sp_track, sp_playlist, sp_album, datetime.fromtimestamp(int(sp_ts)))
                    except Exception as e:
                        print("* Cannot write CSV entry -", e)

                    print_cur_ts("\nTimestamp:\t\t")
                    sp_ts_old=sp_ts
                
                # Track has not changed
                else:
                    alive_counter+=1
                    
                    # Friend got inactive
                    if (cur_ts-sp_ts) > SPOTIFY_INACTIVITY_CHECK and sp_active_ts_start > 0:
                        sp_active_ts_stop=sp_ts
                        print("*** Friend got INACTIVE after listening to music for",calculate_timespan(int(sp_active_ts_stop),int(sp_active_ts_start)))
                        print("*** Friend played music from " + get_range_of_dates_from_tss(sp_active_ts_start,sp_active_ts_stop,short=True,between_sep=" to "))

                        listened_songs_text="*** User played " + str(listened_songs) + " songs"
                        listened_songs_mbody="\n\nUser played " + str(listened_songs) + " songs"
                        listened_songs_mbody_html="<br><br>User played <b>" + str(listened_songs) + "</b> songs"

                        if skipped_songs>0:
                            skipped_songs_text=", skipped " + str(skipped_songs) + " songs (" + str(int((skipped_songs/listened_songs)*100)) + "%)"
                            listened_songs_text+=skipped_songs_text
                            listened_songs_mbody+=skipped_songs_text
                            listened_songs_mbody_html+=", skipped <b>" + str(skipped_songs) + "</b> songs <b>(" + str(int((skipped_songs/listened_songs)*100)) + "%)</b>"

                        if looped_songs>0:
                            looped_songs_text="\n*** User played " + str(looped_songs) + " songs on loop"
                            looped_songs_mbody="\nUser played " + str(looped_songs) + " songs on loop"
                            looped_songs_mbody_html="<br>User played <b>" + str(looped_songs) + "</b> songs on loop"                        
                            listened_songs_text+=looped_songs_text
                            listened_songs_mbody+=looped_songs_mbody
                            listened_songs_mbody_html+=looped_songs_mbody_html

                        print(listened_songs_text)

                        print("*** Last activity:\t" + get_date_from_ts(sp_active_ts_stop) + " (inactive timer: " + display_time(SPOTIFY_INACTIVITY_CHECK) + ")")
                        
                        # If tracking functionality is enabled then either pause the current song via Spotify client or play the indicated SP_USER_GOT_OFFLINE_TRACK_ID "finishing" song
                        if track_songs:
                            sp_track_id=SP_USER_GOT_OFFLINE_TRACK_ID

                            if sp_track_id:
                                if platform.system() == 'Darwin':       # macOS
                                    script = 'tell app "Spotify" to play track "spotify:track:' + sp_track_id + '"'
                                    proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                                    stdout, stderr = proc.communicate(script)
                                    if SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE > 0:
                                        time.sleep(SP_USER_GOT_OFFLINE_DELAY_BEFORE_PAUSE)
                                        script = 'tell app "Spotify" to pause'
                                        proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)                                                     
                                        stdout, stderr = proc.communicate(script)
                            else:
                                script = 'tell app "Spotify" to pause'
                                proc = subprocess.Popen(['osascript', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)                                                     
                                stdout, stderr = proc.communicate(script)
                                                                       
                        if inactive_notification:
                            m_subject="Spotify user " + sp_username + " is inactive: '" + sp_artist + " - " + sp_track + "' (after " + calculate_timespan(int(sp_active_ts_stop),int(sp_active_ts_start),show_seconds=False) + ": " + get_range_of_dates_from_tss(sp_active_ts_start,sp_active_ts_stop,short=True) + ")"
                            m_body="Last played: " + sp_artist + " - " + sp_track + "\nDuration: " + display_time(sp_track_duration) + played_for_m_body + playlist_m_body + "\nAlbum: " + sp_album + context_m_body + "\n\nApple search URL: " + apple_search_url + "\nGenius lyrics URL: " + genius_search_url + "\n\nFriend got inactive after listening to music for " + calculate_timespan(int(sp_active_ts_stop),int(sp_active_ts_start)) + "\nFriend played music from " + get_range_of_dates_from_tss(sp_active_ts_start,sp_active_ts_stop,short=True,between_sep=" to ") + listened_songs_mbody + "\n\nLast activity: " + get_date_from_ts(sp_active_ts_stop) + "\nInactivity timer: " + display_time(SPOTIFY_INACTIVITY_CHECK) + get_cur_ts("\nTimestamp: ")
                            m_body_html="<html><head></head><body>Last played: <b><a href=\"" + sp_artist_url + "\">" + sp_artist + "</a> - <a href=\"" + sp_track_url + "\">" + sp_track + "</a></b><br>Duration: " + display_time(sp_track_duration) + played_for_m_body_html + playlist_m_body_html + "<br>Album: <a href=\"" + sp_album_url + "\">" + sp_album + "</a>" + context_m_body_html + "<br><br>Apple search URL: <a href=\"" + apple_search_url + "\">" + str(sp_artist) + " - " + str(sp_track) + "</a>" + "<br>Genius lyrics URL: <a href=\"" + genius_search_url + "\">" + sp_artist + " - " + sp_track + "</a><br><br>Friend got inactive after listening to music for <b>" + calculate_timespan(int(sp_active_ts_stop),int(sp_active_ts_start)) + "</b><br>Friend played music from <b>" + get_range_of_dates_from_tss(sp_active_ts_start,sp_active_ts_stop,short=True,between_sep="</b> to <b>") + "</b>" + listened_songs_mbody_html + "<br><br>Last activity: <b>" + get_date_from_ts(sp_active_ts_stop) + "</b><br>Inactivity timer: " + display_time(SPOTIFY_INACTIVITY_CHECK) + get_cur_ts("<br>Timestamp: ") + "</body></html>"
                            print("Sending email notification to",RECEIVER_EMAIL)
                            send_email(m_subject,m_body, m_body_html, SMTP_SSL)
                            email_sent = True
                        sp_active_ts_start_old=sp_active_ts_start
                        sp_active_ts_start=0
                        listened_songs_old=listened_songs
                        skipped_songs_old=skipped_songs
                        looped_songs_old=looped_songs
                        listened_songs=0
                        looped_songs=0
                        skipped_songs=0                        
                        print_cur_ts("\nTimestamp:\t\t")

                    if alive_counter >= TOOL_ALIVE_COUNTER:
                        print_cur_ts("Alive check, timestamp: ")
                        alive_counter = 0

                time.sleep(SPOTIFY_CHECK_INTERVAL)

        # User is not found in the Spotify's friend list just after starting the tool
        else:
            if user_not_found is False:
                print("Spotify user", user_uri_id, "not found, retrying in", display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL),"intervals")
                print_cur_ts("Timestamp:\t\t")
                user_not_found=True
            time.sleep(SPOTIFY_DISAPPEARED_CHECK_INTERVAL)
            continue
    return 0

if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        os.system('clear')
    except:
        print("* Cannot clear the screen contents")

    print("Spotify Monitoring Tool",VERSION,"\n")

    parser = argparse.ArgumentParser("spotify_monitor")
    parser.add_argument("spotify_user_uri_id", nargs="?", default="test", help="Spotify user URI ID", type=str)
    parser.add_argument("-s", "--spotify_tracks", help="Filename with Spotify tracks/playlists/albums to monitor.", type=str, metavar="TRACKS_FILENAME")
    parser.add_argument("-l","--list_friends", help="List Spotify friends", action='store_true')
    parser.add_argument("-b", "--csv_file", help="Write every listened track to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-a","--active_notification", help="Send email notification once user gets active", action='store_true')
    parser.add_argument("-i","--inactive_notification", help="Send email notification once user gets inactive", action='store_true')
    parser.add_argument("-t","--track_notification", help="Send email notification once monitored track/playlist/album is found", action='store_true')
    parser.add_argument("-j","--song_notification", help="Send email notification for every changed song", action='store_true')
    parser.add_argument("-x","--song_on_loop_notification", help="Send email notification if user plays a song on loop (>= SONG_ON_LOOP_VALUE times)", action='store_true')       
    parser.add_argument("-e","--error_notification", help="Disable sending email notifications in case of errors like expired sp_dc", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks, in seconds", type=int)
    parser.add_argument("-o", "--offline_timer", help="Time required to mark inactive user as offline, in seconds", type=int)
    parser.add_argument("-p", "--online_timer", help="How long user is considered active after last activity, in seconds", type=int)
    parser.add_argument("-m", "--disappeared_timer", help="Wait time between checks once the user disappears from friends list, in seconds", type=int)
    parser.add_argument("-d", "--disable_logging", help="Disable logging to file 'spotify_monitor_UserURIID.log' file", action='store_true')
    parser.add_argument("-g", "--track_songs", help="Automatically track listened songs by playing it in Spotify client", action='store_true')
    args = parser.parse_args()

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.check_interval:
        SPOTIFY_CHECK_INTERVAL=args.check_interval
        TOOL_ALIVE_COUNTER=TOOL_ALIVE_INTERVAL/SPOTIFY_CHECK_INTERVAL

    if args.offline_timer:
        SPOTIFY_INACTIVITY_CHECK=args.offline_timer

    if args.online_timer:
        SPOTIFY_ACTIVITY_CHECK=args.online_timer

    if args.disappeared_timer:
        SPOTIFY_DISAPPEARED_CHECK_INTERVAL=args.disappeared_timer

    if args.list_friends:
        print("* Listing Spotify friends ...\n")
        try:
            accessToken=spotify_get_access_token(SP_DC_COOKIE)
            sp_friends=spotify_get_friends_json(accessToken)
            spotify_list_friends(sp_friends)
            print("-----------------------------------------------------------------------------------")
        except Exception as e:
            print("* Error -", e)
            traceback.print_exc()
            sys.exit(1)
        sys.exit(0)

    if args.spotify_tracks:
        try:
            with open(args.spotify_tracks) as file:
                sp_tracks = file.read().splitlines()
            file.close()
        except Exception as e:
            print("\n* Error, file with Spotify tracks cannot be opened")
            print("*", e)
            sys.exit(1)
    else:
        sp_tracks=[]

    if args.csv_file:
        csv_enabled=True
        csv_exists=os.path.isfile(args.csv_file)
        try:
            csv_file=open(args.csv_file, 'a', newline='', buffering=1)
        except Exception as e:
            print("\n* Error, CSV file cannot be opened for writing -", e)
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled=False
        csv_file=None
        csv_exists=False

    if not args.disable_logging:
        sp_logfile = sp_logfile + "_" + args.spotify_user_uri_id + ".log"
        sys.stdout = Logger(sp_logfile)

    active_notification=args.active_notification
    inactive_notification=args.inactive_notification
    song_notification=args.song_notification
    track_notification=args.track_notification
    song_on_loop_notification=args.song_on_loop_notification
    track_songs=args.track_songs

    print("* Spotify timers:\t\t[check interval: " + display_time(SPOTIFY_CHECK_INTERVAL) + "] [inactivity: " + display_time(SPOTIFY_INACTIVITY_CHECK) + "] [activity: " + display_time(SPOTIFY_ACTIVITY_CHECK) + "]\n* \t\t\t\t[disappeared: " + display_time(SPOTIFY_DISAPPEARED_CHECK_INTERVAL) + "]" )
    print("* Email notifications:\t\t[active = " + str(active_notification) + "] [inactive = " + str(inactive_notification) + "] [tracked = " + str(track_notification) + "]\n* \t\t\t\t[songs on loop = " + str(song_on_loop_notification) + "] [every song = " + str(song_notification) + "] [errors = " + str(args.error_notification) + "]")
    print("* Output logging disabled:\t" + str(args.disable_logging))
    print("* Track listened songs:\t\t" + str(track_songs))
    print("* CSV logging enabled:\t\t" + str(csv_enabled),"\n")

    signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
    signal.signal(signal.SIGUSR2, toggle_song_notifications_signal_handler)
    signal.signal(signal.SIGCONT, toggle_track_notifications_signal_handler)
    signal.signal(signal.SIGTRAP, increase_inactivity_check_signal_handler)
    signal.signal(signal.SIGABRT, decrease_inactivity_check_signal_handler)

    spotify_monitor_friend_uri(args.spotify_user_uri_id,sp_tracks,args.error_notification,args.csv_file,csv_exists)

    sys.stdout = stdout_bck
    sys.exit(0)

