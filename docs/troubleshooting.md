# Troubleshooting

<a id="doctor-preflight"></a>
## Doctor Preflight

Before starting a long monitoring run, use the read-only preflight command:

```sh
spotify_monitor --doctor
```

The report uses `[PASS]`, `[WARN]` and `[FAIL]` markers across these sections:

* Environment
* Configuration
* Authentication
* Connectivity
* Target
* Notifications
* Summary

The doctor loads the same settings as a normal run. It checks Spotify login, connectivity and the selected target. If email alerts are enabled it can check your email login but it never sends an email. If webhook alerts are enabled it checks the saved link and your alert choices without sending a webhook. It does not create logs, CSV files, flag files, OAuth caches or update config and dotenv files.

Warnings do not make the command fail. The doctor exits nonzero only when at least one check has `[FAIL]`. You can run an authentication-only check without a target or verify one specific account:

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
