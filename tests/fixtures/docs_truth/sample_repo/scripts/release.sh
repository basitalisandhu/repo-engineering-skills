#!/bin/sh
case "$1" in
  --dry-run) echo "would tag" ;;
  *) echo "tagging" ;;
esac
