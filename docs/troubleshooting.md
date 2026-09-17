# Troubleshooting

Examples on this page use the PyPI command `spotify_monitor`. If you chose another installation, replace that command with the matching [command prefix](usage.md#command-format). The setup wizard and `--help` also print commands for the detected installation.

<a id="doctor-preflight"></a>
## Doctor Preflight

Before a long monitoring run, check the current configuration:

```sh
spotify_monitor --doctor
```

The report shows only sections relevant to the checks it performed. It uses `[PASS]`, `[WARN]`, `[FAIL]` and `[SKIP]` markers, colour-coded by status when colour output is on, in these possible sections:

* **Environment**
* **Configuration**
* **Authentication**
* **Metadata**
* **Connectivity**
* **Target**
* **Scrobble health**
* **Notifications**

Every `[WARN]` and `[FAIL]` row carries an indented `To fix:` line under its marker, plus a `Guide:` link when a documentation page covers that row. A `[SKIP]` row names a check that could not run and says why.

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

If Spotify reports `QUOTA_EXCEEDED`, the user-owned app has exhausted its Development Mode request quota. Spotify Monitor reports **Check failed**, preserves earlier scrobble alert history, waits for its normal operational retry interval and alerts only after three consecutive failures. It does not block for the full long `Retry-After` value. Increase `--scrobble-check-interval` if the response repeats and see Spotify's [quota modes guide](https://developer.spotify.com/documentation/web-api/concepts/quota-modes).

Scrobble health liveness banners say `Scrobble health monitor running for USERNAME. Current result: RESULT.` The result describes the current comparison. **Idle** means no completed Spotify plays were returned within the comparison period, even if an earlier check triggered an alert. **Missing scrobbles** means recent plays met the alert threshold. It does not identify the cause or establish a service outage. See [scrobble health settings](configuration.md#lastfm-scrobble-health) for reminder and matching rules.

Each failed check includes a `To fix:` action. A command in that action matches how you installed the tool and carries the `--config-file` or `--env-file` you started with, so it can be pasted as it is. For local cookie authentication failures, open [Spotify Web Player](https://open.spotify.com/) in Firefox and sign in to the Spotify account used for monitoring. Then run:

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

Inside Docker or Docker Compose, the suggested fix shows the read-only Firefox host profile import first. If manual extraction is needed, it shows the recommended `--set-sp-dc` command because its hidden prompt is the most secure entry method. See [Import Firefox into Container Authentication](usage.md#import-firefox-into-container-authentication) for Linux, Snap, Flatpak and macOS commands.

In Friend Activity mode, the banner that says nothing changed prints at any verbosity: `* Monitoring healthy for <user_uri_id>` with what was checked, followed by `Liveness check, timestamp:`. It is timed rather than counted in checks, so it appears once per `LIVENESS_CHECK_INTERVAL` of quiet, measured from the last thing the run printed. That setting defaults to 86400 seconds, a day. Set it to 0 to switch the banner off. A monitoring failure is reported as `* Error: <what failed> (retrying in <time>)`, with the `To fix:` paragraph under it the first time that category appears. Every monitor in this family prints that same line. During a long outage the failure is reported in full once, then the tool stays quiet and reminds you once an hour with `* Monitoring degraded for <user_uri_id>`, the summary of what is still failing, when it started and how many checks have failed so far, so a two-day outage is a handful of lines rather than one block per check. The reminder has its own clock and does not depend on `LIVENESS_CHECK_INTERVAL`, so it keeps coming when the banner is off. When the failure clears, `* Monitoring recovered for <user_uri_id>` reports how long it lasted. An outage that starts failing differently is still one outage: a lost connection that reads as a timeout on one check and as an unreachable host on the next prints nothing new, a change to another kind of failure that clears on its own is one line, `* Monitoring failure changed for <user_uri_id>. <what fails now>`, and a change to a failure that needs you is reported in full. The `ERROR_500_NUMBER_LIMIT`, `ERROR_500_TIME_LIMIT`, `ERROR_NETWORK_ISSUES_NUMBER_LIMIT` and `ERROR_NETWORK_ISSUES_TIME_LIMIT` settings of earlier versions are retired. A configuration file that still sets them is loaded with a note and they are ignored.

For advanced client-mode failures, repeat the [Spotify Desktop Client](configuration.md#spotify-desktop-client) export steps. Add `--debug` to Doctor or a normal run for sanitized technical detail: each line names the operation, then lists its details as comma-separated `key=value` fields such as the URL, the HTTP `status` and, for the steps that report one, `outcome=OK` or `outcome=failed`. Use `--verbose` for a complete startup summary and occasional state changes, without a line per check or a trace for every request. Cookies, tokens, authorization headers, email passwords and webhook URLs remain hidden. A `--debug` run leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen. `--verbose` clears it like an ordinary run.

<a id="terminal-colours-look-wrong"></a>
## Terminal Colours Look Wrong

If escape sequences such as `[36m` appear as literal text, the terminal does not understand ANSI colour. Start the tool with `--no-color`, or set `COLORED_OUTPUT = False` in the configuration file. On Windows, `pip install colorama` fixes the classic Command Prompt.

If colour is missing where you expect it, check in this order: `--no-color` on the command line, `COLORED_OUTPUT` in the configuration file, a `NO_COLOR` environment variable, and whether output is redirected or piped. Colour is switched off in all of those cases, and also when `TERM` is unset or set to `dumb`.

Log files never contain colour by design. To colour a saved log while reading it, see [Coloring Log Output with GRC](usage.md#coloring-log-output-with-grc).

To change which colours are used, see [Terminal Colours](configuration.md#terminal-colours).

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** reports activity changes and important errors
- **Verbose mode (`--verbose`)** adds occasional state changes, a line naming where each delivered alert went and a complete startup summary without private values. Set `DELIVERY_CONFIRMATIONS = False` to keep verbose mode without those delivery lines
- **Debug mode (`--debug`)** adds sanitized request flow, scheduling details and internal diagnostics

Either mode also expands the startup summary with the detected install method and the names of the secrets that came from the dotenv file, the environment or the configuration file. Secret values never appear. The same view names the webhook service alerts go to and whether that channel is switched on, plus the mail server that sends them with the recipient address masked. Each channel's own settings are indented under it. It also reports whether the delivery confirmations are printed and the process id, Python version and operating system the run is on.

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.

## Invalid saved settings and state

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

Unusable scrobble-health timestamps reset to zero with a warning naming each field. Other valid fields remain available.

Malformed path settings and color-theme values are reported by Doctor with the setting name. Invalid color values are ignored while rendering help so you can still find the configuration commands.
