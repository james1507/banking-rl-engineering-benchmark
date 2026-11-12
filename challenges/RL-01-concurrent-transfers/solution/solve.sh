#!/bin/sh
set -eu
git apply "$(dirname "$0")/golden.patch"
