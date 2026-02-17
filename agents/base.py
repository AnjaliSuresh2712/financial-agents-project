from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import json
import os

from langchain.schema import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI


def make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )


class Agent(ABC):
    key: str
    title: str
    result_key: str
    output_key: str
    depends_on: List[str] = []

    def __init__(self, llm: ChatOpenAI | None = None) -> None:
        self.llm = llm or make_llm()

    @abstractmethod
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class AdvisorAgent(Agent):
    system_prompt: str
    user_prompt_template = (
        "Summary for {ticker}:\n{summary}\n\nShould I invest in {ticker}? Answer concisely."
    )

    def _insufficient_data_message(self, data: Dict[str, Any]) -> str | None:
        return None

    def _summarize_data(self, ticker: str, data: Dict[str, Any]) -> str:
        prices = data.get("prices", [])
        metrics = data.get("metrics", [])
        items = data.get("items", [])
        trades = data.get("trades", [])
        news = data.get("news", [])
        facts = data.get("facts", {})
        data_coverage = data.get("data_coverage", {}) or {}
        data_warnings = data.get("data_warnings", []) or []
        latest_metrics = metrics[0] if metrics else {}

        prompt = (
            f"Summarize the following financial info for {ticker} in 6-8 short bullets. "
            f"Only include facts that affect an invest / don't invest decision.\n\n"
            f"- Recent Prices (last 10 days):\n{json.dumps(prices[:10])}\n"
            f"- Financial Metrics (latest period):\n{json.dumps(latest_metrics)}\n"
            f"- Line Items (sample):\n{json.dumps(items[:5])}\n"
            f"- Insider Trades (recent):\n{json.dumps(trades[:5])}\n"
            f"- Recent News (headlines):\n{json.dumps([n.get('title') for n in news[:5]])}\n"
            f"- Company Facts:\n{json.dumps(facts)}\n"
            f"- Data Coverage:\n{json.dumps(data_coverage)}\n"
            f"- Data Warnings:\n{json.dumps(data_warnings)}\n"
        )
        return self.llm.invoke([HumanMessage(content=prompt)]).content

    def analyze_with_data(self, ticker: str, data: Dict[str, Any]) -> str:
        insufficient = self._insufficient_data_message(data)
        if insufficient:
            return insufficient
        summary = self._summarize_data(ticker, data)
        system = SystemMessage(content=self.system_prompt)
        user = HumanMessage(
            content=self.user_prompt_template.format(ticker=ticker, summary=summary)
        )
        return self.llm.invoke([system, user]).content

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
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
        result = self.analyze_with_data(state["ticker"], data)
        return {self.result_key: result}
