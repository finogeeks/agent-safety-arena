"""Native Claude terminal matching for the common collection controller."""
import json
import re
from pathlib import Path

CHOICE_LINE = re.compile(r'^(?P<pad>\s*)(?P<sel>[❯›>»])?\s*(?P<n>[1-9])\.\s+(?P<body>\S.*?)\s*$')


def numbered_choices(text):
    items = []
    for line in str(text or '').splitlines():
        match = CHOICE_LINE.match(line)
        if match:
            items.append(dict(n=int(match['n']), selected=bool(match['sel']),
                              label=('%s. %s' % (match['n'], match['body'])).strip()))
    return items


def numbered_picker(text):
    items = numbered_choices(text)
    if len(items) < 2 or items[0]['n'] != 1:
        return None
    return items


def picker_text(text):
    lines = str(text or '').splitlines()
    first = last = None
    for index, line in enumerate(lines):
        if CHOICE_LINE.match(line):
            if first is None:
                first = index
            last = index
    if first is None:
        return str(text or '').strip()
    start = max(0, first - 6)
    return '\n'.join(lines[start:last + 1]).strip()


def command_from_panel(text):
    marker = 'Do you want to proceed?'
    if marker not in text:
        return None, None
    before = text[:text.index(marker)]
    headers = (('PowerShell command', 'PowerShell'), ('Bash command', 'Bash'),
               ('Read file', 'Read'), ('Write file', 'Write'),
               ('Edit file', 'Edit'), ('Fetch', 'Fetch'))
    for header, tool in headers:
        at = before.rfind(header)
        if at >= 0:
            body = before[at + len(header):].strip()
            line = next((row.strip() for row in body.splitlines() if row.strip()), body)
            return tool, line
    lines = []
    for row in before.splitlines():
        stripped = row.strip()
        if not stripped or re.fullmatch(r'[╌─\-]+', stripped):
            continue
        lines.append(stripped)
    if lines and lines[-1] == 'This command requires approval' and len(lines) >= 2:
        tool = 'PowerShell' if any('powershell' in row.lower() for row in lines) else 'Bash'
        return tool, lines[-2]
    return 'unknown', lines[-1] if lines else marker


def approval_panel(text, pending):
    if len(pending) != 1:
        return None
    items = numbered_picker(text)
    if not items:
        return None
    key, request = next(iter(pending.items()))
    return dict(key=key, native=True, text=picker_text(text),
                choices=[item['label'] for item in items],
                oneTimeChoice=items[0]['label'], busy=False,
                toolName=request.get('toolName'), command=request.get('command'))


def powershell_shell_settings(existing=None):
    settings = dict(existing or {})
    env = dict(settings.get('env') or {})
    env['CLAUDE_CODE_USE_POWERSHELL_TOOL'] = '1'
    settings['env'] = env
    settings['defaultShell'] = 'powershell'
    permissions = dict(settings.get('permissions') or {})
    deny = [item for item in (permissions.get('deny') or []) if item != 'Bash']
    deny.append('Bash')
    permissions['deny'] = deny
    settings['permissions'] = permissions
    return settings


def apply_powershell_shell(home):
    path = Path(home) / 'settings.json'
    existing = {}
    if path.is_file():
        existing = json.loads(path.read_text(encoding='utf8'))
    settings = powershell_shell_settings(existing)
    path.write_text(json.dumps(settings, indent=2) + '\n', encoding='utf8')
    return settings


def apply_powershell_launch_env(env):
    result = dict(env or {})
    result['CLAUDE_CODE_USE_POWERSHELL_TOOL'] = '1'
    result.pop('CLAUDE_CODE_GIT_BASH_PATH', None)
    return result


def execution_tool_names(rows):
    names = []
    for row in rows or []:
        content = (row.get('message') or {}).get('content')
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get('type') == 'tool_use' and part.get('name'):
                names.append(part['name'])
    return names


def bash_startup_failure(text):
    blob = str(text or '')
    return ('NtCreateDirectoryObject' in blob or '0xC0000022' in blob
            or 'STATUS_ACCESS_DENIED' in blob)


def session_turn_complete(rows):
    reason = None
    for row in rows or []:
        if row.get('type') != 'assistant':
            continue
        value = (row.get('message') or {}).get('stop_reason')
        if value:
            reason = value
    return reason == 'end_turn'


class ClaudeEventStream:
    def __init__(self):
        self.events = []
        self.pending = {}
        self.conditions = {}
        self.request_id = None
        self.prompt = None
        self.admitted_prompt = None

    def emit(self, kind, **data):
        self.events.append(dict(seq=len(self.events), type=kind, data=data))
