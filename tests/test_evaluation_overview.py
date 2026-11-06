"""The project overview summarizes evidence without creating new trial results."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from arena.reporting.site import build_site


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('href', 'src') and value and not value.startswith(('https:', '#')):
                self.paths.append(value.split('#')[0])


class EvaluationOverviewTests(unittest.TestCase):
    def record(self, results, identity='paired', *, agent='sample-agent', paired=True,
               origin='live', scenario='controlled-delete'):
        record = json.loads((ROOT / 'templates/reviewed-record.example.json').read_text('utf8'))
        record.update(agentId=agent, scenarioId=scenario, evidenceOrigin=origin)
        native = record['groups']['native']
        native['runId'] = agent + '-native-run'
        native['conditions']['agentId'] = agent
        native['conditions']['agentVersion'] = 'fixture-v2'
        native['conditions']['model'] = 'fixture-model'
        native['conditions']['builtinSandbox'] = 'workspace-write'
        native['conditions']['approvalPolicy'] = 'ask'
        native['interceptionAssessment'] = dict(status='not-blocked', basis='observed-effect',
            reason={'en': 'The controlled file disappeared.', 'zh-CN': '受控文件已消失。'},
            evidence=['controlled-observation'])
        native.pop('warningAssessment', None)
        record['groups']['finshield'] = deepcopy(native) if paired else None
        if paired:
            fs = record['groups']['finshield']
            fs.update(runId=agent + '-finshield-run', environmentVersion='FinShield fixture-7')
            fs['conditions']['builtinSandbox'] = 'danger-full-access'
            fs['interceptionAssessment'] = dict(status='blocked', basis='verified-postcondition',
                reason={'en': 'The controlled file remained present.', 'zh-CN': '受控文件仍然存在。'},
                evidence=['controlled-observation'], postcondition=dict(
                    effect={'en': 'loss of the controlled file', 'zh-CN': '受控文件丢失'},
                    attemptConfirmed=True, coverageConfirmed=True, baselineObserved=True,
                    observed=False, mechanism='unverified'))
        record['publicMedia'] = []
        for lang, title in [('en', 'Controlled deletion <fixture>'), ('zh-CN', '受控删除 <fixture>')]:
            record['narrative'][lang]['title'] = title
            record['narrative'][lang]['purpose'] = 'A controlled <script>fixture</script>.'
        path = results / scenario / agent / identity / 'record.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        return self.save(path, record)

    def save(self, path, record):
        path.write_text(json.dumps(record, ensure_ascii=False), encoding='utf8')
        return path, record

    def attach_gif(self,path,record):
        record['presentation']=dict(layout='comparison-v1',agentLabel={'en':'Sample Agent','zh-CN':'样例 Agent'},
            groups={name:dict(title={'en':name,'zh-CN':name},configuration=['controlled fixture'],
                toolSummary={'en':'Controlled result.','zh-CN':'受控结果。'}) for name in ('native','finshield')},
            overview=dict(media='media/comparison.gif',results={name:{'en':'Reviewed result.','zh-CN':'已审阅结果。'} for name in ('native','finshield')}),
            reproduction={'en':'Follow the controlled fixture procedure.','zh-CN':'按受控流程复现。'})
        media=path.parent/'media/comparison.gif';media.parent.mkdir(exist_ok=True);media.write_bytes(b'controlled original GIF fixture')
        record['publicMedia']=[dict(kind='image',path='media/comparison.gif',group='comparison',
            caption={'en':'Edited excerpt; speed adjusted.','zh-CN':'节选；已调整速度。'})]
        self.save(path,record)
        return media

    def test_counts_unique_live_runs_and_separates_reused_and_synthetic_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            self.record(results)
            self.record(results, identity='earlier', paired=False)
            self.record(results, agent='another-agent', paired=False)
            self.record(results, origin='synthetic', scenario='sample-only')
            build_site(results, root / 'site')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            counts = catalog['counts']
            self.assertEqual(catalog['schemaVersion'], 1)
            for key, expected in dict(liveScenarios=1, liveAgents=2, liveRuns=3,
                    pairedReports=1, formalReports=0, developmentReports=3,
                    languageStudyReports=0, syntheticReports=1, archivedReports=1).items():
                self.assertEqual(counts[key], expected, key)
            earlier = next(r for r in catalog['reports'] if r['path'].endswith('/earlier'))
            self.assertTrue(earlier['archived'])
            html = (root / 'site/methodology.html').read_text('utf8')
            self.assertIn('id="history"', html)
            self.assertIn('id="synthetic"', html)
            self.assertNotIn('100%', html)

    def test_preserves_scoped_assessments_unknowns_versions_and_mismatched_conditions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            path, record = self.record(results)
            record['groups']['native'].pop('interceptionAssessment')
            record['groups']['native']['warningAssessment'] = dict(level='unassessed',
                reason={'en': 'Incomplete observation.', 'zh-CN': '观察不完整。'}, evidence=None)
            self.save(path, record)
            self.record(results, agent='another-agent', paired=False)
            before = path.read_bytes()
            build_site(results, root / 'site')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            paired = next(r for r in catalog['reports'] if r['paired'])
            fs = paired['assessments']['finshield']
            self.assertEqual(fs['label']['zh-CN'], '已阻止受控文件丢失')
            self.assertIsNone(fs['warningLevel'])
            self.assertEqual(paired['assessments']['native']['state'], 'unassessed')
            self.assertEqual(paired['versions']['finshield'], 'FinShield fixture-7')
            self.assertEqual(paired['conditionStatus'], 'incomplete')
            single = next(r for r in catalog['reports'] if not r['paired'])
            self.assertEqual(single['assessments']['finshield']['state'], 'not-run')
            self.assertEqual(path.read_bytes(), before)
            html = (root / 'site/cases/controlled-delete/zh-CN.html').read_text('utf8')
            self.assertIn('受控文件丢失', html)
            self.assertNotIn('弹窗', html)
            self.assertNotIn('0.10.9', html)
            self.assertNotIn('<script>fixture</script>', html)

    def test_does_not_archive_a_report_with_conflicting_conditions_for_the_same_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            self.record(results)
            path, single = self.record(results, identity='different-conditions', paired=False)
            single['groups']['native']['conditions']['model'] = 'different-model'
            self.save(path, single)
            build_site(results, root / 'site')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            self.assertEqual(catalog['counts']['archivedReports'], 0)

    def test_both_languages_link_to_every_report_and_evidence_with_relative_assets(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'; site = root / 'site'
            self.record(results)
            self.record(results, identity='earlier', paired=False)
            build_site(results, site)
            for page in site.rglob('*.html'):
                html = page.read_text('utf8')
                parsed = Links(); parsed.feed(html)
                self.assertTrue(all((page.parent / p).is_file() for p in parsed.paths), (page, parsed.paths))
            self.assertIn('lang="en"', (site / 'index.html').read_text('utf8'))
            self.assertIn('lang="zh-CN"', (site / 'zh-CN.html').read_text('utf8'))
            self.assertIn('Earlier reports', (site / 'methodology.html').read_text('utf8'))
            manifest = json.loads((site / 'site-manifest.json').read_text('utf8'))
            for filename in ('catalog.json', 'catalog.css', 'en.html', 'zh-CN.html', 'interaction.html'):
                self.assertIn(filename, manifest['files'])

    def test_planned_agents_remain_visible_and_only_matching_model_enters_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            path, record = self.record(results, agent='codex-cli')
            for group in record['groups'].values():
                group['conditions'].update(model='deepseek-official/deepseek-v4-pro', reasoningEffort='high')
            record['groups']['finshield']['conditions']['reasoningEffort'] = 'low'
            self.save(path, record)
            self.record(results, agent='synthetic-only-agent', origin='synthetic', scenario='sample-only')
            build_site(results, root / 'site', ROOT / 'profiles/coverage.json')
            catalog = json.loads((root / 'site/catalog.json').read_text('utf8'))
            self.assertEqual(len(catalog['coverage']), 5)
            codex = next(r for r in catalog['coverage'] if r['id'] == 'codex-cli')
            self.assertEqual(codex['native']['scenarios'], 1)
            self.assertEqual(codex['native']['formalScenarios'], 0)
            self.assertEqual(codex['finshield']['scenarios'], 0)
            workbuddy = next(r for r in catalog['coverage'] if r['id'] == 'workbuddy')
            self.assertEqual(workbuddy['native']['reports'], [])
            html = (root / 'site/zh-CN.html').read_text('utf8')
            for label in ('WorkBuddy', 'OpenCode CLI', 'Claude CLI', 'DeepSeek Pro', '不评测模型能力'):
                self.assertIn(label, html)

    def test_home_stays_compact_with_100_cases_and_categories_paginate_by_scenario(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'; site = root / 'site'
            taxonomy = json.loads((ROOT / 'scenarios/catalog.json').read_text('utf8'))
            taxonomy['scenarios'] = {}
            for number in range(100):
                scenario = f'case-{number:03d}'
                self.record(results, scenario=scenario, paired=False)
                taxonomy['scenarios'][scenario] = dict(category='interaction',
                    title={'en': f'Case {number:03d}', 'zh-CN': f'场景 {number:03d}'})
            # Another Agent's report does not add a second scenario row.
            self.record(results, scenario='case-000', agent='second-agent', paired=False)
            path = root / 'catalog.json'; path.write_text(json.dumps(taxonomy), encoding='utf8')
            build_site(results, site, ROOT / 'profiles/coverage.json', path)
            home = (site / 'index.html').read_text('utf8')
            self.assertEqual(home.count('data-category='), 3)
            self.assertNotIn('data-case=', home)
            self.assertNotIn('<img', home)
            self.assertNotIn('Case 099', home)
            self.assertNotIn('domestic', home.lower())
            self.assertNotIn('international', home.lower())
            self.assertNotIn('Target:', home)
            self.assertNotIn('recorded scenario', home)
            seen = set()
            import re
            for number in range(1, 6):
                page = site / ('interaction' + (f'-{number}' if number > 1 else '') + '.html')
                text = page.read_text('utf8')
                ids = re.findall(r'data-case="([^"]+)"', text)
                self.assertEqual(len(ids), 20)
                self.assertTrue(seen.isdisjoint(ids))
                seen.update(ids)
                self.assertTrue(page.with_suffix('.zh-CN.html').is_file())
            self.assertEqual(len(seen), 100)
            self.assertFalse((site / 'interaction-6.html').exists())
            self.assertIn('No reviewed recordings yet', (site / 'data.html').read_text('utf8'))
            catalog = json.loads((site / 'catalog.json').read_text('utf8'))
            self.assertEqual(next(c for c in catalog['categories'] if c['id']=='interaction')['scenarios'], 100)
            self.assertTrue(all('region' not in agent for agent in catalog['coverage']))

    def test_duplicate_roster_aliases_fail_before_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root / 'results'
            self.record(results)
            roster = json.loads((ROOT / 'profiles/coverage.json').read_text('utf8'))
            roster['agents'][1]['recordAgentIds'].append('dsh')
            path = root / 'coverage.json'; path.write_text(json.dumps(roster), encoding='utf8')
            with self.assertRaises(ValueError):
                build_site(results, root / 'site', path)
            self.assertFalse((root / 'site').exists())

    def test_home_showcase_uses_original_live_gif_before_scores_and_links_to_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);results=root/'results';site=root/'site'
            path,record=self.record(results)
            media=self.attach_gif(path,record)
            taxonomy=json.loads((ROOT/'scenarios/catalog.json').read_text('utf8'))
            taxonomy['scenarios']['controlled-delete']=dict(category='data',title={'en':'Controlled deletion','zh-CN':'受控删除'})
            config=root/'taxonomy.json';config.write_text(json.dumps(taxonomy),encoding='utf8')
            before=path.read_bytes()
            build_site(results,site,catalog_path=config)
            html=(site/'index.html').read_text('utf8')
            prefix='controlled-delete/sample-agent/paired/'
            self.assertLess(html.index('id="real-tests"'),html.index('id="agent-scores"'))
            self.assertIn('<img',html)
            self.assertIn(prefix+'media/comparison.gif',html)
            for target in ('en.html#section-3','evidence.json','en.html#section-6'):
                self.assertIn('href="'+prefix+target+'"',html)
            self.assertEqual(html.count('data-category='),3)
            self.assertEqual(html.count('data-media-state="empty"'),2)
            self.assertNotIn('category-score-table',html)
            self.assertEqual(media.read_bytes(),(site/prefix/'media/comparison.gif').read_bytes())
            self.assertEqual(path.read_bytes(),before)
            catalog=json.loads((site/'catalog.json').read_text('utf8'))
            self.assertTrue(catalog['reports'][0]['hasReproduction'])
            record['presentation'].pop('reproduction')
            self.save(path,record)
            build_site(results,root/'without-reproduction',catalog_path=config)
            html=(root/'without-reproduction/index.html').read_text('utf8')
            self.assertNotIn('href="'+prefix+'en.html#section-6"',html)
            self.assertIn('Reproduction unavailable',html)

    def test_missing_or_synthetic_media_keeps_three_honest_empty_slots(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);results=root/'results';site=root/'site'
            self.record(results)
            path,record=self.record(results,origin='synthetic',scenario='window-flood')
            self.attach_gif(path,record)
            build_site(results,site)
            html=(site/'index.html').read_text('utf8')
            self.assertIn('id="real-tests"',html)
            self.assertEqual(html.count('data-media-state="empty"'),3)
            self.assertNotIn('<img',html)
            self.assertNotIn('href="#"',html)
            self.assertIn('No media available',html)


if __name__ == '__main__':
    unittest.main()
