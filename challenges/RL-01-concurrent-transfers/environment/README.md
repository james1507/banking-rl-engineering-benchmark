# Environment
`python3 -m benchmark.cli materialize --task RL-01 --output /tmp/RL-01-workspace`
Creates public source, public unit tests, migrations, instruction and test adapter only.
Runtime image: infra/sandbox.Dockerfile; dependencies locked in uv.lock. Runtime has no reference source, verifier, solutions or Docker socket. Candidate migrations run only in disposable database before verifier fixtures.
