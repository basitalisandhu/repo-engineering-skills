# csvtidy

csvtidy is a command-line tool that rewrites messy CSV files into one consistent dialect.

It is for data engineers who receive CSV exports from many systems, and it replaces the ad hoc sed scripts
that break whenever a quoted field contains a comma.

## Install

```bash
pipx install csvtidy
```

## Quickstart

```bash
csvtidy input.csv --out clean.csv
```

Questions and bug reports: open an issue at https://github.com/example/csvtidy/issues.

## Options

See `csvtidy --help`.
