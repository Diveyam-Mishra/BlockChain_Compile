import os
import asyncio
import json
import pytest

from compliledger.backend.app.services.ai_service import AIService, AnalysisLevel


@pytest.fixture
def ai_service_disabled(monkeypatch):
    # Ensure the service runs in disabled (mock) mode
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    svc = AIService()
    assert svc.enabled is False
    return svc


def test_process_analysis_results_normalizes_values():
    svc = AIService()
    raw = {
        "risk_assessment": [{"risk": "x", "severity": "low"}],
        "compliance_status": {
            "PO.1.1": True,
            "PO.1.2": False,
            "PO.1.3": "Passed",
            "PO.1.4": "failed",
            "PO.1.5": "YES",
            "PO.1.6": "no",
            "PO.1.7": 1,  # non-bool, non-str -> treated as fail
        },
        "recommendations": ["do y"],
        "overall_score": "85",
        "findings": [{"control_id": "PO.1.1", "severity": "low"}],
    }

    out = svc._process_analysis_results(raw)

    # pass/fail normalization
    assert out["compliance_status"]["PO.1.1"] == "pass"
    assert out["compliance_status"]["PO.1.2"] == "fail"
    assert out["compliance_status"]["PO.1.3"] == "pass"
    assert out["compliance_status"]["PO.1.4"] == "fail"
    assert out["compliance_status"]["PO.1.5"] == "pass"
    assert out["compliance_status"]["PO.1.6"] == "fail"
    assert out["compliance_status"]["PO.1.7"] == "fail"

    # derived metrics and score coercion
    assert out["controls_total"] == len(out["compliance_status"])
    assert out["controls_passed"] == 3  # True, Passed, YES
    assert out["controls_failed"] == out["controls_total"] - out["controls_passed"]
    assert out["overall_score"] == 85


def test_process_analysis_results_handles_non_dict_and_bad_types():
    svc = AIService()
    raw = {
        "compliance_status": ["not", "a", "dict"],
        "risk_assessment": "not-a-list",
        "recommendations": None,
        "findings": "oops",
        "overall_score": "not-a-number",
    }

    out = svc._process_analysis_results(raw)

    assert isinstance(out["compliance_status"], dict)
    assert out["controls_total"] == 0
    assert out["controls_passed"] == 0
    assert out["controls_failed"] == 0

    assert isinstance(out["risk_assessment"], list)
    assert isinstance(out["recommendations"], list)
    assert isinstance(out["findings"], list)

    assert out["overall_score"] == 0


@pytest.mark.asyncio
async def test_analyze_artifact_returns_mock_when_disabled(ai_service_disabled):
    svc = ai_service_disabled
    res = await svc.analyze_artifact(
        artifact_path="/tmp/fake.bin",
        metadata={"name": "fake", "type": "bin"},
        level=AnalysisLevel.STANDARD,
    )

    # Expect mock structure without throwing
    assert set(["risk_assessment", "compliance_status", "recommendations", "overall_score", "findings"]) <= set(res.keys())
    assert isinstance(res["overall_score"], int)
    assert 0 <= res["overall_score"] <= 100
