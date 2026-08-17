from __future__ import annotations

from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from repo_doctor_ai.io_utils import BoundedReadError, ConfinedReader, read_bounded_bytes


class ConfinedReaderPortableTests(unittest.TestCase):
    def test_standalone_reader_rejects_a_file_link_without_os_no_follow(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            target = Path(outside) / "outside.txt"
            target.write_bytes(b"outside")
            link = root / "linked.txt"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("file symlink creation unavailable")
            with patch.object(os, "O_NOFOLLOW", 0, create=True):
                with self.assertRaises(BoundedReadError):
                    read_bounded_bytes(link, 1024, label="fixture")

    def test_portable_backend_reads_a_regular_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sub").mkdir()
            (root / "sub" / "file.txt").write_bytes(b"bounded")
            with patch(
                "repo_doctor_ai.io_utils._supports_descriptor_relative_reads",
                return_value=False,
            ):
                with ConfinedReader(root) as reader:
                    content, size = reader.read_bounded_bytes(
                        "sub/file.txt", 1024, label="fixture"
                    )
        self.assertEqual((content, size), (b"bounded", 7))

    def test_portable_backend_rejects_an_ancestor_link_swap(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            inside = root / "sub"
            inside.mkdir()
            (inside / "file.txt").write_bytes(b"inside")
            external = Path(outside)
            (external / "file.txt").write_bytes(b"outside")
            try:
                with patch(
                    "repo_doctor_ai.io_utils._supports_descriptor_relative_reads",
                    return_value=False,
                ):
                    with ConfinedReader(root) as reader:
                        inside.rename(root / "sub-original")
                        (root / "sub").symlink_to(external, target_is_directory=True)
                        with self.assertRaises(BoundedReadError):
                            reader.read_bounded_bytes("sub/file.txt", 1024, label="fixture")
            except OSError:
                self.skipTest("directory symlink creation unavailable")


if __name__ == "__main__":
    unittest.main()
