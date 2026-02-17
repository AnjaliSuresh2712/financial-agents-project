from datetime import datetime, timezone
from math import isfinite
from typing import Any, Dict, List, Optional


def _parse_iso_date(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _date_range(values: List[Dict[str, Any]], key: str) -> Optional[Dict[str, str]]:
    raw = [v.get(key) for v in values if v.get(key)]
    if not raw:
        return None
    parsed = [_parse_iso_date(v) for v in raw]
    parsed = [p for p in parsed if p is not None]
    if parsed:
        return {"start": min(parsed).date().isoformat(), "end": max(parsed).date().isoformat()}
    raw_sorted = sorted(raw)
    return {"start": raw_sorted[0], "end": raw_sorted[-1]}


def build_data_snapshot(data: Dict[str, Any]) -> Dict[str, Any]:
    prices = data.get("prices", [])
    metrics = data.get("metrics", [])
    items = data.get("items", [])
    trades = data.get("trades", [])
    news = data.get("news", [])
    facts = data.get("facts", {})

    return {
        "prices": {
            "count": len(prices),
            "date_range": _date_range(prices, "time"),
            "sample": prices[:3],
        },
        "metrics": {
            "count": len(metrics),
            "latest": metrics[0] if metrics else {},
        },
        "line_items": {
            "count": len(items),
            "sample": items[:5],
        },
        "insider_trades": {
            "count": len(trades),
            "date_range": _date_range(trades, "date"),
            "sample": trades[:5],
        },
        "news": {
            "count": len(news),
            "date_range": _date_range(news, "published_at"),
            "headlines": [n.get("title") for n in news[:8]],
        },
        "facts": facts or {},
    }


def summarize_data_coverage(data: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = build_data_snapshot(data)
    return {
        "prices": {
            "count": snapshot["prices"]["count"],
            "date_range": snapshot["prices"]["date_range"],
        },
        "metrics": {"count": snapshot["metrics"]["count"]},
        "line_items": {"count": snapshot["line_items"]["count"]},
        "insider_trades": {
            "count": snapshot["insider_trades"]["count"],
            "date_range": snapshot["insider_trades"]["date_range"],
        },
        "news": {
            "count": snapshot["news"]["count"],
            "date_range": snapshot["news"]["date_range"],
        },
        "facts": {"present": bool(snapshot["facts"])},
    }


def _days_since(date_str: Optional[str], now: datetime) -> Optional[int]:
    if not date_str:
        return None
    parsed = _parse_iso_date(date_str)
    if not parsed:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    now_aware = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    return (now_aware - parsed).days


def _find_numeric_anomalies(data: Dict[str, Any]) -> List[str]:
    warnings: List[str] = []
    prices = data.get("prices", [])
    metrics = data.get("metrics", [])
    trades = data.get("trades", [])

    # Price sanity checks
    for idx, p in enumerate(prices[:50]):
        high = p.get("high")
        low = p.get("low")
        close = p.get("close")
        open_ = p.get("open")
        volume = p.get("volume")
        for label, value in [("open", open_), ("close", close), ("high", high), ("low", low)]:
            if isinstance(value, (int, float)) and not isfinite(value):
                warnings.append(f"Non-finite price {label} at index {idx}.")
        if isinstance(volume, (int, float)) and volume < 0:
            warnings.append(f"Negative volume at index {idx}.")
        if isinstance(high, (int, float)) and isinstance(low, (int, float)) and high < low:
            warnings.append(f"Price high < low at index {idx}.")
        if (
            isinstance(close, (int, float))
            and isinstance(high, (int, float))
            and isinstance(low, (int, float))
            and (close < low or close > high)
        ):
            warnings.append(f"Close outside high/low range at index {idx}.")

    # Metrics sanity checks
    latest_metrics = metrics[0] if metrics else {}
    for key, value in latest_metrics.items():
        if not isinstance(value, (int, float)):
            continue
        if not isfinite(value):
            warnings.append(f"Non-finite metric value for {key}.")

    # Insider trades sanity checks
    for idx, t in enumerate(trades[:50]):
        shares = t.get("shares")
        price = t.get("price")
        if isinstance(shares, (int, float)) and shares < 0:
            warnings.append(f"Negative insider shares at index {idx}.")
        if isinstance(price, (int, float)) and price < 0:
            warnings.append(f"Negative insider trade price at index {idx}.")

    return warnings


def collect_data_warnings(data: Dict[str, Any], now: Optional[datetime] = None) -> List[str]:
    warnings: List[str] = []
    now = now or datetime.now(timezone.utc)

    coverage = summarize_data_coverage(data)

    prices = coverage["prices"]
    news = coverage["news"]
    trades = coverage["insider_trades"]

    if prices["count"] == 0:
        warnings.append("No price data available.")
    elif prices["count"] < 3:
        warnings.append(f"Price series is sparse ({prices['count']} points).")
    else:
        days = _days_since(prices["date_range"]["end"] if prices["date_range"] else None, now)
        if days is not None and days > 7:
            warnings.append(f"Price data appears stale (latest {days} days old).")

    if coverage["metrics"]["count"] == 0:
        warnings.append("No financial metrics available.")

    if coverage["line_items"]["count"] == 0:
        warnings.append("No line items available; fundamentals detail is limited.")

    if trades["count"] == 0:
        warnings.append("No insider trades data available.")
    else:
        days = _days_since(trades["date_range"]["end"] if trades["date_range"] else None, now)
        if days is not None and days > 180:
            warnings.append(f"Insider trades data is old (latest {days} days old).")

    if news["count"] == 0:
        warnings.append("No news coverage available.")
    else:
        days = _days_since(news["date_range"]["end"] if news["date_range"] else None, now)
        if days is not None and days > 30:
            warnings.append(f"News coverage is old (latest {days} days old).")

    if not coverage["facts"]["present"]:
        warnings.append("No company facts available.")

    warnings.extend(_find_numeric_anomalies(data))

    return warnings
