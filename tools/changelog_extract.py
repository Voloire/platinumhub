#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract one version's section from CHANGELOG.md, for the release notes.

    python tools/changelog_extract.py 3.3.0            > RELEASE_NOTES.md
    python tools/changelog_extract.py v3.3.0 --file CHANGELOG.md

Accepted heading shapes (level 2, "Keep a Changelog" style):

    ## [3.3.0] - 2026-08-20
    ## 3.3.0 - 2026-08-20
    ## v3.3.0

Exits with status 1 and an explicit message when the section is missing, so
that release.yml stops *before* spending five minutes on PyInstaller.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEADING = re.compile(r"^##\s+")


def _version_of(heading: str) -> str | None:
    """Return the bare version in a level-2 heading, or None."""
    text = HEADING.sub("", heading).strip()
    match = re.match(r"^\[?v?(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?)\]?", text)
    return match.group(1) if match else None


def extract(body: str, version: str) -> str:
    version = version.lstrip("vV")
    lines = body.splitlines()
    start = None
    for i, line in enumerate(lines):
        if HEADING.match(line) and _version_of(line) == version:
            start = i + 1
            break
    if start is None:
        found = [v for v in (_version_of(x) for x in lines if HEADING.match(x)) if v]
        raise SystemExit(
            "CHANGELOG.md non contiene una sezione per la versione %s.\n"
            "Versioni trovate: %s\n"
            "Aggiungi '## [%s] - AAAA-MM-GG' prima di creare il tag."
            % (version, ", ".join(found) or "(nessuna)", version)
        )
    end = len(lines)
    for j in range(start, len(lines)):
        if HEADING.match(lines[j]):
            end = j
            break
    section = "\n".join(lines[start:end]).strip("\n")
    if not section.strip():
        raise SystemExit(
            "La sezione %s di CHANGELOG.md e' vuota: scrivi cosa cambia prima di rilasciare."
            % version
        )
    return section


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Estrae una sezione da CHANGELOG.md")
    parser.add_argument("version", help="versione da estrarre, con o senza la v iniziale")
    parser.add_argument(
        "--file",
        default=os.path.join(REPO_ROOT, "CHANGELOG.md"),
        help="percorso del changelog (default: CHANGELOG.md nella radice)",
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.file):
        raise SystemExit("File non trovato: %s" % args.file)
    with open(args.file, encoding="utf-8") as fh:
        body = fh.read()

    sys.stdout.write(extract(body, args.version) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
