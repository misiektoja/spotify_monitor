# Configuration

Examples on this page use the PyPI command `spotify_monitor`. Manual script, Docker Compose and direct Docker users should keep the shown options and use the matching prefix under [Command Format by Installation Method](usage.md#command-format). Container file paths must point into `/data`.

<a id="configuration-file"></a>
## Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, you can store them in a configuration file.

For a guided configuration, it is recommended to use `spotify_monitor --setup`. The setup wizard validates the generated settings before saving them. If you confirm replacement of an existing configuration, it creates a timestamped backup first.

If you want to edit the file manually, generate a default config template and save it to a file named `spotify_monitor.conf`:

```sh
# On macOS, Linux or Windows Command Prompt (cmd.exe)
spotify_monitor --generate-config > spotify_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
spotify_monitor --generate-config spotify_monitor.conf
```

> **IMPORTANT**: On **Windows PowerShell**, using redirection (`>`) can cause the file to be encoded in UTF-16, which will lead to "null bytes" errors when running the tool. It is highly recommended to provide the filename directly as an argument to `--generate-config` to ensure UTF-8 encoding.

When you provide a filename, Spotify Monitor checks that the new configuration can be loaded then saves it as UTF-8. If the file already exists, Spotify Monitor creates a timestamped backup before replacing it.

Edit the `spotify_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

Settings are applied in this order from lowest to highest priority:

1. Built-in defaults
2. The discovered or explicitly selected configuration file
3. Secret environment variables
4. Values from the selected dotenv file
5. Command-line options

The dotenv layer applies only to supported secret keys such as `SP_DC_COOKIE`, `SMTP_PASSWORD` and `WEBHOOK_URL`. A positional target overrides `TARGET_USER_URI_ID`. Use `--config-file PATH` and `--env-file PATH` to make both selected files explicit. See [Storing Secrets](#storing-secrets) for dotenv discovery and supported keys.

You may set `TARGET_USER_URI_ID` to a raw user ID, Spotify user URI or profile URL. A positional command-line target takes precedence over this configured value. With a configured target you can start monitoring with:

```sh
spotify_monitor --config-file spotify_monitor.conf
```

**New in v3.0:** A Spotify developer app is no longer required. Cookie or client mode authenticates Friend Activity while the anonymous web-player backend supplies track and public playlist metadata. Existing working OAuth app credentials remain supported as an optional legacy metadata path. New users should not create an app solely for this tool.

**New in v2.6:** The configuration file includes options to enable/disable music service URLs (Apple Music, YouTube Music, Amazon Music, Deezer, Tidal) and lyrics service URLs (Genius, AZLyrics, Tekstowo.pl, Musixmatch, Lyrics.com) in console and email outputs. You can also configure crossfade detection thresholds and the number of recent songs to include in inactivity emails.

<a id="spotify-access-token-source"></a>
## Spotify access token source

Friend Activity authentication and metadata retrieval are separate.

For Friend Activity monitoring, configure either the `cookie` or `client` token source method. A Spotify developer app is not used for core monitoring.

Track metadata and public playlist metadata use the anonymous Spotify web-player backend automatically. If complete [Spotify OAuth App](#spotify-oauth-app) credentials are configured the tool tries that optional legacy Web API path first then switches the affected metadata type to the web-player backend after a restricted response such as HTTP 403. A playlist HTTP 404 is classified after the web-player lookup resolves its owner. Spotify-curated playlists use web metadata only for that playlist while a non-Spotify playlist hidden from the legacy API switches remaining playlist lookups to the web backend.

The anonymous token and current persisted-query hashes are cached in memory. The tool refreshes an expired token and rediscovers a stale query hash once before reporting an error.

The token source method can be configured via the `TOKEN_SOURCE` configuration option or the `--token-source` flag.

**Recommended: `cookie`**

Uses the `sp_dc` cookie to retrieve a token from the Spotify web endpoint. This method is easy to set up and recommended for most users.

**Alternative: `client`**

Uses captured credentials from the Spotify desktop client and a Protobuf-based login flow. It's more complex to set up and intended for advanced users who want a long-lasting token with the broadest possible access.

If no method is specified, the tool defaults to the `cookie` method.

Spotify Monitor generates an appropriate request user agent automatically for the selected token source. Advanced users can override it with `USER_AGENT` or `--user-agent`, but normal installations should leave it empty.

**Important**: It is strongly recommended to use a separate Spotify account with this tool. It does not rely on the official Spotify Web API for core features (like fetching friend activity), as it is not supported by the public API. That said, while I've never encountered any issues on my own accounts, I can't guarantee that Spotify won't impose restrictions in the future - you've been warned.

<a id="spotify-sp_dc-cookie"></a>
### Spotify sp_dc Cookie

This is the default method used to obtain a Spotify access token.

Firefox browser import is the recommended onboarding path for local PyPI and downloaded-script installations. It works on macOS, Linux and Windows with no optional dependency. For default Docker and Docker Compose installations, use hidden manual entry with `--set-sp-dc`. Container Firefox import is advanced because it requires a read-only host profile mount.

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

**About the `chromium` option:** Chromium is the unbranded open-source browser that Google Chrome is built on. It is a **separate application** from Chrome with its own profile and cookie store. It is also a common default browser on many Linux distributions. Pick `chromium` only if you actually run that browser. If you use Google Chrome pick `chrome`.

**Not currently supported:** Microsoft Edge, Opera, Vivaldi, Arc and other Chromium-based browsers. They share the Chromium engine but each keeps its own separate cookie store. The underlying [`pycookiecheat`](https://github.com/n8henrie/pycookiecheat) library handles only the browsers listed above. If you use one of these browsers log in with Firefox or Chrome/Brave/Chromium for the import instead.

On **Windows** Chromium import is not possible. Chrome's app-bound encryption in Chrome 127 and later blocks external programs from reading its cookies. The tool detects Windows and recommends using Firefox instead.

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

The importer discovers Firefox profiles from `profiles.ini` and normal profile directories. If one usable profile exists it is selected automatically. If several profiles exist an interactive terminal shows a numbered choice. For scripts or other noninteractive runs select one by its friendly name or directory basename:

```sh
spotify_monitor --import-browser-cookie --browser firefox --browser-profile "default-release"
```

The advanced `--cookie-file PATH` option points directly to a Firefox `cookies.sqlite` database and takes precedence over profile discovery:

```sh
spotify_monitor --import-browser-cookie --browser firefox --cookie-file /path/to/cookies.sqlite
```

By default import writes only `SP_DC_COOKIE` to `.env` in the current directory. Use `--env-file PATH` to choose another dotenv file. Import never modifies a dotenv file found only through parent-directory discovery. `--env-file none` is invalid for import because persistence is required.

The cookie is validated through Spotify token acquisition and an authenticated buddy-list request before the dotenv file is changed. Existing comments, blank lines and unrelated settings are preserved. Replacing an existing value requires confirmation in an interactive terminal or `--force` in a noninteractive run. `--force` does not skip validation.

Chrome, Brave and Chromium import is available on macOS and Linux through the optional browser extra:

```sh
pip install "spotify_monitor[browser]"
spotify_monitor --import-browser-cookie --browser chrome
```

Chromium profiles support `Default` and `Profile *` directories plus friendly names from Local State. Both modern `<profile>/Network/Cookies` and legacy `<profile>/Cookies` databases are recognized.

<a id="manual-cookie-extraction"></a>
#### Manual cookie extraction

Manual extraction is a fallback for local installations and the recommended default-container path. Treat `sp_dc` like a password. Anyone who has it may be able to use your Spotify login session.

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
* Add `SP_DC_COOKIE="your_sp_dc_cookie_value"` to a [dotenv file](#storing-secrets) for persistent use.
* Pass it for one run with `-u` or `--spotify-dc-cookie`. This is not recommended because the value may appear in shell history or process listings.
* Store it in the configuration file or source code as a last resort. This is not recommended because it is easier to expose or commit accidentally.

If your `sp_dc` cookie expires, the tool will notify you via the console and email. In that case, you'll need to grab the new `sp_dc` cookie value.

If you store the `SP_DC_COOKIE` in a dotenv file you can update its value and send a `SIGHUP` signal to reload the file with the new `sp_dc` cookie without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

> **NOTE:** Spotify still requires TOTP parameters for web-player token requests. The web player continues to select v61 which was first published in January 2026. Version 3.0 embeds v61 directly and no longer downloads a third-party secret dictionary. The version and cipher bytes are exposed as the `TOTP_VERSION` and `TOTP_SECRET_CIPHER_BYTES` config options, so if Spotify resumes rotation you can patch them from the config file without a code release. Use [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/main/debug/spotify_monitor_secret_grabber.py) to extract the current bundle values then update those two options.

<a id="spotify-desktop-client"></a>
### Spotify Desktop Client

This is the alternative method used to obtain a Spotify access token which simulates a login from the real Spotify desktop app using credentials intercepted from a real session.

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
      - restart the app; since QUIC (HTTP/3) requires raw UDP and can't tunnel over HTTP CONNECT, Spotify will downgrade to TCP-only HTTP/2 or 1.1, which intercepting proxy can decrypt
   -  block Spotify's UDP port 443 at the OS level with a firewall of your choice - this prevents QUIC (HTTP/3), forcing TLS over TCP and letting intercepting proxy perform MITM
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

If successful, the tool will automatically extract the necessary fields and begin monitoring.

Instead of using the `-w` flag each time, you can persist the Protobuf login request file path by setting the `LOGIN_REQUEST_BODY_FILE` configuration option.

The same applies to `--token-source client` flag - you can persist it via `TOKEN_SOURCE` configuration option set to `client`.

The tool will automatically refresh both the access token and client token using the intercepted refresh token.

If your refresh token expires, the tool will notify you via the console and email. In that case, you'll need to re-export the login request body.

If you re-export the login request body to the same file name, you can send a `SIGHUP` signal to reload the file with the new refresh token without restarting the tool. More info in [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

Advanced options are available for further customization - refer to the configuration file comments. However, the default settings are suitable for most users and modifying other values is generally NOT recommended.

<a id="spotify-oauth-app"></a>
## Spotify OAuth App

Since v3.0, you do not need a Spotify OAuth app for normal use, so normally you should not follow this section. OAuth app credentials enable an optional legacy Spotify Web API Client Credentials path for track metadata and playlist owner metadata when the optional Spotipy dependency is installed. Configure this path only if you already have a working app with verified legacy endpoint access. The tool tries it first when configured then falls back automatically when Spotify returns a restricted response or Spotipy is unavailable.

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

If you store the `SP_APP_CLIENT_ID` and `SP_APP_CLIENT_SECRET` in a dotenv file you can update their values and send a `SIGHUP` signal to reload the file with the new secret values without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

<a id="following-the-monitored-user"></a>
## Following the Monitored User

To monitor a user's activity, you must follow them from the Spotify account associated with the `sp_dc` cookie or `client` credentials.

The setup wizard checks that account's follow state after it saves usable authentication. If the target is not followed the wizard asks whether to follow it. The default answer is no. Spotify Monitor sends no follow request unless you explicitly answer yes. After an approved request the wizard queries Spotify again and reports success only when the target is confirmed as followed.

This works in cookie mode and advanced client mode without a separate user-authorized OAuth token. It uses Spotify's private web-player Pathfinder operations rather than a supported public Web API contract. Spotify can change those operations, thats why Spotify Monitor discovers their current persisted-query hashes from the web-player bundle and retries discovery once when Spotify rejects a cached hash.

If you configure authentication outside the wizard you can still follow the target manually in the Spotify desktop or mobile app.

Additionally, the user must have sharing of listening activity enabled in their Spotify client settings. Without this, no activity data will be visible.

<a id="how-to-get-a-friends-user-uri-id"></a>
## How to Get a Friend's User URI ID

The easiest way is via the Spotify desktop or mobile client:
- go to your friend's profile
- click the **three dots** (•••) or press the **Share** button
- copy the link to the profile

You'll get a URL like: [https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id](https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id)

Pass that profile URL directly to the tool. Raw IDs and Spotify user URIs such as `spotify:user:spotify_user_uri_id` are also accepted.

As an alternative you can extract the part between `/user/` and `?si=` - in this case: `spotify_user_uri_id` - then pass that raw ID to the tool.

Alternatively you can list all user URI IDs of accounts you follow by using [Listing mode](usage.md#listing-mode).

<a id="smtp-settings"></a>
## SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `spotify_monitor.conf` file.

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
spotify_monitor --send-test-email
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

Keep private values in an environment variable or a dotenv file. This includes `SP_DC_COOKIE`, `REFRESH_TOKEN`, `SP_APP_CLIENT_ID`, `SP_APP_CLIENT_SECRET`, `SMTP_PASSWORD`, `WEBHOOK_URL` and `NTFY_ACCESS_TOKEN`.

Set the needed environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

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

Alternatively store them persistently in a dotenv file (recommended).

Browser import, `--set-sp-dc` or the setup wizard can create or update `.env` for you. This is the easiest option.

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

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it.

Browser import is intentionally different. Without `--env-file` it writes to `.env` in the current directory and does not modify a parent dotenv file.

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
spotify_monitor <spotify_user_uri_id> --env-file /path/.env-spotify_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
spotify_monitor <spotify_user_uri_id> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.
