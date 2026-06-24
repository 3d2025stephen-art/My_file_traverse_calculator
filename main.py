"""
main.py
-------
CLI entry-point for My_file_traverse_calculator.

Usage examples
--------------
  # Traverse a directory given on the command line and copy summary to clipboard
  python main.py traverse C:\\Users\\Me\\Documents

  # Read a path from the clipboard, traverse it, print + copy summary
  python main.py traverse --from-clipboard

  # Show the session history
  python main.py session --name work --history

  # Pin the clipboard content under a label
  python main.py session --name work --pin mydir

  # Load a pinned value back to clipboard
  python main.py session --name work --load mydir
"""

from __future__ import annotations

import argparse
import sys

from clipboard_pipeline import ClipboardPipeline, _read_clipboard, _write_clipboard
from session_manager import SessionManager


# ------------------------------------------------------------------ #
# Sub-command: traverse                                                #
# ------------------------------------------------------------------ #


def cmd_traverse(args: argparse.Namespace) -> int:
    pipe = ClipboardPipeline(session=args.session)

    if args.from_clipboard:
        pipe.read_clipboard()
        if not pipe.value:
            print("Clipboard is empty — nothing to traverse.", file=sys.stderr)
            return 1
        print(f"Read from clipboard: {pipe.value!r}")
    else:
        if not args.path:
            print("Provide a PATH or use --from-clipboard.", file=sys.stderr)
            return 1
        pipe.set(args.path)

    try:
        pipe.traverse(
            max_depth=args.max_depth,
            include_hidden=args.hidden,
            extensions=args.ext or None,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.files:
        pipe.file_list()
    else:
        pipe.summarise()

    pipe.print()

    if not args.no_clipboard:
        pipe.write_clipboard()
        print("\n[Copied to clipboard]")

    if args.save:
        pipe.save_to_session(label=args.save if args.save != "_auto_" else None)
        print(f"[Saved to session '{args.session}']")

    return 0


# ------------------------------------------------------------------ #
# Sub-command: session                                                 #
# ------------------------------------------------------------------ #


def cmd_session(args: argparse.Namespace) -> int:
    mgr = SessionManager()

    if args.list:
        sessions = mgr.list_sessions()
        if sessions:
            print("Sessions:")
            for s in sessions:
                print(f"  {s}")
        else:
            print("No sessions found.")
        return 0

    name = args.name or "default"

    if args.history:
        entries = mgr.history(name, n=args.n)
        if not entries:
            print(f"No history in session '{name}'.")
        else:
            for i, e in enumerate(entries, 1):
                print(f"[{i}] {e['timestamp']}")
                print(f"    {e['content'][:120]!r}")
        return 0

    if args.pin:
        text = _read_clipboard().strip()
        if not text:
            print("Clipboard is empty — nothing to pin.", file=sys.stderr)
            return 1
        mgr.pin(name, args.pin, text)
        print(f"Pinned under '{args.pin}' in session '{name}'.")
        return 0

    if args.load:
        content = mgr.get_pinned(name, args.load)
        if content is None:
            print(
                f"No pinned entry '{args.load}' in session '{name}'.",
                file=sys.stderr,
            )
            return 1
        _write_clipboard(content)
        print(f"Loaded '{args.load}' → clipboard")
        print(content[:200])
        return 0

    if args.clear:
        mgr.clear_history(name)
        print(f"History cleared for session '{name}'.")
        return 0

    if args.delete:
        if mgr.delete_session(name):
            print(f"Session '{name}' deleted.")
        else:
            print(f"Session '{name}' not found.")
        return 0

    if args.summary:
        print(mgr.summary(name))
        return 0

    # Default: print summary
    print(mgr.summary(name))
    return 0


# ------------------------------------------------------------------ #
# Argument parser                                                      #
# ------------------------------------------------------------------ #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="my_file_calc",
        description="My_file_traverse_calculator — clipboard pipeline for Windows",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- traverse ----
    t = sub.add_parser("traverse", help="Traverse a directory and calculate sizes")
    t.add_argument("path", nargs="?", default="", help="Directory to traverse")
    t.add_argument(
        "--from-clipboard", action="store_true",
        help="Read the directory path from the clipboard",
    )
    t.add_argument(
        "--max-depth", type=int, default=None, metavar="N",
        help="Maximum recursion depth",
    )
    t.add_argument(
        "--hidden", action="store_true",
        help="Include hidden files and directories",
    )
    t.add_argument(
        "--ext", nargs="+", metavar="EXT",
        help="Only count files with these extensions (e.g. .py .txt)",
    )
    t.add_argument(
        "--files", action="store_true",
        help="Output a list of file paths instead of a summary",
    )
    t.add_argument(
        "--no-clipboard", action="store_true",
        help="Do NOT copy the result to the clipboard",
    )
    t.add_argument(
        "--save", nargs="?", const="_auto_", default=None, metavar="LABEL",
        help="Save the result to the current session (optionally pinned under LABEL)",
    )
    t.add_argument(
        "--session", default="default", metavar="NAME",
        help="Session name for history/pinning (default: 'default')",
    )

    # ---- session ----
    s = sub.add_parser("session", help="Manage clipboard sessions")
    s.add_argument("--name", default="default", metavar="NAME", help="Session name")
    s.add_argument("--list", action="store_true", help="List all sessions")
    s.add_argument("--history", action="store_true", help="Show session history")
    s.add_argument("-n", type=int, default=10, help="Number of history entries to show")
    s.add_argument("--pin", metavar="LABEL", help="Pin clipboard content under LABEL")
    s.add_argument("--load", metavar="LABEL", help="Load pinned LABEL to clipboard")
    s.add_argument("--clear", action="store_true", help="Clear session history")
    s.add_argument("--delete", action="store_true", help="Delete the session entirely")
    s.add_argument("--summary", action="store_true", help="Show session summary")

    return parser


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "traverse": cmd_traverse,
        "session": cmd_session,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
