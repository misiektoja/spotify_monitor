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


# Verifies the usage guide states the default container host playback limitation
def test_usage_docs_describe_default_container_playback_limitation():
    usage = read_asset("docs/usage.md")
    assert "Host Spotify auto-play is unavailable by default inside a container" in usage
    assert "TRACK_SONGS" in usage
    assert "--track-in-spotify" in usage


# Verifies setup and Compose docs explain persistent and custom file paths
def test_docs_explain_setup_and_compose_file_paths():
    quick_start = read_asset("docs/setup-and-first-run.md")
    configuration = read_asset("docs/configuration.md")
    usage = read_asset("docs/usage.md")
    assert "Container setup destinations must stay inside `/data`" in quick_start
    assert "Add `--config-file PATH`" in quick_start
    assert "use the explicit `docker compose run` command printed by setup" in quick_start
    assert "fresh configuration from defaults" in configuration
    assert "If setup saved either file under another `/data` path" in usage


# Verifies container Firefox documentation covers persistent auth and host-specific mounts
def test_usage_docs_cover_container_firefox_import():
    usage = read_asset("docs/usage.md")
    compose = read_asset("docker-compose.yml")
    assert '<a id="import-firefox-into-container-authentication"></a>' in usage
    linux_sources = ("$HOME/.mozilla/firefox", "$HOME/snap/firefox/common/.mozilla/firefox", "$HOME/.var/app/org.mozilla.firefox/.mozilla/firefox")
    for source in linux_sources:
        assert f'docker run --rm -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" -v "{source}:/home/spotify/.mozilla/firefox:ro"' in usage
        assert f'docker compose run --rm -v "{source}:/home/spotify/.mozilla/firefox:ro"' in usage
        assert f'docker compose run --rm -v "{source}:/home/spotify/.mozilla/firefox:ro"' in compose
    mac_mount = '${HOME}/Library/Application Support/Firefox:/home/spotify/.mozilla/firefox:ro'
    assert f'docker run --rm -it --init -v "${{PWD}}:/data:z" -v "{mac_mount}"' in usage
    assert f'docker compose run --rm -v "{mac_mount}"' in usage
    assert f'docker compose run --rm -v "{mac_mount}"' in compose
    windows_mounts = (("${PWD}", "$env:APPDATA\\Mozilla\\Firefox", "Windows PowerShell"), ("%cd%", "%APPDATA%\\Mozilla\\Firefox", "Windows Command Prompt"))
    for current_directory, source, label in windows_mounts:
        assert f'docker run --rm -it --init -v "{current_directory}:/data:z" -v "{source}:/home/spotify/.mozilla/firefox:ro"' in usage
        assert f'docker compose run --rm -v "{source}:/home/spotify/.mozilla/firefox:ro"' in usage
        assert f'docker compose run --rm -v "{source}:/home/spotify/.mozilla/firefox:ro"' in compose
        assert f"#### {label}" in usage
    for heading in ("#### Linux with a standard Firefox package", "#### Linux with Firefox from Snap", "#### Linux with Firefox from Flatpak", "#### macOS"):
        assert heading in usage
    assert "Guided setup asks which host environment runs Docker" in usage
    assert "Doctor is deferred until the import succeeds" in usage
    assert "Do not add `:z` or `:Z` to the whole Firefox profile mount" in usage
    assert "You do not need to mount Firefox again" in usage


# Verifies the usage and configuration guides cover portable mounts and safe dotenv copying
def test_docs_describe_portable_mounts_and_safe_dotenv_copy():
    usage = read_asset("docs/usage.md")
    configuration = read_asset("docs/configuration.md")
    assert '-v "$PWD:/data:z"' in usage
    assert "test -e .env || cp .env.example .env" in configuration


# Verifies installation guidance covers every supported delivery and upgrade path
def test_installation_docs_cover_all_delivery_and_upgrade_paths():
    installation = read_asset("docs/installation.md")
    for heading in ("### Install from PyPI", "### Install the Manual Script", "### Install with Docker Compose", "### Install from Docker Hub", "### Upgrade a PyPI Installation", "### Upgrade a Manual Installation", "### Upgrade a Docker Compose Installation", "### Upgrade a Direct Docker Installation", "### Upgrade a Locally Built Docker Image"):
        assert heading in installation
    assert "The published image already contains Python and all core libraries" in installation
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py" in installation
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt" in installation
    assert "pip install --upgrade -r requirements.txt" in installation
    assert "docker build --pull --tag spotify-monitor:local ." in installation
    assert "No separate image download is required" in installation
    assert "docker pull misiektoja/spotify-monitor:latest" in installation
    assert "docker compose pull" in installation


# Verifies container onboarding prioritizes direct Docker and folds pulls into setup
def test_container_onboarding_prioritizes_direct_docker_and_folds_pulls_into_setup():
    installation = read_asset("docs/installation.md")
    quick_start = read_asset("docs/setup-and-first-run.md")
    compose = read_asset("docker-compose.yml")
    assert installation.index("### Install from Docker Hub") < installation.index("### Install with Docker Compose")
    direct_install = installation.split("### Install from Docker Hub", 1)[1].split("### Install with Docker Compose", 1)[0]
    compose_install = installation.split("### Install with Docker Compose", 1)[1].split("### Build the Docker Image Locally", 1)[0]
    assert "docker run --pull=always" in direct_install
    assert "docker pull misiektoja/spotify-monitor:latest" not in direct_install
    assert "\ndocker compose pull\n" not in compose_install
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/docker-compose.yml" in compose_install
    assert "curl -fsSLO" not in quick_start
    assert "If you opened this page first" in quick_start
    assert '=== "Manual Python script on macOS or Linux"' in quick_start
    assert '=== "Manual Python script on Windows"' in quick_start
    assert quick_start.index('=== "Docker image on macOS or Windows"') < quick_start.index('=== "Docker Compose"')
    assert 'docker run --rm --pull=always -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --setup' in quick_start
    assert 'docker run --rm --pull=always -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --setup' in quick_start
    compose_quick_start = quick_start.split('=== "Docker Compose"', 1)[1].split("Run interactive setup commands", 1)[0]
    assert "run these shell commands in the same terminal immediately before setup" in compose_quick_start
    assert 'export SPOTIFY_MONITOR_UID="$(id -u)"' in compose_quick_start
    assert 'export SPOTIFY_MONITOR_GID="$(id -g)"' in compose_quick_start
    assert "docker compose run --rm --pull=always spotify_monitor --setup" in compose_quick_start
    assert "#   docker compose run --rm --pull=always spotify_monitor --setup" in compose
    for relative_path in ("README.md", "docs/index.md"):
        landing_page = read_asset(relative_path)
        quick_install = landing_page.split("Quick Install & Run", 1)[1].split("<a id=\"features\"></a>", 1)[0]
        assert quick_install.index("#### Docker image - fastest container setup") < quick_install.index("#### Docker Compose - shorter recurring commands")
        assert "#### Python from PyPI" in quick_install
        assert "##### macOS or Windows" in quick_install
        assert "##### Linux" in quick_install
        assert "\ndocker pull misiektoja/spotify-monitor:latest" not in quick_install
        assert "\ndocker compose pull" not in quick_install
        assert "docker run --rm --pull=always" in quick_install
        assert "docker compose run --rm --pull=always spotify_monitor --setup" in quick_install
        assert "pip install spotify_monitor\n```\n\nRun setup wizard:\n\n```sh\nspotify_monitor --setup" in quick_install
        assert 'docker run --rm --pull=always -it --init -v "${PWD}:/data:z" misiektoja/spotify-monitor:latest --setup' in quick_install
        assert 'docker run --rm --pull=always -it --init --user "$(id -u):$(id -g)" -v "$PWD:/data:z" misiektoja/spotify-monitor:latest --setup' in quick_install
    readme = read_asset("README.md")
    assert "\n## Quick Start\n" not in readme
    assert '<a id="common-commands"></a>' in readme
    assert readme.index('<a id="features"></a>') < readme.index('<a id="before-monitoring"></a>') < readme.index('<a id="common-commands"></a>') < readme.index('<a id="documentation"></a>')
    assert "| Set up Spotify Monitor for the first time |" not in readme
    assert "https://misiektoja.github.io/spotify_monitor/setup-and-first-run/#run-individual-commands" in readme
    assert "https://misiektoja.github.io/spotify_monitor/setup-and-first-run/" in readme
    common_section = readme.split("## Common Commands", 1)[1].split('<a id="documentation"></a>', 1)[0]
    common_table = common_section.split("| I want to... | Run this |", 1)[1].split("\n\n", 1)[0]
    assert "The table uses PyPI commands." in common_section
    assert "docker compose" not in common_table


# Verifies manual upgrade guidance repeats linked files and direct download commands
def test_manual_upgrade_docs_are_self_contained():
    installation = read_asset("docs/installation.md")
    manual_upgrade = installation.split("### Upgrade a Manual Installation", 1)[1].split("### Upgrade a Docker Compose Installation", 1)[0]
    assert "[spotify_monitor.py](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py)" in manual_upgrade
    assert "[requirements.txt](https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt)" in manual_upgrade
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/spotify_monitor.py" in manual_upgrade
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/requirements.txt" in manual_upgrade
    assert "pip install --upgrade -r requirements.txt" in manual_upgrade


# Verifies every documented PyPI extra clearly includes the base package
def test_installation_docs_explain_optional_extra_contents():
    installation = read_asset("docs/installation.md")
    assert "Each command below that uses square brackets installs the base `spotify_monitor` package" in installation
    assert 'pip install "spotify_monitor[browser]"' in installation
    assert "This installs Spotify Monitor and the optional `pycookiecheat` dependency" in installation
    assert 'pip install "spotify_monitor[legacy-oauth]"' in installation
    assert "This installs Spotify Monitor and the optional Spotipy dependency" in installation


# Verifies landing pages prioritize app-free setup while detailed OAuth guidance stays contextual
def test_landing_pages_do_not_promote_optional_oauth_requirements():
    for relative_path in ("README.md", "docs/index.md"):
        landing_page = read_asset(relative_path)
        assert "Cookie or Desktop Client access with automatic web-player metadata fallback and optional legacy OAuth app support" in landing_page
        assert "Spotify OAuth app note" not in landing_page
    configuration = read_asset("docs/configuration.md")
    assert '<a id="spotify-oauth-app"></a>' in configuration
    assert "official migration guide" in configuration


# Verifies monitoring guidance exposes every target form and install-aware command prefixes
def test_usage_docs_cover_target_forms_and_install_commands():
    usage = read_asset("docs/usage.md")
    for value in ("spotify:user:spotify_user_uri_id", "https://open.spotify.com/user/spotify_user_uri_id?si=tracking_id", "TARGET_USER_URI_ID", "python3 spotify_monitor.py", "docker compose run --rm spotify_monitor", "misiektoja/spotify-monitor:latest"):
        assert value in usage


# Verifies debugging downloads use the same curl convention as installation
def test_debugging_docs_use_curl_downloads():
    debugging = read_asset("docs/debugging.md")
    assert "wget" not in debugging.casefold()
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_totp_test.py" in debugging
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_secret_grabber.py" in debugging


# Verifies secret grabber container usage refreshes mutable images through direct Docker and Compose
def test_secret_grabber_container_pull_contract():
    debugging = read_asset("docs/debugging.md")
    compose = read_asset("debug/spotify_monitor_secret_grabber_docker/compose.yaml")
    assert debugging.count("docker run --rm --pull=always") == 4
    assert "docker compose run --rm spotify-secrets-grabber --all" in debugging
    assert "image: misiektoja/spotify-secrets-grabber:latest" in compose
    assert "pull_policy: always" in compose
    assert "docker.io/misiektoja/spotify-secrets-grabber" not in compose


# Verifies webhook guidance targets the configuration page and its stable anchor
def test_webhook_setup_anchor_is_consistent():
    readme = read_asset("README.md")
    configuration = read_asset("docs/configuration.md")
    assert '<a id="webhook-settings"></a>' in configuration
    assert "https://misiektoja.github.io/spotify_monitor/configuration/#webhook-settings" in readme
    assert "discord-webhook-notifications" not in readme


# Verifies the MkDocs navigation and GitHub Pages deployment contract
def test_documentation_site_contract():
    mkdocs = read_asset("mkdocs.yml")
    workflow = read_asset(".github/workflows/docs.yml")
    assert "site_url: https://misiektoja.github.io/spotify_monitor/" in mkdocs
    for page in ("index.md", "installation.md", "setup-and-first-run.md", "configuration.md", "usage.md", "troubleshooting.md", "debugging.md", "testing.md", "about.md"):
        assert f": {page}" in mkdocs
        assert (PROJECT_ROOT / "docs" / page).is_file()
    assert 'workflows: ["Publish to PyPI"]' in workflow
    assert "mkdocs gh-deploy --force --strict" in workflow
