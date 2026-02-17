from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
import json
import re

from agents.registry import AGENTS
from agents.data_quality import summarize_data_coverage, collect_data_warnings
from data_api import (
    get_stock_prices,
    get_financial_metrics,
    get_line_items,
    get_insider_trades,
    get_news,
    get_company_facts,
    default_date_range,
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
    bias_result: str
    data_coverage: Dict[str, Any]
    data_warnings: List[str]
    timestamp: str

# NODE 1: Fetch all financial data for the ticker
def fetch_data_node(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    print(f"\n{'='*50}")
    print(f"Getting data for {ticker}...")
    print(f"{'='*50}")
    start = datetime.now()
    
    # Fetch all data sources and return Pydantic objects
    start_date, end_date = default_date_range(365)
    prices = get_stock_prices(ticker, "day", 1, start_date, end_date)
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
    data = {
        "prices": [p.model_dump() for p in prices],
        "metrics": [m.model_dump() for m in metrics],
        "items": [i.model_dump() for i in items],
        "trades": [t.model_dump() for t in trades],
        "news": [n.model_dump() for n in news],
        "facts": facts.model_dump() if facts else {},
    }
    data_coverage = summarize_data_coverage(data)
    data_warnings = collect_data_warnings(data)

    return {
        **state,
        "prices": data["prices"],
        "metrics": data["metrics"],
        "items": data["items"],
        "trades": data["trades"],
        "news": data["news"],
        "facts": data["facts"],
        "data_coverage": data_coverage,
        "data_warnings": data_warnings,
        "timestamp": datetime.now().isoformat()
    }

def make_agent_node(agent):
    def node(state: AgentState) -> AgentState:
        print(f"\n{'='*50}")
        print(f"[{agent.key.upper()}] {agent.title}")
        print(f"{'='*50}")
        start = datetime.now()
        result = agent.run(state)
        elapsed = (datetime.now() - start).total_seconds()
        print(f"\n[{agent.key.upper()}] Complete in {elapsed:.2f}s")
        return result

    return node

# Build the graph
def build_graph():
    """Constructs the LangGraph workflow with nodes and edges."""
    workflow = StateGraph(AgentState)
    
    # Add all nodes
    workflow.add_node("fetch_data", fetch_data_node)
    for agent in AGENTS:
        workflow.add_node(agent.key, make_agent_node(agent))
    
    # Set entry point
    workflow.set_entry_point("fetch_data")
    
    for agent in AGENTS:
        if agent.depends_on:
            for dependency in agent.depends_on:
                workflow.add_edge(dependency, agent.key)
        else:
            workflow.add_edge("fetch_data", agent.key)

    depended_on = {dependency for agent in AGENTS for dependency in agent.depends_on}
    for agent in AGENTS:
        if agent.key not in depended_on:
            workflow.add_edge(agent.key, END)
    
    return workflow.compile()

def divider(title: str):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def build_markdown_report(output: Dict[str, Any]) -> str:
    data_summary = output.get("data_summary", {})
    analyses = output.get("analyses", {})
    warnings = data_summary.get("warnings") or []

    lines = []
    lines.append(f"# Analysis for {output.get('ticker', 'UNKNOWN')}")
    lines.append("")
    lines.append(f"Timestamp: {output.get('timestamp')}")
    lines.append(f"Total time: {output.get('total_time_seconds'):.2f} seconds")
    lines.append("")
    lines.append("## Data Summary")
    lines.append(f"- Prices count: {data_summary.get('prices_count')}")
    lines.append(f"- Metrics count: {data_summary.get('metrics_count')}")
    lines.append(f"- News count: {data_summary.get('news_count')}")
    lines.append(f"- Trades count: {data_summary.get('trades_count')}")
    lines.append(f"- Coverage: {json.dumps(data_summary.get('coverage', {}))}")
    if warnings:
        lines.append("### Data Warnings")
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- Data warnings: None")

    lines.append("")
    lines.append("## Warren Buffett - Value Analysis")
    lines.append(analyses.get("warren_buffett", "No result available"))
    lines.append("")
    lines.append("## Bill Ackman - Risk Analysis")
    lines.append(analyses.get("bill_ackman", "No result available"))
    lines.append("")
    lines.append("## Robinhood Coach - Momentum Analysis")
    lines.append(analyses.get("robinhood_coach", "No result available"))
    lines.append("")
    lines.append("## Bias Audit")
    lines.append(analyses.get("bias_audit", "No result available"))
    lines.append("")

    return "\n".join(lines)

def run_analysis(ticker: str):
    """Main function to run the multi-agent analysis."""
    overall_start = datetime.now()
    
    divider(f"ANALYSIS FOR {ticker}")
    
    # Build and run the graph
    graph = build_graph()
    
    # Execute with initial state
    print("\n[LANGGRAPH] Starting workflow execution...")
    initial_state = {"ticker": ticker}
    result = graph.invoke(initial_state)
    
    # Display results
    for agent in AGENTS:
        divider(agent.title)
        print(result.get(agent.result_key, "No result available"))
    
    # Calculate total time
    total_time = (datetime.now() - overall_start).total_seconds()
    
    divider("PERFORMANCE SUMMARY")
    print(f"Total Analysis Time: {total_time:.2f} seconds")
    if result.get("data_warnings"):
        divider("DATA WARNINGS")
        for warning in result.get("data_warnings", []):
            print(f"- {warning}")
    
    # Save to file
    analyses = {agent.output_key: result.get(agent.result_key) for agent in AGENTS}
    output = {
        "ticker": ticker,
        "timestamp": result.get("timestamp"),
        "total_time_seconds": total_time,
        "data_summary": {
            "prices_count": len(result.get("prices", [])),
            "metrics_count": len(result.get("metrics", [])),
            "news_count": len(result.get("news", [])),
            "trades_count": len(result.get("trades", [])),
            "coverage": result.get("data_coverage", {}),
            "warnings": result.get("data_warnings", []),
        },
        "analyses": analyses,
    }
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"analysis_{ticker}_{timestamp}.json"
    md_filename = f"analysis_{ticker}_{timestamp}.md"
    with open(json_filename, "w") as f:
        json.dump(output, f, indent=2)
    with open(md_filename, "w") as f:
        f.write(build_markdown_report(output))
    
    print(f"\nAnalysis saved to: {md_filename}")
    print(f"Raw data saved to: {json_filename}")
    
    return result

# test cases
if __name__ == "__main__":
    ticker = input("\nEnter a stock ticker (e.g., AAPL, TSLA, NVDA): ").strip().upper()
    
    if not ticker:
        print("Error: No ticker provided")
        exit(1)
    if not re.fullmatch(r"[A-Z0-9.-]{1,7}", ticker):
        print("Error: Invalid ticker format")
        exit(1)
    
    try:
        run_analysis(ticker)
    except Exception as e:
        print(f"\nError during analysis: {e}")
        import traceback
        traceback.print_exc()








