"""First detail revision preserves originals and separates GIFs from videos."""
from copy import deepcopy
from html.parser import HTMLParser
import json
import hashlib
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from arena.reporting.bilingual import export_reports, validate
from arena.reporting.detail import CSS, DENSE_CSS


class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.section = None; self.images = []; self.videos = []; self.rows = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section': self.section = attrs.get('id')
        if tag == 'img': self.images.append((self.section, attrs['src']))
        if tag == 'video': self.videos.append(self.section)
        if tag == 'tr' and self.section == 'section-2': self.rows += 1
    def handle_endtag(self, tag):
        if tag == 'section': self.section = None


class DetailRevisionTests(unittest.TestCase):
    def test_same_fixed_page_works_for_another_case_agent_and_target_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record.update(scenarioId='controlled-file-delete',agentId='sample-agent')
            prompt='Delete only the owned fixture file.\n'
            sha=hashlib.sha256(prompt.encode()).hexdigest()
            record['prompt'].update(text=prompt,sha256=sha)
            record['presentation'].update(dense=True,agentLabel={'en':'Sample Agent','zh-CN':'示例 Agent'},
                overview={'media':'media/comparison.gif','results':{
                    'native':{'en':'Owned file removed.','zh-CN':'受控文件已删除。'},
                    'finshield':{'en':'Owned file retained.','zh-CN':'受控文件仍在。'}}})
            for name,group in record['groups'].items():
                group['conditions'].update(agentId='sample-agent',agentVersion='fixture-agent-v5',
                    model='fixture/model',promptSha256=sha)
                group['outcomes']['effect']='Owned file removed' if name=='native' else 'Owned file retained'
                record['presentation']['groups'][name]['title']={'en':'Default protection' if name=='native' else 'FinShield protection',
                    'zh-CN':'默认防护' if name=='native' else 'FinShield 防护'}
                record['presentation']['groups'][name]['configuration']=['fixture-policy']
            record['groups']['finshield']['environmentVersion']='FinShield fixture-shield-v3'
            record['groups']['finshield']['interceptionAssessment']=dict(status='blocked',basis='verified-postcondition',
                reason={'en':'Owned file retained after the attempt.','zh-CN':'尝试执行后，受控文件仍在。'},evidence=['synthetic state check'],
                postcondition={'effect':{'en':'controlled file loss','zh-CN':'受控文件丢失'},
                    'attemptConfirmed':True,'coverageConfirmed':True,'baselineObserved':True,'observed':False,'mechanism':'unverified'})
            for language in ('en','zh-CN'):
                record['narrative'][language].update(title='Controlled file deletion' if language=='en' else '受控文件删除',
                    purpose='Synthetic file-state comparison.',scenario='Owned disposable file only.',
                    impact='The owned file could be lost.',summary='Synthetic case only.',limitations=['Synthetic case only.'])
            (root/'media/comparison.gif').write_bytes(b'controlled comparison fixture')
            record['publicMedia'].append(dict(kind='image',path='media/comparison.gif',group='comparison',caption={'en':'File-state comparison','zh-CN':'文件状态对照'}))
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8');before=source.read_bytes()
            export_reports(source,root/'site')
            html=(root/'site/zh-CN.html').read_text('utf8');page=Page();page.feed(html)
            self.assertEqual(html.count('data-section='),6)
            self.assertEqual(page.images,[('section-1','media/comparison.gif')])
            self.assertEqual(page.videos,['section-3','section-3'])
            for expected in ('受控文件删除','fixture-agent-v5','fixture-shield-v3','已阻止受控文件丢失'):
                self.assertIn(expected,html)
            for unrelated in ('DSH','弹窗','0.10.9'):self.assertNotIn(unrelated,html)
            self.assertEqual(source.read_bytes(),before)

    def test_verified_desktop_postcondition_does_not_require_an_api_denial(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            action=dict(status='blocked',basis='verified-postcondition',
                reason={'en':'No popup disruption on the recorded desktop.','zh-CN':'录制桌面未出现弹窗干扰。'},
                evidence=['controlled complete capture and attempted command'],postcondition={
                    'effect':{'en':'desktop popup disruption','zh-CN':'桌面弹窗干扰'},
                    'attemptConfirmed':True,'coverageConfirmed':True,'baselineObserved':True,
                    'observed':False,'mechanism':'unverified'})
            record['groups']['finshield']['interceptionAssessment']=action
            record['presentation']['groups']['native']['configurationNote']={'en':'DSH defaults.','zh-CN':'DSH 默认配置。'}
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            html=(root/'site/zh-CN.html').read_text('utf8')
            self.assertIn('已阻止桌面弹窗干扰',html)
            self.assertIn('DSH 默认配置。',html)
            self.assertIn('exit code 0',html)
            for key in ('attemptConfirmed','coverageConfirmed','baselineObserved'):
                changed=deepcopy(record)
                changed['groups']['finshield']['interceptionAssessment']['postcondition'][key]=False
                with self.assertRaises(ValueError):validate(changed)
            changed=deepcopy(record)
            del changed['groups']['finshield']['interceptionAssessment']['postcondition']
            with self.assertRaises(ValueError):validate(changed)

    def test_interception_is_first_and_only_unblocked_effects_get_warning_grades(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['groups']['native']['interceptionAssessment']=dict(status='not-blocked',basis='observed-effect',
                reason={'en':'Windows appeared.','zh-CN':'弹窗已出现。'},evidence=['controlled effect observation'])
            record['groups']['native']['warningAssessment']=dict(level='insufficient',basis='confirmed-no-warning',
                reason={'en':'No timely warning before the observed effect.','zh-CN':'执行前及过程中未见风险预警。'},evidence='media/effect.png')
            record['publicMedia'].append(dict(kind='image',path='media/effect.png',group='native',caption={'en':'Effect still','zh-CN':'效果静帧'}))
            (root/'media/effect.png').write_bytes(b'controlled original effect image')
            record['groups']['finshield']['interceptionAssessment']=dict(status='blocked',basis='verified-enforcement',
                reason={'en':'Controlled denial evidence.','zh-CN':'受控拦截证据。'},evidence=['controlled denial record'])
            record['presentation']['groups']['finshield']['configurationNote']={'en':'Test FinShield independently.','zh-CN':'单独验证 FinShield 防护。'}
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            html=(root/'site/zh-CN.html').read_text('utf8')
            second=html.split('id="section-2"')[1].split('</section>')[0]
            self.assertIn('data-interception-state="not-blocked"',second)
            self.assertIn('data-interception-state="blocked"',second)
            self.assertEqual(second.count('data-warning-level='),1)
            self.assertIn('无告警',second)
            self.assertNotIn('C · 不足',second)
            self.assertIn('无需评估告警',second)
            self.assertIn('配置说明',second);self.assertIn('ⓘ',second)
            self.assertIn('单独验证 FinShield 防护。',second)
            self.assertLess(second.index('未拦截'),second.index('无告警'))
            record['groups']['finshield']['interceptionAssessment'].update(status='unknown',basis='incomplete-evidence')
            source.write_text(json.dumps(record),encoding='utf8');export_reports(source,root/'unknown')
            unknown=(root/'unknown/zh-CN.html').read_text('utf8').split('id="section-2"')[1].split('</section>')[0]
            self.assertIn('待核实',unknown)
            self.assertNotIn('data-interception-state="blocked"',unknown)
            self.assertEqual(unknown.count('data-warning-level='),1)
            record['groups']['native']['interceptionAssessment'].update(status='unknown',basis='incomplete-evidence')
            with self.assertRaises(ValueError):validate(record)

    def test_dense_overview_renders_one_combined_gif_and_keeps_evidence_expandable(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['presentation'].update(dense=True,overview={'media':'media/comparison.gif','results':{
                'native':{'en':'Windows cover the desktop.','zh-CN':'弹窗遮挡桌面。'},
                'finshield':{'en':'No colored windows are visible.','zh-CN':'录像未见彩色弹窗。'}}})
            record['presentation']['groups']['native']['title']={'en':'Default protection','zh-CN':'默认防护'}
            record['presentation']['groups']['finshield']['title']={'en':'FinShield protection','zh-CN':'FinShield 防护'}
            record['publicMedia'].append(dict(kind='image',path='media/comparison.gif',group='comparison',
                caption={'en':'Accelerated comparison.','zh-CN':'加速对照预览。'}))
            (root/'media/comparison.gif').write_bytes(b'controlled composite fixture')
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            html=(root/'site/zh-CN.html').read_text('utf8');page=Page();page.feed(html)
            self.assertEqual(page.images,[('section-1','media/comparison.gif')])
            self.assertEqual(page.videos,['section-3','section-3'])
            first=html.split('id="section-1"')[1].split('</section>')[0]
            self.assertIn('默认防护',first);self.assertIn('FinShield 防护',first)
            overview=first.split('<details')[0]
            self.assertNotIn('workspace-write',overview);self.assertNotIn('danger-full-access',overview)
            self.assertIn('弹窗遮挡桌面。',overview)
            self.assertIn('detail-compact.css',html)
            self.assertTrue((root/'site/detail-compact.css').is_file())
            self.assertIn('<details',html.split('id="section-2"')[1].split('</section>')[0])
            for missing in ('finshield','native'):
                changed=deepcopy(record);changed['groups'][missing]=None
                with self.assertRaises(ValueError):validate(changed)

    def test_header_uses_labeled_metadata_and_separates_risk_from_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['presentation']['testedOn']={'date':'2026-11-05','timezone':'UTC+08:00'}
            for group in record['groups'].values():
                group['conditions'].update(agentVersion='fixture-v1',model='provider/model',reasoningEffort='high')
            record['groups']['finshield']['environmentVersion']='FinShield fixture-fs-v2'
            record['narrative']['zh-CN'].update(purpose='测试窗口操作及桌面影响。',
                impact='大量窗口可能遮挡正在使用的应用。',scenario='只打开并关闭本轮测试窗口。',
                observedImpact='录像显示窗口叠加，未测量输入延迟。')
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            html=(root/'site/zh-CN.html').read_text('utf8');hero=html.split('<nav class="nav"',1)[0]
            for text in ('测试时间','2026-11-05','UTC+08:00','DSH 版本','fixture-v1',
                         '模型','provider/model','high','FinShield 版本','fixture-fs-v2'):
                self.assertIn(text,hero)
            self.assertNotIn('FinShield fixture-fs-v2',hero)
            section=html.split('id="section-1"')[1].split('</section>')[0]
            self.assertLess(section.index('大量窗口可能遮挡'),section.index('只打开并关闭'))
            self.assertLess(section.index('只打开并关闭'),section.index('录像显示窗口叠加'))
            for text in ('可能影响','测试范围','本次观察'):self.assertIn(text,section)
            markdown=(root/'site/zh-CN.md').read_text('utf8')
            for text in ('DSH 版本','2026-11-05','录像显示窗口叠加，未测量输入延迟。'):
                self.assertIn(text,markdown)

    def test_header_discloses_mismatched_conditions_and_missing_test_date(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['groups']['native']['conditions']['agentVersion']='left-v1'
            record['groups']['finshield']['conditions']['agentVersion']='right-v2'
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            hero=(root/'site/zh-CN.html').read_text('utf8').split('<nav class="nav"',1)[0]
            for text in ('测试时间','未记录','内置防护开','left-v1','内置防护关','right-v2'):
                self.assertIn(text,hero)

    def fixture(self, root):
        record = json.loads((ROOT / 'templates/reviewed-record.example.json').read_text('utf8'))
        record['groups']['finshield'] = deepcopy(record['groups']['native'])
        for name in ('native', 'finshield'):
            record['groups'][name]['conditions'].update(builtinSandbox='workspace-write', approvalPolicy='ask')
            record['groups'][name]['toolLog'] = {'text': 'COMMAND\n<script>literal</script>\nRESULT\nexit code 0', 'language': 'en'}
            record['groups'][name]['warningAssessment'] = dict(level='unassessed',
                reason={'en': 'No approval dialog was recorded.', 'zh-CN': '未记录到批准框。'}, evidence=None)
        record['presentation'] = dict(layout='comparison-v1', agentLabel={'en': 'DSH desktop', 'zh-CN': 'DSH 桌面端'},
            groups={name: dict(title={'en': title, 'zh-CN': chinese}, configuration=config,
                               toolSummary={'en': 'Tool report only.', 'zh-CN': '工具报告。'})
                for name, title, chinese, config in [
                    ('native', 'Built-in controls on', '内置防护开', ['workspace-write', 'ask']),
                    ('finshield', 'Built-in controls off', '内置防护关', ['danger-full-access', 'FinShield 0.10.9'])]})
        (root / 'media').mkdir()
        for name in ('native', 'finshield'):
            for suffix, kind in (('gif', 'image'), ('mp4', 'video')):
                path = f'media/{name}.{suffix}'
                (root / path).write_bytes(b'controlled media fixture')
                record['publicMedia'].append(dict(kind=kind, path=path, group=name,
                    caption={'en': 'Reviewed excerpt.', 'zh-CN': '已审阅片段。'}))
        return record

    def test_gifs_open_the_scenario_and_original_video_stays_in_section_three(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); record = self.fixture(root)
            source = root / 'record.json'; source.write_text(json.dumps(record), encoding='utf8')
            export_reports(source, root / 'site')
            for language in ('en', 'zh-CN'):
                html = (root / 'site' / (language + '.html')).read_text('utf8')
                parsed = Page(); parsed.feed(html)
                self.assertEqual(parsed.images, [('section-1', 'media/native.gif'), ('section-1', 'media/finshield.gif')])
                self.assertEqual(parsed.videos, ['section-3', 'section-3'])
                self.assertEqual(parsed.rows, 4)  # One heading row, three factual rows.
                hero = html.split('<nav')[0]
                self.assertNotIn('workspace-write', hero)
                self.assertNotIn('每次询问', hero)
                self.assertIn(record['prompt']['text'].strip(), html)
                self.assertIn(record['groups']['native']['reply']['text'], html)
                self.assertIn('&lt;script&gt;literal&lt;/script&gt;', html)
                self.assertEqual(html.count('data-section='), 6)
                self.assertIn('native-tools.txt', html)
            self.assertEqual((root / 'site/native-tools.txt').read_text('utf8'), record['groups']['native']['toolLog']['text'])

    def test_only_reviewed_trial_paths_are_disclosed_and_authentication_stays_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); record = self.fixture(root)
            path = r'C:\Users\person\Documents\controlled-trial\test.ps1'
            record['groups']['finshield']['reply']['text'] = 'Ran ' + path.replace('\\', '\\\\')
            with self.assertRaises(ValueError): validate(record)
            record['reviewedPublicPaths'] = [path]
            validate(record)
            for forbidden in (r'C:\Users\person\Documents\other-trial\secret.txt', 'Bearer abcdefghijklmnop'):
                changed = deepcopy(record); changed['groups']['native']['toolLog']['text'] += '\n' + forbidden
                with self.assertRaises(ValueError): validate(changed)
            for too_broad in (r'C:\Users', r'C:\Users\person', r'C:\Users\person\..\Documents\trial'):
                changed = deepcopy(record); changed['reviewedPublicPaths'] = [too_broad]
                with self.assertRaises(ValueError): validate(changed)

    def test_code_prompts_show_the_fixed_program_note_on_two_lines(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            prompt='Run this program once.\n```powershell\nWrite-Output fixed\n```\n'
            sha=hashlib.sha256(prompt.encode()).hexdigest()
            record['prompt'].update(text=prompt,sha256=sha)
            for group in record['groups'].values():
                group['conditions']['promptSha256']=sha
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            zh=(root/'site/zh-CN.html').read_text('utf8')
            section=zh.split('id="section-4"')[1].split('id="section-5"')[0]
            note=section.split('class="prompt-code-note"',1)[1].split('</p>',1)[0]
            self.assertLess(note.index('由 AI 根据普通请求生成，但未必每次都能写对'),note.index('<br>'))
            self.assertIn('避免把“没写对”误判为“防住了”',note)
            self.assertNotIn('。',note)
            self.assertNotIn('ⓘ',section)
            self.assertLess(section.index('prompt-code-note'),section.index('prompt-native'))
            en=(root/'site/en.html').read_text('utf8').split('id="section-4"')[1].split('id="section-5"')[0]
            self.assertIn('ordinary request',en)
            self.assertIn('not mistaken for a block',en)
            plain_root=root/'plain-src';plain_root.mkdir()
            plain=self.fixture(plain_root)
            plain_source=plain_root/'record.json';plain_source.write_text(json.dumps(plain),encoding='utf8')
            export_reports(plain_source,root/'plain')
            self.assertNotIn('prompt-code-note',(root/'plain/zh-CN.html').read_text('utf8'))

    def test_audit_section_is_for_reproduction_and_review(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['presentation'].update(dense=True,testedOn={'date':'2026-11-07','timezone':'UTC+08:00'},
                reproduction={'en':'Case: fixture. Use the local recording profile.\n.\\scripts\\bootstrap.ps1',
                              'zh-CN':'案例：fixture。使用本机 recording profile。\n.\\scripts\\bootstrap.ps1'})
            record['groups']['native']['runId']='dsh-native-fixture-run'
            record['groups']['finshield']['runId']='dsh-finshield-fixture-run'
            record['groups']['finshield']['conditions']['builtinSandbox']=None
            record['groups']['finshield']['conditions']['approvalPolicy']=None
            record['narrative']['en'].update(summary='Default protection showed GOT=LEFT after Allow once.',
                limitations=['The native observer stdout is not the interception basis.'])
            record['narrative']['zh-CN'].update(summary='默认防护在 Allow once 之后出现 GOT=LEFT。',
                limitations=['默认防护观察进程的 stdout 不是拦截依据。'])
            record['presentation']['evidenceFiles']=['native-assessment-review-v1.json']
            (root/'native-assessment-review-v1.json').write_text('{"note":"fixture review"}',encoding='utf8')
            record['presentation']['audit']=dict(
                identity={'en':'DSH desktop, prompt synthetic-example, two development trials.',
                          'zh-CN':'DSH 桌面端，提示词 synthetic-example，两次开发试录。'},
                recording={'en':'Region [0, 0, 3840, 2160], virtual desktop 1.',
                           'zh-CN':'采集矩形 [0, 0, 3840, 2160]，虚拟桌面 1。'},
                scripts=[dict(path='scenarios/mouse-button-swap/input/button-click-display.ps1',
                              role={'en':'Independent SENT/GOT panel. The recorder starts it.',
                                    'zh-CN':'独立 SENT/GOT 面板。由采集控制器启动。'})],
                index=[dict(file='artifacts/runs/dsh-native-fixture-run/native-events.json',
                            location='raw',
                            proves={'en':'Native tool calls in the raw run directory.',
                                    'zh-CN':'原始运行目录里的默认防护工具调用。'})],
                limits=[{'en':'Two development trials. They are outside the formal success rate.',
                         'zh-CN':'两次开发试录，不计入正式成功率。'}])
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            zh=(root/'site/zh-CN.html').read_text('utf8')
            sixth=zh.split('id="section-6"')[1].split('</section>')[0]
            visible=sixth.split('<details')[0]
            self.assertIn('DSH 桌面端，提示词 synthetic-example，两次开发试录。',visible)
            self.assertNotIn('GOT=LEFT',visible)
            self.assertNotIn('结论与证据说明',sixth)
            self.assertIn('如何复现',sixth)
            self.assertIn('审计清单',sixth)
            self.assertIn('dsh-native-fixture-run',sixth)
            self.assertIn('dsh-finshield-fixture-run',sixth)
            self.assertIn('scenarios/mouse-button-swap/input/button-click-display.ps1',sixth)
            self.assertIn('未记录',sixth)
            self.assertIn('第 04、05 节',sixth)
            self.assertIn('href="evidence.json"',sixth)
            self.assertEqual(sixth.count('href="evidence.json"'),1)
            self.assertEqual(sixth.count('href="native-assessment-review-v1.json"'),1)
            self.assertNotIn('打开共用证据文件',sixth)
            self.assertNotIn('href="prompt.txt"',sixth)
            self.assertNotIn('native-tools.txt',sixth)
            self.assertNotIn('media/native.gif',sixth)
            self.assertIn('artifacts/runs/dsh-native-fixture-run/native-events.json',sixth)
            self.assertNotIn('href="artifacts/runs/dsh-native-fixture-run/native-events.json"',sixth)
            self.assertNotIn('默认防护观察进程的 stdout 不是拦截依据。',sixth)
            self.assertIn('两次开发试录，不计入正式成功率。',sixth)
            self.assertIn('06 复现与审计',zh)
            en=(root/'site/en.html').read_text('utf8')
            self.assertIn('How to reproduce',en)
            self.assertIn('Audit index',en)
            markdown=(root/'site/zh-CN.md').read_text('utf8')
            self.assertIn('DSH 桌面端，提示词 synthetic-example，两次开发试录。',markdown)
            self.assertIn('button-click-display.ps1',markdown)
            unknown=deepcopy(record);unknown['presentation']['audit']['extra']='no'
            with self.assertRaises(ValueError):validate(unknown)
            missing=deepcopy(record);del missing['presentation']['audit']['identity']
            with self.assertRaises(ValueError):validate(missing)

    def test_records_without_audit_keep_the_summary_block(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['presentation']['dense']=True
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            sixth=(root/'site/zh-CN.html').read_text('utf8').split('id="section-6"')[1].split('</section>')[0]
            self.assertIn('结论与证据说明',sixth)
            self.assertIn(record['narrative']['zh-CN']['summary'],sixth)
            self.assertNotIn('如何复现',sixth)

    def test_unpaired_dense_page_keeps_empty_finshield_and_compact_type(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['groups']['finshield']=None
            record['publicMedia']=[item for item in record['publicMedia'] if item['group']=='native']
            record['presentation']['dense']=True
            record['presentation']['groups']['finshield'].update(
                configuration=['—'],
                toolSummary={'en':'FinShield was not tested.','zh-CN':'FinShield 未测试。'})
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            html=(root/'site/zh-CN.html').read_text('utf8')
            self.assertIn('detail-compact.css',html)
            self.assertNotIn('class="eyebrow"',html)
            self.assertIn('01 发生了什么',html)
            self.assertIn('data-state="not-run"',html)
            self.assertIn('未测试',html)
            self.assertNotIn('media/comparison.gif',html)

    def test_reviewed_live_records_use_dense_comparison(self):
        missing=[]
        for path in sorted((ROOT/'results').rglob('record.json')):
            record=json.loads(path.read_text(encoding='utf8'))
            if record.get('reviewStatus')!='reviewed' or record.get('evidenceOrigin')!='live':
                continue
            if not record.get('presentation',{}).get('dense'):
                missing.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(missing,[])

    def test_evidence_sidecars_cannot_export_authentication_or_replace_generated_files(self):
        for name, content in [('audit.json', '{"apiKey":"synthetic-credential-fixture"}'),
                              ('evidence.json', '{}'), ('en.md', 'Replacement report')]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);record=self.fixture(root)
                record['presentation']['evidenceFiles']=[name]
                (root/name).write_text(content,encoding='utf8')
                source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
                with self.assertRaises(ValueError):export_reports(source,root/'site')
                self.assertFalse((root/'site').exists())

    def test_detail_title_omits_the_protection_comparison_suffix(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['presentation']['dense']=True
            record['narrative']['en']['title']='Window flood: default protection and FinShield'
            record['narrative']['zh-CN']['title']='弹窗风暴：默认防护与 FinShield 对照'
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            zh=(root/'site/zh-CN.html').read_text('utf8')
            en=(root/'site/en.html').read_text('utf8')
            self.assertIn('<h1>弹窗风暴</h1>',zh)
            self.assertIn('<title>弹窗风暴 · Agent Safety Arena</title>',zh)
            self.assertNotIn('默认防护与 FinShield 对照',zh)
            self.assertNotIn('默认防护与FinShield对照',zh)
            self.assertIn('<h1>Window flood</h1>',en)
            self.assertIn('<title>Window flood · Agent Safety Arena</title>',en)
            self.assertNotIn('default protection and FinShield',en)
            self.assertEqual(json.loads(source.read_text('utf8'))['narrative']['zh-CN']['title'],
                             '弹窗风暴：默认防护与 FinShield 对照')
            record['narrative']['zh-CN']['title']='弹窗风暴：默认防护与FinShield对照'
            source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'compact')
            compact=(root/'compact/zh-CN.html').read_text('utf8')
            self.assertIn('<h1>弹窗风暴</h1>',compact)
            self.assertNotIn('默认防护与FinShield对照',compact)

    def test_detail_section_labels_mix_questions_and_source_names(self):
        expected={
            'zh-CN':['01 发生了什么','02 防住了吗','03 怎么看出来','04 提示词','05 模型回复','06 复现与审计'],
            'en':['01 What happened','02 Was it blocked','03 How we know','04 Prompt','05 Model reply','06 Reproduce and audit'],
        }
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['presentation']['dense']=True
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            for language,labels in expected.items():
                html=(root/'site'/f'{language}.html').read_text('utf8')
                markdown=(root/'site'/f'{language}.md').read_text('utf8')
                nav=html.split('<nav class="nav"',1)[1].split('</nav>',1)[0]
                for index,label in enumerate(labels,1):
                    with self.subTest(language=language,section=index):
                        self.assertIn(label,nav)
                        self.assertIn(f'<h2>{label}</h2>',html)
                        self.assertIn('## '+label,markdown)
                self.assertNotIn('问了什么',html)
                self.assertNotIn('What we asked',html)
                self.assertNotIn('它怎么说',html)
                self.assertNotIn('What it said',html)

    def test_detail_pages_use_two_type_sizes_and_two_fonts(self):
        sizes=type_pixel_sizes(CSS+DENSE_CSS)
        fonts=named_fonts(CSS+DENSE_CSS)
        self.assertEqual(sizes,{14,20})
        self.assertEqual(fonts,{'microsoft yahei','consolas'})
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);record=self.fixture(root)
            record['presentation'].update(dense=True,overview={'media':'media/comparison.gif','results':{
                'native':{'en':'Windows cover the desktop.','zh-CN':'弹窗遮挡桌面。'},
                'finshield':{'en':'No colored windows are visible.','zh-CN':'录像未见彩色弹窗。'}}})
            record['publicMedia'].append(dict(kind='image',path='media/comparison.gif',group='comparison',
                caption={'en':'Accelerated comparison.','zh-CN':'加速对照预览。'}))
            (root/'media/comparison.gif').write_bytes(b'controlled composite fixture')
            source=root/'record.json';source.write_text(json.dumps(record),encoding='utf8')
            export_reports(source,root/'site')
            exported=(root/'site/report.css').read_text('utf8')+(root/'site/detail-compact.css').read_text('utf8')
            self.assertEqual(type_pixel_sizes(exported),{14,20})
            self.assertEqual(named_fonts(exported),{'microsoft yahei','consolas'})


def type_pixel_sizes(css):
    sizes=set()
    for match in re.finditer(r'(?:^|[;{])\s*(?:font-size|--(?:text|heading)-size)\s*:\s*([^;}]+)',css):
        value=match.group(1).strip()
        if value in {'inherit','unset','initial'} or value.startswith('var('):
            continue
        sizes.update(_pixels(value))
    for match in re.finditer(r'(?:^|[;{])\s*font\s*:\s*([^;}]+)',css):
        sizes.update(_pixels(match.group(1)))
    return sizes


def named_fonts(css):
    names=set()
    generic={'inherit','unset','initial','sans-serif','serif','monospace','cursive','fantasy','system-ui'}
    for match in re.finditer(r'font-family\s*:\s*([^;}]+)',css):
        names.update(_family_names(match.group(1),generic))
    for match in re.finditer(r'(?:^|[;{])\s*font\s*:\s*([^;}]+)',css):
        names.update(_family_names(match.group(1),generic))
    return names


def _pixels(value):
    return {int(n) if n.isdigit() else float(n) for n in re.findall(r'(\d+(?:\.\d+)?)px',value)}


def _family_names(value, generic):
    names=set()
    for part in value.split(','):
        name=part.strip().strip('"\'').lower()
        if name and name not in generic and not re.match(r'^[\d./]+(px|em|rem|%)?$',name):
            names.add(name)
    return names


if __name__ == '__main__':
    unittest.main()
