import unittest

from piuudc.iterables import chunked


class ChunkedTests(unittest.TestCase):
    def test_chunked_groups_items_by_size(self) -> None:
        self.assertEqual(chunked(["a", "b", "c"], 2), [["a", "b"], ["c"]])

    def test_chunked_rejects_non_positive_size(self) -> None:
        with self.assertRaises(ValueError):
            chunked(["a"], 0)


if __name__ == "__main__":
    unittest.main()
