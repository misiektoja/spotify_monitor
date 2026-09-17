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

Doctor uses your normal settings to check authentication, connectivity, the target, output paths and notifications. It shows the configuration and `.env` files in use and where credentials came from, without displaying their values. A failed optional legacy metadata check is a warning if the web-player fallback works. It also warns when [TLS verification](configuration.md#tls-verification) is off.

Doctor checks email login and webhook settings without sending messages. It does not create monitoring output files. Friend Activity checks leave configuration and credentials unchanged. Scrobble health checks may save a replacement refresh token if Spotify rotates it.

In an interactive terminal, Doctor offers a delivery test for each ready notification channel. Each test sends one real message only if you answer Yes. The default is No. Ctrl+C ends the run. Delivery tests are not offered in noninteractive runs.

The **Next steps** block gives the monitoring command with your target and selected file paths. Resolve failing checks before starting.

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

Friend Activity prints a `Monitoring healthy` banner after a day of quiet by default. Change `LIVENESS_CHECK_INTERVAL` to adjust that interval or set it to `0` to disable the banner.

A monitoring failure is reported immediately with recovery guidance. Persistent failures produce an hourly `Monitoring degraded` reminder, even if liveness banners are disabled. `Monitoring recovered` reports when the failure clears and how long it lasted.

The old `ERROR_500_NUMBER_LIMIT`, `ERROR_500_TIME_LIMIT`, `ERROR_NETWORK_ISSUES_NUMBER_LIMIT` and `ERROR_NETWORK_ISSUES_TIME_LIMIT` settings are ignored. Existing configurations containing them still load with a note.

For advanced client-mode failures, repeat the [Spotify Desktop Client](configuration.md#spotify-desktop-client) export steps. Add `--debug` to Doctor or a normal run for technical diagnostics. Debug mode keeps earlier terminal output visible and hides private credentials.

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

Delivery confirmations name the recipient or webhook provider. `DELIVERY_CONFIRMATIONS = False` hides these optional success messages. Monitoring events, send attempts and errors remain visible.

Both `--verbose` and `--debug` show the complete startup summary, including notification settings and credential sources. Use it to check which configuration is active without displaying private values.

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.

## Invalid saved settings and state

Timing values must be finite and within the documented range. Normal startup checks effective timing settings before monitoring. A configuration syntax error reports its file, line number and parser message without echoing source text that may contain credentials.

Unusable scrobble-health timestamps reset to zero with a warning naming each field. Other valid fields remain available.

Doctor names invalid path, truncation and colour settings so you can correct them. Normal monitoring stops for invalid paths, but Doctor, setup and credential commands remain available for recovery. `TRUNCATE_CHARS` must be an integer zero or greater. Use `0` for full lines or `999` to detect terminal width.
