from agents.warren_agent import WARREN_AGENT
from agents.bill_agent import BILL_AGENT
from agents.robin_agent import ROBIN_AGENT
from agents.bias_agent import BIAS_AGENT


AGENTS = [
    WARREN_AGENT,
    BILL_AGENT,
    ROBIN_AGENT,
    BIAS_AGENT,
]

AGENT_BY_KEY = {agent.key: agent for agent in AGENTS}
