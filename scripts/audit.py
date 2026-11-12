import subprocess
import sys

subprocess.run(
    [
        "uv",
        "export",
        "--locked",
        "--no-dev",
        "--no-emit-project",
        "-o",
        "/tmp/lab-requirements.txt",
    ],
    check=True,
    stdout=subprocess.DEVNULL,
)
sys.exit(
    subprocess.run(
        ["pip-audit", "-r", "/tmp/lab-requirements.txt", "--disable-pip", "--no-deps"]
    ).returncode
)
