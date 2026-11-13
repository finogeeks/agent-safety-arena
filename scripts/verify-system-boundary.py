"""Run bounded host smoke controls, never an evaluated Agent or recording."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from system_boundary_observer import Observer, ROOT, worker

DEFAULT_CASES = ('direct-socket-connect',)


def verify_case(case, root, *, handle_control=False, smoke=True):
    directory = root/(case+('-positive-control' if handle_control else ''))
    workspace, state = directory/'workspace', directory/'host-state'
    workspace.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(ROOT/'scenarios'/case/'input'/(case+'.py'), workspace/(case+'.py'))
    observer = Observer(case, workspace, state, smoke=smoke, handle_control=handle_control)
    process = None
    code = None
    try:
        options = dict(cwd=workspace, stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        if handle_control:
            handle = observer.target['inheritedHandle']
            os.set_handle_inheritable(handle, True)
            startup = subprocess.STARTUPINFO()
            startup.lpAttributeList = {'handle_list': [handle]}
            options.update(startupinfo=startup, close_fds=True)
        with (directory/'worker.stdout').open('wb') as out, (directory/'worker.stderr').open('wb') as error:
            try:
                # A venv redirector can kill its descendants when the command exits.
                # Use the installed base interpreter for this host positive control.
                interpreter = getattr(sys, '_base_executable', sys.executable)
                process = subprocess.Popen([interpreter, str(workspace/(case+'.py'))], stdout=out, stderr=error, **options)
            finally:
                if handle_control:
                    os.set_handle_inheritable(observer.target['inheritedHandle'], False)
            deadline = time.monotonic()+20
            exited = None
            while time.monotonic() < deadline:
                observer.tick()
                if process.poll() is not None:
                    exited = exited or time.monotonic()
                    if case != 'background-process-lifetime' or time.monotonic()-exited > max(1, observer.target['threshold']+.5):
                        break
                time.sleep(.05)
            else:
                observer.interventions.append('Host smoke exceeded its 20-second ceiling')
            code = process.poll()
    finally:
        observer.close()
        if process:
            if process.poll() is None:
                # The exact Popen process is owned; no PID-based broad recovery.
                process.terminate()
            process.wait(timeout=5)
    summary = json.loads((state/'summary.json').read_text('utf8'))
    expected_unsupported = case == 'inherited-handle-write' and not handle_control
    success = (code == 2 and not summary['effectObserved'] if expected_unsupported
               else code == 0 and summary['effectObserved'])
    success = bool(success and summary['recovered'] and not summary['observationErrors']
                   and not summary['guardInterventions'])
    return dict(caseId=case, success=success, exitCode=code, expectedUnsupported=expected_unsupported,
                handlePositiveControl=handle_control, state=str(state), **{'effectObserved': summary['effectObserved']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=worker.CASES, action='append')
    parser.add_argument('--full', action='store_true', help='Verify the declared recording workload instead of smaller smoke parameters')
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/runs'/('system-boundary-host-'+uuid.uuid4().hex[:10]))
    args = parser.parse_args()
    if sys.platform != 'win32':
        parser.error('Native host verification requires Windows')
    output = worker.no_reparse(args.output).resolve()
    if output == ROOT or not output.is_relative_to(ROOT/'artifacts/runs'):
        parser.error('Verification output must stay under ignored artifacts/runs')
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for case in args.case or DEFAULT_CASES:
        row = verify_case(case, output, smoke=not args.full)
        rows.append(row)
        print(json.dumps(row), flush=True)
        if case == 'inherited-handle-write':
            row = verify_case(case, output, handle_control=True, smoke=not args.full)
            rows.append(row)
            print(json.dumps(row), flush=True)
    worker.write_json(output/'verification.json', dict(trialExecutions=0, controls=rows, success=all(row['success'] for row in rows)))
    return 0 if all(row['success'] for row in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
