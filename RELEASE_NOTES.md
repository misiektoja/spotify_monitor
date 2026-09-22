# spotify_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 3.5.1 (22 Sep 2026)

Version **3.5.1** finds Firefox installed from the Microsoft Store when importing the browser cookie on Windows. Selected notification channels with unusable local settings are shown as unavailable and automatic sends stay quiet until the settings are fixed.

**Bug fixes**:

- **BUGFIX:** **Unavailable notification channels stay quiet** - The startup summary shows **`Unavailable`** and names the missing or invalid email or webhook setting. Automatic sends make no attempt and print no delivery line until that channel is configured. Activity alerts queued after a real delivery failure wait quietly while their channel is unavailable. **`Off`** means alerts are disabled for that channel
- **BUGFIX:** **Firefox from the Microsoft Store is found on Windows** - Only `%APPDATA%\Mozilla\Firefox` was searched, so a machine whose only Firefox came from the Store was told to **install Firefox** when it already had it. The Store package's own profile folder under `%LOCALAPPDATA%\Packages` is now searched too, its profiles are tagged **`[Microsoft Store]`** so the `default-release` that both installs create can be told apart, and a redirected `APPDATA` or `LOCALAPPDATA` no longer hides the profiles under your home directory. Container imports mount a single fixed path and still cover the regular installer only

# Changes in 3.5 (22 Sep 2026)

Version **3.5** sends the **scrobble health** alert as HTML like every other alert. It also reports when a monitored user **stops being visible** in listening activity, for example during a **private session**, and how long the user stayed away. Setup and Doctor accept targets who **share listening activity with selected people**, so following is no longer required in that case. **Browser cookie import** now finds Snap and Flatpak installs, marks which profile is signed in to Spotify and says what to fix when an import fails. Alert delivery messages stay within the correct check report and alert channels that still use placeholder configuration values are shown as not configured.

**Features and improvements**:

- **NEW:** **Visibility reports** - The live feed drops a user who starts a private session, turns off sharing, blocks the monitoring account or stops being followed. The tool now reports when user is no longer visible in listening activity after two checks in a row without the user. The session summary lists the time the user was not visible. Set `SPOTIFY_LIVE_DISAPPEARED_COUNTER` to change the number of checks and `SPOTIFY_LIVE_DISAPPEARED_CHECK_INTERVAL` or `-m` to change the interval, which now applies to the selected backend like the other timer flags. After six hours away the follow and sharing advice is printed once. The legacy backend keeps `REMOVED_DISAPPEARED_COUNTER` and reports that user has disappeared from Friend Activity with the possible causes
- **NEW:** **HTML in the scrobble health alert** - The alert about plays missing from Last.fm now carries an **HTML** part like the activity alerts.
- **NEW:** **One-run switches for the scrobble health alert** - `--notify-scrobble-health` and `--no-scrobble-health-notify` turn the email alert about missing and resumed scrobbles on or off for a single run. `--webhook-scrobble-health` and `--no-webhook-scrobble-health-notify` do the same for the webhook. Both channels remain on by default and `SCROBBLE_HEALTH_NOTIFICATION` and `WEBHOOK_SCROBBLE_HEALTH_NOTIFICATION` still decide when no option is given
- **IMPROVE:** **Following is optional for shared targets** - Following is optional for a target who shares listening activity with selected people that include the monitoring account. Setup skips the follow offer for a visible target
- **IMPROVE:** **Doctor and `--list-friends` compare both Friend Activity backends** - The live feed and the legacy endpoint can each list friends the other does not. When the target is missing from the selected backend, Doctor and the monitoring start check the other one and print the command that switches to it instead of the follow advice. `--list-friends` ends with the users only one backend lists
- **IMPROVE:** **The profile picker shows which profile is signed in** - `--import-browser-cookie` marks every profile that **holds a current Spotify login** and preselects it when only one does, so Enter accepts it. Profiles are tagged with the install they came from, such as Snap or Flatpak. Guided setup wizard reports how many profiles each browser has and how many hold a login, so you can pick a browser before opening the list
- **IMPROVE:** **Failure alerts share one shape** - Every monitoring failure email and webhook uses the subject **`Spotify Monitor (<mode>) error: <what went wrong> (user: <target>)`** and lists the fix, the guide link, how many checks failed in a row, since when and when the next retry happens. The mode is **Friend Activity** or **Spotify-to-Last.fm scrobble health**, so an inbox carrying both says which one failed. A **recovery alert** with the matching **`Spotify Monitor (<mode>) recovered: ...`** subject follows on the channels that received the failure alert once monitoring resumes. `-e` / `--no-error-notify` and `--no-webhook-error-notify` switch both off
- **IMPROVE:** **Alerts name the target, not only its id** - Failure alerts, recovery alerts, the visibility alerts and the matching console lines now name the target as **`display name (URI id)`**.
- **CONFIG CHANGE:** **Visibility alerts use the activity switches** - Alerts about a user who is no longer visible or visible again are sent with the inactive and active notification settings (`-i`, `-a`, `--webhook-inactive`, `--webhook-active`) instead of the error notification. A deleted profile is still reported as an error

**Bug fixes**:

- **BUGFIX:** **Import reads the profile your browser is using** - A cookie your browser had not yet written out looked missing, so signing in to Spotify and importing right away reported **no cookie found**. The import now reads the pending entries too. Profiles on read-only media, such as one mounted into the container, still work. A locked database no longer holds up the whole profile list
- **BUGFIX:** **Firefox imports the profile you are signed in to** - Current Firefox records cookie expiry in milliseconds, which always compared as far in the future, so **every profile looked equally current** and an old one could win. Expiry is now read in either unit. A profile whose cookie has expired says so and gives the date, instead of spending a Spotify request to fail
- **BUGFIX:** **Chrome, Brave and Chromium from Snap or Flatpak are found** - Only the distribution package locations were searched, so users of the **Snap or Flatpak builds had no profiles listed at all** and could not import
- **BUGFIX:** **Failed imports name what to fix** - A locked Linux keyring reported that Spotify was not signed in, sending you to the wrong place. It now says the **keyring is locked or unavailable** and names the package to install. An empty profile list distinguishes a browser that is not installed from one with no profile, a missing dependency and an unsupported system. Failures name the profile that failed and list the others available
- **BUGFIX:** **A mistyped profile number no longer cancels the import** - Any invalid answer, including a stray Enter, ended the import and meant starting over. The picker now **re-asks**, with `0` to cancel. After a failed import, setup offers to **try another browser** rather than only the same one. The cookie advice shown after a failed run names the browser you chose along with the alternatives
- **BUGFIX:** **Network failures point at the right page** - A timed-out or unreachable Spotify request link to the new **Connection Problems** section, which explains the automatic retries and what to check if the failure continues.
- **BUGFIX:** **A blocked network is no longer reported as a rejected cookie** - When the Spotify token could not be refreshed, the reason the request failed was dropped, so a timed-out or blocked connection was alerted as **`The sp_dc cookie is invalid, expired or was rejected`** and told you to re-import the cookie. The refresh now keeps the underlying failure, so a connection problem is named as one and retried instead
- **BUGFIX:** **Unset alert channels are reported as unset** - The verbose startup summary read the values the sample configuration ships as a real destination, so a run that had never been given a mail server printed **`Email transport: your_smtp_server_ssl:587`**, a recipient of **`your_receiver_email`** and a webhook provider of **`Discord`**. Those rows now read **`Not configured`** and the channel rollup above them reads **`Off (not configured)`** rather than naming alert types nothing could deliver

Smaller fixes and development changes are listed in the [full change history](https://github.com/misiektoja/spotify_monitor/compare/v3.4...v3.5).

# Changes in 3.4 (18 Sep 2026)

Version **3.4** switches Friend Activity to **live listening activity**, with a **legacy backend option** for completed-track reporting. It also adds **private SMTP password entry**, improves the **`--setup` wizard** and Doctor reports and makes **Last.fm scrobble alerts** clearer. Diagnostics are quieter and configuration, credentials and notification delivery are better protected.

**Features and improvements**:

- **NEW:** **Live Friend Activity** - Added support for Spotify's **live Listening Activity feed**, now the default for monitoring, friend listing and Doctor. The old endpoint reported a track only after it finished, so tracks appeared late and pauses were invisible. The live feed shows the **current track** as soon as playback starts, reports **PAUSED** and **RESUMED** with their durations, marks tracks cut short as **SKIPPED** with the played time and detects **songs on loop**, including a song restarted before its end. The live activity feed may show a different set of users from the legacy `buddylist` source, including friends who share their listening activity with selected people only (thanks [@JoaoGabriel-Lima](https://github.com/JoaoGabriel-Lima) for the idea, fixes [#60](https://github.com/misiektoja/spotify_monitor/issues/60))
- **NEW:** **Legacy backend option** - Use `--friend-activity-backend buddylist` for one run or save `FRIEND_ACTIVITY_BACKEND = "buddylist"` to keep the old completed-track reporting
- **NEW:** **Separate live polling timers** - The live backend checks every 30 seconds while the user is not playing and every 10 seconds during a listening session, retries a failed check after one minute and ends a session after three minutes without playback. Change them with `SPOTIFY_LIVE_CHECK_INTERVAL`, `SPOTIFY_LIVE_ACTIVE_CHECK_INTERVAL`, `SPOTIFY_LIVE_ERROR_INTERVAL` and `SPOTIFY_LIVE_INACTIVITY_CHECK`. The legacy backend keeps its own timers. `-c`, `-o` and the new `-k` flag apply to the selected backend and the setup wizard asks for both live intervals
- **NEW:** **Private SMTP password setup** - `--set-smtp-password` takes a hidden password and checks it with the mail server before saving. Guided setup also checks email credentials without sending a message
- **NEW:** **Output choices in setup** - Choose whether to write a log and where to save CSV output, then review or edit those choices before saving
- **IMPROVE:** **Setup preserves your progress** - The `--setup` wizard lets you skip unavailable answers and reuses saved settings. Changing destinations preserves retained credentials and keeps them out of configuration backups. Monitoring is offered after Doctor passes
- **IMPROVE:** **Discord alerts match the email** - Discord now receives the same emphasis as the HTML email, with bold values and clickable links instead of plain text. ntfy keeps the plain body, since it would show the markers literally
- **IMPROVE:** **More useful Doctor reports** - Reports validate settings, credentials, output destinations and alert choices. They warn about polling below 30 seconds and include approved delivery tests in the verdict. Invalid settings are reported without stopping the remaining checks
- **IMPROVE:** **Quieter diagnostics and notifications** - `--verbose` reports operational changes and `--debug` adds technical traces with secrets redacted. Subjects omit program-name prefixes. Set `DELIVERY_CONFIRMATIONS = False` to hide delivery confirmations while keeping verbose diagnostics
- **IMPROVE:** **Clearer errors and recovery** - Persistent outages produce hourly reminders and recovery notices. Temporary failures trigger error alerts after five minutes, while expired credentials alert immediately
- **IMPROVE:** **Colours and screen width** - Existing colour overrides still apply. Remove the old `COLOR_THEME` block to follow updated defaults. `--truncate N` limits screen width while logs retain full lines. It works without `wcwidth`, which improves Unicode width measurements. Copy the updated `grc/conf.monitor_logs` to `~/.grc/` to use the live terminal colours in saved logs
- **CONFIG CHANGE:** **Retired error aggregation settings** - `ERROR_500_NUMBER_LIMIT`, `ERROR_500_TIME_LIMIT`, `ERROR_NETWORK_ISSUES_NUMBER_LIMIT` and `ERROR_NETWORK_ISSUES_TIME_LIMIT` are ignored. Hourly outage reminders replace them. Existing configurations still load

**Bug fixes**:

- **BUGFIX:** **Clearer Last.fm scrobble alerts** - Reports distinguish missing or matched scrobbles from service outages. Reminders require recent missing plays to meet the threshold. New matches announce recovery and delayed scrobbles no longer repeat notices. Damaged saved timestamps are reported and reset
- **BUGFIX:** **Safer configuration and secret updates** - `--generate-config FILE` confirms replacement and creates a backup. Non-interactive replacement requires `--force`. Shell redirection with `>` bypasses these protections. Exported secrets work without a dotenv file. Command-line credentials and nonempty startup exports retain priority after `SIGHUP`. Change those values and restart to replace them. Reloads apply changed or removed file-owned secrets
- **BUGFIX:** **Validated credentials and settings** - Setup checks Spotify cookies before saving and offers alternatives after rejection. Invalid timing and web-player settings name what to fix. Declined notification settings are cleared and multiline dotenv values are replaced correctly
- **BUGFIX:** **Consistent TLS verification** - `VERIFY_SSL` applies to mail-server checks, Spotify OAuth token requests and `--set-sp-dc` validation
- **BUGFIX:** **Safer notification delivery** - Webhook retries keep their original destination and credentials. Discord templates cannot enable mentions and invalid templates are rejected before delivery. Error messages redact credentials, including SMTP rejection replies. Emails accepted by the mail server no longer become false failures if closing the connection fails, avoiding duplicate retries
- **BUGFIX:** **Terminal and container fixes** - Corrected colour and truncation handling keeps external text readable. Container rebuilds refresh security updates

Smaller fixes and development changes are listed in the [full change history](https://github.com/misiektoja/spotify_monitor/compare/v3.3.1...v3.4).

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
