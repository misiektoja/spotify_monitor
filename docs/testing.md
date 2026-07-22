# Testing

The [tests directory](https://github.com/misiektoja/spotify_monitor/tree/main/tests/) contains an offline pytest suite for contributors. It checks configuration and target parsing, setup, browser cookie import, recovery advice, Doctor, startup output, webhook delivery, metadata fallbacks and container files. Tests replace network requests with local test doubles or fixtures.

Install the test dependencies and run the suite from the repository root:

```sh
pip install -e '.[test]'
python -m pytest
```

GitHub Actions runs the same suite on Python 3.9 through 3.14. It also checks Windows setup, optional dependency installation, Docker and Docker Compose. See the [test workflow](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/tests.yml).
