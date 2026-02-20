from __future__ import annotations

from agents.base import AdvisorAgent
from agents.data_quality import summarize_data_coverage, collect_data_warnings


class RobinAgent(AdvisorAgent):
    key = "robin"
    title = "ROBINHOOD COACH"
    result_key = "robin_result"
    output_key = "robinhood_coach"
    system_prompt = """Answer like a Robinhood-style investing coach, my financial advisor. 
Talk about this stock in terms of what's happening right now and in the near future. 
Are people actually buying into it? Look at trends in price movement, trading volume, 
or even news cycles. Don't just say "the stock is up or down," explain whether it looks 
like it has short-term momentum or if it's just noise. Also, mention what events (earnings
reports, product launches, lawsuits, etc.) could shake things up in the next few weeks or 
months. If data coverage is limited or warnings are present, explicitly say so and avoid 
a definitive recommendation. End with:
Confidence: Low/Medium/High
Key assumptions: 1-3 short bullets."""

    def allowed_evidence_keys(self) -> list[str]:
        return [
            "price_trend_10d",
            "price_trend_30d",
            "news_count_30d",
            "insider_net_buy",
            "net_margin",
        ]

    def min_claim_count(self) -> int:
        return 3

    def _insufficient_data_message(self, data: dict) -> str | None:
        if data.get("prices"):
            return None
        data_warnings = data.get("data_warnings", [])
        warning_text = "\n".join(
            f"- {w}" for w in (data_warnings or ["Missing price data."])
        )
        return (
            "Insufficient price data to assess short-term momentum.\n"
            f"Data warnings:\n{warning_text}"
        )


ROBIN_AGENT = RobinAgent()


def robin_agent_with_data(ticker: str, data: dict) -> str:
    """Robinhood Coach agent that uses pre-fetched data."""
    return ROBIN_AGENT.analyze_with_data(ticker, data)


def robin_agent(ticker: str) -> str:
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

    return robin_agent_with_data(ticker, data)
