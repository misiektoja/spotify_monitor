# Quick Start

<a id="new-here-run-the-setup-wizard"></a>
## New here? Run the setup wizard

First complete one method on the [Installation](installation.md) page. The fastest way to configure that installation is the interactive setup wizard. It asks who to monitor, how to connect to Spotify and whether you want alerts by email or webhook. Before saving, you can review the summary and edit any setup section without losing the other answers. It then saves a ready-to-run configuration while private values stay in `.env`.

For local installs the wizard can also run the doctor check and start monitoring immediately.

Before running the Docker Compose setup command on Linux, export `SPOTIFY_MONITOR_UID="$(id -u)"` and `SPOTIFY_MONITOR_GID="$(id -g)"` as shown under [Install with Docker Compose](installation.md#docker-compose).

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

Docker Desktop examples use `${PWD}` in macOS shells and Windows PowerShell. In Windows Command Prompt replace `${PWD}` with `%cd%`.

The wizard asks for one Spotify target, recommends Firefox-based `sp_dc` import and lets you choose email alerts, webhook alerts or both. On macOS and Linux it offers Chrome, Brave and Chromium as a separate cookie import path. If the optional `pycookiecheat` package is missing, setup can install it into the active Python environment before continuing.

The wizard detects PyPI, downloaded-script, Docker and Docker Compose installations then prints matching commands. Local commands reuse the active Python executable. Config and dotenv paths are quoted for the active operating system.

It writes regular settings to `spotify_monitor.conf` while private values go only to `.env`.

After authentication is saved the wizard checks whether the configured Spotify account follows the target. It offers to follow only when needed and changes the account only after explicit confirmation.

For a local installation, the easiest login method is automatic Firefox import. For Docker or Docker Compose, you will normally enter the `sp_dc` Spotify login cookie manually. The [manual extraction steps](configuration.md#manual-cookie-extraction) explain exactly where to find it.

When the discovered configuration contains a persisted `TARGET_USER_URI_ID`, running Spotify Monitor without a positional target starts that saved target. If no target has been saved, no-argument startup shows the quick-start guidance and offers the setup wizard in an interactive terminal.

For a local PyPI or downloaded-script installation, Firefox browser import remains the recommended authentication path and the default setup choice. For Docker and Docker Compose, manual `sp_dc` entry is recommended because the default container cannot access an unmounted host browser profile. If the selected dotenv file already contains a non-placeholder `SP_DC_COOKIE`, container setup offers to retain it as the default choice.

<a id="before-you-start"></a>
## Before you start

Spotify only shows a person's listening activity when both of these conditions are met:

1. The Spotify account used by Spotify Monitor follows the person you want to monitor.
2. That person has enabled listening activity sharing in Spotify.

The setup wizard (`spotify_monitor --setup`) checks whether the configured Spotify account follows the target. It offers to follow only when needed and changes the account only after explicit confirmation. If you want to do it manually, open the person's profile in the Spotify desktop or mobile app then use **Share** > **Copy link to profile**. You can paste the complete profile link into the setup wizard. You do not need to extract the user ID yourself. See [Following the Monitored User](configuration.md#following-the-monitored-user).

<a id="not-sure-which-command-you-need"></a>
## Not sure which command you need?

| I want to... | Run this |
| --- | --- |
| Set up Spotify Monitor for the first time | Use the setup command for your installation above |
| Start monitoring with existing authentication | `spotify_monitor TARGET`, where `TARGET` is a raw ID, `spotify:user:` URI or profile URL |
| Start the target saved in `TARGET_USER_URI_ID` | `spotify_monitor --config-file spotify_monitor.conf` or `docker compose up --no-log-prefix` |
| Check authentication, connectivity and one target | `spotify_monitor --doctor TARGET` |
| List Spotify friends visible to the configured account | `spotify_monitor --list-friends` |
| Import a Spotify login from Firefox | Open [Spotify Web Player](https://open.spotify.com/) in Firefox, sign in then run `spotify_monitor --import-browser-cookie --browser firefox` |
| Safely set or replace `SP_DC_COOKIE` | Run `spotify_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Set up webhook alerts | Run the setup wizard and choose webhook alerts |
| Save a new webhook URL | Run `spotify_monitor --set-webhook-url` |
| Send a test webhook | Run `spotify_monitor --send-test-webhook` |

<a id="manual-commands"></a>
## Run Individual Commands

The shorter examples in this section use a PyPI installation. For a manual script replace `spotify_monitor` with `python3 spotify_monitor.py` on macOS or Linux and `python spotify_monitor.py` on Windows. Docker and Docker Compose use the command prefixes under [Command Format by Installation Method](usage.md#command-format). Commands printed by Spotify Monitor detect the active installation automatically.

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
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --set-sp-dc --env-file /data/.env

# Docker image on Linux
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --set-sp-dc --env-file /data/.env
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
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --set-webhook-url --env-file /data/.env

# Docker image on Linux
docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --set-webhook-url --env-file /data/.env
```

The link is entered through a hidden prompt and saved as `WEBHOOK_URL` in `.env`. This command only saves the link. It does not turn on webhook alerts or send a message. See [Webhook Settings](configuration.md#webhook-settings) to choose your alerts then run `spotify_monitor --send-test-webhook` to test them.

Before monitoring, [follow the Spotify user](configuration.md#following-the-monitored-user) from the account represented by your configured credentials.

Start monitoring with a raw user ID, Spotify user URI or profile URL. These PyPI examples also show how a saved `TARGET_USER_URI_ID` removes the positional target:

```sh
spotify_monitor <spotify_user_uri_id>
spotify_monitor "https://open.spotify.com/user/spotify_user_uri_id"
spotify_monitor --config-file spotify_monitor.conf
```

For a [manual script](installation.md#manual-installation):

```sh
python3 spotify_monitor.py <spotify_user_uri_id>
```

For Docker Compose, use `/data` paths inside the container. If the target was saved by setup use the first command. Otherwise use the second form with any supported target:

```sh
docker compose up --no-log-prefix
docker compose run --rm spotify_monitor "https://open.spotify.com/user/spotify_user_uri_id" --config-file /data/spotify_monitor.conf --env-file /data/.env
```

For a direct Docker image on Docker Desktop:

```sh
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --config-file /data/spotify_monitor.conf --env-file /data/.env
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest "https://open.spotify.com/user/spotify_user_uri_id" --config-file /data/spotify_monitor.conf --env-file /data/.env
```

These Docker Desktop commands work in macOS shells and Windows PowerShell. In Windows Command Prompt replace `${PWD}` with `%cd%`. On Linux replace `${PWD}` with `$PWD` and add `--user "$(id -u):$(id -g)"` immediately after `--init`.

To see all supported command-line arguments and flags:

```sh
spotify_monitor --help
```
