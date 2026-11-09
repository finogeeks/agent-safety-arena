"""The guide supplements the actual submitted prompt and cannot replace it."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import test_detail_revision as fixtures
from arena.reporting.bilingual import export_reports, validate


class PromptGenerationGuideTests(unittest.TestCase):
    fixture = fixtures.DetailRevisionTests.fixture

    def record(self, root):
        record = self.fixture(root)
        text = 'Run this fixed program.\n```python\nprint("owned fixture")\n```\n'
        sha = hashlib.sha256(text.encode()).hexdigest()
        record['prompt'].update(text=text, language='en', sha256=sha)
        for group in record['groups'].values():
            group['conditions']['promptSha256'] = sha
        record['presentation'].update(dense=True, promptGeneration=dict(
            generationPrompt='Write a Python program for the owned fixture.'))
        script='print("owned fixture")\n'
        record['presentation']['promptGeneration'].update(fixedScript=script,
            fixedScriptSha256=hashlib.sha256(script.encode()).hexdigest())
        return record

    def test_guide_has_two_disclosures_and_preserves_original_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = self.record(root)
            path = root / 'record.json'
            path.write_text(json.dumps(record), encoding='utf8')
            before = path.read_bytes()
            export_reports(path, root / 'site')
            page = (root / 'site/zh-CN.html').read_text('utf8')
            section = page.split('id="section-4"')[1].split('</section>')[0]
            self.assertEqual(section.count('<details'), 2)
            self.assertIn('查看 Agent 运行 Prompt', section)
            self.assertIn('生成并保存 Python 脚本', section)
            self.assertIn('Write a Python program for the owned fixture.', section)
            self.assertIn('Run this fixed program.', section)
            self.assertIn('提示词当中的脚本是由AI根据普通提示词生成的。', section)
            self.assertIn(record['prompt']['sha256'], section)
            self.assertIn('id="fixed-script"', section)
            self.assertEqual((root / 'site/prompt.txt').read_text('utf8'), record['prompt']['text'])
            self.assertEqual(path.read_bytes(), before)
            markdown = (root / 'site/zh-CN.md').read_text('utf8')
            self.assertIn('Write a Python program for the owned fixture.', markdown)
            self.assertIn('Run this fixed program.', markdown)

    def test_empty_or_unknown_guide_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            record = self.record(Path(folder))
            for guide in [dict(generationPrompt=''),
                          dict(generationPrompt='Write.', originalPrompt='replace'),
                          dict(generationPrompt='Write.',fixedScript='print(1)'),
                          dict(generationPrompt='Write.',fixedScript='print(1)',fixedScriptSha256='0'*64),
                          {}, []]:
                changed = deepcopy(record)
                changed['presentation']['promptGeneration'] = guide
                with self.subTest(guide=guide), self.assertRaises(ValueError): validate(changed)


if __name__ == '__main__': unittest.main()
