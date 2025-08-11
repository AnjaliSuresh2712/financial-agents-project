!pip install -q langchain openai langchain-community langchain-openai
# Set API key
# key is used to authenticate requests to OpenRouter’s API.
import os
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType, tool

os.environ["OPENROUTER_API_KEY"] = "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"  

# Import agents
from agents.warren_agent import warren_agent
from agents.bill_agent import bill_agent
from agents.robin_agent import robin_agent


