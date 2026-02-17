from __future__ import annotations

from agents.base import AdvisorAgent
from agents.data_quality import summarize_data_coverage, collect_data_warnings


class WarrenAgent(AdvisorAgent):
    key = "warren"
    title = "WARREN BUFFETT - VALUE ANALYSIS"
    result_key = "warren_result"
    output_key = "warren_buffett"
    system_prompt = """Answer like Warren Buffet, my financial advisor. 
Look at this company like you're thinking about holding it for years. Don't 
just say "the fundamentals are good or bad." Point out where they actually make money, 
what part of the business is strong or weak, and how that shows up in real numbers like 
revenue growth, profit margins, or debt. Also, talk about whether the stock price makes 
sense compared to what the company is really worth, instead of just repeating investor 
buzzwords. If data coverage is limited or warnings are present, explicitly say so and 
avoid a definitive recommendation. End with:
Confidence: Low/Medium/High
Key assumptions: 1-3 short bullets."""

    def _insufficient_data_message(self, data: dict) -> str | None:
        if data.get("metrics") or data.get("items"):
            return None
        data_warnings = data.get("data_warnings", [])
        warning_text = "\n".join(
            f"- {w}" for w in (data_warnings or ["Missing metrics and line items."])
        )
        return (
            "Insufficient fundamental data to provide a long-term assessment.\n"
            f"Data warnings:\n{warning_text}"
        )


WARREN_AGENT = WarrenAgent()


def warren_agent_with_data(ticker: str, data: dict) -> str:
    """Warren Buffett agent that uses pre-fetched data."""
    return WARREN_AGENT.analyze_with_data(ticker, data)


def warren_agent(ticker: str) -> str:
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

    return warren_agent_with_data(ticker, data)
