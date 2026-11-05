"""Record one private DSH prompt trial."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time
import uuid

from arena.adapters.agents.dsh import completion_for, scrub


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    # Windows readers can briefly hold the previous evidence file open.
    # Retain atomic replacement and report a persistent denial to the caller.
    for attempt in range(6):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(.05)


def local_scope_guard(path, item):
    try:
        grants = json.loads(path.read_text('utf8'))['grants']
    except (OSError, ValueError, KeyError, TypeError):
        return None
    command = item.get('command')
    if not isinstance(command, str):
        return None
    expected = dict(requestId=item['requestId'], tool=item['tool'],
        commandSha256=hashlib.sha256(command.encode('utf8')).hexdigest())
    return True if isinstance(grants,list) and expected in grants else None


class Confirmations:
    def __init__(self, directory, browser, clock, started, delay_seconds=5, environment_check=None):
        self.directory, self.browser, self.clock, self.started = directory, browser, clock, started
        self.delay_seconds, self.environment_check = delay_seconds, environment_check
        self.items = []
        self.requests = {}
        self.keys = {}

    def create(self, **fields):
        item = {"id": f"confirmation-{len(self.items) + 1:03d}", "text": "", "choices": [],
                "captureStatus": "missing", "choice": None, "source": "unknown", **fields}
        self.items.append(item)
        return item

    def native(self, events):
        calls = {row['data']['callId']: row['data'] for row in events if row['type'] == 'tool/call'}
        for row in events:
            data = row.get("data", {})
            if row["type"] == "approval/asked" and data["id"] not in self.requests:
                early = next((item for item in self.items if item.get("uiNative") and not item.get("requestId")), None)
                item = early if early is not None else self.create()
                item.update(requestId=data["id"], tool=data.get("toolName"), source=data.get('source',"DSH native approval"),
                            nativeReason=data.get("reason"), askedSeq=row["seq"])
                call = calls.get(data.get('callId'), {})
                try:
                    arguments = json.loads(call.get('arguments', '{}'))
                except (TypeError, ValueError):
                    arguments = {}
                if not isinstance(arguments, dict):
                    arguments = {}
                item.update(callId=data.get('callId'), command=data.get('command') or arguments.get('command'))
                self.requests[data["id"]] = item
            elif row["type"] == "approval/decided" and data["id"] in self.requests:
                item = self.requests[data["id"]]
                item["choice"] = data.get("outcome")
                item["decidedSeq"] = row["seq"]

    def capture(self, snapshot):
        for dialog in snapshot.get("dialogs", []):
            key = dialog["key"]
            if key in self.keys:
                continue
            pending = [item for item in self.items if not item.get("uiKey") and not item["choice"]]
            item = pending[0] if dialog.get("native") and pending else self.create()
            self.keys[key] = item
            item.update(uiKey=key, uiNative=bool(dialog.get("native")), text=dialog["text"], choices=dialog.get("choices", []),
                        videoOffsetSeconds=round(max(0, self.clock() - self.started), 3))
            item['autoDecisionNotBeforeSeconds'] = item['videoOffsetSeconds'] + self.delay_seconds
            if dialog.get('oneTimeChoice') in dialog.get('choices',[]):
                item['oneTimeChoice']=dialog['oneTimeChoice']
            relative = f"confirmations/{item['id']}.png"
            path = self.directory / relative
            try:
                captured = self.browser.screenshot(path, key=key)
                if captured is not False:
                    item.update(screenshot=relative, captureStatus="captured")
                    if isinstance(captured, dict):
                        item["capturedAtMs"] = captured.get("at")
                    print(f"Captured {item['id']} before any choice.", flush=True)
            except (OSError, RuntimeError) as error:
                item["captureError"] = scrub(error)
        for choice in snapshot.get("choices", []):
            item = self.keys.get(choice["key"])
            if item:
                item["uiChoice"] = choice.get("label")
                item["choiceAtMs"] = choice.get("at")
                if not item.get("choice"):
                    item["choice"] = choice.get("label")
                if item.get("capturedAtMs") and choice.get("at", 0) <= item["capturedAtMs"]:
                    item["captureStatus"] = "late"

    def persist(self):
        save(self.directory / "confirmations.json", self.items)

    def auto_decide(self, recorder, sleep, guard=None):
        for item in self.items:
            if (item.get("choice") or item.get("autoDecisionAttempted") or not item.get("uiNative")
                    or not item.get("requestId") or item.get("captureStatus") != "captured"
                    or not (self.directory / item.get("screenshot", "")).is_file()
                    or not ({"允许一次", "Allow once"}.intersection(item.get("choices", []))
                            or item.get('oneTimeChoice') in item.get('choices',[]))):
                continue
            if 'recordedPanelAt' not in item:
                self.persist()
                item['recordedPanelAt'] = recorder.checkpoint()
                self.persist()
            scope = guard(item) if guard else False
            if scope is None:
                item['scopeStatus'] = 'pending-review'
                self.persist()
                continue
            if not scope:
                item['scopeStatus'] = 'unmatched-command'
                self.persist()
                raise RuntimeError('Native confirmation is outside the declared command allowlist; no choice made')
            item['scopeStatus'] = 'matched-command'
            if self.clock() - self.started < item['autoDecisionNotBeforeSeconds']:
                self.persist()
                continue
            if self.environment_check:
                self.environment_check()
            recorder.check()
            item["autoDecisionAttempted"] = True
            self.persist()
            decision = self.browser.choose_once(item["uiKey"], item["text"])
            item.update(decisionActor="automation", uiChoice=decision["label"], choiceAtMs=decision["at"])
            self.persist()
            print(f"Selected one-time approval after capture: {item['id']}", flush=True)


def run_trial(config, *, agent, browser, recorder, clock=None, sleep=None):
    clock = clock or time.monotonic
    sleep = sleep or time.sleep
    confirmation_mode = config.get("confirmation_mode", "capture-then-allow-once")
    if confirmation_mode not in {"capture-then-allow-once", "manual"}:
        raise ValueError("Unknown confirmation mode")
    prompt_bytes = Path(config["prompt"]).read_bytes()
    prompt = prompt_bytes.decode("utf8")
    if not prompt.strip():
        raise ValueError("The prompt must contain text")
    if config["timeout"] <= 0:
        raise ValueError("timeout must be positive")
    for key in ("target", "revision", "reason"):
        if not str(config.get(key, "")).strip():
            raise ValueError(f"{key} must be declared")
    output_root = Path(config["output_root"]).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = config.get('agent_id','dsh')+"-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    directory = output_root / run_id
    directory.mkdir()
    workspace_root = Path(config.get("workspace_root") or tempfile.gettempdir()).resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="arena-dsh-workspace-" + run_id[-8:] + "-", dir=workspace_root))
    (directory / "confirmations").mkdir()
    (directory / "prompt.txt").write_bytes(prompt_bytes)
    if config.get("input_file"):
        source = Path(config["input_file"])
        if source.name.lower() in {"agents.md", "claude.md"}:
            raise ValueError("Input fixture must be data, not an Agent instruction file")
        (directory / "input").mkdir()
        shutil.copyfile(source, directory / "input" / source.name)
        shutil.copyfile(source, workspace / source.name)
    state = {"schemaVersion": 1, "runId": run_id, "directory": str(directory), "status": "preparing",
             "createdAtUtc": datetime.now(timezone.utc).isoformat(), "revision": config["revision"],
             "reason": config["reason"], "target": config["target"], "errors": [], "evidenceGaps": [],
             "actualPromptSha256": hashlib.sha256(prompt_bytes).hexdigest(), "requestId": str(uuid.uuid4()),
             "workspacePath": str(workspace),
             "recordingRegion": config.get("region"), "addedProtection": False}
    state.update(promptSubmitted=False,promptLanguage=config.get('prompt_language','und'),
                 promptStatus=config.get('prompt_status','legacy-unspecified'),
                 languageTrack=config.get('language_track','legacy-unspecified'))
    state["confirmationMode"] = confirmation_mode
    if config.get('case_id'):
        state['caseId'] = config['case_id']
    save(directory / "run.json", state)
    print(f"Private Agent trial: {directory}", flush=True)
    started = clock()
    state['approvalDelaySeconds'] = config.get('approval_delay_seconds', 5)
    confirmations = Confirmations(directory, browser, clock, started,
        delay_seconds=state['approvalDelaySeconds'], environment_check=config.get('environment_check'))
    events = []
    submitted = False
    recorder_attempted = False
    try:
        state.update(agent.prepare(workspace, browser, directory))
        expected = config.get('declared_conditions')
        if expected and not config.get('preflight_only'):
            actual = dict(agentVersion=state.get('agentVersion'),uiLanguage=state.get('uiLanguage'),
                          builtinSandbox=state.get('sandboxMode'),approvalPolicy=state.get('approvalPolicy'))
            for key,value in actual.items():
                if value != expected.get(key):
                    raise RuntimeError(f'Prepared {key} differs from the planned condition; no prompt submitted')
        if config.get('approval_review') == 'local-file':
            authorization = directory/'approval-scope.json'
            save(authorization, {'grants': []})
            config['approval_guard'] = lambda item: local_scope_guard(authorization, item)
        if getattr(browser, 'desktop', None):
            state.update(browser.verify_presentation() if hasattr(browser,'verify_presentation') else browser.desktop.verify(browser.chrome_process.pid))
        if not config.get("region"):
            if not state.get("captureWindowTitle"):
                raise RuntimeError("The owned DSH recording window was not identified; no prompt submitted")
            recorder.select_window(state["captureWindowTitle"])
            state["recordingSurface"] = "owned-dsh-viewport"
        else:
            state["recordingSurface"] = "declared-screen-region"
        save(directory / "run.json", state)
        recorder_attempted = True
        recorder.start(directory / "recording.mp4")
        started = clock()
        confirmations.started = getattr(recorder, "started_at", started)
        state["status"] = "running"
        save(directory / "run.json", state)
        if hasattr(agent,'finish_startup'):
            state.update(agent.finish_startup(browser,recorder,directory))
            save(directory/'run.json',state)
        if config.get('preflight_only'):
            browser.screenshot(directory/'presentation.png')
            sleep(2)
            recorder.check()
            state['status'] = 'preflight-completed'
            return state
        # Mark attempted admission before the call: a transport error can follow acceptance.
        submitted = True
        state['promptSubmitted'] = True
        save(directory/'run.json',state)
        agent.submit(prompt, state["requestId"])
        while True:
            if config.get('environment_check'):
                config['environment_check']()
            recorder.check()
            events = agent.observe()
            save(directory / "native-events.json", events)
            for row in events:
                data = row.get("data", {})
                if row["type"] == "request/header":
                    selected = data.get("header", {}).get("config", {})
                    state["model"] = {key: selected[key] for key in ("provider", "model", "reasoningEffort", "maxTokens") if key in selected}
                elif row["type"] == "sandbox/mode":
                    state["sandboxMode"] = data.get("mode")
                elif row["type"] == "approval/policy":
                    state["approvalPolicy"] = data.get("policy")
            confirmations.native(events)
            confirmations.capture(browser.snapshot())
            confirmations.persist()
            completion = completion_for(events, state["requestId"])
            if completion:
                state["completionState"] = completion["state"]
                state["status"] = completion["state"]
                if completion.get("error"):
                    state["errors"].append(scrub(json.dumps(completion["error"], ensure_ascii=False)))
                (directory / "agent-output.txt").write_text(completion["text"], encoding="utf8")
                browser.screenshot(directory / "final-screen.png")
                confirmations.capture(browser.snapshot())
                hold_end = clock() + config.get('final_hold_seconds', 0)
                while clock() < hold_end:
                    if config.get('environment_check'):
                        config['environment_check']()
                    recorder.check()
                    events = agent.observe()
                    save(directory / 'native-events.json', events)
                    confirmations.native(events)
                    confirmations.capture(browser.snapshot())
                    confirmations.persist()
                    if confirmation_mode == 'capture-then-allow-once':
                        confirmations.auto_decide(recorder, sleep, config.get('approval_guard'))
                    sleep(max(0, min(.25, hold_end-clock())))
                browser.screenshot(directory / 'final-screen.png')
                break
            if (directory / "stop").exists():
                state["status"] = "cancelled"
                break
            if clock() - started >= config["timeout"]:
                state["status"] = "timeout"
                break
            if confirmation_mode == "capture-then-allow-once":
                confirmations.auto_decide(recorder, sleep, config.get('approval_guard'))
            sleep(.25)
    except KeyboardInterrupt:
        state["status"] = "cancelled"
    except Exception as error:
        state["status"] = "error"
        state["errors"].append(scrub(error))
    finally:
        if submitted and state["status"] != "completed":
            try:
                agent.cancel()
                events = agent.observe()
                save(directory / "native-events.json", events)
                confirmations.native(events)
                confirmations.capture(browser.snapshot())
            except Exception as error:
                state["errors"].append("Cancellation/final observation: " + scrub(error))
        # Stop the owned Agent before ending an abnormal recording.
        try:
            agent.close()
        except Exception as error:
            state["errors"].append("Agent shutdown: " + scrub(error))
            state["status"] = "error"
        if recorder_attempted:
            try:
                recorder.stop()
            except Exception as error:
                state["errors"].append("Recorder finalization: " + scrub(error))
                state["status"] = "error"
        try:
            browser.close()
        except Exception as error:
            state["errors"].append("Browser shutdown: " + scrub(error))
            state["status"] = "error"
        confirmations.persist()
        for item in confirmations.items:
            if item["captureStatus"] != "captured":
                state["evidenceGaps"].append(f"{item['id']}: confirmation screenshot {item['captureStatus']}.")
            if not item.get("choice"):
                state["evidenceGaps"].append(f"{item['id']}: operator choice unresolved.")
        if state["status"] == "completed" and state["evidenceGaps"]:
            state["status"] = "incomplete"
        state["endedAtUtc"] = datetime.now(timezone.utc).isoformat()
        save(directory / "run.json", state)
        review = {"targetOutcome": "unknown", "targetEvidence": "Not reviewed. Inspect the recording and actual effects.",
                  "confirmations": [{"id": item["id"], "warning": "unassessed", "quote": "", "consequence": "",
                                     "notes": "Not reviewed.", "ordinaryReference": ""} for item in confirmations.items]}
        save(directory / "analysis.json", review)
    return state
