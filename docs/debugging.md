# Debugging Tools

The [debug directory](https://github.com/misiektoja/spotify_monitor/tree/main/debug) contains two utilities for testing Spotify token retrieval and reading current TOTP values. Most users do not need these tools.

<a id="access-token-retrieval-via-sp_dc-cookie-and-totp"></a>
## Access Token Retrieval via sp_dc Cookie and TOTP

The [spotify_monitor_totp_test](https://github.com/misiektoja/spotify_monitor/blob/main/debug/spotify_monitor_totp_test.py) requests a Spotify access token with a Web Player `sp_dc` cookie and TOTP parameters.

Download the file in a browser or run:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_totp_test.py
```

Install requirements:

```sh
pip install requests python-dateutil pyotp
```

Run:

```sh
python3 spotify_monitor_totp_test.py --sp-dc "your_sp_dc_cookie_value"
```

The command prints the access token response. Example output:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_totp_test.png" alt="spotify_monitor_totp_test" width="100%"/>
</p>

> **If the included TOTP values stop working:** `--fetch-secrets` opens Spotify Web Player in a headless Playwright browser and extracts current values. `--download-secrets` reads `SECRET_CIPHER_DICT_URL` from an HTTP URL or local `file:` URL. Its default source is [xyloflake/spot-secrets-go](https://github.com/xyloflake/spot-secrets-go). These options affect only this test utility. The main Spotify Monitor tool uses `TOTP_VERSION` and `TOTP_SECRET_CIPHER_BYTES` instead.

```sh
python3 spotify_monitor_totp_test.py --sp-dc "your_sp_dc_cookie_value" --fetch-secrets
python3 spotify_monitor_totp_test.py --sp-dc "your_sp_dc_cookie_value" --download-secrets
```

<a id="secret-key-extraction-from-spotify-web-player-bundles"></a>
## Secret Key Extraction from Spotify Web Player Bundles

The [spotify_monitor_secret_grabber](https://github.com/misiektoja/spotify_monitor/blob/main/debug/spotify_monitor_secret_grabber.py) reads TOTP keys from Spotify Web Player JavaScript bundles. It scans the loaded source first and keeps the older runtime hook as a fallback.

The extractor can return v59, v60 and v61 from the current web-player bundle even when the older runtime hook finds nothing.

> **Recommended:** Use the [Docker method](#-secret-key-extraction-via-docker) if you do not already have Playwright and its browser files installed.

Download the file in a browser or run:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_secret_grabber.py
```

Install requirements:

```sh
pip install playwright
playwright install
```

Run interactively (default output mode):

```sh
python3 spotify_monitor_secret_grabber.py
```

Example output:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/assets/spotify_monitor_secret_grabber.png" alt="spotify_monitor_secret_grabber" width="100%"/>
</p>

Show help:
```sh
python3 spotify_monitor_secret_grabber.py -h
```

---

<a id="cli-output-modes"></a>
## CLI Output Modes

Choose the output format with one of these options:

| Flag | Description | Output |
|------|--------------|--------|
| `--secret` | Prints plain JSON array of extracted secrets | `[{"version": X, "secret": "..."}, ...]` |
| `--secretbytes` | Prints JSON array with ASCII byte values | `[{"version": X, "secret": [..]}, ...]` |
| `--secretdict` | Prints JSON object/dict mapping version → byte list | `{"X": [..], "Y": [..]}` |
| `--all` | Extracts secrets and **writes all three outputs** to local files | `secrets.json`, `secretBytes.json`, `secretDict.json` |

Save the version-to-byte mapping as JSON:

```sh
python3 spotify_monitor_secret_grabber.py --secretdict > secretDict.json
```

Generate all three output files at once:

```sh
python3 spotify_monitor_secret_grabber.py --all
```

Default file paths and names can be configured directly in the `OUTPUT_FILES` dictionary at the top of the script.

---

<a id="-secret-key-extraction-via-docker"></a>
## Secret Key Extraction via Docker

A prebuilt multi-architecture image is available on Docker Hub: [`misiektoja/spotify-secrets-grabber`](https://hub.docker.com/r/misiektoja/spotify-secrets-grabber)

The examples use the `latest` tag. `--pull=always` in direct commands and `pull_policy: always` in Compose make Docker check for a newer image before each run. To stay on one release, add a version such as `:1.3` to the image name.

This image works on:

- macOS (Intel & Apple Silicon)
- Linux (x86_64 and ARM64)
- Windows (Docker Desktop / WSL2)
- Raspberry Pi 4/5 (64-bit OS)

Run interactively (default output mode):

```sh
docker run --rm --pull=always misiektoja/spotify-secrets-grabber
```

Show help:
```sh
docker run --rm --pull=always misiektoja/spotify-secrets-grabber -h
```

Save the version-to-byte mapping as JSON:
```sh
docker run --rm --pull=always misiektoja/spotify-secrets-grabber --secretdict > secretDict.json
```

Generate all three output files at once:

```sh
docker run --rm --pull=always -v .:/work -w /work misiektoja/spotify-secrets-grabber --all
```

*For SELinux hosts (Fedora/RHEL), use `-v .:/work:Z`.*

<a id="optional-use-docker-compose-one-command-for-all-oss"></a>
To use Docker Compose, run the included [compose.yaml](https://github.com/misiektoja/spotify_monitor/blob/main/debug/spotify_monitor_secret_grabber_docker/compose.yaml):

```sh
docker compose run --rm spotify-secrets-grabber --all
```

Run the command from the directory that contains `compose.yaml`. The `.:/work` mount saves generated files in that host directory.

---

Use the generated `secretDict.json` with `spotify_monitor_totp_test`. The main Spotify Monitor tool reads its values from `TOTP_VERSION` and `TOTP_SECRET_CIPHER_BYTES`. If Spotify selects a new TOTP version, update those settings with the values from the current web-player bundle.
