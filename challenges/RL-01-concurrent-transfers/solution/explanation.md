Use canonical UUID row locking and re-read under lock. The baseline reads stale snapshots; DB projection guards may reject its second commit but that is not a correct insufficient-funds outcome. Optimistic version-checked updates with whole-transaction retry are also accepted.

`lock-only.patch` restores only `FOR UPDATE`, retaining the public unsafe-read callback. The scheduling driver releases that checkpoint when the peer is lock-blocked. This guards verifier fairness for correct solutions that preserve instrumentation.
