import hashlib
import tempfile
import unittest
from pathlib import Path

from migration_verifier.core import verify


def migration(version, sql):
    return {"version": version, "sql": sql, "sha256": hashlib.sha256(sql.encode()).hexdigest()}


def trusted(*migrations):
    return {str(item["version"]): item["sha256"] for item in migrations}


class MigrationTests(unittest.TestCase):
    def test_trusted_digest_is_required_for_verified_claim(self):
        item = migration(1, "create table x(id);")
        self.assertEqual(verify([item])["status"], "self_consistent")
        result = verify([item], trusted_digests=trusted(item))
        self.assertEqual(result["status"], "verified")
        self.assertIn("x", result["tables"])
        self.assertTrue(result["rolled_back"])

    def test_order_and_digest_fail_closed(self):
        self.assertEqual(verify([migration(2, "select 1;")])["reason"], "non_contiguous")
        item = migration(1, "select 1;")
        item["sha256"] = "0" * 64
        self.assertEqual(verify([item], trusted_digests={"1": "0" * 64})["reason"], "checksum")

    def test_sql_error_rolls_back_batch(self):
        first = migration(1, "create table x(id);")
        second = migration(2, "bad sql;")
        result = verify([first, second], trusted_digests=trusted(first, second))
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["rolled_back"])

    def test_blocks_transaction_control_and_dangerous_pragma(self):
        for sql in ("COMMIT;", "SAVEPOINT attacker;", "PRAGMA writable_schema=ON;"):
            item = migration(1, sql)
            with self.subTest(sql=sql):
                self.assertEqual(verify([item], trusted_digests=trusted(item))["reason"], "forbidden_sql")

    def test_blocks_attach_detach_and_vacuum_into_without_file_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            targets = [Path(directory) / name for name in ("attach.db", "vacuum.db")]
            statements = [f"ATTACH DATABASE '{targets[0]}' AS other;", f"VACUUM INTO '{targets[1]}';", "DETACH DATABASE main;"]
            for sql in statements:
                item = migration(1, sql)
                with self.subTest(sql=sql):
                    self.assertEqual(verify([item], trusted_digests=trusted(item))["status"], "blocked")
            self.assertFalse(any(path.exists() for path in targets))

    def test_rejects_malformed_shapes_and_bool_version(self):
        for items in ([{"version": True, "sql": "select 1;", "sha256": "0" * 64}], [{"version": 1, "sql": "select 1;", "sha256": "0" * 64, "extra": 1}]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                verify(items)


if __name__ == "__main__":
    unittest.main()
