from langchain.schema import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import os, json

def _make_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",  
        api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )

llm_bill = _make_llm()

def summarize_stock_data(ticker, prices, metrics, items, trades, news, facts) -> str:

    latest_metrics = metrics[0] if metrics else {}
    
    prompt = (
        f"Summarize the following financial info for {ticker} in 6–8 short bullets. "
        f"Only include facts that affect an invest / don't invest decision.\n\n"
        f"- Recent Prices (last 10 days):\n{json.dumps(prices[:10])}\n"
        f"- Financial Metrics (latest period):\n{json.dumps(latest_metrics)}\n"
        f"- Line Items (sample):\n{json.dumps(items[:5])}\n"
        f"- Insider Trades (recent):\n{json.dumps(trades[:5])}\n"
        f"- Recent News (headlines):\n{json.dumps([n.get('title') for n in news[:5]])}\n"
        f"- Company Facts:\n{json.dumps(facts)}\n"
    )
    return llm_bill.invoke([HumanMessage(content=prompt)]).content

def bill_agent_with_data(ticker: str, data: dict) -> str:
    """
    Bill Ackman agent that uses pre-fetched data.
    This is called by LangGraph with shared data.
    """
    prices = data.get("prices", [])
    metrics = data.get("metrics", [])
    items = data.get("items", [])
    trades = data.get("trades", [])
    news = data.get("news", [])
    facts = data.get("facts", {})
    
    data_summary = summarize_stock_data(ticker, prices, metrics, items, trades, news, facts)
    
    prompt = """Answer as if you are Bill Ackman, my financial advisor.
    Break down where this company might run into real problems. I don't want just generic risk 
    factors that every stock has, but specific ones for this business—like regulations, 
    supply chain issues, leadership decisions, or overdependence on one product.
    Explain how those risks could actually affect earnings or growth, and whether management 
    looks like they have a plan for it or not. Basically, what could go wrong here that people 
    aren't paying enough attention to?"""
    
    system = SystemMessage(content=prompt)
    user = HumanMessage(content=f"Summary for {ticker}:\n{data_summary}\n\nShould I invest in {ticker}? Answer concisely.")
    
    return llm_bill.invoke([system, user]).content


def bill_agent(ticker: str) -> str:

    from data_api import (
        get_stock_prices,
        get_financial_metrics,
        get_line_items,
        get_insider_trades,
        get_news,
        get_company_facts,
    )
    
    prices = get_stock_prices(ticker, "day", 1, "2025-01-01", "2025-10-04")
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
        "facts": facts.model_dump() if facts else {}
    }
    
    return bill_agent_with_data(ticker, data)