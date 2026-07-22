# Usage

<a id="command-format"></a>
## Command Format by Installation Method

Most examples on this page use the PyPI command `spotify_monitor`. If you chose another installation, replace only that command with the prefix in this table. Keep the targets and options that follow it.

| Installation | Command prefix |
| --- | --- |
| PyPI | `spotify_monitor` |
| Manual script on macOS or Linux | `python3 spotify_monitor.py` |
| Manual script on Windows | `python spotify_monitor.py` |
| Docker Compose | `docker compose run --rm spotify_monitor` |
| Direct Docker on Docker Desktop | `docker run --rm -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest` |
| Direct Docker on Linux | `docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest` |

For example, `spotify_monitor --doctor TARGET` becomes `docker compose run --rm spotify_monitor --doctor TARGET` with Compose. The current host directory appears as `/data` inside the container, so container paths to its files must start with `/data/`.

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

The setup wizard asks whether to save the target. A saved target lets a local installation start with `spotify_monitor` and lets Docker Compose start with `docker compose up --no-log-prefix`.

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

The tool runs until you press `Ctrl+C`. On macOS, Linux or Unix, tools such as `tmux` or `screen` can keep it running after you disconnect from a terminal. Docker Compose can run in the background as described below.

You can monitor multiple Spotify friends by running multiple copies with separate output names or directories.

By default, text output is saved to `spotify_monitor_<user_uri_id/file_suffix>.log`. Change the base path with `SP_LOGFILE` and the suffix with `FILE_SUFFIX` or `-y`. Disable file logging with `DISABLE_LOGGING` or `-d`.

Spotify Friend Activity reports a track after the user finishes it. Spotify Monitor therefore cannot show the currently playing track in real time.

<a id="main-application-docker-image"></a>
## Container Operation

See [Docker installation](installation.md#docker-compose) for installation, Linux file ownership, local image builds and upgrades. This section covers everyday use after setup.

Compose makes the current host directory available as `/data` inside the container. The wizard creates `spotify_monitor.conf` and `.env` in that host directory. Logs and CSV output are also written there. The image does not contain your configuration or private values.

Start the target saved by setup in the foreground:

```sh
docker compose up --no-log-prefix
```

For a background run and live logs:

```sh
docker compose up -d
docker compose logs -f --no-log-prefix
```

Stop and remove the service container:

```sh
docker compose down
```

This command does not delete files in the current directory.

If the wizard did not save the target, `docker compose up --no-log-prefix` cannot supply one. Use the direct Compose command printed by setup:

```sh
docker compose run --rm spotify_monitor "https://open.spotify.com/user/spotify_user_uri_id" --config-file /data/spotify_monitor.conf --env-file /data/.env
```

The default container authentication method asks for `sp_dc` through a hidden prompt. To import from Firefox instead, mount the browser profile as described under [Spotify sp_dc Cookie](configuration.md#spotify-sp_dc-cookie).

Host Spotify auto-play is unavailable by default inside a container because the container cannot control the Spotify client running on the host. Run Spotify Monitor locally if you need `TRACK_SONGS` or `--track-in-spotify`. The tool warns but does not disable the setting so custom host integration remains possible.

<a id="terminal-output"></a>
## Terminal Output

The `--help` output includes examples for setup, private cookie entry, webhook setup, Firefox import, test alerts, monitoring, Doctor and friend listing. The examples match the detected installation method.

Spotify Monitor starts user-facing commands with the selected ASCII equalizer banner. Plain ASCII keeps the banner readable in terminals, redirected output and container logs. Machine-oriented `--version` and `--generate-config` output intentionally omit it.

Normal monitoring shows the target, authentication method, polling interval, alert state, output destination, configuration path, `.env` path and metadata source. Optional features appear only when enabled. When file logging is enabled, the log receives a complete summary that excludes private values.

Use `--verbose` to display the complete startup summary plus rare operational events without enabling per-poll or debug HTTP logging:

```sh
spotify_monitor spotify_user_uri_id --verbose
```

Spotify Monitor normally checks every 30 seconds. Verbose mode reports token refreshes, metadata fallback, the first temporary friend-list miss, recovery from temporary problems and a periodic status summary. It does not print every successful check when nothing changed.

`--debug` retains per-poll lifecycle and scheduling detail plus sanitized request flow and internal state diagnostics. Secrets never appear in summaries, verbose events, debug output or the complete log summary.

Use `--truncate N` or `TRUNCATE_CHARS` to limit screen line width. Set it to `999` to detect the terminal width automatically. Truncation does not change log files and is ignored when logging is disabled with `-d`.

<a id="listing-mode"></a>
## Listing Mode

Listing mode shows the Spotify friends visible to the monitoring account and each person's most recently reported track:

```sh
spotify_monitor -l
```

The output includes each person's display name and user URI ID. Use the user URI ID as a monitoring target.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_listing.png" alt="spotify_monitor_listing" width="90%"/>
</p>

<a id="email-notifications"></a>
## Email Notifications

To send an email when a user becomes active:

- set `ACTIVE_NOTIFICATION` to `True`
- or use the `-a` flag

```sh
spotify_monitor <spotify_user_uri_id> -a
```

To send an email when a user becomes inactive:

- set `INACTIVE_NOTIFICATION` to `True`
- or use the `-i` flag

```sh
spotify_monitor <spotify_user_uri_id> -i
```

Inactivity emails include recent songs from the session with skipped track status. Configure the number of recent songs to include via the `INACTIVE_EMAIL_RECENT_SONGS_COUNT` configuration option.

To send an email when a listed track, playlist or album plays:

- set `TRACK_NOTIFICATION` to `True`
- or use the `-t` flag

Create a text file with one track, album or playlist per line. Select it with `MONITOR_LIST_FILE` or `-s`:

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

Start a line with `#` to ignore it.

To send an email for every reported song change:

- set `SONG_NOTIFICATION` to `True`
- or use the `-j` flag

```sh
spotify_monitor <spotify_user_uri_id> -j
```

To send an email when a user repeats the same song:

- set `SONG_ON_LOOP_NOTIFICATION` to `True`
- or use the `-x` flag

```sh
spotify_monitor <spotify_user_uri_id> -x
```

Error emails are enabled by default when SMTP is configured. To disable them:

- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
spotify_monitor <spotify_user_uri_id> -e
```

All email alerts require valid [SMTP settings](configuration.md#smtp-settings).

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_email_notifications.png" alt="spotify_monitor_email_notifications" width="80%"/>
</p>

<a id="webhook-notifications"></a>
## Webhook Notifications

The setup wizard recommends webhook alerts for active, inactive and error events. Choose the custom option to select events individually.

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

To save reported songs in a CSV file, set `CSV_FILE` or use `-b`:

```sh
spotify_monitor <spotify_user_uri_id> -b spotify_tracks_user_uri_id.csv
```

Spotify Monitor creates the file if it does not exist.

<a id="activity-flag-file"></a>
## Activity Flag File

Set `FLAG_FILE` or use `--flag-file PATH` to expose the monitored user's current activity state to another local tool. Spotify Monitor creates the file while the user is active and deletes it after the user becomes inactive:

```sh
spotify_monitor TARGET --flag-file /path/spotify_user_active
```

For a container, place the file under `/data` so it appears in the host directory. Each concurrently monitored user should have a different flag path.

<a id="automatic-playback-of-listened-tracks-in-the-spotify-client"></a>
## Automatic Playback of Listened Tracks in the Spotify Client

To play reported tracks in your local Spotify client:

- set `TRACK_SONGS` to `True`
- or use the `-g` flag

```sh
spotify_monitor <spotify_user_uri_id> -g
```

The Spotify client must be installed and running.

Host Spotify auto-play is unavailable by default inside a container because the container cannot control the Spotify client running on the host. Run Spotify Monitor locally if you need `TRACK_SONGS` or `--track-in-spotify`. A container run prints one warning before monitoring and `--doctor` reports `[WARN]`, but the setting is not disabled automatically.

On Linux and macOS, Spotify Monitor can play each reported track. It can also pause playback or play a selected track when the user becomes inactive. See `SP_USER_GOT_OFFLINE_TRACK_ID`.

On Windows, the first track can start if Spotify is open and currently idle. Later tracks are opened in Spotify but may require you to press Play.

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

Keep the default method unless playback does not work on your system.

Spotify reports each track after the monitored user finishes it. Automatic playback is therefore one track behind. Differences in track length can make your local track repeat or change before it finishes.

For current-track progress plus pause and resume detection, see [lastfm_monitor](https://github.com/misiektoja/lastfm_monitor).

<a id="check-intervals"></a>
## Check Intervals

The polling interval is the number of seconds between Friend Activity checks. Set it through `SPOTIFY_CHECK_INTERVAL` or `-c`:

```sh
spotify_monitor <spotify_user_uri_id> -c 20
```

The inactivity timer starts at the last reported track. Set the number of seconds through `SPOTIFY_INACTIVITY_CHECK` or `-o`:

```sh
spotify_monitor <spotify_user_uri_id> -o 900
```

If a user disappears from Friend Activity, use `-m` or `SPOTIFY_DISAPPEARED_CHECK_INTERVAL` to control the delay between visibility checks:

```sh
spotify_monitor TARGET -m 180
```

<a id="signal-controls-macoslinuxunix"></a>
## Signal Controls (macOS/Linux/Unix)

On macOS, Linux and Unix, operating system signals can change a running process without restarting it.

Supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle active and inactive email notifications (`-a`, `-i`) |
| USR2 | Toggle every-song email notifications (`-j`) |
| CONT | Toggle tracked-song email notifications (`-t`) |
| PIPE | Toggle loop email notifications (`-x`) |
| TRAP | Increase the inactivity timer by 30 seconds (`-o`) |
| ABRT | Decrease the inactivity timer by 30 seconds (`-o`) |
| HUP | Reload private values from `.env` and token credentials from Protobuf files |

Send a signal with `kill` or `pkill`. For example:

```sh
pkill -USR1 -f "spotify_monitor <spotify_user_uri_id>"
```

This feature is not available for a native Windows process because Windows supports only a limited signal set.

<a id="coloring-log-output-with-grc"></a>
## Coloring Log Output with GRC

[GRC](https://github.com/garabik/grc) can color saved log files when you view them in a terminal.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Copy [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/grc/conf.monitor_logs) to `~/.grc/`. Then view a log through `grc`:

```sh
grc tail -F -n 100 spotify_monitor_<user_uri_id/file_suffix>.log
```
