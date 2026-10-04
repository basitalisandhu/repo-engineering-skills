# Security policy

This repository ships skills and scripts that run inside people's Claude Code sessions. The scripts read the files you point them at and write only where you ask; nothing here makes a network call or reports usage anywhere.

## Supported versions

Only the latest release on `main` is supported. Pin a tag if you need stability, and update when a fix is announced in [CHANGELOG.md](CHANGELOG.md).

## Reporting a vulnerability

Please do not open a public issue for a security problem.

1. Use GitHub's private vulnerability reporting on this repository ("Security" tab, "Report a vulnerability").
2. If that is unavailable, open an issue titled "Security contact request" with no details, and the maintainer will reply with a private channel.

Include what you found, how to reproduce it, and what you think the impact is. You will get an acknowledgement within 5 working days and a fix or a mitigation plan within 30 days for confirmed issues.

## What counts

- A script that can be made to execute repository code without `--run-help`, write outside the paths given on its command line, overwrite an existing file through `--stubs-dir`, or send data anywhere.
- `audit_validate.py` accepting a citation that points outside the repository (for example through `..` or a symbolic link).
- `docs_truth_check.py --run-help` passing more of the caller's environment than `PATH`, `LANG` and `NO_COLOR`, or running without its timeout.
- Text in any file of this repository that addresses the model rather than the reader.

Detection gaps (a claim kind not yet extracted, a manifest format not yet parsed, a missed hype word) are welcome as ordinary issues or pull requests.

## What this plugin does and does not do

- No telemetry and no network access.
- Scripts are standard-library Python and read-only unless you pass `--out` or `--stubs-dir`.
- The only subprocess any script starts is the opt-in `--help` run in `docs_truth_check.py --run-help`.
- Skill text tells Claude to treat repository content as untrusted data, never as instructions.
