"""Build static reviewer pages from recorded evidence using only the Python stdlib."""

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence"
OUTPUT = EVIDENCE / "reviewer"
GROUPS = {
    "money-cases": ("Money, concurrency & crash recovery", ("concurrency", "integration")),
    "security-cases": ("API security & operator boundaries", ("security",)),
    "worker-cases": ("Outbox delivery & bounded recovery", ("reliability",)),
    "domain-cases": ("Strict money types & domain boundaries", ("unit",)),
}
STYLE = """
*{box-sizing:border-box}body{margin:0;background:#f5f7fa;color:#18283c;font:16px/1.5 system-ui,sans-serif}
main{max-width:1120px;margin:auto;padding:32px 40px}header{border-bottom:2px solid #183b59;padding-bottom:20px}
.eyebrow{color:#527087;letter-spacing:.1em;font-size:12px;font-weight:700}h1{font-size:30px;margin:8px 0}
h2{font-size:20px;margin:26px 0 10px}p{margin:8px 0}nav{font-size:13px;padding:12px 0}
a{color:#18577a}nav a{margin-right:14px}.muted,footer{color:#546577;font-size:13px}
.numbers{display:flex;gap:50px;padding:18px 0}.numbers strong{display:block;font-size:34px;color:#17614c}
table{border-collapse:collapse;width:100%;background:white;font-size:14px}th{text-align:left;background:#e8eef3}
td,th{padding:10px 12px;border-bottom:1px solid #dbe3e9;vertical-align:top}code{font:13px ui-monospace,monospace;overflow-wrap:anywhere}
.pass{color:#17614c;font-weight:700}.fail{color:#984327;font-weight:700}pre{background:#18283c;color:#e5edf5;padding:18px;white-space:pre-wrap;font-size:13px}
footer{margin-top:24px;padding-top:14px;border-top:1px solid #cbd6e0}
"""


def table(headers, rows):
    return (
        "<table><thead><tr>"
        + "".join(f"<th>{escape(x)}</th>" for x in headers)
        + (
            "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{x}</td>" for x in row) + "</tr>" for row in rows)
            + "</tbody></table>"
        )
    )


def verdict(value):
    return f'<span class="{"pass" if value == "PASS" else "fail"}">{escape(value)}</span>'


def page(name, title, body, source):
    nav = "".join(
        f'<a href="{key}.html">{label}</a>'
        for key, label in (
            ("test-summary", "Test summary"),
            ("money-cases", "Money"),
            ("security-cases", "Security"),
            ("worker-cases", "Worker"),
            ("domain-cases", "Domain"),
            ("rl-results", "RL benchmark"),
            ("operations", "Operations"),
        )
    )
    (OUTPUT / f"{name}.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)} — Banking RL Lab</title><style>{STYLE}</style><main>"
        '<header><div class="eyebrow">BANKING RL LAB / RECORDED LOCAL EVIDENCE</div>'
        f"<h1>{escape(title)}</h1><p>Real PostgreSQL · synthetic data · local verification</p></header>"
        f"<nav>{nav}</nav>{body}<footer>Rendered evidence report, not an operator dashboard. "
        f"Source: {source}. Raw artifacts remain authoritative.</footer></main></html>"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, default=EVIDENCE / "readme-tests.xml")
    args = parser.parse_args()
    destination = EVIDENCE / "readme-tests.xml"
    if args.junit.resolve() != destination.resolve():
        shutil.copy2(args.junit, destination)
    suite = ET.parse(destination).getroot().find("testsuite")
    assert suite is not None
    cases = list(suite.iter("testcase"))
    assert len(cases) == int(suite.attrib["tests"])
    assert not any(
        case.find(tag) is not None for case in cases for tag in ("failure", "error", "skipped")
    )
    assert all(int(suite.attrib[key]) == 0 for key in ("failures", "errors", "skipped"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    counts = Counter(case.attrib["classname"] for case in cases)
    source = '<a href="../readme-tests.xml">readme-tests.xml</a> · <a href="../readme-verification.log">make ci log</a>'
    summary = (
        f'<p class="muted">Executed {escape(suite.attrib["timestamp"])} · command: <code>make ci</code></p>'
        f'<div class="numbers"><div><strong>{len(cases)}</strong>passed test cases</div>'
        f"<div><strong>0</strong>failures / errors / skipped</div><div><strong>{suite.attrib['time']} s</strong>pytest suite time</div></div>"
        + table(
            ["Module", "Cases", "Result"],
            [
                (f"<code>{escape(name)}</code>", str(count), verdict("PASS"))
                for name, count in counts.items()
            ],
        )
        + "<h2>Additional quality gates in this run</h2><p>Ruff lint and formatting, strict mypy, migration to 0002 and independent SQL reconciliation passed.</p>"
        + '<p class="muted">One TestClient/HTTPX adapter deprecation warning is documented in the raw log. No remote CI run is claimed.</p>'
    )
    page("test-summary", "Application verification", summary, source)
    catalogue = [
        "# Executed application test catalogue\n",
        f"Source: [JUnit](evidence/readme-tests.xml), [make ci log](evidence/readme-verification.log). Executed {suite.attrib['timestamp']}; {len(cases)} passed, zero failures/errors/skips. Parameterized entries count separately. Hypothesis examples are not counted as separate test cases.\n",
    ]
    for name, (title, prefixes) in GROUPS.items():
        selected = [case for case in cases if case.attrib["classname"].split(".")[1] in prefixes]
        rows = []
        catalogue.extend(
            [
                f"\n## {title}\n",
                "| Executed test case | Source | Time (s) | Result |",
                "|---|---|---:|---|",
            ]
        )
        for case in selected:
            path = case.attrib["classname"].replace(".", "/") + ".py"
            rows.append(
                (
                    f"<code>{escape(case.attrib['name'])}</code>",
                    case.attrib["time"],
                    verdict("PASS"),
                )
            )
            catalogue.append(
                f"| `{case.attrib['name']}` | [{path}](../{path}) | {case.attrib['time']} | PASS |"
            )
        page(
            name,
            title,
            f"<p><strong>{len(selected)} / {len(selected)} cases passed</strong> · includes parameterized cases.</p>"
            + table(["Executed test case", "Time (s)", "Result"], rows),
            source,
        )
    (ROOT / "docs/test-catalogue.md").write_text("\n".join(catalogue) + "\n")
    matrix = json.loads((EVIDENCE / "validation-matrix.json").read_text())
    runs = matrix["runs"]
    assert matrix["status"] == "PASS" and len(runs) == 56
    assert all(row["status"] == row["expected"] for row in runs)
    rows = []
    for task in ("RL-01", "RL-02", "RL-03"):
        subset = [row for row in runs if row["task"] == task]
        for mode in ("baseline", "golden"):
            found = [row for row in subset if row["mode"] == mode]
            assert len(found) == 5
            rows.append((task, mode, "5", escape(found[0]["expected"]), "5 / 5 matched"))
    controls = [
        "noop",
        "partial",
        "hardcoded",
        "canned",
        "disabled",
        "suppress",
        "delete-evidence",
        "unit-only",
    ]
    control_rows = []
    for mode in controls:
        found = [row for row in runs if row["mode"] == mode]
        assert len(found) == 3 and all(row["status"] == "FAIL" for row in found)
        control_rows.append((f"<code>{mode}</code>", "FAIL", "FAIL", "FAIL", "3 / 3 rejected"))
    alternatives = [row for row in runs if row["mode"] in {"alternative", "lock-only"}]
    assert len(alternatives) == 2 and all(row["status"] == "PASS" for row in alternatives)
    page(
        "rl-results",
        "RL benchmark: 56 / 56 expected verdicts",
        "<p>Task version 1.0.2 · seeds 101, 202, 303, 404, 505 · no skipped checks</p>"
        + table(["Task", "Candidate", "Seeds", "Expected", "Observed"], rows)
        + "<h2>Negative controls</h2>"
        + table(["Control", "RL-01", "RL-02", "RL-03", "Observed"], control_rows)
        + "<h2>Accepted alternate implementations</h2><p>RL-01 optimistic CAS: PASS · RL-01 lock-only with callback retained: PASS</p><p class=muted>Baseline FAIL and control FAIL are expected candidate outcomes. They demonstrate that the verifier detects defects.</p>",
        '<a href="../validation-matrix.json">validation-matrix.json</a> · <a href="../challenges/">individual reports</a>',
    )
    descriptions = {
        "INC-01": "Concurrent withdrawals",
        "INC-02": "Response lost after commit",
        "INC-03": "Process death at posting boundaries",
        "INC-04": "Opposite-direction transfers and lock ordering",
        "INC-05": "Ledger drift detection",
        "INC-06": "Connection pool exhaustion",
        "INC-07": "Provider failure and recovery",
        "INC-08": "Lost ACK, lease expiry and deduplication",
        "INC-10": "Equal timestamps and history cursors",
        "INC-11": "Cross-owner authorization",
        "INC-15": "Daily limit at UTC midnight",
    }
    incident_rows = []
    for path in sorted((EVIDENCE / "scenarios").glob("*.json")):
        data = json.loads(path.read_text())
        assert data["status"] == "PASS" and data["exit_code"] == 0
        incident_rows.append(
            (data["scenario"], escape(descriptions[data["scenario"]]), verdict(data["status"]))
        )
    assert len(incident_rows) == 11
    restore = json.loads((EVIDENCE / "backup-restore.json").read_text())
    assert restore["status"] == "PASS" and restore["source_stats"] == restore["restored_stats"]
    load = json.loads((EVIDENCE / "load/result.json").read_text())
    assert load["status"] == "PASS" and load["invariants"]["invariant_violations"] == 0
    performance = [
        (
            str(row["sample"]),
            str(row["requests"]),
            f"{row['median_ms']:.2f}",
            f"{row['p95_ms']:.2f}",
        )
        for row in load["samples"]
    ]
    page(
        "operations",
        "Incident drills, restore & measured load",
        table(["Incident", "Executed scenario", "Result"], incident_rows)
        + "<h2>Logical restore: PASS</h2><p>New disposable database; equal counts, ledger digest and replay digest. Independent reconciliation: zero discrepancies.</p>"
        + "<h2>Recorded HTTP profile</h2><p class=muted>Apple M2 Pro / 16 GiB · Docker aarch64 / 10 CPUs / 8 GiB · concurrency 10 · 10 warmups</p>"
        + table(["Sample", "HTTP transfers", "Median (ms)", "p95 (ms)"], performance)
        + f"<p>1,000 additional history transfers. Final fixture: {load['invariants']['counts']['transfers']:,} transfers / {load['invariants']['counts']['ledger_postings']:,} postings; zero invariant violations.</p><p class=muted>Recorded small local profile; no production SLO, HA/PITR or 100k-load claim.</p>",
        '<a href="../scenarios/">scenario reports</a> · <a href="../backup-restore.json">restore JSON</a> · <a href="../load/result.json">load JSON</a>',
    )
    print(
        f"Built 7 evidence pages and full {len(cases)}-case catalogue; all source consistency checks passed."
    )


if __name__ == "__main__":
    main()
