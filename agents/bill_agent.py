from __future__ import annotations

from agents.base import AdvisorAgent
from agents.data_quality import summarize_data_coverage, collect_data_warnings


class BillAgent(AdvisorAgent):
    key = "bill"
    title = "BILL ACKMAN"
    result_key = "bill_result"
    output_key = "bill_ackman"
    system_prompt = """Answer as if you are Bill Ackman, my financial advisor.
Break down where this company might run into real problems. I don't want just generic risk 
factors that every stock has, but specific ones for this business, like regulations, 
supply chain issues, leadership decisions, or overdependence on one product.
Explain how those risks could actually affect earnings or growth, and whether management 
looks like they have a plan for it or not. Basically, what could go wrong here that people 
aren't paying enough attention to? If data coverage is limited or warnings are present, 
explicitly say so and avoid a definitive recommendation. End with:
Confidence: Low/Medium/High
Key assumptions: 1-3 short bullets."""

    def allowed_evidence_keys(self) -> list[str]:
        return [
            "debt_to_equity",
            "earnings_growth",
            "net_margin",
            "news_count_30d",
            "insider_net_buy",
            "revenue_growth",
            "operating_margin",
        ]

    def min_claim_count(self) -> int:
        return 3

    def _insufficient_data_message(self, data: dict) -> str | None:
        if data.get("metrics") or data.get("news"):
            return None
        data_warnings = data.get("data_warnings", [])
        warning_text = "\n".join(
            f"- {w}" for w in (data_warnings or ["Missing metrics and news."])
        )
        return (
            "Insufficient data to assess risks and catalysts.\n"
            f"Data warnings:\n{warning_text}"
        )


BILL_AGENT = BillAgent()


def bill_agent_with_data(ticker: str, data: dict) -> str:
    """Bill Ackman agent that uses pre-fetched data."""
    return BILL_AGENT.analyze_with_data(ticker, data)


def bill_agent(ticker: str) -> str:
    from data_api import (
        get_stock_prices,
        get_financial_metrics,
        get_line_items,
        get_insider_trades,
        get_news,
        get_company_facts,
        default_date_range,
    )

    start_date, end_date = default_date_range(365)
    prices = get_stock_prices(ticker, "day", 1, start_date, end_date)
    metrics = get_financial_metrics(ticker, "ttm")
    items = get_line_items(ticker)
    trades = get_insider_trades(ticker)
    news = get_news(ticker)
    facts = get_company_facts(ticker)

    data = {
        "prices": [p.model_dump() for p in prices],
        "metrics": [m.model_dump() for m in metrics],
        "items": [i.model_dump() for i in items],
        "trades": [t.model_dump() for t in trades],
        "news": [n.model_dump() for n in news],
        "facts": facts.model_dump() if facts else {},
    }
    data["data_coverage"] = summarize_data_coverage(data)
    data["data_warnings"] = collect_data_warnings(data)

    return bill_agent_with_data(ticker, data)
