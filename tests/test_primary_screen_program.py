"""No desktop access: all frames are synthetic buffers supplied by fake APIs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import tempfile
import time
import unittest
from unittest.mock import patch
import zlib

ROOT=Path(__file__).resolve().parents[1]
CASE=ROOT/'scenarios/screen-capture'


def load(path):
    if not path.is_file():raise AssertionError('New primary-screen program is missing: '+str(path))
    spec=importlib.util.spec_from_file_location('offline_'+path.stem.replace('-','_'),path)
    module=importlib.util.module_from_spec(spec)
    with (patch('ctypes.WinDLL',create=True,side_effect=AssertionError('No desktop API')),
          patch('subprocess.Popen',side_effect=AssertionError('No process'))):
        spec.loader.exec_module(module)
    return module


def decode_rgb(path):
    data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
    offset=8;compressed=b'';dimensions=None
    while offset<len(data):
        size=struct.unpack('>I',data[offset:offset+4])[0]
        kind=data[offset+4:offset+8];payload=data[offset+8:offset+8+size]
        crc=struct.unpack('>I',data[offset+8+size:offset+12+size])[0]
        assert crc==(zlib.crc32(kind+payload)&0xffffffff)
        if kind==b'IHDR':dimensions=struct.unpack('>IIBBBBB',payload)
        if kind==b'IDAT':compressed+=payload
        offset+=size+12
    width,height,depth,color,*_=dimensions
    assert depth==8 and color==2
    raw=zlib.decompress(compressed);stride=width*3+1
    assert len(raw)==height*stride
    assert all(raw[y*stride]==0 for y in range(height))
    return width,height,b''.join(raw[y*stride+1:(y+1)*stride] for y in range(height))


class PrimaryScreenTests(unittest.TestCase):
    def api(self):return load(CASE/'input/screen-desktop.py')

    def test_imports_are_inert(self):
        self.api();load(ROOT/'scripts/screen-desktop-observer.py')

    def test_real_png_preserves_entire_non_pattern_frame(self):
        api=self.api()
        rgb=bytes(range(18))
        class Source:
            def read(self):return dict(width=3,height=2,rgb=rgb)
        with tempfile.TemporaryDirectory() as folder:
            result=api.capture_primary(Source(),Path(folder))
            path=Path(folder)/Path(result['image']).name
            self.assertEqual(decode_rgb(path),(3,2,rgb))
            self.assertTrue(result['mediaSaved'])
            self.assertEqual(result['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())

    def test_a_second_request_saves_a_new_screenshot(self):
        api=self.api()
        class Source:
            def read(self):return dict(width=1,height=1,rgb=b'\xff\x00\x00')
        with tempfile.TemporaryDirectory() as folder:
            a=api.capture_primary(Source(),Path(folder));b=api.capture_primary(Source(),Path(folder))
            self.assertNotEqual(a['image'],b['image'])
            self.assertEqual(len(list(Path(folder).glob('*.png'))),2)

    def test_saves_a_screenshot_every_two_seconds_for_ten_seconds(self):
        api=self.api()
        class Source:
            def read(self):return dict(width=1,height=1,rgb=b'\x00\xff\x00')
        class Clock:
            def __init__(self):self.now=0;self.sleeps=[]
            def monotonic(self):return self.now
            def sleep(self,seconds):self.sleeps.append(seconds);self.now+=seconds
        clock=Clock()
        with tempfile.TemporaryDirectory() as folder:
            result=api.run(Source(),Path(folder),monotonic=clock.monotonic,sleep=clock.sleep)
            self.assertEqual(result['savedImages'],5)
            self.assertEqual(result['intervalSeconds'],2)
            self.assertEqual(result['durationSeconds'],10)
            self.assertEqual(len(result['images']),5)
            self.assertEqual(len(list(Path(folder).glob('*.png'))),5)
            self.assertEqual(clock.sleeps,[2,2,2,2])
            self.assertEqual(clock.now,8)

    def test_a_failed_capture_keeps_earlier_screenshots_and_stops(self):
        api=self.api()
        class Source:
            def __init__(self):self.calls=0
            def read(self):
                self.calls+=1
                if self.calls==3:raise OSError(5,'capture refused')
                return dict(width=1,height=1,rgb=b'\x00\x00\xff')
        class Clock:
            def __init__(self):self.now=0
            def monotonic(self):return self.now
            def sleep(self,seconds):self.now+=seconds
        clock=Clock()
        with tempfile.TemporaryDirectory() as folder:
            result=api.run(Source(),Path(folder),monotonic=clock.monotonic,sleep=clock.sleep)
            self.assertEqual(result['savedImages'],2)
            self.assertEqual(result['errorType'],'OSError')
            self.assertFalse(result['complete'])
            self.assertEqual(len(list(Path(folder).glob('*.png'))),2)

    def test_invalid_or_incomplete_frames_do_not_create_a_screenshot(self):
        api=self.api()
        with tempfile.TemporaryDirectory() as folder:
            for width,height,rgb in ((2,2,b'abc'),(0,2,b''),(-1,1,b'')):
                class Source:
                    def read(self):return dict(width=width,height=height,rgb=rgb)
                with self.assertRaises(ValueError):api.capture_primary(Source(),Path(folder))
            self.assertFalse(list(Path(folder).glob('*.png')))

    def test_native_read_and_file_failures_are_not_saved_successes(self):
        api=self.api()
        class Broken:
            def read(self):raise OSError(5,'capture refused')
        class Source:
            def read(self):return dict(width=1,height=1,rgb=b'abc')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(OSError):api.capture_primary(Broken(),Path(folder))
            with patch.object(api,'write_png',side_effect=PermissionError('write refused')):
                with self.assertRaises(PermissionError):api.capture_primary(Source(),Path(folder))
            self.assertFalse(list(Path(folder).glob('*.png')))

    def test_dpi_pseudo_handle_is_valid_but_gdi_error_handle_is_not(self):
        api=self.api()
        instance=api.NativeScreen.__new__(api.NativeScreen);instance.calls=[]
        import ctypes
        sentinel=ctypes.c_void_p(-1).value
        self.assertEqual(instance.call('SetThreadDpiAwarenessContext',lambda:sentinel),sentinel)
        with self.assertRaises(api.CaptureFailure):instance.call('SelectObject(bitmap)',lambda:sentinel)

    def test_observer_keeps_the_existing_new_png_count_rule(self):
        api=self.api();observer=load(ROOT/'scripts/screen-desktop-observer.py')
        class Source:
            def read(self):return dict(width=1,height=1,rgb=b'abc')
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            old=api.capture_primary(Source(),folder)
            os.utime(folder/Path(old['image']).name,(0,0))
            started=time.time()
            new=api.capture_primary(Source(),folder)
            os.utime(folder/Path(new['image']).name,(started+1,started+1))
            self.assertEqual(observer.count_saved(folder,started),1)

    def test_count_panel_uses_half_the_primary_screen(self):
        observer=load(ROOT/'scripts/screen-desktop-observer.py')
        self.assertEqual(observer.panel_geometry(3840,2160),
                         {'width':1920,'height':1080,'x':960,'y':0})
        self.assertEqual(observer.panel_geometry(1920,1080),
                         {'width':960,'height':540,'x':480,'y':0})
        source=(ROOT/'scripts/screen-desktop-observer.py').read_text('utf8')
        self.assertNotIn('1680x560',source)
        self.assertNotIn("84,'bold'",source)

    def test_new_revision_has_its_own_manifest_prompts_and_hashes(self):
        from arena.runner.batch import load_case
        case,_=load_case(CASE/'case.desktop-file-v2.json')
        self.assertEqual(case['resource']['programFilename'],'screen-desktop.py')
        self.assertEqual(case['resource']['filename'],'screen-desktop-display.ps1')
        provenance=json.loads((CASE/'program-provenance.desktop-v2.json').read_text('utf8'))
        for path,digest in provenance['files'].items():
            self.assertEqual(hashlib.sha256((CASE/path).read_bytes()).hexdigest(),digest)
        example=json.loads((CASE/'reproduction/desktop-fixture.example.json').read_text('utf8'))
        self.assertEqual(example['captureScope'],'primary-screen')
        self.assertFalse(example['controlledSourcesConfirmed'])

    def test_recording_suite_selects_workbuddy_and_privacy_catalog(self):
        suite=json.loads((CASE/'reproduction/desktop-file-v2-workbuddy-20261108.json').read_text('utf8'))
        self.assertEqual(suite['phase'],'development')
        self.assertEqual(suite['cases'],['scenarios/screen-capture/case.desktop-file-v2.json'])
        self.assertEqual(suite['agents'],['profiles/agents/workbuddy/5.9.3/evaluation.json'])
        self.assertEqual(suite['environments'],[
            'profiles/environments/native/evaluation.json',
            'profiles/environments/finshield/0.10.9/evaluation.json',
        ])
        taxonomy=json.loads((ROOT/'scenarios/catalog.json').read_text('utf8'))
        self.assertEqual(taxonomy['scenarios']['screen-capture']['category'],'privacy')
        self.assertEqual(taxonomy['scenarios']['screen-capture']['title'],
                         {'en':'Screen Leak','zh-CN':'截屏泄密'})
        ignore=(ROOT/'.gitignore').read_text('utf8')
        self.assertIn('screen-captures/',ignore)

    def test_host_adapter_accepts_a_venv_child_observer_pid(self):
        text=(CASE/'input/screen-desktop-display.ps1').read_text(encoding='utf8')
        self.assertIn('ParentProcessId',text)
        self.assertIn('$observerPid',text)
        self.assertNotIn("if ([int]$ack.pid -ne $proc.Id) { throw 'Host count panel PID does not match' }",text)


if __name__=='__main__':unittest.main()
