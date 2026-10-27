import unittest

from summary import category_summary


class SummaryTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(category_summary(0), "No suspicious categories detected.")


if __name__ == "__main__":
    unittest.main()
