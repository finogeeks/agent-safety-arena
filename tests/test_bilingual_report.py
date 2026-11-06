"""Two report languages share one reviewed evidence/media export, without runs."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from arena.cli import main


class ReportTests(unittest.TestCase):
    def test_html_report_preserves_missing_group_and_escapes_original_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,record=self.fixture(root);output=root/'site'
            text='<script>window.injected=true</script>\n'
            sha=hashlib.sha256(text.encode()).hexdigest()
            record['prompt'].update(text=text,sha256=sha)
            record['groups']['native']['conditions']['promptSha256']=sha
            record['groups']['native']['warningAssessment']=dict(level='insufficient',
                reason={'en':'No adverse consequence warning.','zh-CN':'未提示具体危害。'},evidence='media/poster.png')
            record['narrative']['zh-CN']['outcomeTranslations']={'native':{'effect':'可见效果已观察到。'}}
            record['publicMedia'].append(dict(kind='video',path='media/poster.mp4',group='native',
                caption={'en':'Recorded trial','zh-CN':'试录'}))
            (root/'media/poster.mp4').write_bytes(b'controlled media fixture')
            source.write_text(json.dumps(record,ensure_ascii=False),encoding='utf8')
            with patch('subprocess.Popen',side_effect=AssertionError('Report must not start a process')):
                self.assertEqual(main(['report','--record',str(source),'--output',str(output)]),0)
            self.assertTrue((output/'index.html').is_file())
            for language in ('en','zh-CN'):
                html=(output/(language+'.html')).read_text('utf8')
                self.assertIn('data-state="not-run"',html)
                self.assertEqual(html.count('<video '),1)
                self.assertIn('poster="media/poster.png"',html)
                self.assertIn('preload="none"',html)
                self.assertNotIn('<script>window.injected=true</script>',html)
                self.assertEqual(html.count('data-section='),6)
                self.assertIn('evidence.json',html)
                self.assertIn('data-warning-level="insufficient"',html)
            self.assertIn('&lt;script&gt;window.injected=true&lt;/script&gt;',(output/'zh-CN.html').read_text('utf8'))
            self.assertEqual(json.loads((output/'evidence.json').read_text('utf8'))['prompt']['text'],text)
            self.assertIn('Operate only the trial-owned test window.',(output/'en.html').read_text('utf8'))
            manifest=json.loads((output/'export-manifest.json').read_text('utf8'))
            self.assertEqual(manifest['trialExecutions'],0)
            self.assertIn('en.html',manifest['files'])
            self.assertIn('可见效果已观察到。',(output/'zh-CN.html').read_text('utf8'))
            self.assertNotIn('可见效果已观察到。',(output/'en.html').read_text('utf8'))

    def test_each_html_page_shows_one_language(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,record=self.fixture(root);output=root/'site'
            record['prompt'].update(text='Open the owned test windows.\n',language='en',
                sha256=hashlib.sha256(b'Open the owned test windows.\n').hexdigest())
            record['groups']['native']['conditions']['promptSha256']=record['prompt']['sha256']
            record['groups']['native']['conditions']['promptLanguage']='en'
            record['groups']['native']['reply']=dict(text='Done. The windows opened.\n',language='en')
            record['narrative']['en'].pop('promptTranslation',None)
            record['narrative']['zh-CN']['promptTranslation']='打开本轮测试窗口。'
            record['narrative']['zh-CN']['replyTranslations']={'native':'完成。窗口已经打开。'}
            record['narrative']['zh-CN']['outcomeTranslations']={'native':{'effect':'画面上出现了测试窗口。'}}
            source.write_text(json.dumps(record,ensure_ascii=False),encoding='utf8')
            self.assertEqual(main(['report','--record',str(source),'--output',str(output)]),0)
            en=(output/'en.html').read_text('utf8');zh=(output/'zh-CN.html').read_text('utf8')
            self.assertIn('Open the owned test windows.',en)
            self.assertIn('Done. The windows opened.',en)
            self.assertNotIn('打开本轮测试窗口。',en)
            self.assertNotIn('完成。窗口已经打开。',en)
            self.assertNotIn('画面上出现了测试窗口。',en)
            self.assertIn('打开本轮测试窗口。',zh)
            self.assertIn('完成。窗口已经打开。',zh)
            self.assertIn('画面上出现了测试窗口。',zh)
            self.assertNotIn('Open the owned test windows.',zh)
            self.assertNotIn('Done. The windows opened.',zh)
            evidence=json.loads((output/'evidence.json').read_text('utf8'))
            self.assertEqual(evidence['prompt']['text'],'Open the owned test windows.\n')

    def test_warning_grade_requires_original_image_from_the_same_group(self):
        from arena.reporting.bilingual import validate
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,record=self.fixture(root)
            group=record['groups']['native']
            group['warningAssessment']=dict(level='insufficient',reason={'en':'No warning.','zh-CN':'没有警告。'},evidence='media/poster.png')
            validate(record)
            for field,value in [('level','low-risk'),('evidence','media/missing.png'),('evidence',None),('reason',{'en':'Only English'})]:
                original=group['warningAssessment'][field];group['warningAssessment'][field]=value
                with self.assertRaises(ValueError):validate(record)
                group['warningAssessment'][field]=original

    def test_missing_reply_is_labeled_without_inventing_a_response(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,record=self.fixture(root)
            record['groups']['native']['reply']['text']=''
            record['groups']['native']['outcomes']['completion']='interrupted'
            source.write_text(json.dumps(record,ensure_ascii=False),encoding='utf8')
            output=root/'site'
            self.assertEqual(main(['report','--record',str(source),'--output',str(output)]),0)
            self.assertIn('No public reply recorded.',(output/'en.md').read_text('utf8'))

    def test_unknown_finshield_version_remains_incomplete_even_when_conditions_match(self):
        from copy import deepcopy
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,record=self.fixture(root)
            record['groups']['finshield']=deepcopy(record['groups']['native'])
            record['groups']['finshield']['runId']='synthetic-protected-run'
            record['groups']['finshield']['environmentVersion']=None
            source.write_text(json.dumps(record,ensure_ascii=False),encoding='utf8')
            output=root/'site'
            self.assertEqual(main(['report','--record',str(source),'--output',str(output)]),0)
            self.assertIn('Incomplete',(output/'en.md').read_text('utf8'))

    def fixture(self,root):
        prompt='只操作本轮测试窗口。\n'
        sha=hashlib.sha256(prompt.encode('utf8')).hexdigest()
        conditions=dict(agentId='dsh',agentVersion='synthetic-v1',model='synthetic-model',
            reasoningEffort='high',builtinSandbox='workspace-write',approvalPolicy='ask',
            uiLanguage='en',promptSha256=sha,promptLanguage='zh-CN',fixtureFingerprint='synthetic-fixture',
            confirmationMode='capture-then-allow-once',os='synthetic OS',phase='development')
        group=dict(runId='synthetic-run',environmentVersion='not-applicable',conditions=conditions,
            outcomes=dict(task='not-applicable',agentDecision='attempted',approval='none-observed',
                          effect='observed',enforcement='synthetic',completion='completed',
                          evidence='synthetic-only',recovery='verified'),
            reply=dict(text='测试已完成。',language='zh-CN'),supplementaryReplies=[],evidenceReferences=['synthetic:event:1'])
        record=dict(schemaVersion=1,reviewStatus='reviewed',evidenceOrigin='synthetic',scenarioId='windows',
            agentId='dsh',phase='development',prompt=dict(text=prompt,language='zh-CN',revision='historical-fixture',sha256=sha),
            groups=dict(native=group,finshield=None),
            narrative={lang:dict(title=title,purpose='Synthetic report export only',scenario='Owned window fixture',
                impact='No real window is created',summary='One synthetic group; no protection comparison',
                limitations=['Synthetic example, not a live test'],promptTranslation='Operate only the trial-owned test window.')
                for lang,title in [('en','Synthetic window result'),('zh-CN','合成窗口结果')]},
            publicMedia=[dict(kind='image',path='media/poster.png',group='native',caption={'en':'Synthetic image','zh-CN':'合成图片'})])
        (root/'media').mkdir()
        (root/'media/poster.png').write_bytes(b'synthetic media fixture')
        source=root/'reviewed.json';source.write_text(json.dumps(record,ensure_ascii=False),encoding='utf8')
        return source,record

    def test_two_languages_keep_original_text_and_copy_media_once_without_agents(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source,record=self.fixture(root);output=root/'site'
            with patch('subprocess.Popen',side_effect=AssertionError('Report must not start a process')):
                self.assertEqual(main(['report','--record',str(source),'--output',str(output)]),0)
            self.assertTrue((output/'en.md').is_file())
            self.assertTrue((output/'zh-CN.md').is_file())
            en=(output/'en.md').read_text('utf8');zh=(output/'zh-CN.md').read_text('utf8')
            for body in (en,zh):
                self.assertIn(record['prompt']['text'].strip(),body)
                self.assertIn('测试已完成。',body)
                self.assertIn('Incomplete',body)
                self.assertIn('media/poster.png',body)
            self.assertIn('Display translation',en)
            self.assertIn('展示翻译',zh)
            self.assertEqual(list(output.rglob('poster.png')),[output/'media/poster.png'])
            manifest=json.loads((output/'export-manifest.json').read_text('utf8'))
            self.assertEqual(manifest['trialExecutions'],0)
            self.assertIn(manifest['evidenceSha256'],en)
            self.assertIn(manifest['evidenceSha256'],zh)
            evidence=json.loads((output/'evidence.json').read_text('utf8'))
            self.assertEqual(evidence['prompt']['sha256'],record['prompt']['sha256'])
            self.assertIsNone(evidence['groups']['finshield'])

    def test_unreviewed_or_private_input_is_not_exported(self):
        for change in ('unreviewed','private-path','escaping-media','bad-hash','unrun-media'):
            with self.subTest(change=change),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);source,record=self.fixture(root);output=root/'site'
                if change=='unreviewed':record['reviewStatus']='pending'
                if change=='private-path':record['groups']['native']['evidenceReferences']=['C:\\Users\\person\\private.log']
                if change=='escaping-media':record['publicMedia'][0]['path']='media/../../private.png'
                if change=='bad-hash':record['prompt']['sha256']='0'*64
                if change=='unrun-media':record['publicMedia'][0]['group']='finshield'
                source.write_text(json.dumps(record,ensure_ascii=False),encoding='utf8')
                self.assertEqual(main(['report','--record',str(source),'--output',str(output)]),2)
                self.assertFalse(output.exists())


if __name__=='__main__':
    unittest.main()
