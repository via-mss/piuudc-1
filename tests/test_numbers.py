import unittest

from piuudc.numbers import clamp, safe_int


class ClampTests(unittest.TestCase):
    def test_clamp_respects_range_bounds(self) -> None:
        self.assertEqual(clamp(-1, 0, 10), 0)
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(11, 0, 10), 10)

    def test_safe_int_falls_back_for_invalid_input(self) -> None:
        self.assertEqual(safe_int("12"), 12)
        self.assertEqual(safe_int("bad", 9), 9)


if __name__ == "__main__":
    unittest.main()
