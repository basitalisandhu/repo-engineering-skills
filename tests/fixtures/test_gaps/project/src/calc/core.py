def add(a, b):
    return a + b


def parse_config(text):
    """Planted gap: used by the CLI, never mentioned by a test."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def _private_helper():
    return None
