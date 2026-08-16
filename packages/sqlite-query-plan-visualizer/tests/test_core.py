import unittest

from sqlite_query_plan_visualizer import evaluate

FIXTURE = {"tables": [{"name": "items", "columns": [{"name": "key", "type": "TEXT"}, {"name": "value", "type": "TEXT"}], "rows": [["a", "one"], ["b", "two"]]}], "indexes": [{"name": "idx_items_key", "table": "items", "columns": ["key"]}]}
GOOD = {"query": "SELECT value FROM items WHERE key = ?", "parameters": ["a"], "fixture": FIXTURE}


class ContractTests(unittest.TestCase):
    def test_sqlite_generates_real_plan(self):
        result = evaluate(GOOD)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["query_plan"]["source"], "sqlite-explain-query-plan")
        self.assertTrue(result["query_plan"]["uses_index"])

    def test_caller_supplied_plan_strings_are_rejected(self):
        record = {**GOOD, "before_plan": ["SCAN"], "after_plan": ["SEARCH USING INDEX fake"]}
        self.assertEqual(evaluate(record)["status"], "failed")

    def test_with_delete_is_denied(self):
        query = "WITH doomed AS (DELETE FROM items RETURNING *) SELECT * FROM doomed"
        self.assertEqual(evaluate({**GOOD, "query": query, "parameters": []})["status"], "failed")

    def test_write_ddl_attach_and_pragma_are_denied(self):
        for query in ("DELETE FROM items", "CREATE TABLE x(y)", "ATTACH DATABASE ':memory:' AS other", "PRAGMA schema_version"):
            with self.subTest(query=query):
                self.assertEqual(evaluate({**GOOD, "query": query, "parameters": []})["status"], "failed")

    def test_multiple_statements_are_denied(self):
        self.assertEqual(evaluate({**GOOD, "query": "SELECT 1; SELECT 2", "parameters": []})["status"], "failed")

    def test_fixture_identifiers_and_rows_are_validated(self):
        bad = {"tables": [{"name": "items; DROP TABLE x", "columns": [{"name": "x", "type": "TEXT"}], "rows": []}]}
        self.assertEqual(evaluate({"query": "SELECT 1", "fixture": bad})["status"], "failed")
        bad_row = {"tables": [{"name": "items", "columns": [{"name": "x", "type": "TEXT"}], "rows": [[True]]}]}
        self.assertEqual(evaluate({"query": "SELECT * FROM items", "fixture": bad_row})["status"], "failed")

    def test_non_object_and_missing_field_fail_closed(self):
        self.assertEqual(evaluate(None)["status"], "failed")
        self.assertEqual(evaluate({})["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
