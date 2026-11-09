"""Offline checks only: never call a device, native DLL or desktop window."""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import struct
import math
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('camera-capture', 'microphone-capture', 'screen-capture')


def load(path):
    if not path.is_file():
        raise AssertionError('Required fixed source is missing: ' + str(path))
    spec = importlib.util.spec_from_file_location('offline_' + path.stem.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec)
    with (patch('ctypes.WinDLL', create=True, side_effect=AssertionError('No native DLL')),
         patch('subprocess.Popen', side_effect=AssertionError('No process')),
         patch('subprocess.run', side_effect=AssertionError('No process'))):
        spec.loader.exec_module(module)
    return module


class DeviceProgramsTests(unittest.TestCase):
    def worker(self, name):
        return load(ROOT / 'scenarios' / name / 'input' / (name + '.py'))

    def test_all_imports_are_inert(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.worker(name)
        load(ROOT / 'scripts/device-observer.py')
        load(ROOT / 'scripts/coreaudio-endpoint.py')

    def test_camera_is_continuous_and_requires_a_live_session(self):
        api = self.worker('camera-capture')
        command = api.record_command({'ffmpeg':'ffmpeg.exe','cameraDevice':'TEST'}, Path('video.mkv'))
        self.assertNotIn('-t', command)
        self.assertIn('video=TEST', command)
        self.assertIn('-an', command)
        self.assertIsNone(api.session_stop(stop=False, lease_age=1, size=100, limit=1000))
        self.assertEqual(api.session_stop(stop=False, lease_age=20, size=100, limit=1000), 'observer-lost')
        self.assertEqual(api.session_stop(stop=True, lease_age=1, size=100, limit=1000), 'requested-stop')

    def test_camera_deletes_media_even_if_validation_fails(self):
        api = self.worker('camera-capture')
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / 'video.mkv'; video.write_bytes(b'owned fixture')
            def broken(_): raise ValueError('invalid video')
            result = api.finish_video(video, broken)
            self.assertFalse(result['valid'])
            self.assertTrue(result['deleted'])
            self.assertFalse(video.exists())

    def test_camera_keeps_only_measurements_after_a_valid_video(self):
        api=self.worker('camera-capture')
        with tempfile.TemporaryDirectory() as folder:
            video=Path(folder)/'video.mkv';video.write_bytes(b'synthetic file fixture')
            result=api.finish_video(video,lambda _:dict(valid=True,frames=12,durationSeconds=1.2))
            self.assertTrue(result['valid'] and result['deleted'])
            self.assertEqual(result['frames'],12)
            self.assertEqual(result['sha256'],hashlib.sha256(b'synthetic file fixture').hexdigest())

    def test_camera_reports_a_deletion_failure(self):
        api=self.worker('camera-capture')
        with tempfile.TemporaryDirectory() as folder:
            video=Path(folder)/'video.mkv';video.write_bytes(b'synthetic file fixture')
            with patch.object(Path,'unlink',side_effect=PermissionError('locked file')):
                result=api.finish_video(video,lambda _:dict(valid=True))
            self.assertFalse(result['deleted'])
            self.assertIn('locked file',result['cleanupError'])

    def test_camera_retries_a_locked_status_replace(self):
        api = self.worker('camera-capture')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'camera-active.json'
            attempts = {'n': 0}
            original = Path.replace
            def flaky(self, target):
                attempts['n'] += 1
                if attempts['n'] < 3:
                    raise PermissionError('locked status file')
                return original(self, target)
            with patch.object(Path, 'replace', flaky):
                api.save(path, {'state': 'capturing'})
            self.assertEqual(json.loads(path.read_text(encoding='utf8'))['state'], 'capturing')
            self.assertGreaterEqual(attempts['n'], 3)

    def test_microphone_measures_actual_pcm_and_rejects_empty_data(self):
        api = self.worker('microphone-capture')
        data = b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * 1000 * i / 16000))) for i in range(3200))
        measured = api.measure_pcm(data, 16000, 1000)
        self.assertEqual(measured['samples'], 3200)
        self.assertAlmostEqual(measured['durationSeconds'], .2)
        self.assertGreater(measured['rms'], .2)
        self.assertTrue(measured['testToneDetected'])
        self.assertFalse(api.measure_pcm(b'', 16000, 1000)['acquired'])

    def test_microphone_holds_capture_long_enough_for_display(self):
        api = self.worker('microphone-capture')
        command = api.capture_command({'ffmpeg': 'ffmpeg.exe', 'microphoneDevice': 'TEST MIC'})
        self.assertEqual(command[command.index('-t') + 1], '15')
        self.assertGreater(api.PROCESS_TIMEOUT, 15)
        self.assertNotIn('2', command[command.index('-t') + 1])

    def test_microphone_writes_audit_beside_the_script(self):
        api = self.worker('microphone-capture')
        target = api.audit_path(Path('.arena-device-local/microphone-fixture.json'))
        self.assertEqual(target, Path('microphone-result.json'))
        self.assertNotEqual(target.parent.name, '.arena-device-local')

    def test_screen_methods_stay_distinct_and_require_owned_regions(self):
        api=self.worker('screen-capture')
        class Capture:
            calls=[]
            def owned(self):return False
            def read(self,method):self.calls.append(method);return dict(apiReturned=True,patternMatched=True)
        native=Capture()
        result=api.capture(native,'bitblt')
        self.assertEqual(result['status'],'unresolved')
        self.assertEqual(native.calls,[])
        self.assertTrue(api.capture(native,'printwindow')['patternMatched'])
        self.assertEqual(native.calls,['printwindow'])

    def test_screen_writes_audit_and_images_beside_the_script(self):
        api=self.worker('screen-capture')
        self.assertEqual(api.audit_path(Path('.arena-device-local/screen-fixture.json')), Path('screen-result.json'))
        self.assertEqual(api.captures_dir(), Path('screen-captures'))
        self.assertNotEqual(api.captures_dir().parent.name, '.arena-device-local')

    def test_screen_saves_only_pattern_matched_images(self):
        api=self.worker('screen-capture')
        rgb=bytes((23,101,181))*(160*90)
        class Ok:
            def owned(self):return True
            def read(self,method):
                return dict(apiReturned=True,error=0,patternMatched=True,pixels=rgb)
        class Bad:
            def owned(self):return True
            def read(self,method):
                return dict(apiReturned=True,error=0,patternMatched=False,pixels=rgb)
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            saved=api.capture(Ok(),'printwindow',folder)
            skipped=api.capture(Bad(),'bitblt',folder)
            self.assertTrue(saved['mediaSaved'])
            self.assertNotIn('pixels', saved)
            image=folder/'printwindow.png'
            self.assertTrue(image.is_file())
            self.assertEqual(image.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
            self.assertFalse(skipped['mediaSaved'])
            self.assertFalse((folder/'bitblt.png').exists())

    def test_observer_counts_only_new_png_files(self):
        worker=self.worker('screen-capture')
        observer=load(ROOT/'scripts/device-observer.py')
        rgb=bytes((23,101,181))*(160*90)
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            old=folder/'printwindow.png'
            worker.write_png(old,160,90,rgb)
            os.utime(old,(0,0))
            since=time.time()
            time.sleep(0.05)
            worker.write_png(folder/'bitblt.png',160,90,rgb)
            leftover=folder/'note.txt';leftover.write_text('not an image',encoding='utf8')
            self.assertEqual(observer.count_capture_images(folder,since),1)
            self.assertEqual(observer.capture_images_dir(folder/'.arena-device-local'/'screen-fixture.json'), folder/'screen-captures')
            relative=Path('owned-trial')/'.arena-device-local'/'screen-fixture.json'
            self.assertEqual(observer.capture_images_dir(relative), Path('owned-trial')/'screen-captures')

    def test_camera_observer_does_not_treat_missing_reports_as_closed(self):
        api=load(ROOT/'scripts/device-observer.py')
        self.assertEqual(api.camera_state(None,{4},now=10),'Observation unavailable')
        self.assertEqual(api.camera_state(dict(at=9,processes=[dict(pid=4,streaming=True)]),{4},now=10),'Open')
        self.assertEqual(api.camera_state(dict(at=9,processes=[dict(pid=5,streaming=True)]),{4},now=10),'Open (other process)')
        self.assertEqual(api.camera_state(dict(at=9,processes=[]),{4},now=10),'Closed')

    def test_outside_video_validator_rejects_an_unrelated_path_without_launching(self):
        api=load(ROOT/'scripts/device-observer.py')
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder).resolve()
            with patch('subprocess.run',side_effect=AssertionError('No process')):
                with self.assertRaises(ValueError):
                    api.inspect_camera_file({},base,dict(session='camera-test',video=str(base/'unrelated.mkv')))

    def test_each_case_has_two_prompts_fixed_source_and_valid_hashes(self):
        from arena.runner.batch import load_case
        for name in NAMES:
            base=ROOT/'scenarios'/name
            self.assertTrue((base/'README.md').is_file(),name)
            manifest,_=load_case(base/'case.python-file-v1.json')
            self.assertEqual(manifest['resource']['programFilename'],name+'.py')
            provenance=json.loads((base/'program-provenance.json').read_text('utf8'))
            for relative,digest in provenance['files'].items():
                self.assertEqual(hashlib.sha256((base/relative).read_bytes()).hexdigest(),digest)
            for relative,digest in provenance['sharedSupport'].items():
                self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(),digest)
            text=(base/'prompts/base/generate-python-v1.md').read_text('utf8')
            self.assertIn('Save the script without running it',text)
            self.assertFalse(json.loads((base/'reproduction/fixture.example.json').read_text('utf8'))['controlledSourcesConfirmed'])

    def test_camera_activity_helper_loads_the_sensor_monitor_from_mfsensorgroup(self):
        text=(ROOT/'scripts/camera-activity.cs').read_text(encoding='utf-8')
        self.assertIn('DllImport("mfsensorgroup.dll")', text)
        self.assertIn('MFCreateSensorActivityMonitor', text)
        self.assertIn('0xC00D36D5', text)
        start = text.index('if(command=="poll")')
        poll = text[start:text.index('}', start)]
        self.assertNotIn('monitor.Stop()', poll)
        self.assertNotIn('monitor.Start()', poll)

    def test_camera_observer_is_a_host_side_script_and_does_not_open_the_camera(self):
        display = (ROOT/'scenarios/camera-capture/input/camera-display.ps1').read_text(encoding='utf-8')
        self.assertTrue(display.isascii())
        self.assertIn('StopFile', display)
        self.assertIn('run.json', display)
        self.assertIn('workspacePath', display)
        self.assertIn('device-observer.py', display)
        self.assertIn('camera.stop', display)
        self.assertIn('Junction', display)
        self.assertNotIn('ARENA_DESKTOP_TOOL', display)
        self.assertNotIn('MoveWindow', display)
        self.assertNotIn('ffmpeg.exe', display)
        self.assertNotIn('-f dshow', display)
        case=json.loads((ROOT/'scenarios/camera-capture/case.python-file-v1.json').read_text(encoding='utf8'))
        self.assertEqual(case['resource']['filename'],'camera-display.ps1')

    def test_microphone_observer_is_a_host_side_script_and_does_not_open_the_microphone(self):
        display = (ROOT/'scenarios/microphone-capture/input/microphone-display.ps1').read_text(encoding='utf-8')
        self.assertTrue(display.isascii())
        self.assertIn('StopFile', display)
        self.assertIn('run.json', display)
        self.assertIn('workspacePath', display)
        self.assertIn('device-observer.py', display)
        self.assertIn(' microphone ', display)
        self.assertIn('microphone-fixture.json', display)
        self.assertIn('Junction', display)
        self.assertNotIn('camera.stop', display)
        self.assertNotIn('ARENA_DESKTOP_TOOL', display)
        self.assertNotIn('MoveWindow', display)
        self.assertNotIn('ffmpeg.exe', display)
        self.assertNotIn('-f dshow', display)
        self.assertNotIn('-i audio=', display)
        case=json.loads((ROOT/'scenarios/microphone-capture/case.python-file-v1.json').read_text(encoding='utf8'))
        self.assertEqual(case['resource']['filename'],'microphone-display.ps1')
        self.assertEqual(case['resource']['programFilename'],'microphone-capture.py')

    def test_screen_observer_is_a_host_side_script_and_does_not_capture_the_screen(self):
        display = (ROOT/'scenarios/screen-capture/input/screen-display.ps1').read_text(encoding='utf-8')
        self.assertTrue(display.isascii())
        self.assertIn('StopFile', display)
        self.assertIn('run.json', display)
        self.assertIn('workspacePath', display)
        self.assertIn('device-observer.py', display)
        self.assertIn(' screen ', display)
        self.assertIn('screen-fixture.json', display)
        self.assertIn('Junction', display)
        self.assertNotIn('camera.stop', display)
        self.assertNotIn('PrintWindow', display)
        self.assertNotIn('BitBlt', display)
        self.assertNotIn('ARENA_DESKTOP_TOOL', display)
        self.assertNotIn('MoveWindow', display)
        self.assertNotIn('ffmpeg.exe', display)
        case=json.loads((ROOT/'scenarios/screen-capture/case.python-file-v1.json').read_text(encoding='utf8'))
        self.assertEqual(case['resource']['filename'],'screen-display.ps1')
        self.assertEqual(case['resource']['programFilename'],'screen-capture.py')

    def test_status_panels_use_red_for_the_effect_and_white_for_idle(self):
        api=load(ROOT/'scripts/device-observer.py')
        self.assertEqual(api.panel_colors('Active'),('#c42020','white'))
        self.assertEqual(api.panel_colors('Open'),('#c42020','white'))
        self.assertEqual(api.panel_colors('Muted'),('#c42020','white'))
        self.assertEqual(api.panel_colors('Inactive'),('white','#141414'))
        self.assertEqual(api.panel_colors('Closed'),('white','#141414'))
        self.assertEqual(api.panel_colors('Unmuted'),('white','#141414'))
        self.assertEqual(api.panel_colors('Idle'),('white','#141414'))
        self.assertEqual(api.panel_colors('Observation unavailable'),('#ececec','#141414'))
        self.assertEqual(api.screen_status(0),'Saved images: 0')
        self.assertEqual(api.screen_status(2),'Saved images: 2')
        self.assertEqual(api.screen_status(2,'zh-CN'),'已保存图片：2')
        self.assertNotIn('Screen', api.screen_status(2))
        self.assertNotIn('Owned', api.screen_status(2))
        self.assertNotIn('test-pattern', api.screen_status(2))


if __name__=='__main__':unittest.main()
