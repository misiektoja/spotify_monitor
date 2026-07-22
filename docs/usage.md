# Usage

<a id="command-format"></a>
## Command Format by Installation Method

Examples on this page use the PyPI command `spotify_monitor`. Keep the options shown in an example and replace only the command prefix with the form for your installation:

| Installation | Command prefix |
| --- | --- |
| PyPI | `spotify_monitor` |
| Manual script on macOS or Linux | `python3 spotify_monitor.py` |
| Manual script on Windows | `python spotify_monitor.py` |
| Docker Compose | `docker compose run --rm spotify_monitor` |
| Direct Docker on Docker Desktop | `docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest` |
| Direct Docker on Linux | `docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest` |

For example, `spotify_monitor --doctor TARGET` becomes `docker compose run --rm spotify_monitor --doctor TARGET` with Compose. A file used by a container must be under the mounted current directory and its command-line path must start with `/data/`.

The Docker Desktop command works in macOS shells and Windows PowerShell. In Windows Command Prompt replace `${PWD}` with `%cd%`.

See [Installation](installation.md) for setup, optional dependencies, image details and upgrade commands.

<a id="monitoring-mode"></a>
## Monitoring Mode

Pass a [Spotify user target](configuration.md#how-to-get-a-friends-user-uri-id) as a command-line argument. A target can be a raw user ID, a `spotify:user:` URI or a complete profile URL:

```sh
spotify_monitor spotify_user_uri_id
spotify_monitor "spotify:user:spotify_user_uri_id"
spotify_monitor "https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id"
```

You can also save any of these forms as `TARGET_USER_URI_ID` in `spotify_monitor.conf`. A positional target takes precedence. With a saved target no positional value is needed:

```sh
spotify_monitor --config-file spotify_monitor.conf
```

The setup wizard asks whether to persist its target. This lets local installations start with `spotify_monitor` and lets Docker Compose start with `docker compose up --no-log-prefix`.

If you use cookie authentication and have not saved `SP_DC_COOKIE`, the `-u` fallback supplies it for one run:

```sh
spotify_monitor spotify_user_uri_id -u "your_sp_dc_cookie_value"
```

This command can expose the cookie through shell history or process listings. Use browser import locally or hidden `--set-sp-dc` entry in a container instead.

If you have working legacy OAuth app credentials and want the tool to try the Web API metadata path first, use `-r`:

```sh
spotify_monitor spotify_user_uri_id -u "your_sp_dc_cookie_value" -r "your_spotify_app_client_id:your_spotify_app_client_secret"
```

See [Spotify OAuth App](configuration.md#spotify-oauth-app) for the optional dependency and current compatibility guidance.

By default the tool looks for `spotify_monitor.conf` in this order:

1. The path supplied with `--config-file`
2. `spotify_monitor.conf` in the current directory
3. `~/.spotify_monitor.conf` in the home directory
4. `spotify_monitor.conf` in the script directory

Specify another file explicitly when needed:

```sh
spotify_monitor spotify_user_uri_id --config-file /path/spotify_monitor_new.conf
```

The tool runs until interrupted with `Ctrl+C`. Use `tmux` or `screen` for a persistent local run. Docker Compose can run in the background as described below.

You can monitor multiple Spotify friends by running multiple copies with separate output names or directories.

By default, output is saved to `spotify_monitor_<user_uri_id/file_suffix>.log`. Change the base path with `SP_LOGFILE` and the suffix with `FILE_SUFFIX` or `-y`. Disable logging with `DISABLE_LOGGING` or `-d`.

Monitoring reports a listened track after the user finishes it because this is how Spotify reports Friend Activity.

<a id="main-application-docker-image"></a>
## Container Operation

Installation, Linux ownership setup, local image builds and upgrades are documented under [Docker installation](installation.md#docker-compose). This section covers normal container operation after setup.

Compose mounts the current directory at `/data`. The wizard creates `spotify_monitor.conf` and `.env` on the host. Logs and CSV output also persist there. The image contains no user configuration or secrets.

Start the target saved by setup in the foreground:

```sh
docker compose up --no-log-prefix
```

For a background run and live logs:

```sh
docker compose up -d
docker compose logs -f --no-log-prefix
```

Stop and remove the service container without deleting the bind-mounted files:

```sh
docker compose down
```

If the wizard did not persist the target, `docker compose up --no-log-prefix` cannot supply one. Use the direct Compose command printed by setup:

```sh
docker compose run --rm spotify_monitor "https://open.spotify.com/user/spotify_user_uri_id" --config-file /data/spotify_monitor.conf --env-file /data/.env
```

The default container authentication path is hidden manual cookie entry. Advanced mounted Firefox import is documented under [Spotify sp_dc Cookie](configuration.md#spotify-sp_dc-cookie).

Host Spotify auto-play is unavailable by default inside a container because the container cannot control the Spotify client running on the host. Run Spotify Monitor locally if you need `TRACK_SONGS` or `--track-in-spotify`. The tool warns but does not disable the setting so custom host integration remains possible.

<a id="terminal-output"></a>
## Terminal Output

The `--help` output provides copy-paste examples for guided setup, private cookie entry, webhook setup, Firefox cookie import, test alerts, normal monitoring, doctor checks and friend listing. Commands adapt automatically to PyPI, downloaded script, Docker and Docker Compose installations.

Spotify Monitor starts user-facing commands with the selected ASCII equalizer banner. Plain ASCII keeps the banner readable in terminals, redirected output and container logs. Machine-oriented `--version` and `--generate-config` output intentionally omit it.

Normal monitoring shows a concise startup summary led by the target, authentication mode, polling interval, notification state, output destination, config path, dotenv path and metadata backend. Enabled optional features appear only when relevant. When logging is enabled a complete non-secret configuration summary is written once to the log while the terminal remains concise.

Use `--verbose` to display the complete startup summary plus rare operational events without enabling per-poll or debug HTTP logging:

```sh
spotify_monitor spotify_user_uri_id --verbose
```

Spotify Monitor normally polls every 30 seconds so verbose mode is event-driven rather than check-driven. It reports token refreshes, metadata-backend fallback, the first transient buddy-list miss, recovery from transient visibility or connectivity problems plus a richer summary at the configured liveness interval. It does not print a line for every successful unchanged poll.

`--debug` retains per-poll lifecycle and scheduling detail plus sanitized request flow and internal state diagnostics. Secrets never appear in summaries, verbose events, debug output or the complete log summary.

Use `--truncate N` or `TRUNCATE_CHARS` to limit screen line width. Set it to `999` to detect the terminal width automatically. Truncation does not change log files and is ignored when logging is disabled with `-d`.

<a id="listing-mode"></a>
## Listing Mode

There is also another mode of the tool which displays various requested information.

If you want to display a list of all the friends you follow with their recently listened tracks (`-l` flag):

```sh
spotify_monitor -l
```

It also displays your friend's Spotify username (often the user's first and last name) and user URI ID (often a string of random characters). The latter should be used as a tool's command-line argument to monitor the user.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_listing.png" alt="spotify_monitor_listing" width="90%"/>
</p>

<a id="email-notifications"></a>
## Email Notifications

To enable email notifications when a user becomes active:

- set `ACTIVE_NOTIFICATION` to `True`
- or use the `-a` flag

```sh
spotify_monitor <spotify_user_uri_id> -a
```

To be informed when a user gets inactive:

- set `INACTIVE_NOTIFICATION` to `True`
- or use the `-i` flag

```sh
spotify_monitor <spotify_user_uri_id> -i
```

Inactivity emails include recent songs from the session with skipped track status. Configure the number of recent songs to include via the `INACTIVE_EMAIL_RECENT_SONGS_COUNT` configuration option.

To get email notifications when a monitored track/playlist/album plays:

- set `TRACK_NOTIFICATION` to `True`
- or use the `-t` flag

For that feature you also need to create a file with a list of songs you want to track (one track, album or playlist per line). Specify the file using the `MONITOR_LIST_FILE` or `-s` flag:

```sh
spotify_monitor <spotify_user_uri_id> -t -s spotify_tracks_spotify_user_uri_id
```

Example file `spotify_tracks_spotify_user_uri_id`:

```
we fell in love in october
Like a Stone
Half Believing
Something Changed
I Will Be There
```

You can comment out specific lines with # if needed.

To enable email notifications for every song listened by the user:

- set `SONG_NOTIFICATION` to `True`
- or use the `-j` flag

```sh
spotify_monitor <spotify_user_uri_id> -j
```

To be notified when a user listens to the same song on loop:

- set `SONG_ON_LOOP_NOTIFICATION` to `True`
- or use the `-x` flag

```sh
spotify_monitor <spotify_user_uri_id> -x
```

To disable sending an email on errors (enabled by default):

- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
spotify_monitor <spotify_user_uri_id> -e
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](configuration.md#smtp-settings)).

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_email_notifications.png" alt="spotify_monitor_email_notifications" width="80%"/>
</p>

<a id="webhook-notifications"></a>
## Webhook Notifications

The setup wizard's recommended choice sends active, inactive and error alerts. Choose the custom option in the wizard if you want to decide one by one.

You can also change the settings yourself in `spotify_monitor.conf` or use a command-line option for one run:

| Event | Config setting | CLI override |
| --- | --- | --- |
| User becomes active | `WEBHOOK_ACTIVE_NOTIFICATION` | `--webhook-active` |
| User becomes inactive | `WEBHOOK_INACTIVE_NOTIFICATION` | `--webhook-inactive` |
| Monitored track, playlist or album plays | `WEBHOOK_TRACK_NOTIFICATION` | `--webhook-track` |
| Every song change | `WEBHOOK_SONG_NOTIFICATION` | `--webhook-song-changes` |
| Song loop detected | `WEBHOOK_SONG_ON_LOOP_NOTIFICATION` | `--webhook-loop` |
| Monitoring error | `WEBHOOK_ERROR_NOTIFICATION` | Disable with `--no-webhook-error-notify` |

For example, this sends a webhook alert for every song change during one run:

```sh
spotify_monitor <spotify_user_uri_id> --webhook-song-changes
```

Use `--webhook` or `--no-webhook` to turn all configured webhook alerts on or off for one run. A tracked-song webhook alert uses the same song list as a tracked-song email alert.

<a id="csv-export"></a>
## CSV Export

If you want to save all listened songs to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
spotify_monitor <spotify_user_uri_id> -b spotify_tracks_user_uri_id.csv
```

The file will be automatically created if it does not exist.

<a id="activity-flag-file"></a>
## Activity Flag File

Set `FLAG_FILE` or use `--flag-file PATH` to expose the monitored user's current activity state to another local tool. Spotify Monitor creates the file while the user is active and deletes it after the user becomes inactive:

```sh
spotify_monitor TARGET --flag-file /path/spotify_user_active
```

For a container, place the file under `/data` so it appears in the host directory. Each concurrently monitored user should have a different flag path.

<a id="automatic-playback-of-listened-tracks-in-the-spotify-client"></a>
## Automatic Playback of Listened Tracks in the Spotify Client

If you want the tool to automatically play the tracks listened to by the user in your local Spotify client:

- set `TRACK_SONGS` to `True`
- or use the `-g` flag

```sh
spotify_monitor <spotify_user_uri_id> -g
```

Your Spotify client needs to be installed and running for this feature to work.

Host Spotify auto-play is unavailable by default inside a container because the container cannot control the Spotify client running on the host. Run Spotify Monitor locally if you need `TRACK_SONGS` or `--track-in-spotify`. A container run prints one warning before monitoring and `--doctor` reports `[WARN]`, but the setting is not disabled automatically.

The tool fully supports automatic playback on **Linux** and **macOS**. This means it will automatically play the changed track and can also pause or play the indicated track once the user becomes inactive (see the `SP_USER_GOT_OFFLINE_TRACK_ID` configuration option).

For **Windows**, it works in a semi-automatic way: if you have the Spotify client running and you are not listening to any song, then the first track will play automatically. However, subsequent tracks will be located in the client, but you will need to press the play button manually.

You can change the playback method per platform using the corresponding configuration option.

For **macOS** set `SPOTIFY_MACOS_PLAYING_METHOD` to one of the following values:

-  "**apple-script**" (recommended, **default**)
-  "trigger-url"

For **Linux** set `SPOTIFY_LINUX_PLAYING_METHOD` to one of the following values:

- "**dbus-send**" (most common one, **default**)
- "qdbus" (try if dbus-send does not work)
- "trigger-url"

For **Windows** set `SPOTIFY_WINDOWS_PLAYING_METHOD` to one of the following values:

- "**start-uri**" (recommended, **default**)
- "spotify-cmd"
- "trigger-url"

The recommended defaults should work for most people.

Note: monitoring reports the listened track after the user finishes listening to it. This is how activities are reported by Spotify. It means you will be one song behind the monitored user and if the song currently listened to by the tracked user is longer than the previous one, then the previously listened song might be played in your Spotify client on repeat (and if shorter it might be changed in the middle of the currently played song).

For real-time playback tracking of a user's music activities, ask your friend to connect their Spotify account with [Last.fm](https://www.last.fm/). Then use my other tool: [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor).

<a id="check-intervals"></a>
## Check Intervals

If you want to customize the polling interval, use `-c` flag (or `SPOTIFY_CHECK_INTERVAL` configuration option):

```sh
spotify_monitor <spotify_user_uri_id> -c 20
```

If you want to change the time required to mark the user as inactive (the timer starts from the last reported track), use `-o` flag (or `SPOTIFY_INACTIVITY_CHECK` configuration option):

```sh
spotify_monitor <spotify_user_uri_id> -o 900
```

If a user disappears from Friend Activity, use `-m` or `SPOTIFY_DISAPPEARED_CHECK_INTERVAL` to control the delay between visibility checks:

```sh
spotify_monitor TARGET -m 180
```

<a id="signal-controls-macoslinuxunix"></a>
## Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets active/inactive (-a, -i) |
| USR2 | Toggle email notifications for every song (-j) |
| CONT | Toggle email notifications for tracked songs (-t) |
| PIPE | Toggle email notifications when user plays song on loop (-x) |
| TRAP | Increase the inactivity check timer (by 30 seconds) (-o) |
| ABRT | Decrease the inactivity check timer (by 30 seconds) (-o) |
| HUP | Reload secrets from .env file and token source credentials from Protobuf files |

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "spotify_monitor <spotify_user_uri_id>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
## Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to color logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 spotify_monitor_<user_uri_id/file_suffix>.log
```
