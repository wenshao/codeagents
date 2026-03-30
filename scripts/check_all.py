#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
CHECKS = [
    ('data schema', SCRIPTS / 'check_data_schema.py'),
    ('repository consistency', SCRIPTS / 'check_repo_consistency.py'),
    ('stale data', SCRIPTS / 'check_stale_data.py'),
]


def run_check(label: str, script: Path) -> int:
    print(f'==> Running {label}: {script.name}')
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT)
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
