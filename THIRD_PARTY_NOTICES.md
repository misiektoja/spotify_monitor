# Third-party notices

spotify_monitor original code is licensed under GPL-3.0-or-later. See [LICENSE](LICENSE).

The distributed package contains no vendored third-party source. It declares the dependencies below, which are installed from PyPI under their own licenses and remain the property of their authors.

## Runtime dependencies

| Component | Required version | License | Use |
| --- | --- | --- | --- |
| [requests](https://github.com/psf/requests) | >=2.0 | Apache-2.0 | HTTP for Spotify, Last.fm, notifications and artwork downloads |
| [python-dateutil](https://github.com/dateutil/dateutil) | >=2.8 | Apache-2.0 or BSD-3-Clause | Timestamp parsing and relative date arithmetic |
| [urllib3](https://github.com/urllib3/urllib3) | >=2.0.7 | MIT | HTTP connection pooling and retry handling |
| [pyotp](https://github.com/pyauth/pyotp) | >=2.9.0 | MIT | TOTP generation for Spotify web-player token refresh |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | >=0.19 | BSD-3-Clause | Reading secrets from `.env` |
| [wcwidth](https://github.com/jquast/wcwidth) | >=0.2.7 | MIT | Terminal column widths for aligned output and truncation |
| [Pillow](https://github.com/python-pillow/Pillow) | >=12.0.0 on Python 3.10 and newer, >=11.3.0,<12 on Python 3.9, `notification-images` extra | MIT-CMU | Artwork handling for ntfy image notifications |
| [spotipy](https://github.com/spotipy-dev/spotipy) | >=2.24.0, `legacy-oauth` extra | MIT | Legacy Spotify Web API metadata backend |
| [pycookiecheat](https://github.com/n8henrie/pycookiecheat) | >=0.8, `browser` extra | MIT | Importing Chrome, Brave and Chromium cookies on macOS and Linux |

## Build, test and documentation dependencies

These are not installed with the package and are not redistributed with it.

| Component | License | Use |
| --- | --- | --- |
| [pytest](https://github.com/pytest-dev/pytest) | MIT | Test suite |
| [coverage](https://github.com/nedbat/coveragepy) | Apache-2.0 | Branch coverage measurement |
| [Hypothesis](https://github.com/HypothesisWorks/hypothesis) | MPL-2.0 | Property-based tests for configuration round-trips |
| [pyright](https://github.com/microsoft/pyright) | MIT | Static type checking |
| [Ruff](https://github.com/astral-sh/ruff) | MIT | Linting the module and the test suite |
| [PyYAML](https://github.com/yaml/pyyaml) | MIT | Validating workflows and issue templates in the test suite |
| [Playwright](https://github.com/microsoft/playwright-python) | Apache-2.0 | Headless browser for the debug secret grabber |
| [CycloneDX](https://github.com/CycloneDX/cyclonedx-python) | Apache-2.0 | Software bill of materials in the supply chain workflow |
| [build](https://github.com/pypa/build), [setuptools](https://github.com/pypa/setuptools), [wheel](https://github.com/pypa/wheel) | MIT | Package build |
| [MkDocs Material](https://github.com/squidfunk/mkdocs-material) | MIT | Documentation site |

## Container image

The published Docker image is built on the official [`python:3.13-slim-trixie`](https://hub.docker.com/_/python) image and inherits the licenses of Debian and the Python distribution it carries.

The debug secret grabber image is built on the official [`python:3.13-slim-trixie`](https://hub.docker.com/_/python) image and additionally carries the [Chromium](https://www.chromium.org/chromium-projects/) build that Playwright downloads, which is covered by its own BSD-3-Clause and related upstream licenses.

## External data sources

The debug utility `spotify_monitor_totp_test --download-secrets` can fetch current TOTP secret material from [xyloflake/spot-secrets-go](https://github.com/xyloflake/spot-secrets-go). Nothing from that project is vendored, redistributed or used by the main monitoring tool. The download happens only when you pass that flag explicitly and the source URL is configurable through `SECRET_CIPHER_DICT_URL`.

## Reporting a licensing problem

If a component is listed incorrectly or a notice is missing, open an issue. This manually maintained notice does not replace the license texts distributed by the dependency authors.
