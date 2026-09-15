import unittest

from piuudc.text import normalize_whitespace


class NormalizeWhitespaceTests(unittest.TestCase):
    def test_collapses_mixed_whitespace(self) -> None:
        self.assertEqual(normalize_whitespace("  alpha\n beta\t gamma  "), "alpha beta gamma")


if __name__ == "__main__":
    unittest.main()
