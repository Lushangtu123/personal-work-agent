import unittest

from notes import accept_note


class NotesTests(unittest.TestCase):
    def test_short_note(self):
        self.assertEqual(accept_note("keep spaces "), "keep spaces ")

    def test_oversized_note(self):
        with self.assertRaisesRegex(ValueError, "^note too large$"):
            accept_note("a" * 513)
