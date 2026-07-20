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

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_skipped.png" alt="spotify_monitor_skipped" width="90%"/>
</p>

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

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor.png" alt="spotify_monitor_screenshot" width="90%"/>
</p>

🎵 For even better real-time tracking with pause/resume detection, track progress indicators, enhanced stats and offline mode support, check out [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor) - it is much easier to set up, simply ask your friend to connect Last.fm to Spotify (Last.fm Settings → Applications → Connect Spotify Scrobbling) and you're ready to go!

✨ If you're interested in tracking changes to Spotify users' profiles including their playlists, take a look at another tool I've developed: [spotify_profile_monitor](https://github.com/misiektoja/spotify_profile_monitor).

🛠️ If you're looking for debug tools to get Spotify Web Player access tokens and extract secret keys: [click here](https://misiektoja.github.io/spotify_monitor/debugging/#debugging-tools)

<a id="documentation"></a>
## Documentation

Full documentation is available at **[misiektoja.github.io/spotify_monitor](https://misiektoja.github.io/spotify_monitor/)**:

- [Installation](https://misiektoja.github.io/spotify_monitor/installation/) - PyPI, optional extras and manual installation
- [Quick Start](https://misiektoja.github.io/spotify_monitor/quick-start/) - setup wizard, authentication and first run
- [Configuration](https://misiektoja.github.io/spotify_monitor/configuration/) - Spotify login, targets, SMTP, webhooks and secrets
- [Usage](https://misiektoja.github.io/spotify_monitor/usage/) - Docker, monitoring, notifications, playback and output
- [Troubleshooting](https://misiektoja.github.io/spotify_monitor/troubleshooting/) - the `--doctor` self-check and logging levels
- [Debugging Tools](https://misiektoja.github.io/spotify_monitor/debugging/) - TOTP token testing and secret extraction

<a id="quick-start"></a>
## Quick Start

<a id="before-you-start"></a>
### Before you start

Spotify only shows a person's listening activity when both of these conditions are met:

1. The Spotify account used by Spotify Monitor follows the person you want to monitor.
2. That person has enabled listening activity sharing in Spotify.

Open the person's profile in the Spotify desktop or mobile app then use **Share** > **Copy link to profile**. You can paste the complete profile link into the setup wizard. You do not need to extract the user ID yourself. See [Following the Monitored User](https://misiektoja.github.io/spotify_monitor/configuration/#following-the-monitored-user) if the doctor later reports that the person is not visible.

For a local installation, the easiest login method is automatic Firefox import. For Docker or Docker Compose, you will normally enter the `sp_dc` Spotify login cookie manually. The [manual extraction steps](https://misiektoja.github.io/spotify_monitor/configuration/#manual-cookie-extraction) explain exactly where to find it.

<a id="new-here-run-the-setup-wizard"></a>
### New here? Run the setup wizard

The fastest way to get started is the interactive setup wizard. It asks a few simple questions about who to monitor, how to connect to Spotify and whether you want alerts by email or webhook. Before saving, you can review the summary and edit any setup section without losing the other answers. Discarding all answers requires a separate confirmation. It then saves a ready-to-run configuration for you while private values stay in `.env`. For local installs the wizard can also check the setup and start monitoring immediately.

Before running the Docker Compose setup command on Linux, export `SPOTIFY_MONITOR_UID="$(id -u)"` and `SPOTIFY_MONITOR_GID="$(id -g)"` as shown in the [Docker section](https://misiektoja.github.io/spotify_monitor/usage/#main-application-docker-image).

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
docker run --rm -it --init -v "$PWD:/data:z" misiektoja/spotify-monitor --setup

# Docker image on Linux
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor --setup
```

The wizard asks for one Spotify target, recommends Firefox-based `sp_dc` import and lets you choose email alerts, webhook alerts or both. On macOS and Linux it offers Chrome, Brave and Chromium as a separate authentication path. If the optional `pycookiecheat` package is missing, setup can install it into the active Python environment before continuing. It writes regular settings to `spotify_monitor.conf` while private values go only to `.env`. It also detects whether you use PyPI, the downloaded script or Docker then shows commands that match your installation. Local next-step commands use the current Python interpreter and quote paths for the active operating system.

When the discovered configuration contains a persisted `TARGET_USER_URI_ID`, running Spotify Monitor without a positional target starts that saved target. If no target has been saved, no-argument startup shows the quick-start guidance and offers the setup wizard in an interactive terminal.

For a local PyPI or downloaded-script installation, Firefox browser import remains the recommended authentication path and the default setup choice. For Docker and Docker Compose, manual `sp_dc` entry is recommended because the default container cannot access an unmounted host browser profile. If the selected dotenv file already contains a non-placeholder `SP_DC_COOKIE`, container setup offers to retain it as the default choice.

<a id="not-sure-which-command-you-need"></a>
### Not sure which command you need?

| I want to... | Run this |
| --- | --- |
| Set up Spotify Monitor for the first time | Use the setup command for your installation above |
| Start monitoring with existing authentication | `spotify_monitor <spotify_user_uri_id>` |
| Check authentication, connectivity and one target | `spotify_monitor --doctor <spotify_user_uri_id>` |
| List Spotify friends visible to the configured account | `spotify_monitor --list-friends` |
| Import a Spotify login from Firefox | Open [Spotify Web Player](https://open.spotify.com/) in Firefox, sign in then run `spotify_monitor --import-browser-cookie --browser firefox` |
| Safely set or replace `SP_DC_COOKIE` | Run `spotify_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Set up webhook alerts | Run the setup wizard and choose webhook alerts |
| Save a new webhook URL | Run `spotify_monitor --set-webhook-url` |
| Send a test webhook | Run `spotify_monitor --send-test-webhook` |

<a id="manual-commands"></a>
### Manual commands

Manual script examples use `python3` on macOS and Linux. On Windows use `python` in place of `python3`. Commands printed by Spotify Monitor detect the current interpreter automatically.

If you prefer to configure authentication without the wizard, first open [Spotify Web Player](https://open.spotify.com/) in Firefox and sign in to the Spotify account you will use for monitoring. Then return to the terminal and import that browser login:

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

If browser import is not available, use the [manual cookie extraction](https://misiektoja.github.io/spotify_monitor/configuration/#manual-cookie-extraction) fallback.

The safe standalone replacement command reads `sp_dc` through a hidden prompt. It validates the cookie with Spotify before atomically updating only `SP_DC_COOKIE`. If validation fails, the dotenv file is left byte-for-byte unchanged. Existing cookie replacement always requires confirmation.

```sh
# PyPI install
spotify_monitor --set-sp-dc

# Manual Python script
python3 spotify_monitor.py --set-sp-dc

# Docker Compose
docker compose run --rm spotify_monitor --set-sp-dc --env-file /data/.env

# Docker image on macOS or Windows
docker run --rm -it --init -v "$PWD:/data:z" misiektoja/spotify-monitor --set-sp-dc --env-file /data/.env

# Docker image on Linux
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor --set-sp-dc --env-file /data/.env
```

`--set-sp-dc` never accepts the cookie as a command-line value. Use `--env-file PATH` to select a different dotenv destination. `--env-file none` is rejected because the command must persist the validated cookie. The existing `-u` and `--spotify-dc-cookie` options remain available for backward compatibility, but command-line secrets may be visible in shell history or process listings.

A webhook URL is a private link that receives notifications. Treat it like a password because anyone who has it may be able to post through it. Follow the [webhook setup steps](https://misiektoja.github.io/spotify_monitor/configuration/#webhook-settings) then save the link with the command that matches your installation:

```sh
# PyPI install
spotify_monitor --set-webhook-url

# Manual Python script
python3 spotify_monitor.py --set-webhook-url

# Docker Compose
docker compose run --rm spotify_monitor --set-webhook-url --env-file /data/.env

# Docker image on macOS or Windows
docker run --rm -it --init -v "$PWD:/data:z" misiektoja/spotify-monitor --set-webhook-url --env-file /data/.env

# Docker image on Linux
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor --set-webhook-url --env-file /data/.env
```

The link is entered through a hidden prompt and saved as `WEBHOOK_URL` in `.env`. This command only saves the link. It does not turn on webhook alerts or send a message. See [Webhook Settings](https://misiektoja.github.io/spotify_monitor/configuration/#webhook-settings) to choose your alerts then run `spotify_monitor --send-test-webhook` to test them.

Before monitoring, [follow the Spotify user](https://misiektoja.github.io/spotify_monitor/configuration/#following-the-monitored-user) from the account represented by your configured credentials.

Start monitoring with a raw user ID, Spotify user URI or profile URL. A target saved by the wizard does not need to be repeated:

```sh
spotify_monitor <spotify_user_uri_id>
spotify_monitor "https://open.spotify.com/user/spotify_user_uri_id"
spotify_monitor --config-file spotify_monitor.conf
```

Or if you installed [manually](https://misiektoja.github.io/spotify_monitor/installation/#manual-installation):

```sh
python3 spotify_monitor.py <spotify_user_uri_id>
```

To see all supported command-line arguments and flags:

```sh
spotify_monitor --help
```

<a id="webhook-settings"></a>
## Webhook Settings

Spotify Monitor can send activity alerts through Discord or the native [ntfy publish API](https://docs.ntfy.sh/publish/). You can use webhook alerts instead of email or use both. The easiest option is to run `spotify_monitor --setup`, choose webhook alerts then select Discord or ntfy.

`WEBHOOK_PROVIDER` selects the request format. It defaults to `"discord"` so existing configurations keep working.

<a id="discord"></a>
### Discord

If you are new to Discord, follow these steps to get your private webhook URL:

1. Open your Discord server and choose the channel that should receive the alerts.
2. Click **Edit Channel** then open **Integrations** > **Webhooks**.
3. Click **New Webhook**, choose a name if you want then click **Copy Webhook URL**.
4. Return to the terminal and run:

```sh
spotify_monitor --set-webhook-url
```

Paste the copied link at the hidden prompt. Spotify Monitor saves it in `.env` so it does not appear in your command history. Treat this link like a password because anyone who has it can post through it.

Keep the default provider in `spotify_monitor.conf`:

```ini
WEBHOOK_PROVIDER = "discord"
```

<a id="ntfy"></a>
### ntfy

For ntfy.sh or a self-hosted ntfy server:

1. Choose a hard-to-guess topic such as `spotify-monitor-long-random-value`.
2. Use the complete topic URL such as `https://ntfy.sh/spotify-monitor-long-random-value`.
3. Set the provider in `spotify_monitor.conf`:

```ini
WEBHOOK_PROVIDER = "ntfy"
```

4. Save the topic URL privately:

```sh
spotify_monitor --set-webhook-url
```

Spotify Monitor sends the alert body as a native UTF-8 ntfy message and sends the alert subject as its title. Query parameters already present in the topic URL are preserved. This allows the ntfy [`auth` query parameter](https://docs.ntfy.sh/publish/#authentication) when a protected topic needs authentication.

Playlist and album artwork is enabled by default for supported ntfy alerts. To keep ntfy alerts text-only, disable images in `spotify_monitor.conf`:

```ini
NTFY_IMAGES = False
```

Active and inactive alerts use playlist artwork when available then fall back to album artwork. Tracked-song, every-song and loop alerts use album artwork. Error alerts and `--send-test-webhook` remain text-only. Spotify Monitor accepts only Spotify HTTPS CDN image URLs, limits downloads to 5 MiB and rejects oversized decoded images before preparing each attachment in memory. PyPI, requirements-file and Docker installs include Pillow. Manual single-file users who install dependencies individually must include Pillow. If image preparation fails, the alert is sent as text. If the attachment upload fails, the alert is retried once as text so artwork cannot suppress the notification. Self-hosted ntfy servers must allow attachments.

For a protected topic, the setup wizard can collect an ntfy access token through a hidden prompt. It saves the token in `.env` without displaying it. For manual setup, add the token to `.env`:

```ini
NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

Spotify Monitor sends this value as `Authorization: Bearer <token>`. `NTFY_ACCESS_TOKEN` takes precedence over an `Authorization` entry in `WEBHOOK_HEADERS`.

For compatibility with other advanced webhook integrations, static custom headers are also supported in `spotify_monitor.conf`:

```ini
WEBHOOK_HEADERS = {
    "Authorization": "Bearer tk_your_ntfy_access_token",
}
```

The dictionary applies to Discord and ntfy requests. For ntfy, Spotify Monitor sets `text/plain` for text alerts and `image/jpeg` for artwork attachments. Prefer `NTFY_ACCESS_TOKEN` in `.env` for Bearer authentication because a token inside `WEBHOOK_HEADERS` is easier to expose or commit accidentally. Basic authentication remains available through a custom `Authorization` header. Header names and values are validated before any request is sent.

Topics on the public ntfy.sh service are public unless protected through an account reservation. Treat an unprotected topic name like a password and do not reuse the example topic above.

If you used the setup wizard, it saves your alert choices automatically. For the recommended alerts, the saved settings look like this:

```ini
WEBHOOK_ENABLED = True
WEBHOOK_PROVIDER = "discord"  # Use "ntfy" for an ntfy topic URL
WEBHOOK_ACTIVE_NOTIFICATION = True
WEBHOOK_INACTIVE_NOTIFICATION = True
WEBHOOK_ERROR_NOTIFICATION = True
```

This sends an alert when the user becomes active, becomes inactive or when monitoring has a problem. See [Webhook Notifications](https://misiektoja.github.io/spotify_monitor/usage/#webhook-notifications) if you want different alerts.

Send one test webhook without starting monitoring:

```sh
spotify_monitor --send-test-webhook
```

Email and webhooks work separately. If one fails, Spotify Monitor can still send the other. Discord messages cannot trigger `@everyone` or `@here` mentions.

If the webhook service temporarily refuses a message, Spotify Monitor tries once more and waits at most five seconds. Spotify monitoring continues normally and its retry behavior is unchanged.

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
