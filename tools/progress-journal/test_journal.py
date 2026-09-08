"""Offline checks for containment, history and portable output."""
import json
from pathlib import Path
import tempfile
import unittest
from journal import prepare

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/'images').mkdir()
        (self.root/'images/frame one.png').write_bytes(b'example image bytes')

    def run_prepare(self, title='Review', **kw):
        return prepare(self.root, title, 'A generic design note.',
                       kw.get('images', ['images/frame one.png']), [],
                       kw.get('journal', 'docs/journal.md'),
                       kw.get('entries', 'docs/history.json'), '.journal/publish.json')

    def test_history_links_and_no_workspace_identity(self):
        self.run_prepare('First review')
        result = self.run_prepare('Second review')
        history = json.loads((self.root/'docs/history.json').read_text())
        self.assertEqual([x['title'] for x in history], ['Second review', 'First review'])
        text = (self.root/'docs/journal.md').read_text()
        self.assertIn('../images/frame%20one.png', text)
        self.assertNotIn(str(self.root), text + json.dumps(result) + json.dumps(history))
        self.assertEqual(set(history[0]), {'utc','title','note','images'})
        self.assertNotIn('.journal/publish.json', result['paths'])

    def test_path_escape_is_rejected_without_writing(self):
        with self.assertRaises(ValueError):
            self.run_prepare(images=['../outside.png'])
        self.assertFalse((self.root/'docs').exists())
        with tempfile.TemporaryDirectory() as outside:
            (self.root/'escape').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                self.run_prepare(journal='escape/journal.md')

    def test_missing_image_and_colliding_outputs(self):
        with self.assertRaises(FileNotFoundError):
            self.run_prepare(images=['missing.png'])
        with self.assertRaises(ValueError):
            self.run_prepare(journal='same.json', entries='same.json')
        with self.assertRaises(ValueError):
            self.run_prepare('Invalid\ntitle')

if __name__ == '__main__':
    unittest.main()
