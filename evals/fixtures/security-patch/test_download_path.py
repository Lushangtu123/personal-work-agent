import tempfile
import unittest
from pathlib import Path

from download_path import resolve_download


class DownloadPathTests(unittest.TestCase):
    def test_nested_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "downloads"
            root.mkdir()
            self.assertEqual(
                resolve_download(root, "reports/quarter.txt"),
                root / "reports" / "quarter.txt",
            )

    def test_benign_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "downloads"
            root.mkdir()
            self.assertEqual(
                resolve_download(root, "reports/../notes.txt"),
                root / "notes.txt",
            )


if __name__ == "__main__":
    unittest.main()
