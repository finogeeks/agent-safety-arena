"""Speaker-on Agent comparison case is withdrawn."""
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SpeakerMuteRecordingTests(unittest.TestCase):
    def test_speaker_leak_is_withdrawn_from_the_catalog_and_case_tree(self):
        taxonomy = json.loads((ROOT / 'scenarios/catalog.json').read_text(encoding='utf8'))
        self.assertNotIn('speaker-mute', taxonomy['scenarios'])
        self.assertFalse((ROOT / 'scenarios/speaker-mute').exists())
        index = (ROOT / 'scenarios/README.md').read_text(encoding='utf8')
        self.assertNotIn('speaker-mute', index)
        observer = (ROOT / 'scripts/device-observer.py').read_text(encoding='utf8')
        self.assertNotIn('scenarios/speaker-mute', observer)
        self.assertIn('coreaudio-endpoint.py', observer)


if __name__ == '__main__':
    unittest.main()
