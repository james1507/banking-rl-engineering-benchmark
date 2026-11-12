#!/bin/sh
set -eu
python3 -m benchmark.cli run --task RL-03 --mode "${MODE:-golden}"
