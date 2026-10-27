import unittest

from summary import category_summary


class SummaryTests(unittest.TestCase):
    def test_single(self):
        self.assertEqual(category_summary(1), "1 suspicious category detected.")

    def test_multiple(self):
        self.assertEqual(category_summary(2), "2 suspicious categories detected.")
