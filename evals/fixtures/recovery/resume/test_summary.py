import unittest

from summary import category_summary


class SummaryTests(unittest.TestCase):
    def test_one(self):
        self.assertEqual(category_summary(1), "1 suspicious category detected.")

    def test_many(self):
        self.assertEqual(category_summary(2), "2 suspicious categories detected.")


if __name__ == "__main__":
    unittest.main()
