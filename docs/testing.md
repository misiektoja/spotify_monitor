# Testing

The [tests directory](https://github.com/misiektoja/spotify_monitor/tree/main/tests/) contains an offline pytest suite for contributors. It checks configuration and target parsing, setup, browser cookie import, recovery advice, Doctor, startup output, notification delivery, metadata fallbacks, packaging and container files. Tests replace Spotify requests with local fixtures.

Install the test dependencies and run the suite from the repository root:

```sh
pip install -e '.[test]'
python -m pytest
```

GitHub Actions runs the same suite on Python 3.9 through 3.14. It also checks Windows setup, optional dependency installation, the built wheel, strict documentation, Docker and Docker Compose. A separate quality job runs pyright plus subprocess-aware branch coverage. See the [test workflow](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/tests.yml).

## Test Layers

The suite combines several test types:

- Unit and component tests exercise focused functions with deterministic inputs.
- Integration tests use temporary files, SQLite databases and real loopback HTTP and SMTP connections.
- Packaging tests build the wheel, install it into a clean environment and run the installed command outside the source tree.
- The offline E2E test runs one complete CLI monitoring iteration against a loopback Spotify fixture.
- Contract tests validate stable documentation commands, links, container assets and publishing workflows.
- CI smoke tests run the application through Windows, Docker and Docker Compose.

No test needs a real Spotify cookie, SMTP password or webhook URL. Loopback transport tests use fake credentials that are accepted only by temporary local servers.

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
