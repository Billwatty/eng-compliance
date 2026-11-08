"""Extraction with a fake client: shapes, refusal handling and the AI-to-rule path."""
from types import SimpleNamespace

import pytest

from app import extraction
from app.config import load_settings
from app.matcher import match_lab_report


class FakeMessages:
    def __init__(self, parsed, stop="end_turn"):
        self.parsed, self.stop, self.calls = parsed, stop, []

    def parse(self, **kw):
        self.calls.append(kw)
        return SimpleNamespace(stop_reason=self.stop, parsed_output=self.parsed,
                               stop_details=SimpleNamespace(category="cyber") if self.stop == "refusal" else None)


class FakeClient:
    def __init__(self, parsed, stop="end_turn"):
        self.messages = FakeMessages(parsed, stop)
        self.beta = SimpleNamespace(messages=self.messages)


def test_lab_report_request_shape():
    report = extraction.LabReportExtract(sample_tags=["BL-1204"], results=[
        extraction.TestValue(parameter="field_density_pct_mdd", value=96.8, unit="%", sample_tag="BL-1204")])
    client = FakeClient(report)
    out = extraction.extract_lab_report(load_settings(), b"%PDF-1.4", "r.pdf", "application/pdf", ["x"], client=client)
    assert out.results[0].value == 96.8
    kw = client.messages.calls[0]
    assert kw["model"] == "claude-opus-5-5" and kw["output_format"] is extraction.LabReportExtract
    assert kw["fallbacks"] == "default" and kw["betas"] == [extraction.FALLBACK_BETA]
    assert kw["messages"][0]["content"][0]["type"] == "document"


def test_refusal_becomes_manual_entry():
    with pytest.raises(extraction.ExtractionRefused):
        extraction.extract_certificate(load_settings(), b"\x89PNG", "c.png", "image/png",
                                       client=FakeClient(None, stop="refusal"))


def test_unsupported_file_type():
    with pytest.raises(extraction.ExtractionFailed):
        extraction._content_block(b"PK", "x.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


def test_rule_draft_params():
    d = extraction.RuleDraft(rule_code="R", boq_code="4.2", parameter="grading", unit="%", limit_type="envelope",
                             sieves=[extraction.SieveBand(sieve_mm="20", low=60, high=85)], source_ref="T 5.1")
    assert d.params() == {"sieves": {"20": [60, 85]}}


def test_matcher(conn, demo):
    assert match_lab_report(conn, demo, {"sample_tags": ["BL-1204"]})["confidence"] == 1.0
    m = match_lab_report(conn, demo, {"sample_tags": [], "chainage_from_m": 12100, "layer": "base"})
    assert m["lot_id"] == 2 and m["confidence"] == 0.7
    assert match_lab_report(conn, demo, {})["lot_id"] is None
