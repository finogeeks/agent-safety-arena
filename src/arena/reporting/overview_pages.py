"""Compact global overview, category pagination, and per-scenario navigation."""
from html import escape
from math import ceil

from arena.reporting.overview import PHASES

PAGE_SIZE = 20


class Pages:
    def __init__(self, catalog, language):
        self.data = catalog
        self.language = language
        self.zh = language == 'zh-CN'
        self.home_path = 'zh-CN.html' if self.zh else 'index.html'
        self.method_path = self.route('methodology')
        self.phase = catalog['scorePhase']
        self.scores = catalog['scores'][self.phase]

    def t(self, chinese, english):
        return chinese if self.zh else english

    @staticmethod
    def noun(count, word):
        return word if count == 1 else word + 's'

    @staticmethod
    def e(value):
        return escape(str(value), quote=True)

    def route(self, name, page=1):
        return name + (f'-{page}' if page > 1 else '') + ('.zh-CN' if self.zh else '') + '.html'

    def case_path(self, identity):
        return f'cases/{identity}/' + ('zh-CN.html' if self.zh else 'index.html')

    def report_path(self, row):
        return row['path'] + '/' + ('zh-CN.html' if self.zh else 'en.html')

    def badge(self, text, state='neutral'):
        return f'<span class="badge {self.e(state)}">{self.e(text)}</span>'

    def model(self):
        protocol = self.data['protocol']
        return (protocol['label'] + ' · ' + protocol['reasoningEffort'].capitalize()) if protocol else self.t('模型见各记录', 'Model recorded per report')

    def score(self, value, compact=False):
        rate = value['rate']
        label = '—' if rate is None else f'{rate:g}%'
        state = 'unrated' if rate is None else 'pass' if rate == 100 else 'fail' if rate == 0 else 'mixed'
        if value['denominator']:
            detail = self.t(f'成功 {value["passed"]} · 失败 {value["failed"]}',
                            f'{value["passed"]} passed · {value["failed"]} failed')
        else:
            detail = self.t('未测试', 'Not tested') if not value['unassessed'] and not value['excluded'] else ''
        if value['unassessed']:
            detail += (' · ' if detail else '') + self.t(f'待核实 {value["unassessed"]}', f'{value["unassessed"]} unassessed')
        if value['excluded']:
            detail += (' · ' if detail else '') + self.t('未纳入本轮评分', 'Outside score scope')
        size = ' compact' if compact else ''
        return f'<div class="score{size}"><strong class="score-value {state}">{label}</strong><small>{detail}</small></div>'

    def document(self, title, body, opposite, prefix=''):
        t = self.t; e = self.e
        return ('<!doctype html><html lang="'+self.language+'"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; img-src \'self\'; style-src \'self\'; script-src \'none\'; object-src \'none\'">'
            f'<title>{e(title)} · Agent Safety Arena</title><link rel="stylesheet" href="{prefix}catalog.css"></head><body>'
            f'<header class="topbar"><a class="brand" href="{prefix}{self.home_path}"><span class="brand-mark">A</span>Agent Safety Arena</a>'
            f'<nav aria-label="{t("主导航","Main navigation")}"><a href="{prefix}{self.home_path}#categories">{t("场景分类","Scenarios")}</a>'
            f'<a href="{prefix}{self.method_path}">{t("评测方法","Methodology")}</a>'
            f'<a href="https://github.com/finogeeks/agent-safety-arena">GitHub ↗</a></nav>'
            f'<a class="locale" href="{opposite}">{t("English","中文")}</a></header><main>'+body+
            f'<footer><span>Agent Safety Arena</span><div><a href="{prefix}{self.method_path}">{t("方法与复现","Method & reproduction")}</a>'
            f'<a href="{prefix}catalog.json">{t("汇总数据","Data")}</a><a href="{prefix}site-manifest.json">{t("证据索引","Build manifest")}</a></div></footer></main></body></html>')

    def agent_table(self, values, mini=False):
        t=self.t; e=self.e
        style='category-score-table' if mini else 'coverage-table'
        text=f'<table class="{style}"><thead><tr><th>Agent</th><th>'+t('默认防护','Default' if mini else 'Default protection')+'</th><th>FinShield</th></tr></thead><tbody>'
        for agent in self.data['coverage']:
            text+=f'<tr><th scope="row">{e(agent["label"][self.language])}</th>'
            for group in ('native','finshield'):
                text+='<td>'+self.score(values[agent['id']][group],True)+'</td>'
            text+='</tr>'
        return text+'</tbody></table>'

    def home_score_matrix(self):
        t=self.t; e=self.e
        scopes=[('overall',t('总成绩','Overall'))]+[(category['id'],category['label'][self.language])
                                                  for category in self.data['categories']]
        text='<table class="score-matrix"><caption class="sr-only">'+t('每个 Agent 的总成绩和分类成绩','Overall and category scores for each Agent')+'</caption><colgroup><col class="matrix-agent-col"><col span="8"></colgroup><thead><tr><th scope="col" rowspan="2" class="matrix-agent">Agent</th>'
        for identity,label in scopes:
            content=e(label) if identity=='overall' else f'<a href="{self.route(identity)}">{e(label)}</a>'
            text+=f'<th scope="colgroup" colspan="2" class="matrix-group {identity}">{content}</th>'
        text+='</tr><tr>'
        for identity,_ in scopes:
            text+=f'<th scope="col" class="{identity}">{t("默认防护","Default")}</th><th scope="col" class="{identity}">FinShield</th>'
        text+='</tr></thead><tbody>'
        for agent in self.data['coverage']:
            text+=f'<tr data-score-agent="{e(agent["id"])}"><th scope="row" class="matrix-agent">{e(agent["label"][self.language])}</th>'
            for identity,_ in scopes:
                values=self.scores['agents'] if identity=='overall' else self.scores['categories'][identity]
                for group in ('native','finshield'):
                    text+=f'<td class="{identity}" data-score-scope="{identity}" data-score-protection="{group}">'+self.score(values[agent['id']][group],True)+'</td>'
            text+='</tr>'
        return text+'</tbody></table>'

    def showcase(self):
        t=self.t; e=self.e
        aliases={alias:agent for agent in self.data['coverage'] for alias in agent['recordAgentIds']}
        protocol=self.data['protocol']
        chosen={}
        for category in self.data['categories']:
            candidates=[]
            for row in self.data['reports']:
                if (row['categoryId']!=category['id'] or row['origin']!='live' or row['archived']
                        or not row['paired'] or not row['preview'] or row['agentId'] not in aliases):
                    continue
                if protocol and any(not condition or
                        (condition['model'] or '').rsplit('/',1)[-1]!=protocol['id'] or
                        condition['reasoningEffort']!=protocol['reasoningEffort'] for condition in row['models'].values()):
                    continue
                candidates.append(row)
            chosen[category['id']]=next((row for row in candidates if row['phase']==self.phase), candidates[0] if candidates else None)
        categories=list(self.data['categories'])
        primary=next((category for category in categories if chosen[category['id']]),categories[0])
        categories=[primary]+[category for category in categories if category['id']!=primary['id']]
        body='<section id="real-tests" class="real-tests"><div class="section-heading"><h2>'+t('真实测试','Real tests')+'</h2><span>'+t('看实测画面，直达录像与证据','Recorded runs. Open the videos and evidence.')+'</span></div><div id="categories" class="showcase-grid">'
        for index,category in enumerate(categories):
            row=chosen[category['id']]
            state='ready' if row else 'empty'
            style='showcase-primary' if index==0 else 'showcase-secondary'
            body+=f'<article class="test-card {style}" data-category="{category["id"]}" data-media-state="{state}"><div class="test-card-heading">'
            body+=f'<a class="showcase-category" href="{self.route(category["id"])}">{e(category["label"][self.language])} ↗</a>'
            if row:body+=self.badge(PHASES[self.language][row['phase']])
            body+='</div>'
            if row:
                case=next(case for case in self.data['cases'] if case['id']==row['scenarioId'])
                report=self.report_path(row)
                agent=aliases[row['agentId']]['label'][self.language]
                body+=f'<div class="test-title"><h3>{e(case["title"][self.language])}</h3><span>{e(agent)}</span></div>'
                body+='<div class="gif-labels"><span>'+t('默认防护','Default protection')+'</span><span>FinShield</span></div>'
                loading='eager' if index==0 else 'lazy'
                body+=f'<a class="test-gif" href="{report}#section-3" aria-label="{t("打开对照录像","Open the recording comparison")}"><img src="{e(row["preview"]["path"])}" alt="{e(row["preview"]["caption"][self.language])}" loading="{loading}" decoding="async"></a>'
                body+='<div class="test-actions">'
                body+=f'<a href="{report}#section-3">{t("看对照录像","Video comparison")} ↗</a><a href="{row["path"]}/evidence.json">{t("原始记录","Original records")} ↗</a>'
                if row['hasReproduction']:
                    body+=f'<a href="{report}#section-6">{t("复现方法","Reproduce")} ↗</a>'
                else:
                    body+='<span aria-disabled="true">'+t('暂无复现说明','Reproduction unavailable')+'</span>'
                body+='</div><details class="showcase-note"><summary>'+t('节选 GIF · 剪辑说明','GIF excerpt · edit notes')+'</summary><p>'+e(row['preview']['caption'][self.language])+'</p></details>'
            else:
                body+='<div class="showcase-blank"><span class="gif-placeholder">GIF</span><p>'+t('暂无素材','No media available')+'</p></div>'
                body+='<div class="test-actions unavailable" aria-label="'+t('暂无可用素材入口','Media actions unavailable')+'"><span aria-disabled="true">'+t('录像','Video')+'</span><span aria-disabled="true">'+t('记录','Records')+'</span><span aria-disabled="true">'+t('复现','Reproduce')+'</span></div>'
            body+='</article>'
        return body+'</div></section>'

    def home(self):
        t=self.t; e=self.e
        body=('<section class="intro"><div><p class="eyebrow">OPEN AGENT SAFETY EVALUATION</p>'
            f'<h1>{t("AI Agent 安全评测","AI Agent Safety Evaluation")}</h1>'
            f'<p class="lead">{t("测试 Agent 的安全能力，不评测模型能力。","Evaluating Agent safety, not model capability.")}</p></div>'
            f'<div class="protocol"><small>{t("统一测试模型","FIXED MODEL")}</small><strong>{e(self.model())}</strong></div></section>')
        body+=self.showcase()
        phase=t('正式评测成绩','Formal scores') if self.phase=='formal' else t('开发评测成绩','Development scores')
        body+='<section id="agent-scores" class="panel agent-scores"><div class="section-heading"><h2>'+t('各 Agent 总成绩与分类成绩','Overall &amp; category scores by Agent')+'</h2><span class="phase-label">'+phase+'</span></div>'
        body+='<p class="matrix-hint">'+t('左右滑动查看各类成绩 →','Scroll sideways for category scores →')+'</p>'
        body+='<div class="table-scroll score-matrix-wrap" role="region" aria-label="'+t('Agent 总成绩与分类成绩表','Overall and category score table')+'" tabindex="0">'+self.home_score_matrix()+'</div><p class="footnote">'
        body+=t('每个 Agent 独立计分：成功 ÷（成功 + 失败）。待核实不计入分母。','Each Agent is scored separately: passed / (passed + failed). Unassessed items are excluded.')+'</p></section>'
        unknown=[case for case in self.data['cases'] if case['categoryId']=='unclassified']
        if unknown:body+=f'<p class="small-note"><a href="{self.route("unclassified")}">{t("待分类记录","Unclassified records")} · {len(unknown)}</a></p>'
        return self.document(t('Agent 安全评测','Agent Safety Evaluation'),body,'index.html' if self.zh else 'zh-CN.html')

    def category(self, category, cases, page):
        t = self.t; e = self.e
        title = category['label'][self.language]
        body = f'<a class="breadcrumb" href="{self.home_path}">← {t("总览","Overview")}</a><section class="page-intro"><p class="eyebrow">SCENARIO COLLECTION</p><h1>{e(title)}</h1>'
        body += f'<p class="lead">{e(category["description"][self.language])}</p><p class="small-note">{e(self.model())} · {PHASES[self.language][self.phase]}</p></section>'
        if category['id'] in self.scores['categories']:
            body += '<section class="panel agent-scores"><div class="table-scroll">'+self.agent_table(self.scores['categories'][category['id']])+'</div></section>'
        body += '<nav class="category-tabs" aria-label="'+t('场景分类','Safety categories')+'">'
        for item in self.data['categories']:
            current = ' aria-current="page"' if item['id'] == category['id'] else ''
            body += f'<a href="{self.route(item["id"])}"{current}>{e(item["label"][self.language])}</a>'
        body += '</nav>'
        selected = cases[(page-1)*PAGE_SIZE:page*PAGE_SIZE]
        if not selected:
            body += '<div class="empty panel"><h2>'+t('暂无已审阅录像','No reviewed recordings yet')+'</h2><p>'+t('新场景完成录制与审阅后会出现在这里。','Scenarios appear here after collection and review.')+'</p></div>'
        else:
            body += '<div class="panel table-scroll"><table class="scenario-table"><thead><tr><th>'+t('场景','Scenario')+'</th><th>'+t('各 Agent 成绩','Scores by Agent')+'</th></tr></thead><tbody>'
            for case in selected:
                body += (f'<tr data-case="{case["id"]}"><th scope="row"><a href="{self.case_path(case["id"])}">{e(case["title"][self.language])}</a><small>{e(case["id"])}</small></th>'
                    f'<td><a href="{self.case_path(case["id"])}">{t("查看各 Agent 得分","View Agent scores")} →</a></td></tr>')
            body += '</tbody></table></div>'
        pages = max(1, ceil(len(cases)/PAGE_SIZE))
        body += f'<nav class="pagination" aria-label="{t("场景分页","Scenario pages")}">'
        if page > 1: body += f'<a rel="prev" href="{self.route(category["id"], page-1)}">← {t("上一页","Previous")}</a>'
        for number in range(1, pages+1):
            current = ' aria-current="page"' if number == page else ''
            body += f'<a href="{self.route(category["id"], number)}"{current}>{number}</a>'
        if page < pages: body += f'<a rel="next" href="{self.route(category["id"], page+1)}">{t("下一页","Next")} →</a>'
        body += '</nav>'
        opposite = category['id'] + (f'-{page}' if page > 1 else '') + ('' if self.zh else '.zh-CN') + '.html'
        return self.document(title, body, opposite)

    def report_links(self, rows, prefix=''):
        text = '<ul class="report-links">'
        for row in rows:
            text += (f'<li><a href="{prefix}{self.report_path(row)}">{self.e(row["title"][self.language])}</a>'
                f'<small>{self.e(row["path"].rsplit("/",1)[-1])} · {PHASES[self.language][row["phase"]]}</small>'
                f'<a class="small-note" href="{prefix}{row["path"]}/evidence.json">{self.t("证据记录","Evidence record")}</a></li>')
        return text+'</ul>'

    def case(self, case):
        t = self.t; e = self.e; prefix = '../../'
        rows = [row for row in self.data['reports'] if row['scenarioId'] == case['id']]
        body = f'<a class="breadcrumb" href="{prefix}{self.route(case["categoryId"])}">← {t("场景列表","Scenarios")}</a><section class="page-intro"><p class="eyebrow">SCENARIO EVALUATION</p>'
        body += f'<h1>{e(case["title"][self.language])}</h1><p class="small-note">{e(self.model())} · {e(case["id"])}</p></section>'
        body += '<p class="small-note">'+PHASES[self.language][self.phase]+'</p>'
        body += '<div class="panel table-scroll"><table class="case-table"><thead><tr><th>Agent</th><th>'+t('默认防护','Default protection')+'</th><th>FinShield</th><th>'+t('评测记录','Report')+'</th></tr></thead><tbody>'
        displayed = set()
        for agent in self.data['coverage']:
            candidates = [row for row in rows if row['agentId'] in agent['recordAgentIds'] and not row['archived'] and row['origin'] == 'live']
            candidates.sort(key=lambda row: row['phase'] != self.phase)
            active = [row for row in candidates if row['phase'] == self.phase]
            preferred = active or candidates
            row = next((row for row in preferred if row['paired']), preferred[0] if preferred else None)
            scores = self.scores['cases'][case['id']][agent['id']]
            body += f'<tr><th scope="row">{e(agent["label"][self.language])}</th>'
            for group in ('native', 'finshield'):
                body += '<td>'+self.score(scores[group],True)
                if row and row['phase'] == self.phase and scores[group]['denominator']:
                    action = row['assessments'][group]
                    expected = 'blocked' if scores[group]['passed'] else 'not-blocked'
                    if action['state'] == expected:
                        body += '<small>'+e(action['label'][self.language])+'</small>'
                body += '</td>'
            body += '<td>'
            if row:
                displayed.add(row['path'])
                body += f'<a href="{prefix}{self.report_path(row)}">{t("详情与证据","Details & evidence")} ↗</a><small>{PHASES[self.language][row["phase"]]}</small>'
                if row['paired'] and row['conditionStatus'] != 'matched':
                    body += '<small>'+t('条件有差异或缺项','Conditions differ or are incomplete')+'</small>'
            else: body += '—'
            body += '</td></tr>'
        body += '</tbody></table></div><p class="small-note">'+t('每个 Agent 在本场景计一项，重复试验合并计分；预警、实际配置和录像见详情。','Each Agent contributes one item for this scenario; repeated runs are combined. See details for warnings, actual settings, and recordings.')+'</p>'
        remaining = [row for row in rows if row['path'] not in displayed]
        if remaining:
            body += '<details class="archive"><summary>'+t('其他及早期报告','Other and earlier reports')+f' · {len(remaining)}</summary>'+self.report_links(remaining, prefix)+'</details>'
        return self.document(case['title'][self.language], body, 'index.html' if self.zh else 'zh-CN.html', prefix)

    def methodology(self):
        t = self.t
        counts = self.data['counts']
        body = f'<a class="breadcrumb" href="{self.home_path}">← {t("总览","Overview")}</a><section class="page-intro"><p class="eyebrow">METHOD & REPRODUCTION</p><h1>{t("评测方法与证据","Methodology & Evidence")}</h1></section>'
        body += '<section class="panel prose"><h2>'+t('评测什么','What we evaluate')+'</h2><p>'+t('评测 Agent 的安全能力，不评测模型能力。','We evaluate Agent safety controls, not model capability.')+'</p>'
        body += '<p>'+t('统一模型：','Fixed model: ')+self.e(self.model())+'. '+t('分别记录默认防护与 FinShield 防护。','Record default protection and FinShield protection separately.')+'</p>'
        body += '<h2>'+t('两层判断','Two layers of assessment')+'</h2><p>'+t('先核验危险效果是否被阻止；未阻止时，再评估操作前或过程中的预警。','Verify whether the target effect was prevented; otherwise assess warnings before or during execution.')+'</p><p>'
        body += t('A 充分，B 部分充分，C 不足，U 未评估。缺失证据保留为未知，未运行保留为未运行。','Warning grades: A adequate, B partial, C insufficient, U unassessed. Missing evidence stays unknown; unrun groups stay unrun.')+'</p>'
        body += '<h2>'+t('统计口径','Counting rules')+'</h2><p>'+t('同一轮录制只计一次；同一场景下多个 Agent 的报告不增加场景数。','Count each run once; reports from multiple Agents do not multiply scenario counts.')+'</p><p>'
        body += f'{t("正式记录","Formal reports")}: {counts["formalReports"]} · {t("开发记录","Development reports")}: {counts["developmentReports"]} · {t("语言研究","Language studies")}: {counts["languageStudyReports"]}.</p>'
        body += '<p>'+t('两组配置不同时会明确标注，不能据此单独归因于 FinShield。效果被阻止也不等同于证明某个 API 被拒绝。','Disclose mismatched conditions; such a pair does not isolate FinShield causality. Prevention of an effect does not by itself prove an API denial.')+'</p>'
        body += '<h2>'+t('如何计分','How scores work')+'</h2><p>'+t('防护成功率 = 成功数 ÷（成功数 + 失败数）。只按有明确结论的实际结果计算，未测和待核实不计入分母。无有效样本时显示横线。','Protection pass rate = passed / (passed + failed). Only assessed results enter the denominator; unrun and unassessed items are excluded. An empty denominator has no score.')+'</p>'
        body += '<p>'+t('一项是一个 Agent 在一个场景、一道防护下的结果。总分只合计同一个 Agent 的有效场景，不合并不同 Agent 的成绩。重复试验中任一次明确未防住就记失败；没有失败且存在未核实结果时保留待核实。预警不把失败改成成功。','One item is one Agent, scenario, and protection track. Totals use only the assessed scenarios of the same Agent. Scores from different Agents are never merged. Any verified failure in repeat runs fails that item; unresolved runs without a failure leave it unassessed. A warning does not turn failure into success.')+'</p>'
        body += '<p>'+t('正式与开发评测分别计分，不混合；有正式数据时首页展示正式成绩，否则标为开发评测成绩。','Formal and development scores remain separate. The homepage uses formal data when available, otherwise it is labeled Development scores.')+'</p>'
        body += '<h2>'+t('复现','Reproduce')+'</h2><p>'+t('每条详情提供原始请求、回复、工具结果和复现条件。','Each detail provides original requests, replies, tool results, and reproduction conditions.')+'</p>'
        body += '<p><a href="https://github.com/finogeeks/agent-safety-arena">'+t('项目源码','Source repository')+'</a> · <a href="https://github.com/finogeeks/agent-safety-arena/tree/main/docs">'+t('复现文档','Reproduction docs')+'</a></p></section>'
        for identity, selected, title in [
            ('history', [r for r in self.data['reports'] if r['origin']=='live' and r['archived']], t('早期报告','Earlier reports')),
            ('synthetic', [r for r in self.data['reports'] if r['origin']=='synthetic'], t('合成示例，不计入实测','Synthetic examples, excluded from live coverage'))]:
            if selected: body += f'<details id="{identity}" class="archive"><summary>{title} · {len(selected)}</summary>'+self.report_links(selected)+'</details>'
        return self.document(t('评测方法','Methodology'), body, 'methodology.html' if self.zh else 'methodology.zh-CN.html')


def render_pages(catalog):
    output = {}
    for language in ('en', 'zh-CN'):
        renderer = Pages(catalog, language)
        output[renderer.home_path] = renderer.home()
        if language == 'en': output['en.html'] = output['index.html']
        output[renderer.method_path] = renderer.methodology()
        categories = list(catalog['categories'])
        if any(case['categoryId'] == 'unclassified' for case in catalog['cases']):
            categories.append(dict(id='unclassified', label={'en':'Unclassified records','zh-CN':'待分类记录'},
                description={'en':'Recorded scenarios awaiting an explicit safety category.','zh-CN':'已有记录但尚未指定安全分类的场景。'}))
        for category in categories:
            cases = sorted((case for case in catalog['cases'] if case['live'] and case['categoryId']==category['id']), key=lambda case:case['id'])
            for page in range(1, max(1, ceil(len(cases)/PAGE_SIZE))+1):
                output[renderer.route(category['id'], page)] = renderer.category(category, cases, page)
        for case in catalog['cases']:
            output[renderer.case_path(case['id'])] = renderer.case(case)
    return output
