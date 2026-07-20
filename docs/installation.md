# Installation

<a id="requirements"></a>
## Requirements

* Python 3.9 or higher
* Core libraries: `requests`, `python-dateutil`, `urllib3`, `pyotp`, `python-dotenv`, `wcwidth`, `Pillow`
* Optional legacy OAuth library: `spotipy`
* Optional Chromium cookie import library: `pycookiecheat`

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="installation"></a>
## Installation

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install spotify_monitor
```

<a id="manual-installation"></a>
### Manual Installation

Download the *[spotify_monitor.py](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install requests python-dateutil urllib3 pyotp python-dotenv wcwidth Pillow
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

Spotipy is optional and is needed only for configured legacy OAuth app credentials that use the Web API metadata path. PyPI users can install that support through the `legacy-oauth` extra:

```sh
pip install "spotify_monitor[legacy-oauth]"
```

For manual single-file installations install the optional dependency directly:

```sh
pip install "spotipy>=2.24.0"
```

Firefox cookie import needs no extra dependency. To import from Chrome, Brave or Chromium on macOS or Linux install the browser extra:

```sh
pip install "spotify_monitor[browser]"
```

For a manual single-file installation use `pip install "pycookiecheat>=0.8"` instead.

<a id="upgrading"></a>
### Upgrading

To upgrade to the latest version when installed from PyPI:

```sh
pip install spotify_monitor -U
```

If you installed manually, download the newest *[spotify_monitor.py](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py)* file to replace your existing installation.
