#!/usr/bin/env python3
from __future__ import annotations

import argparse

from podcast_atlas.cli import main as cli_main


def main() -> int:
    ap = argparse.ArgumentParser(description="Build demo sqlite DB from fixture feeds")
    ap.add_argument("--db", default="active.db", help="Output sqlite path")
    args = ap.parse_args()
    return cli_main(["build-sample", "--db", args.db])


if __name__ == "__main__":
    raise SystemExit(main())
