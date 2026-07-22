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
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --setup
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --config-file /data/spotify_monitor.conf
```

The Docker Desktop commands use macOS shell or Windows PowerShell syntax. In Windows Command Prompt replace `${PWD}` with `%cd%`.

On Linux, pass your host user and group so the container can write to the current directory:

```sh
docker pull misiektoja/spotify-monitor:latest
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --setup
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --config-file /data/spotify_monitor.conf
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

<a id="documentation"></a>
## Documentation

Full documentation is available at **[misiektoja.github.io/spotify_monitor](https://misiektoja.github.io/spotify_monitor/)**:

- [Installation](https://misiektoja.github.io/spotify_monitor/installation/) - PyPI, manual script, Docker installation and upgrades
- [Quick Start](https://misiektoja.github.io/spotify_monitor/quick-start/) - setup wizard, authentication and first run
- [Configuration](https://misiektoja.github.io/spotify_monitor/configuration/) - Spotify login, targets, SMTP, webhooks and secrets
- [Usage](https://misiektoja.github.io/spotify_monitor/usage/) - command formats, monitoring, container operation, notifications, playback and output
- [Troubleshooting](https://misiektoja.github.io/spotify_monitor/troubleshooting/) - the `--doctor` self-check and logging levels
- [Debugging Tools](https://misiektoja.github.io/spotify_monitor/debugging/) - TOTP token testing and secret extraction

<a id="quick-start"></a>
## Quick Start

<a id="new-here-run-the-setup-wizard"></a>
### New here? Run the setup wizard

The fastest way to get started is `--setup`. It asks who to monitor, how to connect to Spotify and which alerts you want then saves a ready-to-run configuration. Private values stay in `.env`.

On Linux, set `SPOTIFY_MONITOR_UID="$(id -u)"` and `SPOTIFY_MONITOR_GID="$(id -g)"` before using Docker Compose.

Use the command that matches how you run the tool:

```sh
# PyPI install
spotify_monitor --setup

# Manual Python script on macOS or Linux
python3 spotify_monitor.py --setup

# Manual Python script on Windows
python spotify_monitor.py --setup

# Docker Compose (skip curl if you cloned the repository)
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/docker-compose.yml
docker compose run --rm spotify_monitor --setup

# Docker image on macOS or Windows
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --setup

# Docker image on Linux
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --setup
```

Running the tool with no arguments also offers the wizard when no target has been saved. It detects whether you use PyPI, the downloaded script, Docker or Docker Compose then shows matching commands.

<a id="before-monitoring"></a>
### Before monitoring

Spotify only shows a person's listening activity when both of these conditions are met:

1. The Spotify account used by Spotify Monitor follows the person you want to monitor.
2. That person has enabled listening activity sharing in Spotify.

The setup wizard (`spotify_monitor --setup`) checks whether the configured Spotify account follows the target. It offers to follow only when needed and changes the account only after explicit confirmation. If you want to do it manually, open the person's profile in the Spotify desktop or mobile app then use **Share** > **Copy link to profile**. You can paste the complete profile link into the setup wizard. You do not need to extract the user ID yourself. See [Following the Monitored User](https://misiektoja.github.io/spotify_monitor/configuration/#following-the-monitored-user).

For local installs, Firefox import is the recommended login path. Docker users should use the wizard's hidden manual `sp_dc` entry. See the [full Quick Start guide](https://misiektoja.github.io/spotify_monitor/quick-start/) for details.

<a id="not-sure-which-command-you-need"></a>
### Not sure which command you need?

| I want to... | Run this |
| --- | --- |
| Set up Spotify Monitor for the first time | Use the setup command for your installation above |
| Start monitoring with existing authentication | `spotify_monitor TARGET`, where `TARGET` is a raw ID, `spotify:user:` URI or profile URL |
| Start a target saved as `TARGET_USER_URI_ID` | `spotify_monitor --config-file spotify_monitor.conf` or `docker compose up` |
| Check authentication, connectivity and one target | `spotify_monitor --doctor TARGET` |
| List Spotify friends visible to the configured account | `spotify_monitor --list-friends` |
| Import a Spotify login from Firefox | Open [Spotify Web Player](https://open.spotify.com/) in Firefox, sign in then run `spotify_monitor --import-browser-cookie --browser firefox` |
| Safely set or replace `SP_DC_COOKIE` | Run `spotify_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](https://misiektoja.github.io/spotify_monitor/configuration/#webhook-settings) |

<a id="manual-commands"></a>
### Manual commands

The examples below use a PyPI install. For a manual script install, replace `spotify_monitor` with `python3 spotify_monitor.py` on macOS or Linux and `python spotify_monitor.py` on Windows. Docker users can copy the complete command prefixes from the [Usage guide](https://misiektoja.github.io/spotify_monitor/usage/#command-format).

Sign in to [Spotify Web Player](https://open.spotify.com/) with Firefox then import that login:

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

If browser import is unavailable, enter `sp_dc` through a hidden prompt:

```sh
spotify_monitor --set-sp-dc
```

Start monitoring with a raw user ID, Spotify user URI or profile URL. A target saved by the wizard does not need to be repeated:

```sh
spotify_monitor <spotify_user_uri_id>
spotify_monitor "https://open.spotify.com/user/spotify_user_uri_id"
spotify_monitor --config-file spotify_monitor.conf
```

Run the self-check or view every command:

```sh
spotify_monitor --doctor <spotify_user_uri_id>
spotify_monitor --list-friends
spotify_monitor --help
```

For browser profiles, manual cookie extraction, Docker authentication, email and webhook setup, see [Configuration](https://misiektoja.github.io/spotify_monitor/configuration/). For notification choices, playback controls and output files, see [Usage](https://misiektoja.github.io/spotify_monitor/usage/).

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
