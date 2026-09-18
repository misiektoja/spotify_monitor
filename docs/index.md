# spotify_monitor

[![GitHub Release](https://img.shields.io/github/v/release/misiektoja/spotify_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/spotify_monitor/releases)
[![PyPI Version](https://img.shields.io/pypi/v/spotify_monitor?style=flat-square&color=teal)](https://pypi.org/project/spotify-monitor/)
[![GitHub Stars](https://img.shields.io/github/stars/misiektoja/spotify_monitor?style=flat-square&color=magenta)](https://github.com/misiektoja/spotify_monitor)
[![Python Versions](https://img.shields.io/badge/python-3.9+-blueviolet?style=flat-square)](https://pypi.org/project/spotify-monitor/)
[![Docker Pulls](https://img.shields.io/docker/pulls/misiektoja/spotify-monitor?style=flat-square&logo=docker)](https://hub.docker.com/r/misiektoja/spotify-monitor)
[![License](https://img.shields.io/github/license/misiektoja/spotify_monitor?style=flat-square&color=blue)](https://github.com/misiektoja/spotify_monitor/blob/main/LICENSE)
[![OpenSSF Scorecard](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Fspotify_monitor&query=%24.score&label=openssf%20scorecard&style=flat-square)](https://scorecard.dev/viewer/?uri=github.com/misiektoja/spotify_monitor)
[![Last Commit](https://img.shields.io/github/last-commit/misiektoja/spotify_monitor?style=flat-square&color=green)](https://github.com/misiektoja/spotify_monitor/commits/main)
[![Maintenance](https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square)](https://github.com/misiektoja/spotify_monitor)

Track Spotify friend listening activity, play reported tracks in your local Spotify client and receive activity notifications.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor.png" alt="spotify_monitor_screenshot" width="90%"/>
</p>

<a id="quick-install-run"></a>
### 🚀 Quick Install & Run

#### Python from PyPI

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/spotify_monitor/installation/#new-to-python-check-and-install) first.

```sh
pip install spotify_monitor
```

Run setup for **friend activity mode** (Spotify friend's shared tracks, playback state and listening session):

```sh
spotify_monitor --setup
```

Or for **Last.fm scrobble health mode** (checks whether plays from your Spotify account reach your Last.fm profile):
```sh
spotify_monitor --setup-scrobble-health
```

The wizard asks for few details and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/spotify_monitor/setup-and-first-run/) for other options.

#### Docker image - fastest container setup

The Docker commands below run Friend Activity setup. For Last.fm scrobble health, replace the final `--setup` with `--setup-scrobble-health`.

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

For the manual single-file method, optional extras and upgrade commands, see [Installation](https://misiektoja.github.io/spotify_monitor/installation/).

<a id="features"></a>
## Features

### 🔍 Real-time Tracking
- **Friend Activity**: Track what your friends are listening to.
- **Scrobble Health**: Detect and alert when Spotify scrobbles stop showing up on Last.fm.
- **Presence Detection**: Detect when friends get **online** or **offline** and how long they stay **out of view**, such as during a private session.
- **Session Stats**: Display **duration, track counts, pauses** and **songs on loop**.

### 🎮 Playback Control
- **Auto-Sync**: Automatically **play friends' songs** in your local Spotify client.
- **Smart Pause**: **Pause** or **switch** tracks when the monitored user goes offline.
- **Crossfade Support**: Detect and annotate **crossfaded songs** during transitions.

### 📊 Rich Insights
- **Track Context**: View **playlist, artist** and **album info** with clickable URLs.
- **Skip Detection**: See **skipped songs** and how long each song was played.
- **Global Search**: Instant links to **Spotify, YouTube Music, Apple Music, Tidal, lyrics** and more.
- **Coloured Output**: Readable terminal colours with a **customizable theme**, while log files stay plain text.

### 🔔 Smart Notifications
- **Multi-Channel**: Instant alerts via **Email** and **Webhooks** (**Discord**, **ntfy** etc.).
- **Detailed Alerts**: Choose activity, tracked-song, every-song, loop and error alerts.
- **Session Summaries**: Receive detailed reports when a friend finishes a session.
- **Error Reporting**: Be notified if the monitoring process hits a snag.

### ⚙️ Power Features
- **Auth Flexibility**: Sign in with a browser **cookie** or the **Spotify Desktop Client**, no developer app required.
- **CSV Logging**: Save every listened song with full timestamps to a CSV file.
- **Flexible Config**: Support for files, dotenv and environment variables.
- **Signal Control**: Manage the running script via system signals (macOS/Linux).
- **Docker Ready**: Run through Docker Hub, Docker Compose or a local image with persistent configuration, secrets and output.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_skipped.png" alt="spotify_monitor_skipped" width="90%"/>
</p>

For track progress indicators and offline scrobble history, see [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor).

For Spotify profile and playlist change tracking, see [spotify_profile_monitor](https://github.com/misiektoja/spotify_profile_monitor).

For Spotify Web Player token and TOTP utilities, see [Debugging Tools](debugging.md#debugging-tools).
