# spotify_monitor

<p align="left">
  <img src="https://img.shields.io/github/v/release/misiektoja/spotify_monitor?style=flat-square&color=blue" alt="GitHub Release" />
  <img src="https://img.shields.io/pypi/v/spotify_monitor?style=flat-square&color=teal" alt="PyPI Version" />
  <img src="https://img.shields.io/github/stars/misiektoja/spotify_monitor?style=flat-square&color=magenta" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/python-3.9+-blueviolet?style=flat-square" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/misiektoja/spotify_monitor?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/github/last-commit/misiektoja/spotify_monitor?style=flat-square&color=green" alt="Last Commit" />
  <img src="https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square" alt="Maintenance" />
</p>

Powerful real-time tracker for Spotify friend music activity: monitor listening habits, auto-sync playback to your local client, detect skipped tracks and receive instant notifications for every beat your friends play.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor.png" alt="spotify_monitor_screenshot" width="90%"/>
</p>

<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

Python from PyPI

```sh
pip install spotify_monitor
spotify_monitor --setup
```

Docker Compose

On Linux, set the container user to your host user before the first setup command. This lets Spotify Monitor create its configuration and private `.env` file in the current directory. Docker Desktop users on macOS or Windows can skip the two `export` commands.

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/docker-compose.yml
export SPOTIFY_MONITOR_UID="$(id -u)"
export SPOTIFY_MONITOR_GID="$(id -g)"
docker compose run --rm spotify_monitor --setup
docker compose up
```

Docker run

On macOS or Windows with Docker Desktop:

```sh
docker pull misiektoja/spotify-monitor:latest
docker run --rm -it --init -v "$PWD:/data:z" misiektoja/spotify-monitor --setup
docker run --rm -it --init -v "$PWD:/data:z" misiektoja/spotify-monitor --config-file /data/spotify_monitor.conf
```

On Linux, pass your host user and group so the container can write to the current directory:

```sh
docker pull misiektoja/spotify-monitor:latest
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor --setup
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor --config-file /data/spotify_monitor.conf
```

<a id="features"></a>
## Features

### 🔍 Real-time Tracking
- **Friend Activity**: Monitor songs listened by Spotify users in real-time.
- **Presence Detection**: Detect when friends get **online** or **offline**.
- **Session Stats**: Display **duration, track counts** and **songs on loop**.

### 🎮 Playback Control
- **Auto-Sync**: Automatically **play friends' songs** in your local Spotify client.
- **Smart Pause**: **Pause** or **switch** tracks when the monitored user goes offline.
- **Crossfade Support**: Detect and annotate **crossfaded songs** during transitions.

### 📊 Rich Insights
- **Track Context**: View **playlist, artist** and **album info** with clickable URLs.
- **Skip Detection**: Identify exactly when and how long a song was played.
- **Global Search**: Instant links to **Spotify, YouTube Music, Apple Music, Tidal, lyrics** and more.

### 🔔 Smart Notifications
- **Multi-Channel**: Instant alerts via **Email** and **Webhooks** (**Discord**, **ntfy** etc.).
- **Detailed Alerts**: Choose activity, tracked-song, every-song, loop and error alerts.
- **Session Summaries**: Receive detailed reports when a friend finishes a session.
- **Error Reporting**: Be notified if the monitoring process hits a snag.

### ⚙️ Power Features
- **Auth Flexibility**: Cookie or Desktop Client access with automatic web-player metadata fallback and optional legacy OAuth app support.
- **CSV Logging**: Save every listened song with full timestamps to a CSV file.
- **Flexible Config**: Support for files, dotenv and environment variables.
- **Signal Control**: Manage the running script via system signals (macOS/Linux).

> **Spotify OAuth app note:** Spotify requires the owner of every Development Mode app to have an active Spotify Premium subscription. This applies to old and new apps. OAuth app credentials are optional because Spotify Monitor falls back automatically to the web-player metadata backend. See Spotify's [official migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide).

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_skipped.png" alt="spotify_monitor_skipped" width="90%"/>
</p>

🎵 For even better real-time tracking with pause/resume detection, track progress indicators, enhanced stats and offline mode support, check out [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor) - it is much easier to set up, simply ask your friend to connect Last.fm to Spotify (Last.fm Settings → Applications → Connect Spotify Scrobbling) and you're ready to go!

✨ If you're interested in tracking changes to Spotify users' profiles including their playlists, take a look at another tool I've developed: [spotify_profile_monitor](https://github.com/misiektoja/spotify_profile_monitor).

🛠️ If you're looking for debug tools to get Spotify Web Player access tokens and extract secret keys: [click here](debugging.md#debugging-tools)
