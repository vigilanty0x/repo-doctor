"""Transactional SQLite migration verification with explicit digest provenance."""

import hashlib
import re
import sqlite3

MAX_MIGRATIONS = 1_000
MAX_SQL_BYTES = 1_000_000
MAX_TOTAL_SQL_BYTES = 10_000_000
_FORBIDDEN_LEADERS = {"ATTACH", "DETACH", "VACUUM", "BEGIN", "COMMIT", "END", "ROLLBACK", "SAVEPOINT", "RELEASE", "PRAGMA"}


def _statements(sql):
    statements = []
    buffer = ""
    for character in sql:
        buffer += character
        if sqlite3.complete_statement(buffer):
            if buffer.strip():
                statements.append(buffer)
            buffer = ""
    if buffer.strip():
        raise ValueError("migration SQL contains an incomplete statement")
    if not statements:
        raise ValueError("migration SQL must contain at least one statement")
    return statements


def _leader(statement):
    without_comments = re.sub(r"/\*.*?\*/|--[^\r\n]*", " ", statement, flags=re.DOTALL)
    match = re.match(r"\s*([A-Za-z]+)", without_comments)
    return match.group(1).upper() if match else ""


def _validate_migrations(migrations):
    if not isinstance(migrations, list) or not 1 <= len(migrations) <= MAX_MIGRATIONS:
        raise ValueError("migrations must be a bounded nonempty list")
    total = 0
    for migration in migrations:
        if not isinstance(migration, dict) or set(migration) != {"version", "sql", "sha256"}:
            raise ValueError("each migration must contain exactly version, sql, and sha256")
        version = migration["version"]
        sql = migration["sql"]
        digest = migration["sha256"]
        if isinstance(version, bool) or not isinstance(version, int) or version <= 0:
            raise ValueError("migration version must be a positive integer")
        if not isinstance(sql, str) or not sql:
            raise ValueError("migration SQL must be a nonempty string")
        sql_bytes = len(sql.encode("utf-8"))
        total += sql_bytes
        if sql_bytes > MAX_SQL_BYTES or total > MAX_TOTAL_SQL_BYTES:
            raise ValueError("migration SQL byte limit exceeded")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("sha256 must be a lowercase hexadecimal digest")


def _trusted_map(trusted_digests, versions):
    if trusted_digests is None:
        return None
    if not isinstance(trusted_digests, dict) or set(trusted_digests) != {str(version) for version in versions}:
        raise ValueError("trusted_digests must cover every migration version exactly")
    if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in trusted_digests.values()):
        raise ValueError("trusted digests must be lowercase hexadecimal SHA-256 values")
    return trusted_digests


def _authorizer(action, arg1, arg2, _database, _trigger):
    denied_actions = {
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_DETACH,
        sqlite3.SQLITE_PRAGMA,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_SAVEPOINT,
    }
    if action in denied_actions:
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION and (arg1 or arg2 or "").casefold() == "load_extension":
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def verify(migrations, *, trusted_digests=None):
    _validate_migrations(migrations)
    versions = [migration["version"] for migration in migrations]
    if versions != list(range(1, len(versions) + 1)):
        return {"status": "blocked", "reason": "non_contiguous"}
    trusted = _trusted_map(trusted_digests, versions)
    batches = []
    for migration in migrations:
        calculated = hashlib.sha256(migration["sql"].encode("utf-8")).hexdigest()
        if migration["sha256"] != calculated:
            return {"status": "blocked", "reason": "checksum"}
        if trusted is not None and trusted[str(migration["version"])] != calculated:
            return {"status": "blocked", "reason": "trusted_checksum"}
        statements = _statements(migration["sql"])
        if any(_leader(statement) in _FORBIDDEN_LEADERS for statement in statements):
            return {"status": "blocked", "reason": "forbidden_sql", "rolled_back": True}
        batches.append(statements)

    connection = sqlite3.connect(":memory:", isolation_level=None)
    rolled_back = False
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.set_authorizer(_authorizer)
        for statements in batches:
            for statement in statements:
                connection.execute(statement)
        tables = sorted(row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'"))
        connection.set_authorizer(None)
        connection.rollback()
        rolled_back = True
        status = "verified" if trusted is not None else "self_consistent"
        provenance = "trusted" if trusted is not None else "untrusted"
        return {"status": status, "digest_provenance": provenance, "versions": versions, "tables": tables, "rolled_back": True}
    except sqlite3.Error as error:
        connection.set_authorizer(None)
        if connection.in_transaction:
            connection.rollback()
        rolled_back = True
        reason = "forbidden_sql" if "not authorized" in str(error).casefold() else "sql_error"
        return {"status": "blocked", "reason": reason, "error": type(error).__name__, "rolled_back": True}
    finally:
        if not rolled_back and connection.in_transaction:
            connection.set_authorizer(None)
            connection.rollback()
        connection.close()


def run(data):
    if not isinstance(data, dict) or "migrations" not in data or set(data) - {"migrations", "trusted_digests"}:
        raise ValueError("input must contain migrations and optional trusted_digests")
    return verify(**data)
