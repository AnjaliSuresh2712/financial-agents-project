from __future__ import annotations

from typing import Any, Dict, List, Literal
import json

from pydantic import BaseModel, Field, ValidationError


class Claim(BaseModel):
    statement: str
    stance: Literal["bullish", "bearish", "neutral"] = "neutral"
    evidence_keys: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class StructuredAnalysis(BaseModel):
    agent: str
    ticker: str
    thesis: str
    recommendation: Literal["buy", "hold", "avoid"] = "hold"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    claims: List[Claim] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)


def structured_output_instructions(
    allowed_evidence_keys: List[str],
    min_claims: int = 3,
    max_claims: int = 5,
    focus_hint: str = "",
) -> str:
    keys = ", ".join(allowed_evidence_keys)
    focus_block = f"\nFocus guidance: {focus_hint}\n" if focus_hint else "\n"
    return (
        "Return ONLY valid JSON with this schema:\n"
        "{\n"
        '  "agent": "string",\n'
        '  "ticker": "string",\n'
        '  "thesis": "string",\n'
        '  "recommendation": "buy|hold|avoid",\n'
        '  "confidence": 0.0-1.0,\n'
        '  "claims": [\n'
        "    {\n"
        '      "statement": "string",\n'
        '      "stance": "bullish|bearish|neutral",\n'
        '      "evidence_keys": ["array of strings"],\n'
        '      "confidence": 0.0-1.0\n'
        "    }\n"
        "  ],\n"
        '  "caveats": ["array of strings"]\n'
        "}\n"
        f"Provide {min_claims}-{max_claims} claims.\n"
        "Each claim should include at least one evidence key.\n"
        f"Use only these evidence_keys when possible: [{keys}].\n"
        + focus_block +
        "Do not include markdown, code fences, or extra text."
    )


def build_fallback_analysis(
    agent: str,
    ticker: str,
    message: str,
    recommendation: Literal["buy", "hold", "avoid"] = "hold",
) -> StructuredAnalysis:
    return StructuredAnalysis(
        agent=agent,
        ticker=ticker,
        thesis="Insufficient evidence for a high-confidence recommendation.",
        recommendation=recommendation,
        confidence=0.15,
        claims=[],
        caveats=[message],
    )


def _extract_json_block(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return "{}"

    if raw.startswith("```"):
        lines = raw.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        return raw[start : end + 1]
    return raw


def parse_structured_analysis(
    raw: str,
    agent: str,
    ticker: str,
    allowed_evidence_keys: List[str] | None = None,
    min_claims: int = 0,
) -> StructuredAnalysis:
    payload = _extract_json_block(raw)
    try:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise TypeError("Structured output must be a JSON object.")

        data["agent"] = str(data.get("agent") or agent)
        data["ticker"] = str(data.get("ticker") or ticker)
        if "recommendation" in data and isinstance(data["recommendation"], str):
            data["recommendation"] = data["recommendation"].strip().lower()
        if "confidence" in data and isinstance(data["confidence"], (int, float)):
            conf = float(data["confidence"])
            data["confidence"] = conf / 100.0 if conf > 1.0 else conf

        claims = data.get("claims")
        if isinstance(claims, list):
            for claim in claims:
                if not isinstance(claim, dict):
                    continue
                if "stance" in claim and isinstance(claim["stance"], str):
                    claim["stance"] = claim["stance"].strip().lower()
                if "confidence" in claim and isinstance(claim["confidence"], (int, float)):
                    c_conf = float(claim["confidence"])
                    claim["confidence"] = c_conf / 100.0 if c_conf > 1.0 else c_conf

        parsed = StructuredAnalysis(**data)

        if allowed_evidence_keys:
            allowed_set = set(allowed_evidence_keys)
            removed_keys = 0
            empty_evidence_claims = 0
            for claim in parsed.claims:
                before = list(claim.evidence_keys)
                claim.evidence_keys = [k for k in claim.evidence_keys if k in allowed_set]
                removed_keys += max(0, len(before) - len(claim.evidence_keys))
                if not claim.evidence_keys:
                    empty_evidence_claims += 1

            if removed_keys > 0:
                parsed.caveats.append(
                    f"{removed_keys} evidence keys were removed for being outside the allowed set."
                )
            if empty_evidence_claims > 0:
                parsed.caveats.append(
                    f"{empty_evidence_claims} claims have no allowed evidence keys."
                )

        if min_claims and len(parsed.claims) < min_claims:
            parsed.caveats.append(
                f"Expected at least {min_claims} claims, but got {len(parsed.claims)}."
            )

        return parsed
    except (json.JSONDecodeError, ValidationError, TypeError):
        return build_fallback_analysis(
            agent=agent,
            ticker=ticker,
            message=f"Could not parse structured output. Raw snippet: {(raw or '')[:300]}",
        )


def structured_to_json_text(analysis: StructuredAnalysis) -> str:
    return analysis.model_dump_json(indent=2)


def summary_payload(analysis: StructuredAnalysis) -> Dict[str, Any]:
    return analysis.model_dump()
