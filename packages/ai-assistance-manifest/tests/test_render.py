from __future__ import annotations

import unittest

from ai_assistance_manifest.render import render_manifest

from helpers import valid_manifest


class RenderTests(unittest.TestCase):
    def test_render_is_deterministic(self) -> None:
        manifest = valid_manifest()
        self.assertEqual(render_manifest(manifest), render_manifest(manifest))

    def test_render_contains_truth_status_and_limitations(self) -> None:
        output = render_manifest(valid_manifest())
        self.assertIn("# AI Assistance Manifest", output)
        self.assertIn("`verified`", output)
        self.assertIn("## Limitations", output)
        self.assertIn("Edit the manifest, not this file", output)

    def test_table_cells_escape_pipes(self) -> None:
        manifest = valid_manifest()
        manifest["models"][0]["provider"] = "A | B"
        self.assertIn("A \\| B", render_manifest(manifest))


if __name__ == "__main__":
    unittest.main()

