"""Export translated narrative around one immutable, reviewed evidence set."""
from copy import deepcopy
import hashlib
from html import escape
import json
from pathlib import Path
import re

from arena.evidence.media import resolve_public_media_sources, copy_public_media
from arena.runner.suite import compare_conditions, CONDITION_KEYS
from arena.runner.trial import save


OUTCOMES=('task','agentDecision','approval','effect','enforcement','completion','evidence','recovery')
TOP_FIELDS={'schemaVersion','reviewStatus','evidenceOrigin','scenarioId','agentId','phase','prompt','groups','narrative','publicMedia'}
GROUP_FIELDS={'runId','environmentVersion','conditions','outcomes','reply','supplementaryReplies','evidenceReferences'}
WORDS={
 'en':dict(sections=['01 Scenario and impact','02 Observed comparison and limits','03 Reviewed media',
                    '04 Submitted prompts','05 Verified public replies','06 Summary and evidence'],
           native='Built-in controls',finshield='Built-in controls + FinShield',missing='Not run; no replacement evidence.',
           translation='Display translation — not the submitted text',original='Original',reply='Matched-turn public reply',
           supplement='Separate supplementary reply',limits='Limitations',synthetic='SYNTHETIC — not a live Agent or OS test',
           development='Development / exploratory evidence; excluded from formal counts',
           evidence='Evidence and conditions',shared='Both report languages share the same original evidence and media.'),
 'zh-CN':dict(sections=['01 场景与影响','02 观察对比与限制','03 已评审展示媒体','04 实际提交的提示词',
                       '05 核对后的公开回复','06 总结与证据'],native='内置控制',finshield='内置控制＋FinShield',
           missing='未运行；没有替代证据。',translation='展示翻译——不是实际提交的原文',original='原文',
           reply='匹配原始请求的公开回复',supplement='单独列出的补充回复',limits='限制',synthetic='合成数据——不是真实 Agent 或系统试验',
           development='开发／探索性证据，不计入正式试验分母',evidence='证据与条件',shared='中英文报告共用同一份原始证据和展示媒体。')}


def plain(value):
    return re.sub(r'([\\`*_{}\[\]()#!|])',r'\\\1',escape(str(value),quote=False))


def block(text):
    fence='`'*max(3,max((len(m.group())+1 for m in re.finditer(r'`+',text)),default=3))
    return fence+'text\n'+text+('' if text.endswith('\n') else '\n')+fence


def valid_prompt(prompt):
    if not isinstance(prompt,dict) or set(prompt)!={'text','language','revision','sha256'}:
        raise ValueError('Reviewed prompt requires original text, language, revision, and hash')
    if any(not isinstance(prompt[key],str) for key in prompt) or prompt['language'] not in {'en','zh-CN','und'}:
        raise ValueError('Invalid original prompt metadata')
    if hashlib.sha256(prompt['text'].encode('utf8')).hexdigest()!=prompt['sha256']:
        raise ValueError('Original prompt hash does not match its text')


def private_values(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key.lower() in {'apikey','cookie','authurl','startuplog','nativelog','reasoningtext','thinking'}:
                raise ValueError('Private logs, authentication, and reasoning are not public report fields')
            private_values(item)
    elif isinstance(value,list):
        for item in value:private_values(item)
    elif isinstance(value,str) and re.search(r'(?i)([a-z]:[\\/]users[\\/]|/(?:home|Users)/[^/]+/|[?&]token=|bearer\s+[A-Za-z0-9._~-]{8,})',value):
        raise ValueError('Private paths or authentication material require review and substitution before export')


def validate(record):
    if not isinstance(record,dict) or set(record)!=TOP_FIELDS or record.get('schemaVersion')!=1:
        raise ValueError('Unsupported bilingual reviewed-record fields or version')
    if record['reviewStatus']!='reviewed':raise ValueError('Only reviewed records may be exported')
    if record['evidenceOrigin'] not in {'live','synthetic'} or record['phase'] not in {'development','formal','language-study'}:
        raise ValueError('Declare evidence origin and evaluation phase')
    for key in ('scenarioId','agentId'):
        if not isinstance(record[key],str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*',record[key]):
            raise ValueError('Record identity must be a lowercase slug')
    private_values(record)
    valid_prompt(record['prompt'])
    if not isinstance(record['groups'],dict) or set(record['groups'])!={'native','finshield'}:
        raise ValueError('Declare native and finshield groups; use null for an unrun group')
    for group in record['groups'].values():
        if group is None:continue
        if not isinstance(group,dict) or not GROUP_FIELDS.issubset(group) or set(group)-GROUP_FIELDS-{'prompt','warningAssessment'}:
            raise ValueError('Invalid recorded group fields')
        if not isinstance(group['runId'],str) or not group['runId']:
            raise ValueError('Recorded group requires a run identity')
        if group['environmentVersion'] is not None and not isinstance(group['environmentVersion'],str):
            raise ValueError('Environment version must be text or null')
        if not isinstance(group['conditions'],dict) or set(group['conditions'])-set(CONDITION_KEYS):
            raise ValueError('Conditions contain unsupported raw fields')
        if any(value is not None and not isinstance(value,str) for value in group['conditions'].values()):
            raise ValueError('Condition values must be text or null')
        if group['conditions'].get('agentId') not in (None,record['agentId']):
            raise ValueError('An environment pair must refer to the same Agent')
        prompt=group.get('prompt',record['prompt']);valid_prompt(prompt)
        if group['conditions'].get('promptSha256')!=prompt['sha256']:
            raise ValueError('Each group must identify its actual original prompt')
        if not isinstance(group['outcomes'],dict) or set(group['outcomes'])!=set(OUTCOMES) or any(not isinstance(v,str) for v in group['outcomes'].values()):
            raise ValueError('Keep all eight factual outcome fields separate')
        if not isinstance(group['supplementaryReplies'],list) or not isinstance(group['evidenceReferences'],list) or any(not isinstance(v,str) for v in group['evidenceReferences']):
            raise ValueError('Invalid supplementary replies or evidence references')
        for reply in [group['reply'],*group['supplementaryReplies']]:
            if not isinstance(reply,dict) or set(reply)!={'text','language'} or not isinstance(reply['text'],str) or reply['language'] not in {'en','zh-CN','und'}:
                raise ValueError('Keep original public reply text and language together')
    if not isinstance(record['narrative'],dict) or set(record['narrative'])!={'en','zh-CN'}:
        raise ValueError('Supply reviewed English and Chinese narrative; no automatic translation')
    for language,text in record['narrative'].items():
        required={'title','purpose','scenario','impact','summary','limitations'}
        if not isinstance(text,dict) or not required.issubset(text) or set(text)-required-{'promptTranslation','replyTranslations','outcomeTranslations'}:
            raise ValueError('Unsupported report narrative fields')
        if any(not isinstance(text[k],str) for k in required-{'limitations'}) or not isinstance(text['limitations'],list) or any(not isinstance(v,str) for v in text['limitations']):
            raise ValueError('Narrative must contain text and a limitation list')
        if 'promptTranslation' in text and not isinstance(text['promptTranslation'],str):
            raise ValueError('Display prompt translation must be text')
        if 'replyTranslations' in text and (not isinstance(text['replyTranslations'],dict) or set(text['replyTranslations'])-{'native','finshield'} or any(not isinstance(v,str) for v in text['replyTranslations'].values())):
            raise ValueError('Display reply translations must be named text')
        if 'outcomeTranslations' in text:
            translations=text['outcomeTranslations']
            if (not isinstance(translations,dict) or set(translations)-{'native','finshield'}
                    or any(not isinstance(v,dict) or set(v)-set(OUTCOMES) or any(not isinstance(t,str) for t in v.values()) for v in translations.values())):
                raise ValueError('Outcome translations must name groups and factual outcome keys')
    if not isinstance(record['publicMedia'],list):raise ValueError('Reviewed public media must be a list')
    for media in record['publicMedia']:
        if not isinstance(media,dict) or set(media)!={'kind','path','group','caption'} or media['kind'] not in {'image','video'} or media['group'] not in {'native','finshield'} or not isinstance(media['caption'],dict) or set(media['caption'])!={'en','zh-CN'} or any(not isinstance(v,str) for v in media['caption'].values()):
            raise ValueError('Reviewed media requires a kind, group, safe path, and bilingual caption')
        if record['groups'][media['group']] is None:
            raise ValueError('Media cannot replace an unrun environment group')
        extensions={'.mp4'} if media['kind']=='video' else {'.png','.jpg','.jpeg','.webp'}
        if not isinstance(media['path'],str) or Path(media['path']).suffix.lower() not in extensions:
            raise ValueError('Public media must use a reviewed video or image filename, not a log')
    for name,group in record['groups'].items():
        if group is None or 'warningAssessment' not in group:continue
        assessment=group['warningAssessment']
        if (not isinstance(assessment,dict) or set(assessment)!={'level','reason','evidence'}
                or not isinstance(assessment['level'],str) or assessment['level'] not in {'adequate','partial','insufficient','unassessed'}
                or not isinstance(assessment['reason'],dict) or set(assessment['reason'])!={'en','zh-CN'}
                or any(not isinstance(v,str) or not v.strip() for v in assessment['reason'].values())):
            raise ValueError('Warning assessment requires a level and a short bilingual reason')
        images={m['path'] for m in record['publicMedia'] if m['kind']=='image' and m['group']==name}
        if not (assessment['level']=='unassessed' and assessment['evidence'] is None) and (not isinstance(assessment['evidence'],str) or assessment['evidence'] not in images):
            raise ValueError('An assessed warning requires an original reviewed image from its own group')


def comparison(record):
    groups=record['groups']
    if groups['native'] is None or groups['finshield'] is None:
        return dict(status='incomplete',reason='missing-group',differences={},unknown=[])
    result=compare_conditions(groups['native']['conditions'],groups['finshield']['conditions'])
    for name,group in groups.items():
        if group['environmentVersion'] in (None,'','unknown','unverified'):
            result['unknown'].append(name+'.environmentVersion')
            result['status']='incomplete'
    return result


def render(record,language,evidence_hash):
    words=WORDS[language];text=record['narrative'][language];groups=record['groups'];pair=comparison(record)
    status='Incomplete' if pair['status']!='matched' else 'Conditions matched; protection not scored'
    lines=['# '+plain(text['title']),'',plain(text['purpose']),'',
           f"Agent: {plain(record['agentId'])} · {plain(record['phase'])} · {status}",'',words['shared'],'']
    if record['evidenceOrigin']=='synthetic':lines += ['**'+words['synthetic']+'**','']
    if record['phase']!='formal':lines += [words['development'],'']
    lines += ['## '+words['sections'][0],'',plain(text['scenario']),'',plain(text['impact']),'',
              '## '+words['sections'][1],'',status,'',f"| Field | {words['native']} | {words['finshield']} |",'| --- | --- | --- |']
    for key in OUTCOMES:
        values=[plain(text.get('outcomeTranslations',{}).get(name,{}).get(key,groups[name]['outcomes'][key])) if groups[name] else words['missing'] for name in ('native','finshield')]
        lines.append('| '+key+' | '+' | '.join(values)+' |')
    from arena.reporting.detail import TEXT
    grade_values=[]
    for group in groups.values():
        if group is None:grade_values.append(words['missing']);continue
        assessment=group.get('warningAssessment',{})
        letter,label=TEXT[language]['grades'][assessment.get('level','unassessed')]
        grade_values.append(plain(letter+' · '+label+' — '+assessment.get('reason',{}).get(language,'')))
    lines.append('| '+TEXT[language]['grade']+' | '+' | '.join(grade_values)+' |')
    lines += ['',words['limits']+':','']+['- '+plain(item) for item in text['limitations']]
    lines += ['','## '+words['sections'][2],'']
    for name,group in groups.items():
        lines += ['### '+words[name],'']
        items=[item for item in record['publicMedia'] if item['group']==name]
        if group is None:lines.append(words['missing'])
        elif not items:lines.append('No reviewed media attached.' if language=='en' else '尚无已评审展示媒体。')
        for media in items:
            caption=plain(media['caption'][language]);path=media['path']
            lines.append(f'![{caption}]({path})' if media['kind']=='image' else f'[{caption}]({path})')
        lines.append('')
    lines += ['','## '+words['sections'][3],'']
    prompts=[(name,group.get('prompt',record['prompt'])) for name,group in groups.items() if group]
    if not prompts:prompts=[('native',record['prompt'])]
    if len({p['sha256'] for _,p in prompts})==1:prompts=prompts[:1]
    for name,prompt in prompts:
        if len(prompts)>1:lines += ['### '+words[name],'']
        lines += [f"{words['original']} · {prompt['language']} · {plain(prompt['revision'])}",'',block(prompt['text']),
                  '',f"SHA256: `{prompt['sha256']}`",'']
    if text.get('promptTranslation'):
        lines += [words['translation'],'',block(text['promptTranslation']),'']
    lines += ['## '+words['sections'][4],'']
    for name,group in groups.items():
        lines += ['### '+words[name],'']
        if group is None:lines += [words['missing'],''];continue
        if group['reply']['text'].strip():
            lines += [words['reply']+' · '+group['reply']['language'],'',block(group['reply']['text']),'']
        else:
            lines += ['No public reply recorded.' if language=='en' else '没有记录到公开回复。','']
        translation=text.get('replyTranslations',{}).get(name)
        if translation:lines += [words['translation'],'',block(translation),'']
        for reply in group['supplementaryReplies']:
            lines += [words['supplement']+' · '+reply['language'],'',block(reply['text']),'']
    lines += ['## '+words['sections'][5],'',plain(text['summary']),'',
        '<details><summary>'+words['evidence']+'</summary>','',
        block(json.dumps(dict(comparison=pair,groups=groups),ensure_ascii=False,indent=2)),'',
        f"Evidence SHA256: `{evidence_hash}`",'','[evidence.json](evidence.json)','','</details>','']
    return '\n'.join(lines)


def export_reports(record_path, output):
    record_path=Path(record_path).resolve();record=json.loads(record_path.read_text('utf8'));validate(record)
    sources=resolve_public_media_sources(record['publicMedia'],record_path.parent)
    output=Path(output).resolve()
    if output.exists():raise ValueError('Report output already exists; preserve the previous export')
    evidence={key:deepcopy(value) for key,value in record.items() if key not in {'narrative','publicMedia'}}
    evidence['publicMedia']=[dict(kind=m['kind'],path=m['path'],group=m['group']) for m in record['publicMedia']]
    evidence_hash=hashlib.sha256(json.dumps(evidence,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    reports={language:render(record,language,evidence_hash) for language in WORDS}
    output.mkdir(parents=True)
    copy_public_media(sources,output)
    save(output/'evidence.json',evidence)
    (output/'prompt.txt').write_bytes(record['prompt']['text'].encode('utf8'))
    for language,body in reports.items():(output/(language+'.md')).write_text(body,encoding='utf8')
    from arena.reporting.detail import render_detail, render_index, CSS, JS
    (output/'index.html').write_text(render_index(record),encoding='utf8')
    (output/'report.css').write_text(CSS,encoding='utf8')
    (output/'report.js').write_text(JS,encoding='utf8')
    for language in WORDS:
        (output/(language+'.html')).write_text(render_detail(record,language,evidence_hash,comparison(record),WORDS[language],OUTCOMES),encoding='utf8')
    for name,group in record['groups'].items():
        if group:
            (output/(name+'-reply.txt')).write_bytes(group['reply']['text'].encode('utf8'))
            for index,reply in enumerate(group['supplementaryReplies'],1):
                (output/f'{name}-supplement-{index}.txt').write_bytes(reply['text'].encode('utf8'))
    hashes={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
    manifest=dict(schemaVersion=1,sourceRecordSha256=hashlib.sha256(record_path.read_bytes()).hexdigest(),
        evidenceSha256=evidence_hash,languages=list(WORDS),trialExecutions=0,files=hashes,
        comparison=comparison(record),format='Bilingual report content and local comparison pages')
    save(output/'export-manifest.json',manifest)
    return dict(directory=str(output),languages=list(WORDS),evidenceSha256=evidence_hash,trialExecutions=0)
