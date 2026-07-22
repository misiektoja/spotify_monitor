# Troubleshooting

Examples on this page use the PyPI command `spotify_monitor`. If you chose another installation, replace that command with the matching [command prefix](usage.md#command-format). The setup wizard and `--help` also print commands for the detected installation.

<a id="doctor-preflight"></a>
## Doctor Preflight

Before a long monitoring run, check the current configuration:

```sh
spotify_monitor --doctor
```

The report uses `[PASS]`, `[WARN]` and `[FAIL]` markers in these sections:

* Environment
* Configuration
* Authentication
* Metadata
* Connectivity
* Target
* Notifications
* Summary

Doctor loads the same settings as a normal run. It checks the Spotify login, connection and selected target. If complete legacy OAuth credentials are present, it requests a temporary token and checks track metadata. A failed legacy check becomes a warning when the web-player fallback works. Doctor also checks configured email and webhook settings without sending a message. It does not create logs, CSV files, flag files or OAuth caches. It does not change configuration or `.env` files.

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

Each failed check includes a `To fix:` action. For local cookie authentication failures, open [Spotify Web Player](https://open.spotify.com/) in Firefox and sign in to the Spotify account used for monitoring. Then run:

```sh
spotify_monitor --import-browser-cookie --browser firefox
```

Inside Docker or Docker Compose, the suggested fix shows the read-only Firefox host profile import first. It also shows hidden `--set-sp-dc` entry as a fallback. See [Import Firefox into Container Authentication](usage.md#import-firefox-into-container-authentication) for Linux, Snap, Flatpak and macOS commands.

For advanced client-mode failures, repeat the [Spotify Desktop Client](configuration.md#spotify-desktop-client) export steps. Add `--debug` to Doctor or a normal run for sanitized technical detail. Use `--verbose` for a complete startup summary plus occasional state changes without output for every poll. Cookies, tokens, authorization headers, email passwords and webhook URLs remain hidden.

<a id="choosing-the-right-logging-level"></a>
## Choosing the Right Logging Level

- **Default mode** reports activity changes and important errors
- **Verbose mode (`--verbose`)** adds occasional state changes and a complete startup summary without private values
- **Debug mode (`--debug`)** adds sanitized request flow, scheduling details and internal diagnostics

Start with `--doctor`. If the suggested fix does not resolve the issue, retry with `--debug` and include only sanitized output when opening a GitHub issue.
