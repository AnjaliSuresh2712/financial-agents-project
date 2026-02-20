from __future__ import annotations

from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone

from agents.reliability import StructuredAnalysis


# Keep this list small and deterministic so we can verify claims in code.
ALLOWED_EVIDENCE_KEYS = [
    "price_trend_30d",
    "price_trend_10d",
    "revenue_growth",
    "earnings_growth",
    "operating_margin",
    "net_margin",
    "debt_to_equity",
    "return_on_equity",
    "insider_net_buy",
    "news_count_30d",
]

AGENT_ALLOWED_EVIDENCE_KEYS = {
    "warren": [
        "revenue_growth",
        "earnings_growth",
        "operating_margin",
        "net_margin",
        "debt_to_equity",
        "return_on_equity",
        "insider_net_buy",
        "price_trend_30d",
    ],
    "bill": [
        "debt_to_equity",
        "earnings_growth",
        "net_margin",
        "news_count_30d",
        "insider_net_buy",
        "revenue_growth",
        "operating_margin",
    ],
    "robin": [
        "price_trend_10d",
        "price_trend_30d",
        "news_count_30d",
        "insider_net_buy",
        "net_margin",
    ],
}

AGENT_CLAIM_GUIDANCE = {
    "warren": (
        "Focus on long-term fundamentals. Prioritize profitability, growth quality, "
        "capital efficiency, and leverage discipline."
    ),
    "bill": (
        "Focus on downside risk and catalyst risk. Prioritize leverage stress, "
        "earnings durability, and risk signals from news flow."
    ),
    "robin": (
        "Focus on short-term momentum. Prioritize recent price trend, recent news volume, "
        "and near-term signal strength."
    ),
}


def allowed_evidence_keys_for_agent(agent_key: str) -> List[str]:
    return AGENT_ALLOWED_EVIDENCE_KEYS.get(agent_key, ALLOWED_EVIDENCE_KEYS)


def _parse_iso_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _trend_percent(prices: List[Dict[str, Any]], window: int) -> float | None:
    if len(prices) < 2:
        return None
    sample = prices[-window:] if len(prices) >= window else prices
    first = sample[0].get("close")
    last = sample[-1].get("close")
    if not isinstance(first, (int, float)) or not isinstance(last, (int, float)):
        return None
    if first == 0:
        return None
    return ((last - first) / first) * 100.0


def _insider_net_buy(trades: List[Dict[str, Any]]) -> float | None:
    if not trades:
        return None
    score = 0.0
    seen = False
    for trade in trades[:100]:
        shares = trade.get("shares")
        if not isinstance(shares, (int, float)):
            continue
        tx = (trade.get("transaction_type") or "").lower()
        if "buy" in tx or "acquire" in tx:
            score += float(shares)
            seen = True
        elif "sell" in tx or "dispose" in tx:
            score -= float(shares)
            seen = True
    return score if seen else None


def _recent_news_count(news: List[Dict[str, Any]], days: int = 30) -> int:
    if not news:
        return 0
    now = datetime.now(timezone.utc)
    count = 0
    for article in news:
        published = _parse_iso_datetime(article.get("published_at") or "")
        if published is None:
            continue
        if (now - published).days <= days:
            count += 1
    return count


def compute_feature_signals(data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    prices = data.get("prices", [])
    metrics = data.get("metrics", [])
    trades = data.get("trades", [])
    news = data.get("news", [])
    latest = metrics[0] if metrics else {}

    signals: Dict[str, Dict[str, Any]] = {}

    trend_30 = _trend_percent(prices, 30)
    trend_10 = _trend_percent(prices, 10)
    insider = _insider_net_buy(trades)
    news_30 = _recent_news_count(news, 30)

    metric_fields: List[Tuple[str, bool]] = [
        ("revenue_growth", True),
        ("earnings_growth", True),
        ("operating_margin", True),
        ("net_margin", True),
        ("debt_to_equity", False),  # Lower leverage is usually better.
        ("return_on_equity", True),
    ]

    def to_signal(value: float | int | None, positive_good: bool = True) -> int:
        if value is None:
            return 0
        if value > 0:
            return 1 if positive_good else -1
        if value < 0:
            return -1 if positive_good else 1
        return 0

    signals["price_trend_30d"] = {"value": trend_30, "signal": to_signal(trend_30, True)}
    signals["price_trend_10d"] = {"value": trend_10, "signal": to_signal(trend_10, True)}
    signals["insider_net_buy"] = {"value": insider, "signal": to_signal(insider, True)}
    signals["news_count_30d"] = {"value": news_30, "signal": 1 if news_30 > 0 else 0}

    for key, positive_good in metric_fields:
        raw = latest.get(key)
        value = float(raw) if isinstance(raw, (int, float)) else None
        signals[key] = {"value": value, "signal": to_signal(value, positive_good)}

    return signals


def _expected_signal_for_stance(stance: str) -> int:
    if stance == "bullish":
        return 1
    if stance == "bearish":
        return -1
    return 0


def verify_analysis_claims(
    analysis: StructuredAnalysis, feature_signals: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    verified = 0

    for claim in analysis.claims:
        valid_keys = [k for k in claim.evidence_keys if k in feature_signals]
        invalid_keys = [k for k in claim.evidence_keys if k not in feature_signals]
        expected = _expected_signal_for_stance(claim.stance)

        matched = False
        used = []
        for key in valid_keys:
            signal = feature_signals[key]["signal"]
            if expected == 0:
                matched = True
                used.append({"key": key, "signal": signal, "value": feature_signals[key]["value"]})
                continue
            if signal == expected:
                matched = True
                used.append({"key": key, "signal": signal, "value": feature_signals[key]["value"]})

        is_verified = bool(valid_keys) and matched
        if is_verified:
            verified += 1

        checks.append(
            {
                "statement": claim.statement,
                "stance": claim.stance,
                "evidence_keys": claim.evidence_keys,
                "valid_evidence_keys": valid_keys,
                "invalid_evidence_keys": invalid_keys,
                "matched_evidence": used,
                "verified": is_verified,
            }
        )

    total = len(analysis.claims)
    rate = (verified / total) if total else 0.0
    return {
        "agent": analysis.agent,
        "claim_count": total,
        "verified_claim_count": verified,
        "verification_rate": round(rate, 4),
        "checks": checks,
    }
