#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path('/root/git/codeagents-x1')
DATA_FILE = ROOT / 'docs' / 'data' / 'agents-metadata.json'
SCHEMA_FILE = ROOT / 'docs' / 'data' / 'agents-metadata.schema.json'
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
ID_RE = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
CATEGORY_VALUES = {'deep-analysis', 'single-file'}
DOWNLOAD_TYPES = {'npm_weekly', 'pypi_monthly', 'none', 'unknown'}
EVIDENCE_STATUS = {'complete', 'partial', 'single-file-only'}
EVIDENCE_SOURCE_TYPES = {'source-analysis', 'binary-analysis', 'summary-analysis', 'official-docs'}
TOP_LEVEL_REQUIRED = {'schema_version', 'last_updated', 'agents'}
TOP_LEVEL_OPTIONAL = {'maintainer_note'}
AGENT_REQUIRED = {
    'id', 'name', 'category', 'license', 'developer',
    'implementation_language', 'runtime', 'package_ecosystem', 'evidence'
}
AGENT_OPTIONAL = {'stars', 'downloads', 'pricing_summary', 'free_tier'}
DOWNLOADS_REQUIRED = {'type', 'value', 'as_of'}
EVIDENCE_REQUIRED = {'status', 'source_type', 'evidence_path', 'last_verified'}


def load_json(path: Path):
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def is_valid_date(value: str) -> bool:
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.strptime(value, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def require_keys(obj: dict, required: set[str], optional: set[str], label: str, errors: list[str]):
    keys = set(obj.keys())
    missing = required - keys
    extra = keys - required - optional
    for key in sorted(missing):
        errors.append(f'{label}: missing required key `{key}`')
    for key in sorted(extra):
        errors.append(f'{label}: unexpected key `{key}`')


def validate_agent(agent: dict, index: int, errors: list[str], seen_ids: set[str]):
    label = f'agents[{index}]'
    if not isinstance(agent, dict):
        errors.append(f'{label}: must be an object')
        return

    require_keys(agent, AGENT_REQUIRED, AGENT_OPTIONAL, label, errors)

    agent_id = agent.get('id')
    if not isinstance(agent_id, str) or not ID_RE.match(agent_id):
        errors.append(f'{label}.id: must be kebab-case string')
    elif agent_id in seen_ids:
        errors.append(f'{label}.id: duplicate id `{agent_id}`')
    else:
        seen_ids.add(agent_id)

    for field in ['name', 'license', 'developer', 'implementation_language', 'runtime', 'package_ecosystem']:
        value = agent.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{label}.{field}: must be a non-empty string')

    category = agent.get('category')
    if category not in CATEGORY_VALUES:
        errors.append(f'{label}.category: must be one of {sorted(CATEGORY_VALUES)}')

    if 'stars' in agent and not isinstance(agent.get('stars'), str):
        errors.append(f'{label}.stars: must be a string when present')
    if 'pricing_summary' in agent and not isinstance(agent.get('pricing_summary'), str):
        errors.append(f'{label}.pricing_summary: must be a string when present')
    if 'free_tier' in agent and not isinstance(agent.get('free_tier'), str):
        errors.append(f'{label}.free_tier: must be a string when present')

    downloads = agent.get('downloads')
    if downloads is not None:
        if not isinstance(downloads, dict):
            errors.append(f'{label}.downloads: must be an object')
        else:
            require_keys(downloads, DOWNLOADS_REQUIRED, set(), f'{label}.downloads', errors)
            if downloads.get('type') not in DOWNLOAD_TYPES:
                errors.append(f'{label}.downloads.type: must be one of {sorted(DOWNLOAD_TYPES)}')
            if not isinstance(downloads.get('value'), str) or not downloads.get('value').strip():
                errors.append(f'{label}.downloads.value: must be a non-empty string')
            if not is_valid_date(downloads.get('as_of')):
                errors.append(f'{label}.downloads.as_of: must be a valid YYYY-MM-DD date')

    evidence = agent.get('evidence')
    if not isinstance(evidence, dict):
        errors.append(f'{label}.evidence: must be an object')
    else:
        require_keys(evidence, EVIDENCE_REQUIRED, set(), f'{label}.evidence', errors)
        if evidence.get('status') not in EVIDENCE_STATUS:
            errors.append(f'{label}.evidence.status: must be one of {sorted(EVIDENCE_STATUS)}')
        if evidence.get('source_type') not in EVIDENCE_SOURCE_TYPES:
            errors.append(f'{label}.evidence.source_type: must be one of {sorted(EVIDENCE_SOURCE_TYPES)}')
        if not isinstance(evidence.get('evidence_path'), str) or not evidence.get('evidence_path').strip():
            errors.append(f'{label}.evidence.evidence_path: must be a non-empty string')
        if not is_valid_date(evidence.get('last_verified')):
            errors.append(f'{label}.evidence.last_verified: must be a valid YYYY-MM-DD date')


def main() -> int:
    errors: list[str] = []

    if not DATA_FILE.exists():
        print(f'ERROR: missing data file {DATA_FILE.relative_to(ROOT)}')
        return 1
    if not SCHEMA_FILE.exists():
        print(f'ERROR: missing schema file {SCHEMA_FILE.relative_to(ROOT)}')
        return 1

    try:
        data = load_json(DATA_FILE)
        load_json(SCHEMA_FILE)
    except json.JSONDecodeError as exc:
        print(f'ERROR: invalid JSON: {exc}')
        return 1

    if not isinstance(data, dict):
        print('ERROR: top-level JSON must be an object')
        return 1

    require_keys(data, TOP_LEVEL_REQUIRED, TOP_LEVEL_OPTIONAL, 'root', errors)

    if not isinstance(data.get('schema_version'), int) or data.get('schema_version', 0) < 1:
        errors.append('root.schema_version: must be an integer >= 1')
    if not is_valid_date(data.get('last_updated')):
        errors.append('root.last_updated: must be a valid YYYY-MM-DD date')
    if 'maintainer_note' in data and not isinstance(data.get('maintainer_note'), str):
        errors.append('root.maintainer_note: must be a string when present')

    agents = data.get('agents')
    if not isinstance(agents, list) or not agents:
        errors.append('root.agents: must be a non-empty array')
    else:
        seen_ids: set[str] = set()
        for idx, agent in enumerate(agents):
            validate_agent(agent, idx, errors, seen_ids)

    if errors:
        for err in errors:
            print(f'ERROR: {err}')
        return 1

    print('OK: data schema checks passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
