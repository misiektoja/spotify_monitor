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

<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

#### Python from PyPI

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/spotify_monitor/installation/#new-to-python-install-everything) first.

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

For the manual single-file method, optional extras and upgrade commands for every method, see [Installation](https://misiektoja.github.io/spotify_monitor/installation/).

<a id="features"></a>
## Features

### 🔍 Real-time Tracking
- **Friend Activity**: Monitor live shared tracks by default or select the legacy completed-track backend.
- **Scrobble Health**: Detect and alert when Spotify scrobbles stop showing up on Last.fm.
- **Presence Detection**: Detect when friends get **online** or **offline**.
- **Session Stats**: Display session duration, played track counts, pauses and songs on loop.

### 🎮 Playback Control
- **Auto-Sync**: Automatically **play friends' songs** in your local Spotify client.
- **Smart Pause**: **Pause** or **switch** tracks when the monitored user goes offline.
- **Crossfade Support**: Estimate crossfaded transitions with the legacy backend.

### 📊 Rich Insights
- **Track Context**: View **playlist, artist** and **album info** with clickable URLs.
- **Skip Detection**: Report skipped tracks and played duration. Live timing follows the feed timestamps, excludes pauses and does not mark partially observed tracks as skipped.
- **Global Search**: Instant links to **Spotify, YouTube Music, Apple Music, Tidal, lyrics** and more.
- **Coloured Output**: Readable terminal colours with a **customizable theme**, while log files stay plain text.

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

For track progress indicators and offline scrobble history, see [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor).

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
| Start monitoring with existing authentication | `spotify_monitor TARGET`, where `TARGET` is a complete profile URL, `spotify:user:` URI or user ID |
| Check authentication, connectivity and one target | `spotify_monitor --doctor TARGET` |
| List Spotify friends visible to the configured account | `spotify_monitor --list-friends` |
| Import a Spotify login from Firefox | Open [Spotify Web Player](https://open.spotify.com/) in Firefox, sign in then run `spotify_monitor --import-browser-cookie --browser firefox` |
| Enter or replace securely a manually extracted `SP_DC_COOKIE` | Run `spotify_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Enter or replace securely `LASTFM_API_KEY` | Run `spotify_monitor --set-lastfm-credentials` and enter the key at the hidden prompt |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](https://misiektoja.github.io/spotify_monitor/configuration/#webhook-settings) |
| Start scrobble health monitoring from saved settings | Run `spotify_monitor --monitor-mode scrobble_health` |
| Select the monitoring mode for one run | Run `spotify_monitor --monitor-mode friend_activity TARGET` or `spotify_monitor --monitor-mode scrobble_health` |

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

<a id="contributing"></a>
## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/spotify_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/spotify_monitor/blob/main/CODE_OF_CONDUCT.md).

<a id="security"></a>
## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/spotify_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/spotify_monitor/blob/main/SECURITY.md) covers the reporting process, the supported versions and the security posture of stored secrets, configuration loading and local playback.

<a id="maintainers"></a>
## Maintainers

- **misiektoja** ([@misiektoja](https://github.com/misiektoja))
- **tomballgithub** ([@tomballgithub](https://github.com/tomballgithub))

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/spotify_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/spotify_monitor/blob/main/THIRD_PARTY_NOTICES.md).

<a id="support"></a>
## Support

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).
