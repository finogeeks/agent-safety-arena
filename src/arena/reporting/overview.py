"""Shared evaluation overview; conclusions come only from reviewed fields."""
import json
from pathlib import Path
import re

from arena.reporting.bilingual import comparison
from arena.reporting.scoring import score_catalog

LANGUAGES = ('zh-CN', 'en')
GROUPS = ('native', 'finshield')
PHASES = {'zh-CN': {'development': '开发评测', 'formal': '正式评测', 'language-study': '语言研究'},
          'en': {'development': 'Development', 'formal': 'Formal', 'language-study': 'Language study'}}
GRADES = {'adequate': ('A', '充分', 'Adequate'), 'partial': ('B', '部分充分', 'Partial'),
          'insufficient': ('C', '不足', 'Insufficient'), 'unassessed': ('U', '未评估', 'Unassessed')}


def bi(chinese, english):
    return {'zh-CN': chinese, 'en': english}


def bilingual_text(value):
    return (isinstance(value, dict) and set(value) == set(LANGUAGES)
            and all(isinstance(v, str) and v.strip() for v in value.values()))


def load_taxonomy(path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[3] / 'scenarios/catalog.json'
    data = json.loads(path.read_text('utf8'))
    if (not isinstance(data, dict) or set(data) != {'schemaVersion', 'categories', 'scenarios'}
            or data['schemaVersion'] != 1 or not isinstance(data['categories'], list)
            or not isinstance(data['scenarios'], dict)):
        raise ValueError('Invalid scenario catalog')
    ids = []
    for category in data['categories']:
        if (not isinstance(category, dict) or set(category) != {'id', 'label', 'description'}
                or category['id'] not in ('privacy', 'interaction', 'system', 'data')
                or not bilingual_text(category['label']) or not bilingual_text(category['description'])):
            raise ValueError('Invalid safety category')
        ids.append(category['id'])
    if ids != ['privacy', 'interaction', 'system', 'data']:
        raise ValueError('Declare the four safety categories in authored order')
    for identity, item in data['scenarios'].items():
        if (not re.fullmatch(r'[a-z0-9][a-z0-9-]*', identity) or not isinstance(item, dict)
                or not {'category', 'title'}.issubset(item)
                or set(item) - {'category', 'title', 'description', 'displayOrder'}
                or item['category'] not in ids or not bilingual_text(item['title'])
                or ('description' in item and not bilingual_text(item['description']))
                or ('displayOrder' in item and (type(item['displayOrder']) is not int
                                               or item['displayOrder'] < 0))):
            raise ValueError('Invalid scenario category or title')
    return data


def load_roster(path):
    if path is None:
        return None
    roster = json.loads(Path(path).read_text('utf8'))
    if (not isinstance(roster, dict) or not {'schemaVersion', 'model', 'agents'}.issubset(roster)
            or set(roster)-{'schemaVersion', 'model', 'agents', 'scenarioGoal'}
            or roster['schemaVersion'] != 1 or not isinstance(roster['model'], dict)
            or set(roster['model']) != {'id', 'label', 'reasoningEffort'}
            or not all(isinstance(v, str) and v.strip() for v in roster['model'].values())
            or not isinstance(roster['agents'], list) or not roster['agents']
            or ('scenarioGoal' in roster and (type(roster['scenarioGoal']) is not int or roster['scenarioGoal'] <= 0))):
        raise ValueError('Invalid evaluation coverage roster')
    identities, aliases = set(), set()
    for agent in roster['agents']:
        if (not isinstance(agent, dict) or set(agent) != {'id', 'label', 'recordAgentIds'}
                or not isinstance(agent['id'], str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', agent['id'])
                or not bilingual_text(agent['label'])
                or not isinstance(agent['recordAgentIds'], list) or not agent['recordAgentIds']
                or any(not isinstance(v, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*', v)
                       for v in agent['recordAgentIds'])):
            raise ValueError('Invalid evaluation Agent entry')
        if (agent['id'] in identities or len(set(agent['recordAgentIds'])) != len(agent['recordAgentIds'])
                or aliases.intersection(agent['recordAgentIds'])):
            raise ValueError('Coverage Agent identities and aliases must be unique')
        identities.add(agent['id']); aliases.update(agent['recordAgentIds'])
    return roster


def assessment(group):
    result = dict(state='not-run' if group is None else 'unassessed',
                  label=bi('未运行', 'Not run') if group is None else bi('未评估拦截', 'Not assessed'),
                  reason=bi('', ''), warningLevel=None, warningBasis=None)
    if group is None:
        return result
    action = group.get('interceptionAssessment')
    if action:
        result.update(state=action['status'], reason=action['reason'])
        if action['status'] == 'blocked':
            if action['basis'] == 'verified-postcondition':
                effect = action['postcondition']['effect']
                result['label'] = bi('已阻止' + effect['zh-CN'], 'Prevented: ' + effect['en'])
            else:
                result['label'] = bi('已拦截', 'Blocked')
        elif action['status'] == 'not-blocked':
            result['label'] = bi('未拦截', 'Not blocked')
        else:
            result['label'] = bi('待核实', 'Unverified')
    if (not action or action['status'] == 'not-blocked') and group.get('warningAssessment'):
        result['warningLevel'] = group['warningAssessment']['level']
        result['warningBasis'] = group['warningAssessment'].get('basis', 'dialog-wording')
    return result


def reused_single(record, records):
    present = [name for name in GROUPS if record['groups'][name]]
    if len(present) != 1:
        return False
    name = present[0]; group = record['groups'][name]
    for _, _, other in records:
        if (other is record or other['scenarioId'] != record['scenarioId']
                or other['agentId'] != record['agentId'] or other['evidenceOrigin'] != record['evidenceOrigin']
                or other['phase'] != record['phase'] or not all(other['groups'].values())):
            continue
        candidate = other['groups'][name]
        if (group['runId'] == candidate['runId'] and group['conditions'] == candidate['conditions']
                and group.get('prompt', record['prompt']) == candidate.get('prompt', other['prompt'])):
            return True
    return False


def make_catalog(records, roster=None, taxonomy=None):
    taxonomy = taxonomy or load_taxonomy()
    reports = []
    for _, relative, record in records:
        groups = record['groups']; presentation = record.get('presentation', {})
        pair = comparison(record)
        overview = presentation.get('overview')
        preview = next((media for media in record['publicMedia']
                        if overview and media['path'] == overview['media'] and media['group'] == 'comparison'), None)
        reports.append(dict(path=relative.parent.as_posix(), scenarioId=record['scenarioId'],
            agentId=record['agentId'], title={lang: record['narrative'][lang]['title'] for lang in LANGUAGES},
            categoryId=taxonomy['scenarios'].get(record['scenarioId'], {}).get('category', 'unclassified'),
            purpose={lang: record['narrative'][lang]['purpose'] for lang in LANGUAGES},
            origin=record['evidenceOrigin'], phase=record['phase'], date=presentation.get('testedOn'),
            archived=reused_single(record, records), paired=all(group is not None for group in groups.values()),
            conditionStatus=pair['status'], conditionsDiffer=bool(pair['differences']),
            versions={name: (group.get('environmentVersion') if name == 'finshield'
                      else group['conditions'].get('agentVersion')) if group else None for name, group in groups.items()},
            agentVersions={name: group['conditions'].get('agentVersion') if group else None
                           for name, group in groups.items()},
            models={name: {key: group['conditions'].get(key) for key in ('model', 'reasoningEffort')}
                    if group else None for name, group in groups.items()},
            assessments={name: assessment(group) for name, group in groups.items()},
            runIds={name: group['runId'] if group else None for name, group in groups.items()},
            hasReproduction=bool(presentation.get('reproduction')),
            preview=dict(path=relative.parent.as_posix() + '/' + preview['path'], caption=preview['caption']) if preview else None))
    reports.sort(key=lambda row: ((row['date'] or {}).get('date', ''), row['path']), reverse=True)
    live = [(p, r, data) for p, r, data in records if data['evidenceOrigin'] == 'live']
    aliases = {alias: agent['id'] for agent in (roster or {}).get('agents', []) for alias in agent['recordAgentIds']}
    identity = lambda agent: aliases.get(agent, agent)
    counts = dict(liveScenarios=len({data['scenarioId'] for _, _, data in live}),
        liveAgents=len({identity(data['agentId']) for _, _, data in live}),
        liveRuns=len({(identity(data['agentId']), group['runId']) for _, _, data in live
                      for group in data['groups'].values() if group}),
        pairedReports=sum(row['paired'] for row in reports if row['origin'] == 'live'),
        formalReports=sum(data['phase'] == 'formal' for _, _, data in live),
        developmentReports=sum(data['phase'] == 'development' for _, _, data in live),
        languageStudyReports=sum(data['phase'] == 'language-study' for _, _, data in live),
        syntheticReports=sum(row['origin'] == 'synthetic' for row in reports),
        archivedReports=sum(row['archived'] for row in reports if row['origin'] == 'live'))
    agents = [dict(agent) for agent in (roster or {}).get('agents', [])]
    if roster is None:
        for agent in sorted({data['agentId'] for _, _, data in live}):
            agents.append(dict(id=agent, label=bi(agent, agent), recordAgentIds=[agent]))
    coverage = []
    for agent in agents:
        row = dict(id=agent['id'], label=agent['label'],
                   recordAgentIds=agent['recordAgentIds'])
        for name in GROUPS:
            selected = []
            for _, relative, record in live:
                group = record['groups'][name]
                if record['agentId'] not in agent['recordAgentIds'] or not group:
                    continue
                condition = group['conditions']
                if roster and ((condition.get('model') or '').rsplit('/', 1)[-1] != roster['model']['id']
                               or condition.get('reasoningEffort') != roster['model']['reasoningEffort']):
                    continue
                selected.append((relative.parent.as_posix(), record))
            row[name] = dict(scenarios=len({record['scenarioId'] for _, record in selected}),
                formalScenarios=len({record['scenarioId'] for _, record in selected if record['phase'] == 'formal'}),
                reports=[path for path, _ in selected])
        coverage.append(row)
    cases = []
    for identity in sorted({row['scenarioId'] for row in reports}):
        rows = [row for row in reports if row['scenarioId'] == identity]
        paths = {row['path'] for row in rows}
        metadata = taxonomy['scenarios'].get(identity, {})
        cases.append(dict(id=identity, title=metadata.get('title', rows[0]['title']),
            description=metadata.get('description', rows[0]['purpose']),
            displayOrder=metadata.get('displayOrder'),
            categoryId=metadata.get('category', 'unclassified'), reportPaths=sorted(paths),
            live=any(row['origin'] == 'live' for row in rows),
            nativeAgents=sum(bool(paths.intersection(agent['native']['reports'])) for agent in coverage),
            finshieldAgents=sum(bool(paths.intersection(agent['finshield']['reports'])) for agent in coverage)))
    categories = []
    for category in taxonomy['categories']:
        selected = [case for case in cases if case['live'] and case['categoryId'] == category['id']]
        paths = {path for case in selected for path in case['reportPaths']}
        categories.append(dict(category, scenarios=len(selected),
            nativeAgents=sum(bool(paths.intersection(agent['native']['reports'])) for agent in coverage),
            finshieldAgents=sum(bool(paths.intersection(agent['finshield']['reports'])) for agent in coverage)))
    catalog = dict(schemaVersion=1, protocol=roster['model'] if roster else None,
                scenarioGoal=roster.get('scenarioGoal') if roster else None,
                counts=counts, coverage=coverage, reports=reports, cases=cases, categories=categories)
    catalog.update(score_catalog(catalog))
    return catalog
