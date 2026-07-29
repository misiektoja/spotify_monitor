# Troubleshooting

Examples on this page use the PyPI command `spotify_monitor`. If you chose another installation, replace that command with the matching [command prefix](usage.md#command-format). The setup wizard and `--help` also print commands for the detected installation.

<a id="doctor-preflight"></a>
## Doctor Preflight

Before a long monitoring run, check the current configuration:

```sh
spotify_monitor --doctor
```

The report shows only sections relevant to the checks it performed. It uses `[PASS]`, `[WARN]` and `[FAIL]` markers in these possible sections:

* Environment
* Configuration
* Authentication
* Metadata
* Connectivity
* Target
* Scrobble health
* Notifications
* Summary

Doctor loads the same settings as a normal run. It checks the Spotify login, connection and selected target. If complete legacy OAuth credentials are present, it requests a temporary token and checks track metadata. A failed legacy check becomes a warning when the web-player fallback works. Doctor also checks configured email and webhook settings without sending a message. It does not create logs, CSV files, flag files or OAuth caches. Friend Activity Doctor does not change configuration or `.env` files. Focused scrobble health Doctor may atomically update `SPOTIFY_SCROBBLE_REFRESH_TOKEN` if Spotify rotates it while access is checked.

In an interactive terminal, Doctor can offer one real delivery test for each notification channel that passes its checks. Each prompt defaults to No. Answering Yes to the email prompt sends one test email. Answering Yes to the webhook prompt sends one Discord or ntfy message. Doctor does not offer delivery tests when it runs without an interactive terminal.

Warnings do not make the command fail. Doctor returns a nonzero exit status if a check or approved delivery test fails, so scripts can detect the failure. Run it without a target to check authentication or pass a target to check one specific user:

```sh
spotify_monitor --doctor
spotify_monitor --doctor <spotify_user_uri_id>
```

Doctor accepts the normal configuration options:

```sh
spotify_monitor --doctor <spotify_user_uri_id> --config-file spotify_monitor.conf
spotify_monitor --doctor <spotify_user_uri_id> --env-file /path/.env-spotify_monitor
spotify_monitor --doctor <spotify_user_uri_id> --token-source client
```

For scrobble health, focused Doctor shows live progress while it checks the environment, configuration, Spotify recent plays, Last.fm scrobbles and notifications. Its final report includes how many recent plays each service returned plus the current comparison status. Add `--verbose` to list up to ten recent Spotify plays with match markers, their matched Last.fm timestamps and the recent Last.fm scrobbles used for comparison:

```sh
spotify_monitor --monitor-mode scrobble_health --doctor --verbose
```

Track titles and listening timestamps appear only in this verbose diagnostic output. Spotify and Last.fm can timestamp different points in the same playback, so matched rows can have different times. Refresh tokens, API keys and other private credentials remain hidden.

If focused Doctor reports missing, expired or revoked Spotify recent-play authorization, run:

```sh
spotify_monitor --authorize-scrobble-health
```

The command shows the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard), the exact redirect URI plus Spotify's [app creation](https://developer.spotify.com/documentation/web-api/concepts/apps) and [PKCE](https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow) guides. Confirm that the app owner has Premium, Web API is selected and the redirect URI matches exactly. If the Spotify account being authorized is not the app owner, add it under User Management.

If Spotify reports `QUOTA_EXCEEDED`, the user-owned app has exhausted its Development Mode request quota. This is not evidence that Last.fm scrobbling is broken. Spotify Monitor leaves the current health state unchanged, waits for its normal operational retry interval and alerts only after three consecutive failures. It does not block for the full long `Retry-After` value. Increase `--scrobble-check-interval` if the response repeats and see Spotify's [quota modes guide](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

Each failed check includes a `To fix:` action. For local cookie authentication failures, open [Spotify Web Player](https://open.spotify.com/) in Firefox and sign in to the Spotify account used for monitoring. Then run:

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

Inside Docker or Docker Compose, the suggested fix shows the read-only Firefox host profile import first. If manual extraction is needed, it shows the recommended `--set-sp-dc` command because its hidden prompt is the most secure entry method. See [Import Firefox into Container Authentication](usage.md#import-firefox-into-container-authentication) for Linux, Snap, Flatpak and macOS commands.

For advanced client-mode failures, repeat the [Spotify Desktop Client](configuration.md#spotify-desktop-client) export steps. Add `--debug` to Doctor or a normal run for sanitized technical detail. Use `--verbose` for a complete startup summary plus occasional state changes without output for every poll. Cookies, tokens, authorization headers, email passwords and webhook URLs remain hidden.

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** reports activity changes and important errors
- **Verbose mode (`--verbose`)** adds occasional state changes and a complete startup summary without private values
- **Debug mode (`--debug`)** adds sanitized request flow, scheduling details and internal diagnostics

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.
