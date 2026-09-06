"""Evidence-first local AI development diagnostics."""

from .api import diagnose
from .models import DiagnosticReport, EvidenceClass, ToolDiagnostic, ToolStatus

__all__ = [
    "DiagnosticReport",
    "EvidenceClass",
    "ToolDiagnostic",
    "ToolStatus",
    "diagnose",
]

__version__ = "0.1.0"

