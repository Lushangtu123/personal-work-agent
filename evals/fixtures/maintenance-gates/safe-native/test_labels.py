import unittest

from labels import summarize


class LabelTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(summarize(0), "No labels")

    def test_singular(self):
        self.assertEqual(summarize(1), "1 label")

    def test_plural(self):
        self.assertEqual(summarize(2), "2 labels")


if __name__ == "__main__":
    unittest.main()
