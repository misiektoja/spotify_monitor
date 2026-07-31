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

Powerful real-time tracker for Spotify friend music activity: monitor listening habits, auto-sync playback to your local Spotify client, detect skipped tracks and receive instant notifications for every beat your friends play.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor.png" alt="spotify_monitor_screenshot" width="90%"/>
</p>

<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

Spotify Monitor has two independent modes:

- **Friend Activity** monitors a Spotify friend's completed plays, activity status and listening sessions.
- **Last.fm Scrobble Health** checks whether plays from your Spotify account reach your Last.fm profile and alerts you when scrobbles stop showing up.

#### Python from PyPI

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/spotify_monitor/installation/#new-to-python-install-everything) first.

```sh
pip install spotify_monitor
```

Run setup for friend activity mode:

```sh
spotify_monitor --setup
```

Or for Last.fm Scrobble Health:
```sh
spotify_monitor --setup-scrobble-health
```

#### Docker image - fastest container setup

The Docker commands below run Friend Activity setup. For Last.fm Scrobble Health, replace the final `--setup` with `--setup-scrobble-health`.

##### macOS or Windows

Use a macOS shell or Windows PowerShell with a Docker-compatible runtime that provides the `docker` CLI.

```sh
docker run --rm --pull=always -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --setup
```

In Windows Command Prompt replace `${PWD}` with `%cd%` above.

##### Linux

Run the container with your numeric user and group IDs (`--user "$(id -u):$(id -g)"` below). This lets the container write files that your host account can edit.

```sh
docker run --rm --pull=always -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --setup
```

#### Docker Compose - shorter recurring commands

Download the Compose file:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/docker-compose.yml
```

Linux container engine requires to export your numeric user ID and group ID so files created in the current directory belong to you instead of `root`.

```sh
export SPOTIFY_MONITOR_UID="$(id -u)"
export SPOTIFY_MONITOR_GID="$(id -g)"
```

Docker-compatible runtimes on macOS and Windows normally do not need these values.

Run setup wizard:

```sh
docker compose run --rm --pull=always spotify_monitor --setup
```

For the manual single-file method, optional extras and upgrade commands for every method, see [Installation](https://misiektoja.github.io/spotify_monitor/installation/).

<a id="features"></a>
## Features

### 🔍 Real-time Tracking
- **Friend Activity**: Monitor songs listened to by Spotify users in real time.
- **Scrobble Health**: Detect and alert when Spotify scrobbles stop showing up on Last.fm.
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
- **Docker Ready**: Run through Docker Hub, Docker Compose or a local image with persistent configuration, secrets and output.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_skipped.png" alt="spotify_monitor_skipped" width="90%"/>
</p>

For even better real-time tracking with pause/resume detection, track progress indicators, enhanced stats and offline mode support, see [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor).

For Spotify profile and playlist change tracking, see [spotify_profile_monitor](https://github.com/misiektoja/spotify_profile_monitor).

For Spotify Web Player token and TOTP utilities, see [Debugging Tools](debugging.md#debugging-tools).
