"""Build a relocatable catalog from reviewed comparisons, without live trials."""
import hashlib
import json
from pathlib import Path
import re
import tempfile

from arena.evidence.media import resolve_public_media_sources
from arena.reporting import bilingual
from arena.reporting.overview import load_roster, load_taxonomy, make_catalog
from arena.reporting.overview_pages import render_pages
from arena.reporting.search import write_discovery


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def report_navigation(catalog, relative, record):
    """Use the same authored identities as the site's category and case pages."""
    case = next(case for case in catalog['cases'] if case['id'] == record['scenarioId'])
    category = next((item for item in catalog['categories'] if item['id'] == case['categoryId']),
                    dict(label={'en': 'Unclassified records', 'zh-CN': '待分类记录'}))
    agent = next((item for item in catalog['coverage'] if record['agentId'] in item['recordAgentIds']), None)
    agent_label = agent['label'] if agent else record.get('presentation', {}).get('agentLabel',
                    {language: record['agentId'] for language in ('en', 'zh-CN')})
    prefix = '../' * len(relative.parent.parts)
    return {language: dict(categoryLabel=category['label'][language],
        searchRoutes={locale: relative.parent.as_posix() + '/' + locale + '.html' for locale in ('en', 'zh-CN')},
        categoryHref=prefix + case['categoryId'] + ('.zh-CN' if language == 'zh-CN' else '') + '.html',
        caseLabel=case['title'][language],
        caseHref=prefix + 'cases/' + case['id'] + ('/zh-CN.html' if language == 'zh-CN' else '/index.html'),
        agentLabel=agent_label[language],
        categoryId=case['categoryId'],
        categories=[dict(id=item['id'], label=item['label'][language],
            href=prefix + item['id'] + ('.zh-CN' if language == 'zh-CN' else '') + '.html')
            for item in catalog['categories'] if item['id'] != 'unclassified'],
        guideHref=prefix + ('articles.zh-CN.html' if language == 'zh-CN' else 'articles.html'),
        homeHref=prefix + ('zh-CN.html' if language == 'zh-CN' else 'index.html'))
        for language in ('en', 'zh-CN')}


def build_site(results_root, output, coverage_path=None, catalog_path=None):
    root = Path(results_root).resolve()
    output = Path(output).resolve()
    if not root.is_dir():
        raise ValueError('Results root must be an existing directory')
    if output.exists():
        raise ValueError('Site output already exists; choose a new directory')
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError('Site output must not overlap the results source')
    roster = load_roster(coverage_path)
    taxonomy = load_taxonomy(catalog_path)

    records = []
    withheld = []
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
        if taxonomy['scenarios'].get(record['scenarioId'], {}).get('publication') == 'withheld':
            withheld.append(relative.as_posix())
            continue
        records.append((path, relative, record))
    if not records:
        raise ValueError('No reviewed comparison record.json files found')

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='arena-site-', dir=output.parent) as temporary:
        staging = Path(temporary) / 'site'
        staging.mkdir()
        catalog = make_catalog(records, roster, taxonomy)
        for path, relative, record in records:
            bilingual.export_reports(path, staging / relative.parent, report_navigation(catalog, relative, record))
        for filename, content in render_pages(catalog).items():
            target = staging / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf8')
        (staging / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        static_assets = ('catalog.css', '404.html', '_redirects')
        for filename in static_assets:
            (staging / filename).write_bytes(Path(__file__).with_name(filename).read_bytes())
        # Synthetic examples stay public but are not promoted as live evaluations.
        excluded_routes = [row['path'] + '/' + locale + '.html'
                           for row in catalog['reports'] if row['origin'] != 'live'
                           for locale in ('en', 'zh-CN')]
        excluded_routes += ['cases/' + case['id'] + '/' + leaf
                            for case in catalog['cases'] if not case['live']
                            for leaf in ('index.html', 'zh-CN.html')]
        write_discovery(staging, excluded_routes)
        manifest = dict(schemaVersion=1, trialExecutions=0,
                        sources={relative.as_posix(): file_hash(path) for path, relative, _ in records},
                        excludedReplayResults=[p.relative_to(root).as_posix() for p in sorted(root.rglob('result.json'))],
                        excludedWithheldResults=withheld,
                        files={p.relative_to(staging).as_posix(): file_hash(p)
                               for p in sorted(staging.rglob('*')) if p.is_file()})
        (staging / 'site-manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
        if output.exists():
            raise ValueError('Site output appeared during build; preserve it')
        staging.rename(output)
    return dict(directory=str(output), comparisons=len(records), trialExecutions=0)
