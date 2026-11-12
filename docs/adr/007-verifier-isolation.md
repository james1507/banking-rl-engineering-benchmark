# ADR-007: Separate containers and authoritative verifier
Context: Candidate code must not own evaluation results or hidden fixtures.

Decision: Freeze source into read-only candidate mount; strip reference code from image; isolated internal network and per-run PG. Verifier has separate read-only code mount and private owner credentials. Candidate runtime has app role only.

Consequences: Public GitHub solutions remain public on internet; runtime isolation is demonstrable, not unseen benchmark secrecy. Candidate migrations run before fixtures with owner rights in disposable cluster.

Rejected alternatives: Same-process import of candidate into grader, writable grader mounts, Docker socket in candidate.

Evidence: benchmark/cli.py sandbox flags, source archive allowlist, independent benchmark/verifier.py.
