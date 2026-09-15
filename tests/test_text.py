import unittest

from piuudc.text import is_blank, normalize_whitespace


class NormalizeWhitespaceTests(unittest.TestCase):
    def test_collapses_mixed_whitespace(self) -> None:
        self.assertEqual(normalize_whitespace("  alpha\n beta\t gamma  "), "alpha beta gamma")

    def test_is_blank_for_whitespace_only_input(self) -> None:
        self.assertTrue(is_blank(" \n\t "))
        self.assertFalse(is_blank("  data "))


if __name__ == "__main__":
    unittest.main()
