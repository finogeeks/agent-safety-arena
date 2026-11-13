"""Native Codex terminal transport for the common collection controller."""
import json
import re

def admission_text(text):
    """Compare composer transport changes without changing admitted evidence."""
    return text.replace('\r\n','\n').replace('\r','\n').rstrip()

def model_arguments(profile):
    required={'model','model_provider','model_providers'}
    if not required.issubset(profile) or set(profile)-required-{'tui','projects'}:
        raise ValueError('The Codex profile must contain only model connection settings')
    tui=profile.get('tui',{})
    if set(tui)-{'screen_reader_detection_done','model_availability_nux'}:
        raise ValueError('Unexpected native terminal preferences in the model profile')
    nux=tui.get('model_availability_nux',{})
    if (not isinstance(nux,dict) or any(not isinstance(k,str) or not k
            or type(v) is not int or v<0 for k,v in nux.items())):
        raise ValueError('Unexpected model availability UI preferences')
    if any(set(value)!={'trust_level'} or value['trust_level'] not in {'trusted','untrusted'}
           for value in profile.get('projects',{}).values()):
        raise ValueError('Unexpected project policy overrides in the model profile')
    provider=profile['model_provider']
    if set(profile['model_providers']) != {provider} or not re.fullmatch(r'[a-zA-Z0-9_-]+',provider):
        raise ValueError('The Codex profile must select one provider')
    settings=profile['model_providers'][provider]
    if set(settings) != {'name','base_url','wire_api','env_key','requires_openai_auth'}:
        raise ValueError('Provider fields are outside the model-only contract')
    if settings['base_url'] != 'https://api.deepseek.com' or settings['env_key'] != 'DEEPSEEK_API_KEY' or settings['wire_api'] != 'responses' or settings['requires_openai_auth'] is not False:
        raise ValueError('DeepSeek must use the official endpoint and environment credential reference')
    entries={'model':profile['model'],'model_provider':provider,
             **{f'model_providers.{provider}.{k}':v for k,v in settings.items()}}
    return [f'{key}={json.dumps(value)}' for key,value in entries.items()]

def approval_panel(text, pending):
    if len(pending)!=1:
        return None
    key,request=next(iter(pending.items()))
    if request.get('method') not in {'item/commandExecution/requestApproval','item/fileChange/requestApproval'}:
        return None
    marker='Would you like to run the following command?'
    panel=(text[text.index(marker):] if marker in text else text).strip()
    choices=[re.sub(r'^[\s›>]+','',line).strip() for line in panel.splitlines()
             if re.match(r'^[\s›>]*[1-9]\.\s',line)]
    once=[label for label in choices if re.fullmatch(r'1\. Yes, proceed \(y\)',label)]
    compact=lambda value:re.sub(r'\s+','',value).replace('\\\\','\\')
    command=request.get('command')
    full_match=isinstance(command,str) and compact(command) in compact(panel)
    reason=request.get('reason')
    reason_match=isinstance(reason,str) and bool(reason.strip()) and compact('Reason:'+reason) in compact(panel)
    if len(once)!=1:
        return None
    return dict(key=key,native=True,text=panel,choices=choices,oneTimeChoice=once[0],busy=False,
                commandTruncated=not full_match, reasonVisible=reason_match,
                association='unique-pending-native-request')

class CodexEventStream:
    def __init__(self):
        self.events = []
        self.pending = {}
        self.conditions = {}
        self.request_id = None
        self.prompt = None
        self.admitted_prompt = None
        self.calls = {}
        self.turn_input = None
        self.thread_id = None

    def emit(self, kind, **data):
        self.events.append(dict(seq=len(self.events),type=kind,data=data))

    def feed(self, direction, message):
        method=message.get('method');params=message.get('params',{})
        key=str(message.get('id'))
        if direction=='client' and method:
            self.calls[key]=method
            if method=='turn/start' and (not self.thread_id or params.get('threadId')==self.thread_id):
                self.turn_input='\n'.join(item.get('text','') for item in params.get('input',[]) if item.get('type')=='text')
            return
        if direction=='server' and not method and self.calls.get(key) in {'thread/start','thread/resume'}:
            result=message.get('result',{})
            if self.thread_id and result.get('thread',{}).get('id')!=self.thread_id:return
            if result.get('thread',{}).get('id'):
                self.thread_id=result['thread']['id']
                sandbox=result.get('sandbox',{}).get('type')
                mode={'workspaceWrite':'workspace-write','readOnly':'read-only','dangerFullAccess':'danger-full-access'}.get(sandbox,sandbox)
                self.conditions.update(model=result.get('model'),provider=result.get('modelProvider'),
                    sandboxMode=mode,approvalPolicy=result.get('approvalPolicy'),reasoningEffort=result.get('reasoningEffort'))
                self.emit('sandbox/mode',mode=mode)
                self.emit('approval/policy',policy=result.get('approvalPolicy'))
                self.emit('request/header',header={'config':{k:self.conditions[k] for k in ('model','provider','reasoningEffort')}})
            return
        if direction=='client' and key in self.pending and 'result' in message:
            decision=message['result'].get('decision')
            self.pending.pop(key)
            self.emit('approval/decided',id=key,outcome='allowed' if decision=='accept' else decision,nativeDecision=decision)
            return
        if direction!='server':
            return
        if self.thread_id and params.get('threadId') and params['threadId']!=self.thread_id:return
        if method=='turn/started':
            turn=params['turn']['id'];self.emit('turn/start',turn=turn)
            if self.prompt is not None and self.turn_input is not None and admission_text(self.turn_input)==admission_text(self.prompt):
                self.admitted_prompt=self.turn_input
                self.emit('user/message',content=[{'type':'text','text':self.turn_input}],source={'rpcId':self.request_id})
        elif method in {'item/started','item/completed'}:
            item=params.get('item',{});kind=item.get('type')
            if kind=='commandExecution' and method=='item/started':
                self.emit('tool/call',callId=item['id'],toolName='exec_command',arguments=json.dumps({'command':item.get('command')}))
            elif kind=='commandExecution':
                self.emit('tool/result',callId=item['id'],native=item)
            elif kind=='agentMessage' and method=='item/completed':
                self.emit('assistant/message',turn=params.get('turnId'),message={'content':[{'type':'text','text':item.get('text','')}]})
        elif method in {'item/commandExecution/requestApproval','item/fileChange/requestApproval'}:
            item={**params,'method':method};self.pending[key]=item
            self.emit('approval/asked',id=key,callId=params.get('itemId'),toolName='exec_command' if 'commandExecution' in method else 'apply_patch',
                command=params.get('command'),reason=params.get('reason'),source='Codex CLI native approval',native=item)
        elif method=='turn/completed':
            turn=params['turn'];status=turn.get('status')
            self.emit('turn/end',turn=turn['id'],reason={'kind':status if status in {'completed','interrupted'} else 'error','error':turn.get('error')})
