"""Local comparison pages from the existing reviewed-record contract."""
from html import escape
from pathlib import PurePosixPath
import re


TEXT = {
    'en': dict(back='All cases', evidence='Evidence', missing='Not tested', blank='No trial or conclusion is available.',
        conditions='Run conditions', comparison='Comparison incomplete', development='Development trial',
        synthetic='Synthetic evidence', grade='Warning adequacy', reason='Assessment basis',
        grades={'adequate':('A','Adequate'),'partial':('B','Partial'),'insufficient':('C','Insufficient'),'unassessed':('U','Unassessed')},
        fields=['Task','Agent decision','Approval','Visible effect','Enforcement','Completion','Evidence','Recovery'],
        copy='Copy text', copied='Copied', original='Original', translation='Display translation',
        stored='The submitted original is kept in the evidence file.',
        no_reply='No public reply was recorded.', evidence_note='Open the shared evidence file',
        hash_label='Evidence SHA-256', sections_nav='Sections',
        open_image='Open original screenshot', locale='简体中文', locale_path='zh-CN.html',
        shared='Shared original evidence · local report', detail='View result', scope='This grade evaluates the warning, not action severity or sandbox strength.',
        chips={'workspace-write':'workspace-write','ask':'ask'}),
    'zh-CN': dict(back='全部案例', evidence='证据', missing='未测试', blank='尚无试验素材或结论。',
        conditions='运行条件', comparison='对比尚未完成', development='开发试录', synthetic='合成证据',
        grade='警示充分度', reason='评级依据',
        grades={'adequate':('A','充分'),'partial':('B','部分'),'insufficient':('C','不足'),'unassessed':('U','未评估')},
        fields=['请求任务','Agent 决定','原生审批','可见效果','沙箱执行','完成状态','证据边界','资源恢复'],
        copy='复制本页文字', copied='已复制', original='原文', translation='中文展示',
        stored='实际提交的原文保存在证据文件中。',
        no_reply='没有记录到公开回复。', evidence_note='打开共用证据文件',
        hash_label='证据 SHA-256', sections_nav='章节',
        open_image='打开原始截图', locale='English', locale_path='en.html', shared='共用原始证据 · 本地结果页',
        detail='查看结果', scope='本等级评价提示是否充分，不代表操作危险程度或沙箱强度。',
        chips={'workspace-write':'工作区可写','ask':'每次询问'})}


CSS = """
:root{--text-size:14px;--heading-size:20px;color-scheme:light;color:#243248;background:#f4f6f9;font-family:"Microsoft YaHei",sans-serif;font-size:var(--text-size);line-height:1.65}
*{box-sizing:border-box;font-family:inherit;font-size:inherit;letter-spacing:normal}body{margin:0}a{color:#285dbb;text-decoration:none}a:hover{text-decoration:underline}
main,.bar,.site-bar{max-width:1000px;margin:auto;padding:24px 22px}.bar,.site-bar{display:flex;align-items:center;justify-content:flex-start;gap:16px;flex-wrap:wrap;padding-top:17px;padding-bottom:17px}
.site-header{background:white;border-bottom:1px solid #dde3eb}.brand{display:inline-flex;align-items:center;gap:8px;color:#22324b;font-weight:650}.brand-mark{display:grid;place-items:center;background:#285ecc;color:white;width:26px;height:28px;border-radius:6px}.site-nav{display:flex;flex-wrap:wrap;align-items:center;gap:12px 18px;margin-left:auto}.site-nav a[aria-current]{color:#172b4a;font-weight:600}.locale{color:#778397}.bar small{color:#778397;margin-left:12px}
h1,h2,.group-title,.overview-headings strong{font-size:var(--heading-size);font-weight:600;line-height:1.4;color:#172b4a}
h1{margin:12px 0 10px}h2{margin:0 0 16px}h3{margin:0 0 10px;font-weight:600}p{margin:8px 0;white-space:pre-line}
.eyebrow,.muted,figcaption,.lead,.fine,.metadata-row,footer,.prompt-code-note{color:#69798d}.lead{max-width:760px}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:15px 0}.chip{display:inline-flex;padding:3px 9px;border:1px solid #e0e5ed;border-radius:5px;color:#516479;background:#f8fafc}
.hero{padding:4px 0 10px}.panel{background:white;border:1px solid #e0e6ee;border-radius:10px;padding:22px;margin:16px 0;scroll-margin-top:75px}
.nav{position:sticky;top:0;z-index:10;display:flex;gap:18px;overflow:auto;background:#f4f6f9f5;border-bottom:1px solid #dfe5ed;padding:13px 0;backdrop-filter:blur(8px);white-space:nowrap}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}.group{min-width:0}.group-title{padding:0 0 10px;border-bottom:1px solid #e7ebf1;margin-bottom:12px}
.empty{background:#fafbfd;border:1px dashed #dce2eb;border-radius:8px;min-height:230px;display:flex;flex-direction:column;justify-content:center;align-items:center;color:#8a97a9;padding:26px;text-align:center}.empty strong{color:#7a899e;font-weight:500}
.grade-row{display:flex;align-items:center;gap:12px;margin-bottom:12px}.grade{display:inline-flex;align-items:center;gap:8px;padding:4px 11px;border-radius:6px;font-weight:650;border:1px solid #e3e7ee;background:#f3f5f8;color:#55657b}
.assessment-status{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:8px 12px;margin-bottom:10px}
.assessment-pair>.group>.group-title,.assessment-evidence>summary{text-align:center}
.interception-badge{display:inline-flex;padding:4px 11px;border-radius:6px;font-weight:650;background:#f3f5f8;color:#55657b;border:1px solid #e3e7ee}
.interception-badge.blocked{background:#eaf5ee;color:#316746;border-color:#c6e1cf}.interception-badge.not-blocked{background:#fff0f0;color:#9f2424;border-color:#ecc4c4}
.assessment-status .grade{padding:0;border:0;background:transparent;font-weight:500}.assessment-note{color:#78869a}.assessment-evidence{margin:8px 0 14px;padding-top:8px}
.grade[data-warning-level="insufficient"]{background:#fff3e8;border-color:#f3d6ba;color:#97511c}.grade[data-warning-level="adequate"]{background:#eaf5ee;border-color:#c6e1cf;color:#316746}.grade[data-warning-level="partial"]{background:#fff8df;border-color:#eadba4;color:#806113}
.assessment-status .warning-absent{background:transparent;color:#9f2424;font-weight:600}
.grade-reason{color:#475c74;margin-bottom:12px}.fine{overflow-wrap:anywhere}
table{width:100%;border-collapse:collapse;text-align:left;table-layout:fixed}th,td{padding:10px 11px;border-bottom:1px solid #e9edf2;vertical-align:top;overflow-wrap:anywhere}th{color:#65758c;font-weight:500;background:#f8fafc}th:first-child{width:18%}.facts td:first-child{color:#64748b;width:26%}.facts td{padding-left:0}
figure{margin:0 0 22px}img{display:block;width:100%;max-width:100%;border-radius:7px;border:1px solid #e3e8ef}
.video-frame{aspect-ratio:16/9;background:#e9edf3;border:1px solid #e3e8ef;border-radius:7px}
.video-frame video{display:block;width:100%;height:100%;border:0;background:#e9edf3}
figcaption{line-height:1.5;margin-top:8px;white-space:pre-line}.still img{max-height:420px;object-fit:contain;background:#f8fafc}
pre,code{font-family:Consolas,monospace}
pre{background:#f7f9fc;border:1px solid #e6ebf2;border-radius:7px;padding:15px;white-space:pre-wrap;overflow-wrap:anywhere;margin:12px 0;line-height:1.7}.reply{font-family:inherit;background:transparent;border:0;padding:0}
#fixed-script,#generation-prompt{max-height:420px;overflow:auto}
.tools{display:flex;justify-content:space-between;align-items:center;gap:8px}.copy{font:inherit;background:white;border:1px solid #dbe2ec;border-radius:5px;padding:4px 10px;color:#3e5c82;cursor:pointer}
.prompt-code-note{margin:0 0 14px;line-height:1.7}
details{border-top:1px solid #e8edf3;margin-top:16px;padding-top:14px}summary{cursor:pointer;color:#315e9a}li{margin:5px 0}footer{padding:20px 0 35px;overflow-wrap:anywhere}
:focus-visible{outline:3px solid #92b8f4;outline-offset:3px}.case-card{display:block;background:white;border:1px solid #dfe5ee;border-radius:9px;padding:20px;max-width:480px}.case-card h2{margin:10px 0}.case-card p{color:#63768e}
.report-breadcrumb{display:flex;align-items:baseline;flex-wrap:wrap;gap:5px 8px;margin:0 0 10px;overflow-wrap:anywhere}
.report-breadcrumb [aria-hidden],.report-breadcrumb [aria-current]{color:#78869a}
.condition-banner{margin:0 0 14px;padding:12px 14px;border:1px solid #ead7b0;border-radius:8px;background:#faf7ee;color:#6a5a3c;line-height:1.55}
.report-return{display:inline-block;margin:12px 0 0}
@media(max-width:760px){.pair{grid-template-columns:1fr}main,.bar,.site-bar{padding-left:16px;padding-right:16px}.panel{padding:16px}.bar small{display:none}.site-nav{width:100%;order:3;margin:0;padding-top:8px;border-top:1px solid #dde3eb}.nav{gap:15px}th,td{padding:8px 6px}th:first-child{width:22%}.empty{min-height:130px}}
"""

JS = """document.addEventListener('click',async event=>{const b=event.target.closest('[data-copy]');if(!b)return;const t=document.getElementById(b.dataset.copy);if(!t)return;try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(t.textContent)}else{const r=document.createRange();r.selectNodeContents(t);const s=getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy');s.removeAllRanges()}b.textContent=b.dataset.copied}catch{t.focus()}});
document.querySelectorAll('video').forEach(video=>{const localize=async()=>{if(video.dataset.local==='blob')return;const src=video.currentSrc||video.querySelector('source')?.src;const end=video.seekable.length?video.seekable.end(video.seekable.length-1):0;if(end>0||!src||src.startsWith('blob:')){if(end>0)video.dataset.local='ok';return}video.dataset.local='blob';const url=URL.createObjectURL(await(await fetch(src)).blob());const time=video.currentTime,paused=video.paused;video.querySelectorAll('source').forEach(s=>s.remove());video.src=url;video.currentTime=time;if(!paused)video.play()};const seek=event=>{const box=video.getBoundingClientRect();if(!video.duration||box.height<=0)return false;const y=event.clientY-box.top,x=event.clientX-box.left;if(y<box.height-44||x<48||x>box.width-96)return false;video.currentTime=((x-48)/Math.max(box.width-144,1))*video.duration;return true};video.addEventListener('pointerdown',async event=>{if(event.button)return;await localize();if(seek(event)){event.preventDefault();event.stopPropagation()}},true);video.addEventListener('play',localize)});"""

DENSE_CSS = """
main,.bar,.site-bar{padding:14px 20px}.bar,.site-bar{padding-top:12px;padding-bottom:12px}
.hero{padding:0 0 5px}.hero h1{margin:5px 0 6px}.lead{margin:4px 0 7px}
.metadata-row{margin:5px 0;overflow-wrap:anywhere}
.nav{gap:14px;padding:8px 0}.panel{padding:15px 18px;margin:11px 0}
.panel h2{margin-bottom:9px}.panel p{margin:5px 0}.panel details{margin-top:9px;padding-top:8px}
.overview-headings{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0 8px}
.overview-headings strong{display:block}.overview-headings span{color:#61718a}
.overview-media{margin:0}.overview-media img{width:100%;height:auto}.overview-media figcaption{margin-top:5px}
.panel figure{margin-bottom:10px}.panel .group-title{margin-bottom:8px;padding-bottom:7px}
.panel pre{margin:8px 0}footer{padding:12px 0}
.configuration-note{display:inline-block;position:relative;border:0!important;margin:0 0 0 5px!important;padding:0!important}
.configuration-note summary{display:inline;list-style:none;cursor:pointer}.configuration-note summary::-webkit-details-marker{display:none}
.configuration-note p{position:absolute;right:0;top:16px;z-index:20;min-width:170px;padding:8px 10px!important;background:white;border:1px solid #dfe5ee;border-radius:6px;box-shadow:0 3px 12px #24324818}
@media(max-width:760px){main,.bar{padding-left:12px;padding-right:12px}.panel{padding:13px}}
"""


def e(value):
    return escape(str(value), quote=True)


GITHUB_HREF = 'https://github.com/finogeeks/agent-safety-arena'


def site_header_markup(language, home_href, locale_href, locale_label, categories=None,
                       current_category=None, brand_mark=False):
    aria = '主导航' if language == 'zh-CN' else 'Main navigation'
    locale_lang = 'en' if language == 'zh-CN' else 'zh-CN'
    def nav_label(value):
        if language == 'zh-CN':
            value = re.sub(r'(?<=[\u3400-\u9fff])\s+(?=[A-Za-z0-9])|(?<=[A-Za-z0-9])\s+(?=[\u3400-\u9fff])', '', str(value))
        return e(value)
    brand = f'<a class="brand" href="{e(home_href)}">'
    if brand_mark:
        brand += '<span class="brand-mark">A</span>'
    brand += 'Agent Safety Arena</a>'
    nav = f'<nav class="site-nav" aria-label="{aria}">'
    for item in categories or []:
        current = ' aria-current="page"' if item['id'] == current_category else ''
        nav += f'<a href="{e(item["href"])}"{current}>{nav_label(item["label"])}</a>'
    nav += f'<a href="{GITHUB_HREF}">GitHub ↗</a></nav>'
    locale = f'<a class="locale" href="{e(locale_href)}" lang="{locale_lang}">{e(locale_label)}</a>'
    return f'<header class="site-header"><div class="site-bar">{brand}{nav}{locale}</div></header>'


def breadcrumb_markup(language, crumbs, current):
    aria='当前位置' if language=='zh-CN' else 'Breadcrumb'
    def nav_label(value):
        if language=='zh-CN':
            value=re.sub(r'(?<=[\u3400-\u9fff])\s+(?=[A-Za-z0-9])|(?<=[A-Za-z0-9])\s+(?=[\u3400-\u9fff])','',str(value))
        return e(value)
    body='<nav class="report-breadcrumb" aria-label="'+aria+'">'
    for href,label in crumbs:
        body+=f'<a href="{e(href)}">{nav_label(label)}</a><span aria-hidden="true">›</span>'
    return body+'<span aria-current="page">'+nav_label(current)+'</span></nav>'


def page_title(title):
    text=str(title)
    for suffix in ('：默认防护与 FinShield 对照','：默认防护与FinShield对照',
                   ': default protection and FinShield'):
        if text.endswith(suffix):
            return text[:-len(suffix)].rstrip(' ：:')
    return text


PROMPT_CODE_NOTE={
    'en':(
        'The code in the prompt was generated by an AI from an ordinary request, but it is not written correctly every time',
        'We keep this code fixed to test the Agent\'s safety controls, so a wrong program is not mistaken for a block',
    ),
    'zh-CN':(
        '提示词中的代码由 AI 根据普通请求生成，但未必每次都能写对',
        '我们固定这些代码，是为了评测 Agent 的安全管控能力，避免把“没写对”误判为“防住了”',
    ),
}

GENERATION_CODE_NOTE={
    'en':('The script in the prompt was generated by AI from an ordinary prompt.',
          'We keep this code fixed to test the Agent\'s safety controls, so a wrong program is not mistaken for a block'),
    'zh-CN':('提示词当中的脚本是由AI根据普通提示词生成的。',
             '我们固定这些代码，是为了评测 Agent 的安全管控能力，避免把“没写对”误判为“防住了”'),
}


def prompt_has_code(prompts):
    return any('```' in prompt['text'] for _,prompt in prompts)


def prompt_code_note(language, prompts):
    if not prompt_has_code(prompts):return ''
    return '<p class="prompt-code-note">'+'<br>'.join(e(line) for line in PROMPT_CODE_NOTE[language])+'</p>'


def header_metadata(record, language):
    """Use reviewed dates and actual group conditions for both report formats."""
    presentation=record['presentation'];groups=record['groups'];ui=TEXT[language]
    missing='Not recorded' if language=='en' else '未记录'
    def shared_value(value_for):
        values=[(presentation['groups'][name]['title'][language],value_for(group))
                for name,group in groups.items() if group]
        if not values:return missing
        if len({value for _,value in values})==1:return values[0][1]
        return ' / '.join(f'{name}: {value}' for name,value in values)
    agent_version=shared_value(lambda group:group['conditions'].get('agentVersion') or missing)
    model=shared_value(lambda group:' · '.join(group['conditions'].get(key) or missing
                                            for key in ('model','reasoningEffort')))
    tested=presentation.get('testedOn')
    tested_label=f'{tested["date"]} ({tested["timezone"]})' if tested else missing
    fs_version=(groups.get('finshield') or {}).get('environmentVersion') or missing
    fs_version=re.sub(r'^(?:FinShield|FinSAFE)\s+', '',fs_version,flags=re.I)
    phase=ui['development'] if record['phase']!='formal' else record['phase']
    labels=(['Test date',record['agentId'].upper()+' version','Model','FinShield version','Track']
            if language=='en' else ['测试时间',record['agentId'].upper()+' 版本','模型','FinShield 版本','试验类型'])
    return list(zip(labels,[tested_label,agent_version,model,fs_version,phase]))


AUDIT_CONDITION_LABELS={
    'en':[('runId','Run ID'),('revision','Prompt revision'),('sha','Prompt SHA-256'),
          ('agentVersion','Agent version'),('model','Model'),('reasoning','Reasoning'),
          ('sandbox','Built-in sandbox'),('approval','Approval policy'),
          ('confirmation','Confirmation'),('os','OS'),('environment','Environment version')],
    'zh-CN':[('runId','运行 ID'),('revision','提示词修订'),('sha','提示词 SHA-256'),
             ('agentVersion','Agent 版本'),('model','模型'),('reasoning','推理强度'),
             ('sandbox','内置沙箱'),('approval','批准策略'),
             ('confirmation','确认方式'),('os','操作系统'),('environment','环境版本')]}
AUDIT_LOCATION={'page':('This page','本页'),'raw':('Raw run, not copied','原始运行，未复制到本页'),
                'repo':('Repository','仓库')}


def audit_condition_value(record, group, key, missing):
    if not group:
        return '—'
    prompt=group.get('prompt',record['prompt'])
    conditions=group['conditions']
    value={'runId':group['runId'],'revision':prompt.get('revision'),'sha':conditions.get('promptSha256'),
           'agentVersion':conditions.get('agentVersion'),'model':conditions.get('model'),
           'reasoning':conditions.get('reasoningEffort'),'sandbox':conditions.get('builtinSandbox'),
           'approval':conditions.get('approvalPolicy'),'confirmation':conditions.get('confirmationMode'),
           'os':conditions.get('os'),'environment':group.get('environmentVersion')}[key]
    return missing if value in (None,'') else str(value)


def audit_condition_rows(record, language):
    missing='Not recorded' if language=='en' else '未记录'
    rows=[]
    tested=record.get('presentation',{}).get('testedOn')
    if tested:
        value=f'{tested["date"]} ({tested["timezone"]})'
        rows.append(('Test date' if language=='en' else '测试时间',value,value))
    for key,label in AUDIT_CONDITION_LABELS[language]:
        rows.append((label,audit_condition_value(record,record['groups']['native'],key,missing),
                     audit_condition_value(record,record['groups']['finshield'],key,missing)))
    return rows


def page_audit_index(record):
    items=[]
    def add(path, english, chinese):
        items.append({'file':path,'location':'page','proves':{'en':english,'zh-CN':chinese}})
    add('evidence.json','Structured original packet. English and Chinese pages share this file.','结构化原文包。中文页和英文页共用这一份。')
    add('export-manifest.json','SHA-256 of every exported file.','每个导出文件的 SHA-256。')
    for name in record.get('presentation',{}).get('evidenceFiles',[]):
        add(name,'Reviewed provenance sidecar.','已评审的来源说明文件。')
    return items


def merged_audit_index(record, audit):
    ordered=[];by_file={}
    def add(item):
        name=item['file']
        if name in by_file:
            by_file[name]=item
            return
        by_file[name]=item
        ordered.append(name)
    for item in page_audit_index(record):
        add(item)
    for item in audit.get('index',[]):
        add(item)
    return [by_file[name] for name in ordered]


def audit_location_label(location, language):
    return AUDIT_LOCATION[location][0 if language=='en' else 1]


def render_audit_section(record, language, presentation, disclosure):
    audit=presentation['audit']
    names={name:presentation['groups'][name]['title'][language] for name in ('native','finshield')}
    body=f'<p>{e(audit["identity"][language])}</p>'
    cond='<table class="facts"><thead><tr><th></th>'+''.join(f'<th>{e(names[name])}</th>' for name in ('native','finshield'))+'</tr></thead><tbody>'
    for label,left,right in audit_condition_rows(record, language):
        cond+=f'<tr><td>{e(label)}</td><td>{e(left)}</td><td>{e(right)}</td></tr>'
    cond+='</tbody></table>'
    scripts=audit.get('scripts') or []
    if scripts:
        script_html='<ul>'+''.join(f'<li><code>{e(item["path"])}</code> — {e(item["role"][language])}</li>' for item in scripts)+'</ul>'
    else:
        script_html='<p>'+e('No side script. The Agent tool produced the visible effect.' if language=='en' else '无侧栏脚本。可见效果由 Agent 工具产生。')+'</p>'
    repro=f'<pre tabindex="0">{e(presentation["reproduction"][language])}</pre>' if 'reproduction' in presentation else ''
    recording=f'<p>{e(audit["recording"][language])}</p>' if 'recording' in audit else ''
    body+=disclosure('How to reproduce' if language=='en' else '如何复现',cond+script_html+repro+recording)
    pointer='<p>'+e('The prompt, public replies, and tool logs are in sections 04 and 05. Pictures are in sections 01 and 03.' if language=='en' else '提示词、公开回复和工具日志在第 04、05 节。画面在第 01、03 节。')+'</p>'
    table='<table><thead><tr><th>'+e('File' if language=='en' else '文件')+'</th><th>'+e('Purpose' if language=='en' else '用来核什么')+'</th><th>'+e('Where' if language=='en' else '位置')+'</th></tr></thead><tbody>'
    for item in merged_audit_index(record, audit):
        name=item['file']
        file_html=f'<a href="{e(name)}">{e(name)}</a>' if item['location']=='page' else f'<code>{e(name)}</code>'
        table+=f'<tr><td>{file_html}</td><td>{e(item["proves"][language])}</td><td>{e(audit_location_label(item["location"],language))}</td></tr>'
    table+='</tbody></table>'
    private='<p class="fine">'+e('dsh.log, reasoning, and token logs stay in the raw run directory and are not published.' if language=='en' else 'dsh.log、推理内容和 token 日志留在原始运行目录，不公开。')+'</p>'
    limits=''
    if audit.get('limits'):
        limits='<ul>'+''.join(f'<li>{e(item[language])}</li>' for item in audit['limits'])+'</ul>'
    body+=disclosure('Audit index' if language=='en' else '审计清单',pointer+table+private+limits)
    return body


def warning_label(level, basis, language):
    labels = {
        'adequate': ('告警充分', 'Warning sufficient'),
        'partial': ('告警不全', 'Warning incomplete'),
        'insufficient': ('告警不足', 'Warning insufficient'),
        'not-required': ('无需评估告警', 'Warning review not required'),
    }
    if level == 'insufficient' and basis == 'confirmed-no-warning':
        return '无告警' if language == 'zh-CN' else 'No warning'
    return labels.get(level, ('', ''))[0 if language == 'zh-CN' else 1]


def grade(group, language):
    assessment=(group or {}).get('warningAssessment') or {'level':'unassessed','reason':{language:''}}
    label=warning_label(assessment['level'], assessment.get('basis'), language)
    if not label:return ''
    absent=' warning-absent' if assessment.get('basis')=='confirmed-no-warning' else ''
    return f'<span class="grade{absent}" data-warning-level="{assessment["level"]}">{e(label)}</span>'


def assessment_markup(group, language):
    action=(group or {}).get('interceptionAssessment')
    warning_reason=e((group or {}).get('warningAssessment',{}).get('reason',{}).get(language,''))
    if not action:
        title='Assessment basis' if language=='en' else '评估依据'
        status=grade(group,language)
        body='<div class="assessment-status">'+status+'</div>' if status else ''
        if warning_reason:body+=f'<details class="assessment-evidence"><summary>{title}</summary><p>{warning_reason}</p></details>'
        return body
    labels=({'blocked':'Blocked','not-blocked':'Not blocked','unknown':'Unverified'} if language=='en'
            else {'blocked':'已拦截','not-blocked':'未拦截','unknown':'待核实'})
    status=labels[action['status']]
    reasons=f'<p>{e(action["reason"][language])}</p>'
    if action['basis']=='verified-postcondition':
        effect=action['postcondition']['effect'][language]
        reasons='<p>'+e('Prevented: '+effect if language=='en' else '已阻止'+effect)+'</p>'+reasons
    body=f'<div class="assessment-status" data-interception-state="{action["status"]}"><span class="interception-badge {action["status"]}">{e(status)}</span>'
    if action['status']=='not-blocked':
        body+=grade(group,language)
        reasons+=f'<p>{warning_reason}</p>'
    elif action['status']=='blocked':
        body+='<span class="assessment-note">'+warning_label('not-required',None,language)+'</span>'
    body+='</div>'
    return body+'<details class="assessment-evidence"><summary>'+('Assessment basis' if language=='en' else '评估依据')+'</summary>'+reasons+'</details>'


def shell(title, language, body, dense=False, home_href='index.html', navigation=None):
    ui=TEXT[language]
    categories=(navigation or {}).get('categories')
    header=site_header_markup(language, home_href, ui['locale_path'], ui['locale'],
        categories=categories, current_category=(navigation or {}).get('categoryId'),
        brand_mark=bool(categories))
    return ('<!doctype html><html lang="'+language+'"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; img-src \'self\'; media-src \'self\' blob:; style-src \'self\'; script-src \'self\'; object-src \'none\'">'
        f'<title>{e(title)} · Agent Safety Arena</title><link rel="stylesheet" href="report.css">'
        +('<link rel="stylesheet" href="detail-compact.css">' if dense else '')+'</head><body>'
        +header+'<main>'+body+'</main><script src="report.js" defer></script></body></html>')


def display_text(record, language, original, original_language, translation):
    """Show this page's language. Keep the other language out of the page body."""
    if language=='zh-CN' and original_language!='zh-CN' and translation:
        return translation, False
    if language=='en' and original_language not in {'en','en-US'} and translation:
        return translation, False
    return original, True


def render_index(record):
    cards=[]
    for language in ('en','zh-CN'):
        text=record['narrative'][language];ui=TEXT[language]
        phase=ui['development'] if record['phase']!='formal' else record['phase']
        cards.append(f'<a class="case-card" href="{language}.html" lang="{language}"><span class="chip">{e(phase)}</span>'
            f'<h2>{e(page_title(text["title"]))}</h2><p>{e(text["purpose"])}</p>{assessment_markup(record["groups"]["native"],language)}'
            f'<p>{ui["detail"]} →</p></a>')
    return shell('Results','en','<div class="hero"><h1>Results</h1></div><div class="pair">'+''.join(cards)+'</div>')


def render_detail(record, language, evidence_hash, pair, words, outcomes, navigation=None):
    ui=TEXT[language];text=record['narrative'][language];groups=record['groups'];native=groups['native']
    presentation=record.get('presentation');compact=bool(presentation)
    dense=bool((presentation or {}).get('dense'));overview=(presentation or {}).get('overview')
    condition=(native or {}).get('conditions',{})
    names={name:presentation['groups'][name]['title'][language] if compact else words[name] for name in groups}
    def empty():return f'<div class="empty" data-state="not-run"><strong>{ui["missing"]}</strong><span>{ui["blank"]}</span></div>'
    def section(index, body):return f'<section class="panel" id="section-{index}" data-section="{index}"><h2>{e(words["sections"][index-1])}</h2>{body}</section>'
    def copy_button(identifier):return f'<button class="copy" data-copy="{identifier}" data-copied="{ui["copied"]}">{ui["copy"]}</button>'
    def original(identifier, content):return f'<pre id="{identifier}" tabindex="0">{e(content)}</pre>'
    def disclosure(title,content):return f'<details><summary>{title}</summary>{content}</details>'
    def media(name, preview=False):
        if groups[name] is None:return empty()
        items=[m for m in record['publicMedia'] if m['group']==name
               and (not compact or (m['path'].lower().endswith('.gif') == preview))]
        posters={str(PurePosixPath(m['path']).with_suffix('.png')) for m in items if m['kind']=='video'}
        images={m['path'] for m in items if m['kind']=='image'}
        output=[]
        for item in items:
            path=item['path'];caption=item['caption'][language]
            if item['kind']=='image' and path in posters:continue
            if item['kind']=='video':
                poster=str(PurePosixPath(path).with_suffix('.png'))
                attr=f' poster="{e(poster)}"' if poster in images else ''
                element=f'<div class="video-frame"><video controls preload="none" playsinline{attr} aria-label="{e(caption)}"><source src="{e(path)}" type="video/mp4"></video></div>'
                kind=''
            else:
                element=f'<a href="{e(path)}" target="_blank" rel="noopener" aria-label="{ui["open_image"]}"><img src="{e(path)}" alt="{e(caption)}" loading="lazy"></a>'
                kind='' if path.lower().endswith('.gif') else ' class="still"'
            caption_html=(disclosure('Video notes' if language=='en' else '视频说明',f'<p>{e(caption)}</p>')
                          if dense and item['kind']=='video' else f'<figcaption>{e(caption)}</figcaption>')
            output.append(f'<figure{kind}>{element}{caption_html}</figure>')
        if dense and not preview:
            videos=[item for item in output if '<video ' in item]
            stills=[item for item in output if '<video ' not in item]
            return ''.join(videos)+(disclosure('Original screenshots' if language=='en' else '原始截图',''.join(stills)) if stills else '')
        return ''.join(output)
    if navigation:
        current = navigation['agentLabel'] + ('详情' if language == 'zh-CN' else ' details')
        body = breadcrumb_markup(language, (
            (navigation['homeHref'], '首页' if language == 'zh-CN' else 'Home'),
            (navigation['categoryHref'], navigation['categoryLabel']),
            (navigation['caseHref'], navigation['caseLabel']),
        ), current)
    else:
        body = '' if dense else f'<a class="fine" href="index.html">← {ui["back"]}</a>'
    title=page_title(text['title'])
    body += '<div class="hero">'
    if not dense:body+=f'<div class="eyebrow">{e(record["agentId"])} / {e(record["scenarioId"])}</div>'
    body+=f'<h1>{e(title)}</h1><p class="lead">{e(text["purpose"])}</p>'
    phase=ui['development'] if record['phase']!='formal' else record['phase']
    if compact:
        chips=[f'{label}：{value}' for label,value in header_metadata(record,language)]
    else:
        chips=[phase,condition.get('agentVersion',''),condition.get('model','')]
    if record['evidenceOrigin']=='synthetic':chips.append(ui['synthetic'])
    if dense:
        metadata=header_metadata(record,language)
        short_model=metadata[2][1]
        if ' / ' not in short_model:short_model=short_model.split(' · ')[0].rsplit('/',1)[-1]
        body+='<p class="metadata-row">'+e(' · '.join([
            metadata[0][1].split(' (')[0],f'{record["agentId"].upper()} {metadata[1][1]}',
            short_model,f'FinShield {metadata[3][1]}']))+'</p></div>'
    else:
        body+='<div class="chips">'+''.join(f'<span class="chip">{e(ui.get("chips",{}).get(v,v))}</span>' for v in chips if v)+'</div></div>'
    if compact and pair.get('differences'):
        mismatch=('Recorded configuration differs between default protection and FinShield. '
                  'This pair does not isolate FinShield causality.' if language=='en'
                  else '默认防护与 FinShield 两侧记录配置不同；该对照不能单独归因于 FinShield。')
        body+=f'<div class="condition-banner" role="note">{e(mismatch)}</div>'
    body+='<nav class="nav" aria-label="'+e(ui['sections_nav'])+'">'+''.join(f'<a href="#section-{i+1}">{e(label)}</a>' for i,label in enumerate(words['sections']))+'</nav>'
    if compact and overview:
        item=next(m for m in record['publicMedia'] if m['group']=='comparison' and m['path']==overview['media'])
        scenario=f'<p>{e(text["impact"])}</p><div class="overview-headings">'+''.join(
            f'<div><strong>{e(names[name])}</strong><span>{e(overview["results"][name][language])}</span></div>' for name in groups)+'</div>'
        scenario+=f'<figure class="overview-media"><a href="{e(item["path"])}" target="_blank" rel="noopener"><img src="{e(item["path"])}" alt="{e(item["caption"][language])}"></a></figure>'
        note=f'<p>{e(text["scenario"])}</p><p>{e(text.get("observedImpact",""))}</p><p>{e(item["caption"][language])}</p>'
        scenario+=disclosure('Run notes' if language=='en' else '运行说明',note)
    elif compact:
        labels=(['Possible impact','Test scope','Recorded observation'] if language=='en'
                else ['可能影响','测试范围','本次观察'])
        scenario=(f'<p><strong>{labels[0]}：</strong>{e(text["impact"])}</p>'
                  f'<p><strong>{labels[1]}：</strong>{e(text["scenario"])}</p>')
        if text.get('observedImpact'):
            scenario+=f'<p class="muted"><strong>{labels[2]}：</strong>{e(text["observedImpact"])}</p>'
    else:
        scenario=f'<p>{e(text["scenario"])}</p><p class="muted">{e(text["impact"])}</p>'
    if compact and not overview:
        scenario+='<div class="pair">'+''.join(
            f'<div class="group"><div class="group-title">{e(names[name])}</div>'
            f'<p class="fine">{e(presentation["agentLabel"][language])} · '
            f'{e(" · ".join(presentation["groups"][name]["configuration"]))}</p>{media(name,True)}</div>'
            for name in groups)+'</div>'
    body+=section(1,scenario)
    grading=[]
    for name,group in groups.items():
        content=empty() if group is None else assessment_markup(group,language)
        grading.append(f'<div class="group"><div class="group-title">{e(names[name])}</div>{content}</div>')
    table='<table><thead><tr><th></th>'+''.join(f'<th>{e(name)}</th>' for name in names.values())+'</tr></thead><tbody>'
    if compact:
        for key,label in [('configuration','Configuration' if language=='en' else '配置'),
                          ('effect','Picture' if language=='en' else '画面'),
                          ('toolSummary','Tool' if language=='en' else '工具')]:
            table+=f'<tr><td>{label}</td>'
            for name,group in groups.items():
                display=presentation['groups'][name]
                value=(' · '.join(display['configuration']) if key=='configuration'
                       else display['toolSummary'][language] if key=='toolSummary'
                       else text.get('outcomeTranslations',{}).get(name,{}).get(key,group['outcomes'][key])) if group else '—'
                note=''
                if key=='configuration' and display.get('configurationNote'):
                    label='Configuration note' if language=='en' else '配置说明'
                    note=f'<details class="configuration-note"><summary aria-label="{label}">ⓘ</summary><p>{e(display["configurationNote"][language])}</p></details>'
                table+=f'<td>{e(value)}{note}</td>'
            table+='</tr>'
    else:
        for key in ('agentDecision','enforcement','approval','effect','completion'):
            table+=f'<tr><td>{ui["fields"][outcomes.index(key)]}</td>'+''.join(f'<td>{e(text.get("outcomeTranslations",{}).get(name,{}).get(key,group["outcomes"][key])) if group else "—"}</td>' for name,group in groups.items())+'</tr>'
    table+='</tbody></table>'
    limitations=f'<details><summary>{words["limits"]}</summary><ul>'+''.join(f'<li>{e(v)}</li>' for v in text['limitations'])+'</ul></details>'
    scope=ui['scope']
    if any(group and group.get('interceptionAssessment') for group in groups.values()):
        scope='Assess interception first; assess warnings if the effect was not blocked.' if language=='en' else '先看是否拦截，未拦截再评预警。'
    summary='<div class="pair assessment-pair">'+''.join(grading)+'</div>'
    comparison_body='<p class="fine">'+scope+'</p>'+table+('' if compact else limitations)
    if dense:
        metadata='<p class="fine">'+e(' · '.join(f'{k}: {v}' for k,v in header_metadata(record,language)))+'</p>'
        comparison_body=disclosure('Execution, warnings and configuration' if language=='en' else '执行、提醒与配置',metadata+comparison_body)
    body+=section(2,summary+comparison_body)
    body+=section(3,'<div class="pair">'+''.join(f'<div class="group"><div class="group-title">{e(names[name])}</div>{media(name)}</div>' for name in groups)+'</div>')
    prompts=[]
    for name,group in groups.items():
        if group is None:continue
        prompt=group.get('prompt',record['prompt'])
        if any(p['sha256']==prompt['sha256'] for _,p in prompts):continue
        prompts.append((name,prompt))
    prompt_body=''
    for name,prompt in prompts or [('native',record['prompt'])]:
        identifier='prompt-'+name
        shown,is_original=(prompt['text'],True) if compact else display_text(record,language,prompt['text'],prompt.get('language'),text.get('promptTranslation'))
        label=ui['original'] if is_original else ui['translation']
        prompt_body+=f'<div class="tools"><span class="fine">{label} · {e(prompt["revision"])}</span>{copy_button(identifier)}</div>'+original(identifier,shown)
        if not is_original:prompt_body+=f'<p class="fine">{ui["stored"]}</p>'
        prompt_body+=f'<p class="fine">SHA-256: {e(prompt["sha256"])}</p>'
    shown_prompts=prompts or [('native',record['prompt'])]
    guide=(presentation or {}).get('promptGeneration')
    if guide:
        note='<p class="prompt-code-note">'+'<br>'.join(e(line) for line in GENERATION_CODE_NOTE[language])+'</p>'
        generation_body='<div class="tools"><span class="fine">'+e('Generate window-flood.py and save it' if language=='en' else '先生成 window-flood.py 并保存')+'</span>'+copy_button('generation-prompt')+'</div>'+original('generation-prompt',guide['generationPrompt'])
        generation_body+='<p class="fine">'+e('Then run the saved script with the execution prompt below' if language=='en' else '保存后，使用下面的运行 Prompt 执行脚本')+'</p>'
        if guide.get('fixedScript'):
            prompt_body+='<div class="tools"><span class="fine">'+e('Saved Python script' if language=='en' else '已保存的 Python 脚本')+'</span>'+copy_button('fixed-script')+'</div>'+original('fixed-script',guide['fixedScript'])
            prompt_body+='<p class="fine">SHA-256: '+e(guide['fixedScriptSha256'])+'</p>'
        body+=section(4,note+disclosure('1. Generate and save the Python script' if language=='en' else '1. 生成并保存 Python 脚本',generation_body)+disclosure('2. View the Agent execution prompt' if language=='en' else '2. 查看 Agent 运行 Prompt',prompt_body))
    else:
        body+=section(4,prompt_code_note(language,shown_prompts)+(disclosure('Original submitted prompt' if language=='en' else '查看原始提示词',prompt_body) if dense else prompt_body))
    replies=[]
    for name,group in groups.items():
        content=empty()
        if group:
            identifier='reply-'+name
            shown,is_original=(group['reply']['text'],True) if compact else display_text(record,language,group['reply']['text'],group['reply'].get('language'),text.get('replyTranslations',{}).get(name))
            label=ui['original'] if is_original else ui['translation']
            visible=shown if shown.strip() else ui['no_reply']
            content=f'<div class="tools"><span class="fine">{label}</span>{copy_button(identifier)}</div>'+f'<pre class="reply" id="{identifier}">{e(visible)}</pre>'
            if not is_original:content+=f'<p class="fine">{ui["stored"]}</p>'
            for supplement in group['supplementaryReplies']:content+=f'<details><summary>{words["supplement"]}</summary><pre>{e(supplement["text"])}</pre></details>'
            if 'toolLog' in group:
                tool_title='Full tool log' if language=='en' else '完整工具日志'
                content+=f'<details><summary>{tool_title}</summary><p><a href="{name}-tools.txt" download>{tool_title} (.txt)</a></p><pre tabindex="0">{e(group["toolLog"]["text"])}</pre></details>'
        if dense:content=disclosure('Original reply and tool log' if language=='en' else '查看原始回复与工具日志',content)
        replies.append(f'<div class="group"><div class="group-title">{e(names[name])}</div>{content}</div>')
    body+=section(5,'<div class="pair">'+''.join(replies)+'</div>')
    if compact and presentation.get('audit'):
        evidence_body=render_audit_section(record,language,presentation,disclosure)
    else:
        conclusion=f'<p>{e(text["summary"])}</p>'
        evidence_body=(disclosure('Findings and limits' if language=='en' else '结论与证据说明',conclusion) if dense else conclusion)+(limitations if compact else '')
        if compact and 'reproduction' in presentation:
            title='Reproduction steps' if language=='en' else '复现方法'
            evidence_body+=f'<details><summary>{title}</summary><pre tabindex="0">{e(presentation["reproduction"][language])}</pre></details>'
        evidence_body+=f'<p><a href="evidence.json">{ui["evidence_note"]}</a></p>'
        if compact:
            evidence_body+=''.join(f'<p><a href="{e(name)}">{e(name)}</a></p>' for name in presentation.get('evidenceFiles',[]))
    body+=section(6,evidence_body)
    if navigation:
        body += f'<a class="report-return" href="{e(navigation["caseHref"])}">← '+('返回场景评测' if language == 'zh-CN' else 'Back to scenario')+'</a>'
    body+=f'<footer>{ui["hash_label"]}: {e(evidence_hash)}</footer>'
    return shell(title,language,body,dense,navigation['homeHref'] if navigation else 'index.html', navigation)
