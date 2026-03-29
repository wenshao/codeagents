#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

ROOT = Path('/root/git/codeagents-x1')
DOCS = ROOT / 'docs'
DATA_FILE = DOCS / 'data' / 'agents-metadata.json'
README = ROOT / 'README.md'
SUMMARY = DOCS / 'SUMMARY.md'
TOOLS_INDEX = DOCS / 'tools' / 'README.md'
EVIDENCE_INDEX = DOCS / 'evidence-index.md'

CHECK_FILES = [
    README,
    SUMMARY,
    TOOLS_INDEX,
    DOCS / 'comparison' / 'features.md',
    DOCS / 'comparison' / 'pricing.md',
    DOCS / 'comparison' / 'privacy-telemetry.md',
    DOCS / 'comparison' / 'system-requirements.md',
]


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def load_data() -> dict:
    return json.loads(read_text(DATA_FILE))


def check_required_files(errors: list[str]):
    for path in [DATA_FILE, README, SUMMARY, TOOLS_INDEX, EVIDENCE_INDEX]:
        if not path.exists():
            errors.append(f'Missing required file: {path.relative_to(ROOT)}')


def check_evidence_paths(metadata: dict, errors: list[str]):
    for agent in metadata.get('agents', []):
        evidence_path = agent.get('evidence', {}).get('evidence_path')
        if evidence_path:
            full = ROOT / evidence_path
            if not full.exists():
                errors.append(f"Missing evidence path for {agent['id']}: {evidence_path}")


def check_agent_mentions(metadata: dict, warnings: list[str]):
    files_text = {path: read_text(path) for path in CHECK_FILES if path.exists()}
    for agent in metadata.get('agents', []):
        name = agent['name']
        mentions = [path.relative_to(ROOT).as_posix() for path, text in files_text.items() if name in text]
        if not mentions:
            warnings.append(f"Agent not mentioned in tracked summary files: {name}")


def check_links(errors: list[str], warnings: list[str]):
    link_pattern = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
    ignored_literal_targets = {'链接', 'link', 'url', 'example', '.*'}
    for md in ROOT.rglob('*.md'):
        if '.git' in md.parts:
            continue
        text = read_text(md)
        in_code_block = False
        for line in text.splitlines():
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            for target in link_pattern.findall(line):
                if target.startswith(('http://', 'https://', '#', 'mailto:')):
                    continue
                normalized = target.split('#', 1)[0].strip()
                if not normalized or normalized in ignored_literal_targets:
                    continue
                candidate = (md.parent / normalized).resolve()
                if not candidate.exists():
                    errors.append(f'Broken relative link in {md.relative_to(ROOT)} -> {target}')
                elif candidate.is_dir():
                    index_md = candidate / 'README.md'
                    if not index_md.exists():
                        warnings.append(f'Directory link without README target: {md.relative_to(ROOT)} -> {target}')


def check_tools_index_consistency(warnings: list[str]):
    text = read_text(TOOLS_INDEX)
    qoder_lines = [line for line in text.splitlines() if '[Qoder CLI](./qoder-cli/)' in line]
    if any('单文件' in line for line in qoder_lines):
        warnings.append('docs/tools/README.md lists Qoder CLI as a directory link but labels it 单文件; consider clarifying depth/type.')


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    check_required_files(errors)
    if errors:
        for item in errors:
            print(f'ERROR: {item}')
        return 1

    metadata = load_data()
    check_evidence_paths(metadata, errors)
    check_agent_mentions(metadata, warnings)
    check_links(errors, warnings)
    check_tools_index_consistency(warnings)

    if errors:
        for item in errors:
            print(f'ERROR: {item}')
    if warnings:
        for item in warnings:
            print(f'WARN: {item}')

    if errors:
        return 1

    print('OK: repository consistency checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
