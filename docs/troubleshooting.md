# Troubleshooting

Examples on this page use the PyPI command `spotify_monitor`. For a manual script or container, use the matching prefix under [Command Format by Installation Method](usage.md#command-format). The setup wizard and `--help` print commands for the detected installation.

<a id="doctor-preflight"></a>
## Doctor Preflight

Before starting a long monitoring run, use the doctor preflight command:

```sh
spotify_monitor --doctor
```

The report uses `[PASS]`, `[WARN]` and `[FAIL]` markers across these sections:

* Environment
* Configuration
* Authentication
* Metadata
* Connectivity
* Target
* Notifications
* Summary

The doctor loads the same settings as a normal run. It checks Spotify login, connectivity and the selected target. When complete legacy OAuth credentials are configured it requests a memory-only token and checks live track metadata access. If that legacy check fails but the automatic web-player fallback succeeds the doctor reports a warning and still exits successfully. For Development Mode apps the warning reminds you that Spotify requires the app owner to have active Premium. A legacy failure can have other causes, so the doctor does not claim that a 403 proves the subscription has lapsed. For enabled email alerts it checks SMTP login without sending. For enabled webhook alerts it checks the provider, saved link, headers and alert choices without publishing. It never creates logs, CSV files, flag files or OAuth caches and it never updates config or dotenv files.

In an interactive terminal, each notification channel that passes its passive checks gets a separate optional delivery prompt. Both prompts default to No. Approving the email prompt delivers one real test email. Approving the webhook prompt publishes one real Discord or ntfy notification. Declining either prompt sends nothing. Noninteractive doctor runs never offer or send delivery tests.

Warnings do not make the command fail. The doctor exits nonzero when at least one passive check or approved delivery test fails. You can run an authentication-only check without a target or verify one specific account:

```sh
spotify_monitor --doctor
spotify_monitor --doctor <spotify_user_uri_id>
```

Normal configuration overrides work with the doctor:

```sh
spotify_monitor --doctor <spotify_user_uri_id> --config-file spotify_monitor.conf
spotify_monitor --doctor <spotify_user_uri_id> --env-file /path/.env-spotify_monitor
spotify_monitor --doctor <spotify_user_uri_id> --token-source client
```

Each failed check includes a `To fix:` action. For local cookie authentication failures, open [Spotify Web Player](https://open.spotify.com/) in Firefox and sign in to the Spotify account used for monitoring. Then run:

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

Inside Docker or Docker Compose, recovery guidance prefers the hidden `--set-sp-dc` path and also shows the advanced mounted Firefox command.

For advanced client-mode failures, follow the [Spotify Desktop Client](configuration.md#spotify-desktop-client) export instructions again. Add `--debug` to normal runs or doctor checks for sanitized technical detail. Use `--verbose` for startup settings plus rare operational state changes without per-poll traces. Cookies, tokens, authorization headers, email passwords and webhook URLs remain hidden.

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** keeps long-running monitoring quiet and reports activity changes plus important errors
- **Verbose mode (`--verbose`)** adds occasional operational events and a complete non-secret startup summary without printing every polling cycle
- **Debug mode (`--debug`)** adds sanitized request flow, scheduling details and internal diagnostics for deeper troubleshooting

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.
