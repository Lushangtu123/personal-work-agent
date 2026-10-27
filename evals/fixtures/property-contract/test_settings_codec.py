import unittest

from settings_codec import decode_options, encode_options


class SettingsCodecTests(unittest.TestCase):
    def test_existing_settings_round_trip(self):
        options = {"theme": "dark", "language": "English"}
        self.assertEqual(decode_options(encode_options(options)), options)

    def test_export_order_and_format(self):
        self.assertEqual(
            encode_options({"theme": "dark mode", "language": "English"}),
            "language=English&theme=dark+mode",
        )


if __name__ == "__main__":
    unittest.main()
