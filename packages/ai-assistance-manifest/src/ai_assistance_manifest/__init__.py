"""AI Assistance Manifest public API."""

from .render import render_manifest
from .validation import validate_manifest

__all__ = ["render_manifest", "validate_manifest"]
__version__ = "0.2.0"
