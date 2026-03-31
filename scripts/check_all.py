#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
CHECKS = [
    ('data schema', str(SCRIPTS / 'check_data_schema.py')),
    ('repository consistency', str(SCRIPTS / 'check_repo_consistency.py')),
    ('stale data', str(SCRIPTS / 'check_stale_data.py')),
    ('repo URL + Stars verification', str(SCRIPTS / 'check_repo_url.py')),
]


def run_check(label: str, script: str) -> int:
    print(f'==> Running {label}: {script}')
    parts = script.split()
    result = subprocess.run([sys.executable] + parts, cwd=ROOT)
    print(f'==> Exit code: {result.returncode}\n')
    return result.returncode


def main() -> int:
    exit_codes = [run_check(label, script) for label, script in CHECKS]
    if any(code != 0 for code in exit_codes):
        print('FAIL: one or more checks returned non-zero exit codes')
        return 1
    print('OK: all repository checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
