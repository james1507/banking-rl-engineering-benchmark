#!/bin/sh
set -eu
python3 -m benchmark.cli run --task RL-02 --mode "${MODE:-golden}"
