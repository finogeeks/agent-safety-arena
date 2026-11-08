"""Installed FinSafe route and actual daemon identity checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from arena.adapters.agents import workbuddy


class FinSafeWorkBuddyTests(unittest.TestCase):
    def test_workbuddy_doctor_does_not_require_the_dsh_desktop_launcher(self):
        from arena.setup import check_repository
        from test_workbuddy_recording import workbuddy_profile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            executable = root/'finsafe.exe'; executable.write_bytes(b'synthetic executable')
            config = root/'effective.yaml'; config.write_text('synthetic: true')
            profile = root/'profile.json'
            profile.write_text(json.dumps(workbuddy_profile(finshield=str(executable),finshieldConfig=str(config))))
            checks = check_repository(Path(__file__).resolve().parents[1],profile,'finshield')['checks']
            names = {row['name']:row['status'] for row in checks}
            self.assertNotIn('dshDesktop',names)
            self.assertEqual(names['finshield'],'pass')

    def test_only_finshield_wraps_the_native_gui_command(self):
        profile = {'workbuddyEntry':'C:/Apps/WorkBuddy.exe','debugPort':9333}
        confinement = {'executable':'C:/FinSafe/finsafe.exe','config':'C:/FinSafe/effective.yaml'}
        native = workbuddy.launch_command(profile,'C:/owned')
        protected = workbuddy.launch_command(profile,'C:/owned',confinement)
        self.assertEqual(protected, ['C:/FinSafe/finsafe.exe','app','launch','workbuddy',
            '--yaml-path','C:/FinSafe/effective.yaml','--integration-id','workbuddy','--',*native])
        self.assertNotIn('--no-sandbox',protected)

    def test_ready_pid_requires_original_hook_ready_and_a_positive_integer(self):
        self.assertEqual(workbuddy.finshield_main_pid('{"main_pid":123,"hook_ready":true}'),123)
        for line in ['{"main_pid":123}', '{"main_pid":123,"hook_ready":false}',
                     '{"main_pid":true,"hook_ready":true}', '{"main_pid":-1,"hook_ready":true}', 'noise']:
            self.assertIsNone(workbuddy.finshield_main_pid(line))

    def test_chromium_appcontainer_does_not_prove_a_protected_daemon(self):
        rows=[{'pid':1,'parentId':0,'image':'C:/Apps/WorkBuddy.exe','appContainer':False},
              {'pid':2,'parentId':1,'image':'C:/Apps/WorkBuddy.exe','appContainer':True}]
        self.assertEqual(workbuddy.protected_daemon_pids(rows),[])
        rows.extend([{'pid':3,'parentId':1,'image':'C:/FinSafe/finsafe.exe','appContainer':False},
                     {'pid':4,'parentId':3,'image':'C:/Apps/WorkBuddy.exe','appContainer':True}])
        self.assertEqual(workbuddy.protected_daemon_pids(rows),[4])

    def test_missing_launch_files_fail_before_start(self):
        with self.assertRaises(ValueError):
            workbuddy.workbuddy_confinement({'finshield':'C:/absent/finsafe.exe','finshieldConfig':'C:/absent/effective.yaml'})
