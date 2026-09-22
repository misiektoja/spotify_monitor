"""Contract tests for container assets and publishing workflows."""

import re
import sqlite3
from pathlib import Path

import pytest


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


# Where Firefox really keeps its profile root on each documented host, as a base variable, a path below it and the
# folder profiles sit in. The host side of a mount must name this exact directory, since the container reads only the
# path it is mapped onto and cannot descend into a tree handed to it one level too high
CONTAINER_HOST_FIREFOX_ROOTS = {
    "macos": ("HOME", "Library/Application Support/Firefox", "Profiles"),
    "linux": ("HOME", ".mozilla/firefox", ""),
    "linux-snap": ("HOME", "snap/firefox/common/.mozilla/firefox", ""),
    "linux-flatpak": ("HOME", ".var/app/org.mozilla.firefox/.mozilla/firefox", ""),
    "windows-powershell": ("APPDATA", "Mozilla/Firefox", "Profiles"),
    "windows-cmd": ("APPDATA", "Mozilla/Firefox", "Profiles"),
}


# Returns the container path a documented host mount lands on
def container_mount_target(mount: str) -> str:
    return mount.strip('"').rsplit(":", 2)[-2]


# Returns the host path a documented mount reads, with its home or APPDATA variable resolved to a real directory
def expand_mount_source(mount: str, base: Path) -> Path:
    source = mount.strip('"').rsplit(":", 2)[0]
    for variable in ("${HOME}", "$HOME", "$env:APPDATA", "%APPDATA%"):
        source = source.replace(variable, str(base))
    return Path(source.replace("\\", "/"))


# Writes a minimal Firefox cookie database holding one Spotify session cookie
def write_firefox_cookie(cookie_file: Path, value: str) -> None:
    with sqlite3.connect(cookie_file) as connection:
        connection.execute("CREATE TABLE moz_cookies (host TEXT, name TEXT, value TEXT, expiry INTEGER, lastAccessed INTEGER)")
        connection.execute("INSERT INTO moz_cookies VALUES ('spotify.com', 'sp_dc', ?, 0, 1)", (value,))


# Verifies every documented host mount lands on the one path the container importer reads
def test_every_container_mount_targets_the_importer_path():
    import spotify_monitor as monitor

    assert set(monitor.CONTAINER_FIREFOX_HOSTS) == set(CONTAINER_HOST_FIREFOX_ROOTS)
    for host_os, (_, mount) in monitor.CONTAINER_FIREFOX_HOSTS.items():
        assert container_mount_target(mount) == "/home/spotify/.mozilla/firefox", host_os
        assert mount.strip('"').endswith(":ro"), host_os


# Verifies each documented mount hands the container a profile it can actually read, starting from the host layout
# rather than the container one. String equality between the constant and the docs cannot catch a host path that
# names a parent of the profile root, because the mount string stays internally consistent either way
@pytest.mark.parametrize("host_os", sorted(CONTAINER_HOST_FIREFOX_ROOTS))
def test_a_documented_mount_reaches_a_profile_inside_the_container(tmp_path, host_os, real_browser_profiles):
    import spotify_monitor as monitor

    base_variable, root_path, profile_folder = CONTAINER_HOST_FIREFOX_ROOTS[host_os]
    host_base = tmp_path / "host" / base_variable
    host_root = host_base / root_path
    profile_dir = (host_root / profile_folder if profile_folder else host_root) / "abc.default-release"
    profile_dir.mkdir(parents=True)
    write_firefox_cookie(profile_dir / "cookies.sqlite", "mounted-cookie")
    relative = f"{profile_folder}/" if profile_folder else ""
    (host_root / "profiles.ini").write_text(f"[Profile0]\nName=default-release\nIsRelative=1\nPath={relative}abc.default-release\n", encoding="utf-8")

    mount = monitor.CONTAINER_FIREFOX_HOSTS[host_os][1]
    assert expand_mount_source(mount, host_base) == host_root, host_os

    # A bind mount makes the host directory appear at the container path, which a symlink reproduces well enough here
    container_home = tmp_path / "container"
    mount_point = container_home / Path(container_mount_target(mount)).relative_to("/home/spotify")
    mount_point.parent.mkdir(parents=True)
    mount_point.symlink_to(expand_mount_source(mount, host_base), target_is_directory=True)

    # The container always runs Linux, whatever host the mount came from
    profiles = monitor.discover_firefox_profiles(system_name="Linux", home=container_home)

    assert [profile["dir"] for profile in profiles] == ["abc.default-release"], host_os
    assert monitor.read_firefox_sp_dc(profiles[0]["cookie_file"]) == "mounted-cookie"


# Verifies a mounted tree is still reached when profiles.ini is absent, which happens when the ini is unreadable or
# when only the profile directory itself was copied into place
@pytest.mark.parametrize("profile_folder", ["", "Profiles"])
def test_a_mount_without_profiles_ini_still_reaches_a_profile(tmp_path, profile_folder, real_browser_profiles):
    import spotify_monitor as monitor

    profile_dir = tmp_path / ".mozilla/firefox" / profile_folder / "abc.default-release"
    profile_dir.mkdir(parents=True)
    write_firefox_cookie(profile_dir / "cookies.sqlite", "deep-mount-cookie")

    profiles = monitor.discover_firefox_profiles(system_name="Linux", home=tmp_path)

    assert [profile["dir"] for profile in profiles] == ["abc.default-release"]
    assert monitor.read_firefox_sp_dc(profiles[0]["cookie_file"]) == "deep-mount-cookie"
