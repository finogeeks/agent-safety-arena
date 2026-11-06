"""Build a relocatable catalog from reviewed comparisons, without live trials."""
import hashlib
from html import escape
import json
from pathlib import Path
import re
import tempfile

from arena.evidence.media import resolve_public_media_sources
from arena.reporting import bilingual


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_site(results_root, output):
    root = Path(results_root).resolve()
    output = Path(output).resolve()
    if not root.is_dir():
        raise ValueError('Results root must be an existing directory')
    if output.exists():
        raise ValueError('Site output already exists; choose a new directory')
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError('Site output must not overlap the results source')

    records = []
    for path in sorted(root.rglob('record.json')):
        relative = path.relative_to(root)
        if (not path.resolve().is_relative_to(root) or len(relative.parts) != 4
                or any(not re.fullmatch(r'[a-z0-9][a-z0-9-]*', part) for part in relative.parts[:-1])):
            raise ValueError(f'Record must use case/Agent/comparison/record.json: {relative.as_posix()}')
        record = json.loads(path.read_text('utf8'))
        bilingual.validate(record)
        if (record['scenarioId'], record['agentId']) != relative.parts[:2]:
            raise ValueError(f'Record identities differ from its directories: {relative.as_posix()}')
        sources = resolve_public_media_sources(record['publicMedia'], path.parent)
        if any(not source.is_relative_to(path.parent.resolve()) for _, source in sources):
            raise ValueError(f'Media must stay inside its reviewed result: {relative.as_posix()}')
        records.append((path, relative, record))
    if not records:
        raise ValueError('No reviewed comparison record.json files found')

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='arena-site-', dir=output.parent) as temporary:
        staging = Path(temporary) / 'site'
        staging.mkdir()
        items = []
        for path, relative, record in records:
            bilingual.export_reports(path, staging / relative.parent)
            prefix = relative.parent.as_posix()
            title = escape(record['narrative']['zh-CN']['title'])
            identity = escape(f'{record["scenarioId"]} / {record["agentId"]} / {relative.parent.name}')
            items.append(f'<li><strong>{title}</strong><p>{identity} · '
                         f'{escape(record["evidenceOrigin"])} / {escape(record["phase"])}</p>'
                         f'<a href="{prefix}/zh-CN.html">中文</a> · '
                         f'<a href="{prefix}/en.html">English</a></li>')
        index = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                 '<meta name="viewport" content="width=device-width,initial-scale=1">'
                 '<title>Agent Safety Arena</title><link rel="stylesheet" href="catalog.css">'
                 '</head><body><main><h1>Agent Safety Arena</h1>'
                 '<p>案例 / Case → Agent → 对照 / Comparison</p><ul>' + ''.join(items)
                 + '</ul><p><a href="site-manifest.json">Build manifest</a></p></main></body></html>')
        (staging / 'index.html').write_text(index, encoding='utf8')
        (staging / 'catalog.css').write_text(
            'body{font:16px/1.6 system-ui,sans-serif;margin:0;background:#f4f6f9;color:#243248}'
            'main{max-width:1000px;margin:auto;padding:24px}ul{padding:0;list-style:none}'
            'li{background:white;border:1px solid #dfe5ee;border-radius:8px;padding:20px;margin:16px 0}'
            'p{overflow-wrap:anywhere}a{color:#285dbb}', encoding='utf8')
        manifest = dict(schemaVersion=1, trialExecutions=0,
                        sources={relative.as_posix(): file_hash(path) for path, relative, _ in records},
                        excludedReplayResults=[p.relative_to(root).as_posix() for p in sorted(root.rglob('result.json'))],
                        files={p.relative_to(staging).as_posix(): file_hash(p)
                               for p in sorted(staging.rglob('*')) if p.is_file()})
        (staging / 'site-manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        if output.exists():
            raise ValueError('Site output appeared during build; preserve it')
        staging.rename(output)
    return dict(directory=str(output), comparisons=len(records), trialExecutions=0)
