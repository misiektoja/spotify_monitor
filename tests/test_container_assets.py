"""Contract tests for container assets and publishing workflows."""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Reads one repository asset as UTF-8 for structural assertions
def read_asset(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


# Verifies the main image uses Python 3.13, a non-root user and an exec-form entrypoint
def test_dockerfile_runtime_contract():
    dockerfile = read_asset("Dockerfile")
    assert "FROM python:3.13-slim-trixie" in dockerfile
    # The base image is digest-pinned so a rebuilt tag cannot change the runtime silently. Dependabot refreshes the digest
    assert re.search(r"^FROM python:3\.13-slim-trixie@sha256:[0-9a-f]{64}$", dockerfile, re.M)
    # Pending Debian fixes are applied at build time, since the base image lags behind between rebuilds
    assert "apt-get upgrade -y" in dockerfile
    assert "pip uninstall --yes pip" in dockerfile
    assert "SPOTIFY_MONITOR_DOCKER=1" in dockerfile
    assert "USER spotify" in dockerfile
    assert 'ENTRYPOINT ["/usr/local/bin/python", "/opt/spotify_monitor/spotify_monitor.py"]' in dockerfile
    assert 'CMD ["--help"]' in dockerfile
    assert "EXPOSE" not in dockerfile
    assert "COPY ." not in dockerfile
    assert ".env" not in dockerfile
    assert "spotify_monitor.conf" not in dockerfile
    assert "spotipy" not in dockerfile.casefold()
    assert "pycookiecheat" not in dockerfile.casefold()


# Verifies the Docker build context excludes secrets and local development artifacts
def test_dockerignore_excludes_secrets_and_local_artifacts():
    dockerignore = read_asset(".dockerignore").splitlines()
    required = {".git", ".github", ".env", ".env*", "*.conf", "local/", "tests/", "debug/", "assets/", "docs/", "site/", "mkdocs.yml", "__pycache__/", "*.log", "dist/", "*.egg-info/"}
    assert required.issubset(set(dockerignore))


# Verifies Compose uses the published main image, /data mount and detection marker
def test_compose_contract():
    compose = read_asset("docker-compose.yml")
    assert "spotify_monitor:" in compose
    assert "misiektoja/spotify-monitor:latest" in compose
    assert "# build: ." in compose
    assert "init: true" in compose
    assert "stdin_open: true" in compose
    assert "tty: true" in compose
    assert 'SPOTIFY_MONITOR_COMPOSE: "1"' in compose
    assert "- ./:/data:z" in compose
    assert '["--config-file", "/data/spotify_monitor.conf", "--env-file", "/data/.env"]' in compose
    assert "env_file:" not in compose
    assert "ports:" not in compose
    assert "restart:" not in compose
    assert "SPOTIFY_MONITOR_UID" in compose
    assert "SPOTIFY_MONITOR_GID" in compose
    assert "docker compose up --no-log-prefix" in compose


# Verifies the debug secret grabber uses the pinned base, runs non-root and supports host ownership mapping
def test_secret_grabber_container_runtime_contract():
    dockerfile = read_asset("debug/spotify_monitor_secret_grabber_docker/Dockerfile")
    compose = read_asset("debug/spotify_monitor_secret_grabber_docker/compose.yaml")
    assert "FROM python:3.13-slim-trixie" in dockerfile
    # The base image is digest-pinned so a rebuilt tag cannot change the runtime silently. Dependabot refreshes the digest
    assert re.search(r"^FROM python:3\.13-slim-trixie@sha256:[0-9a-f]{64}$", dockerfile, re.M)
    assert "apt-get upgrade -y" in dockerfile
    assert "pip uninstall --yes pip setuptools wheel" in dockerfile
    assert "ARG APP_UID=1000" in dockerfile
    assert "ARG APP_GID=1000" in dockerfile
    assert "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright" in dockerfile
    assert "USER spotify-secrets" in dockerfile
    assert 'user: "${SPOTIFY_SECRET_GRABBER_UID:-1000}:${SPOTIFY_SECRET_GRABBER_GID:-1000}"' in compose
    assert "HOME: /tmp" in compose


# Verifies Docker publishing is test-gated and uses the expected Hub credentials and architectures
def test_docker_publish_workflow_contract():
    workflow = read_asset(".github/workflows/publish-docker.yml")
    assert "IMAGE_NAME: misiektoja/spotify-monitor" in workflow
    assert "uses: ./.github/workflows/tests.yml" in workflow
    assert "needs: test" in workflow
    assert "linux/amd64,linux/arm64" in workflow
    for action in ("docker/setup-qemu-action", "docker/setup-buildx-action", "docker/login-action", "docker/build-push-action"):
        assert re.search(rf"{re.escape(action)}@[0-9a-f]{{40}} # v\d", workflow)
    assert "secrets.DOCKERHUB_USERNAME" in workflow
    assert "secrets.DOCKERHUB_TOKEN" in workflow
    assert "${base_tag#v}" in workflow
    assert "${GITHUB_SHA::7}" in workflow
    assert "push_latest" in workflow
    assert "password:" in workflow
    assert "DOCKERHUB_TOKEN:" not in workflow


# Verifies the debug image publishes on its own cadence, stays test-gated and keeps both architectures
def test_debug_docker_publish_workflow_contract():
    workflow = read_asset(".github/workflows/publish-debug-docker.yml")
    assert "IMAGE_NAME: misiektoja/spotify-secrets-grabber" in workflow
    assert "uses: ./.github/workflows/tests.yml" in workflow
    assert "needs: test" in workflow
    assert "linux/amd64,linux/arm64" in workflow
    assert "file: ./debug/spotify_monitor_secret_grabber_docker/Dockerfile" in workflow
    # The weekly rebuild is what keeps a published image current between extractor changes
    assert "schedule:" in workflow
    assert "workflow_dispatch:" in workflow
    for action in ("docker/setup-qemu-action", "docker/setup-buildx-action", "docker/login-action", "docker/build-push-action"):
        assert re.search(rf"{re.escape(action)}@[0-9a-f]{{40}} # v\d", workflow)
    assert "secrets.DOCKERHUB_USERNAME" in workflow
    assert "secrets.DOCKERHUB_TOKEN" in workflow
    assert "${GITHUB_SHA::7}" in workflow
    assert "push_latest" in workflow
    assert "DOCKERHUB_TOKEN:" not in workflow


# Verifies the extractor keeps the version its published image is tagged with
def test_secret_grabber_declares_a_taggable_version():
    source = read_asset("debug/spotify_monitor_secret_grabber.py")
    version = re.search(r"^v(\d+\.\d+(?:\.\d+)?)$", source, re.M)

    assert version is not None
    assert re.fullmatch(r"[A-Za-z0-9._-]+", version.group(1))


# Verifies the reusable test workflow includes all required container smoke checks
def test_reusable_test_workflow_has_container_gate():
    workflow = read_asset(".github/workflows/tests.yml")
    assert "workflow_call:" in workflow
    assert "container-smoke:" in workflow
    assert "docker build --tag spotify-monitor:ci ." in workflow
    assert "Confirm Python 3.13 runtime" in workflow
    assert "spotify-monitor:ci --version" in workflow
    assert "spotify-monitor:ci --help" in workflow
    assert "spotify-monitor:ci --setup" in workflow
    assert "--generate-config /data/spotify_monitor.conf" in workflow
    assert ':/data:z"' in workflow
    assert "docker compose -f docker-compose.yml config" in workflow
    assert "docker tag spotify-monitor:ci misiektoja/spotify-monitor:latest" in workflow
    assert "docker compose -f docker-compose.yml run --rm --pull=never spotify_monitor --version" in workflow
    assert "docker compose -f docker-compose.yml run --rm --pull=never spotify_monitor --generate-config /data/local/container-smoke/compose-spotify-monitor.conf" in workflow
    assert "SPOTIFY_MONITOR_UID" in workflow
    assert "SPOTIFY_MONITOR_GID" in workflow
    assert "test -s local/container-smoke/compose-spotify-monitor.conf" in workflow
    assert "docker login" not in workflow
    assert "docker push" not in workflow
