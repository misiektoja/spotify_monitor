# Installation

Choose one installation method and keep using its command format throughout the documentation. PyPI is the simplest local installation. Docker Compose is the recommended container installation because it keeps configuration, secrets and output files in the current directory.

<a id="requirements"></a>
## Requirements

Choose one runtime path:

**Python path**:

- [Python](https://www.python.org/downloads/) 3.9 or higher
- Core libraries: `requests`, `python-dateutil`, `urllib3`, `pyotp`, `python-dotenv`, `wcwidth`, `Pillow`
- Optional legacy OAuth library: `spotipy`
- Optional Chromium cookie import library: `pycookiecheat`

**Container path** (Python is not required on the host):

- Any Docker-compatible runtime such as:
    - [Docker Desktop](https://docs.docker.com/get-started/get-docker/) (macOS, Windows, Linux)
    - [Docker Engine](https://docs.docker.com/engine/install/) (Linux)
    - [Colima](https://colima.run/docs/installation/) with Docker CLI (macOS)
    - [OrbStack](https://docs.orbstack.dev/quick-start) (macOS)
    - [Rancher Desktop](https://docs.rancherdesktop.io/getting-started/installation/) with Moby or Docker CLI enabled (macOS, Windows, Linux)
- The Docker Compose v2 plugin if you choose Docker Compose

The published image already contains Python and all core libraries. You do not need a local Python installation for Docker.

Container commands use the Docker-compatible `docker` CLI. Check the runtime with `docker --version`. If you choose Compose, check the plugin with `docker compose version`.

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="installation"></a>
## Choose an Installation Method

| Method | Best for | Command used in later examples |
| --- | --- | --- |
| PyPI | The easiest local install and automatic upgrades | `spotify_monitor [OPTIONS]` |
| Manual script | A portable single-file local install | `python3 spotify_monitor.py [OPTIONS]` on macOS/Linux or `python spotify_monitor.py [OPTIONS]` on Windows |
| Docker Compose | A persistent container with files stored in the current directory | `docker compose run --rm spotify_monitor [OPTIONS]` |
| Docker Hub image | Direct container runs without a Compose file | `docker run ... misiektoja/spotify-monitor:latest [OPTIONS]` |

The examples on Configuration, Usage and Troubleshooting use the shorter PyPI command unless a container path or behavior needs a dedicated example. Replace that command with the matching form above. The setup wizard and `--help` also detect the active installation and print matching commands.

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install spotify_monitor
spotify_monitor --version
```

Each command below that uses square brackets installs the base `spotify_monitor` package plus its named optional dependencies. Use only the command matching your needs. You do not need to run the plain install command first.

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

<a id="docker-compose"></a>
### Install with Docker Compose

Download the project Compose file into the directory where you want to keep the configuration and output:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/docker-compose.yml
docker compose pull
docker compose run --rm spotify_monitor --version
```

You can also download [docker-compose.yml](https://github.com/misiektoja/spotify_monitor/blob/main/docker-compose.yml) in a browser or use the file from a cloned repository.

On Linux, export your host user and group before setup if the current directory is not writable by the image user `10001:10001`:

```sh
export SPOTIFY_MONITOR_UID="$(id -u)"
export SPOTIFY_MONITOR_GID="$(id -g)"
```

Keep these variables set for later `docker compose` commands. Alternatively store their numeric values as `SPOTIFY_MONITOR_UID` and `SPOTIFY_MONITOR_GID` in `.env`. The setup wizard preserves unrelated entries in that file. Docker Desktop on macOS and Windows normally handles bind-mount ownership without this override.

Compose mounts the current directory at `/data`. The setup wizard creates `spotify_monitor.conf` and `.env` on the host so upgrades or container replacement do not remove them. Continue with [Quick Start](quick-start.md#new-here-run-the-setup-wizard).

<a id="docker-image"></a>
### Install from Docker Hub

The published [`misiektoja/spotify-monitor`](https://hub.docker.com/r/misiektoja/spotify-monitor) image supports `linux/amd64` and `linux/arm64`:

```sh
docker pull misiektoja/spotify-monitor:latest
docker run --rm misiektoja/spotify-monitor:latest --version
```

Plain `docker run` reuses a cached image when the tag already exists locally. Repeat the documented `docker pull` during upgrades. Normal monitoring commands do not force a registry check on every start, which avoids an unexpected release change during routine runs.

Normal runs mount the current directory at `/data` so configuration and output survive the temporary container. On Linux, pass your host identity so setup can write to that directory. The [Quick Start](quick-start.md#new-here-run-the-setup-wizard) shows both Docker Desktop and Linux commands.

Docker Desktop examples use `${PWD}` in macOS shells and Windows PowerShell. In Windows Command Prompt use `%cd%` for the current directory. Linux examples use `$PWD` and add the host user mapping when needed.

The Compose file and direct commands use the `/data:z` mount form for SELinux hosts. If a Docker-compatible runtime rejects the `:z` suffix, remove only that suffix and keep the `/data` mount.

The published image includes the core dependencies but not the optional `legacy-oauth` or Chromium browser extras. Anonymous web-player metadata works without Spotipy. Default container authentication uses private `sp_dc` entry because Chromium browser credentials are unavailable inside the image.

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

Configuration files, dotenv secrets, logs and CSV output are not part of the PyPI package or Docker image. Keep them in your working directory or another persistent path and reuse them after an upgrade.

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
docker compose up
```

Compose recreates the service from the current `latest` image when needed. The bind-mounted `spotify_monitor.conf`, `.env`, logs and CSV files remain on the host.

### Upgrade a Direct Docker Installation

Stop the current run then pull the current image:

```sh
docker pull misiektoja/spotify-monitor:latest
docker run --rm misiektoja/spotify-monitor:latest --version
```

Start the tool again with the same `/data` bind mount and options you used before. If you pin a versioned tag such as `3.0`, change that tag explicitly when you want to move to another release. Published releases update `latest` and also publish both `vX.Y` and `X.Y` tags.

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
