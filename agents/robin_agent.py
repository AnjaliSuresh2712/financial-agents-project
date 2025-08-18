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

# Set up the LLM from OpenRouter
# Uses gpt-3.5-turbo model via OpenRouter.
# Points to OpenRouter’s API endpoint, which proxies requests to the gpt model.
def _make_llm():
    return ChatOpenAI(
        model="gpt-3.5-turbo",
        api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
    )

llm_robin = _make_llm()

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
    return llm_robin.invoke([HumanMessage(content=prompt)]).content

# Will pull the data, summarize it, then asks a Robinhood coahc for a recommendation.
# (can change dates/interval later)
def robin_agent(ticker: str) -> str:
    prices  = get_stock_prices(ticker, "day", 1, "2025-01-01", "2025-08-01")
    metrics = get_financial_metrics(ticker, "ttm")
    items   = get_line_items(ticker)
    trades  = get_insider_trades(ticker)
    news    = get_news(ticker)
    facts   = get_company_facts(ticker)

    data_summary = summarize_stock_data(ticker, prices, metrics, items, trades, news, facts)

    system = SystemMessage(content="Answer as if you are a Robinhood-style investing coach, my financial advisor.")
    user   = HumanMessage(content=f"Summary for {ticker}:\n{data_summary}\n\nShould I invest in {ticker}? Answer concisely.")
    return llm_robin.invoke([system, user]).content
