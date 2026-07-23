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

#### Python from PyPI

```sh
pip install spotify_monitor
```

Run setup by itself:

```sh
spotify_monitor --setup
```

#### Docker image - fastest container setup

##### macOS or Windows

Use a macOS shell or Windows PowerShell with a Docker-compatible runtime that provides the `docker` CLI.

```sh
docker run --rm --pull=always -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --setup
```

After setup finishes, start monitoring with the files created by the wizard:

```sh
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --config-file /data/spotify_monitor.conf
```

The setup command pulls the current image. Both commands keep configuration, private values and output in the current directory.

In Windows Command Prompt replace `${PWD}` with `%cd%`.

##### Linux

`--user "$(id -u):$(id -g)"` runs the container with your numeric user and group IDs. This lets the container write files that your host account can edit.

```sh
docker run --rm --pull=always -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --setup
```

After setup finishes, start monitoring:

```sh
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --config-file /data/spotify_monitor.conf
```

#### Docker Compose - shorter recurring commands

Download the Compose file:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/docker-compose.yml
```

On a native Linux container engine, export your numeric user ID and group ID so files created in the current directory belong to you instead of `root`. Docker-compatible runtimes on macOS and Windows normally do not need these values.

```sh
export SPOTIFY_MONITOR_UID="$(id -u)"
export SPOTIFY_MONITOR_GID="$(id -g)"
```

Run setup by itself:

```sh
docker compose run --rm --pull=always spotify_monitor --setup
```

After setup finishes, start monitoring with the shorter recurring command:

```sh
docker compose up --no-log-prefix
```

For the manual single-file method, optional extras and upgrade commands for every method, see [Installation](installation.md).

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
- **Docker Ready**: Run through Docker Hub, Docker Compose or a local image with persistent configuration, secrets and output.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_skipped.png" alt="spotify_monitor_skipped" width="90%"/>
</p>

For even better real-time tracking with pause/resume detection, track progress indicators, enhanced stats and offline mode support, see [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor).

For Spotify profile and playlist change tracking, see [spotify_profile_monitor](https://github.com/misiektoja/spotify_profile_monitor).

For Spotify Web Player token and TOTP utilities, see [Debugging Tools](debugging.md#debugging-tools).
