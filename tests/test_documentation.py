"""Semantic regression tests for user-facing documentation contracts."""

import re
import textwrap
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


# Reads one repository asset as UTF-8
def read_asset(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


# Returns Markdown headings and offsets while ignoring code-fence contents
def markdown_headings(text: str) -> list[tuple[int, int, str]]:
    headings = []
    offset = 0
    in_fence = False
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            match = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
            if match:
                headings.append((offset, len(match.group(1)), match.group(2)))
        offset += len(line)
    return headings


# Returns one Markdown section whose heading contains every requested term
def markdown_section(text: str, level: int, *heading_terms: str) -> str:
    headings = markdown_headings(text)
    lowered_terms = tuple(term.casefold() for term in heading_terms)
    for index, (start, heading_level, heading_text) in enumerate(headings):
        if heading_level == level and all(term in heading_text.casefold() for term in lowered_terms):
            later_boundaries = (later_start for later_start, later_level, _later_text in headings[index + 1:] if later_level <= level)
            end = next(later_boundaries, len(text))
            return text[start:end]
    raise AssertionError(f"No level-{level} Markdown section contains terms: {heading_terms}")


# Returns normalized nonempty lines from fenced Markdown code blocks
def fenced_code_lines(text: str) -> list[str]:
    blocks = re.findall(r"^[ \t]*```[^\n]*\n(.*?)^[ \t]*```[ \t]*$", text, flags=re.MULTILINE | re.DOTALL)
    return [line.strip() for block in blocks for line in textwrap.dedent(block).splitlines() if line.strip()]


# Verifies a document contains all requested concepts without fixing sentence wording
def assert_concepts(text: str, *concepts: str) -> None:
    lowered = text.casefold()
    for concept in concepts:
        assert concept.casefold() in lowered


# Verifies usage guidance retains the container playback limitation and its controls
def test_usage_docs_cover_default_container_playback_limitation():
    usage = read_asset("docs/usage.md")
    assert_concepts(usage, "host Spotify", "container", "TRACK_SONGS", "--track-in-spotify")


# Verifies setup and Compose guidance retains persistent and custom file-path concepts
def test_docs_cover_setup_and_compose_file_paths():
    assert_concepts(read_asset("docs/setup-and-first-run.md"), "/data", "--config-file", "--env-file")
    assert_concepts(read_asset("docs/configuration.md"), "defaults", ".env")
    assert_concepts(read_asset("docs/usage.md"), "/data", "docker compose run", "--config-file", "--env-file")


# Verifies container Firefox guidance retains every supported host command
def test_usage_docs_cover_container_firefox_import():
    usage = read_asset("docs/usage.md")
    compose = read_asset("docker-compose.yml")
    commands = fenced_code_lines(markdown_section(usage, 3, "Import", "Firefox", "Container"))
    assert '<a id="import-firefox-into-container-authentication"></a>' in usage
    linux_sources = ("$HOME/.mozilla/firefox", "$HOME/snap/firefox/common/.mozilla/firefox", "$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox")
    for source in linux_sources:
        assert f'docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" -v "{source}:/home/spotify/.mozilla/firefox:ro" misiektoja/spotify-monitor:latest --import-browser-cookie --browser firefox --env-file /data/.env' in commands
        assert f'docker compose run --rm -v "{source}:/home/spotify/.mozilla/firefox:ro" spotify_monitor --import-browser-cookie --browser firefox --env-file /data/.env' in commands
        assert f'docker compose run --rm -v "{source}:/home/spotify/.mozilla/firefox:ro"' in compose
    mac_mount = '${HOME}/Library/Application Support/Firefox:/home/spotify/.mozilla/firefox:ro'
    assert any(line.startswith(f'docker run --rm -it --init -v "${{PWD}}:/data:z" -v "{mac_mount}"') for line in commands)
    assert any(line.startswith(f'docker compose run --rm -v "{mac_mount}"') for line in commands)
    windows_mounts = (("${PWD}", "$env:APPDATA\\Mozilla\\Firefox"), ("%cd%", "%APPDATA%\\Mozilla\\Firefox"))
    for current_directory, source in windows_mounts:
        assert any(line.startswith(f'docker run --rm -it --init -v "{current_directory}:/data:z" -v "{source}:/home/spotify/.mozilla/firefox:ro"') for line in commands)
        assert any(line.startswith(f'docker compose run --rm -v "{source}:/home/spotify/.mozilla/firefox:ro"') for line in commands)
    assert_concepts(usage, "Doctor", ":z", ":Z", "Firefox profile")


# Verifies documentation retains portable mounts and a nondestructive dotenv copy command
def test_docs_cover_portable_mounts_and_safe_dotenv_copy():
    assert any('-v "$PWD:/data:z"' in line for line in fenced_code_lines(read_asset("docs/usage.md")))
    assert "test -e .env || cp .env.example .env" in fenced_code_lines(read_asset("docs/configuration.md"))


# Verifies installation guidance retains every supported delivery and upgrade command
def test_installation_docs_cover_delivery_and_upgrade_commands():
    installation = read_asset("docs/installation.md")
    commands = fenced_code_lines(installation)
    required_commands = ("pip install spotify_monitor", "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py", "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt", "pip install --upgrade -r requirements.txt", "docker build --pull --tag spotify-monitor:local .", "docker pull misiektoja/spotify-monitor:latest", "docker compose pull")
    for command in required_commands:
        assert command in commands
    assert_concepts(installation, "PyPI", "Docker Hub", "Docker Compose", "Manual")


# Verifies container onboarding keeps direct Docker first and avoids redundant pulls
def test_container_onboarding_prioritizes_direct_docker_and_avoids_redundant_pulls():
    installation = read_asset("docs/installation.md")
    quick_start = read_asset("docs/setup-and-first-run.md")
    direct_install = markdown_section(installation, 3, "Docker Hub")
    compose_install = markdown_section(installation, 3, "Docker Compose")
    assert installation.index(direct_install) < installation.index(compose_install)
    assert any(line.startswith("docker run --rm --pull=always") for line in fenced_code_lines(direct_install))
    assert "docker pull misiektoja/spotify-monitor:latest" not in fenced_code_lines(direct_install)
    assert "docker compose pull" not in fenced_code_lines(compose_install)
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/docker-compose.yml" in fenced_code_lines(compose_install)
    assert not any(line.startswith("curl -fsSLO") for line in fenced_code_lines(quick_start))
    assert "docker compose run --rm --pull=always spotify_monitor --setup" in fenced_code_lines(quick_start)
    assert "#   docker compose run --rm --pull=always spotify_monitor --setup" in read_asset("docker-compose.yml")


# Verifies both landing pages retain equivalent quick-install commands
def test_landing_pages_offer_equivalent_quick_install_commands():
    required_commands = ("pip install spotify_monitor", "spotify_monitor --setup", "docker compose run --rm --pull=always spotify_monitor --setup", 'docker run --rm --pull=always -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --setup', 'docker run --rm --pull=always -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --setup')
    for relative_path in ("README.md", "docs/index.md"):
        quick_install = markdown_section(read_asset(relative_path), 3, "Quick", "Install")
        commands = fenced_code_lines(quick_install)
        for command in required_commands:
            assert command in commands
        assert "docker pull misiektoja/spotify-monitor:latest" not in commands
        assert "docker compose pull" not in commands
        assert_concepts(quick_install, "PyPI", "Docker image", "Docker Compose", "Linux", "Windows")


# Verifies manual upgrade guidance remains independently executable
def test_manual_upgrade_docs_are_self_contained():
    manual_upgrade = markdown_section(read_asset("docs/installation.md"), 3, "Upgrade", "Manual")
    commands = fenced_code_lines(manual_upgrade)
    for filename in ("spotify_monitor.py", "requirements.txt"):
        assert f"https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/{filename}" in manual_upgrade
    for command in ("curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py", "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt", "pip install --upgrade -r requirements.txt"):
        assert command in commands


# Verifies optional installation extras retain their package and dependency contracts
def test_installation_docs_cover_optional_extra_contents():
    installation = read_asset("docs/installation.md")
    commands = fenced_code_lines(installation)
    assert 'pip install "spotify_monitor[browser]"' in commands
    assert 'pip install "spotify_monitor[legacy-oauth]"' in commands
    assert_concepts(installation, "base", "pycookiecheat", "Spotipy")


# Verifies landing pages retain app-free authentication concepts and the stable OAuth anchor
def test_landing_pages_cover_authentication_policy():
    for relative_path in ("README.md", "docs/index.md"):
        assert_concepts(read_asset(relative_path), "Cookie", "Desktop Client", "web-player", "optional legacy OAuth")
    configuration = read_asset("docs/configuration.md")
    assert '<a id="spotify-oauth-app"></a>' in configuration
    assert_concepts(configuration, "migration")


# Verifies usage guidance exposes every supported target form and install command prefix
def test_usage_docs_cover_target_forms_and_install_commands():
    assert_concepts(read_asset("docs/usage.md"), "spotify:user:spotify_user_uri_id", "https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id", "TARGET_USER_URI_ID", "python3 spotify_monitor.py", "docker compose run --rm spotify_monitor", "misiektoja/spotify-monitor:latest")


# Verifies debugging downloads retain the supported curl commands
def test_debugging_docs_use_curl_downloads():
    commands = fenced_code_lines(read_asset("docs/debugging.md"))
    assert not any(line.casefold().startswith("wget ") for line in commands)
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_totp_test.py" in commands
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_secret_grabber.py" in commands


# Verifies secret-grabber container guidance retains mutable-image pull behavior
def test_secret_grabber_container_pull_contract():
    commands = fenced_code_lines(read_asset("docs/debugging.md"))
    compose = read_asset("debug/spotify_monitor_secret_grabber_docker/compose.yaml")
    assert sum(line.startswith("docker run --rm --pull=always") for line in commands) == 4
    assert "docker compose run --rm spotify-secrets-grabber --all" in commands
    assert "image: misiektoja/spotify-secrets-grabber:latest" in compose
    assert "pull_policy: always" in compose


# Verifies webhook guidance targets the configuration page and its stable anchor
def test_webhook_setup_anchor_is_consistent():
    configuration = read_asset("docs/configuration.md")
    assert '<a id="webhook-settings"></a>' in configuration
    assert "https://misiektoja.github.io/spotify_monitor/configuration/#webhook-settings" in read_asset("README.md")


# Verifies MkDocs navigation includes every published page and strict deployment
def test_documentation_site_contract():
    mkdocs = read_asset("mkdocs.yml")
    workflow = read_asset(".github/workflows/docs.yml")
    assert "site_url: https://misiektoja.github.io/spotify_monitor/" in mkdocs
    for page in ("index.md", "installation.md", "setup-and-first-run.md", "configuration.md", "usage.md", "troubleshooting.md", "debugging.md", "testing.md", "about.md"):
        assert f": {page}" in mkdocs
        assert (PROJECT_ROOT / "docs" / page).is_file()
    assert "mkdocs gh-deploy --force --strict" in workflow
