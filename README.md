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

Run setup wizard:

```sh
spotify_monitor --setup
```

#### Docker image - fastest container setup

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

For pause and resume tracking, progress indicators and offline mode, see [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor).

For Spotify profile and playlist change tracking, see [spotify_profile_monitor](https://github.com/misiektoja/spotify_profile_monitor).

For Spotify Web Player token and TOTP utilities, see [Debugging Tools](https://misiektoja.github.io/spotify_monitor/debugging/#debugging-tools).

<a id="before-monitoring"></a>
## Before Monitoring

Spotify only shows a person's listening activity when both of these conditions are met:

1. The Spotify account used by Spotify Monitor follows the person you want to monitor.
2. That person has enabled listening activity sharing in Spotify.

The setup wizard checks whether the monitoring account follows the target. It can send the follow request after you confirm. To follow manually, open the target's profile in the Spotify desktop or mobile app. You can use **Share** > **Copy link to profile** and paste the complete link into the wizard. You do not need to extract the user ID. See [Following the Monitored User](https://misiektoja.github.io/spotify_monitor/configuration/#following-the-monitored-user).

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) above for first-time setup. The table uses PyPI commands. For manual script, direct Docker and Docker Compose equivalents, see [Run Individual Commands](https://misiektoja.github.io/spotify_monitor/setup-and-first-run/#run-individual-commands).

| I want to... | Run this |
| --- | --- |
| Start monitoring with existing authentication | `spotify_monitor TARGET`, where `TARGET` is a raw ID, `spotify:user:` URI or profile URL |
| Start a target saved as `TARGET_USER_URI_ID` | `spotify_monitor --config-file spotify_monitor.conf` |
| Check authentication, connectivity and one target | `spotify_monitor --doctor TARGET` |
| List Spotify friends visible to the configured account | `spotify_monitor --list-friends` |
| Import a Spotify login from Firefox | Open [Spotify Web Player](https://open.spotify.com/) in Firefox, sign in then run `spotify_monitor --import-browser-cookie --browser firefox` |
| Safely set or replace `SP_DC_COOKIE` | Run `spotify_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](https://misiektoja.github.io/spotify_monitor/configuration/#webhook-settings) |

Running the tool with no arguments offers the wizard if you have not saved a target. If a target is already saved, it starts monitoring that target.

For authentication, saved targets, configuration backups and setup recovery, see the [full Setup & First Run guide](https://misiektoja.github.io/spotify_monitor/setup-and-first-run/).

For browser profiles, manual cookie extraction, Docker authentication, email and webhook setup, see [Configuration](https://misiektoja.github.io/spotify_monitor/configuration/). For notification choices, playback controls and output files, see [Usage](https://misiektoja.github.io/spotify_monitor/usage/).

<a id="documentation"></a>
## Documentation

Full documentation is available at **[misiektoja.github.io/spotify_monitor](https://misiektoja.github.io/spotify_monitor/)**:

- [Installation](https://misiektoja.github.io/spotify_monitor/installation/) - PyPI, manual script, Docker installation and upgrades
- [Setup & First Run](https://misiektoja.github.io/spotify_monitor/setup-and-first-run/) - setup wizard, authentication and first run
- [Configuration](https://misiektoja.github.io/spotify_monitor/configuration/) - Spotify login, targets, SMTP, webhooks and secrets
- [Usage](https://misiektoja.github.io/spotify_monitor/usage/) - command formats, monitoring, container operation, notifications, playback and output
- [Troubleshooting](https://misiektoja.github.io/spotify_monitor/troubleshooting/) - the `--doctor` self-check and logging levels
- [Debugging Tools](https://misiektoja.github.io/spotify_monitor/debugging/) - TOTP token testing and secret extraction

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/spotify_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="maintainers"></a>
## Maintainers

- **misiektoja** ([@misiektoja](https://github.com/misiektoja))
- **tomballgithub** ([@tomballgithub](https://github.com/tomballgithub))

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/spotify_monitor/blob/main/LICENSE).
