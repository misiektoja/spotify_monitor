# Security policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability.

Report it privately through [GitHub security advisories](https://github.com/misiektoja/spotify_monitor/security/advisories/new), which keeps the report visible only to the maintainer until an advisory is published. If you cannot use that, email <misiektoja-github@rm-rf.ninja>.

Do not include your `sp_dc` cookie, captured Protobuf login files, Spotify refresh tokens, Last.fm API keys, SMTP passwords, webhook URLs, ntfy tokens or the friends you monitor in a report. Include the affected version, the impact, the preconditions to reproduce it and a sanitized proof when you have one.

The maintainer will acknowledge the report and coordinate disclosure once a fix is available.

## Supported versions

Security fixes are made on the default branch and shipped in the next release to [PyPI](https://pypi.org/project/spotify-monitor/), the [GitHub releases](https://github.com/misiektoja/spotify_monitor/releases) and the [Docker image](https://hub.docker.com/r/misiektoja/spotify-monitor). Only the latest released version is supported. Earlier versions receive no backports.

## Security posture

This tool holds credentials for your own Spotify account and records what your friends listen to. Both matter when you deploy it.

- **Configuration files are parsed, not executed.** Only documented `SETTING = value` lines with plain literal values are accepted. Imports, function calls, expressions and control flow are rejected without being run, so a configuration file found in the working directory cannot execute code.
- **Secrets belong in `.env`, not in the configuration file.** `--set-sp-dc`, `--set-webhook-url`, `--set-lastfm-credentials` and the setup wizard write to `.env` and set owner-only permissions on POSIX systems. Generated configuration backups keep the owner-only mode of the file they replace. See [Configuration](https://misiektoja.github.io/spotify_monitor/configuration/).
- **Spotify-supplied text is untrusted input.** Friend, artist, track, album and context names are stripped of terminal control sequences before they reach console or log output, so a crafted name cannot drive the terminal.
- **Local playback never builds a shell command.** Track IDs are validated against ASCII letters and digits before macOS, Linux or Windows playback. Every integration passes an argument list rather than a shell string.
- **The debug utilities send tokens only to Spotify.** `spotify_monitor_totp_test --token-validity-url` accepts HTTPS Spotify API hosts only and follows no redirects, so a copied command cannot forward your bearer token elsewhere.
- **Monitoring an account is subject to the law where you are.** The tool is intended for accounts you own or are authorized to observe.

## Supply chain

Every GitHub Actions workflow pins third-party actions to a commit SHA with the version recorded alongside it. The test suite fails when a pin or its version comment is missing and when a workflow passes an event value straight into a shell. Dependencies, actions and the container base image are tracked by Dependabot. Each change runs secret scanning, a dependency vulnerability audit, an SBOM build and a container image scan. CodeQL analyzes the Python source with the `security-extended` query set while OpenSSF Scorecard scores the repository's security practices. See [.github/workflows/supply-chain.yml](https://github.com/misiektoja/spotify_monitor/blob/main/.github/workflows/supply-chain.yml) and [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/spotify_monitor/blob/main/THIRD_PARTY_NOTICES.md).

Publishing to PyPI and to Docker Hub runs the full test suite first and stops if it fails, so no untested artifact is released under the project's name. Both publishing jobs run in a named GitHub environment and the PyPI upload uses trusted publishing rather than a stored API token.

The default branch and the development branch are protected by rulesets that block deletion and force pushes and require changes to arrive through a pull request.
