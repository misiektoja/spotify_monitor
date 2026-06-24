from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Reads one repository asset as UTF-8 for structural assertions
def read_asset(relative_path):
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


# Verifies the main image uses Python 3.9, a non-root user and an exec-form entrypoint
def test_dockerfile_runtime_contract():
    dockerfile = read_asset("Dockerfile")
    assert "FROM python:3.9-slim-bookworm" in dockerfile
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


# Verifies the Docker build context excludes secret-bearing and development artifacts
def test_dockerignore_excludes_secrets_and_local_artifacts():
    dockerignore = read_asset(".dockerignore").splitlines()
    required = {".git", ".github", ".env", ".env*", "*.conf", "local/", "tests/", "debug/", "assets/", "__pycache__/", "*.log", "dist/", "*.egg-info/"}
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
    assert "- ./:/data" in compose
    assert '["--config-file", "/data/spotify_monitor.conf"]' in compose
    assert "env_file:" not in compose
    assert "ports:" not in compose
    assert "restart:" not in compose
    assert "SPOTIFY_MONITOR_UID" in compose
    assert "SPOTIFY_MONITOR_GID" in compose


# Verifies Docker publishing is test-gated and uses the expected Hub credentials and architectures
def test_docker_publish_workflow_contract():
    workflow = read_asset(".github/workflows/publish-docker.yml")
    assert "IMAGE_NAME: misiektoja/spotify-monitor" in workflow
    assert "uses: ./.github/workflows/tests.yml" in workflow
    assert "needs: test" in workflow
    assert "linux/amd64,linux/arm64" in workflow
    assert "docker/setup-qemu-action@v4" in workflow
    assert "docker/setup-buildx-action@v4" in workflow
    assert "docker/login-action@v4" in workflow
    assert "docker/build-push-action@v7" in workflow
    assert "secrets.DOCKERHUB_USERNAME" in workflow
    assert "secrets.DOCKERHUB_TOKEN" in workflow
    assert "${base_tag#v}" in workflow
    assert "${GITHUB_SHA::7}" in workflow
    assert "push_latest" in workflow
    assert "password:" in workflow
    assert "DOCKERHUB_TOKEN:" not in workflow


# Verifies the reusable test workflow includes all required container smoke checks
def test_reusable_test_workflow_has_container_gate():
    workflow = read_asset(".github/workflows/tests.yml")
    assert "workflow_call:" in workflow
    assert "container-smoke:" in workflow
    assert "docker build --tag spotify-monitor:ci ." in workflow
    assert "Confirm Python 3.9 runtime" in workflow
    assert "spotify-monitor:ci --version" in workflow
    assert "spotify-monitor:ci --help" in workflow
    assert "spotify-monitor:ci --setup" in workflow
    assert "--generate-config /data/spotify_monitor.conf" in workflow
    assert "docker compose -f docker-compose.yml config" in workflow
    assert "docker tag spotify-monitor:ci misiektoja/spotify-monitor:latest" in workflow
    assert "docker compose -f docker-compose.yml run --rm spotify_monitor --version" in workflow
    assert "docker compose -f docker-compose.yml run --rm spotify_monitor --generate-config /data/local/container-smoke/compose-spotify-monitor.conf" in workflow
    assert "SPOTIFY_MONITOR_UID" in workflow
    assert "SPOTIFY_MONITOR_GID" in workflow
    assert "test -s local/container-smoke/compose-spotify-monitor.conf" in workflow
    assert "docker login" not in workflow
    assert "docker push" not in workflow


# Verifies the README states the default container host playback limitation
def test_readme_documents_default_container_playback_limitation():
    readme = read_asset("README.md")
    assert "Host Spotify auto-play is unavailable by default inside a container" in readme
    assert "TRACK_SONGS" in readme
    assert "--track-in-spotify" in readme
