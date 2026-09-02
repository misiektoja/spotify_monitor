# Test suite

These tests cover logic in `spotify_monitor.py` and the `debug/` utilities that can run without
network access. Functions that normally contact Spotify or Last.fm are replaced with test doubles.
See `test_monitoring_loop.py` for an example.

The default suite also builds and installs the project wheel to test the shipped console commands.
Integration tests bind local loopback HTTP and SMTP servers and never leave the machine.

## Running

From the repository root:

```bash
pip install -e '.[test]'
python -m pytest
```

`pyproject.toml` puts the repository root first on `sys.path`, so the tests use the working tree
instead of an installed copy of the module.

Optional extras are needed only for the code paths that use them:

```bash
pip install -e '.[test,browser,legacy-oauth]'
```

Without them, `test_browser_cookie_import.py` and the legacy OAuth metadata paths fall back to the
same absent-dependency behavior a user would see.

## Layout

| File | Area under test |
| --- | --- |
| `test_config_and_inputs.py` | Target normalization, CLI and config precedence, duration parsing, URI to URL conversion |
| `test_config_effects.py` | Config-file settings reaching their consumers, including check interval, connectivity and TLS verification |
| `test_setup_wizard.py` | Prompt helpers, validation, reprompting and the generated configuration |
| `test_set_sp_dc.py` | `--set-sp-dc` interactivity guards, atomic dotenv updates and failure rollback |
| `test_set_lastfm_credentials.py` | `--set-lastfm-credentials` prompts, partial updates and replacement confirmation |
| `test_browser_cookie_import.py` | Firefox and Chromium profile discovery, selection and cookie extraction |
| `test_spotify_web_backends.py` | TOTP generation, token validity probes, metadata backend selection and running without spotipy |
| `test_totp_secret_extraction.py` | Secret extraction from bundles and the debug utility's destination and redirect restrictions |
| `test_monitoring_loop.py` | Friend Activity loop error and auth recovery, retry timing, activity flags and track-change recording |
| `test_scrobble_health.py` | Spotify to Last.fm authorization, token retries, play matching and outage detection |
| `test_webhook_notifications.py` | Webhook URL validation, provider detection, ntfy normalization and `SIGHUP` reload |
| `test_notification_escaping.py` | Source-level sweep proving every HTML email body and attribute escapes Spotify-supplied text |
| `test_local_transports.py` | Real loopback HTTP and SMTP delivery, marked `integration` |
| `test_runtime_security.py` | Request deadlines and watchdog nesting, playback argument lists, cookie polling and terminal-safe Spotify output |
| `test_terminal_color.py` | Coloured terminal output: theme resolution, line rules, the colour-aware sanitizer, plain log files and the uncoloured Doctor progress line |
| `test_help_screen.py` | The `--help` screen: the shared argument group names, the task-grouped examples and the startup banner |
| `test_tls_verification.py` | Every connection honouring `VERIFY_SSL` and the single shared TLS context builder |
| `test_recovery_errors.py` | Error classification and install-method-aware recovery advice |
| `test_doctor.py` | `--doctor` report structure, sections, detail indentation and exit status |
| `test_startup_ui.py` | Startup banner rendering, alignment and machine-friendly `--version` and `--generate-config` output |
| `test_install_method_commands.py` | Install-method detection and the command prefixes shown for pip, manual, Docker and Compose |
| `test_properties.py` | Property-based parsing, serialization and secret-safety round-trips |
| `test_offline_e2e.py` | One complete CLI monitoring iteration against a loopback Spotify fixture, marked `e2e` |
| `test_documentation.py` | Semantic documentation contracts, community health files, issue templates and security workflows plus repository metadata: citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_container_assets.py` | Dockerfile, Compose and publishing workflow contracts |
| `test_packaging.py` | Wheel contents, installed console commands, action pinning and version consistency |

## Conventions

* Keep everything offline. If a code path needs network access, stub it with `monkeypatch` rather
  than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a leaked global
  affects whatever runs next.
* Mark tests that bind a local server `integration`, and full-flow CLI tests `e2e`.
* Never use a real cookie, refresh token, API key, SMTP password or webhook URL. Loopback tests use
  fake credentials that only the temporary local servers accept.

Online tests that authenticate against Spotify are excluded, because automated logins could trigger
account protection. A change to token handling, the monitoring loop or a metadata backend is not
verified by this suite alone. Exercise it against a real account and say so in the pull request.

See [Testing](https://misiektoja.github.io/spotify_monitor/testing/) for the CI jobs, supply chain
checks and focused test commands.
