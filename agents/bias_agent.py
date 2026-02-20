from agents.base import Agent
from agents.claim_verifier import allowed_evidence_keys_for_agent
from agents.data_quality import build_data_snapshot, collect_data_warnings
from agents.reliability import parse_structured_analysis, summary_payload

from langchain.schema import SystemMessage, HumanMessage
import json


class BiasAuditAgent(Agent):
    key = "bias_audit"
    title = "BIAS AUDIT"
    result_key = "bias_result"
    output_key = "bias_audit"
    depends_on = ["warren", "bill", "robin"]

    def audit_with_data(self, ticker: str, data: dict, agent_outputs: dict) -> str:
        snapshot = build_data_snapshot(data)
        warnings = collect_data_warnings(data)

        system_prompt = (
            "You are a bias auditor for an investment research workflow. "
            "Your job is to audit BOTH the input data coverage and the analysts' outputs. "
            "Identify biases like cherry-picking, recency bias, survivorship bias, "
            "overconfidence, confirmation bias, framing effects, and missing data risks. "
            "Also highlight disagreements or inconsistencies across analysts. "
            "Crucially, separate true contradictions from time-horizon differences "
            "(e.g., short-term momentum vs long-term value). "
            "Be specific: cite which data gaps could mislead decisions and where the "
            "analysis might be overstated. Keep it short and structured."
        )

        user_prompt = (
            f"Ticker: {ticker}\n\n"
            f"DATA SNAPSHOT:\n{json.dumps(snapshot, indent=2)}\n\n"
            f"DATA WARNINGS:\n{json.dumps(warnings, indent=2)}\n\n"
            f"AGENT OUTPUTS:\n{json.dumps(agent_outputs, indent=2)}\n\n"
            "Write a bias audit using this exact format and constraints:\n"
            "Section: Data Coverage and Gaps\n"
            "- 2-3 bullets, max 20 words each\n"
            "Section: Output Biases and Overreach\n"
            "- 2-3 bullets, max 20 words each\n"
            "Section: Cross-Agent Disagreements\n"
            "- 2-3 bullets, note if due to time horizon vs real contradiction\n"
            "Section: Mitigations / What to Verify Next\n"
            "- 2-3 bullets, max 20 words each\n"
            "No paragraphs, only bullets."
        )

        system = SystemMessage(content=system_prompt)
        user = HumanMessage(content=user_prompt)

        return self.llm.invoke([system, user]).content

    def run(self, state: dict) -> dict:
        data = {
            "prices": state.get("prices", []),
            "metrics": state.get("metrics", []),
            "items": state.get("items", []),
            "trades": state.get("trades", []),
            "news": state.get("news", []),
            "facts": state.get("facts", {}),
            "data_coverage": state.get("data_coverage", {}),
            "data_warnings": state.get("data_warnings", []),
        }
        agent_outputs = {}
        for advisor in ["warren", "bill", "robin"]:
            raw = state.get(f"{advisor}_result", "")
            parsed = parse_structured_analysis(
                raw=raw,
                agent=advisor,
                ticker=state["ticker"],
                allowed_evidence_keys=allowed_evidence_keys_for_agent(advisor),
                min_claims=3,
            )
            agent_outputs[advisor] = summary_payload(parsed)
        result = self.audit_with_data(state["ticker"], data, agent_outputs)
        return {self.result_key: result}


BIAS_AGENT = BiasAuditAgent()


def bias_agent_with_data(ticker: str, data: dict, agent_outputs: dict) -> str:
    """Bias audit agent that inspects both data coverage and other agents' outputs."""
    return BIAS_AGENT.audit_with_data(ticker, data, agent_outputs)


def bias_agent(ticker: str) -> str:
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

    agent_outputs = {"warren": "", "bill": "", "robin": ""}

    return bias_agent_with_data(ticker, data, agent_outputs)
