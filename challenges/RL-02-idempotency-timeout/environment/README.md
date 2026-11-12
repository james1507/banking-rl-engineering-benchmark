# Environment
`python3 -m benchmark.cli materialize --task RL-02 --output /tmp/RL-02-workspace`
Creates public source, public unit tests, migrations, instruction and test adapter only.
Runtime image: infra/sandbox.Dockerfile; dependencies locked in uv.lock. Runtime has no reference source, verifier, solutions or Docker socket. Candidate migrations run only in disposable database before verifier fixtures.
