from __future__ import annotations

import copy

from ai_assistance_manifest.io import bundled_template


def valid_manifest() -> dict:
    return copy.deepcopy(bundled_template())

