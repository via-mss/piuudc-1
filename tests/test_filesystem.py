import tempfile
import unittest
from pathlib import Path

from piuudc.filesystem import read_text, write_text


class ReadTextTests(unittest.TestCase):
    def test_returns_default_for_missing_file(self) -> None:
        self.assertEqual(read_text("missing.file", "fallback"), "fallback")

    def test_reads_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sample.txt"
            target.write_text("hello", encoding="utf-8")
            self.assertEqual(read_text(str(target)), "hello")

    def test_write_text_creates_parents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "nested" / "sample.txt"
            write_text(str(target), "created")
            self.assertEqual(target.read_text(encoding="utf-8"), "created")


if __name__ == "__main__":
    unittest.main()
