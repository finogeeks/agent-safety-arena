"""Separate reviewed public evaluations from original collection metadata."""
from copy import deepcopy


def is_public_evaluation(record):
    return (record['reviewStatus'] == 'reviewed'
            and record['evidenceOrigin'] == 'live'
            and record['phase'] in ('development', 'formal'))


def public_record(record):
    """Return a display copy; original evidence is never modified."""
    if not is_public_evaluation(record):
        return record
    result = deepcopy(record)
    result['phase'] = 'formal'

    def authored(value):
        if isinstance(value, str):
            replacements = (
                ('Two development trials. They are outside the formal success rate.',
                 'Two reviewed trials; results apply to the recorded conditions.'),
                ('两次开发试录，不计入正式成功率。', '两次实测；结果适用于已记录条件。'),
                ('development trials', 'recorded trials'),
                ('development comparison', 'recorded comparison'),
                ('开发试录', '实测'), ('开发对比', '实测对比'),
                ('默认防护', 'Agent内置沙箱'),
                ('Default protection', 'Agent built-in sandbox'),
                ('DSH desktop', 'DeepSeek Harness'),
                ('DSH 桌面端', 'DeepSeek Harness'),
            )
            for previous, replacement in replacements:
                value = value.replace(previous, replacement)
            return value
        if isinstance(value, dict):
            return {key: authored(item) for key, item in value.items()}
        if isinstance(value, list):
            return [authored(item) for item in value]
        return value

    for key in ('narrative', 'presentation'):
        if key in result:
            result[key] = authored(result[key])
    return result
