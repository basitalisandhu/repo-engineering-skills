"""Tiny CLI. The README next to this package documents it, with some claims planted to be wrong."""
import argparse
import os

from greeter.utils import normalise_name


def build_greeting(name: str, shout: bool = False) -> str:
    lang = os.environ.get("GREETER_LANG", "en")
    text = ("Hola, " if lang == "es" else "Hello, ") + normalise_name(name)
    return text.upper() if shout else text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="greeter")
    ap.add_argument("--name", default="world")
    ap.add_argument("--shout", action="store_true")
    ap.add_argument("--times", type=int, default=1)
    ap.add_argument("--retries", type=int, default=5)
    args = ap.parse_args(argv)
    for _ in range(args.times):
        print(build_greeting(args.name, args.shout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
