"""Run the local API or update instrument-specific macro research."""

import argparse
import sys
import uvicorn

from backend.config import log_level, server_host, server_port


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "refresh-macro":
        parser = argparse.ArgumentParser(prog="python -m backend refresh-macro")
        parser.add_argument("--instrument", choices=("WIN", "WDO"), required=True)
        parsed = parser.parse_args(args[1:])
        from backend.macro_refresh import run_refresh_macro
        return run_refresh_macro(parsed.instrument)
    if args:
        raise SystemExit(f"Unknown command: {args[0]}")
    uvicorn.run("backend.main:app", host=server_host(), port=server_port(), log_level=log_level())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
