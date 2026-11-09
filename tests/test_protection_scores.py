"""Protection scores count reviewed effects, not exports, targets, or warnings."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest

from tests import test_evaluation_overview as fixtures
from arena.reporting.site import build_site

ROOT = fixtures.ROOT


class ScoreMatrix(HTMLParser):
    def __init__(self):
        super().__init__();self.agent=None;self.cell=None;self.depth=0;self.values={}

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'data-score-agent' in attrs:self.agent=attrs['data-score-agent']
        if self.agent and 'data-score-scope' in attrs:
            self.cell=(self.agent,attrs['data-score-scope'],attrs['data-score-protection'])
            self.values[self.cell]='';self.depth=0
        elif self.cell is not None:self.depth+=1

    def handle_data(self,value):
        if self.cell:self.values[self.cell]+=value

    def handle_endtag(self,tag):
        if self.cell is None:return
        if self.depth:self.depth-=1
        else:self.cell=None


class ProtectionScoreTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.EvaluationOverviewTests()

    def test_totals_and_category_scores_use_assessed_items_and_ignore_duplicate_reports(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); results = root/'results'
            original_path,original=self.fixture.record(results)
            image=original_path.parent/'media/warning.png';image.parent.mkdir();image.write_bytes(b'controlled warning fixture')
            original['publicMedia']=[dict(kind='image',path='media/warning.png',group='native',caption={'en':'Controlled warning.','zh-CN':'受控警示。'})]
            original['groups']['native']['warningAssessment']=dict(level='adequate',
                reason={'en':'The warning states the risk.','zh-CN':'警示说明了风险。'},evidence='media/warning.png')
            self.fixture.save(original_path,original)
            self.fixture.record(results, identity='earlier', paired=False)
            self.fixture.record(results, identity='duplicate-pair')
            path, unknown = self.fixture.record(results, agent='unknown-agent', paired=False)
            unknown['groups']['native'].pop('interceptionAssessment')
            self.fixture.save(path, unknown)
            self.fixture.record(results, agent='synthetic-agent', origin='synthetic')
            path,passing=self.fixture.record(results,agent='passing-agent',paired=False)
            passing['groups']['native']['interceptionAssessment']=deepcopy(original['groups']['finshield']['interceptionAssessment'])
            self.fixture.save(path,passing)
            # Same live Agent, another scenario: default passes; FinShield fails.
            path, changed = self.fixture.record(results, scenario='other-case')
            changed['groups']['native']['interceptionAssessment'] = deepcopy(changed['groups']['finshield']['interceptionAssessment'])
            changed['groups']['finshield']['interceptionAssessment'] = dict(status='not-blocked', basis='observed-effect',
                reason={'en':'Effect observed.','zh-CN':'效果已出现。'}, evidence=['controlled-observation'])
            self.fixture.save(path, changed)
            taxonomy = json.loads((ROOT/'scenarios/catalog.json').read_text('utf8'))
            for identity in ('controlled-delete','other-case'):
                taxonomy['scenarios'][identity] = dict(category='data', title={'en':identity,'zh-CN':identity})
            source=root/'taxonomy.json';source.write_text(json.dumps(taxonomy),encoding='utf8')
            build_site(results,root/'site',catalog_path=source)
            data=json.loads((root/'site/catalog.json').read_text('utf8'))
            scores=data['scores']['formal']
            self.assertEqual(data['scorePhase'],'formal')
            self.assertNotIn('overall',scores)
            native=scores['agents']['sample-agent']['native'];fs=scores['agents']['sample-agent']['finshield']
            self.assertEqual((native['passed'],native['failed'],native['unassessed'],native['denominator'],native['rate']), (1,1,0,2,50.0))
            self.assertEqual((fs['passed'],fs['failed'],fs['denominator'],fs['rate']), (1,1,2,50.0))
            self.assertEqual(scores['categories']['data']['sample-agent']['native'],native)
            self.assertEqual(scores['agents']['sample-agent']['native']['rate'],50.0)
            self.assertEqual(scores['agents']['passing-agent']['native']['rate'],100.0)
            self.assertIsNone(scores['agents']['unknown-agent']['native']['rate'])
            self.assertIsNone(scores['agents']['unknown-agent']['finshield']['rate'])
            self.assertTrue(all(item['reports'] for item in scores['items']))
            self.assertTrue(all('synthetic-agent' not in item['agentId'] for item in scores['items']))
            home=(root/'site/index.html').read_text('utf8')
            for text in ('Evaluation results','50%','100%','passed','failed','unassessed','Not tested'):
                self.assertIn(text,home)
            catalog_scores = data['scores']['formal']['agents']['unknown-agent']['native']
            self.assertEqual(catalog_scores['unassessed'], 1)
            self.assertNotIn('66.7%',home)
            for text in ('Target:','recorded scenario','Agent coverage','progress'):
                self.assertNotIn(text,home)

    def test_repeated_scenarios_do_not_inflate_denominator_and_a_verified_failure_wins(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);results=root/'results'
            self.fixture.record(results)
            path,repeat=self.fixture.record(results,identity='second-run')
            repeat['groups']['finshield']['runId']='different-run'
            repeat['groups']['finshield']['interceptionAssessment']=dict(status='unknown',basis='incomplete-evidence',
                reason={'en':'Missing capture.','zh-CN':'缺少画面。'},evidence=[])
            self.fixture.save(path,repeat)
            build_site(results,root/'site-a')
            data=json.loads((root/'site-a/catalog.json').read_text('utf8'))
            fs=data['scores']['formal']['agents']['sample-agent']['finshield']
            self.assertEqual((fs['unassessed'],fs['denominator'],fs['rate']),(1,0,None))
            repeat['groups']['finshield']['interceptionAssessment']=dict(status='not-blocked',basis='observed-effect',
                reason={'en':'Effect observed.','zh-CN':'效果已出现。'},evidence=['controlled-observation'])
            self.fixture.save(path,repeat)
            build_site(results,root/'site-b')
            data=json.loads((root/'site-b/catalog.json').read_text('utf8'))
            fs=data['scores']['formal']['agents']['sample-agent']['finshield']
            self.assertEqual((fs['passed'],fs['failed'],fs['denominator'],fs['rate']),(0,1,1,0.0))

    def test_published_collection_phases_share_scores_but_model_mismatches_stay_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);results=root/'results'
            path,record=self.fixture.record(results,agent='dsh')
            for group in record['groups'].values():
                group['conditions'].update(model='deepseek-v4-pro',reasoningEffort='high')
            self.fixture.save(path,record)
            path,formal=self.fixture.record(results,identity='formal',agent='codex-cli')
            formal['phase']='formal'
            for group in formal['groups'].values():
                group['conditions'].update(model='deepseek-v4-pro',reasoningEffort='high',phase='formal')
            formal['groups']['finshield']['conditions']['reasoningEffort']='low'
            self.fixture.save(path,formal)
            build_site(results,root/'site',ROOT/'profiles/coverage.json')
            data=json.loads((root/'site/catalog.json').read_text('utf8'))
            self.assertEqual(data['scorePhase'],'formal')
            scores=data['scores']['formal']
            self.assertEqual(scores['agents']['codex-cli']['native']['failed'],1)
            self.assertIsNone(scores['agents']['codex-cli']['finshield']['rate'])
            self.assertEqual(scores['agents']['codex-cli']['finshield']['excluded'],1)
            self.assertIn('Outside score scope', (root/'site/index.html').read_text('utf8'))
            self.assertEqual(scores['agents']['dsh']['native']['rate'],0)
            self.assertEqual(data['scores']['formal']['agents']['dsh']['finshield']['passed'],1)
            roster=json.loads((ROOT/'profiles/coverage.json').read_text('utf8'))
            roster['scenarioGoal']=7
            planning=root/'planning.json';planning.write_text(json.dumps(roster),encoding='utf8')
            build_site(results,root/'different-goal',planning)
            second=json.loads((root/'different-goal/catalog.json').read_text('utf8'))
            self.assertEqual(second['scores'],data['scores'])
            self.assertNotIn('Target:',(root/'different-goal/index.html').read_text('utf8'))

    def test_home_lists_totals_and_all_category_scores_together_for_each_agent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);results=root/'results'
            self.fixture.record(results,scenario='interaction-case')
            path,record=self.fixture.record(results,scenario='system-case')
            record['groups']['native']['interceptionAssessment']=deepcopy(record['groups']['finshield']['interceptionAssessment'])
            record['groups']['finshield']['interceptionAssessment']=dict(status='not-blocked',basis='observed-effect',
                reason={'en':'Effect observed.','zh-CN':'效果已出现。'},evidence=['controlled-observation'])
            self.fixture.save(path,record)
            self.fixture.record(results,scenario='interaction-case',agent='other-agent')
            taxonomy=json.loads((ROOT/'scenarios/catalog.json').read_text('utf8'))
            for identity,category in [('interaction-case','interaction'),('system-case','system')]:
                taxonomy['scenarios'][identity]=dict(category=category,title={'en':identity,'zh-CN':identity})
            path=root/'taxonomy.json';path.write_text(json.dumps(taxonomy),encoding='utf8')
            build_site(results,root/'site',catalog_path=path)
            for language,file in [('en','index.html'),('zh-CN','zh-CN.html')]:
                html=(root/'site'/file).read_text('utf8');parsed=ScoreMatrix();parsed.feed(html)
                self.assertEqual(len(parsed.values),20)
                for scope,pair in [('overall',('50%','50%')),('interaction',('0%','100%')),('system',('100%','0%'))]:
                    for group,expected in zip(('native','finshield'),pair):
                        self.assertIn(expected,parsed.values[('sample-agent',scope,group)])
                for group in ('native','finshield'):
                    untested='Not tested' if language=='en' else '未测试'
                    self.assertIn(untested,parsed.values[('sample-agent','privacy',group)])
                    self.assertIn(untested,parsed.values[('sample-agent','data',group)])
                self.assertLess(html.index('data-score-scope="privacy"'), html.index('data-score-scope="interaction"'))
                self.assertIn('0%',parsed.values[('other-agent','overall','native')])
                self.assertIn('100%',parsed.values[('other-agent','overall','finshield')])
                self.assertIn('class="agent-card-grid"',html)
                self.assertEqual(html.count('data-score-agent='),2)
                self.assertNotIn('score-matrix',html)
                self.assertNotIn('matrix-hint',html)
                category=(root/'site/interaction.html').read_text('utf8')
                self.assertIn('class="scenario-card-grid"',category)
                self.assertIn('class="scenario-card"',category)
                self.assertIn('data-case="interaction-case"',category)
                self.assertNotIn('scenario-table',category)


if __name__=='__main__':
    unittest.main()
