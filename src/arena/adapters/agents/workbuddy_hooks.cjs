// Session transport only. The desktop owns session creation and native policy.
function createWorkBuddyHooks(bridge, sessionId) {
  if (typeof sessionId !== 'string' || !sessionId.trim()) {
    throw Error('An owned session ID is required');
  }
  if (typeof bridge?.invoke !== 'function' || typeof bridge?.subscribe !== 'function') {
    throw Error('The native invoke and event bridge are required');
  }
  let closed = false;
  let requestId = null;
  let status = 'ready';
  let result = null;
  let error = null;
  let visiblePrompt = null;
  const events = [];
  const copy = value => JSON.parse(JSON.stringify(value));
  const unsubscribe = bridge.subscribe((topic, event) => {
    if (closed || !event || typeof event !== 'object') return;
    if (topic === 'sandbox:interceptRequest') {
      if (event.sessionId !== sessionId) return;
    } else if (topic !== `session:event:${sessionId}`) return;
    if (event.sessionId != null && event.sessionId !== sessionId) return;
    events.push({ seq: events.length, sessionId, requestId, topic, event: copy(event) });
  });
  if (typeof unsubscribe !== 'function') throw Error('Native event subscription has no cleanup');

  return {
    trackVisible(prompt, id) {
      if (closed) throw Error('WorkBuddy hooks are closed');
      if (requestId !== null) throw Error('This hook has already submitted a request');
      if (typeof prompt !== 'string' || !prompt.trim()) throw Error('A prompt string is required');
      if (typeof id !== 'string' || !id.trim()) throw Error('A request ID is required');
      visiblePrompt = prompt;
      requestId = id;
      status = 'running';
      return { sessionId, requestId };
    },
    settleVisible(turn) {
      if (closed || visiblePrompt === null || turn?.userText !== visiblePrompt || typeof turn.id !== 'string') return;
      if (!['completed', 'cancelled', 'error'].includes(turn.state)) return;
      result = { nativeRequest: copy(turn) };
      status = 'finished';
    },
    input(prompt, id) {
      if (closed) throw Error('WorkBuddy hooks are closed');
      if (requestId !== null) throw Error('This hook has already submitted a request');
      if (typeof prompt !== 'string' || !prompt.trim()) throw Error('A prompt string is required');
      if (typeof id !== 'string' || !id.trim()) throw Error('A request ID is required');
      requestId = id;
      status = 'running';
      const failed = failure => {
        if (!closed) {
          status = 'error';
          error = failure instanceof Error ? failure.message : String(failure);
        }
      };
      try {
        Promise.resolve(bridge.invoke('session:sendMessage', undefined, sessionId,
          [{ type: 'text', text: prompt }], {
            messageId: id,
            'codebuddy.ai': { userMessageId: id, clientRequestId: id },
          })).then(response => {
            if (closed) return;
            if (typeof response?.stopReason !== 'string' || !response.stopReason.trim()) {
              throw Error('Native prompt result has no stopReason');
            }
            result = copy(response);
            status = 'finished';
          }).catch(failed);
      } catch (failure) {
        failed(failure);
      }
      return { sessionId, requestId };
    },
    output() {
      return copy({ sessionId, requestId, status, events, result, error });
    },
    close() {
      if (closed) return;
      closed = true;
      unsubscribe();
    },
  };
}

function nativeRuntimePath(version) {
  if (!['5.9.3', '5.9.4'].includes(version)) throw Error('Unsupported WorkBuddy native runtime version');
  return './assets/runtime-Cq08wGJM.js';
}

function pollOwnedRequests(state, conversation, hooks, visiblePrompt) {
  const cached = hooks.output();
  if (cached.requestId && cached.status !== 'finished' && !state.pending) {
    state.pending = true;
    Promise.resolve().then(() => conversation.requests(null)).then(page => {
      if (!page || !Array.isArray(page.items)) throw Error('Invalid owned request-list result');
      const publicText = parts => (parts || [])
        .filter(part => part.type === 'text' && typeof part.text === 'string')
        .map(part => part.text).join('');
      for (const request of page.items) {
        const userText = publicText(request.userMessage?.content);
        if (userText !== visiblePrompt) continue;
        hooks.settleVisible({id:request.id,state:request.state,userText,
          assistantText:publicText(request.assistantMessage?.content)});
      }
      state.error = null;
    }).catch(error => {
      state.error = error instanceof Error ? error.message : String(error);
    }).finally(() => {state.pending = false;});
  }
  return {...cached, requestObservation:{pending:!!state.pending,error:state.error || null}};
}

module.exports = { createWorkBuddyHooks, nativeRuntimePath, pollOwnedRequests };
