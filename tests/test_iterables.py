import unittest

from piuudc.iterables import chunked, flatten_once, unique_preserve_order


class ChunkedTests(unittest.TestCase):
    def test_chunked_groups_items_by_size(self) -> None:
        self.assertEqual(chunked(["a", "b", "c"], 2), [["a", "b"], ["c"]])

    def test_chunked_rejects_non_positive_size(self) -> None:
        with self.assertRaises(ValueError):
            chunked(["a"], 0)

    def test_flatten_once_joins_nested_lists(self) -> None:
        self.assertEqual(flatten_once([["a"], ["b", "c"]]), ["a", "b", "c"])

    def test_unique_preserve_order_removes_repeats(self) -> None:
        self.assertEqual(unique_preserve_order(["x", "y", "x", "z", "y"]), ["x", "y", "z"])


if __name__ == "__main__":
    unittest.main()
