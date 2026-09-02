# Troubleshooting

Examples on this page use the PyPI command `spotify_monitor`. If you chose another installation, replace that command with the matching [command prefix](usage.md#command-format). The setup wizard and `--help` also print commands for the detected installation.

<a id="doctor-preflight"></a>
## Doctor Preflight

Before a long monitoring run, check the current configuration:

```sh
spotify_monitor --doctor
```

The report shows only sections relevant to the checks it performed. It uses `[PASS]`, `[WARN]`, `[FAIL]` and `[SKIP]` markers in these possible sections:

* Environment
* Configuration
* Authentication
* Metadata
* Connectivity
* Target
* Scrobble health
* Notifications

Doctor loads the same settings as a normal run. It opens with the raw `manual`, `pip`, `docker` or `compose` install method, then checks the Spotify login, the connectivity endpoint, the Spotify connection and the selected target. If complete legacy OAuth credentials are present, it requests a temporary token and checks track metadata. A failed legacy check becomes a warning when the web-player fallback works. Doctor names the configuration file and the dotenv file it loaded, then lists which secrets are in effect and whether each one came from the dotenv file, an environment variable or the configuration file. Secret names are listed, never their values. It reports whether [TLS verification](configuration.md#tls-verification) is on, and warns while it is off. It also names the log and CSV files monitoring would write and reports whether each one can be created, or says so when either is disabled. Doctor also signs in to the configured SMTP server and checks webhook settings without sending a message, and each ready row lists the alert categories that channel would deliver. It does not create logs, CSV files, flag files or OAuth caches. Friend Activity Doctor does not change configuration or `.env` files. Focused scrobble health Doctor may atomically update `SPOTIFY_SCROBBLE_REFRESH_TOKEN` if Spotify rotates it while access is checked.

In an interactive terminal, Doctor can offer one real delivery test for each notification channel that passes its checks. Each prompt defaults to No. Answering Yes to the email prompt sends one test email. Answering Yes to the webhook prompt sends one Discord or ntfy message. Ctrl+C at either prompt ends the run rather than declining one test and asking the next. Doctor does not offer delivery tests when it runs without an interactive terminal. The `Summary` line is printed after the tests finish and counts their results, so the sentence and the exit code always describe the same run.

The report ends with a **Next steps** block naming the command that starts monitoring, carrying the same `--config-file` and `--env-file` this run checked. It carries the target this run used, leaves it out when the configuration file already supplies one and otherwise shows `<spotify_target>` for you to replace. While a check is failing it asks for the failures first.

Warnings do not make the command fail. Doctor returns a nonzero exit status if a check or approved delivery test fails, so scripts can detect the failure. Run it without a target to check authentication or pass a target to check one specific user:

```sh
spotify_monitor --doctor
spotify_monitor --doctor <spotify_target>
```

Doctor accepts the normal configuration options:

```sh
spotify_monitor --doctor <spotify_target> --config-file spotify_monitor.conf
spotify_monitor --doctor <spotify_target> --env-file /path/.env-spotify_monitor
spotify_monitor --doctor <spotify_target> --token-source client
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

Each failed check includes a `To fix:` action. A command in that action matches how you installed the tool and carries the `--config-file` or `--env-file` you started with, so it can be pasted as it is. For local cookie authentication failures, open [Spotify Web Player](https://open.spotify.com/) in Firefox and sign in to the Spotify account used for monitoring. Then run:

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

Inside Docker or Docker Compose, the suggested fix shows the read-only Firefox host profile import first. If manual extraction is needed, it shows the recommended `--set-sp-dc` command because its hidden prompt is the most secure entry method. See [Import Firefox into Container Authentication](usage.md#import-firefox-into-container-authentication) for Linux, Snap, Flatpak and macOS commands.

A monitoring failure is reported as `* Error: <what failed> (retrying in <time>)`, with the `To fix:` paragraph under it the first time that category appears. Every monitor in this family prints that same line. During a long outage the failure is reported in full once, then the liveness banner takes over with `* Monitoring degraded for <user_uri_id>` and the summary of what is still failing, so a broken run keeps saying it is alive without repeating the same paragraph. When the failure clears, `* Monitoring recovered for <user_uri_id>` reports how long it lasted. Setting `LIVENESS_CHECK_INTERVAL` to 0 removes the banner that carries the reminder, so the one-line summary goes back to printing on every check.

For advanced client-mode failures, repeat the [Spotify Desktop Client](configuration.md#spotify-desktop-client) export steps. Add `--debug` to Doctor or a normal run for sanitized technical detail: each line names the operation, then lists its details as comma-separated `key=value` fields, and every outbound call reports `outcome=OK` or `outcome=failed`. Use `--verbose` for a complete startup summary and occasional state changes, without a line per check or a trace for every request. Cookies, tokens, authorization headers, email passwords and webhook URLs remain hidden. A `--debug` run leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen. `--verbose` clears it like an ordinary run.

<a id="terminal-colours-look-wrong"></a>
## Terminal Colours Look Wrong

If escape sequences such as `[36m` appear as literal text, the terminal does not understand ANSI colour. Start the tool with `--no-color`, or set `COLORED_OUTPUT = False` in the configuration file. On Windows, `pip install colorama` fixes the classic Command Prompt.

If colour is missing where you expect it, check in this order: `--no-color` on the command line, `COLORED_OUTPUT` in the configuration file, a `NO_COLOR` environment variable, and whether output is redirected or piped. Colour is switched off in all of those cases, and also when `TERM` is unset or set to `dumb`.

Log files never contain colour by design. To colour a saved log while reading it, see [Coloring Log Output with GRC](usage.md#coloring-log-output-with-grc).

To change which colours are used, see [Terminal Colours](configuration.md#terminal-colours).

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** reports activity changes and important errors
- **Verbose mode (`--verbose`)** adds occasional state changes and a complete startup summary without private values
- **Debug mode (`--debug`)** adds sanitized request flow, scheduling details and internal diagnostics

Either mode also expands the startup summary with the detected install method and the names of the secrets that came from the dotenv file, the environment or the configuration file. Secret values never appear.

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.
