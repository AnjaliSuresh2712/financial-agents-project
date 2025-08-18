import requests

def get_stock_prices(ticker: str, interval="day", interval_multiplier=1, start_date=None, end_date=None):
    url = "https://api.financialdatasets.ai/prices/"
    params = {
        "ticker": ticker,
        "interval": interval,
        "interval_multiplier": interval_multiplier,
        "start_date": start_date,
        "end_date": end_date
    }
    params = {k: v for k, v in params.items() if v is not None}
    r = requests.get(url, params=params)
    return r.json() if r.status_code == 200 else None

def get_financial_metrics(ticker: str, period="ttm"):
    url = "https://api.financialdatasets.ai/financial-metrics"
    params = {"ticker": ticker, "period": period}
    r = requests.get(url, params=params)
    return r.json() if r.status_code == 200 else None

def get_line_items(ticker):
    url = "https://api.financialdatasets.ai/financials/search/line-items"
    r = requests.get(url, params={"ticker": ticker})
    return r.json()

def get_insider_trades(ticker):
    url = "https://api.financialdatasets.ai/insider-trades"
    r = requests.get(url, params={"ticker": ticker})
    return r.json()

def get_news(ticker):
    url = "https://api.financialdatasets.ai/news/"
    r = requests.get(url, params={"ticker": ticker})
    return r.json()

def get_company_facts(ticker):
    url = "https://api.financialdatasets.ai/company/facts/"
    r = requests.get(url, params={"ticker": ticker})
    return r.json()

