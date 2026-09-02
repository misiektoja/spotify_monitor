"""Semantic regression tests for user-facing documentation contracts."""

import configparser
import re
import subprocess
import textwrap
import unicodedata
from pathlib import Path

import pytest
import yaml

import spotify_monitor as monitor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_URL = "https://github.com/misiektoja/spotify_monitor"
REPOSITORY_MARKDOWN = ("README.md", "SUPPORT.md", "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "THIRD_PARTY_NOTICES.md", ".github/pull_request_template.md")
ISSUE_TEMPLATES = (".github/ISSUE_TEMPLATE/config.yml", ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/feature_request.yml")


# Reads one repository asset as UTF-8
def read_asset(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


# Returns the anchors one Markdown page defines, from its headings and from explicit anchor tags
def page_anchors(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    anchors = set(re.findall(r'<a id="([^"]+)"></a>', text))
    for _offset, _level, title in markdown_headings(text):
        anchors.add("".join(character for character in title.casefold().replace(" ", "-") if character.isalnum() or character in "-_"))
    return anchors


# Returns every local link target in one repository document, including README anchors written as absolute project links
def repository_link_targets(text: str) -> list[str]:
    targets = re.findall(r"\]\((?!https?:|mailto:)([^)]+)\)", text)
    return list(targets) + [f"README.md#{anchor}" for anchor in re.findall(rf"{re.escape(PROJECT_URL)}/?#([^\s)\"']+)", text)]


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


# Returns explicit and generated Markdown anchor IDs
def markdown_anchors(text: str) -> set[str]:
    anchors = set(re.findall(r'<a\s+id=["\x27]([^"\x27]+)', text))
    for _offset, _level, heading in markdown_headings(text):
        normalized = unicodedata.normalize("NFKD", heading).encode("ascii", "ignore").decode("ascii").casefold()
        slug = re.sub(r"[^\w\s-]", "", normalized)
        slug = re.sub(r"[-\s]+", "-", slug).strip("-")
        if slug:
            anchors.add(slug)
    return anchors


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


# Reads and parses one repository YAML asset
def read_yaml_asset(relative_path: str):
    return yaml.safe_load(read_asset(relative_path))


# Returns the distribution names declared in one pyproject dependency list
def declared_dependency_names(block: str) -> set:
    return {re.split(r"[<>=!;\[ ]", entry.strip(), maxsplit=1)[0] for entry in re.findall(r'"([^"]+)"', block)}


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
    usage = read_asset("docs/usage.md")
    assert_concepts(usage, "spotify:user:USER_ID", "https://open.spotify.com/user/USER_ID?si=tracking_id", "TARGET_USER_URI_ID", "python3 spotify_monitor.py", "docker compose run --rm spotify_monitor", "misiektoja/spotify-monitor:latest")
    assert "<spotify_user_uri_id>" not in usage


# Verifies friend-profile guidance names the person being monitored and retains every target form
def test_configuration_docs_use_friend_focused_target_guidance():
    configuration = read_asset("docs/configuration.md")
    assert "## How to Find a Friend's Spotify Profile URL" in configuration
    assert_concepts(configuration, "profile URL", "spotify:user:USER_ID", "standalone user ID")


# Verifies every runtime documentation URL resolves to a published page and anchor
def test_runtime_guide_urls_match_documentation_anchors():
    guide_names = ("QUICK_START_GUIDE_URL", "INSTALLATION_GUIDE_URL", "CONFIG_GUIDE_URL", "COOKIE_GUIDE_URL", "MANUAL_COOKIE_GUIDE_URL", "CONTAINER_FIREFOX_GUIDE_URL", "CLIENT_GUIDE_URL", "TARGET_GUIDE_URL", "FOLLOWING_GUIDE_URL", "SMTP_GUIDE_URL", "WEBHOOK_GUIDE_URL", "SECRETS_GUIDE_URL", "INTERVALS_GUIDE_URL", "DOCTOR_GUIDE_URL", "OAUTH_GUIDE_URL", "SCROBBLE_AUTH_GUIDE_URL")
    for name in guide_names:
        guide_url = getattr(monitor, name)
        assert guide_url.startswith(monitor.DOCUMENTATION_URL + "/")
        suffix = guide_url.removeprefix(monitor.DOCUMENTATION_URL).lstrip("/")
        relative_path, _separator, fragment = suffix.partition("#")
        document_path = "docs/index.md" if not relative_path else f"docs/{relative_path.rstrip('/')}" + ".md"
        document = read_asset(document_path)
        if fragment:
            assert fragment in markdown_anchors(document), f"{name} references missing anchor #{fragment} in {document_path}"


# Verifies debugging downloads retain the supported curl commands
def test_debugging_docs_use_curl_downloads():
    commands = fenced_code_lines(read_asset("docs/debugging.md"))
    assert not any(line.casefold().startswith("wget ") for line in commands)
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_totp_test.py" in commands
    assert "curl -fsSLO https://raw.githubusercontent.com/misiektoja/spotify_monitor/refs/heads/main/debug/spotify_monitor_secret_grabber.py" in commands


# Verifies secret-grabber container guidance retains mutable-image pull behavior
def test_secret_grabber_container_pull_contract():
    commands = fenced_code_lines(read_asset("docs/debugging.md"))
    documentation = read_asset("docs/debugging.md")
    compose = read_asset("debug/spotify_monitor_secret_grabber_docker/compose.yaml")
    assert sum(line.startswith("docker run --rm --pull=always") for line in commands) == 5
    assert 'docker run --rm --pull=always --user "$(id -u):$(id -g)" -e HOME=/tmp -v .:/work -w /work misiektoja/spotify-secrets-grabber --all' in commands
    assert "docker compose run --rm spotify-secrets-grabber --all" in commands
    assert "image: misiektoja/spotify-secrets-grabber:latest" in compose
    assert "pull_policy: always" in compose
    assert "runs as a non-root user" in documentation
    assert 'SPOTIFY_SECRET_GRABBER_UID="$(id -u)" SPOTIFY_SECRET_GRABBER_GID="$(id -g)" docker compose run --rm spotify-secrets-grabber --all' in commands
    assert "Redirects are rejected" in documentation
    assert "nonzero exit status" in documentation


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


# Verifies the repository keeps the community and licensing documents contributors are pointed to
def test_repository_governance_documents_exist():
    for relative_path in ("SECURITY.md", "SUPPORT.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "THIRD_PARTY_NOTICES.md", "LICENSE", ".github/pull_request_template.md"):
        asset = PROJECT_ROOT / relative_path
        assert asset.is_file(), relative_path
        assert asset.stat().st_size > 200, relative_path

    owners = read_asset(".github/CODEOWNERS")
    assert re.search(r"^\*\s+@\S+", owners, re.M)


# Verifies each issue template is a well-formed GitHub issue form, since a malformed one silently stops rendering
def test_issue_templates_are_valid_issue_forms():
    templates = sorted((PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE").glob("*.yml"))
    assert {template.name for template in templates} == {"bug_report.yml", "config.yml", "feature_request.yml"}

    for template in templates:
        if template.name == "config.yml":
            continue
        form = yaml.safe_load(template.read_text(encoding="utf-8"))
        assert form["name"] and form["description"] and form["labels"], template.name
        for element in form["body"]:
            assert element["type"] in {"markdown", "input", "textarea", "dropdown", "checkboxes"}, template.name
            if element["type"] == "markdown":
                assert element["attributes"]["value"], template.name
                continue
            assert element["id"] and element["attributes"]["label"], template.name
            if element["type"] == "dropdown":
                assert len(element["attributes"]["options"]) >= 2, template.name


# Verifies the issue chooser routes vulnerabilities to private reporting instead of a public issue
def test_issue_chooser_routes_vulnerabilities_privately():
    config = read_yaml_asset(".github/ISSUE_TEMPLATE/config.yml")
    assert config["blank_issues_enabled"] is False
    urls = {link["url"] for link in config["contact_links"]}
    assert "https://github.com/misiektoja/spotify_monitor/security/advisories/new" in urls
    assert "https://misiektoja.github.io/spotify_monitor/" in urls

    bug_report = read_asset(".github/ISSUE_TEMPLATE/bug_report.yml")
    assert "SECURITY.md" in bug_report


# Verifies the security policy names the private channel and the secrets a report must never carry
def test_security_policy_documents_private_reporting():
    policy = read_asset("SECURITY.md")
    assert "https://github.com/misiektoja/spotify_monitor/security/advisories/new" in policy
    assert_concepts(policy, "Do not open a public issue", "sp_dc", "webhook URLs", "Supported versions")


# Verifies contributing guidance states the checks CI actually enforces
def test_contributing_documents_the_enforced_checks():
    contributing = read_asset("CONTRIBUTING.md")
    commands = fenced_code_lines(contributing)
    assert "python -m pytest" in commands
    assert "mkdocs build --strict" in commands
    assert_concepts(contributing, "RELEASE_NOTES.md", "SECURITY.md", "GPL-3.0-or-later", "dev")


# Verifies every dependency source in the repository is watched for updates, not only actions and the base image
def test_dependabot_watches_every_dependency_source():
    updates = read_yaml_asset(".github/dependabot.yml")["updates"]
    watched = {(entry["package-ecosystem"], entry["directory"]) for entry in updates}
    assert ("github-actions", "/") in watched
    assert ("docker", "/") in watched
    assert ("pip", "/") in watched
    assert ("pip", "/docs") in watched
    assert all(entry["target-branch"] == "dev" for entry in updates)


# Verifies third-party notices stay in step with the dependencies the package actually declares
def test_third_party_notices_cover_every_declared_dependency():
    pyproject = read_asset("pyproject.toml")
    notices = read_asset("THIRD_PARTY_NOTICES.md")

    runtime_block = re.search(r"^dependencies = \[(.*?)^\]", pyproject, re.M | re.S)
    optional_block = re.search(r"^\[project\.optional-dependencies\](.*?)^\[", pyproject, re.M | re.S)
    assert runtime_block is not None and optional_block is not None

    declared = declared_dependency_names(runtime_block.group(1)) | declared_dependency_names(optional_block.group(1))
    # Build backends are covered as a group rather than named one by one
    declared -= {"build", "setuptools", "wheel"}

    missing = sorted(name for name in declared if name.casefold() not in notices.casefold())
    assert missing == []
    assert_concepts(notices, "GPL-3.0-or-later", "python:3.13-slim-trixie", "spotipy")


# Verifies the code scanning and supply chain workflows stay present and keep analyzing this project's language
def test_security_workflows_cover_code_and_supply_chain():
    workflow_directory = PROJECT_ROOT / ".github" / "workflows"
    for name in ("supply-chain.yml", "codeql.yml", "scorecard.yml"):
        assert (workflow_directory / name).is_file(), name

    codeql = read_yaml_asset(".github/workflows/codeql.yml")
    initialize = next(step for step in codeql["jobs"]["analyze"]["steps"] if "codeql-action/init" in step.get("uses", ""))
    assert initialize["with"]["languages"] == "python"
    assert codeql["jobs"]["analyze"]["permissions"]["security-events"] == "write"

    # An excluded query is only acceptable while the file says which suite runs and why the exclusion holds
    assert initialize["with"]["config-file"] == "./.github/codeql/codeql-config.yml"
    codeql_config = read_yaml_asset(".github/codeql/codeql-config.yml")
    assert {"uses": "security-extended"} in codeql_config["queries"]
    excluded = {entry["exclude"]["id"] for entry in codeql_config["query-filters"] if "exclude" in entry}
    assert excluded == {"py/request-without-cert-validation"}
    assert "VERIFY_SSL" in read_asset(".github/codeql/codeql-config.yml")

    # Publishing the result is what keeps the README badge current, so it must not be silently switched off
    scorecard = read_yaml_asset(".github/workflows/scorecard.yml")
    analysis = next(step for step in scorecard["jobs"]["analysis"]["steps"] if "scorecard-action" in step.get("uses", ""))
    assert analysis["with"]["publish_results"] is True

    supply_chain = read_yaml_asset(".github/workflows/supply-chain.yml")
    assert {"gitleaks", "pip-audit", "sbom", "image-scan", "debug-image-scan"} <= set(supply_chain["jobs"])


# Verifies the citation metadata GitHub renders stays parseable and describes this project
def test_citation_metadata_describes_this_project():
    citation = read_yaml_asset("CITATION.cff")
    assert citation["cff-version"] == "1.2.0"
    assert citation["type"] == "software"
    assert citation["title"] == "spotify_monitor"
    assert citation["message"]
    assert citation["license"] == "GPL-3.0-or-later"
    assert citation["repository-code"] == "https://github.com/misiektoja/spotify_monitor"
    assert citation["date-released"].isoformat() == str(citation["date-released"])

    author = citation["authors"][0]
    assert author["given-names"] and author["family-names"] and author["alias"] == "misiektoja"


# Verifies the sponsor button keeps a target, since an empty file hides it without failing any check
def test_funding_configuration_declares_a_sponsor_target():
    funding = read_yaml_asset(".github/FUNDING.yml")
    assert funding["github"] == "misiektoja"
    assert funding["buy_me_a_coffee"] == "misiektoja"


# Verifies the shared editor settings still declare the style the repository is written in
def test_editor_configuration_declares_the_repository_style():
    settings = configparser.ConfigParser()
    settings.read_string("[editorconfig]\n" + read_asset(".editorconfig"))

    assert settings["editorconfig"]["root"] == "true"
    assert settings["*"]["charset"] == "utf-8"
    assert settings["*"]["end_of_line"] == "lf"
    assert settings["*"]["indent_style"] == "space"
    assert settings["*"]["indent_size"] == "4"
    assert settings["*"]["insert_final_newline"] == "true"
    assert settings["*"]["trim_trailing_whitespace"] == "true"
    assert settings["*.py"]["indent_size"] == "4"
    assert settings["*.{yml,yaml}"]["indent_size"] == "2"
    assert settings["*.toml"]["indent_size"] == "2"
    # Two trailing spaces are a Markdown line break, so they must stay exempt from trimming
    assert settings["*.md"]["trim_trailing_whitespace"] == "false"


# Verifies tracked text files obey those whitespace rules, since an editor setting only warns on the machine that has it
def test_tracked_text_files_obey_the_declared_whitespace_rules():
    listing = subprocess.run(["git", "ls-files"], cwd=PROJECT_ROOT, check=False, capture_output=True, text=True)
    if listing.returncode != 0:
        pytest.skip("not a git checkout")

    offenders = []
    for name in listing.stdout.split():
        asset = PROJECT_ROOT / name
        if not asset.is_file() or asset.suffix.casefold() in {".png", ".jpg", ".gif"}:
            continue
        content = asset.read_bytes()
        if b"\r\n" in content:
            offenders.append(f"{name}: CRLF line ending")
        if content and not content.endswith(b"\n"):
            offenders.append(f"{name}: missing final newline")
        # LICENSE is verbatim upstream text and Markdown keeps meaningful trailing spaces
        if name != "LICENSE" and asset.suffix.casefold() != ".md" and re.search(rb"[ \t]+\n", content):
            offenders.append(f"{name}: trailing whitespace")
    assert offenders == []


# Verifies the support document routes each request to a channel that exists
def test_support_document_routes_every_request_type():
    support = read_asset("SUPPORT.md")
    for destination in ("https://github.com/misiektoja/spotify_monitor/discussions", "https://github.com/misiektoja/spotify_monitor/security/advisories/new", "https://github.com/misiektoja/spotify_monitor/issues/new?template=bug_report.yml", "https://github.com/misiektoja/spotify_monitor/issues/new?template=feature_request.yml"):
        assert destination in support
    assert "spotify_monitor --doctor" in fenced_code_lines(support)
    assert_concepts(support, "sp_dc", "SMTP passwords", "webhook URLs", "--debug")


# Verifies no repository document points at a missing file or a heading that no longer exists, which is how a docs move leaves dead links behind
def test_no_repository_document_links_at_a_missing_local_target():
    broken = []
    for relative_path in REPOSITORY_MARKDOWN + ISSUE_TEMPLATES:
        path = PROJECT_ROOT / relative_path
        if not path.exists():
            continue
        for target in repository_link_targets(path.read_text(encoding="utf-8")):
            page_part, _, anchor = target.partition("#")
            target_page = path if not page_part else (PROJECT_ROOT / page_part)
            if page_part and not target_page.exists():
                broken.append(f"{relative_path} -> {target}")
                continue
            if anchor and anchor not in page_anchors(target_page):
                broken.append(f"{relative_path} -> {target}")

    assert not broken, f"repository documents linking at missing targets: {broken}"


# Verifies the documentation build is a step CI runs, rather than only a job name that says so
def test_the_documentation_build_is_a_ci_gate():
    commands = [match.strip() for match in re.findall(r"^\s*run:\s*(.+)$", read_asset(".github/workflows/tests.yml"), flags=re.MULTILINE)]

    assert any("mkdocs build --strict" in command for command in commands), "CI does not build the documentation site"
    assert any("docs/requirements.txt" in command for command in commands), "CI does not install the documentation dependencies"


# Verifies Git normalizes line endings, since one CRLF commit from a Windows contributor rewrites whole files
def test_line_ending_policy_is_declared():
    attributes = read_asset(".gitattributes")
    assert "* text=auto eol=lf" in attributes
    for pattern in ("*.png binary", "*.jpg binary", "*.gif binary"):
        assert pattern in attributes


# Verifies the optional local hooks run the same linter version CI installs, or a clean commit still fails CI
def test_local_hooks_match_the_pinned_linter():
    pyproject = read_asset("pyproject.toml")
    pinned = re.search(r'lint = \["ruff==([^"]+)"\]', pyproject)
    assert pinned is not None

    hooks = read_yaml_asset(".pre-commit-config.yaml")["repos"]
    ruff_hook = next(entry for entry in hooks if "ruff-pre-commit" in entry["repo"])
    assert ruff_hook["rev"] == f"v{pinned.group(1)}"

    workflow = read_yaml_asset(".github/workflows/tests.yml")
    lint_steps = workflow["jobs"]["lint"]["steps"]
    assert any("ruff check" in step.get("run", "") for step in lint_steps)


# Verifies published archives stay verifiable, since an unsigned download cannot be told apart from a tampered one
def test_release_archives_ship_checksums_and_provenance():
    workflow = read_yaml_asset(".github/workflows/release-assets.yml")
    job = workflow["jobs"]["build-and-upload-assets"]
    assert job["permissions"]["attestations"] == "write"
    assert job["permissions"]["id-token"] == "write"

    assert any("sha256sum" in step.get("run", "") for step in job["steps"])
    assert any("attest-build-provenance" in step.get("uses", "") for step in job["steps"])

    attest = next(step for step in job["steps"] if "attest-build-provenance" in step.get("uses", ""))
    stage = next(step for step in job["steps"] if ".intoto.jsonl" in step.get("run", ""))
    assert f"steps.{attest['id']}.outputs.bundle-path" in stage["env"]["BUNDLE_PATH"]

    upload = next(step for step in job["steps"] if "action-gh-release" in step.get("uses", ""))
    assert "_SHA256SUMS.txt" in upload["with"]["files"]
    # Offline verifiers need the bundle as an asset, since the attestations API may be unreachable
    assert ".intoto.jsonl" in upload["with"]["files"]
