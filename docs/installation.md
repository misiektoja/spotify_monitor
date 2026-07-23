# Installation

Choose one installation method. You do not need both Python and Docker. PyPI is usually the easiest local option. The direct Docker image is the fastest container option. Docker Compose takes one extra download but gives you shorter commands for later runs.

<a id="requirements"></a>
## Requirements

Choose either the Python path or the container path.

**Python path**:

- [Python](https://www.python.org/downloads/) 3.9 or higher
- Core libraries: `requests`, `python-dateutil`, `urllib3`, `pyotp`, `python-dotenv`, `wcwidth`, `Pillow`
- `spotipy` is optional and is needed only for legacy OAuth metadata access
- `pycookiecheat` is optional and is needed only to import cookies from Chrome, Brave or Chromium

**Container path** (Python is included in the image):

- Any Docker-compatible runtime such as:
    - [Docker Desktop](https://docs.docker.com/get-started/get-docker/) (macOS, Windows, Linux)
    - [Docker Engine](https://docs.docker.com/engine/install/) (Linux)
    - [Colima](https://colima.run/docs/installation/) with Docker CLI (macOS)
    - [OrbStack](https://docs.orbstack.dev/quick-start) (macOS)
    - [Rancher Desktop](https://docs.rancherdesktop.io/getting-started/installation/) with Moby or Docker CLI enabled (macOS, Windows, Linux)
- The Docker Compose v2 plugin if you choose the Compose method

The published image already contains Python and all core libraries. You do not need a local Python installation for Docker.

The examples use the `docker` command. Check that it works with `docker --version`. If you choose Compose, also check `docker compose version`.

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="installation"></a>
## Choose an Installation Method

| Method | Best for | Command used in later examples |
| --- | --- | --- |
| PyPI | Most local users | `spotify_monitor [OPTIONS]` |
| Manual script | Users who want to download and run one Python file | `python3 spotify_monitor.py [OPTIONS]` on macOS/Linux or `python spotify_monitor.py [OPTIONS]` on Windows |
| Docker Hub image | Users who want the fastest container setup | `docker run ... misiektoja/spotify-monitor:latest [OPTIONS]` |
| Docker Compose | Users who prefer shorter recurring commands after setup | `docker compose run --rm spotify_monitor [OPTIONS]` |

Later pages use the short PyPI command unless Docker behaves differently. If you chose another method, keep the options after `spotify_monitor` but replace `spotify_monitor` with the command in the table. The setup wizard and `--help` also print commands for the detected installation.

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install spotify_monitor
spotify_monitor --version
```

Each command below that uses square brackets installs the base `spotify_monitor` package plus the named optional dependency. Run only the command that matches your needs. You do not need to run the plain install command first.

Firefox cookie import needs no extra dependency. To import from Chrome, Brave or Chromium on macOS or Linux install the browser extra:

```sh
pip install "spotify_monitor[browser]"
```

This installs Spotify Monitor and the optional `pycookiecheat` dependency.

Spotipy is optional. Install the legacy OAuth extra only if you already have working [Spotify OAuth App](configuration.md#spotify-oauth-app) credentials and want to enable the optional legacy Web API metadata path. The automatic web-player backend works without this extra:

```sh
pip install "spotify_monitor[legacy-oauth]"
```

This installs Spotify Monitor and the optional Spotipy dependency. It also includes the base package, so this single command is sufficient.

Both extras can be installed together:

```sh
pip install "spotify_monitor[browser,legacy-oauth]"
```

<a id="manual-installation"></a>
### Install the Manual Script

Download the script and dependency list into the same directory:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt
```

You can also download [spotify_monitor.py](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py) and [requirements.txt](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt) in a browser or use the files from a cloned repository.

Install the core dependencies:

```sh
pip install -r requirements.txt
```

You can install the core dependencies directly if you downloaded only the script:

```sh
pip install requests python-dateutil urllib3 pyotp python-dotenv wcwidth Pillow
```

For optional legacy OAuth support install `spotipy`:

```sh
pip install "spotipy>=2.24.0"
```

For optional Chrome, Brave or Chromium import on macOS or Linux install `pycookiecheat`:

```sh
pip install "pycookiecheat>=0.8"
```

Verify the script:

```sh
python3 spotify_monitor.py --version
```

Use `python spotify_monitor.py --version` on Windows.

<a id="docker-image"></a>
### Install from Docker Hub

The published [`misiektoja/spotify-monitor`](https://hub.docker.com/r/misiektoja/spotify-monitor) image supports `linux/amd64` and `linux/arm64`:

No separate image download is required. Continue to [Quick Start](quick-start.md#new-here-run-the-setup-wizard). Its first-run command uses `docker run --pull=always` to pull the current image and start the setup wizard in one step.

Normal monitoring commands reuse the installed image and do not check for a newer release. The [upgrade instructions](#upgrade-a-direct-docker-installation) pull explicitly when you choose to upgrade.

Normal runs make the current directory available as `/data` in the container. Configuration and output written there remain on the host after the temporary container stops. On a native Linux container engine, the command also passes your numeric user and group IDs so new files belong to you. [Quick Start](quick-start.md#new-here-run-the-setup-wizard) shows the complete commands for macOS shells, Windows PowerShell and native Linux engines.

The macOS shell and Windows PowerShell examples use `${PWD}`. In Windows Command Prompt use `%cd%` for the current directory. Native Linux examples use `$PWD` and pass your numeric user and group IDs.

The `:z` suffix lets Docker relabel the mounted directory on hosts that use SELinux. If your Docker-compatible runtime reports that `:z` is invalid, remove only `:z` and keep the rest of the mount.

The published image includes the core dependencies but not the optional `legacy-oauth` or Chromium browser extras. Anonymous web-player metadata works without Spotipy. Firefox works inside a container when its cookie database is mounted read-only for the import command. Chrome, Brave and Chromium need the host password service to decrypt cookies. A container cannot use that service. See [Container Operation](usage.md#import-firefox-into-container-authentication) for the complete Firefox commands. Hidden `sp_dc` entry remains available as a fallback.

<a id="docker-compose"></a>
### Install with Docker Compose

Compose adds a reusable project file and shorter commands for later runs. Create or choose a directory for Spotify Monitor and download the Compose file there:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/docker-compose.yml
```

You can also download [docker-compose.yml](https://github.com/misiektoja/spotify_monitor/blob/main/docker-compose.yml) in a browser or use the file from a cloned repository.

On a native Linux container engine, the container does not automatically know which host user should own new files. Export your numeric user ID and group ID so configuration, logs and CSV files created by the container belong to your account instead of `root`:

```sh
export SPOTIFY_MONITOR_UID="$(id -u)"
export SPOTIFY_MONITOR_GID="$(id -g)"
```

Run these commands in the same terminal that you will use for setup and later Compose commands. A new terminal will not keep the exported values. To make them permanent for this project, put the numeric results from `id -u` and `id -g` in the Compose `.env` file:

```ini
SPOTIFY_MONITOR_UID=1000
SPOTIFY_MONITOR_GID=1000
```

The values above are only examples. Use the numbers returned on your system. The setup wizard keeps unrelated entries in this file. Docker-compatible runtimes on macOS and Windows normally handle bind-mount ownership, so users on those systems can usually skip this step. If `/data` is not writable, set the host user and group IDs as shown above.

Compose makes the current host directory available as `/data` inside the container. This is called a bind mount. The setup wizard creates `spotify_monitor.conf` and `.env` there, so the files remain on your computer when the container is replaced. Keep this directory and continue with [Quick Start](quick-start.md#new-here-run-the-setup-wizard). Its Compose setup command pulls the current image with `--pull=always`, so no separate `docker compose pull` is needed during onboarding.

<a id="build-docker-locally"></a>
### Build the Docker Image Locally

From a cloned repository:

```sh
docker build --pull --tag spotify-monitor:local .
docker run --rm spotify-monitor:local --version
```

To use this image through Compose, comment out `image:` in `docker-compose.yml` and uncomment `build: .`.

<a id="next-step"></a>
## Next Step

Continue to [Quick Start](quick-start.md). It shows the setup wizard command for every installation method then explains authentication and the first monitoring run.

<a id="upgrading"></a>
## Upgrading

Upgrading the package or image does not remove your configuration, `.env` secrets, logs or CSV files. Keep those files in the same working directory or another persistent location.

### Upgrade a PyPI Installation

```sh
pip install --upgrade spotify_monitor
spotify_monitor --version
```

Retain any optional extras you use during the upgrade:

```sh
pip install --upgrade "spotify_monitor[browser,legacy-oauth]"
```

### Upgrade a Manual Installation

Replace [spotify_monitor.py](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py) and [requirements.txt](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt) with the newest copies. You can download them in a browser, use the files from an updated clone or run:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt
pip install --upgrade -r requirements.txt
python3 spotify_monitor.py --version
```

Refresh the dependencies even when `requirements.txt` appears unchanged because a new release may add or change a required library.

Use `python spotify_monitor.py --version` on Windows. If you modified the script itself, save your changes before replacing it and reapply them to the new version.

### Upgrade a Docker Compose Installation

Stop an attached run with `Ctrl+C`. From the directory that contains `docker-compose.yml` run:

```sh
docker compose pull
docker compose up --no-log-prefix
```

Compose replaces the service container with one based on the current `latest` image. The host files `spotify_monitor.conf` and `.env` remain in place with the logs and CSV files.

### Upgrade a Direct Docker Installation

Stop the current run then pull the current image:

```sh
docker pull misiektoja/spotify-monitor:latest
docker run --rm misiektoja/spotify-monitor:latest --version
```

Start the tool again with the same `/data` mount and options you used before. If your command uses a version such as `3.0` instead of `latest`, replace that version yourself when you want to upgrade. Each release publishes `latest` plus tags in `vX.Y` and `X.Y` forms.

For example, to pin version 3.0:

```sh
docker pull misiektoja/spotify-monitor:3.0
```

### Upgrade a Locally Built Docker Image

Rebuild from the updated repository and refresh the base image:

```sh
docker build --pull --tag spotify-monitor:local .
docker run --rm spotify-monitor:local --version
```

### Check Upgrade

After any upgrade run the doctor command for your installation:

```sh
spotify_monitor --doctor
```

For Docker Compose use `docker compose run --rm spotify_monitor --doctor`. For a direct image use the normal `/data` mount plus `--doctor`.
