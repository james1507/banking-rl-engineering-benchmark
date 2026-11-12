"""Small local leak guard, not a certified secret scanner."""

import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
values = []
local = root / ".env"
if local.exists():
    values = [
        line.split("=", 1)[1]
        for line in local.read_text().splitlines()
        if "=" in line and len(line.split("=", 1)[1]) >= 32
    ]
paths = subprocess.check_output(
    ["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=root, text=True
).splitlines()
findings = []
for name in paths:
    path = root / name
    if not path.is_file():
        continue
    content = path.read_text(errors="replace")
    if (
        any(value in content for value in values)
        or re.search(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", content)
        or re.search(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", content)
    ):
        findings.append(name)
if findings:
    raise SystemExit("Potential secret leak in: " + ", ".join(findings))
print("Local secret/JWT scan passed for " + str(len(paths)) + " files (heuristic only).")
