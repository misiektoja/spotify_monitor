# spotify_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 3.4 (TBD)

Version **3.4** reports **TLS certificate verification**, gives **every rejected setup answer a way out**, **checks the mail server during setup**, adds **`--set-smtp-password`**, adds the **install method and secret origins** to the complete startup summary, makes **debug traces scannable** and brings Doctor, setup, the startup summary and the one-shot secret commands in line with the sibling monitors.

**Features and improvements**:

- **IMPROVE:** **TLS certificate verification is reported, not just configured** - **`VERIFY_SSL`** already controlled certificate checking for every outbound request and now also covers the mail server that sends email alerts. The startup summary now shows `TLS verification` and moves that row into the concise view while verification is off, and **`--doctor`** reports a warning naming the setting. The repeated certificate warning is silenced once the config file has been read, so the choice is reported once instead of on every request. Setting it to `False` still only makes sense on a network that intercepts TLS with its own certificate authority
- **NEW:** **`--set-smtp-password` saves the mail server password privately** - Enter `SMTP_PASSWORD` through a hidden prompt instead of editing the dotenv file by hand. The mail server has to accept the password before it is written and no email is sent, so a wrong password, or an app password the provider requires, is reported straight away. A refused sign-in leaves the dotenv file unchanged, and a password already saved there is replaced only after you confirm. The command ends with the same labelled next-step commands the other one-shot commands print.
- **IMPROVE:** **Email setup is checked before it is saved** - **`--setup`** now signs in to the mail server after the last email question, so a wrong password or an unreachable host is reported during setup instead of at the first alert. No email is sent. A refused sign-in offers the mail server questions again, and giving up switches email alerts off. An unreachable server keeps the answers instead, so `--doctor` can check them once the machine is back online. The mail server questions now show the values already saved as defaults, so re-running setup no longer means retyping a working mail server. The SMTP port question now refuses a number outside 1 through 65535, so setup can no longer save a port `--doctor` would then reject. Declining the retry offer at a number question keeps the value already saved instead of asking the same question again.
- **IMPROVE:** **A way out of every rejected setup answer** - **`--setup`** no longer repeats a prompt you cannot answer, in either monitoring mode. A blank entry asks whether to continue without it and names what stops working, and an entry it cannot use offers to enter it again. Declining keeps every answer already given and switches off only the part that needed the value, so half a mail server, a webhook with no destination or a Spotify app with no Client ID is never written
- **IMPROVE:** **Names, IDs and links have their own colours** - Display names are `bright_cyan underline`, Spotify user IDs and URIs are `bright_magenta` and URLs are `blue underline`, so a name is never mistaken for a link. The `Target:` row is coloured as the ID it holds. The same three colours mean the same three things in every monitor in this family. The `user_uri_id` theme key is now **`id`** and a configuration file that still sets `user_uri_id` keeps working
- **IMPROVE:** **A generated configuration no longer freezes the colours** - `COLOR_THEME` now ships commented out, so the tool's own defaults apply and a later change to them reaches you. Uncomment it to override colours and keep only the lines you want to change. **A configuration file written by an earlier version sets every colour explicitly and therefore keeps the old ones**: delete its `COLOR_THEME` block to follow the current defaults, or edit the values you want to keep. Such a file still loads unchanged
- **IMPROVE:** **Doctor names every output destination** - The Configuration section now says when CSV or log output is disabled instead of leaving the row out, so the report always states which files monitoring would write
- **NEW:** **Setup chooses the log and CSV output** - `--setup` now ends with an **Output files** section that asks whether the per-target log file is written and takes an optional CSV path, where a blank answer disables CSV output and a path with no extension is saved with `.csv` added. Both settings appear in the review summary and can be changed from the section editor before saving
- **IMPROVE:** **Doctor and setup read the same as the sibling monitors** - Each ready notification row now lists the **alert categories** that channel would deliver. The setup summary aligns its rows, names the **webhook provider** and colour-codes values such as the target, the polling interval and each enabled or disabled channel. `--set-sp-dc`, `--set-lastfm-credentials`, `--set-webhook-url` and `--import-browser-cookie` end with the same labelled next-step commands the wizard prints. Doctor also reports the optional `colorama` package, and reports it only on Windows, since the classic Command Prompt is the only place it changes anything. **Hidden prompts look like every other question**, such as the cookie or password prompt. Debug output stays off while a secret is typed. The Python row names the minimum version the tool supports, and a numeric setting that is merely valid no longer takes a row of its own. Detail lines now carry only what the label does not, so a disabled CSV file, log file or webhook channel no longer repeats itself on a second line. Each row is now one block: the `To fix:` and `Guide:` lines sit indented under their marker alongside the detail. A check that could not run, such as connectivity after a failed sign-in, is now `[SKIP]` instead of `[WARN]`, so it no longer counts towards the warning total. Setup groups its questions the way the siblings group theirs, so the polling question opens its own block instead of running on from the target answer. Every command it prints for you to run is now the short portable form (`python3 spotify_monitor.py ...` for a downloaded script) and carries the `--config-file` or `--env-file` this run was given, so it can be pasted as it is. Doctor's Connectivity section now opens with the shared endpoint row, naming the endpoint the tool contacts at startup, ahead of the service check. Doctor now ends with the command that starts monitoring whatever the verdict, labelled so a failing report asks for the failures first The optional delivery tests now name the webhook provider in every result row and each row explains its outcome, so an approved test that failed points at the error above and a declined one says how to approve it next time. The one-shot secret commands now name the secret rather than its dotenv key when they ask to replace it, so `--set-sp-dc` and `--set-lastfm-credentials` read the way `--set-webhook-url` and `--set-smtp-password` already did. Doctor's progress line calls the target step `the monitored profile`, the label every sibling uses. Doctor rows are now colour-coded by status, the connectivity endpoint is probed before authentication, a row that could not run reads `was not checked` and a `--env-file` path that does not exist is a warning rather than a failure, as in the siblings. An email or webhook channel that is configured with no alert types selected is reported as a warning. After saving, setup offers `--doctor` whenever a target was given, runs the same report as the `--doctor` command and offers to start monitoring only after that run passed. A rerun proposes the saved webhook switch as the default of the webhook question and proposes email when the saved settings already send it. The review menu uses the sibling section labels and a switched-off destination such as `--config-file none` is refused with the shared message.
- **IMPROVE:** **A missing target is reported first** - Starting without a target now names the **missing target** before the `sp_dc` cookie is checked, so a first run is told the simpler problem first. `--list-friends` and the Protobuf decoding modes still run without one
- **IMPROVE:** **Readable debug traces and quieter verbose output** - Every **`--debug`** line now names the operation, then lists its details as comma-separated `key=value` fields, so a long trace is scannable instead of one run-on sentence. Every outbound call reports `outcome=OK` or `outcome=failed` with an `error=` field. **`--verbose`** says when an alert channel was switched off because `SMTP_HOST` or `WEBHOOK_URL` is still a placeholder, and prints each operational notice raised during monitoring, such as a token refresh, as its own block closed by the same `Timestamp:` line and separator as every other block. Notices printed before monitoring starts stay part of the startup screen, which the monitoring header closes. Scrobble health mode follows the same rule: after the first check it reports the checks where the health result changes, plus a liveness banner every `LIVENESS_CHECK_INTERVAL`, instead of repeating an unchanged result on every check. It **stays quiet between events** instead of printing a line per check, which `--debug` records instead. A `--debug` run also leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen, while `--verbose` clears it like an ordinary run. Routine Spotify token refreshes are now `--debug` detail rather than verbose notices, so a verbose run stays quiet between real events. The format matches the sibling monitors
- **IMPROVE:** **The startup summary reads the same as the sibling monitors** - The rows now appear in the shared order: what is monitored, how often, where alerts go, where output goes, then this tool's own features, with the environment rows last. `TLS verification` and `ASCII log separators` moved into that last block, a new `Coloured output` row reports whether colour is actually in use, and the secret origins are now three rows naming what came from the dotenv file, the environment and the configuration file. Scrobble health mode ends with the same `More details` line as normal mode
- **IMPROVE:** **Install method and effective secret origins in diagnostics** - `--verbose` and `--debug` show a readable install method and name the effective source of each secret. Doctor opens with the raw `manual`, `pip`, `docker` or `compose` method used by support reports. An exported value wins when the same key also exists in the dotenv file. Explicit command-line values are identified separately. Only secret names are shown, never values. The default concise startup view is unchanged
- **IMPROVE:** **A clearer `--help` screen** - The argument groups now appear in the order shared with the sibling monitors, with **`Email notifications`** and **`Webhook notifications`** named apart so one group name no longer stands for both. `--setup`, `--doctor`, `--generate-config`, `--set-sp-dc`, `--set-lastfm-credentials` and `--set-webhook-url` sit together under **`Configuration & dotenv files`**. The examples are grouped by task, one heading per thing you might be trying to do, with a comment above each command saying what it is for. Every command is written for the detected install method. The one-shot commands - `--setup`, `--doctor`, the `--set-*` commands and the `--send-test-*` commands - describe themselves with the same sentence in every monitor, so the same command no longer reads as a different one in each tool
- **IMPROVE:** **One-shot commands keep the screen** - **`--doctor`**, **`--help`**, the `--set-*` commands and the `--send-test-*` commands no longer clear the terminal, so their output stays in the scrollback and can be pasted into a bug report. Monitoring runs and `--setup` still start on a clean screen when `CLEAR_SCREEN` is on.
- **IMPROVE:** **Test commands send the same message in every monitor** - **`--send-test-email`** and **`--send-test-webhook`** now use one subject and one body shared by the sibling monitors. The body names the command that sent it, so a test message arriving beside real alerts is easy to place
- **IMPROVE:** **Doctor warns about a check interval that invites rate limiting** - A **`SPOTIFY_CHECK_INTERVAL`** below 30 seconds now gets its own `[WARN]` row naming the interval in use and the setting to raise. A rate-limited account looks like a broken tool rather than a setting, so the warning arrives before the run instead of during it. The same row appears in every monitor in this family

**Bug fixes**:

- **BUGFIX:** **Setup checks a manually entered `sp_dc` cookie** - Choosing to paste an existing `sp_dc` value in `--setup` saved it without asking Spotify whether it worked, so an expired cookie was written and only reported at the first check. The same applied to the private-entry recovery offered after a failed browser import, which also recorded the cookie as unvalidated. Setup now reports `Checking the cookie with Spotify ...` and only saves a cookie Spotify accepts. A rejected one names the reason and offers another authentication method, matching `--set-sp-dc`
- **BUGFIX:** **A late scrobble no longer reports the same track twice** - In scrobble health monitoring a play Spotify had finished but Last.fm had not recorded yet moved the result to `Waiting`, which `--verbose` reported as a change, then reported again as `Healthy` once the scrobble arrived. An active listening session produced one such pair per track. `Waiting` is now treated as no news, so it neither reports nor replaces the last reported result. An outage that a late scrobble briefly interrupts is no longer announced a second time either. Outages, recoveries and their alerts are unchanged
- **BUGFIX:** **The liveness banner now follows the clock** - Its cadence was counted in checks derived from **`SPOTIFY_CHECK_INTERVAL`**, so it drifted from the interval you configured: with a check interval longer than **`LIVENESS_CHECK_INTERVAL`** the banner printed after every check. During an outage the reminder was spaced by **`SPOTIFY_ERROR_INTERVAL`** instead, which stretched it to days. The banner and the outage reminder now print once per **`LIVENESS_CHECK_INTERVAL`** of elapsed time
- **BUGFIX:** **The liveness banner explains itself without `--verbose`** - The banner printed `* Monitoring healthy for <user_uri_id> ...` only under **`--verbose`**, while its `Liveness check, timestamp:` line printed either way, so a plain run showed a bare timestamp every `LIVENESS_CHECK_INTERVAL` with nothing saying what it was. Both lines now print in any mode
- **BUGFIX:** **A failed check is reported when it happens** - A Spotify outage or network failure printed nothing until it had repeated six times over a set period, so a run that stopped working looked idle. The first failure is now reported straight away with its `To fix:` action. While it lasts the summary is not repeated: the liveness banner takes over with `* Monitoring degraded for <user_uri_id>` and what is still failing, once per **`LIVENESS_CHECK_INTERVAL`** however often the failing run retries. Once it clears, `* Monitoring recovered for <user_uri_id>` reports how long the outage lasted. With **`LIVENESS_CHECK_INTERVAL`** set to 0 there is no banner to carry the reminder, so the aggregated 50x and network summaries keep their old cadence The report line itself now reads `* Error: <what failed> (retrying in <time>)`, the same shape every monitor in this family prints
- **BUGFIX:** **Ctrl+C leaves the optional delivery tests** - Pressing Ctrl+C at `Send one test email now?` declined only that one test, then the webhook prompt appeared and declined the same way, so there was no way out of the section. Ctrl+C now ends the run there, the way it does everywhere else
- **BUGFIX:** **The printed monitoring command carries a usable target** - After `--import-browser-cookie`, `--set-sp-dc`, `--doctor` and setup, the command printed under `start monitoring` used `SPOTIFY_USER_URI_ID` in place of a target, so pasting it failed even when a target was already saved in the configuration file. In setup it left the target out entirely when you chose not to persist it, which left the command unable to run. It now carries the target the run used, leaves the positional out when the configuration file already supplies one and otherwise shows `<spotify_target>` for you to replace. The `--doctor` command above it follows the same rule without the placeholder, since Doctor reports a missing target itself
- **BUGFIX:** **The ntfy setup hint no longer sends you to the wrong value** - The webhook question said to paste the topic name for `ntfy.sh` and the complete HTTPS URL for a self-hosted server, which reads as though a full `https://ntfy.sh/...` URL would be refused. It was always accepted. The hint now says to paste the complete topic URL, or just the topic name when it is hosted on ntfy.sh, matching the prompt printed directly below it
- **BUGFIX:** **Every screen names every target form it accepts** - The setup question asked for a `Spotify profile URL or user ID` and the welcome screen said the same, so a `spotify:user:USER_ID` URI read as unsupported. It was always accepted, and the message shown after a rejected answer already said so. Both now name all three forms, matching spotify_profile_monitor, and the examples use the same `<spotify_target>` placeholder as the rest of the screen
- **BUGFIX:** **A failed delivery test no longer reports a clean run** - **`--doctor`** printed the `Summary` line before offering the optional email and webhook tests, so an approved test that failed still printed `All checks passed. You are good to go!` while the command exited `1`. The summary is now printed after the tests finish and counts their results, in the normal report, in the focused scrobble health report and in the Doctor run setup offers, so the sentence and the exit code always describe the same run
- **BUGFIX:** **Ctrl+C during setup reports what happened to your files** - Interrupting a setup, secret or Doctor question ended the run with `* You pressed Ctrl+C, tool is terminated.`, because the shared signal handler answered before the prompt could. Every prompt now reports its own outcome: `Setup cancelled. Destination files were not changed.` before anything is written, and at the `Run doctor now?` and `Start monitoring now?` questions that follow the save, setup says it is saved and prints the next-step commands instead of claiming a cancellation. Ctrl+C outside a prompt still ends the tool the same way it always did
- **BUGFIX:** **An unset webhook destination switches the channel off** - With `WEBHOOK_ENABLED = True` and a `WEBHOOK_URL` left unset or still holding its `your_webhook_url` placeholder, every alert failed with `WEBHOOK_URL must contain a complete HTTPS link`. Webhook alerts are now switched off at startup instead, and `--verbose` reports why
- **BUGFIX:** **A disabled config search reaches the command the error suggests** - After `--config-file none`, the Firefox cookie import command printed with a rejected cookie left that value out. Pasting it started an import that picked up a `spotify_monitor.conf` in the working directory, which the run reporting the error had ignored. The command now carries `--config-file none`
- **BUGFIX:** **A name with an apostrophe is coloured whole** - A track, playlist or album name containing an apostrophe, such as `Don't Stop Me Now`, was coloured only up to that apostrophe and the rest of the name was left plain. The whole name is now coloured. A quoted **`<placeholder>`**, a quoted command-line option such as `'--env-file none'` and a quoted piece of a URL such as `'?code='` are no longer coloured as names, since each is text to replace or retype rather than something the tool read from Spotify
- **BUGFIX:** **Ordinary words and sentence punctuation are no longer coloured** - The word after `user` was coloured as a **Spotify user ID**, so setup and configuration text such as `Spotify user to monitor` or `check for user activity` highlighted the wrong word. Only a value that looks like an identifier, or one written as a `user:` or `user=` field, is coloured now. A **link** no longer swallows the character that follows it, so the closing bracket, quote or full stop after a URL stays outside the underline
- **BUGFIX:** **`--no-color` now leaves the help screen plain on Python 3.14** - From Python 3.14 argparse colours the help screen itself. `--no-color`, `NO_COLOR` and a redirected output stream switched off this tool's own colours but not argparse's, so `--help` still carried a second palette this tool could not silence. The help screen is now coloured by this tool alone
- **BUGFIX:** **Truncation no longer counts colour codes as visible characters** - With **`TRUNCATE_CHARS`** or **`--truncate`** set, a line that was already coloured lost about five characters for every colour change, because the invisible escape sequence was measured as if it were text. Colour sequences are now copied through without spending any of the width, so a truncated line shows as many visible characters as you asked for
- **BUGFIX:** **A cancelled secret command says it was cancelled** - Ctrl+C or an `n` at the `Replace the saved ...?` question of `--set-sp-dc`, `--set-lastfm-credentials`, `--set-webhook-url` or `--set-smtp-password` was reported as `The webhook URL was not changed` or `SP_DC_COOKIE was not changed`, with advice about copying a fresh value that fits neither outcome. A cancel now says so and names the command that resumes it. A declined replacement says the saved value was left as it is and names the answer that replaces it
- **BUGFIX:** **Email settings that were never filled in no longer fail Doctor** - `--doctor` reported `[FAIL] The SMTP configuration is incomplete or invalid` when email alerts were on with placeholder SMTP credentials, and that alone made it exit 1. A channel that is switched on but cannot deliver is now `[WARN] Email alerts are enabled but unusable`, with a detail line naming the settings at fault and a `To fix:` naming the same ones. Only a real failure still changes the exit code
- **BUGFIX:** **A declined setup section no longer keeps the old settings** - Re-running **`--setup`** over an existing configuration builds the new file from the settings already in place, so declining the email questions left the previous SMTP host, username, sender and receiver in the saved file while the summary reported email as disabled. A declined section is now cleared back to the unset defaults. The replace question also states that the rebuilt file starts from the current settings rather than from defaults

# Changes in 3.3.1 (28 Aug 2026)

Version **3.3.1** makes explicit **`--debug` and `--verbose` flags cover configuration startup** while preserving their precedence over saved defaults, and stops settings, diagnostics and fallback notices from being coloured as errors.

**Bug fixes**:

- **BUGFIX:** **Diagnostic flags cover configuration startup** - Explicit **`--debug`** and **`--verbose`** flags now take effect before configuration errors are reported, then remain enabled after the selected config loads
- **BUGFIX:** **Accurate error colouring** - Lines that only mention a problem word are no longer painted red. The **`Disappeared timer`** and **`Error retry timer`** rows shown by **`--verbose`**, every **`[DEBUG]`** trace line, including the ones recording a retried or handled request, and the notice about switching to the web-player backend now keep their normal colours, while real failures stay red

# Changes in 3.3 (27 Aug 2026)

Version **3.3** adds **coloured terminal output** with a customizable theme, fixes **false Last.fm outage alerts**, retries **failed alert delivery** and escapes a friend's display name in email notifications. **Pillow is now optional**, **config files are parsed instead of executed**, access tokens are reused until they expire and releases ship with a checksum file plus a signed build attestation.

**Features and improvements**:

- **NEW:** **Coloured terminal output** - Live output is now coloured by default: usernames, track, playlist and album names, dates, durations, counters and links each get their own colour, while errors, warnings and received signals are highlighted as whole lines. Override any part through **`COLOR_THEME`**, which merges over the built-in theme, and turn colour off with **`--no-color`** or `COLORED_OUTPUT = False`. Colour switches itself off when output is redirected or piped, when `TERM` is unset or `dumb` and when `NO_COLOR` is set. **Log files stay plain text**, so `grep` and `tail` are unaffected, and the existing **grc** recipe still colours saved logs. Install the optional `colorama` package for the classic Windows Command Prompt
- **CONFIG CHANGE:** **Artwork is now an optional extra** - **Pillow is no longer required**. Artwork moved to the `notification-images` extra and `NTFY_IMAGES` now defaults to `False`. Install with `pip install "spotify_monitor[notification-images]"` or let setup do it for you. **Upgraders who want cover art back should install the extra and set `NTFY_IMAGES = True`**
- **IMPROVE:** **Fewer Friend Activity requests** - Cached access tokens are now reused until they expire, roughly halving the number of requests
- **IMPROVE:** **Refreshed, automatically published Docker images** - Both images now run Python 3.13 on Debian 13 with a digest-pinned, patched base and no `pip` in the runtime, so a fresh pull carries no known fixable high/critical vulnerabilities. The secret grabber image is now built, versioned and published automatically, runs as a non-root user and is rebuilt weekly for security updates
- **IMPROVE:** **Clearer ntfy webhook customization** - `WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` are documented as Discord-only; customize ntfy delivery through `WEBHOOK_HEADERS`
- **IMPROVE:** **Checksums and signed attestation for releases** - Releases now ship a `SHA256SUMS.txt`, a signed build attestation checkable with `gh attestation verify` and the attestation bundle itself as an **`.intoto.jsonl` asset**, so provenance can be verified from the downloaded files without calling GitHub
- **IMPROVE:** **Releases publish only after the tests pass** - PyPI and Docker Hub releases can no longer publish unless the full test suite passes, every workflow action is pinned to a commit SHA, release tags reach the workflow through the environment instead of a shell command and `--version` is checked against package metadata and these notes
- **IMPROVE:** **Automated checks on every change** - A pinned Ruff lint pass now runs in CI ahead of the test suite, which covers Python 3.9 through 3.14 plus a Windows job. Optional pre-commit hooks and a shared `.editorconfig` catch the same issues before you commit
- **IMPROVE:** **Continuous security scanning** - Dependencies, images and source are scanned on every change and weekly, with a published SBOM, Dependabot coverage for Python dependencies and a public OpenSSF Scorecard rating
- **IMPROVE:** **Security policy and support guidance** - Added private vulnerability reporting, [SUPPORT.md](https://github.com/misiektoja/spotify_monitor/blob/main/SUPPORT.md), contribution guidance, a code of conduct, a dependency licensing notice and issue templates that collect version, install method and `--doctor` output
- **IMPROVE:** Corrected and improved wording in setup wizard and doctor preflight

**Bug fixes**:

- **BUGFIX:** **No more false Last.fm outages** - Repeated plays are now matched pairwise instead of greedily
- **BUGFIX:** **Alerts retried until every channel succeeds** - Failed Friend Activity and scrobble-health alerts stay pending until every enabled email and webhook channel goes through. Successful channels are not sent again while another channel retries
- **BUGFIX:** **Clearer missing-play alerts** - Outage notifications now name the first missing play and correctly label the displayed tracks
- **BUGFIX:** **Reliable Spotify links** - Links built from a Spotify URI are now parsed exactly instead of guessed
- **BUGFIX:** **Accurate dotenv and activity-file state** - `SIGHUP` now clears removed secrets and resets caches while activity flag files are written atomically
- **BUGFIX:** **Hardened email notifications** - A friend's display name is now escaped in emails, so it can no longer inject markup, a live link or a tracking image
- **BUGFIX:** **Terminal-safe Spotify text** - Spotify-supplied friend, artist, track, album and context names are stripped of terminal control sequences before reaching the console or log file, including `--list-friends` and normal monitoring output. Colour codes are the one exception, since they can only change how text looks, and they are still removed from everything written to a log file
- **BUGFIX:** **Webhook delivery respects `VERIFY_SSL`** - Discord and ntfy now honor the same TLS setting as other requests and follow no redirects, so alert content and headers cannot reach an unconfigured host
- **BUGFIX:** **Configuration files are read as data** - The config file is now parsed instead of executed, so it can no longer run code at startup. Settings dropped by older upgrades are ignored gracefully and config backups keep owner-only permissions
- **BUGFIX:** **Connectivity check respects configuration** - The startup internet check now honors `CHECK_INTERNET_URL`, `CHECK_INTERNET_TIMEOUT` and `VERIFY_SSL`
- **BUGFIX:** **Reliable anti-hang watchdog** - The watchdog can no longer be disabled by a nested request timer
- **BUGFIX:** **Safer debug utilities** - `spotify_monitor_totp_test` now accepts only HTTPS Spotify destinations for token validation and follows no redirects
- **BUGFIX:** **Smaller fixes** - Generated config preserves emoji, track IDs are validated before local playback and the direct Linux container instructions map host IDs when they differ from 1000

# Changes in 3.2.1 (04 Aug 2026)

Version **3.2.1** makes Spotify-to-Last.fm token refreshes more resilient, adds portable log files and streamlines Friend Activity setup, help and diagnostics.

**Features and improvements**:

- **IMPROVE:** **Portable log separators** - The new `ASCII_LOG_SEPARATORS` setting controls whether separator-only lines saved to log files use ASCII hyphens. `"Auto"` enables them on Windows by default, `"On"` enables them on every operating system and `"Off"` preserves Unicode separators. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.
- **IMPROVE:** **Flexible setup intervals** - The setup wizard accepts polling interval durations such as `30s`, `2m`, `1.5h`, `1h 30m` and `1d` while still saving the value as seconds
- **IMPROVE:** **Focused command-line help** - `--help` now groups concise examples into Friend Activity and Scrobble Health sections so the main setup, monitoring and diagnostic commands are easier to find
- **IMPROVE:** **Actionable Doctor output** - Details remain attached to their checks, final target-specific log destinations are validated and `pycookiecheat` is clearly identified as a Chromium-only import dependency that Firefox does not need
- **IMPROVE:** **Clearer Friend Activity guidance** - Setup examples consistently document Spotify user IDs, URIs and profile URLs while in-app recovery links open the correct target guide

**Bug fixes**:

- **BUGFIX:** **Resilient recent-play token refreshes** - Spotify-to-Last.fm monitoring now retries a connection failure, timeout or temporary 5xx response once after a short delay. Rate limits and rejected credentials still return directly to the existing backoff and recovery handling

# Changes in 3.2 (31 Jul 2026)

Version **3.2** adds **Spotify-to-Last.fm scrobble health monitoring** plus flexible **webhook runtime controls and request customization** for Discord, ntfy and advanced integrations.

**Features and improvements**:

- **NEW:** Added **Spotify-to-Last.fm scrobble health monitoring** to address new Spotify's six-month re-authorization requirement and warn when Spotify scrobbles stop showing up on Last.fm. Reconnecting may recover only the 50 most recent Spotify plays, so early detection reduces the risk of a permanent gap. The monitor compares recent plays automatically then sends console, email or webhook alerts when the problem persists and again when scrobbling recovers
- **NEW:** Added one-run **webhook provider, URL and error-notification controls** while retaining `--set-webhook-url` as the recommended way to save private destinations
- **NEW:** Added **customizable Discord-format payloads** through `WEBHOOK_AVATAR_URL`, `WEBHOOK_TEMPLATE`, `WEBHOOK_TRANSFORMS` and placeholder-aware `WEBHOOK_HEADERS`
- **NEW:** Added **compact ntfy activity alerts** through `NTFY_SHORT` while keeping Discord, email and error notification details unchanged (thanks [@tomballgithub](https://github.com/tomballgithub), [#44](https://github.com/misiektoja/spotify_monitor/pull/44))
- **IMPROVE:** Added **webhook request validation** during Doctor checks and delivery plus automatic provider correction for standard Discord and `ntfy.sh` URLs
- **IMPROVE:** Split the startup notification summary into compact **email and webhook rows** with short labels and unstarred continuation lines across concise, verbose and logged views (thanks [@tomballgithub](https://github.com/tomballgithub), [#46](https://github.com/misiektoja/spotify_monitor/pull/46))
- **IMPROVE:** Added portable beginner Python installation walkthroughs for Windows, macOS and Debian-family Linux systems

**Bug fixes**:

- **BUGFIX:** Applied terminal-width auto-detection when `TRUNCATE_CHARS = 999` comes from configuration while preserving `--truncate` precedence and skipping truncation when logging is disabled (thanks [@tomballgithub](https://github.com/tomballgithub), [#45](https://github.com/misiektoja/spotify_monitor/pull/45))
- **BUGFIX:** Kept long ntfy text notifications below the server's 4 KB attachment boundary and added a visible truncation marker
- **BUGFIX:** Made `SIGHUP` clear cached Spotify authentication after credential rotation and redetect Discord or ntfy when the private webhook destination changes

# Changes in 3.1.1 (24 Jul 2026)

**Bug fixes**:

- **BUGFIX:** Updated the built-in guide link to the renamed **Setup & First Run** page so CLI help and recovery guidance no longer point to the retired Quick Start URL

# Changes in 3.1 (23 Jul 2026)

Version **3.1** makes **Docker onboarding portable across macOS, Linux and Windows**. Setup now centers on **host-aware Firefox authentication**, keeps configuration and secrets on the persistent **`/data` bind mount** and carries exact **Doctor and monitoring commands** through recovery.

**Features and improvements**:

- **IMPROVE:** Kept Firefox import as the **recommended Docker authentication path** while making its deferred workflow explicit. Setup now asks whether Docker runs on macOS, standard Linux, Linux with Snap, Linux with Flatpak, Windows PowerShell or Windows Command Prompt then prints the matching read-only profile mount
- **NEW:** Added **Windows-host Firefox import** for direct Docker and Docker Compose through the normal `%APPDATA%\Mozilla\Firefox` profile root with shell-specific PowerShell and Command Prompt commands
- **IMPROVE:** Deferred **Doctor until Firefox authentication has been imported**. Container setup now finishes with ordered commands to import the login, verify authentication and the target then start monitoring
- **IMPROVE:** Preserved **setup guidance across one-time authentication commands** by keeping terminal history visible and repeating the exact Doctor and monitoring commands after a successful Firefox import
- **IMPROVE:** Printed the **install-aware monitoring command** after a successful Doctor run while preserving explicit or saved targets and selected configuration files

**Bug fixes**:

- **BUGFIX:** Fixed generated Docker commands that used the container UID `10001:10001` and always assumed the Linux `~/.mozilla/firefox` profile path. **macOS commands omit Linux user mapping** while Linux commands resolve the host user and group IDs in the host shell
- **BUGFIX:** Stopped standalone container recovery guidance from presenting one Linux-only Firefox command when the Docker host is unknown
- **BUGFIX:** Anchored **default container setup files** to the bind-mounted **`/data` directory** so the generated configuration and dotenv files survive the temporary setup container
- **BUGFIX:** Rejected **Docker setup destinations outside `/data`** instead of saving ephemeral files then printing commands for different paths
- **BUGFIX:** Generated direct Docker commands with **`${PWD}` for macOS, Linux and Windows PowerShell** then switched to `%cd%` for Windows Command Prompt while retaining Linux user mapping
- **BUGFIX:** Saved the **selected dotenv destination** in generated configuration so later config-only starts and secret reloads keep using it
- **BUGFIX:** Printed an **explicit Compose monitoring command** when setup uses nondefault config or dotenv paths instead of falling back to hardcoded defaults
- **BUGFIX:** Preserved the selected configuration path through the hidden **`--set-sp-dc` fallback** and its Doctor and monitoring guidance
- **BUGFIX:** Prevented a **Windows traceback after Ctrl+C** when monitoring was started directly from setup. The setup parent now treats its duplicate console interrupt as the same clean termination already handled by the monitoring child

# Changes in 3.0.1 (22 Jul 2026)

**Features and improvements**:

- **IMPROVE:** Made Firefox login import the recommended Docker and Docker Compose authentication path. A one-time read-only host profile mount imports `sp_dc` into the persistent `.env` file, later runs no longer need the browser mount and hidden manual cookie entry remains available as a fallback
- **IMPROVE:** Updated `spotify_monitor_totp_test --fetch-secrets` to scan current web-player bundles for inline TOTP secret objects while retaining the original runtime hook for older bundle formats

**Bug fixes**:

- **BUGFIX:** Fixed Docker Compose startup after guided setup. The default service command now loads `/data/.env` explicitly, preventing `docker compose up` from reporting a missing `SP_DC_COOKIE` when setup and doctor already saved and validated it

# Changes in 3.0 (22 Jul 2026)

Version **3.0** focuses on making Spotify Monitor easier to set up, safer to configure and easier to recover when something goes wrong. It adds guided onboarding, simpler Spotify login, Docker Compose, clearer terminal output and Discord + ntfy webhook alerts while keeping advanced client mode available for experienced users.

Special thanks to [@tomballgithub](https://github.com/tomballgithub) for testing this release in real time and providing valuable feedback.

**Features and Improvements**:

- **NEW:** Added an **automatic public web-player metadata backend** for track and public playlist details. Spotify's current Development Mode restrictions can block the required legacy Web API endpoints, so version 3.0 can retrieve the same monitoring data without depending on a new Spotify OAuth app. It refreshes temporary tokens, adapts when Spotify changes web-player queries and retries brief Spotify service failures automatically
- **IMPROVE:** Made **Spotify OAuth app credentials optional** in cookie and client modes. Existing complete `SP_APP_CLIENT_ID` and `SP_APP_CLIENT_SECRET` configurations remain supported and are tried first. If the legacy Web API is restricted, track and playlist metadata switch independently to the web-player backend. Startup output now shows the login token source and metadata backend separately
- **IMPROVE:** Clarified that Spotify requires the owner of every **Development Mode app** to keep an active Premium subscription regardless of app creation date. Doctor recovery guidance now checks this first while retaining automatic web-player fallback because an HTTP 403 alone does not prove its cause
- **BUGFIX:** Preserved **Spotify-curated playlist detection** when the legacy Web API returns HTTP 404. Web-player owner metadata now distinguishes a curated-playlist restriction from an app-wide legacy restriction and caches the correct routing decision
- **NEW:** Added **webhook notifications for Discord and ntfy** for active, inactive, tracked-song, every-song, loop and error events. Choose the service in the setup wizard or with `WEBHOOK_PROVIDER`, store the private URL with `--set-webhook-url` and test it with `--send-test-webhook`. Discord remains the default while ntfy uses its native topic API. Email and webhook delivery work independently
- **NEW:** Added **authentication for protected ntfy topics** via `NTFY_ACCESS_TOKEN` support with Bearer authentication and custom `Authorization` headers in `WEBHOOK_HEADERS`
- **NEW:** Added **playlist and album artwork in ntfy alerts**, enabled by default and configurable through `NTFY_IMAGES`. Set it to `False` to keep ntfy alerts text-only. Active and inactive alerts prefer playlist artwork then fall back to album artwork, while tracked-song, every-song and loop alerts use album artwork (thanks [@tomballgithub](https://github.com/tomballgithub), [#39](https://github.com/misiektoja/spotify_monitor/pull/39))
- **NEW:** Added an **interactive setup wizard** for first-time setup. Run `--setup` or launch the tool with no arguments and accept the prompt. The wizard detects PyPI, downloaded-script, Docker and Docker Compose installs, writes a ready-to-run `spotify_monitor.conf`, keeps private values in `.env` and can check or start local monitoring immediately
- **NEW:** Added a **confirmed target follow step** to setup for cookie and advanced client authentication. The wizard checks the configured account through Spotify's private web-player operations, offers a follow prompt only when needed and verifies the follow state after every approved request
- **NEW:** Added **browser-based `sp_dc` import** from **Firefox, Chrome, Brave and Chromium** with profile selection. Firefox needs no extra dependency and works on macOS, Linux and Windows. Chromium-based import is optional on macOS and Linux, while Windows users are guided to Firefox
- **IMPROVE:** Made **targets and configuration easier to use**. Targets can be raw Spotify user IDs, `spotify:user` URIs or profile URLs and can be saved as `TARGET_USER_URI_ID`. Broken config files report the offending line, config writes create recoverable backups and private values stay hidden from normal or debug output
- **NEW:** Added **private `sp_dc` entry** with `--set-sp-dc`. The cookie is entered through a hidden prompt, checked with Spotify and saved only after validation. This is the recommended setup path for Docker and Docker Compose
- **NEW:** Added a file-safe **`--doctor` self-check** for configuration, secrets, Spotify authentication, metadata backends, connectivity, target visibility and notifications. Configured legacy OAuth metadata uses a memory-only live check and becomes a warning when the automatic web-player fallback succeeds. Interactive runs offer separate delivery tests for email and webhook channels. Each approved test sends one real message while non-interactive runs remain message-free. Common failures now include a clear **`To fix:` next step** instead of only a technical error
- **CONFIG CHANGE:** Changed **TOTP secret handling** for cookie mode. Version 3.0 embeds the current v61 cipher and no longer downloads a third-party secret dictionary. Existing configs keep working with the built-in default, but `SECRET_CIPHER_DICT`, `SECRET_CIPHER_DICT_URL` and `TOTP_VER` no longer control token generation. Future overrides use `TOTP_VERSION` and `TOTP_SECRET_CIPHER_BYTES`, which `--doctor` checks. The updated `spotify_monitor_secret_grabber` v1.3 can extract replacement values if Spotify rotates them
- **IMPROVE:** Updated `spotify_monitor_secret_grabber` to v1.3 so it extracts current inline object-literal TOTP secrets while retaining the original runtime hook for older bundle formats
- **NEW:** Added a **non-root Docker image**, **Docker Compose quick start** and a copyable **`.env.example`**. Setup commands adapt to containers and the release workflow supports `linux/amd64` plus `linux/arm64` images
- **IMPROVE:** Added a friendlier **terminal experience** with a pure ASCII equalizer banner, a short no-arguments welcome, a concise startup summary and install-aware examples in `--help`. Use `--verbose` for the complete non-secret summary plus occasional operational details
- **NEW:** Published a **documentation site** at [misiektoja.github.io/spotify_monitor](https://misiektoja.github.io/spotify_monitor/), built with MkDocs Material and deployed through GitHub Actions. The README is now a concise landing page while installation, configuration, usage, troubleshooting and debugging have dedicated guides
- **IMPROVE:** Added an editable setup summary so answers can be reviewed before saving
- **IMPROVE:** Simplified browser onboarding with separate Firefox and Chromium choices plus optional `pycookiecheat` installation
- **IMPROVE:** Made generated commands portable across Python installations and custom config paths
- **IMPROVE:** Added confirmation, backups and validation when replacing configuration files
- **BUGFIX:** No-argument launches now honor saved targets
- **BUGFIX:** Improved Docker and Compose support for Linux user mappings, persistent sessions and saved interface choices
- **IMPROVE:** Updated support to **Python 3.9 through 3.14** and made Spotipy optional. It is now needed only for the advanced legacy OAuth metadata path

# Changes in 2.9.2 (27 Apr 2026)

**Bug fixes**:

- **BUGFIX:** Bounded the retry loop in `spotify_get_access_token_from_sp_dc` to prevent an infinite loop when TOTP secrets are repeatedly fetched but the resulting token refresh keeps failing (thanks [@tomballgithub](https://github.com/tomballgithub), fixes [#37](https://github.com/misiektoja/spotify_monitor/issues/37))
- **BUGFIX:** Auto-fallback to the highest available TOTP version when the configured `TOTP_VER` is missing from `SECRET_CIPHER_DICT` (with a warning) so the script self-heals instead of failing every retry

# Changes in 2.9.1 (09 Mar 2026)

**Features and Improvements**:

- **IMPROVE:** Updated SECRET_CIPHER_DICT_URL used in `cookie` mode and enabled last v61 secret since it does not appear to be rotated anymore

# Changes in 2.9 (23 Feb 2026)

**Features and Improvements**:

- **NEW:** Added configuration option `SPOTIFY_SUFFIX` to allow a **custom string** after **Spotify-curated public playlists** (thanks [@tomballgithub](https://github.com/tomballgithub))
- **NEW:** Added **debug mode** with `DEBUG_MODE` config option and `--debug` CLI flag for technical troubleshooting output

**Bug fixes**:

- **BUGFIX:** Capped server-provided `Retry-After` for HTTP 429 responses to avoid long hangs
- **BUGFIX:** Fixed fetching of TOTP secrets so it happens before retries

# Changes in 2.8 (07 Feb 2026)

**Features and Improvements**:

- **IMPROVE:** Migrated deprecated `GET /browse/categories` and `GET /users/{id}` endpoints to handle **Spotify API changes** scheduled for **February 11, 2026**; used `GET /tracks/{id}` for oauth_app token validation and `spclient` internal API for user status checks
- **IMPROVE:** Enhanced `--generate-config` to support writing directly to a file (e.g. `spotify_monitor --generate-config spotify_monitor.conf`). This avoids UTF-16 encoding issues on **Windows PowerShell**
- **IMPROVE:** Expanded tabs to spaces in output log files to ensure **consistent alignment across different viewers**
- **IMPROVE:** Enhanced error handling for empty or malformed secret files
- **IMPROVE:** Added `spotify_monitor_secret_grabber` and `spotify_monitor_totp_test` as pip-installed **console scripts**

# Changes in 2.7 (27 Dec 2025)

**Features and Improvements**:

- **NEW:** Implemented **hybrid authentication approach** to support two auth methods: **cookie/client** for friend activity monitoring and **oauth_app** (**Client Credentials OAuth Flow**) for track API calls to address restrictions introduced by Spotify on **22 Dec 2025** (thanks [@tomballgithub](https://github.com/tomballgithub) and [@0xXiHan](https://github.com/0xXiHan), fixes [#27](https://github.com/misiektoja/spotify_monitor/issues/27))
- **NEW:** Added configuration options (`SP_APP_CLIENT_ID`, `SP_APP_CLIENT_SECRET`) and `-r` / `--oauth-app-creds` flag for **Client Credentials OAuth Flow (oauth_app)**
- **NEW:** Added **OAuth app token caching** via `SP_APP_TOKENS_FILE` configuration option
- **NEW:** Added **Spotipy** dependency (required since v2.7 due to new Spotify restrictions)
- **IMPROVE:** Enhanced **email notification formatting**

**Bug fixes**:

- **BUGFIX:** Removed `spotify_get_playlist_info` function to overcome Spotify's client credentials flow limitations and streamline playlist handling (fixes [#31](https://github.com/misiektoja/spotify_monitor/issues/31))
- **BUGFIX:** Removed old **TOTP versions** from `SECRET_CIPHER_DICT` (fixes [#28](https://github.com/misiektoja/spotify_monitor/issues/28))
- **BUGFIX:** Updated **TOTP version handling** in `refresh_access_token_from_sp_dc` function to ensure compatibility with varying **TOTP versions** (fixes [#32](https://github.com/misiektoja/spotify_monitor/issues/32))
- **BUGFIX:** Added missing **OAuth app** support for user removal check and improved error handling in `is_user_removed` function (fixes [#30](https://github.com/misiektoja/spotify_monitor/issues/30))

**Breaking changes**:

- **BREAKING:** Removed **token owner display** at startup due to `/v1/me` endpoint limitations introduced by Spotify on **22 Dec 2025**
- **BREAKING:** **OAuth app credentials** are now required for track information retrieval when using either `cookie` or `client` **token source methods**

# Changes in 2.6 (11 Nov 2025)

**Features and Improvements**:

- **NEW:** Added support for **Amazon Music**, **Deezer** and **Tidal** URLs in console and email outputs
- **NEW:** Added support for **AZLyrics**, **Tekstowo.pl**, **Musixmatch** and **Lyrics.com** lyrics services
- **NEW:** Added detection and annotation for **crossfaded songs** during playback with configurable thresholds (see `DETECT_CROSSFADED_SONGS`, `CROSSFADE_DETECTION_MIN` and `CROSSFADE_DETECTION_MAX` config options)
- **NEW:** Added configuration options to enable/disable music service URLs in console and email outputs (see `ENABLE_APPLE_MUSIC_URL`, `ENABLE_YOUTUBE_MUSIC_URL`, `ENABLE_AMAZON_MUSIC_URL`, `ENABLE_DEEZER_URL` and `ENABLE_TIDAL_URL` config options)
- **NEW:** Added configuration options to enable/disable lyrics service URLs in console and email outputs (see `ENABLE_GENIUS_LYRICS_URL`, `ENABLE_AZLYRICS_URL`, `ENABLE_TEKSTOWO_URL`, `ENABLE_MUSIXMATCH_URL` and `ENABLE_LYRICS_COM_URL` config options)
- **NEW:** Added recent songs tracking in session with inclusion in inactivity emails, including skipped track status (see `INACTIVE_EMAIL_RECENT_SONGS_COUNT` config option)
- **IMPROVE:** Introduced tolerance for "Played for" display to account for playback duration discrepancies (see `PLAYED_FOR_DURATION_TOLERANCE` config option)
- **IMPROVE:** Token owner info is now displayed at startup before the monitoring loop

**Bug fixes**:

- **BUGFIX:** Fixed "Played for" display when songs are played longer than track duration
- **BUGFIX:** Prevented duplicate emails when songs on loop also match track/song alerts

# Changes in 2.5 (12 Oct 2025)

**Features and Improvements**:

- **IMPROVE:** Added support for loading TOTP secrets from local files via file:// URLs
- **IMPROVE:** Updated remote URL in SECRET_CIPHER_DICT_URL
- **IMPROVE:** Updated  [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/main/debug/spotify_monitor_secret_grabber.py) to dump secrets in different formats. Choose what you need with the `--secret`,` --secretbytes` and `--secretdict` CLI flags, or go all out with the `--all` mode to write all secret formats to files like `secrets.json`, `secretBytes.json` and `secretDict.json` (thanks [@tomballgithub](https://github.com/tomballgithub))
- **IMPROVE:** Added multi-arch Docker image build and compose support for  [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/main/debug/spotify_monitor_secret_grabber.py) - more info at [Secret Key Extraction via Docker](https://misiektoja.github.io/spotify_monitor/debugging/#secret-key-extraction-via-docker)
- **IMPROVE:** Added deletion of flag_file at launch if specified via .conf file. Previously only done when flag_file was specified on command line
- **IMPROVE:** Added info to console output when TOTP secrets are fetched from a remote URL or local file

**Bug fixes**:

- **BUGFIX:** Removed walrus operator to support min python version 3.6 (thanks [@tomballgithub](https://github.com/tomballgithub), fixes [#20](https://github.com/misiektoja/spotify_monitor/issues/20))

# Changes in 2.4 (14 Jul 2025)

**Features and Improvements**:

- **IMPROVE:** Added automatic fetching of secrets used by web-player access token endpoint (`cookie` mode) while generating TOTP; it avoids manual updates since Spotify started rotating them every two days

**Bug fixes**:

- **BUGFIX:** Fixed bugs in retry logic and error handling in spotify_get_access_token_from_sp_dc()

# Changes in 2.3.1 (10 Jul 2025)

**Features and Improvements**:

- **IMPROVE:** Updated secret cipher bytes used by web-player access token endpoint (`cookie` mode) to v11 & v12
- **IMPROVE:** Moved secret cipher bytes for web-player endpoint to configuration section
- **IMPROVE:** Implemented auto-selection of highest cipher version when `TOTP_VER` is set to 0
- **NEW:** Added tool to extract secret keys used for TOTP generation in Spotify Web Player JavaScript bundles (see [Debugging Tools](https://misiektoja.github.io/spotify_monitor/debugging/) for more info)

**Bug fixes**:

- **BUGFIX:** Fixed truncation code to handle emojis with an actual width greater than one character (thanks [@tomballgithub](https://github.com/tomballgithub))

# Changes in 2.3 (07 Jul 2025)

**Features and Improvements**:

- **NEW:** Added new config option (`FLAG_FILE`) and flag (`--flag-file`) to create a file when the user is active and delete it when inactive; useful for external tools to detect streaming status (thanks [@tomballgithub](https://github.com/tomballgithub))
- **NEW:** Added new config option (`TRUNCATE_CHARS`) and flag (`--truncate`) to limit screen line length; set to 999 to auto-detect terminal width (thanks [@tomballgithub](https://github.com/tomballgithub))
- **IMPROVE:** Updated secret cipher bytes used by web-player access token endpoint (`cookie` mode) to v9 & v10 (thanks [@Thereallo1026](https://github.com/Thereallo1026) for reverse engineering the current secrets)
- **IMPROVE:** Added number of songs played and elapsed time to session events (thanks [@tomballgithub](https://github.com/tomballgithub))

**Bug fixes**:

- **BUGFIX:** Fixed missing asterisk on startup screen (thanks [@tomballgithub](https://github.com/tomballgithub))

# Changes in 2.2.1 (02 Jul 2025)

**Bug fixes**:

- **BUGFIX:** Fixed web-player access token retrieval via sp_dc cookie by updating secret cipher bytes (thanks [@WurdahMekanik](https://github.com/WurdahMekanik) and [@matthewcamilizer](https://github.com/matthewcamilizer), fixes [#11](https://github.com/misiektoja/spotify_monitor/issues/11))
- **BUGFIX:** Delayed removal/reappearance alerts; see new REMOVED_DISAPPEARED_COUNTER config option (fixes [#10](https://github.com/misiektoja/spotify_monitor/issues/10))
- **BUGFIX:** Fixed missing email alerts for failed token requests when using sp_dc cookie method

# Changes in 2.2 (18 Jun 2025)

**Features and Improvements**:

- **NEW:** Added new config option (`USER_AGENT`) and flag (`--user-agent`) to set Spotify user agent string
- **NEW:** Ensured all Spotify requests now include the appropriate user agent, if not specified - it is randomly generated per session for specific type of token source
- **IMPROVE:** Improved detection when a Spotify user has been removed
- **IMPROVE:** HTTPAdapter now honors the Retry-After header on 429 responses for better Spotify API rate limit handling
- **IMPROVE:** Updated captions shown for Apple and YouTube Music links
- **IMPROVE:** Added more descriptive error messages and covered additional corner cases
- **IMPROVE:** Suppressed -z / --clienttoken-request-body-file from help output to reduce confusion (flag remains functional, but hidden)
- **IMPROVE:** Clarifications in inline comments explaining how to configure Spotify Desktop client method

**Bug fixes**:

- **BUGFIX:** Fixed issue with incorrectly reported songs played on loop

# Changes in 2.1.2 (10 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Fixed web-player access token retrieval via sp_dc cookie (fixes [#8](https://github.com/misiektoja/spotify_monitor/issues/8))

# Changes in 2.1.1 (10 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Ensured all Spotify requests include the custom User-Agent header
- **BUGFIX:** Fixed config file generation to work reliably on Windows systems

# Changes in 2.1 (09 Jun 2025)

**Features and Improvements**:

- **NEW:** Added support for a new method to obtain the Spotify access token. This method uses captured credentials from the Spotify desktop client and a Protobuf-based login flow. It is intended for advanced users who want an indefinitely valid token with the widest scope. Check the [Spotify Desktop Client](https://misiektoja.github.io/spotify_monitor/configuration/#spotify-desktop-client) for more info.

# Changes in 2.0 (21 May 2025)

**Features and Improvements**:

- **NEW:** The tool can now be installed via pip: `pip install spotify_monitor`
- **NEW:** Added support for external config files, environment-based secrets and dotenv integration with auto-discovery
- **NEW:** Display access token owner information and Spotify friend profile URLs
- **IMPROVE:** Enhanced startup summary to show loaded config, dotenv and monitored tracks file paths
- **IMPROVE:** Simplified and renamed command-line arguments for improved usability
- **NEW:** Implemented SIGHUP handler for dynamic reload of secrets from dotenv files
- **NEW:** Added configuration option to control clearing the terminal screen at startup
- **IMPROVE:** Changed connectivity check to use Spotify API endpoint for reliability
- **IMPROVE:** Added check for missing pip dependencies with install guidance
- **IMPROVE:** Allow disabling liveness check by setting interval to 0 (default changed to 12h)
- **IMPROVE:** Improved handling of log file creation
- **IMPROVE:** Refactored CSV file initialization and processing
- **NEW:** Added support for `~` path expansion across all file paths
- **IMPROVE:** Refactored code structure to support packaging for PyPI
- **IMPROVE:** Enforced configuration option precedence: code defaults < config file < env vars < CLI flags
- **IMPROVE:** Removed short option for `--send-test-email` to avoid ambiguity

**Bug fixes**:

- **BUGFIX:** Fixed edge cases while converting Spotify URIs to URLs

# Changes in 1.9 (07 Apr 2025)

**Features and Improvements**:

- **IMPROVE:** Improved 'track songs' file parsing: now supports comments (lines starting with #) and ignores empty lines
- **IMPROVE:** Refactored comparison logic for file-listed vs. user-played song tracks
- **IMPROVE:** Replaced repeated requests.get calls with a shared SESSION to reuse HTTP connections and improve performance
- **IMPROVE:** Add retry-enabled HTTPAdapter to global SESSION
- **IMPROVE:** Display number of friends sharing listening activity (when using -l parameter)
- **IMPROVE:** Updated horizontal line for improved output aesthetics

**Bug fixes**:

- **BUGFIX:** Fixed issue handling 'track songs' files encoded in Windows-1252/CP1252 (fixes [#5](https://github.com/misiektoja/spotify_monitor/issues/5))

# Changes in 1.8.1 (25 Mar 2025)

**Bug fixes**:

- **BUGFIX:** Fixes occasional None return from get_random_user_agent(), avoiding downstream NoneType error (fixes [#4](https://github.com/misiektoja/spotify_monitor/issues/4))

# Changes in 1.8 (20 Mar 2025)

**Features and Improvements**:

- **NEW:** Added support for TOTP parameters in Spotify Web Player token endpoint, the tool now requires the pyotp pip module (fixes [#1](https://github.com/misiektoja/spotify_monitor/issues/1), [#2](https://github.com/misiektoja/spotify_monitor/issues/2))
- **NEW:** Caching mechanism to avoid unnecessary token refreshes
- **NEW:** Added the possibility to disable SSL certificate verification (VERIFY_SSL global variable)
- **IMPROVE:** Email notification flags are now automatically disabled if the SMTP configuration is invalid
- **IMPROVE:** Better exception handling in network-related functions
- **IMPROVE:** Better overall error handling
- **IMPROVE:** Code cleanup & linting fixes

# Changes in 1.7 (03 Nov 2024)

**Features and Improvements**:

- **NEW:** Support for YouTube Music search URLs

# Changes in 1.6 (15 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new parameter (**-z** / **--send_test_email_notification**) which allows to send test email notification to verify SMTP settings defined in the script
- **IMPROVE:** Possibility to define email sending timeout (default set to 15 secs)

**Bug fixes**:

- **BUGFIX:** Fixed "SyntaxError: f-string: unmatched (" issue in older Python versions
- **BUGFIX:** Fixed "SyntaxError: f-string expression part cannot include a backslash" issue in older Python versions

# Changes in 1.5 (07 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new signal handler for SIGPIPE allowing to switch songs on loop email notifications
- **IMPROVE:** Better way of checking for error strings (without case sensitivity) + some additional ones added to the list
- **NEW:** Support for float type of timestamps added in date/time related functions + get_short_date_from_ts() rewritten to display year if show_year == True and current year is different, also can omit displaying hour and minutes if show_hours == False

**Bug fixes**:

- **BUGFIX:** Escaping of exception error string fixed + some unbound vars corrected

# Changes in 1.4 (24 May 2024)

**Features and Improvements**:

- **NEW:** Possibility to define output log file name suffix (**-y** / **--log_file_suffix**)
- **NEW:** Feature allowing to suppress repeating API or network related errors (check **ERROR_500_NUMBER_LIMIT**, **ERROR_500_TIME_LIMIT**, **ERROR_NETWORK_ISSUES_NUMBER_LIMIT** and **ERROR_NETWORK_ISSUES_TIME_LIMIT** variables)
- **IMPROVE:** Information about log file name visible in the start screen
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime

**Bug fixes**:

- **BUGFIX:** Fixed issues with sporadic broken links in HTML emails (vars with special characters are now escaped properly)

# Changes in 1.3 (18 May 2024)

**Features and Improvements**:

- **NEW:** Full support for real-time playing of tracked songs (**-g**) in Spotify client in **Linux**
- **NEW:** Rewritten code for playing tracked songs (**-g**) in Spotify client in **macOS**
- **NEW:** New way of playing tracked songs (**-g**) in Spotify client in **Windows**
- **IMPROVE:** Improvements for running the code in Python under Windows
- **IMPROVE:** Better checking for wrong command line arguments
- **IMPROVE:** pep8 style convention corrections

**Bug fixes**:

- **BUGFIX:** Improved exception handling for some functions

# Changes in 1.2 (07 May 2024)

**Features and Improvements**:

- **NEW:** Possibility to define SP_DC_COOKIE via command line argument (-u / --spotify_dc_cookie)
- **IMPROVE:** SPOTIFY_ACTIVITY_CHECK and -p / --online_timer parameter have been removed as it only complicated the code with no visible benefit; SPOTIFY_INACTIVITY_CHECK is used in all places now, so user is considered active if the time of last activity is <= SPOTIFY_INACTIVITY_CHECK
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings
- **IMPROVE:** Strings have been converted to f-strings for better code visibility
- **IMPROVE:** Info about CSV file name in the start screen

# Changes in 1.1 (30 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for detection of songs listened on loop; if user plays the same song consecutively SONG_ON_LOOP_VALUE times (3 by default, configurable in the .py file) then there will be proper message on the console + you can get email notification (new -x / --song_on_loop_notification parameter); the alarm is triggered only once, when the SONG_ON_LOOP_VALUE is reached and once the user changes the song the timer is zeroed
- **NEW:** Feature to detect skipped songs; if the user plays the song for <= SKIPPED_SONG_THRESHOLD (0.6 by default = 60%, configurable in the .py file) of track duration, then the song is treated as skipped with proper message on the console & email notifications
- **NEW:** Information about number of listened songs in the session (console + notification emails)
- **IMPROVE:** Adding info about Artist and Album context of listened songs to notification emails
- **IMPROVE:** Adding info about Artist and Album context URLs in the console & email notifications
- **IMPROVE:** Information about readjusting session start due to too low inactivity timer is also in the notification email now

# Changes in 1.0 (23 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for detecting Artist context of listened songs
- **IMPROVE:** Additional search/replace strings to sanitize tracks for Genius URLs

**Bug fixes**:

- **BUGFIX:** Fix for "SyntaxWarning: invalid escape sequence '\d'" in regexps
