import unittest

from piuudc.numbers import clamp


class ClampTests(unittest.TestCase):
    def test_clamp_respects_range_bounds(self) -> None:
        self.assertEqual(clamp(-1, 0, 10), 0)
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(11, 0, 10), 10)


if __name__ == "__main__":
    unittest.main()
