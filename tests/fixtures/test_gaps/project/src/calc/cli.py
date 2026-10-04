import sys

from calc.core import add, parse_config


def main(argv=None):
    cfg = parse_config("a = 1\nb = 2")
    print(add(int(cfg["a"]), int(cfg["b"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
