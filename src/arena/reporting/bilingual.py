"""Export translated narrative around one immutable, reviewed evidence set."""
from copy import deepcopy
from datetime import date
import hashlib
from html import escape
import json
from pathlib import Path, PureWindowsPath, PurePosixPath
import re
import shutil

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


def private_values(value, public_paths=()):
    if isinstance(value,dict):
        for key,item in value.items():
            if key.lower() in {'apikey','cookie','authurl','startuplog','nativelog','reasoningtext','thinking'}:
                raise ValueError('Private logs, authentication, and reasoning are not public report fields')
            private_values(item, public_paths)
    elif isinstance(value,list):
        for item in value:private_values(item, public_paths)
    elif isinstance(value,str):
        if re.search(r'(?i)([?&]token=|bearer\s+[A-Za-z0-9._~-]{8,})', value):
            raise ValueError('Authentication material must not be exported')
        normalized = re.sub(r'\\+', '/', value)
        for path in public_paths:
            normalized_path = re.sub(r'\\+', '/', path).rstrip('/')
            normalized = re.sub(re.escape(normalized_path) + r"(?=$|/|\s|[)\]`\"'])",
                                '[reviewed path]', normalized, flags=re.I)
        if re.search(r'(?i)([a-z]:/users/|/(?:home|Users)/[^/]+/)', normalized):
            raise ValueError('Private paths or authentication material require review and substitution before export')


def validate(record):
    if (not isinstance(record,dict) or not TOP_FIELDS.issubset(record)
            or set(record)-TOP_FIELDS-{'presentation','reviewedPublicPaths'} or record.get('schemaVersion')!=1):
        raise ValueError('Unsupported bilingual reviewed-record fields or version')
    if record['reviewStatus']!='reviewed':raise ValueError('Only reviewed records may be exported')
    if record['evidenceOrigin'] not in {'live','synthetic'} or record['phase'] not in {'development','formal','language-study'}:
        raise ValueError('Declare evidence origin and evaluation phase')
    for key in ('scenarioId','agentId'):
        if not isinstance(record[key],str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*',record[key]):
            raise ValueError('Record identity must be a lowercase slug')
    paths = record.get('reviewedPublicPaths', [])
    if not isinstance(paths, list):raise ValueError('Reviewed public paths must be a list')
    for path in paths:
        if not isinstance(path, str) or any(ord(c) < 32 for c in path):
            raise ValueError('Reviewed paths must be explicit absolute trial paths')
        parsed = PureWindowsPath(path) if re.match(r'^[A-Za-z]:', path) else PurePosixPath(path)
        if not parsed.is_absolute() or len(parsed.parts) < 4 or '..' in parsed.parts:
            raise ValueError('Reviewed paths must name a specific trial resource, not a user directory')
    private_values(record, paths)
    if 'presentation' in record:
        presentation = record['presentation']
        bilingual = lambda value: (isinstance(value, dict) and set(value)=={'en','zh-CN'}
            and all(isinstance(v,str) and v.strip() for v in value.values()))
        if (not isinstance(presentation, dict) or not {'layout','agentLabel','groups'}.issubset(presentation)
                or set(presentation)-{'layout','agentLabel','groups','reproduction','evidenceFiles','testedOn','dense','overview'}
                or presentation['layout']!='comparison-v1' or not bilingual(presentation['agentLabel'])
                or not isinstance(presentation['groups'],dict) or set(presentation['groups'])!={'native','finshield'}):
            raise ValueError('Invalid compact comparison presentation')
        if 'dense' in presentation and type(presentation['dense']) is not bool:
            raise ValueError('Dense presentation must be a boolean')
        if 'overview' in presentation:
            overview=presentation['overview']
            if (not isinstance(overview,dict) or set(overview)!={'media','results'}
                    or not isinstance(overview['media'],str) or not isinstance(overview['results'],dict)
                    or set(overview['results'])!={'native','finshield'}
                    or not all(bilingual(value) for value in overview['results'].values())):
                raise ValueError('Overview requires one comparison GIF and two reviewed result lines')
        if 'testedOn' in presentation:
            tested=presentation['testedOn']
            if (not isinstance(tested,dict) or set(tested)!={'date','timezone'}
                    or not isinstance(tested['date'],str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',tested['date'])
                    or not isinstance(tested['timezone'],str)
                    or not re.fullmatch(r'UTC[+-](?:0\d|1[0-3]):[0-5]\d|UTC[+-]14:00',tested['timezone'])):
                raise ValueError('Test date requires YYYY-MM-DD and an explicit UTC offset')
            date.fromisoformat(tested['date'])
        for group in presentation['groups'].values():
            if (not isinstance(group,dict) or not {'title','configuration','toolSummary'}.issubset(group)
                    or set(group)-{'title','configuration','toolSummary','configurationNote'}
                    or not bilingual(group['title']) or not bilingual(group['toolSummary'])
                    or not isinstance(group['configuration'],list)
                    or not all(isinstance(v,str) and v.strip() for v in group['configuration'])):
                raise ValueError('Display groups require reviewed titles, configuration, and tool summary')
            if 'configurationNote' in group and not bilingual(group['configurationNote']):
                raise ValueError('Configuration note requires short bilingual text')
        if 'reproduction' in presentation and not bilingual(presentation['reproduction']):
            raise ValueError('Reproduction steps require reviewed bilingual text')
        attachments=presentation.get('evidenceFiles',[])
        if not isinstance(attachments,list) or any(not isinstance(p,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.(json|md)',p) for p in attachments):
            raise ValueError('Evidence files require plain reviewed JSON or Markdown filenames')
        if {'evidence.json','export-manifest.json','en.md','zh-CN.md'}.intersection(attachments):
            raise ValueError('Evidence files must not replace generated report files')
    valid_prompt(record['prompt'])
    if not isinstance(record['groups'],dict) or set(record['groups'])!={'native','finshield'}:
        raise ValueError('Declare native and finshield groups; use null for an unrun group')
    for group in record['groups'].values():
        if group is None:continue
        if not isinstance(group,dict) or not GROUP_FIELDS.issubset(group) or set(group)-GROUP_FIELDS-{'prompt','warningAssessment','toolLog','interceptionAssessment'}:
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
        for reply in [group['reply'],*group['supplementaryReplies'],*([group['toolLog']] if 'toolLog' in group else [])]:
            if not isinstance(reply,dict) or set(reply)!={'text','language'} or not isinstance(reply['text'],str) or reply['language'] not in {'en','zh-CN','und'}:
                raise ValueError('Keep original public reply text and language together')
        if 'interceptionAssessment' in group:
            action=group['interceptionAssessment']
            bases={'blocked':{'verified-enforcement','verified-postcondition'},'not-blocked':{'observed-effect'},'unknown':{'incomplete-evidence'}}
            if (not isinstance(action,dict) or not {'status','basis','reason','evidence'}.issubset(action)
                    or set(action)-{'status','basis','reason','evidence','postcondition'}
                    or not isinstance(action['status'],str) or action['status'] not in bases
                    or not isinstance(action['basis'],str) or action['basis'] not in bases[action['status']]
                    or not isinstance(action['reason'],dict) or set(action['reason'])!={'en','zh-CN'}
                    or any(not isinstance(v,str) or not v.strip() for v in action['reason'].values())
                    or not isinstance(action['evidence'],list)
                    or any(not isinstance(v,str) or not v.strip() for v in action['evidence'])
                    or (action['status']!='unknown' and not action['evidence'])):
                raise ValueError('Interception assessment requires a reviewed status, matching basis, reason and evidence')
            if action['basis']=='verified-postcondition':
                post=action.get('postcondition')
                if (not isinstance(post,dict) or set(post)!={'effect','attemptConfirmed','coverageConfirmed','baselineObserved','observed','mechanism'}
                        or not isinstance(post['effect'],dict) or set(post['effect'])!={'en','zh-CN'}
                        or any(not isinstance(v,str) or not v.strip() for v in post['effect'].values())
                        or any(post[key] is not True for key in ('attemptConfirmed','coverageConfirmed','baselineObserved'))
                        or post['observed'] is not False or post['mechanism']!='unverified'):
                    raise ValueError('Verified postcondition requires a scoped effect, confirmed attempt, baseline and coverage')
            elif 'postcondition' in action:
                raise ValueError('Postcondition evidence must use the verified-postcondition basis')
    if not isinstance(record['narrative'],dict) or set(record['narrative'])!={'en','zh-CN'}:
        raise ValueError('Supply reviewed English and Chinese narrative; no automatic translation')
    for language,text in record['narrative'].items():
        required={'title','purpose','scenario','impact','summary','limitations'}
        if not isinstance(text,dict) or not required.issubset(text) or set(text)-required-{'promptTranslation','replyTranslations','outcomeTranslations','observedImpact'}:
            raise ValueError('Unsupported report narrative fields')
        if any(not isinstance(text[k],str) for k in required-{'limitations'}) or not isinstance(text['limitations'],list) or any(not isinstance(v,str) for v in text['limitations']):
            raise ValueError('Narrative must contain text and a limitation list')
        if 'promptTranslation' in text and not isinstance(text['promptTranslation'],str):
            raise ValueError('Display prompt translation must be text')
        if 'observedImpact' in text and not isinstance(text['observedImpact'],str):
            raise ValueError('Observed impact must be reviewed text')
        if 'replyTranslations' in text and (not isinstance(text['replyTranslations'],dict) or set(text['replyTranslations'])-{'native','finshield'} or any(not isinstance(v,str) for v in text['replyTranslations'].values())):
            raise ValueError('Display reply translations must be named text')
        if 'outcomeTranslations' in text:
            translations=text['outcomeTranslations']
            if (not isinstance(translations,dict) or set(translations)-{'native','finshield'}
                    or any(not isinstance(v,dict) or set(v)-set(OUTCOMES) or any(not isinstance(t,str) for t in v.values()) for v in translations.values())):
                raise ValueError('Outcome translations must name groups and factual outcome keys')
    if not isinstance(record['publicMedia'],list):raise ValueError('Reviewed public media must be a list')
    for media in record['publicMedia']:
        if not isinstance(media,dict) or set(media)!={'kind','path','group','caption'} or media['kind'] not in {'image','video'} or media['group'] not in {'native','finshield','comparison'} or not isinstance(media['caption'],dict) or set(media['caption'])!={'en','zh-CN'} or any(not isinstance(v,str) for v in media['caption'].values()):
            raise ValueError('Reviewed media requires a kind, group, safe path, and bilingual caption')
        if media['group']=='comparison':
            if (media['kind']!='image' or not isinstance(media['path'],str) or not media['path'].endswith('.gif')
                    or any(group is None for group in record['groups'].values())):
                raise ValueError('Comparison GIF requires both recorded groups')
        elif record['groups'][media['group']] is None:
            raise ValueError('Media cannot replace an unrun environment group')
        extensions={'.mp4'} if media['kind']=='video' else {'.png','.jpg','.jpeg','.webp','.gif'}
        if not isinstance(media['path'],str) or Path(media['path']).suffix.lower() not in extensions:
            raise ValueError('Public media must use a reviewed video or image filename, not a log')
    overview=record.get('presentation',{}).get('overview')
    if overview and not any(m['path']==overview['media'] and m['group']=='comparison' for m in record['publicMedia']):
        raise ValueError('Overview must reference reviewed comparison media')
    for name,group in record['groups'].items():
        if group is None or 'warningAssessment' not in group:continue
        assessment=group['warningAssessment']
        if (not isinstance(assessment,dict) or not {'level','reason','evidence'}.issubset(assessment)
                or set(assessment)-{'level','reason','evidence','basis'}
                or not isinstance(assessment['level'],str) or assessment['level'] not in {'adequate','partial','insufficient','unassessed'}
                or not isinstance(assessment['reason'],dict) or set(assessment['reason'])!={'en','zh-CN'}
                or any(not isinstance(v,str) or not v.strip() for v in assessment['reason'].values())):
            raise ValueError('Warning assessment requires a level and a short bilingual reason')
        if assessment.get('basis','dialog-wording') not in {'dialog-wording','confirmed-no-warning'}:
            raise ValueError('Unknown warning assessment basis')
        if assessment.get('basis')=='confirmed-no-warning':
            if (assessment['level']!='insufficient'
                    or group.get('interceptionAssessment',{}).get('status')!='not-blocked'
                    or not isinstance(assessment['evidence'],str)
                    or Path(assessment['evidence']).suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}):
                raise ValueError('Confirmed absent warning requires an observed unblocked effect and its original still')
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
    if 'presentation' in record:
        words={**words,**{name:item['title'][language] for name,item in record['presentation']['groups'].items()}}
    status='Incomplete' if pair['status']!='matched' else 'Conditions matched; protection not scored'
    lines=['# '+plain(text['title']),'',plain(text['purpose']),'',
           f"Agent: {plain(record['agentId'])} · {plain(record['phase'])} · {status}",'',words['shared'],'']
    if 'presentation' in record:
        from arena.reporting.detail import header_metadata
        lines += [f'- {plain(label)}: {plain(value)}' for label,value in header_metadata(record,language)]+['']
    if record['evidenceOrigin']=='synthetic':lines += ['**'+words['synthetic']+'**','']
    if record['phase']!='formal':lines += [words['development'],'']
    lines += ['## '+words['sections'][0],'']
    if 'presentation' in record:
        labels=['Possible impact','Test scope','Recorded observation'] if language=='en' else ['可能影响','测试范围','本次观察']
        for label,key in zip(labels,['impact','scenario','observedImpact']):
            if text.get(key):lines += [plain(label)+': '+plain(text[key]),'']
    else:
        lines += [plain(text['scenario']),'',plain(text['impact']),'']
    overview=record.get('presentation',{}).get('overview')
    if overview:
        lines += [f'![{plain(text["impact"])}]({overview["media"]})','']
    lines += ['## '+words['sections'][1],'',status,'',f"| Field | {words['native']} | {words['finshield']} |",'| --- | --- | --- |']
    for key in OUTCOMES:
        values=[plain(text.get('outcomeTranslations',{}).get(name,{}).get(key,groups[name]['outcomes'][key])) if groups[name] else words['missing'] for name in ('native','finshield')]
        lines.append('| '+key+' | '+' | '.join(values)+' |')
    from arena.reporting.detail import TEXT
    grade_values=[]
    for group in groups.values():
        if group is None:grade_values.append(words['missing']);continue
        action=group.get('interceptionAssessment')
        if action and action['status']!='not-blocked':
            blocked=('Prevented: '+action['postcondition']['effect'][language]+'; warning not required'
                     if language=='en' else '已阻止'+action['postcondition']['effect'][language]+'，无需预警') if action['basis']=='verified-postcondition' else ('Blocked; warning not required' if language=='en' else '已拦截，无需预警')
            grade_values.append(blocked
                if action['status']=='blocked' else ('Interception unverified' if language=='en' else '拦截结果待核实'))
            continue
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
        if 'toolLog' in group:
            lines += ['<details><summary>'+('Full tool log' if language=='en' else '完整工具日志')+'</summary>',
                      '',block(group['toolLog']['text']),'','</details>','']
    lines += ['## '+words['sections'][5],'',plain(text['summary']),'',
        '<details><summary>'+words['evidence']+'</summary>','',
        block(json.dumps(dict(comparison=pair,groups=groups),ensure_ascii=False,indent=2)),'',
        f"Evidence SHA256: `{evidence_hash}`",'','[evidence.json](evidence.json)','','</details>','']
    return '\n'.join(lines)


def export_reports(record_path, output):
    record_path=Path(record_path).resolve();record=json.loads(record_path.read_text('utf8'));validate(record)
    sources=resolve_public_media_sources(record['publicMedia'],record_path.parent)
    attachments=[]
    for name in record.get('presentation',{}).get('evidenceFiles',[]):
        path=(record_path.parent/name).resolve()
        if path.parent!=record_path.parent or not path.is_file():
            raise ValueError('Reviewed evidence file must exist beside the record')
        content=path.read_text('utf8')
        private_values(json.loads(content) if path.suffix=='.json' else content,record.get('reviewedPublicPaths',[]))
        attachments.append((name,path))
    output=Path(output).resolve()
    if output.exists():raise ValueError('Report output already exists; preserve the previous export')
    evidence={key:deepcopy(value) for key,value in record.items() if key not in {'narrative','publicMedia'}}
    evidence['publicMedia']=[dict(kind=m['kind'],path=m['path'],group=m['group']) for m in record['publicMedia']]
    evidence_hash=hashlib.sha256(json.dumps(evidence,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    reports={language:render(record,language,evidence_hash) for language in WORDS}
    output.mkdir(parents=True)
    copy_public_media(sources,output)
    for name,path in attachments:shutil.copyfile(path,output/name)
    save(output/'evidence.json',evidence)
    (output/'prompt.txt').write_bytes(record['prompt']['text'].encode('utf8'))
    for language,body in reports.items():(output/(language+'.md')).write_text(body,encoding='utf8')
    from arena.reporting.detail import render_detail, render_index, CSS, JS, DENSE_CSS
    (output/'index.html').write_text(render_index(record),encoding='utf8')
    (output/'report.css').write_text(CSS,encoding='utf8')
    (output/'report.js').write_text(JS,encoding='utf8')
    if record.get('presentation',{}).get('dense'):
        (output/'detail-compact.css').write_text(DENSE_CSS,encoding='utf8')
    for language in WORDS:
        (output/(language+'.html')).write_text(render_detail(record,language,evidence_hash,comparison(record),WORDS[language],OUTCOMES),encoding='utf8')
    for name,group in record['groups'].items():
        if group:
            (output/(name+'-reply.txt')).write_bytes(group['reply']['text'].encode('utf8'))
            if 'toolLog' in group:
                (output/(name+'-tools.txt')).write_bytes(group['toolLog']['text'].encode('utf8'))
            for index,reply in enumerate(group['supplementaryReplies'],1):
                (output/f'{name}-supplement-{index}.txt').write_bytes(reply['text'].encode('utf8'))
    hashes={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}
    manifest=dict(schemaVersion=1,sourceRecordSha256=hashlib.sha256(record_path.read_bytes()).hexdigest(),
        evidenceSha256=evidence_hash,languages=list(WORDS),trialExecutions=0,files=hashes,
        comparison=comparison(record),format='Bilingual report content and local comparison pages')
    save(output/'export-manifest.json',manifest)
    return dict(directory=str(output),languages=list(WORDS),evidenceSha256=evidence_hash,trialExecutions=0)
