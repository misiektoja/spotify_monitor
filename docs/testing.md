# Testing

The [tests directory](https://github.com/misiektoja/spotify_monitor/tree/main/tests/) contains an offline pytest suite for contributors. It checks configuration and target parsing, setup, browser cookie import, recovery advice, Doctor, startup output, notification delivery, metadata fallbacks, packaging and container files. Tests replace Spotify requests with local fixtures. Its [README](https://github.com/misiektoja/spotify_monitor/blob/main/tests/README.md) maps every test file to the area it covers.

Install the test dependencies and run the suite from the repository root:

```sh
pip install -e '.[test]'
python -m pytest
```

Add the browser and legacy OAuth extras when you work on browser cookie import or the legacy OAuth backend:

```sh
pip install -e '.[test,browser,legacy-oauth]'
```

The `notification-images` extra needs no separate install. The test extra already brings in Pillow, so the artwork tests covering ntfy attachments run from a plain `.[test]` install. If Pillow is missing anyway, those tests skip instead of failing.

A pinned [Ruff](https://docs.astral.sh/ruff/) lint pass runs alongside the suite. It selects defect rules only, pyflakes and bugbear, so it reports unused names, undefined names and common bug patterns without enforcing formatting or import order:

```sh
pip install -e '.[lint]'
python -m ruff check spotify_monitor.py debug tests
```

GitHub Actions runs the linter, then the same suite on Python 3.9 through 3.14. It also checks Windows setup, optional dependency installation, the built wheel, strict documentation, Docker and Docker Compose. A separate quality job runs pyright plus subprocess-aware branch coverage. See the [test workflow](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/tests.yml).

The same suite gates every release. Publishing to [PyPI](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/publish.yml) and to [Docker Hub](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/publish-docker.yml) runs it first and stops if anything fails, so a release cannot ship ahead of a passing test run.

## Test Layers

The suite combines several test types:

- Unit and component tests exercise focused functions with deterministic inputs.
- Integration tests use temporary files, SQLite databases and real loopback HTTP and SMTP connections.
- Packaging tests build the wheel, install it into a clean environment and run the installed command outside the source tree.
- The offline E2E test runs one complete CLI monitoring iteration against a loopback Spotify fixture.
- Monitoring-loop tests drive the Friend Activity loop against fake buddy-list responses to check authentication recovery, retry timing, activity flag transitions and track-change recording.
- Contract tests validate stable documentation commands, links, container assets and publishing workflows.
- CI smoke tests run the application through Windows, Docker and Docker Compose.

No test needs a real Spotify cookie, SMTP password or webhook URL. Loopback transport tests use fake credentials that are accepted only by temporary local servers.

## Supply Chain Checks

A separate [supply chain workflow](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/supply-chain.yml) runs on every change and again weekly, so a vulnerability published after a merge is still caught. It scans the full commit history for leaked credentials with gitleaks, audits the resolved dependency tree with `pip-audit`, builds a CycloneDX software bill of materials that lists every package a user actually installs and scans the container image for fixable high and critical vulnerabilities.

Two further workflows watch the code and the project setup. [CodeQL](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/codeql.yml) runs GitHub's `security-extended` Python queries on every change and weekly, reporting findings as code scanning alerts. [OpenSSF Scorecard](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/scorecard.yml) scores the repository's security practices such as branch protection, action pinning and dependency update automation. It publishes the score shown as a badge on the project page.

Published archives stay verifiable: the [release assets workflow](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/release-assets.yml) records SHA-256 checksums and signs a build provenance attestation, so an unsigned download can be told apart from a tampered one. The attestation bundle is attached to the release as an `.intoto.jsonl` asset, so provenance can be checked from the downloaded files alone when the attestations API is unreachable.

The pytest suite covers the workflows themselves. It fails when a third-party action is not pinned to a commit SHA, when a pin lacks its version comment or when a workflow passes an event value straight into a shell.

## Focused Test Commands

Run semantic documentation contracts:

```sh
python -m pytest tests/test_documentation.py
```

Run packaging tests:

```sh
python -m pytest tests/test_packaging.py
```

Run local transport and offline E2E tests:

```sh
python -m pytest tests/test_local_transports.py tests/test_offline_e2e.py
```

Run property-based tests:

```sh
python -m pytest tests/test_properties.py
```

## Coverage and Type Checking

Coverage stores all parent and subprocess data below `local/`:

```sh
mkdir -p local/coverage-data
COVERAGE_FILE="$PWD/local/coverage-data/.coverage" python -m coverage run -m pytest
COVERAGE_FILE="$PWD/local/coverage-data/.coverage" python -m coverage combine local/coverage-data
COVERAGE_FILE="$PWD/local/coverage-data/.coverage" python -m coverage report
```

Run pyright against the application, debug tools and tests while selecting the active interpreter:

```sh
python -m pyright --pythonpath "$(command -v python)" spotify_monitor.py debug tests
```

The current coverage floor is a baseline rather than a final target. Raise it gradually as meaningful behavior receives new tests.
