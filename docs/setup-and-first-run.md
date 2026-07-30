# Setup & First Run

<a id="new-here-run-the-setup-wizard"></a>
## Run the setup wizard

This page assumes Spotify Monitor is already installed (see [Installation](installation.md)). It walks through the interactive setup wizard then your first monitoring run. If you opened this page first, choose [PyPI](installation.md#install-from-pypi), the [manual Python script](installation.md#manual-installation), the [Docker image](installation.md#docker-image) or [Docker Compose](installation.md#docker-compose), finish that method's steps then return here.

Then use the regular interactive setup wizard for Friend Activity monitoring. It asks who to monitor, how to connect to Spotify and which alerts to enable. You can review and change your answers before saving. Regular settings go in `spotify_monitor.conf`. Private values such as login cookies and webhook URLs go in `.env`.

Both setup wizards explain at the beginning that Enter accepts the shown default and Ctrl+C cancels setup.

For a local install, the wizard can check the setup and start monitoring immediately.

Use the tab that matches how you installed the tool. Copy and run only the commands in that tab.

=== "PyPI"

    ```sh
    spotify_monitor --setup
    ```

=== "Manual Python script on macOS or Linux"

    ```sh
    python3 spotify_monitor.py --setup
    ```

=== "Manual Python script on Windows"

    ```powershell
    python spotify_monitor.py --setup
    ```

=== "Docker image on macOS or Windows"

    ```sh
    docker run --rm --pull=always -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --setup
    ```

=== "Docker image on Linux"

    ```sh
    docker run --rm --pull=always -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --setup
    ```

=== "Docker Compose"

    Run setup from the directory used during installation. You do not need to download `docker-compose.yml` again.

    On a native Linux container engine, run these shell commands in the same terminal immediately before setup unless the variables are already set there or you saved the numeric values in the Compose `.env` file during installation. For permanent project values, use the numeric `.env` form under [Install with Docker Compose](installation.md#docker-compose). Docker-compatible runtimes on macOS and Windows should skip this export block.

    ```sh
    export SPOTIFY_MONITOR_UID="$(id -u)"
    export SPOTIFY_MONITOR_GID="$(id -g)"
    ```

    Then run setup by itself:

    ```sh
    docker compose run --rm --pull=always spotify_monitor --setup
    ```

Run interactive setup commands by themselves instead of including them in a multi-command paste.

### Set up Last.fm scrobble health instead

Spotify's six-month reauthorization requirement can disconnect Spotify Scrobbling. Last.fm currently shows only a website banner and sends no email warning, so the problem can remain unnoticed when someone rarely opens the website. Use the focused wizard to configure independent console, email or webhook alerts:

```sh
spotify_monitor --setup-scrobble-health
```

The focused wizard selects scrobble health as the saved mode. It asks for the Last.fm username and API key, links to [Last.fm API account management](https://www.last.fm/api/accounts) and guides you through a user-owned app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard). The app owner needs Spotify Premium in Development Mode. Create or open an app, add the recommended `http://127.0.0.1:8888/callback` redirect URI, select Web API in the API/SDKs section and save the app before copying its Client ID. The wizard uses this redirect automatically instead of asking you to choose one. A Client Secret is not needed. Spotify Monitor requests only `user-read-recently-played` through PKCE, opens or prints the authorization URL then asks you to paste the complete redirected URL from the browser address bar. The redirect page may fail to load because Spotify Monitor does not need to run a callback web server.

Authorize the Spotify account whose completed plays should be checked. A separate Spotify account is not required. If that account is different from the app owner, add it under the app's User Management first. See Spotify's [app creation guide](https://developer.spotify.com/documentation/web-api/concepts/apps) and [PKCE guide](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow) for the corresponding Dashboard screens.

The wizard offers email or webhook alerts only for outages, recovery and operational errors. It defaults to five consecutive missing completed plays plus a 20 minute dead period. Duration prompts show seconds plus a readable equivalent such as `120s - 2m`. Enter seconds directly or add `s` for seconds, `m` for minutes, `h` for hours or `d` for days. Examples include `120`, `120s`, `2m`, `1h` and `1d`. Use the regular `--setup` wizard instead for Friend Activity monitoring.

Like regular setup, the focused wizard lets you review or change each section before saving. It defaults to `spotify_monitor_scrobble_health.conf` plus `.env.scrobble_health` so its settings and private values do not replace the Friend Activity files. Pass `--config-file` or `--env-file` to choose another destination. With complete local authentication it can run the focused Doctor checks then start monitoring immediately. If authentication remains incomplete, it prints the exact authentication command before the Doctor and monitoring commands. Once monitoring starts, the console prints the first check and its result with the same timestamp separator used by Friend Activity. Later routine results appear with `--verbose` while outages, recoveries and errors remain visible normally.

To enter or replace only `LASTFM_API_KEY` through a hidden prompt, run `spotify_monitor --set-lastfm-credentials`. It saves only the API key in `.env.scrobble_health` by default because scrobble health does not need the Last.fm shared secret.

To grant access again after the Spotify authorization expires or is revoked, run:

```sh
spotify_monitor --authorize-scrobble-health
```

The command reuses the saved Client ID and redirect URI then replaces only `SPOTIFY_SCROBBLE_REFRESH_TOKEN` in `.env.scrobble_health`. It also prints the matching Doctor and monitoring commands. Spotify refresh tokens expire after six months, so this reauthorization is separate from reconnecting Spotify Scrobbling on Last.fm when the monitor detects an outage.

Saved files are optional. For a one-off or externally managed run, select `--monitor-mode scrobble_health` then provide `--lastfm-username`, `--lastfm-api-key`, `--scrobble-client-id` and `--scrobble-refresh-token`. The redirect URI defaults to `http://127.0.0.1:8888/callback` and can be overridden with `--scrobble-redirect-uri`. The same private values can come from environment variables. Private command-line values may remain in shell history or process listings, so process environment variables are safer when persistence is not needed.

For Docker Compose use `docker compose run --rm spotify_monitor --setup-scrobble-health`. For a direct Docker image replace `--setup` in the matching command above with `--setup-scrobble-health`.

The macOS shell and Windows PowerShell examples use `${PWD}`. In Windows Command Prompt replace `${PWD}` with `%cd%`. Windows hosts must use Linux containers. The `:z` suffix is for hosts that use SELinux. If your Docker-compatible runtime reports that it is invalid, remove only `:z`.

In this documentation, a **target** is the Spotify user whose activity you want to monitor. The **monitoring account** is the Spotify account represented by your saved login cookie or client credentials. The monitoring account must follow the target. They are normally different accounts.

The wizard recommends importing the monitoring account's saved Firefox login. On macOS and Linux it can also import from Chrome, Brave or Chromium. Those three browsers require the optional `pycookiecheat` package. If it is missing, the wizard can install it in a local Python installation.

Both wizards display the detected installation method plus the selected configuration and dotenv destinations before the first prompt. They detect PyPI, a downloaded script, Docker or Docker Compose then print matching commands with paths formatted for the current operating system.

Container setup destinations must stay inside `/data`. That directory is the current host directory mounted into the temporary setup container, so files written there survive `--rm`. The wizard rejects paths such as `/tmp/spotify_monitor.conf` instead of printing a command for a different file.

After saving authentication, the wizard checks whether the monitoring account follows the target. It offers to follow the target only when needed and sends the follow request only after you confirm.

For Docker or Docker Compose, choose **Import from Firefox after setup**. The wizard asks whether Docker runs on macOS, standard Linux, Linux with Snap, Linux with Flatpak, Windows PowerShell or Windows Command Prompt. It then prints the matching command to mount the signed-in host profile read-only once and save `SP_DC_COOKIE` in the host `.env` file. Windows commands use the Firefox profile under `%APPDATA%\Mozilla\Firefox`. Use [manual extraction](configuration.md#manual-cookie-extraction) only when that mount is unavailable.

If the selected configuration contains `TARGET_USER_URI_ID`, running Spotify Monitor without a target starts that saved user. If no target is saved, an interactive no-argument run shows setup guidance and offers the setup wizard.

If the selected `.env` file already contains a saved `SP_DC_COOKIE`, container setup offers to keep it. Otherwise Firefox import remains the default. Setup does not run Doctor while that import is pending. It finishes with the host-specific import command followed by the Doctor and monitoring commands.

<a id="before-you-start"></a>
## Before you start

Spotify only shows a person's listening activity when both of these conditions are met:

1. The Spotify account used by Spotify Monitor follows the person you want to monitor.
2. That person has enabled listening activity sharing in Spotify.

The setup wizard checks whether the monitoring account follows the target. It can send the follow request after you confirm. To follow manually, open the target's profile in the Spotify desktop or mobile app. You can use **Share** > **Copy link to profile** and paste the complete link into the wizard. You do not need to extract the user ID. See [Following the Monitored User](configuration.md#following-the-monitored-user).

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
| Most securely enter or replace a manually extracted `SP_DC_COOKIE` | Run `spotify_monitor --set-sp-dc` and enter `sp_dc` at the hidden prompt |
| Set up webhook alerts | Run the setup wizard and choose webhook alerts |
| Save a new webhook URL | Run `spotify_monitor --set-webhook-url` |
| Send a test webhook | Run `spotify_monitor --send-test-webhook` |

<a id="run-individual-commands"></a>
## Run Individual Commands

The examples below use PyPI. For a manual script, replace `spotify_monitor` with `python3 spotify_monitor.py` on macOS or Linux. Use `python spotify_monitor.py` on Windows. Docker users should copy the matching prefix under [Command Format by Installation Method](usage.md#command-format).

To configure authentication without the wizard, first open [Spotify Web Player](https://open.spotify.com/) in Firefox and sign in to the monitoring account. Then import that browser login:

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

If browser import is not available, use the [manual cookie extraction](configuration.md#manual-cookie-extraction) fallback.

For a manually extracted cookie, `--set-sp-dc` is the recommended and most secure entry method. The command reads `sp_dc` through a hidden prompt, so the value does not appear on screen or in the command line. It validates the cookie with Spotify before updating only `SP_DC_COOKIE`. If validation fails, it does not change the `.env` file. Replacing an existing cookie requires confirmation. Directly adding `SP_DC_COOKIE` to `.env` remains supported.

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

`--set-sp-dc` does not accept the cookie as a command-line value. Use `--env-file PATH` to select another `.env` file. Add `--config-file PATH` when its success output should preserve a nondefault configuration path. `--env-file none` is invalid because this command must save the validated cookie. The older `-u` and `--spotify-dc-cookie` options still work, but their values may appear in shell history or process listings.

A webhook URL is the private address used to deliver notifications. Treat it like a password because anyone who has it may be able to post through it. Follow the [webhook setup steps](configuration.md#webhook-settings) then save the link with the command that matches your installation:

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

`docker compose up --no-log-prefix` uses the default `/data/spotify_monitor.conf` and `/data/.env` paths declared in `docker-compose.yml`. If setup saved either file under another `/data` path, use the explicit `docker compose run` command printed by setup.

For a direct `docker run` command on macOS or Windows PowerShell:

```sh
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --config-file /data/spotify_monitor.conf --env-file /data/.env
docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest "https://open.spotify.com/user/spotify_user_uri_id" --config-file /data/spotify_monitor.conf --env-file /data/.env
```

These commands work in macOS shells and Windows PowerShell with a Docker-compatible runtime that provides the `docker` CLI. In Windows Command Prompt replace `${PWD}` with `%cd%`. On a native Linux container engine replace `${PWD}` with `$PWD` and add `--user "$(id -u):$(id -g)"` immediately after `--init`.

To see all supported command-line arguments and flags:

```sh
spotify_monitor --help
```

<a id="next-step"></a>
## Next Step

With authentication saved and a first run working, continue to [Configuration](configuration.md) for targets, Spotify login, SMTP and secrets. See [Usage](usage.md) for command formats, monitoring, container operation, notifications, playback and output.
