import re
from typing import Any, Dict, List


class SmartContractAnalyzer:
    """
    Lightweight Solidity analyzer (no external deps) for MVP.
    Heuristic checks only. Can be upgraded to Slither/Mythril later.
    """

    def analyze_solidity(self, source: str) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []

        def add(id_: str, title: str, severity: str, desc: str, pattern: str):
            for m in re.finditer(pattern, source, flags=re.IGNORECASE | re.MULTILINE):
                findings.append({
                    "id": id_,
                    "title": title,
                    "severity": severity,
                    "description": desc,
                    "location": {
                        "start": m.start(),
                        "end": m.end(),
                    },
                    "control_tags": self._map_to_controls(id_),
                })

        # Heuristic rules
        add(
            "REENTRANCY_LOW_LEVEL_CALL",
            "Potential reentrancy via low-level call",
            "high",
            "Contract uses low-level call which may allow reentrancy without proper guards.",
            r"\.call\(|call\.(value|{)"
        )
        add(
            "TX_ORIGIN_AUTH",
            "Authentication via tx.origin",
            "high",
            "Use of tx.origin for authorization is insecure; use msg.sender.",
            r"tx\.origin"
        )
        add(
            "SELFDESTRUCT",
            "Contract can selfdestruct",
            "medium",
            "Contract can be destroyed; ensure only authorized paths can trigger this.",
            r"selfdestruct\(|suicide\("
        )
        add(
            "UNSAFE_SEND",
            "Unchecked Ether transfer (send/transfer)",
            "medium",
            "send/transfer can fail or break under EIP-1884; prefer call with checks.",
            r"\.send\(|\.transfer\("
        )
        add(
            "PUBLIC_STATE_MUTABILITY",
            "Missing explicit visibility or mutability",
            "low",
            "Functions missing explicit visibility/mutability can be risky.",
            r"function\s+\w+\s*\([^)]*\)\s*\{"
        )

        # Simple metrics
        sloc = len([ln for ln in source.splitlines() if ln.strip()])
        functions = len(re.findall(r"function\s+\w+\s*\(", source))

        # Scoring: basic heuristic
        sev_weight = {"high": 5, "medium": 3, "low": 1}
        score_penalty = sum(sev_weight.get(f.get("severity", "low"), 1) for f in findings)
        base = 100
        compliance_score = max(0, base - min(60, score_penalty * 4))

        controls_failed = len([f for f in findings if f["severity"] in ("high", "medium")])
        controls_passed = 10 + max(0, functions - controls_failed)  # rough placeholder

        return {
            "findings": findings,
            "metrics": {
                "sloc": sloc,
                "functions": functions,
            },
            "compliance_score": compliance_score,
            "controls_passed": controls_passed,
            "controls_failed": controls_failed,
            "findings_count": len(findings),
        }

    def _map_to_controls(self, rule_id: str) -> List[str]:
        # Minimal mapping to generic NIST-like tags
        mapping = {
            "REENTRANCY_LOW_LEVEL_CALL": ["AC-3", "SI-10"],
            "TX_ORIGIN_AUTH": ["IA-5", "AC-6"],
            "SELFDESTRUCT": ["CP-10", "CM-7"],
            "UNSAFE_SEND": ["SC-5", "SI-5"],
            "PUBLIC_STATE_MUTABILITY": ["CM-2"],
        }
        return mapping.get(rule_id, ["CUSTOM"])
