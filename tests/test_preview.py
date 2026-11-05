"""Preview ordering, crop boundaries, provenance, and real video decoding."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from arena.evidence.preview import export_preview, validate_moments
from arena.adapters.agents.dsh import hidden_process_options


class PreviewTests(unittest.TestCase):
    def test_export_name_cannot_replace_raw_recording_or_escape_run_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'recording.mp4').write_bytes(b'controlled placeholder')
            for name in ('recording.mp4','../escape.mp4'):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError,'output'):
                    export_preview(root,root/'unused.json',ffmpeg='unused',output_name=name)

    def moments(self):
        return [dict(stage=stage,startSeconds=index,durationSeconds=.5)
                for index,stage in enumerate(('opening','effect','response'))]

    def test_rejects_missing_reordered_outside_or_cropped_effect_stages(self):
        info=dict(width=320,height=180,duration=3)
        valid=self.moments()
        self.assertEqual(validate_moments(valid,info),valid)
        invalid=[valid[:2],list(reversed(valid)),
                 [valid[0],valid[1],{**valid[2],'startSeconds':2.9}],
                 [{**valid[0],'crop':[0,0,400,180]},valid[1],valid[2]],
                 [valid[0],{**valid[1],'crop':[0,0,160,180]},valid[2]]]
        for moments in invalid:
            with self.subTest(moments=moments), self.assertRaises(ValueError):
                validate_moments(moments,info)

    @unittest.skipUnless(os.environ.get('ARENA_TEST_FFMPEG'),'Set ARENA_TEST_FFMPEG for export decoding')
    def test_three_stages_decode_in_order_and_preserve_source_hash(self):
        ffmpeg=os.environ['ARENA_TEST_FFMPEG']
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'recording.mp4'
            command=[ffmpeg,'-v','error','-n']
            for color in ('red','green','blue'):
                command+=['-f','lavfi','-i',f'color=c={color}:s=320x180:r=8:d=1']
            command+=['-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[out]',
                '-map','[out]','-c:v','libx264','-pix_fmt','yuv420p',str(source)]
            subprocess.run(command,capture_output=True,check=True,**hidden_process_options())
            before=hashlib.sha256(source.read_bytes()).hexdigest()
            moments=self.moments()
            moments[0]['crop']=[0,0,160,180]
            recipe=root/'moments.json'
            recipe.write_text(json.dumps(moments),encoding='utf8')
            output=export_preview(root,recipe,ffmpeg)
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
            edit=json.loads((root/'overview-edit.json').read_text('utf8'))
            self.assertEqual(edit['sourceSha256'],before)
            self.assertEqual(edit['moments'],moments)
            self.assertAlmostEqual(edit['outputInfo']['duration'],1.5,places=2)
            for index,offset in enumerate((.25,.75,1.25)):
                frame=subprocess.run([ffmpeg,'-v','error','-ss',str(offset),'-i',str(output),
                    '-frames:v','1','-vf','crop=2:2:960:540,scale=1:1,format=rgb24',
                    '-f','rawvideo','pipe:1'],capture_output=True,check=True,**hidden_process_options()).stdout
                self.assertEqual(len(frame),3)
                self.assertEqual(max(range(3),key=lambda channel:frame[channel]),index)
            with self.assertRaisesRegex(ValueError,'already exists'):
                export_preview(root,recipe,ffmpeg)


if __name__=='__main__':
    unittest.main()
