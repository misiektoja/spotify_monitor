# Contributing

spotify_monitor is a real-time tracker for Spotify friend activity and Spotify-to-Last.fm scrobble health. Bug reports, documentation fixes and code contributions are welcome.

## Before contributing

Open an issue or a [discussion](https://github.com/misiektoja/spotify_monitor/discussions) before starting substantial work, so an approach is agreed before you write it. [SUPPORT.md](SUPPORT.md) lists where usage questions and bug reports belong. Suspected vulnerabilities go through [SECURITY.md](SECURITY.md), never a public issue.

Contribute only code you have the right to license under GPL-3.0-or-later.

Never commit `sp_dc` cookies, captured Protobuf login files, Spotify refresh tokens, Last.fm API keys, SMTP passwords, webhook URLs, ntfy tokens, generated configuration files or log files. Keep scratch files and local test state out of commits. Secret scanning and gitleaks run on every change, but they are a backstop, not the first line of defense.

## Development setup

```sh
git clone https://github.com/misiektoja/spotify_monitor.git
cd spotify_monitor
pip install -e '.[test]'
```

The test extra already includes Pillow, which ntfy artwork tests need. Add the remaining optional extras when you touch browser cookie import or the legacy OAuth backend:

```sh
pip install -e '.[test,browser,legacy-oauth]'
```

## Development checks

Run these before submitting a change:

```sh
python -m ruff check spotify_monitor.py debug tests
python -m pytest
mkdocs build --strict
```

The linter comes from a pinned extra so a new ruff release cannot fail your build on a rule that did not exist yet:

```sh
pip install -e '.[lint]'
```

It selects defect rules only (pyflakes and bugbear). Formatting and import order are deliberately not enforced, so keep following the surrounding code.

The default suite is offline. It never contacts Spotify or Last.fm and network functions are replaced with local test doubles. See [tests/README.md](tests/README.md) for what each test file covers and [Testing](https://misiektoja.github.io/spotify_monitor/testing/) for the CI jobs and supply chain checks.

CodeQL runs the extended security queries. For a verified false positive, put a `codeql[rule-id]` comment immediately above the reported line and explain why it is safe. The workflow filters results with accepted source suppressions before upload. Other findings remain reportable.

CI additionally runs the suite on Python 3.9 through 3.14, a Windows setup-wizard smoke test and container checks that build the image and exercise Docker Compose. The supported Python floor is 3.9, so avoid syntax and standard-library features added after it.

A change to token handling, the monitoring loop or metadata backends is not verified by the offline suite alone. Exercise it against a real Spotify account and say so in the pull request, without usernames or credentials.

## What a change needs

- **Tests.** New behavior needs a test. A bug fix needs a test that fails without it. Match the existing files in `tests/`.
- **Documentation.** User-facing behavior belongs under `docs/`. The documentation build is strict and the suite asserts documentation contracts, so a new setting or option that is missing from the docs will fail CI.
- **A release-notes entry.** Add it under the unreleased section of [RELEASE_NOTES.md](RELEASE_NOTES.md), following the existing category and `**BUGFIX:**`, `**IMPROVE:**` or `**NEW:**` prefixes. Write it for a user, not as an implementation log.
- **A Conventional Commits message.** Use the scope the repository already uses for that area, for example `fix(runtime):`, `test(webhook):` or `docs(usage):`.

Pull requests target `dev`. The pull request template lists the checks to report.

## Code style

The codebase favors complete implementations over minimal patches, explicit validation of anything Spotify or Last.fm supplies and one concise summary comment directly above each shared function. Follow the surrounding code rather than introducing a new style.

Optional local hooks run the same linter, the whitespace rules and a private-key check before a commit is written. The lint hook calls the Ruff installed by `.[lint]` above rather than a copy of its own, so it always matches the version CI runs:

```sh
pip install pre-commit
pre-commit install
```

[.editorconfig](.editorconfig) records the whitespace rules the repository already follows: UTF-8, LF line endings, a final newline, no trailing whitespace, four-space indentation for Python and two spaces for YAML and TOML. Most editors apply it automatically, a few need a plugin. The test suite checks tracked files against the same rules, so a change made in an editor that ignores them will fail CI.
