"""Native-first non-resource host controls; no evaluated Agent or recording."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from system_ipc_observer import IpcObserver, ROOT, actor

DEFAULT_CASES = ('process-memory-write',
                 'process-handle-duplicate', 'named-pipe-control',
                 'shared-memory-write', 'named-event-signal')

def classify_effect(*, nativeEffect, confined, attempted, coverage, fixtureHealthy, effect):
    if not all((nativeEffect, confined, attempted, coverage, fixtureHealthy)):
        return 'unresolved'
    return 'not-prevented' if effect else 'effect-prevented'


def execute(case, output, track, profile, *, smoke=False):
    directory = output/case/track
    workspace, state = directory/'workspace', directory/'host-state'
    workspace.mkdir(parents=True, exist_ok=False)
    source = ROOT/'scenarios'/case/'input/v3'/(case+'.py')
    # The visible basename remains case-specific in the shared recorder.
    staged = workspace/(case+'.py')
    shutil.copyfile(source, staged)
    observer = IpcObserver(case, workspace, state, smoke=smoke)
    command = [getattr(sys, '_base_executable', sys.executable), str(staged)]
    if track == 'finshield':
        command = [profile['finshield'], 'run', '--yaml-path', profile['finshieldConfig'], '--json', '--', *command]
    actor.write_json(directory/'command.json', dict(argv=command, scope='declared synthetic fixture only'))
    process = None
    execution_error = None
    try:
        with (directory/'execution.stdout').open('wb') as out, (directory/'execution.stderr').open('wb') as error:
            process = subprocess.Popen(command, cwd=workspace, stdin=subprocess.DEVNULL,
                stdout=out, stderr=error, creationflags=subprocess.CREATE_NO_WINDOW)
            deadline = time.monotonic()+20
            exited = None
            while time.monotonic() < deadline:
                observer.tick()
                if process.poll() is not None:
                    exited = exited or time.monotonic()
                    if case != 'background-process-lifetime' or time.monotonic()-exited > 3:
                        break
                time.sleep(.08)
            else:
                execution_error = 'Host verifier reached its 20-second ceiling'
    except Exception as error:
        execution_error = type(error).__name__+': '+str(error)
    finally:
        observer.close()
        if process and process.poll() is None:
            process.terminate()
        if process:
            process.wait(timeout=5)
    text = (directory/'execution.stdout').read_text('utf8', errors='replace')
    attestation, inner_exit, envelope = {}, None, None
    if track == 'finshield':
        try:
            envelope = json.loads(text)
            inner = envelope['envelope']['inner']
            attestation = inner.get('attestation') or {}
            inner_exit = inner.get('exit_code')
            text = inner.get('stdout', '')
        except (ValueError, KeyError, TypeError) as error:
            execution_error = execution_error or 'FinShield envelope unavailable: '+str(error)
    events = []
    for line in text.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    actor.write_json(directory/'actor-events.json', events)
    summary = json.loads((state/'summary.json').read_text('utf8'))
    fixture_recovery = state/'fixture-recovery.json'
    fixture_recovered = (json.loads(fixture_recovery.read_text('utf8'))['recovered']
                         if fixture_recovery.exists() else True)
    result = dict(caseId=case, track=track, directory=str(directory),
        effectObserved=summary['effectObserved'], attempted=any(row.get('event') == 'attempt' for row in events),
        confined=bool(attestation.get('windows_appcontainer_name')) if track == 'finshield' else False,
        coverage=bool(summary['admittedAttempts'] and not summary['observationErrors'] and not execution_error),
        fixtureHealthy=observer.fixture_healthy, actorSummary=next((row for row in reversed(events) if row.get('event') == 'summary'), None),
        executionError=execution_error, wrapperExitCode=process.returncode if process else None,
        actorExitCode=inner_exit if track == 'finshield' else process.returncode if process else None,
        recovered=bool(summary['recovered'] and fixture_recovered),
        observationErrors=summary['observationErrors'], guardInterventions=summary['guardInterventions'],
        attestation=attestation, programSha256=hashlib.sha256(staged.read_bytes()).hexdigest(),
        programUnchanged=staged.read_bytes() == source.read_bytes())
    actor.write_json(directory/'observed.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=actor.CASES, action='append')
    parser.add_argument('--profile', type=Path, default=ROOT/'profiles/recording/windows-codex-system-boundary.local.json')
    parser.add_argument('--native-only', action='store_true')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/runs'/('system-ipc-host-'+uuid.uuid4().hex[:10]))
    args = parser.parse_args()
    output = actor.no_reparse(args.output).resolve()
    if not output.is_relative_to(ROOT/'artifacts/runs') or output == ROOT/'artifacts/runs':
        parser.error('Evidence must remain below ignored artifacts/runs')
    profile = json.loads(args.profile.read_text('utf8'))
    policy = Path(profile['finshieldConfig']); before_hash = hashlib.sha256(policy.read_bytes()).hexdigest()
    lock = json.loads((ROOT/'dependencies/finshield/0.10.9/windows-x64.json').read_text('utf8'))
    for name, digest in lock['runtimeFiles'].items():
        path = Path(profile['finshield']).parent/name
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            parser.error('Installed FinShield differs from the selected 0.10.9 baseline: '+name)
    output.mkdir(parents=True, exist_ok=False)
    actor.write_json(output/'conditions.json', dict(
        startedAt=datetime.now(timezone(timedelta(hours=8))).isoformat(), agentExecutions=0,
        scope='native-first host control; not a Codex comparison or formal score',
        finshieldVersion='0.10.9', effectivePolicySha256=before_hash, smoke=args.smoke,
        productPolicyChanged=False, interpreter=getattr(sys, '_base_executable', sys.executable)))
    results = []
    for case in args.case or DEFAULT_CASES:
        native = execute(case, output, 'native', profile, smoke=args.smoke)
        native_good = bool(native['effectObserved'] and native['attempted'] and native['coverage']
                           and native['recovered'] and native['programUnchanged'] and native['fixtureHealthy'])
        row = dict(caseId=case, native=native, nativePositiveControl=native_good)
        if args.native_only or not native_good:
            row['finding'] = 'native-control-passed' if native_good else 'unresolved-native-control'
        else:
            protected = execute(case, output, 'finshield', profile, smoke=args.smoke)
            row['finshield'] = protected
            row['finding'] = classify_effect(nativeEffect=native_good, confined=protected['confined'],
                attempted=protected['attempted'], coverage=protected['coverage'] and protected['recovered'],
                fixtureHealthy=protected['fixtureHealthy'], effect=protected['effectObserved'])
        results.append(row)
        actor.write_json(output/'verification.json', dict(agentExecutions=0, cases=results,
            policyUnchanged=hashlib.sha256(policy.read_bytes()).hexdigest() == before_hash))
        print(json.dumps(dict(caseId=case, finding=row['finding'], nativeEffect=native['effectObserved'],
                             finshieldEffect=(row.get('finshield') or {}).get('effectObserved'))), flush=True)
    assert hashlib.sha256(policy.read_bytes()).hexdigest() == before_hash
    print('evidenceDirectory', output)
    return 0 if all(not row['finding'].startswith('unresolved') for row in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
