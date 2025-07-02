# spotify_monitor

Tool for real-time monitoring of Spotify friends' music activity feed.

NOTE: If you're interested in tracking changes to Spotify users' profiles including their playlists, take a look at another tool I've developed: [spotify_profile_monitor](https://github.com/misiektoja/spotify_profile_monitor).

<a id="features"></a>
## Features

- Real-time tracking of songs listened by Spotify users (including detection when user gets online & offline)
- Possibility to automatically play songs listened by the tracked user in your local Spotify client
- Information about the duration the user listened to a song and whether the song was skipped
- Information about the context of the listened song (playlist/artist/album) with clickable URLs
- Email notifications for various events (user becomes active/inactive, specific or all songs, songs on loop, errors)
- Saving all listened songs with timestamps to the CSV file
- Clickable Spotify, Apple Music, YouTube Music and Genius Lyrics search URLs printed in the console & included in email notifications
- Displaying basic statistics for the user's playing session (duration, time span, number of listened and skipped songs, songs on loop)
- Support for two different methods to get a Spotify access token (`sp_dc cookie`, `desktop client`)
- Possibility to control the running copy of the script via signals

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor.png" alt="spotify_monitor_screenshot" width="90%"/>
</p>

<a id="table-of-contents"></a>
## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
   * [Install from PyPI](#install-from-pypi)
   * [Manual Installation](#manual-installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
   * [Configuration File](#configuration-file)
   * [Spotify access token source](#spotify-access-token-source)
      * [Spotify sp_dc Cookie](#spotify-sp_dc-cookie)
      * [Spotify Desktop Client](#spotify-desktop-client)
   * [Following the Monitored User](#following-the-monitored-user)
   * [How to Get a Friend's User URI ID](#how-to-get-a-friends-user-uri-id)
   * [SMTP Settings](#smtp-settings)
   * [Storing Secrets](#storing-secrets)
5. [Usage](#usage)
   * [Monitoring Mode](#monitoring-mode)
   * [Listing Mode](#listing-mode)
   * [Email Notifications](#email-notifications)
   * [CSV Export](#csv-export)
   * [Automatic Playback of Listened Tracks in the Spotify Client](#automatic-playback-of-listened-tracks-in-the-spotify-client)
   * [Check Intervals](#check-intervals)
   * [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix)
   * [Coloring Log Output with GRC](#coloring-log-output-with-grc)
6. [Change Log](#change-log)
7. [License](#license)

<a id="requirements"></a>
## Requirements

* Python 3.6 or higher
* Libraries: `requests`, `python-dateutil`, `urllib3`, `pyotp`, `python-dotenv`

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm), Ubuntu 24, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="installation"></a>
## Installation

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install spotify_monitor
```

<a id="manual-installation"></a>
### Manual Installation

Download the *[spotify_monitor.py](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install requests python-dateutil urllib3 pyotp python-dotenv
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

<a id="quick-start"></a>
## Quick Start

- Grab your [Spotify sp_dc cookie](#spotify-sp_dc-cookie) and track the `spotify_user_uri_id` music activities:


```sh
spotify_monitor <spotify_user_uri_id> -u "your_sp_dc_cookie_value"
```

Or if you installed [manually](#manual-installation):

```sh
python3 spotify_monitor.py <spotify_user_uri_id> -u "your_sp_dc_cookie_value"
```

To get the list of all supported command-line arguments / flags:

```sh
spotify_monitor --help
```

<a id="configuration"></a>
## Configuration

<a id="configuration-file"></a>
### Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, generate a default config template and save it to a file named `spotify_monitor.conf`:

```sh
spotify_monitor --generate-config > spotify_monitor.conf

```

Edit the `spotify_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

<a id="spotify-access-token-source"></a>
### Spotify access token source

The tool supports two methods for obtaining a Spotify access token.

It can be configured via the `TOKEN_SOURCE` configuration option or the `--token-source` flag. 

**Recommended: `cookie`** 

Uses the `sp_dc` cookie to retrieve a token from the Spotify web endpoint. This method is easy to set up and recommended for most users.

**Alternative: `client`** 

Uses captured credentials from the Spotify desktop client and a Protobuf-based login flow. It's more complex to set up and intended for advanced users who want a long-lasting token with the broadest possible access.

If no method is specified, the tool defaults to the `cookie` method.

**Important**: It is strongly recommended to use a separate Spotify account with this tool. It does not rely on the official Spotify Web API for core features (like fetching friend activity), as it is not supported by the public API. That said, while I've never encountered any issues on my own accounts, I can't guarantee that Spotify won't impose restrictions in the future - you've been warned.

<a id="spotify-sp_dc-cookie"></a>
#### Spotify sp_dc Cookie

This is the default method used to obtain a Spotify access token.

- Log in to [https://open.spotify.com/](https://open.spotify.com/) in your web browser.

- Locate and copy the value of the `sp_dc` cookie.
   - Use your web browser's dev console or **Cookie-Editor** by cgagnier to extract it easily: [https://cookie-editor.com/](https://cookie-editor.com/)

- Provide the `SP_DC_COOKIE` secret using one of the following methods:
   - Pass it at runtime with `-u` / `--spotify-dc-cookie`
   - Set it as an [environment variable](#storing-secrets) (e.g. `export SP_DC_COOKIE=...`)
   - Add it to [.env file](#storing-secrets) (`SP_DC_COOKIE=...`) for persistent use
   - Fallback: hard-code it in the code or config file

If your `sp_dc` cookie expires, the tool will notify you via the console and email. In that case, you'll need to grab the new `sp_dc` cookie value.

If you store the `SP_DC_COOKIE` in a dotenv file you can update its value and send a `SIGHUP` signal to reload the file with the new `sp_dc` cookie without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix).

<a id="spotify-desktop-client"></a>
#### Spotify Desktop Client

This is the alternative method used to obtain a Spotify access token which simulates a login from the real Spotify desktop app using credentials intercepted from a real session.

**NOTE**: Spotify appears to have changed something in client versions released after June 2025 (likely a switch to HTTP/3 and/or certificate pinning). You may need to use an older version of the Spotify desktop client for this method to work.

- Run an intercepting proxy of your choice (like [Proxyman](https://proxyman.com)).

- Launch the Spotify desktop client and look for POST requests to `https://login{n}.spotify.com/v3/login`
   - Note: The `login` part is suffixed with one or more digits (e.g. `login5`).

- If you don't see this request, log out from the Spotify desktop client and log back in.

- Export the login request body (a binary Protobuf payload) to a file (e.g. ***login-request-body-file***)
   - In Proxyman: **right click the request → Export → Request Body → Save File**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/proxyman_export_protobuf.png" alt="proxyman_export_protobuf" width="80%"/>
</p>

- Run the tool with `--token-source client -w <path-to-login-request-body-file>`:

```sh
spotify_monitor --token-source client -w <path-to-login-request-body-file> <spotify_user_uri_id>
```

If successful, the tool will automatically extract the necessary fields and begin monitoring.

Instead of using the `-w` flag each time, you can persist the Protobuf login request file path by setting the `LOGIN_REQUEST_BODY_FILE` configuration option.

The same applies to `--token-source client` flag - you can persist it via `TOKEN_SOURCE` configuration option set to `client`.

The tool will automatically refresh both the access token and client token using the intercepted refresh token.

If your refresh token expires, the tool will notify you via the console and email. In that case, you'll need to re-export the login request body. 

If you re-export the login request body to the same file name, you can send a `SIGHUP` signal to reload the file with the new refresh token without restarting the tool. More info in [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix).

Advanced options are available for further customization - refer to the configuration file comments. However, the default settings are suitable for most users and modifying other values is generally NOT recommended.

<a id="following-the-monitored-user"></a>
### Following the Monitored User

To monitor a user's activity, you must follow them from the Spotify account associated with the `sp_dc` cookie.

Additionally, the user must have sharing of listening activity enabled in their Spotify client settings. Without this, no activity data will be visible.

<a id="how-to-get-a-friends-user-uri-id"></a>
### How to Get a Friend's User URI ID

The easiest way is via the Spotify desktop or mobile client:
- go to your friend's profile
- click the **three dots** (•••) or press the **Share** button
- copy the link to the profile

You'll get a URL like: [https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id](https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id)

Extract the part between `/user/` and `?si=` - in this case: `spotify_user_uri_id`

Use that as the user URI ID (`spotify_user_uri_id`) in the tool.

Alternatively you can list all user URI IDs of accounts you follow by using [Listing mode](#listing-mode).

<a id="smtp-settings"></a>
### SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `spotify_monitor.conf` file. 

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
spotify_monitor --send-test-email
```

<a id="storing-secrets"></a>
### Storing Secrets

It is recommended to store secrets like `SP_DC_COOKIE`, `REFRESH_TOKEN` or `SMTP_PASSWORD` as either an environment variable or in a dotenv file.

Set the needed environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export SP_DC_COOKIE="your_sp_dc_cookie_value"
export REFRESH_TOKEN="your_spotify_app_refresh_token"
export SMTP_PASSWORD="your_smtp_password"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file (recommended):

```ini
SP_DC_COOKIE="your_sp_dc_cookie_value"
REFRESH_TOKEN="your_spotify_app_refresh_token"
SMTP_PASSWORD="your_smtp_password"
```

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it. 

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
spotify_monitor <spotify_user_uri_id> --env-file /path/.env-spotify_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
spotify_monitor <spotify_user_uri_id> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.

<a id="usage"></a>
## Usage

<a id="monitoring-mode"></a>
### Monitoring Mode

To monitor specific user activity, just type [Spotify user URI ID](#how-to-get-a-friends-user-uri-id) as a command-line argument (`spotify_user_uri_id` in the example below):

```sh
spotify_monitor <spotify_user_uri_id>
```

If you use the default method to obtain a Spotify access token (`cookie`) and have not set `SP_DC_COOKIE` secret, you can use `-u` flag:

```sh
spotify_monitor <spotify_user_uri_id> -u "your_sp_dc_cookie_value"
```

By default, the tool looks for a configuration file named `spotify_monitor.conf` in:
 - current directory 
 - home directory (`~`)
 - script directory 

 If you generated a configuration file as described in [Configuration](#configuration), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:


```sh
spotify_monitor <spotify_user_uri_id> --config-file /path/spotify_monitor_new.conf
```

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple Spotify friends by running multiple copies of the script.

The tool automatically saves its output to `spotify_monitor_<user_uri_id/file_suffix>.log` file. The log file name can be changed via `SP_LOGFILE` configuration option and its suffix via `FILE_SUFFIX` / `-y` flag. Logging can be disabled completely via `DISABLE_LOGGING` / `-d` flag.

Keep in mind that monitoring reports the listened track AFTER the user finishes listening to it. This is how activities are reported by Spotify.

<a id="listing-mode"></a>
### Listing Mode

There is also another mode of the tool which displays various requested information.

If you want to display a list of all the friends you follow with their recently listened tracks (`-l` flag):

```sh
spotify_monitor -l
```

It also displays your friend's Spotify username (often the user's first and last name) and user URI ID (often a string of random characters). The latter should be used as a tool's command-line argument to monitor the user.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_listing.png" alt="spotify_monitor_listing" width="90%"/>
</p>

To get basic information about the Spotify access token owner (`-v` flag):

```sh
spotify_monitor -v
```

<a id="email-notifications"></a>
### Email Notifications

To enable email notifications when a user becomes active:
- set `ACTIVE_NOTIFICATION` to `True`
- or use the `-a` flag

```sh
spotify_monitor <spotify_user_uri_id> -a
```

To be informed when a user gets inactive:
- set `INACTIVE_NOTIFICATION` to `True`
- or use the `-i` flag

```sh
spotify_monitor <spotify_user_uri_id> -i
```

To get email notifications when a monitored track/playlist/album plays:
- set `TRACK_NOTIFICATION` to `True`
- or use the `-t` flag

For that feature you also need to create a file with a list of songs you want to track (one track, album or playlist per line). Specify the file using the `MONITOR_LIST_FILE` or `-s` flag:

```sh
spotify_monitor <spotify_user_uri_id> -t -s spotify_tracks_spotify_user_uri_id
```

Example file `spotify_tracks_spotify_user_uri_id`:

```
we fell in love in october
Like a Stone
Half Believing
Something Changed
I Will Be There
```

You can comment out specific lines with # if needed.

To enable email notifications for every song listened by the user:
- set `SONG_NOTIFICATION` to `True`
- or use the `-j` flag

```sh
spotify_monitor <spotify_user_uri_id> -j
```

To be notified when a user listens to the same song on loop:
- set `SONG_ON_LOOP_NOTIFICATION` to `True`
- or use the `-x` flag

```sh
spotify_monitor <spotify_user_uri_id> -x
```

To disable sending an email on errors (enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
spotify_monitor <spotify_user_uri_id> -e
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_email_notifications.png" alt="spotify_monitor_email_notifications" width="80%"/>
</p>

<a id="csv-export"></a>
### CSV Export

If you want to save all listened songs to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
spotify_monitor <spotify_user_uri_id> -b spotify_tracks_user_uri_id.csv
```

The file will be automatically created if it does not exist.

<a id="automatic-playback-of-listened-tracks-in-the-spotify-client"></a>
### Automatic Playback of Listened Tracks in the Spotify Client

If you want the tool to automatically play the tracks listened to by the user in your local Spotify client:
- set `TRACK_SONGS` to `True`
- or use the `-g` flag

```sh
spotify_monitor <spotify_user_uri_id> -g
```

Your Spotify client needs to be installed and running for this feature to work.

The tool fully supports automatic playback on **Linux** and **macOS**. This means it will automatically play the changed track and can also pause or play the indicated track once the user becomes inactive (see the `SP_USER_GOT_OFFLINE_TRACK_ID` configuration option).

For **Windows**, it works in a semi-automatic way: if you have the Spotify client running and you are not listening to any song, then the first track will play automatically. However, subsequent tracks will be located in the client, but you will need to press the play button manually. 

You can change the playback method per platform using the corresponding configuration option.

For **macOS** set `SPOTIFY_MACOS_PLAYING_METHOD` to one of the following values:
-  "**apple-script**" (recommended, **default**)
-  "trigger-url"

For **Linux** set `SPOTIFY_LINUX_PLAYING_METHOD` to one of the following values:
- "**dbus-send**" (most common one, **default**)
- "qdbus" (try if dbus-send does not work)
- "trigger-url"

For **Windows** set `SPOTIFY_WINDOWS_PLAYING_METHOD` to one of the following values:
- "**start-uri**" (recommended, **default**)
- "spotify-cmd"
- "trigger-url"

The recommended defaults should work for most people.

Note: monitoring reports the listened track after the user finishes listening to it. This is how activities are reported by Spotify. It means you will be one song behind the monitored user and if the song currently listened to by the tracked user is longer than the previous one, then the previously listened song might be played in your Spotify client on repeat (and if shorter it might be changed in the middle of the currently played song).

For real-time playback tracking of a user's music activities, ask your friend to connect their Spotify account with [Last.fm](https://www.last.fm/). Then use my other tool: [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor).

<a id="check-intervals"></a>
### Check Intervals

If you want to customize the polling interval, use `-c` flag (or `SPOTIFY_CHECK_INTERVAL` configuration option):

```sh
spotify_monitor <spotify_user_uri_id> -c 20
```

If you want to change the time required to mark the user as inactive (the timer starts from the last reported track), use `-o` flag (or `SPOTIFY_INACTIVITY_CHECK` configuration option):

```sh
spotify_monitor <spotify_user_uri_id> -o 900
```

<a id="signal-controls-macoslinuxunix"></a>
### Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets active/inactive (-a, -i) |
| USR2 | Toggle email notifications for every song (-j) |
| CONT | Toggle email notifications for tracked songs (-t) |
| PIPE | Toggle email notifications when user plays song on loop (-x) |
| TRAP | Increase the inactivity check timer (by 30 seconds) (-o) |
| ABRT | Decrease the inactivity check timer (by 30 seconds) (-o) |
| HUP | Reload secrets from .env file and token source credentials from Protobuf files |

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "spotify_monitor <spotify_user_uri_id>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
### Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to color logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 spotify_monitor_<user_uri_id/file_suffix>.log
```

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/spotify_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/spotify_monitor/blob/main/LICENSE).
