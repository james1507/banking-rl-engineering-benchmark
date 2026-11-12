"""Trusted outcome verifier. Runs in separate container; never imports candidate modules."""

import concurrent.futures
import json
import os
import random
import time
import traceback
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import jwt
import psycopg
from argon2 import PasswordHasher
from psycopg.rows import dict_row

TASK = os.environ["TASK_ID"]
SEED = int(os.environ["RUN_SEED"])
RNG = random.Random(SEED)
DB = os.environ["VERIFIER_DATABASE_URL"]
SECRET = os.environ["JWT_SECRET"]
BASES = ["http://candidate-a:8000", "http://candidate-b:8000"]
PASSWORD_HASH = PasswordHasher().hash("verifier-strong-password")
RESULTS = []
EVIDENCE = []


def ident():
    return UUID(int=RNG.getrandbits(128), version=4)


def connect():
    return psycopg.connect(
        DB, row_factory=dict_row, connect_timeout=3, options="-c statement_timeout=10000"
    )


def scalar(sql, args=()):
    with connect() as c:
        row = c.execute(sql, args).fetchone()
        return next(iter(row.values()))


def token(actor):
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(actor),
            "iss": "banking-lab",
            "aud": "banking-lab-api",
            "iat": now,
            "exp": now + timedelta(minutes=10),
            "jti": str(uuid4()),
        },
        SECRET,
        algorithm="HS256",
    )


def request(path, *, actor=None, body=None, key=None, request_id=None, server=0, method="POST"):
    headers = {"X-Request-ID": request_id or "verify-" + uuid4().hex}
    if actor:
        headers["Authorization"] = "Bearer " + token(actor)
    if key:
        headers["Idempotency-Key"] = key
    try:
        with httpx.Client(timeout=20, verify=False) as client:
            response = client.request(method, BASES[server] + path, json=body, headers=headers)
            return response.status_code, response.json() if response.content else None
    except httpx.TransportError:
        return 0, None


def wait_ready(server):
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        status, _ = request("/health/ready", server=server, method="GET")
        if status == 200:
            return
        time.sleep(0.2)
    raise RuntimeError("Candidate did not become ready")


def run(name, func):
    started = time.monotonic()
    try:
        func()
        RESULTS.append(
            {
                "name": name,
                "status": "PASS",
                "duration_ms": round((time.monotonic() - started) * 1000),
            }
        )
    except AssertionError as exc:
        RESULTS.append(
            {"name": name, "status": "FAIL", "code": name.upper(), "message": str(exc)[:300]}
        )
    except Exception as exc:
        RESULTS.append(
            {
                "name": name,
                "status": "FAIL",
                "code": "CANDIDATE_" + type(exc).__name__.upper(),
                "message": str(exc)[:300],
            }
        )


def fixture(balance=None):
    balance = balance if balance is not None else RNG.randint(10000, 20000)
    user, other, admin = ident(), ident(), ident()
    accounts = [ident(), ident(), ident(), ident()]
    now = datetime.now(UTC)
    with connect() as c:
        for uid, role in ((user, "USER"), (other, "USER"), (admin, "ADMIN")):
            c.execute(
                "INSERT INTO users(id,email,password_hash,role) VALUES(%s,%s,%s,%s)",
                (uid, str(uid) + "@example.test", PASSWORD_HASH, role),
            )
        for aid, owner in zip(accounts, [user, other, user, other], strict=True):
            c.execute(
                "INSERT INTO accounts(id,owner_user_id,account_type,currency) VALUES(%s,%s,'CUSTOMER','USD')",
                (aid, owner),
            )
        treasury = c.execute("SELECT id FROM accounts WHERE account_type='SYSTEM'").fetchone()
        if treasury:
            treasury = treasury["id"]
        else:
            treasury = ident()
            c.execute(
                "INSERT INTO accounts(id,account_type,currency) VALUES(%s,'SYSTEM','USD')",
                (treasury,),
            )
        for aid in accounts:
            tid, gid, iid, eid = ident(), ident(), ident(), ident()
            result = {"id": str(tid), "status": "COMPLETED"}
            c.execute(
                "INSERT INTO idempotency_records(id,actor_user_id,operation_type,key,request_hash,status,response_status,response_body,transfer_id,created_at,finalized_at,expires_at) VALUES(%s,%s,'FUNDING',%s,%s,'FINALIZED',201,%s,%s,%s,%s,%s)",
                (
                    iid,
                    admin,
                    str(iid),
                    "0" * 64,
                    json.dumps(result),
                    tid,
                    now,
                    now,
                    now + timedelta(days=1),
                ),
            )
            c.execute(
                "INSERT INTO journal_groups(id,operation_type,business_reference_id,currency,posted_at) VALUES(%s,'FUNDING',%s,'USD',%s)",
                (gid, tid, now),
            )
            c.execute(
                "UPDATE accounts SET balance_minor=balance_minor-%s,version=version+1 WHERE id=%s",
                (balance, treasury),
            )
            c.execute(
                "UPDATE accounts SET balance_minor=balance_minor+%s,version=version+1 WHERE id=%s",
                (balance, aid),
            )
            for seq, account, amount in ((1, treasury, -balance), (2, aid, balance)):
                c.execute(
                    "INSERT INTO ledger_postings(id,journal_group_id,account_id,currency,signed_amount_minor,created_at,entry_sequence) VALUES(%s,%s,%s,'USD',%s,%s,%s)",
                    (ident(), gid, account, amount, now, seq),
                )
            c.execute(
                "INSERT INTO transfers(id,actor_user_id,source_account_id,destination_account_id,currency,amount_minor,status,journal_group_id,idempotency_record_id,created_at,completed_at,request_id) VALUES(%s,%s,%s,%s,'USD',%s,'COMPLETED',%s,%s,%s,%s,'verifier-funding')",
                (tid, admin, treasury, aid, balance, gid, iid, now, now),
            )
            c.execute(
                "INSERT INTO outbox_events(id,event_type,aggregate_id,payload_json,available_at,created_at) VALUES(%s,'TransferCompleted',%s,%s,%s,%s)",
                (eid, tid, json.dumps({"transfer_id": str(tid)}), now, now),
            )
    return {
        "actor": user,
        "other": other,
        "source": accounts[0],
        "destination": accounts[1],
        "savings": accounts[2],
        "other_savings": accounts[3],
        "balance": balance,
    }


def payload(f, amount, source=None, destination=None):
    return {
        "source_account_id": str(source or f["source"]),
        "destination_account_id": str(destination or f["destination"]),
        "amount_minor": amount,
        "currency": "USD",
        "reference": "verifier-synthetic",
    }


def transfer(f, amount, key, **kwargs):
    body = kwargs.pop("body", None) or payload(f, amount)
    return request(
        "/api/v1/transfers", actor=kwargs.pop("actor", f["actor"]), body=body, key=key, **kwargs
    )


def invariants():
    queries = {
        "BALANCE_DRIFT": "SELECT a.id FROM accounts a LEFT JOIN ledger_postings p ON p.account_id=a.id GROUP BY a.id HAVING a.balance_minor<>coalesce(sum(p.signed_amount_minor),0)",
        "JOURNAL": "SELECT g.id FROM journal_groups g LEFT JOIN ledger_postings p ON p.journal_group_id=g.id LEFT JOIN accounts a ON a.id=p.account_id GROUP BY g.id HAVING count(p.id)<>2 OR coalesce(sum(p.signed_amount_minor),0)<>0 OR count(*) FILTER(WHERE p.currency<>g.currency OR p.currency<>a.currency)>0",
        "SOLVENCY": "SELECT id FROM accounts WHERE account_type='CUSTOMER' AND balance_minor<0",
        "TRANSFER": "SELECT t.id FROM transfers t WHERE (t.status='COMPLETED' AND (SELECT count(*) FROM ledger_postings p JOIN journal_groups g ON g.id=p.journal_group_id WHERE g.id=t.journal_group_id AND g.business_reference_id=t.id AND p.currency=t.currency AND ((p.account_id=t.source_account_id AND p.signed_amount_minor=-t.amount_minor) OR (p.account_id=t.destination_account_id AND p.signed_amount_minor=t.amount_minor)))<>2) OR t.status='PENDING' OR (t.status='REJECTED' AND t.journal_group_id IS NOT NULL)",
        "EVENT": "SELECT t.id FROM transfers t LEFT JOIN outbox_events o ON o.aggregate_id=t.id WHERE (t.status='COMPLETED' AND o.id IS NULL) OR (t.status<>'COMPLETED' AND o.id IS NOT NULL)",
        "IDEMPOTENCY": "SELECT i.id FROM idempotency_records i LEFT JOIN transfers t ON t.id=i.transfer_id WHERE t.id IS NULL OR i.status<>'FINALIZED' OR t.idempotency_record_id<>i.id OR (t.status='COMPLETED' AND (i.response_status<>201 OR i.response_body->>'id' IS DISTINCT FROM t.id::text)) OR (t.status='REJECTED' AND i.response_body->'error'->>'code' IS DISTINCT FROM t.rejection_code)",
    }
    violations = []
    with connect() as c:
        c.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        for code, query in queries.items():
            violations.extend({"code": code, "id": str(row["id"])} for row in c.execute(query))
    return violations


def serial_and_auth():
    f = fixture()
    amount = RNG.randint(1, 99)
    key = str(ident())
    status, result = transfer(f, amount, key)
    assert status == 201 and result["status"] == "COMPLETED", f"healthy transfer returned {status}"
    assert (
        scalar("SELECT balance_minor FROM accounts WHERE id=%s", (f["source"],))
        == f["balance"] - amount
    ), "Success without correct DB debit"
    assert (
        scalar(
            "SELECT count(*) FROM ledger_postings WHERE journal_group_id=%s",
            (UUID(result["journal_group_id"]),),
        )
        == 2
    )
    status, _ = transfer(f, amount, str(ident()), actor=f["other"])
    assert status in {403, 404}, "Cross-owner debit accepted"
    status, _ = request("/api/v1/accounts/" + str(f["source"]), actor=f["other"], method="GET")
    assert status == 404, "Foreign account visible"
    status, _ = request(
        "/api/v1/accounts/" + str(f["source"]) + "/statement", actor=f["other"], method="GET"
    )
    assert status == 404, "Foreign statement visible"
    status, _ = request("/api/v1/transfers", body=payload(f, 1), key=str(ident()))
    assert status == 401, "Unauthenticated transfer accepted"
    for invalid in [True, 1.0, 0, -1, 2**63]:
        status, _ = transfer(f, 1, str(ident()), body={**payload(f, 1), "amount_minor": invalid})
        assert status == 422, "Invalid money accepted"
    assert not invariants(), "Serial invariants broken"


def replay_and_conflict(count=100):
    f = fixture()
    key = str(ident())
    amount = RNG.randint(10, 500)
    status, first = transfer(f, amount, key, request_id="first-" + uuid4().hex)
    assert status == 201, "Initial operation failed"

    def call(n):
        return transfer(f, amount, key, server=n % 2, request_id="duplicate-" + uuid4().hex)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(call, range(count)))
    assert all(status == 201 and body == first for status, body in results), (
        "Identical replay changed status/body across processes"
    )
    assert (
        scalar("SELECT count(*) FROM transfers WHERE source_account_id=%s", (f["source"],)) == 1
    ), "Duplicate monetary effect"
    status, body = transfer(f, amount + 1, key, server=1)
    assert status == 409 and body["error"]["code"] == "IDEMPOTENCY_KEY_REUSED", (
        "Changed payload not rejected"
    )
    assert not invariants(), "Replay invariants broken"


def rejection_replay():
    f = fixture()
    key = str(ident())
    first = transfer(f, f["balance"] + 1, key)
    assert first[0] == 409 and first[1]["error"]["code"] == "INSUFFICIENT_FUNDS"
    status, _ = transfer(
        f,
        100,
        str(ident()),
        actor=f["other"],
        body=payload(f, 100, source=f["destination"], destination=f["source"]),
    )
    assert status == 201
    assert transfer(f, f["balance"] + 1, key, server=1) == first, (
        "Rejected result changed after funding"
    )


def concurrent_races():
    for n in range(20):
        f = fixture()
        amount = f["balance"] * 7 // 10
        rid = f"race-{SEED}-{n}"
        keys = [str(ident()), str(ident())]

        def call(server, f=f, amount=amount, keys=keys, rid=rid):
            return transfer(f, amount, keys[server], server=server, request_id=rid)

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(call, [0, 1]))
        assert sorted(status for status, _ in results) == [201, 409], (
            f"Round {n}: expected 201/409, got {[s for s, _ in results]}"
        )
        assert (
            scalar("SELECT balance_minor FROM accounts WHERE id=%s", (f["source"],))
            == f["balance"] - amount
        )
        assert not invariants(), f"Race {n} broke accounting"
    EVIDENCE.append({"synchronized_overspend_rounds": 20, "separate_candidate_processes": 2})


def opposite_and_unrelated():
    f = fixture()
    for n in range(20):
        rid = f"race-opposite-{SEED}-{n}"
        keys = [str(ident()), str(ident())]

        def call(server, keys=keys, rid=rid):
            return transfer(
                f,
                1,
                keys[server],
                server=server,
                request_id=rid,
                actor=f["other"] if server else f["actor"],
                body=payload(
                    f,
                    1,
                    source=f["destination"] if server else f["source"],
                    destination=f["source"] if server else f["destination"],
                ),
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(call, [0, 1]))
        assert all(s == 201 for s, _ in results), "Opposite-direction requests failed/hung"
    # Independent accounts must also remain live.
    rid = f"race-unrelated-{SEED}"
    keys = [str(ident()), str(ident())]

    def separate(server):
        return transfer(
            f,
            1,
            keys[server],
            server=server,
            request_id=rid,
            body=payload(
                f,
                1,
                source=f["savings"] if server else f["source"],
                destination=f["other_savings"] if server else f["destination"],
            ),
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(separate, [0, 1]))
    assert all(s == 201 for s, _ in results), "Unrelated transfers blocked"
    assert not invariants()


def crash(point):
    f = fixture()
    key = str(ident())
    amount = RNG.randint(1, 999)
    status, _ = transfer(f, amount, key, request_id="fault-" + point + "-1", server=0)
    assert status == 0, "Expected actual process termination at controlled failpoint"
    wait_ready(0)
    committed = point == "AFTER_SQL_COMMIT_BEFORE_HTTP_RESPONSE"
    actual = scalar("SELECT balance_minor FROM accounts WHERE id=%s", (f["source"],))
    assert actual == f["balance"] - (amount if committed else 0), (
        "Partial debit survived process crash"
    )
    assert scalar(
        "SELECT count(*) FROM transfers WHERE source_account_id=%s", (f["source"],)
    ) == int(committed)
    assert not invariants(), "Crash caused partial committed state"
    status, recovered = transfer(f, amount, key, server=1)
    assert status == 201, "Same-key retry after crash failed"
    assert scalar("SELECT count(*) FROM transfers WHERE source_account_id=%s", (f["source"],)) == 1
    assert transfer(f, amount, key, server=0) == (201, recovered), "Restart lost durable outcome"
    assert not invariants()


def main():
    started = time.monotonic()
    try:
        wait_ready(0)
        wait_ready(1)
        run("serial_authorization_contract", serial_and_auth)
        run(
            "cross_process_exact_replay",
            lambda: replay_and_conflict(100 if TASK in {"RL-01", "RL-02"} else 12),
        )
        run("persisted_terminal_rejection", rejection_replay)
        if TASK == "RL-01":
            run("synchronized_overspend", concurrent_races)
            run("opposite_and_unrelated_liveness", opposite_and_unrelated)
        if TASK in {"RL-02", "RL-03"}:
            points = (
                ["AFTER_SQL_COMMIT_BEFORE_HTTP_RESPONSE"]
                if TASK == "RL-02"
                else [
                    "BEFORE_POSTING",
                    "AFTER_SOURCE_UPDATE",
                    "BEFORE_SQL_COMMIT",
                    "AFTER_SQL_COMMIT_BEFORE_HTTP_RESPONSE",
                ]
            )
            for point in points:
                run("crash_" + point.lower(), lambda point=point: crash(point))
        violations = invariants()
        passed = sum(t["status"] == "PASS" for t in RESULTS)
        report = {
            "status": "PASS" if passed == len(RESULTS) and not violations else "FAIL",
            "tests": {"passed": passed, "failed": len(RESULTS) - passed, "skipped": 0},
            "checks": RESULTS,
            "invariant_violations": len(violations),
            "violations": violations,
            "failure_codes": [t["code"] for t in RESULTS if t["status"] != "PASS"],
            "duration_ms": round((time.monotonic() - started) * 1000),
            "observations": EVIDENCE,
        }
    except Exception as exc:
        report = {
            "status": "VERIFIER_ERROR",
            "error_type": type(exc).__name__,
            "message": str(exc)[:200],
            "tests": {"passed": 0, "failed": 0, "skipped": 0},
            "invariant_violations": None,
            "failure_codes": ["VERIFIER_ERROR"],
        }
        traceback.print_exc()
    print("RESULT_JSON:" + json.dumps(report))


if __name__ == "__main__":
    main()
