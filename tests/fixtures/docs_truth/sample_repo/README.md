# greeter

greeter prints a greeting. Install it with `pip install greeter==1.1.0`.

## Usage

```bash
python3 src/greeter/cli.py --name Ada --shout
python3 src/greeter/cli.py --name Ada --color red
greeter --times 2
make test
./scripts/release.sh --dry-run
```

Options:

- `--times` repeats the greeting; it defaults to `1`.
- `--retries` sets how many attempts to make; it defaults to `3`.
- `--name` defaults to `world`.

Set `GREETER_LANG` to change the language.
`GREETER_LANG` defaults to `es`.

Name helpers live in `src/greeter/helpers.py`; call `format_name()` to tidy a name.

The greeting is built by `build_greeting()` in `src/greeter/cli.py`, which calls `normalise_name()`.

See the [usage guide](docs/usage.md) and the [old guide](docs/guide.md).

This README describes greeter version 1.2.0.
