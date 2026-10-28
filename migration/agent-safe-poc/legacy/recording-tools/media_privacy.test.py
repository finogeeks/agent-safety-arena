"""Privacy masks follow real source times, including previews that omit waiting."""
import unittest
import subprocess


class PrivacyIntervals(unittest.TestCase):
    def test_wait_omission_does_not_shift_masks_onto_the_effect(self):
        from media_privacy import mask_runs
        samples=[1000,1100,1200,8000,8100,8200,10000,10100]
        masks=[{'startUnixMs':8000,'endUnixMs':8200,'rect':[0,0,64,40]}]
        self.assertEqual(mask_runs(samples,masks,64,48),[{'firstFrame':3,'lastFrame':5,'rect':[0,0,64,40]}])

    def test_empty_masks_leave_all_frames_unchanged(self):
        from media_privacy import mask_runs
        self.assertEqual(mask_runs([1,2,3],[],64,48),[])

    def test_final_review_retains_privacy_without_retaining_staging_full_length(self):
        from media_privacy import review_overrides
        masks=[{'startUnixMs':1,'endUnixMs':2,'rect':[0,0,64,40]}]
        self.assertEqual(review_overrides({'bare':{'privacyMasks':masks,'fullRecording':True}}),
            {'bare':{'privacyMasks':masks}})

    def test_out_of_frame_mask_is_rejected(self):
        from media_privacy import mask_runs
        with self.assertRaises(ValueError):
            mask_runs([1],[{'startUnixMs':0,'endUnixMs':2,'rect':[0,0,65,40]}],64,48)

    def test_real_ffmpeg_masks_only_declared_frames_and_rectangle(self):
        import sys
        from pathlib import Path
        sys.path.insert(0,str(Path.home()/'.cache/codex-media-tools'))
        import imageio_ffmpeg
        from media_privacy import mask_runs,ffmpeg_filters
        masks=[{'startUnixMs':200,'endUnixMs':300,'rect':[0,0,640,400]}]
        runs=mask_runs([0,100,200,300,400,500],masks,640,480)
        result=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-f','lavfi',
            '-i','color=c=white:s=640x480:r=10','-frames:v','6','-vf',','.join(ffmpeg_filters(runs)),
            '-pix_fmt','rgb24','-f','rawvideo','pipe:1'],capture_output=True,check=True)
        size=640*480*3
        self.assertEqual(len(result.stdout),6*size)
        for frame in range(6):
            pixel=result.stdout[frame*size:frame*size+3]
            if frame in (2,3):self.assertLess(max(pixel),250)
            else:self.assertGreater(min(pixel),250)
            offset=frame*size+470*640*3
            self.assertGreater(min(result.stdout[offset:offset+3]),250,'Unmasked taskbar rectangle changed')


if __name__=='__main__':
    unittest.main()
