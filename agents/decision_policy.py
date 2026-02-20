from __future__ import annotations

from typing import Any, Dict


ADVISOR_WEIGHTS = {
    "warren": 0.4,
    "bill": 0.35,
    "robin": 0.25,
}

RECOMMENDATION_SCORE = {
    "buy": 1.0,
    "hold": 0.0,
    "avoid": -1.0,
}


def _coverage_factor(data_coverage: Dict[str, Any]) -> float:
    prices = data_coverage.get("prices", {}).get("count", 0)
    metrics = data_coverage.get("metrics", {}).get("count", 0)
    news = data_coverage.get("news", {}).get("count", 0)
    line_items = data_coverage.get("line_items", {}).get("count", 0)

    score = 0.0
    score += 0.35 if prices >= 20 else (0.2 if prices >= 5 else 0.0)
    score += 0.25 if metrics >= 1 else 0.0
    score += 0.2 if news >= 3 else (0.1 if news >= 1 else 0.0)
    score += 0.2 if line_items >= 1 else 0.0
    return min(1.0, score)


def compute_final_policy(
    analyses: Dict[str, Dict[str, Any]],
    verification: Dict[str, Dict[str, Any]],
    data_coverage: Dict[str, Any],
    data_warnings: list[str],
) -> Dict[str, Any]:
    coverage_factor = _coverage_factor(data_coverage)
    warning_penalty = min(0.5, 0.08 * len(data_warnings))
    advisor_breakdown: Dict[str, Any] = {}
    weighted_sum = 0.0
    total_weight = 0.0

    for advisor, weight in ADVISOR_WEIGHTS.items():
        analysis = analyses.get(advisor) or {}
        verify = verification.get(advisor) or {}
        rec = (analysis.get("recommendation") or "hold").lower()
        rec_score = RECOMMENDATION_SCORE.get(rec, 0.0)
        model_conf = float(analysis.get("confidence") or 0.0)
        verification_rate = float(verify.get("verification_rate") or 0.0)

        reliability = max(0.0, min(1.0, 0.15 + 0.45 * model_conf + 0.4 * verification_rate))
        effective_weight = weight * reliability

        advisor_breakdown[advisor] = {
            "recommendation": rec,
            "recommendation_score": rec_score,
            "model_confidence": round(model_conf, 4),
            "verification_rate": round(verification_rate, 4),
            "base_weight": weight,
            "effective_weight": round(effective_weight, 4),
        }

        weighted_sum += rec_score * effective_weight
        total_weight += effective_weight

    consensus_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0
    adjusted_score = consensus_score * coverage_factor * (1.0 - warning_penalty)

    average_verification = 0.0
    if verification:
        average_verification = sum(
            float(v.get("verification_rate") or 0.0) for v in verification.values()
        ) / len(verification)

    abstain_reasons: list[str] = []
    if coverage_factor < 0.45:
        abstain_reasons.append("Data coverage is too low for a reliable decision.")
    if average_verification < 0.4:
        abstain_reasons.append("Too few claims are verified against deterministic checks.")
    if len(data_warnings) >= 5:
        abstain_reasons.append("Data warnings are high; recommendation confidence is degraded.")

    if abstain_reasons:
        final_recommendation = "abstain"
    elif adjusted_score >= 0.25:
        final_recommendation = "buy"
    elif adjusted_score <= -0.25:
        final_recommendation = "avoid"
    else:
        final_recommendation = "hold"

    confidence = max(
        0.0,
        min(1.0, 0.2 + 0.45 * coverage_factor + 0.35 * average_verification - warning_penalty),
    )

    rationale = [
        f"Coverage factor: {coverage_factor:.2f}",
        f"Average claim verification: {average_verification:.2f}",
        f"Consensus score: {consensus_score:.2f}",
        f"Adjusted policy score: {adjusted_score:.2f}",
    ]

    return {
        "final_recommendation": final_recommendation,
        "confidence": round(confidence, 4),
        "consensus_score": round(consensus_score, 4),
        "adjusted_policy_score": round(adjusted_score, 4),
        "coverage_factor": round(coverage_factor, 4),
        "warning_count": len(data_warnings),
        "advisor_breakdown": advisor_breakdown,
        "abstain_reasons": abstain_reasons,
        "rationale": rationale,
    }

