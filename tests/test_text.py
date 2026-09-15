import unittest

from piuudc.text import is_blank, normalize_whitespace, slugify


class NormalizeWhitespaceTests(unittest.TestCase):
    def test_collapses_mixed_whitespace(self) -> None:
        self.assertEqual(normalize_whitespace("  alpha\n beta\t gamma  "), "alpha beta gamma")

    def test_is_blank_for_whitespace_only_input(self) -> None:
        self.assertTrue(is_blank(" \n\t "))
        self.assertFalse(is_blank("  data "))

    def test_slugify_uses_single_dashes(self) -> None:
        self.assertEqual(slugify("  Project  Name "), "project-name")


if __name__ == "__main__":
    unittest.main()
