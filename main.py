from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import re

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore[assignment]

if load_dotenv is not None:
    project_root = Path(__file__).resolve().parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / "backend/.env")

from agents.registry import AGENTS
from agents.data_quality import summarize_data_coverage, collect_data_warnings
from agents.claim_verifier import compute_feature_signals, verify_analysis_claims
from agents.decision_policy import compute_final_policy
from agents.reliability import parse_structured_analysis, summary_payload
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
    structured_analyses: Dict[str, Any]
    claim_verification: Dict[str, Any]
    final_policy: Dict[str, Any]
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
    structured = output.get("structured_analyses", {})
    policy = output.get("final_policy", {})
    verification = output.get("claim_verification", {})
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
    lines.append("## Final Policy Decision")
    lines.append(f"- Recommendation: {policy.get('final_recommendation', 'N/A')}")
    lines.append(f"- Confidence: {policy.get('confidence', 'N/A')}")
    lines.append(f"- Adjusted Score: {policy.get('adjusted_policy_score', 'N/A')}")
    if policy.get("abstain_reasons"):
        lines.append("### Abstain Reasons")
        for reason in policy.get("abstain_reasons", []):
            lines.append(f"- {reason}")
    lines.append("### Verification Summary")
    for advisor, summary in verification.items():
        lines.append(
            f"- {advisor}: {summary.get('verified_claim_count', 0)}/{summary.get('claim_count', 0)} claims verified"
        )

    lines.append("")
    lines.append("## Warren Buffett - Value Analysis")
    warren_structured = structured.get("warren")
    if warren_structured:
        lines.append(f"- Recommendation: {warren_structured.get('recommendation', 'N/A')}")
        lines.append(f"- Confidence: {warren_structured.get('confidence', 'N/A')}")
        lines.append(f"- Thesis: {warren_structured.get('thesis', 'N/A')}")
    else:
        lines.append(analyses.get("warren_buffett", "No result available"))
    lines.append("")
    lines.append("## Bill Ackman - Risk Analysis")
    bill_structured = structured.get("bill")
    if bill_structured:
        lines.append(f"- Recommendation: {bill_structured.get('recommendation', 'N/A')}")
        lines.append(f"- Confidence: {bill_structured.get('confidence', 'N/A')}")
        lines.append(f"- Thesis: {bill_structured.get('thesis', 'N/A')}")
    else:
        lines.append(analyses.get("bill_ackman", "No result available"))
    lines.append("")
    lines.append("## Robinhood Coach - Momentum Analysis")
    robin_structured = structured.get("robin")
    if robin_structured:
        lines.append(f"- Recommendation: {robin_structured.get('recommendation', 'N/A')}")
        lines.append(f"- Confidence: {robin_structured.get('confidence', 'N/A')}")
        lines.append(f"- Thesis: {robin_structured.get('thesis', 'N/A')}")
    else:
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

    shared_data = {
        "prices": result.get("prices", []),
        "metrics": result.get("metrics", []),
        "items": result.get("items", []),
        "trades": result.get("trades", []),
        "news": result.get("news", []),
        "facts": result.get("facts", {}),
    }
    feature_signals = compute_feature_signals(shared_data)
    structured_analyses: Dict[str, Any] = {}
    claim_verification: Dict[str, Any] = {}
    advisor_keys = {"warren", "bill", "robin"}

    for agent in AGENTS:
        if agent.key not in advisor_keys:
            continue
        allowed_keys = agent.allowed_evidence_keys() if hasattr(agent, "allowed_evidence_keys") else None
        min_claims = agent.min_claim_count() if hasattr(agent, "min_claim_count") else 0
        parsed = parse_structured_analysis(
            raw=result.get(agent.result_key, ""),
            agent=agent.key,
            ticker=ticker,
            allowed_evidence_keys=allowed_keys,
            min_claims=min_claims,
        )
        structured_analyses[agent.key] = summary_payload(parsed)
        claim_verification[agent.key] = verify_analysis_claims(parsed, feature_signals)

    final_policy = compute_final_policy(
        analyses=structured_analyses,
        verification=claim_verification,
        data_coverage=result.get("data_coverage", {}),
        data_warnings=result.get("data_warnings", []),
    )
    result["structured_analyses"] = structured_analyses
    result["claim_verification"] = claim_verification
    result["final_policy"] = final_policy
    
    # Display results
    for agent in AGENTS:
        divider(agent.title)
        if agent.key in advisor_keys:
            structured_result = structured_analyses.get(agent.key, {})
            print(f"Recommendation: {structured_result.get('recommendation', 'N/A')}")
            print(f"Confidence: {structured_result.get('confidence', 'N/A')}")
            print(f"Thesis: {structured_result.get('thesis', 'N/A')}")
            for idx, caveat in enumerate(structured_result.get("caveats", [])[:3], start=1):
                print(f"Caveat {idx}: {caveat}")
        else:
            print(result.get(agent.result_key, "No result available"))

    divider("FINAL POLICY DECISION")
    print(f"Recommendation: {final_policy.get('final_recommendation')}")
    print(f"Confidence: {final_policy.get('confidence')}")
    print(f"Adjusted Score: {final_policy.get('adjusted_policy_score')}")
    if final_policy.get("abstain_reasons"):
        print("Abstain Reasons:")
        for reason in final_policy.get("abstain_reasons", []):
            print(f"- {reason}")

    divider("CLAIM VERIFICATION SUMMARY")
    for advisor, summary in claim_verification.items():
        verified = summary.get("verified_claim_count", 0)
        total = summary.get("claim_count", 0)
        rate = summary.get("verification_rate", 0.0)
        print(f"- {advisor}: {verified}/{total} verified (rate={rate:.2f})")
    
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
        "structured_analyses": result.get("structured_analyses", {}),
        "claim_verification": result.get("claim_verification", {}),
        "final_policy": result.get("final_policy", {}),
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








