#!/usr/bin/env python3
import json
import re
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
DATA_FILE = DOCS / 'data' / 'agents-metadata.json'

CHECK_FILES = [
    ROOT / 'README.md',
    DOCS / 'SUMMARY.md',
    DOCS / 'comparison' / 'features.md',
    DOCS / 'comparison' / 'pricing.md',
    DOCS / 'comparison' / 'privacy-telemetry.md',
    DOCS / 'comparison' / 'system-requirements.md',
    DOCS / 'evidence-index.md',
]

DATE_PATTERN = re.compile(r'20\d{2}-\d{2}-\d{2}')
STALE_DAYS_WARNING = 45
DYNAMIC_TERMS = ('Stars', 'stars', '下载', 'downloads', '验证', '测量')


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def load_data() -> dict:
    return json.loads(read_text(DATA_FILE))


def parse_date(value: str) -> date:
    return datetime.strptime(value, '%Y-%m-%d').date()


def should_scan_line(line: str) -> bool:
    stripped = line.strip()
    if not any(term in stripped for term in DYNAMIC_TERMS):
        return False
    if stripped.startswith('>'):
        return False
    if stripped.startswith('#'):
        return False
    return '|' in stripped or stripped.startswith('- ')


def collect_metadata_tokens(metadata: dict) -> dict[str, dict[str, set[str]]]:
    tokens: dict[str, dict[str, set[str]]] = {}
    for agent in metadata.get('agents', []):
        bucket: dict[str, set[str]] = defaultdict(set)
        name = agent['name']
        bucket['stars'].add(str(agent.get('stars', '')).strip())
        downloads = agent.get('downloads', {})
        bucket['downloads'].add(str(downloads.get('value', '')).strip())
        bucket['dates'].add(str(downloads.get('as_of', '')).strip())
        evidence = agent.get('evidence', {})
        bucket['dates'].add(str(evidence.get('last_verified', '')).strip())
        bucket['pricing'].add(str(agent.get('pricing_summary', '')).strip())
        bucket['free_tier'].add(str(agent.get('free_tier', '')).strip())
        tokens[name] = bucket
    return tokens


def check_metadata_freshness(metadata: dict, warnings: list[str]):
    today = date.today()
    all_dates = []
    root_last_updated = metadata.get('last_updated')
    if root_last_updated:
        all_dates.append(('docs/data/agents-metadata.json:last_updated', root_last_updated))
    for agent in metadata.get('agents', []):
        downloads_as_of = agent.get('downloads', {}).get('as_of')
        evidence_verified = agent.get('evidence', {}).get('last_verified')
        if downloads_as_of:
            all_dates.append((f"{agent['id']}:downloads.as_of", downloads_as_of))
        if evidence_verified:
            all_dates.append((f"{agent['id']}:evidence.last_verified", evidence_verified))
    for label, value in all_dates:
        try:
            days = (today - parse_date(value)).days
        except ValueError:
            warnings.append(f'无法解析日期: {label} -> {value}')
            continue
        if days > STALE_DAYS_WARNING:
            warnings.append(f'数据可能过期: {label} 距今 {days} 天（阈值 {STALE_DAYS_WARNING} 天）')


def check_tracked_files_for_token_drift(metadata_tokens: dict[str, dict[str, set[str]]], warnings: list[str]):
    for path in CHECK_FILES:
        if not path.exists():
            continue
        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not should_scan_line(line):
                continue
            matched_agents = [name for name in metadata_tokens if name in line]
            for agent_name in matched_agents:
                token_groups = metadata_tokens[agent_name]
                if 'Stars' in line or 'stars' in line or 'Stars' in line:
                    if token_groups['stars'] and not any(token in line for token in token_groups['stars'] if token):
                        warnings.append(
                            f'{path.relative_to(ROOT)}:{line_no} 中 {agent_name} 的 Stars 可能未与 docs/data 同步: {line.strip()}'
                        )
                if '下载' in line or 'downloads' in line:
                    if token_groups['downloads'] and not any(token in line for token in token_groups['downloads'] if token and token != '—'):
                        warnings.append(
                            f'{path.relative_to(ROOT)}:{line_no} 中 {agent_name} 的下载量可能未与 docs/data 同步: {line.strip()}'
                        )


def check_date_mentions_against_metadata(metadata: dict, warnings: list[str]):
    known_dates = {metadata.get('last_updated', '')}
    for agent in metadata.get('agents', []):
        known_dates.add(agent.get('downloads', {}).get('as_of', ''))
        known_dates.add(agent.get('evidence', {}).get('last_verified', ''))
    known_dates = {value for value in known_dates if value}

    for path in CHECK_FILES:
        if not path.exists():
            continue
        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if not should_scan_line(line):
                continue
            for found in DATE_PATTERN.findall(line):
                if found not in known_dates:
                    warnings.append(
                        f'{path.relative_to(ROOT)}:{line_no} 出现未在 docs/data 注册的日期 {found}: {line.strip()}'
                    )


def main() -> int:
    warnings: list[str] = []
    if not DATA_FILE.exists():
        print('ERROR: missing docs/data/agents-metadata.json')
        return 1

    metadata = load_data()
    metadata_tokens = collect_metadata_tokens(metadata)
    check_metadata_freshness(metadata, warnings)
    check_tracked_files_for_token_drift(metadata_tokens, warnings)
    check_date_mentions_against_metadata(metadata, warnings)

    if warnings:
        for item in warnings:
            print(f'WARN: {item}')
        return 0

    print('OK: stale data checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
