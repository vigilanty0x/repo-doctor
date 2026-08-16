import unittest

from duplicate_finder.core import find


class DuplicateFinderTests(unittest.TestCase):
    def test_exact_and_normalized_groups(self):
        records = [{"id": "1", "x": " A "}, {"id": "2", "x": "a"}]
        result = find(records, ["x"])
        self.assertEqual(result["exact"], [])
        self.assertEqual(result["normalized"], [["1", "2"]])

    def test_multi_field_is_distinct(self):
        records = [{"id": "1", "x": "a", "y": 1}, {"id": "2", "x": "a", "y": 2}]
        self.assertEqual(find(records, ["x", "y"])["exact"], [])

    def test_fields_and_records_are_strict(self):
        for records, fields in (([], []), ("bad", ["x"]), ([{"id": "1"}], ["x"]), ([{"id": "1", "x": 1}], "x")):
            with self.subTest(records=records, fields=fields), self.assertRaises(ValueError):
                find(records, fields)

    def test_ids_must_be_unique_strings(self):
        with self.assertRaises(ValueError):
            find([{"id": "1", "x": 1}, {"id": "1", "x": 1}], ["x"])


if __name__ == "__main__":
    unittest.main()
