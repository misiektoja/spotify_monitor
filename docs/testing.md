# Testing

The project ships an offline pytest suite under [tests/](https://github.com/misiektoja/spotify_monitor/tree/main/tests/). It covers configuration and target parsing, setup flows, browser cookie import, recovery advice, doctor checks, startup output, webhook delivery, Spotify metadata fallbacks and container assets. Network-facing paths use mocks or local fixtures.

Install the test dependencies and run the suite from the repository root:

```sh
pip install -e '.[test]'
python -m pytest
```

The same suite runs in GitHub Actions across Python 3.9 through 3.14. It also includes Windows setup checks, optional dependency installation and Docker plus Docker Compose smoke checks. See the [test workflow](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/tests.yml).
