# Configuration

Examples on this page use the PyPI command `spotify_monitor`. Manual script, Docker Compose and direct Docker users should keep the shown options and use the matching prefix under [Command Format by Installation Method](usage.md#command-format). Container file paths must point into `/data`.

<a id="configuration-file"></a>
## Configuration File

You can pass most settings as command-line options or save them in a configuration file for later runs.

The easiest way to create this file is `spotify_monitor --setup`. The wizard checks the settings before saving. If you approve replacement of an existing file, it saves a timestamped backup first.

To edit every available setting yourself, generate a default configuration file:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
spotify_monitor --generate-config > spotify_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
spotify_monitor --generate-config spotify_monitor.conf
```

> **Windows PowerShell:** Pass the filename directly to `--generate-config`. PowerShell redirection can write UTF-16, which Spotify Monitor rejects with a "null bytes" error.

When you provide a filename, Spotify Monitor checks that the new configuration can be loaded then saves it as UTF-8. If the file already exists, Spotify Monitor creates a timestamped backup before replacing it.

Open `spotify_monitor.conf` in a text editor and change the settings you need. The file contains a short explanation above each setting.

If the same setting appears in more than one place, the item later in this list wins:

1. Built-in defaults
2. The discovered or explicitly selected configuration file
3. Secret environment variables
4. Values from the selected `.env` file
5. Command-line options

The `.env` layer applies only to supported private keys such as `SP_DC_COOKIE`, `SMTP_PASSWORD` and `WEBHOOK_URL`. A target written directly after the command overrides `TARGET_USER_URI_ID`. Use `--config-file PATH` and `--env-file PATH` if you do not want automatic file discovery. See [Storing Secrets](#storing-secrets) for the search rules and supported keys.

You may set `TARGET_USER_URI_ID` to a raw user ID, Spotify user URI or profile URL. A positional command-line target takes precedence over this configured value. With a configured target you can start monitoring with:

```sh
spotify_monitor --config-file spotify_monitor.conf
```

A Spotify developer app is not required. Cookie or client mode authenticates Friend Activity. The anonymous web-player backend supplies track and public playlist details. Existing working OAuth app credentials remain available as an optional legacy metadata path.

<a id="spotify-access-token-source"></a>
## Spotify Access Token Source

Spotify Monitor uses either the `cookie` or `client` token source for Friend Activity.

Track details and public playlist details normally come from Spotify's anonymous web-player service. If [Spotify OAuth App](#spotify-oauth-app) credentials are present, Spotify Monitor tries that optional legacy API first (but it is not mandatory).

The token source method can be configured via the `TOKEN_SOURCE` configuration option or the `--token-source` flag.

**Recommended: `cookie`**

Uses an `sp_dc` browser cookie to request a Spotify access token. Use this method unless you specifically need advanced client mode.

**Alternative: `client`**

Uses login data captured from the Spotify desktop client. Setup requires an intercepting proxy and a saved Protobuf request body. This method is intended for advanced users.

If no method is specified, the tool defaults to the `cookie` method.

Spotify Monitor creates a suitable user agent automatically for the selected token source. A user agent is text that identifies the application making a request. Leave `USER_AGENT` empty unless you have a specific reason to override it.

Friend Activity is not available through Spotify's supported public Web API. Spotify can change or restrict the private endpoints used by this tool. Use a separate Spotify account if losing access to your main account would be unacceptable.

<a id="spotify-sp_dc-cookie"></a>
### Spotify sp_dc Cookie

This is the default method used to obtain a Spotify access token.

For a local PyPI or downloaded-script installation, import a Firefox login. This works on macOS, Linux and Windows without an optional package. Docker and Docker Compose also support Firefox import through a one-time read-only host profile mount. See [Import Firefox into Container Authentication](usage.md#import-firefox-into-container-authentication) for Linux, Snap, Flatpak and macOS commands.

Before importing, open [Spotify Web Player](https://open.spotify.com/) in the browser you want to use and sign in to the Spotify account that follows the user you plan to monitor. Then return to the terminal and run the import command.

<a id="which-browsers-are-supported"></a>
#### Which browsers are supported

The `--browser` flag accepts these values:

| `--browser` | Application it reads | Platforms |
| --- | --- | --- |
| `firefox` (default) | Mozilla Firefox | macOS, Linux, Windows |
| `chrome` | Google Chrome | macOS, Linux |
| `brave` | Brave | macOS, Linux |
| `chromium` | The standalone open-source Chromium browser | macOS, Linux |

**About `chromium`:** Chromium is a separate browser application from Google Chrome. It has its own profiles and cookies. Choose `chromium` only if that is the browser you use. Choose `chrome` for Google Chrome.

**Not currently supported:** Microsoft Edge, Opera, Vivaldi, Arc and other Chromium-based browsers. Each application stores its cookies separately. The [`pycookiecheat`](https://github.com/n8henrie/pycookiecheat) library used by Spotify Monitor supports only the browsers in the table. To import a login, use one of those supported browsers.

On Windows, Chrome 127 and newer prevent external programs from reading these cookies through app-bound encryption. Use Firefox import instead.

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

On Linux, Firefox profiles installed natively, through Snap or through Flatpak are discovered automatically. On every platform, the importer reads `profiles.ini` and normal profile directories. If one usable profile exists it is selected automatically. If several profiles exist an interactive terminal shows a numbered choice. For scripts or other noninteractive runs select one by its friendly name or directory basename:

```sh
spotify_monitor --import-browser-cookie --browser firefox --browser-profile "default-release"
```

For a custom Firefox layout, the advanced `--cookie-file PATH` option points directly to a `cookies.sqlite` database. It overrides automatic profile selection:

```sh
spotify_monitor --import-browser-cookie --browser firefox --cookie-file /path/to/cookies.sqlite
```

By default, import writes only `SP_DC_COOKIE` to `.env` in the current directory. Use `--env-file PATH` to choose another `.env` file. Import does not change a file found only in a parent directory. `--env-file none` is invalid because the imported cookie must be saved.

Before changing `.env`, Spotify Monitor uses the cookie to request a token and read the authenticated friend list. It keeps comments, blank lines and unrelated settings. Replacing an existing value requires confirmation in an interactive terminal or `--force` in a noninteractive run. `--force` does not skip validation.

Chrome, Brave and Chromium import is available on macOS and Linux through the optional browser extra:

```sh
pip install "spotify_monitor[browser]"
spotify_monitor --import-browser-cookie --browser chrome
```

Chromium profiles support `Default` and `Profile *` directories plus friendly names from Local State. Both modern `<profile>/Network/Cookies` and legacy `<profile>/Cookies` databases are recognized.

Chromium-based import does not work inside Docker because the container cannot use the host password service needed to decrypt the cookies. Use Firefox as shown under [Container Operation](usage.md#import-firefox-into-container-authentication). You can also perform a Chromium import with a local PyPI or manual installation.

<a id="manual-cookie-extraction"></a>
#### Manual cookie extraction

Use manual extraction when browser import is unavailable. In containers it is the fallback when a Firefox host profile cannot be mounted. Treat `sp_dc` like a password because it represents a Spotify login session.

Follow these steps:

1. Open [Spotify Web Player](https://open.spotify.com/) and sign in to the Spotify account that follows the person you want to monitor.
2. Open your browser's developer tools. Press `F12` or `Ctrl+Shift+I` on Windows and Linux. Press `Command+Option+I` on macOS.
3. In Firefox, open **Storage** > **Cookies** > `https://open.spotify.com`.
4. In Chrome, Brave or Chromium, open **Application** > **Storage** > **Cookies** > `https://open.spotify.com`.
5. Find the cookie named `sp_dc` and copy only its **Value**. Do not copy the cookie name or the complete table row.
6. Run the `--set-sp-dc` command for your installation and paste the value at the hidden prompt. The value will not appear on the screen.

As an alternative, [Cookie-Editor by cgagnier](https://cookie-editor.com/) can display the `sp_dc` value. Only use a browser extension that you trust because browser extensions can access sensitive login cookies.

The recommended `--set-sp-dc` command validates the cookie with Spotify before changing `.env`. Existing cookie replacement requires confirmation. See the [copy-paste commands](quick-start.md#manual-commands) for PyPI, downloaded-script, Docker Compose and Docker installations.

You can also provide `SP_DC_COOKIE` in these ways:

* Set it as an [environment variable](#storing-secrets), for example `export SP_DC_COOKIE="your_sp_dc_cookie_value"`.
* Add `SP_DC_COOKIE="your_sp_dc_cookie_value"` to an [`.env` file](#storing-secrets) to keep it for later runs.
* Pass it for one run with `-u` or `--spotify-dc-cookie`. This is not recommended because the value may appear in shell history or process listings.
* Store it in the configuration file or source code as a last resort. This is not recommended because it is easier to expose or commit accidentally.

If `sp_dc` expires, Spotify Monitor reports the error in the console. It also sends the error through each enabled notification channel: email, Discord or ntfy. Extract a new cookie and replace the saved value.

If `SP_DC_COOKIE` is in `.env`, a running process on macOS, Linux or Unix can reload it after a `SIGHUP` signal. See [Storing Secrets](#storing-secrets) and [Signal Controls](usage.md#signal-controls-macoslinuxunix).

> **TOTP parameters:** Spotify's web-player token request currently uses v61. Spotify Monitor includes those values in `TOTP_VERSION` and `TOTP_SECRET_CIPHER_BYTES`. If Spotify changes them, use [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/main/debug/spotify_monitor_secret_grabber.py) to read the current values from the web-player bundle and update both settings.

<a id="spotify-desktop-client"></a>
### Spotify Desktop Client

Client mode reuses login data from a real Spotify desktop session. It is an advanced alternative to the `sp_dc` cookie method.

- Run an intercepting proxy of your choice (like [Proxyman](https://proxyman.com) - the trial version is sufficient)

- Enable SSL traffic decryption for `spotify.com` domain
   - in Proxyman: click **Tools → SSL Proxying List → + button → Add Domain → paste `*.spotify.com` → Add**

- Launch the Spotify desktop client, then switch to your intercepting proxy (like Proxyman) and look for POST requests to `https://login5.spotify.com/v3/login`

- If you don't see this request, try following steps (stop once it works):
   - restart the Spotify desktop client
   - log out from the Spotify desktop client and log back in
   - point Spotify at the intercepting proxy directly in its settings, i.e. in **Spotify → Settings → Proxy Settings**, set:
      - **proxy type**: `HTTP`
      - **host**: `127.0.0.1` (IP/FQDN of your proxy, for Proxyman use the IP you see at the top bar)
      - **port**: `9090` (port of your proxy, for Proxyman use the port you see at the top bar)
      - restart the app. This makes Spotify use a TCP connection that the proxy can inspect instead of QUIC over UDP
   - block Spotify's UDP port 443 with an operating system firewall. This also forces a TCP connection that the proxy can inspect
   - try an older version of the Spotify desktop client

- Export the login request body (a binary Protobuf payload) to a file (e.g. ***login-request-body-file***)
   - In Proxyman: **right click the request → Export → Request Body → Save File**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/proxyman_export_protobuf.png" alt="proxyman_export_protobuf" width="80%"/>
</p>

- Run the tool with `--token-source client -w <path-to-login-request-body-file>`:

```sh
spotify_monitor --token-source client -w <path-to-login-request-body-file> <spotify_user_uri_id>
```

Spotify Monitor reads the required fields from the saved request and starts monitoring.

To avoid passing `-w` each time, save the file path in `LOGIN_REQUEST_BODY_FILE`.

Also set `TOKEN_SOURCE = "client"` so later runs use client mode without the flag.

Spotify Monitor refreshes the access token and client token with the captured refresh token.

If the refresh token expires, Spotify Monitor reports the error in the console. It also sends the error through each enabled notification channel: email, Discord or ntfy. Export the login request body again.

If you re-export the login request body to the same file name, you can send a `SIGHUP` signal to reload the file with the new refresh token without restarting the tool. More info in [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

The generated configuration file documents other client-mode settings. Keep their defaults unless you know that your captured client data requires different values.

<a id="spotify-oauth-app"></a>
## Spotify OAuth App

Normal use does not need a Spotify OAuth app. This optional legacy path uses the Spotify Web API for track details and playlist owner details when Spotipy is installed. Configure it only if you already have a working app with verified access to the legacy endpoints. When this path is unavailable, Spotify Monitor falls back to web-player metadata.

Spotify requires the owner of every Development Mode app to keep an active Premium subscription. This applies to old and new apps. A Development Mode app stops working when the owner loses Premium and resumes after the owner resubscribes. An HTTP 403 is consistent with restricted legacy access but does not prove the cause by itself. The doctor checks this path live and reports a warning when web-player metadata succeeds. See Spotify's [official migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide).

If you already have a working app or want to create a new one:

- Log in to [Spotify Developer dashboard](https://developer.spotify.com/dashboard)

- Open an app owned by an account with active Spotify Premium and verified legacy endpoint access (or create new one)

- Copy the **Client ID** and **Client Secret**

- Provide the `SP_APP_CLIENT_ID` and `SP_APP_CLIENT_SECRET` secrets using one of the following methods:
   - Pass it at runtime with `-r` / `--oauth-app-creds` (use `SP_APP_CLIENT_ID:SP_APP_CLIENT_SECRET` format - note the colon separator)
   - Set it as an [environment variable](#storing-secrets) (e.g. `export SP_APP_CLIENT_ID=...; export SP_APP_CLIENT_SECRET=...`)
   - Add it to [.env file](#storing-secrets) (`SP_APP_CLIENT_ID=...` and `SP_APP_CLIENT_SECRET=...`) for persistent use
   - Fallback: hard-code it in the code or config file

Example:

```sh
spotify_monitor <spotify_user_uri_id> -r "your_spotify_app_client_id:your_spotify_app_client_secret"
```

When configured the tool automatically refreshes the OAuth app access token. Tokens are cached in the file specified by `SP_APP_TOKENS_FILE` configuration option (default: `.spotify-monitor-oauth-app.json`).

If `SP_APP_CLIENT_ID` and `SP_APP_CLIENT_SECRET` are in `.env`, a running process on macOS, Linux or Unix can reload them after a `SIGHUP` signal. See [Storing Secrets](#storing-secrets) and [Signal Controls](usage.md#signal-controls-macoslinuxunix).

<a id="following-the-monitored-user"></a>
## Following the Monitored User

To monitor a user's activity, you must follow them from the Spotify account associated with the `sp_dc` cookie or `client` credentials.

The setup wizard checks that account's follow state after it saves usable authentication. If the target is not followed the wizard asks whether to follow it. The default answer is no. Spotify Monitor sends no follow request unless you explicitly answer yes. After an approved request the wizard queries Spotify again and reports success only when the target is confirmed as followed.

This works in cookie mode and advanced client mode without a separate user-authorized OAuth token. It uses private web-player Pathfinder operations rather than a supported public Web API. Spotify can change these operations. Spotify Monitor therefore reads their current identifiers from the web-player bundle and retries discovery once if Spotify rejects a cached identifier.

If you configure authentication outside the wizard you can still follow the target manually in the Spotify desktop or mobile app.

Additionally, the user must have sharing of listening activity enabled in their Spotify client settings. Without this, no activity data will be visible.

<a id="how-to-get-a-friends-user-uri-id"></a>
## How to Get a Friend's User URI ID

Use the Spotify desktop or mobile app:

- go to your friend's profile
- click the **three dots** (•••) or press the **Share** button
- copy the link to the profile

You'll get a URL like: [https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id](https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id)

Pass that profile URL directly to the tool. Raw IDs and Spotify user URIs such as `spotify:user:spotify_user_uri_id` are also accepted.

As an alternative you can extract the part between `/user/` and `?si=` - in this case: `spotify_user_uri_id` - then pass that raw ID to the tool.

Alternatively you can list all user URI IDs of accounts you follow by using [Listing mode](usage.md#listing-mode).

<a id="smtp-settings"></a>
## SMTP Settings

Email notifications need SMTP server details for the email account that sends the messages. Add them to `spotify_monitor.conf` or use the setup wizard.

Send one test message to verify the settings:

```sh
spotify_monitor --send-test-email
```

<a id="webhook-settings"></a>
## Webhook Settings

Spotify Monitor can send activity alerts through Discord or the native [ntfy publish API](https://docs.ntfy.sh/publish/). Webhook alerts work with or without email. Run `spotify_monitor --setup`, choose webhook alerts and select Discord or ntfy.

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
2. In the setup wizard, paste either the bare ntfy.sh topic name or its complete topic URL such as `https://ntfy.sh/spotify-monitor-long-random-value`. A bare topic name is expanded to an ntfy.sh URL. For a self-hosted server, use the complete HTTPS topic URL.
3. Set the provider in `spotify_monitor.conf`:

```ini
WEBHOOK_PROVIDER = "ntfy"
```

4. When configuring without the setup wizard, save the complete topic URL privately:

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

This sends an alert when the user becomes active, becomes inactive or when monitoring has a problem. See [Webhook Notifications](usage.md#webhook-notifications) if you want different alerts.

Send one test webhook without starting monitoring:

```sh
spotify_monitor --send-test-webhook
```

Email and webhooks work separately. If one fails, Spotify Monitor can still send the other. Discord messages cannot trigger `@everyone` or `@here` mentions.

If the webhook service temporarily refuses a message, Spotify Monitor tries once more and waits at most five seconds. Spotify monitoring continues normally and its retry behavior is unchanged.

<a id="storing-secrets"></a>
## Storing Secrets

A `.env` file is a plain text file that holds private values separately from regular configuration. Store `SP_DC_COOKIE`, `REFRESH_TOKEN`, `SP_APP_CLIENT_ID`, `SP_APP_CLIENT_SECRET`, `SMTP_PASSWORD`, `WEBHOOK_URL` and `NTFY_ACCESS_TOKEN` there. Do not commit this file or share it.

You can use operating system environment variables instead of a file. Set them with `export` on Linux, Unix, macOS or WSL:

```sh
export SP_DC_COOKIE="your_sp_dc_cookie_value"
export REFRESH_TOKEN="your_spotify_app_refresh_token"
export SP_APP_CLIENT_ID="your_spotify_app_client_id"
export SP_APP_CLIENT_SECRET="your_spotify_app_client_secret"
export SMTP_PASSWORD="your_smtp_password"
export WEBHOOK_URL="https://discord.com/api/webhooks/your_id/your_token"
export NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

To keep the values between terminal sessions, store them in `.env`.

Browser import, `--set-sp-dc` and the setup wizard can create or update `.env` for you.

If you cloned the repository, you can copy the included example then fill in only the secrets you use:

```sh
test -e .env || cp .env.example .env
```

If you installed from PyPI or downloaded only `spotify_monitor.py`, `.env.example` will not be in your current directory. Create a plain text file named `.env` in the directory where you run Spotify Monitor then add only the values you use. `REFRESH_TOKEN` is for advanced client mode. Spotify app credentials are optional legacy metadata credentials.

```ini
SP_DC_COOKIE="your_sp_dc_cookie_value"
REFRESH_TOKEN="your_spotify_app_refresh_token"
SP_APP_CLIENT_ID="your_spotify_app_client_id"
SP_APP_CLIENT_SECRET="your_spotify_app_client_secret"
SMTP_PASSWORD="your_smtp_password"
WEBHOOK_URL="https://discord.com/api/webhooks/your_id/your_token"
NTFY_ACCESS_TOKEN="tk_your_ntfy_access_token"
```

By default, Spotify Monitor looks for `.env` in the current directory. If it is not there, the search continues in each parent directory.

Browser import does not use the parent-directory search when choosing where to write. Without `--env-file`, it writes to `.env` in the current directory.

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
spotify_monitor <spotify_user_uri_id> --env-file /path/.env-spotify_monitor
```

Disable automatic `.env` search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
spotify_monitor <spotify_user_uri_id> --env-file none
```

As a last resort, you can store private values in the configuration file or source code. This makes them easier to expose or commit accidentally.
