#!/bin/sh
set -eu
python3 -m benchmark.cli run --task RL-01 --mode "${MODE:-golden}"
