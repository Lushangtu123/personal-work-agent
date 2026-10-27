import unittest

from labels import label


class LabelTests(unittest.TestCase):
    def test_outer_whitespace(self):
        self.assertEqual(label("  A  B  "), "A  B")

    def test_empty_name(self):
        with self.assertRaises(ValueError):
            label(" \t\n ")


if __name__ == "__main__":
    unittest.main()
