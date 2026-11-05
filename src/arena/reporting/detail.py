"""Local comparison pages from the existing reviewed-record contract."""
from html import escape
import json
from pathlib import PurePosixPath


TEXT = {
    'en': dict(back='All cases', evidence='Evidence', missing='Not tested', blank='No trial or conclusion is available.',
        conditions='Run conditions', comparison='Comparison incomplete', development='Development trial',
        synthetic='Synthetic evidence', grade='Warning adequacy', reason='Assessment basis',
        grades={'adequate':('A','Adequate'),'partial':('B','Partial'),'insufficient':('C','Insufficient'),'unassessed':('U','Unassessed')},
        fields=['Task','Agent decision','Approval','Visible effect','Enforcement','Completion','Evidence','Recovery'],
        copy='Copy original', copied='Copied', original='Original', translation='Display translation',
        no_reply='No public reply was recorded.', evidence_note='Original warnings, conditions and observations',
        open_image='Open original screenshot', locale='简体中文', locale_path='zh-CN.html',
        shared='Shared original evidence · local report', detail='View result', scope='This grade evaluates the warning, not action severity or sandbox strength.'),
    'zh-CN': dict(back='全部案例', evidence='证据', missing='未测试', blank='尚无试验素材或结论。',
        conditions='运行条件', comparison='对比尚未完成', development='开发试录', synthetic='合成证据',
        grade='警示充分度', reason='评级依据',
        grades={'adequate':('A','充分'),'partial':('B','部分'),'insufficient':('C','不足'),'unassessed':('U','未评估')},
        fields=['请求任务','Agent 决定','原生审批','可见效果','沙箱执行','完成状态','证据边界','资源恢复'],
        copy='复制原文', copied='已复制', original='原文', translation='展示翻译',
        no_reply='没有记录到公开回复。', evidence_note='原始提示、条件与观测记录',
        open_image='打开原始截图', locale='English', locale_path='en.html', shared='共用原始证据 · 本地结果页',
        detail='查看结果', scope='本等级评价提示是否充分，不代表操作危险程度或沙箱强度。')}


CSS = """
:root{font-family:'Segoe UI Variable Text','Segoe UI','Microsoft YaHei',sans-serif;color:#243248;background:#f4f6f9;font-size:14px;line-height:1.65;color-scheme:light}
*{box-sizing:border-box}body{margin:0}a{color:#285dbb;text-decoration:none}a:hover{text-decoration:underline}
main,.bar{max-width:1000px;margin:auto;padding:24px 22px}.bar{display:flex;align-items:center;justify-content:space-between;padding-top:17px;padding-bottom:17px}
header{background:white;border-bottom:1px solid #dde3eb}.brand{color:#22324b;font-weight:650;letter-spacing:.1px}.bar small{color:#778397;margin-left:12px}
h1{font-size:24px;line-height:1.35;margin:12px 0 10px;color:#172b4a}h2{font-size:18px;margin:0 0 16px}h3{font-size:14px;margin:0 0 10px}p{margin:8px 0;white-space:pre-line}
.eyebrow{color:#69809e;font-size:12px;letter-spacing:.08em;text-transform:uppercase}.muted,figcaption{color:#69798d}.lead{color:#56687e;max-width:760px}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:15px 0}.chip{display:inline-flex;padding:3px 9px;border:1px solid #e0e5ed;border-radius:5px;color:#516479;background:#f8fafc;font-size:12px}
.hero{padding:4px 0 10px}.panel{background:white;border:1px solid #e0e6ee;border-radius:10px;padding:22px;margin:16px 0;scroll-margin-top:75px}
.nav{position:sticky;top:0;z-index:10;display:flex;gap:18px;overflow:auto;background:#f4f6f9f5;border-bottom:1px solid #dfe5ed;padding:13px 0;backdrop-filter:blur(8px);white-space:nowrap;font-size:12px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:18px}.group{min-width:0}.group-title{padding:0 0 10px;border-bottom:1px solid #e7ebf1;margin-bottom:12px;font-weight:600}
.empty{background:#fafbfd;border:1px dashed #dce2eb;border-radius:8px;min-height:230px;display:flex;flex-direction:column;justify-content:center;align-items:center;color:#8a97a9;padding:26px;text-align:center}.empty strong{color:#7a899e;font-weight:500}
.grade-row{display:flex;align-items:center;gap:12px;margin-bottom:12px}.grade{display:inline-flex;align-items:center;gap:8px;padding:4px 11px;border-radius:6px;font-weight:650;border:1px solid #e3e7ee;background:#f3f5f8;color:#55657b}
.grade[data-warning-level="insufficient"]{background:#fff3e8;border-color:#f3d6ba;color:#97511c}.grade[data-warning-level="adequate"]{background:#eaf5ee;border-color:#c6e1cf;color:#316746}.grade[data-warning-level="partial"]{background:#fff8df;border-color:#eadba4;color:#806113}
.grade-reason{font-size:14px;color:#475c74;margin-bottom:12px}.fine{font-size:12px;color:#78869a;overflow-wrap:anywhere}
table{width:100%;border-collapse:collapse;text-align:left;table-layout:fixed}th,td{padding:10px 11px;border-bottom:1px solid #e9edf2;vertical-align:top;overflow-wrap:anywhere}th{color:#65758c;font-weight:500;background:#f8fafc}th:first-child{width:18%}.facts td:first-child{color:#64748b;width:26%}.facts td{padding-left:0}
figure{margin:0 0 22px}video,img{display:block;width:100%;max-width:100%;border-radius:7px;border:1px solid #e3e8ef}video{aspect-ratio:16/9;background:#e9edf3}figcaption{font-size:12px;line-height:1.5;margin-top:8px;white-space:pre-line}.still img{max-height:420px;object-fit:contain;background:#f8fafc}
pre{font-family:'Cascadia Code',Consolas,monospace;font-size:12px;background:#f7f9fc;border:1px solid #e6ebf2;border-radius:7px;padding:15px;white-space:pre-wrap;overflow-wrap:anywhere;margin:12px 0;line-height:1.7}.reply{font-family:inherit;font-size:14px;background:transparent;border:0;padding:0}
.tools{display:flex;justify-content:space-between;align-items:center;gap:8px}.copy{font:inherit;font-size:12px;background:white;border:1px solid #dbe2ec;border-radius:5px;padding:4px 10px;color:#3e5c82;cursor:pointer}
details{border-top:1px solid #e8edf3;margin-top:16px;padding-top:14px}summary{cursor:pointer;color:#315e9a}li{margin:5px 0}footer{padding:20px 0 35px;color:#8a96a7;font-size:12px;overflow-wrap:anywhere}
:focus-visible{outline:3px solid #92b8f4;outline-offset:3px}.case-card{display:block;background:white;border:1px solid #dfe5ee;border-radius:9px;padding:20px;max-width:480px}.case-card h2{margin:10px 0}.case-card p{color:#63768e}
@media(max-width:760px){.pair{grid-template-columns:1fr}main,.bar{padding-left:16px;padding-right:16px}.panel{padding:16px}h1{font-size:21px}.bar small{display:none}.nav{gap:15px}th,td{padding:8px 6px}th:first-child{width:22%}.empty{min-height:130px}}
"""

JS = """document.addEventListener('click',async event=>{const b=event.target.closest('[data-copy]');if(!b)return;const t=document.getElementById(b.dataset.copy);if(!t)return;try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(t.textContent)}else{const r=document.createRange();r.selectNodeContents(t);const s=getSelection();s.removeAllRanges();s.addRange(r);document.execCommand('copy');s.removeAllRanges()}b.textContent=b.dataset.copied}catch{t.focus()}});"""


def e(value):
    return escape(str(value), quote=True)


def grade(group, language):
    ui=TEXT[language]
    assessment=(group or {}).get('warningAssessment') or {'level':'unassessed','reason':{language:''}}
    letter,label=ui['grades'][assessment['level']]
    return f'<span class="grade" data-warning-level="{assessment["level"]}">{letter} · {label}</span>'


def shell(title, language, body):
    ui=TEXT[language]
    return ('<!doctype html><html lang="'+language+'"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; img-src \'self\'; media-src \'self\'; style-src \'self\'; script-src \'self\'; object-src \'none\'">'
        f'<title>{e(title)} · Agent Safety Arena</title><link rel="stylesheet" href="report.css"></head><body>'
        f'<header><div class="bar"><a class="brand" href="index.html">Agent Safety Arena</a><small>{ui["shared"]}</small>'
        f'<a href="{ui["locale_path"]}" lang="{"en" if language=="zh-CN" else "zh-CN"}">{ui["locale"]}</a></div></header>'
        '<main>'+body+'</main><script src="report.js" defer></script></body></html>')


def render_index(record):
    text=record['narrative']['zh-CN'];ui=TEXT['zh-CN']
    return shell('案例结果','zh-CN',f'<div class="hero"><div class="eyebrow">EVALUATION RESULTS</div><h1>案例结果</h1></div>'
        f'<a class="case-card" href="zh-CN.html"><span class="chip">{ui["development"] if record["phase"]!="formal" else e(record["phase"])}</span>'
        f'<h2>{e(text["title"])}</h2><p>{e(text["purpose"])}</p>{grade(record["groups"]["native"],"zh-CN")}'
        f'<p>{ui["detail"]} →</p></a>')


def render_detail(record, language, evidence_hash, pair, words, outcomes):
    ui=TEXT[language];text=record['narrative'][language];groups=record['groups'];native=groups['native']
    condition=(native or {}).get('conditions',{})
    names={'native':words['native'],'finshield':words['finshield']}
    def empty():return f'<div class="empty" data-state="not-run"><strong>{ui["missing"]}</strong><span>{ui["blank"]}</span></div>'
    def section(index, body):return f'<section class="panel" id="section-{index}" data-section="{index}"><h2>{e(words["sections"][index-1])}</h2>{body}</section>'
    def copy_button(identifier):return f'<button class="copy" data-copy="{identifier}" data-copied="{ui["copied"]}">{ui["copy"]}</button>'
    def original(identifier, content):return f'<pre id="{identifier}" tabindex="0">{e(content)}</pre>'
    def media(name):
        if groups[name] is None:return empty()
        items=[m for m in record['publicMedia'] if m['group']==name]
        posters={str(PurePosixPath(m['path']).with_suffix('.png')) for m in items if m['kind']=='video'}
        images={m['path'] for m in items if m['kind']=='image'}
        output=[]
        for item in items:
            path=item['path'];caption=item['caption'][language]
            if item['kind']=='image' and path in posters:continue
            if item['kind']=='video':
                poster=str(PurePosixPath(path).with_suffix('.png'))
                attr=f' poster="{e(poster)}"' if poster in images else ''
                element=f'<video controls preload="none" playsinline{attr} aria-label="{e(caption)}"><source src="{e(path)}" type="video/mp4"></video>'
                kind=''
            else:
                element=f'<a href="{e(path)}" target="_blank" rel="noopener" aria-label="{ui["open_image"]}"><img src="{e(path)}" alt="{e(caption)}" loading="lazy"></a>'
                kind=' class="still"'
            output.append(f'<figure{kind}>{element}<figcaption>{e(caption)}</figcaption></figure>')
        return ''.join(output)
    body=f'<a class="fine" href="index.html">← {ui["back"]}</a><div class="hero"><div class="eyebrow">{e(record["agentId"])} / {e(record["scenarioId"])}</div><h1>{e(text["title"])}</h1><p class="lead">{e(text["purpose"])}</p><div class="chips">'
    chips=[ui['development'] if record['phase']!='formal' else record['phase']]
    if record['evidenceOrigin']=='synthetic':chips.append(ui['synthetic'])
    chips += [condition.get('agentVersion',''),condition.get('model',''),condition.get('builtinSandbox',''),condition.get('approvalPolicy','')]
    body+=''.join(f'<span class="chip">{e(v)}</span>' for v in chips if v)+'</div></div>'
    body+='<nav class="nav" aria-label="Sections">'+''.join(f'<a href="#section-{i+1}">{e(label)}</a>' for i,label in enumerate(words['sections']))+'</nav>'
    body+=section(1,f'<p>{e(text["scenario"])}</p><p class="muted">{e(text["impact"])}</p>')
    grading=[]
    for name,group in groups.items():
        content=empty() if group is None else f'<div class="grade-row"><span>{ui["grade"]}</span>{grade(group,language)}</div><p class="grade-reason">{e(group.get("warningAssessment",{}).get("reason",{}).get(language,""))}</p>'
        grading.append(f'<div class="group"><div class="group-title">{names[name]}</div>{content}</div>')
    table='<table><thead><tr><th></th>'+''.join(f'<th>{name}</th>' for name in names.values())+'</tr></thead><tbody>'
    for key in ('agentDecision','enforcement','approval','effect','completion'):
        table+=f'<tr><td>{ui["fields"][outcomes.index(key)]}</td>'+''.join(f'<td>{e(text.get("outcomeTranslations",{}).get(name,{}).get(key,group["outcomes"][key])) if group else "—"}</td>' for name,group in groups.items())+'</tr>'
    table+='</tbody></table>'
    body+=section(2,'<div class="pair">'+''.join(grading)+'</div><p class="fine">'+ui['scope']+'</p>'+table+f'<details><summary>{words["limits"]}</summary><ul>'+''.join(f'<li>{e(v)}</li>' for v in text['limitations'])+'</ul></details>')
    body+=section(3,'<div class="pair">'+''.join(f'<div class="group"><div class="group-title">{names[name]}</div>{media(name)}</div>' for name in groups)+'</div>')
    prompts=[]
    for name,group in groups.items():
        if group is None:continue
        prompt=group.get('prompt',record['prompt'])
        if any(p['sha256']==prompt['sha256'] for _,p in prompts):continue
        prompts.append((name,prompt))
    prompt_body=''
    for name,prompt in prompts or [('native',record['prompt'])]:
        identifier='prompt-'+name
        prompt_body+=f'<div class="tools"><span class="fine">{ui["original"]} · {e(prompt["language"])} · {e(prompt["revision"])}</span>{copy_button(identifier)}</div>'+original(identifier,prompt['text'])+f'<p class="fine">SHA-256: {e(prompt["sha256"])}</p>'
    if text.get('promptTranslation'):prompt_body+=f'<details><summary>{ui["translation"]}</summary><p>{e(text["promptTranslation"])}</p></details>'
    body+=section(4,prompt_body)
    replies=[]
    for name,group in groups.items():
        content=empty()
        if group:
            identifier='reply-'+name;reply=group['reply']['text']
            content=f'<div class="tools"><span class="fine">{ui["original"]} · {e(group["reply"]["language"])}</span>{copy_button(identifier)}</div>'+f'<pre class="reply" id="{identifier}">{e(reply) if reply.strip() else ui["no_reply"]}</pre>'
            translation=text.get('replyTranslations',{}).get(name)
            if translation:content+=f'<details><summary>{ui["translation"]}</summary><p>{e(translation)}</p></details>'
            for supplement in group['supplementaryReplies']:content+=f'<details><summary>{words["supplement"]}</summary><pre>{e(supplement["text"])}</pre></details>'
        replies.append(f'<div class="group"><div class="group-title">{names[name]}</div>{content}</div>')
    body+=section(5,'<div class="pair">'+''.join(replies)+'</div>')
    evidence=dict(comparison=pair,groups=groups)
    body+=section(6,f'<p>{e(text["summary"])}</p><details><summary>{ui["evidence_note"]}</summary><pre>{e(json.dumps(evidence,ensure_ascii=False,indent=2))}</pre><a href="evidence.json">evidence.json</a></details>')
    body+=f'<footer>{ui["shared"]}<br>Evidence SHA-256: {e(evidence_hash)}</footer>'
    return shell(text['title'],language,body)
