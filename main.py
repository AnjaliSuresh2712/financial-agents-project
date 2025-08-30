import os
from agents.warren_agent import warren_agent
from agents.bill_agent import bill_agent
from agents.robin_agent import robin_agent

def divider(title: str):
    print("\n" + "=" * 12 + f" {title} " + "=" * 12)

def run_all_agents(ticker: str, question: str):
    divider(f"Question: {question} | Ticker: {ticker}")
    
    try:
        divider("Warren Buffett")
        print(warren_agent(ticker))
    except Exception as e:
        print(f"[Warren error] {e}")

    try:
        divider("Bill Ackman")
        print(bill_agent(ticker))
    except Exception as e:
        print(f"[Bill error] {e}")

    try:
        divider("Robinhood")
        print(robin_agent(ticker))
    except Exception as e:
        print(f"[Robin error] {e}")

# test cases for now
if __name__ == "__main__":
    test_cases = [
        ("AAPL", "Should I invest in Apple?"),
        ("TSLA", "Should I invest in Tesla?"),
        ("HON", "Should I invest in Honeywell?")
    ]
    for ticker, question in test_cases:
        run_all_agents(ticker, question)






