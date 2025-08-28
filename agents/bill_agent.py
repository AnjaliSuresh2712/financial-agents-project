from langchain.schema import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import os, json

# data helpers
from data_api import (
    get_stock_prices,
    get_financial_metrics,
    get_line_items,
    get_insider_trades,
    get_news,
    get_company_facts,
)

def _make_llm():
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    )

llm_bill = _make_llm()

def summarize_stock_data(ticker, prices, metrics, items, trades, news, facts) -> str:
    prompt = (
        f"Summarize the following financial info for {ticker} in 6–8 short bullets. "
        f"Only include facts that affect an invest / don't invest decision.\n\n"
        f"- Recent Prices (trend/range):\n{json.dumps(prices)[:900]}\n"
        f"- Financial Metrics:\n{json.dumps(metrics)[:900]}\n"
        f"- Line Items:\n{json.dumps(items)[:900]}\n"
        f"- Insider Trades:\n{json.dumps(trades)[:900]}\n"
        f"- Recent News:\n{json.dumps(news)[:900]}\n"
        f"- Company Facts:\n{json.dumps(facts)[:900]}\n"
    )
    return llm_bill.invoke([HumanMessage(content=prompt)]).content

def bill_agent(ticker: str) -> str:
    prices  = get_stock_prices(ticker, "day", 1, "2025-01-01", "2025-08-01")
    metrics = get_financial_metrics(ticker, "ttm")
    items   = get_line_items(ticker)
    trades  = get_insider_trades(ticker)
    news    = get_news(ticker)
    facts   = get_company_facts(ticker)

    data_summary = summarize_stock_data(ticker, prices, metrics, items, trades, news, facts)
    prompt = """Answer as if you are a Bill Ackman, my financial advisor.
    Break down where this company might run into real problems. I don’t want just generic risk 
    factors that every stock has, but specific ones for this business — like regulations, 
    supply chain issues, leadership decisions, or overdependence on one product.
    Explain how those risks could actually affect earnings or growth, and whether management looks like they have a plan for it or not. Basically, what could go wrong here that people aren’t paying enough attention to?"""
    system = SystemMessage(content=prompt)
    system = SystemMessage(content="Answer as if you are a Bill Ackman, my financial advisor.")
    user   = HumanMessage(content=f"Summary for {ticker}:\n{data_summary}\n\nShould I invest in {ticker}? Answer concisely.")
    return llm_bill.invoke([system, user]).content


