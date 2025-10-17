from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
import json

from agents.warren_agent import warren_agent_with_data
from agents.bill_agent import bill_agent_with_data
from agents.robin_agent import robin_agent_with_data
from data_api import (
    get_stock_prices,
    get_financial_metrics,
    get_line_items,
    get_insider_trades,
    get_news,
    get_company_facts,
)

# State for the agents 
class AgentState(TypedDict):
    ticker: str
    prices: List[Dict[str, Any]]
    metrics: List[Dict[str, Any]]
    items: List[Dict[str, Any]]
    trades: List[Dict[str, Any]]
    news: List[Dict[str, Any]]
    facts: Optional[Dict[str, Any]]
    warren_result: str
    bill_result: str
    robin_result: str
    timestamp: str

# NODE 1: Fetch all financial data for the ticker
def fetch_data_node(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    print(f"\n{'='*50}")
    print(f"Getting data for {ticker}...")
    print(f"{'='*50}")
    start = datetime.now()
    
    # Fetch all data sources and return Pydantic objects
    prices = get_stock_prices(ticker, "day", 1, "2025-01-01", "2025-10-04")
    metrics = get_financial_metrics(ticker, "ttm")
    items = get_line_items(ticker)
    trades = get_insider_trades(ticker)
    news = get_news(ticker)
    facts = get_company_facts(ticker)
    
    elapsed = (datetime.now() - start).total_seconds()
    print(f"\nComplete in {elapsed:.2f}s")
    print(f"  - Prices: {len(prices)} data points")
    print(f"  - Metrics: {len(metrics)} periods")
    print(f"  - Line Items: {len(items)} items")
    print(f"  - Insider Trades: {len(trades)} trades")
    print(f"  - News: {len(news)} articles")
    print(f"  - Facts: {'Available' if facts else 'N/A'}")
    
    # Convert Pydantic models to dicts
    return {
        **state,
        "prices": [p.model_dump() for p in prices],
        "metrics": [m.model_dump() for m in metrics],
        "items": [i.model_dump() for i in items],
        "trades": [t.model_dump() for t in trades],
        "news": [n.model_dump() for n in news],
        "facts": facts.model_dump() if facts else {},
        "timestamp": datetime.now().isoformat()
    }

# NODE 2: Warren Buffett Agent
def warren_node(state: AgentState) -> AgentState:
    """Runs Warren Buffett value analysis."""
    print(f"\n{'='*50}")
    print("[WARREN AGENT] Analyzing long-term value...")
    print(f"{'='*50}")
    
    data = {
        "prices": state["prices"],
        "metrics": state["metrics"],
        "items": state["items"],
        "trades": state["trades"],
        "news": state["news"],
        "facts": state["facts"]
    }
    
    start = datetime.now()
    result = warren_agent_with_data(state["ticker"], data)
    elapsed = (datetime.now() - start).total_seconds()
    
    print(f"\n[WARREN AGENT] Complete in {elapsed:.2f}s")
    return {"warren_result": result}

# NODE 3: Bill Ackman Agent
def bill_node(state: AgentState) -> AgentState:
    """Runs Bill Ackman risk analysis."""
    print(f"\n{'='*50}")
    print("[BILL AGENT] Analyzing risks and catalysts...")
    print(f"{'='*50}")
    
    data = {
        "prices": state["prices"],
        "metrics": state["metrics"],
        "items": state["items"],
        "trades": state["trades"],
        "news": state["news"],
        "facts": state["facts"]
    }
    
    start = datetime.now()
    result = bill_agent_with_data(state["ticker"], data)
    elapsed = (datetime.now() - start).total_seconds()
    
    print(f"\n[BILL AGENT] Complete in {elapsed:.2f}s")
    return {"bill_result": result}

# NODE 4: Robinhood Coach Agent
def robin_node(state: AgentState) -> AgentState:
    """Runs Robinhood momentum analysis."""
    print(f"\n{'='*50}")
    print("[ROBIN AGENT] Analyzing short-term momentum...")
    print(f"{'='*50}")
    
    data = {
        "prices": state["prices"],
        "metrics": state["metrics"],
        "items": state["items"],
        "trades": state["trades"],
        "news": state["news"],
        "facts": state["facts"]
    }
    
    start = datetime.now()
    result = robin_agent_with_data(state["ticker"], data)
    elapsed = (datetime.now() - start).total_seconds()
    
    print(f"\n[ROBIN AGENT] Complete in {elapsed:.2f}s")
    return {"robin_result": result}

# Build the graph
def build_graph():
    """Constructs the LangGraph workflow with nodes and edges."""
    workflow = StateGraph(AgentState)
    
    # Add all nodes
    workflow.add_node("fetch_data", fetch_data_node)
    workflow.add_node("warren", warren_node)
    workflow.add_node("bill", bill_node)
    workflow.add_node("robin", robin_node)
    
    # Set entry point
    workflow.set_entry_point("fetch_data")
    
    # Define edges - parallel execution after fetch_data
    # All three agents run simultaneously after data is fetched
    workflow.add_edge("fetch_data", "warren")
    workflow.add_edge("fetch_data", "bill")
    workflow.add_edge("fetch_data", "robin")
    
    # All agents converge to END
    workflow.add_edge("warren", END)
    workflow.add_edge("bill", END)
    workflow.add_edge("robin", END)
    
    return workflow.compile()

def divider(title: str):
    """Print a nice divider."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def run_analysis(ticker: str):
    """Main function to run the multi-agent analysis."""
    overall_start = datetime.now()
    
    divider(f"MULTI-AGENT ANALYSIS FOR {ticker}")
    
    # Build and run the graph
    graph = build_graph()
    
    # Execute with initial state
    print("\n[LANGGRAPH] Starting workflow execution...")
    initial_state = {"ticker": ticker}
    result = graph.invoke(initial_state)
    
    # Display results
    divider("WARREN BUFFETT - VALUE ANALYSIS")
    print(result.get("warren_result", "No result available"))
    
    divider("BILL ACKMAN - RISK ANALYSIS")
    print(result.get("bill_result", "No result available"))
    
    divider("ROBINHOOD COACH - MOMENTUM ANALYSIS")
    print(result.get("robin_result", "No result available"))
    
    # Calculate total time
    total_time = (datetime.now() - overall_start).total_seconds()
    
    divider("PERFORMANCE SUMMARY")
    print(f"Total Analysis Time: {total_time:.2f} seconds")
    print(f"Timestamp: {result.get('timestamp')}")
    
    # Save to file
    output = {
        "ticker": ticker,
        "timestamp": result.get("timestamp"),
        "total_time_seconds": total_time,
        "data_summary": {
            "prices_count": len(result.get("prices", [])),
            "metrics_count": len(result.get("metrics", [])),
            "news_count": len(result.get("news", [])),
            "trades_count": len(result.get("trades", []))
        },
        "analyses": {
            "warren_buffett": result.get("warren_result"),
            "bill_ackman": result.get("bill_result"),
            "robinhood_coach": result.get("robin_result")
        }
    }
    
    filename = f"analysis_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\nAnalysis saved to: {filename}")
    
    return result

# test cases
if __name__ == "__main__":
    print("\n" + "="*60)
    print(" AI FINANCIAL ADVISORY SYSTEM")
    print(" Multi-Agent Analysis with LangGraph")
    print("="*60)
    
    ticker = input("\nEnter a stock ticker (e.g., AAPL, TSLA, NVDA): ").strip().upper()
    
    if not ticker:
        print("Error: No ticker provided")
        exit(1)
    
    try:
        run_analysis(ticker)
    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()








