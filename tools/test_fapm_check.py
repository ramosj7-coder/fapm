"""Regression test: the worked example must yield exactly the documented findings."""
from pathlib import Path

from fapm_check import check, load

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "ambient-documentation" / "pipeline.yaml"

EXPECTED = {
    ("G1", "N3", "model_version_ID"),
    ("G1", "N4", "edit_interface_active"),
    ("G5", "N4/C", "rejection_reason"),
    ("G1", "N5", "final_note_content"),
    ("G1", "N5", "ehr_write_access"),
    ("G4", "N5", "rejection_reason"),
    ("G4", "N5", "ehr_context_accessed_flag"),
}


def test_ambient_documentation_findings():
    found = {(f.code, f.node, f.feature) for f in check(load(str(EXAMPLE)))}
    assert found == EXPECTED


def test_declaring_a_producer_closes_the_gap():
    model = load(str(EXAMPLE))
    n1 = next(n for n in model["nodes"] if n["id"] == "N1")
    n1["produced"].append("model_version_ID")
    found = {(f.code, f.node, f.feature) for f in check(model)}
    assert ("G1", "N3", "model_version_ID") not in found
