"""Command line entry point."""
import os
import sys


def main(argv=None):
    db = os.environ.get("DATABASE_URL", "postgresql://localhost/inventory")
    level = os.getenv("INVENTORY_LOG_LEVEL", "info")
    print(db, level)
    return 0


if __name__ == "__main__":
    sys.exit(main())
