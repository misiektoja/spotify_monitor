# Quick Start

<a id="before-you-start"></a>
## Before you start

Spotify only shows a person's listening activity when both of these conditions are met:

1. The Spotify account used by Spotify Monitor follows the person you want to monitor.
2. That person has enabled listening activity sharing in Spotify.

Open the person's profile in the Spotify desktop or mobile app then use **Share** > **Copy link to profile**. You can paste the complete profile link into the setup wizard. You do not need to extract the user ID yourself. See [Following the Monitored User](configuration.md#following-the-monitored-user) if the doctor later reports that the person is not visible.

For a local installation, the easiest login method is automatic Firefox import. For Docker or Docker Compose, you will normally enter the `sp_dc` Spotify login cookie manually. The [manual extraction steps](configuration.md#manual-cookie-extraction) explain exactly where to find it.

<a id="new-here-run-the-setup-wizard"></a>
## New here? Run the setup wizard

The fastest way to get started is the interactive setup wizard. It asks a few simple questions about who to monitor, how to connect to Spotify and whether you want alerts by email or webhook. Before saving, you can review the summary and edit any setup section without losing the other answers. Discarding all answers requires a separate confirmation. It then saves a ready-to-run configuration for you while private values stay in `.env`. For local installs the wizard can also check the setup and start monitoring immediately.

Before running the Docker Compose setup command on Linux, export `SPOTIFY_MONITOR_UID="$(id -u)"` and `SPOTIFY_MONITOR_GID="$(id -g)"` as shown in the [Docker section](usage.md#main-application-docker-image).

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
## Not sure which command you need?

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
## Manual commands

Manual script examples use `python3` on macOS and Linux. On Windows use `python` in place of `python3`. Commands printed by Spotify Monitor detect the current interpreter automatically.

If you prefer to configure authentication without the wizard, first open [Spotify Web Player](https://open.spotify.com/) in Firefox and sign in to the Spotify account you will use for monitoring. Then return to the terminal and import that browser login:

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

If browser import is not available, use the [manual cookie extraction](configuration.md#manual-cookie-extraction) fallback.

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

A webhook URL is a private link that receives notifications. Treat it like a password because anyone who has it may be able to post through it. Follow the [webhook setup steps](configuration.md#webhook-settings) then save the link with the command that matches your installation:

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

The link is entered through a hidden prompt and saved as `WEBHOOK_URL` in `.env`. This command only saves the link. It does not turn on webhook alerts or send a message. See [Webhook Settings](configuration.md#webhook-settings) to choose your alerts then run `spotify_monitor --send-test-webhook` to test them.

Before monitoring, [follow the Spotify user](configuration.md#following-the-monitored-user) from the account represented by your configured credentials.

Start monitoring with a raw user ID, Spotify user URI or profile URL. A target saved by the wizard does not need to be repeated:

```sh
spotify_monitor <spotify_user_uri_id>
spotify_monitor "https://open.spotify.com/user/spotify_user_uri_id"
spotify_monitor --config-file spotify_monitor.conf
```

Or if you installed [manually](installation.md#manual-installation):

```sh
python3 spotify_monitor.py <spotify_user_uri_id>
```

To see all supported command-line arguments and flags:

```sh
spotify_monitor --help
```
