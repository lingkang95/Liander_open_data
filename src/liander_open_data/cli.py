"""Command line interface: ``liander-open-data <command> ...``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .database import VALUE_COLUMNS, ProfileDatabase, ProfileNotFoundError, build_database
from .dictionary import load_dictionary, write_dictionary_csv

DEFAULT_DB = "liander_profiles.db"


def _progress(done: int, total: int, code: str) -> None:
    width = 30
    filled = int(width * done / total)
    bar = "#" * filled + "-" * (width - filled)
    end = "\n" if done == total else ""
    print(f"\r[{bar}] {done}/{total} {code:<6}", end=end, file=sys.stderr, flush=True)


def _cmd_build(args: argparse.Namespace) -> int:
    path = build_database(
        args.profiles_dir,
        args.output,
        dictionary=args.dictionary,
        overwrite=args.overwrite,
        progress=None if args.quiet else _progress,
    )
    size_mb = path.stat().st_size / 1e6
    print(f"Database written to {path} ({size_mb:.0f} MB)")
    return 0


def _cmd_info(args: argparse.Namespace) -> int:
    with ProfileDatabase(args.db) as db:
        for key, value in db.metadata.items():
            print(f"{key:>16}: {value}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    with ProfileDatabase(args.db) as db:
        df = db.list_profiles()
    print(df[["description", "n_timeseries"]].to_string(max_colwidth=70))
    return 0


def _cmd_lookup(args: argparse.Namespace) -> int:
    with ProfileDatabase(args.db) as db:
        entry = db.lookup(args.code, fallback_to_parent=True)
    for key, value in entry.to_dict().items():
        print(f"{key:>22}: {value}")
    print(f"{'recommended_profile':>22}: {entry.recommended_profile}")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    with ProfileDatabase(args.db) as db:
        df = db.dictionary(args.text, only_with_profile=args.with_profile)
    cols = ["description", "has_profile", "best_profile", "ko_profile"]
    print(df[cols].to_string(max_colwidth=60) if len(df) else "No matches.")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    with ProfileDatabase(args.db) as db:
        if args.recommended:
            df = db.recommended_profile(args.code, args.columns, start=args.start, end=args.end)
        else:
            df = db.get_profile(args.code, args.columns, start=args.start, end=args.end)
    out = Path(args.output)
    if out.suffix.lower() == ".parquet":
        df.to_parquet(out)
    else:
        df.to_csv(out)
    print(f"Wrote {len(df)} rows to {out}")
    return 0


def _cmd_dictionary(args: argparse.Namespace) -> int:
    records = load_dictionary(args.source)
    write_dictionary_csv(records, args.output)
    print(f"Wrote {len(records)} SBI codes to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser (exposed for documentation generation)."""
    parser = argparse.ArgumentParser(
        prog="liander-open-data",
        description="Build and query a SQLite database of Liander SBI load profiles.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logging")
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    def add_db(p: argparse.ArgumentParser) -> None:
        p.add_argument("--db", default=DEFAULT_DB, help=f"database file (default: {DEFAULT_DB})")

    p = sub.add_parser("build", help="build the database from the profile CSV files")
    p.add_argument("profiles_dir", help="directory with <SBI code>.csv files")
    p.add_argument(
        "-o", "--output", default=DEFAULT_DB, help=f"output file (default: {DEFAULT_DB})"
    )
    p.add_argument(
        "-d",
        "--dictionary",
        help="SBI dictionary (.xlsx or .csv); defaults to the bundled copy",
    )
    p.add_argument("--overwrite", action="store_true", help="replace an existing database")
    p.add_argument("-q", "--quiet", action="store_true", help="hide the progress bar")
    p.set_defaults(func=_cmd_build)

    p = sub.add_parser("info", help="show build metadata of a database")
    add_db(p)
    p.set_defaults(func=_cmd_info)

    p = sub.add_parser("list", help="list all stored profiles")
    add_db(p)
    p.set_defaults(func=_cmd_list)

    p = sub.add_parser("lookup", help="show the dictionary entry of an SBI code")
    p.add_argument("code")
    add_db(p)
    p.set_defaults(func=_cmd_lookup)

    p = sub.add_parser("search", help="search SBI codes by description or code prefix")
    p.add_argument("text")
    p.add_argument("--with-profile", action="store_true", help="only codes with a profile")
    add_db(p)
    p.set_defaults(func=_cmd_search)

    p = sub.add_parser("export", help="export one profile to CSV or Parquet")
    p.add_argument("code")
    p.add_argument("-o", "--output", required=True, help="output .csv or .parquet file")
    p.add_argument(
        "-c", "--columns", nargs="+", choices=VALUE_COLUMNS, help="columns (default: all)"
    )
    p.add_argument("--start", help="inclusive start timestamp, e.g. 2023-06-01")
    p.add_argument("--end", help="exclusive end timestamp")
    p.add_argument(
        "--recommended",
        action="store_true",
        help="export the profile recommended for CODE instead of CODE itself",
    )
    add_db(p)
    p.set_defaults(func=_cmd_export)

    p = sub.add_parser("dictionary", help="convert the SBI dictionary workbook to CSV")
    p.add_argument("source", nargs="?", help=".xlsx workbook (default: bundled copy)")
    p.add_argument("-o", "--output", required=True, help="output CSV file")
    p.set_defaults(func=_cmd_dictionary)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point of the ``liander-open-data`` command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    try:
        return args.func(args)
    except (FileNotFoundError, FileExistsError, ProfileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
