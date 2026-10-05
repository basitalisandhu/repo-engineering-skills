# syntax=docker/dockerfile:1
#
# The repo-engineering skill scripts as one command-line image. Build and run with:
#   docker build -t repo-engineering-skills .
#   docker run --rm -v "$PWD:/work" repo-engineering-skills --help
#
# Standard library only: no pip install. The base image is pinned by digest (python:3.12-slim, multi-arch index).
ARG PYTHON_IMAGE=python:3.12-slim@sha256:dddfd7e07f9d15aeeca61529320492139d21cac7f0070c00609243e51e4e0016

# Assemble the tree in a throwaway stage: only the dispatcher and the skill scripts, byte-compiled, and smoke-tested.
FROM ${PYTHON_IMAGE} AS build
WORKDIR /app
COPY LICENSE README.md pyproject.toml ./
COPY scripts/cli.py scripts/cli.py
COPY plugins/repo-engineering/skills/ /tmp/skills/
RUN set -e; for d in /tmp/skills/*/scripts; do \
      skill=$(basename "$(dirname "$d")"); \
      mkdir -p "plugins/repo-engineering/skills/$skill/scripts"; \
      cp "$d"/*.py "plugins/repo-engineering/skills/$skill/scripts/"; \
    done \
 && chmod 0755 scripts/cli.py plugins/repo-engineering/skills/*/scripts/*.py \
 && python -m compileall -q scripts plugins \
 && python scripts/cli.py --help > /dev/null

FROM ${PYTHON_IMAGE}
ARG VERSION=0.0.0-dev
LABEL org.opencontainers.image.title="repo-engineering-skills" \
      org.opencontainers.image.description="Repository engineering skill scripts (docs truth check, cited audits, agent context lint, README check, test gaps, onboarding facts, restructure plans, ADR mining, hygiene, release notes, stale branches, plan checks) behind one command" \
      org.opencontainers.image.source="https://github.com/basitalisandhu/repo-engineering-skills" \
      org.opencontainers.image.url="https://github.com/basitalisandhu/repo-engineering-skills" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${VERSION}"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=build /app/ /app/
# git is needed by the adr and release-notes subcommands (read-only log, show, ls-tree, blame). The mounted
# repository belongs to another uid, so /work is marked as a safe directory for git.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/* \
 && git config --system --add safe.directory /work \
 && git config --system --add safe.directory '/work/*' \
 && ln -s /app/scripts/cli.py /usr/local/bin/repo-engineering \
 && useradd --uid 1000 --user-group --no-create-home --shell /usr/sbin/nologin app
# Mount the files to read (and the folder for any output) at /work.
WORKDIR /work
USER 1000:1000
ENTRYPOINT ["repo-engineering"]
CMD ["--help"]
