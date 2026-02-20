import requests
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_fixed
from datetime import datetime, timedelta
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # type: ignore[assignment]

if load_dotenv is not None:
    project_root = Path(__file__).resolve().parent
    load_dotenv(project_root / ".env")
    load_dotenv(project_root / "backend/.env")


def default_date_range(days: int = 365):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    return start_date.isoformat(), end_date.isoformat()


def _auth_headers() -> dict:
    """Build auth headers for financialdatasets.ai requests."""
    api_key = (
        os.environ.get("FINANCIAL_DATASETS_API_KEY")
        or os.environ.get("FINANCIAL_DATA_API_KEY")
        or os.environ.get("FD_API_KEY")
    )
    if not api_key:
        return {}
    return {"X-API-KEY": api_key}

# Pydantic models 
class Price(BaseModel):
    open: float
    close: float
    high: float
    low: float
    volume: int
    time: str

class FinancialMetrics(BaseModel):
    ticker: str
    report_period: str
    fiscal_period: str
    period: str
    currency: str
    
    # Valuation Metrics
    market_cap: Optional[float] = None
    enterprise_value: Optional[float] = None
    price_to_earnings_ratio: Optional[float] = None
    price_to_book_ratio: Optional[float] = None
    price_to_sales_ratio: Optional[float] = None
    enterprise_value_to_ebitda_ratio: Optional[float] = None
    enterprise_value_to_revenue_ratio: Optional[float] = None
    free_cash_flow_yield: Optional[float] = None
    peg_ratio: Optional[float] = None
    
    # Profitability Margins
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    
    # Returns
    return_on_equity: Optional[float] = None
    return_on_assets: Optional[float] = None
    return_on_invested_capital: Optional[float] = None
    
    # Efficiency Ratios
    asset_turnover: Optional[float] = None
    inventory_turnover: Optional[float] = None
    receivables_turnover: Optional[float] = None
    days_sales_outstanding: Optional[float] = None
    operating_cycle: Optional[float] = None
    working_capital_turnover: Optional[float] = None
    
    # Liquidity Ratios
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    cash_ratio: Optional[float] = None
    operating_cash_flow_ratio: Optional[float] = None
    
    # Leverage Ratios
    debt_to_equity: Optional[float] = None
    debt_to_assets: Optional[float] = None
    interest_coverage: Optional[float] = None
    
    # Growth Metrics
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    book_value_growth: Optional[float] = None
    earnings_per_share_growth: Optional[float] = None
    free_cash_flow_growth: Optional[float] = None
    operating_income_growth: Optional[float] = None
    ebitda_growth: Optional[float] = None
    
    # Per Share Metrics
    payout_ratio: Optional[float] = None
    earnings_per_share: Optional[float] = None
    book_value_per_share: Optional[float] = None
    free_cash_flow_per_share: Optional[float] = None

class LineItem(BaseModel):
    line_item: str
    value: Optional[float] = None
    period: Optional[str] = None

class InsiderTrade(BaseModel):
    insider_name: Optional[str] = None
    transaction_type: Optional[str] = None
    shares: Optional[int] = None
    price: Optional[float] = None
    date: Optional[str] = None

class NewsArticle(BaseModel):
    title: str
    published_at: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None

class CompanyFact(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_stock_prices(ticker: str, interval="day", interval_multiplier=1, 
                     start_date=None, end_date=None) -> List[Price]:
    """Fetch stock prices with Pydantic validation and retry logic."""
    url = "https://api.financialdatasets.ai/prices/"
    headers = _auth_headers()
    params = {
        "ticker": ticker,
        "interval": interval,
        "interval_multiplier": interval_multiplier,
        "start_date": start_date,
        "end_date": end_date
    }
    params = {k: v for k, v in params.items() if v is not None}
    
    r = requests.get(url, params=params, headers=headers, timeout=10)
    
    if r.status_code != 200:
        if r.status_code == 401:
            raise ValueError(
                "API error: status 401 (set FINANCIAL_DATASETS_API_KEY for financialdatasets.ai)"
            )
        raise ValueError(f"API error: status {r.status_code}")
    
    data = r.json()
    prices = data.get("prices", [])
    
    try:
        return [Price(**item) for item in prices]
    except ValidationError as e:
        print(f"Validation error in prices: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_financial_metrics(ticker: str, period="ttm") -> List[FinancialMetrics]:
    """Fetch financial metrics - returns list of time periods."""
    url = "https://api.financialdatasets.ai/financial-metrics"
    headers = _auth_headers()
    params = {"ticker": ticker, "period": period}
    
    r = requests.get(url, params=params, headers=headers, timeout=10)
    
    if r.status_code != 200:
        if r.status_code == 401:
            raise ValueError(
                "API error: status 401 (set FINANCIAL_DATASETS_API_KEY for financialdatasets.ai)"
            )
        raise ValueError(f"API error: status {r.status_code}")
    
    data = r.json()
    metrics_list = data.get("financial_metrics", [])
    
    try:
        return [FinancialMetrics(**item) for item in metrics_list]
    except ValidationError as e:
        print(f"Validation error in metrics: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_line_items(ticker: str) -> List[LineItem]:
    """Fetch key line items via the financials search endpoint."""
    url = "https://api.financialdatasets.ai/financials/search/line-items"
    headers = {**_auth_headers(), "Content-Type": "application/json"}
    requested_items = [
        "revenue",
        "net_income",
        "operating_income",
        "free_cash_flow",
        "total_debt",
        "cash_and_equivalents",
        "total_assets",
        "total_liabilities",
    ]
    body = {
        "line_items": requested_items,
        "tickers": [ticker],
        "period": "ttm",
        "limit": 1,
    }

    try:
        r = requests.post(url, json=body, headers=headers, timeout=10)

        if r.status_code != 200:
            print(f"[INFO] Line items not available (status {r.status_code})")
            return []

        data = r.json()
        search_results = data.get("search_results", [])
        if not search_results:
            return []

        latest = search_results[0]
        period = latest.get("report_period") or latest.get("period")
        items: List[LineItem] = []
        for key in requested_items:
            value = latest.get(key)
            if isinstance(value, (int, float)):
                items.append(LineItem(line_item=key, value=float(value), period=period))
        return items
    except Exception as e:
        print(f"[INFO] Could not fetch line items: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_insider_trades(ticker: str) -> List[InsiderTrade]:
    """Fetch insider trades with Pydantic validation."""
    url = "https://api.financialdatasets.ai/insider-trades"
    headers = _auth_headers()
    
    r = requests.get(url, params={"ticker": ticker, "limit": 100}, headers=headers, timeout=10)
    
    if r.status_code != 200:
        if r.status_code == 401:
            raise ValueError(
                "API error: status 401 (set FINANCIAL_DATASETS_API_KEY for financialdatasets.ai)"
            )
        raise ValueError(f"API error: status {r.status_code}")
    
    data = r.json()
    trades = data.get("insider_trades", [])
    normalized: List[InsiderTrade] = []
    for item in trades:
        shares_raw = item.get("transaction_shares")
        price_raw = item.get("transaction_price_per_share")
        shares: Optional[int] = int(shares_raw) if isinstance(shares_raw, (int, float)) else None
        price: Optional[float] = float(price_raw) if isinstance(price_raw, (int, float)) else None

        tx_type = item.get("transaction_type")
        if not tx_type and isinstance(shares_raw, (int, float)):
            tx_type = "buy" if shares_raw > 0 else ("sell" if shares_raw < 0 else "unknown")

        normalized.append(
            InsiderTrade(
                insider_name=item.get("name"),
                transaction_type=tx_type,
                shares=shares,
                price=price,
                date=item.get("transaction_date") or item.get("filing_date"),
            )
        )

    try:
        return [InsiderTrade(**item.model_dump()) for item in normalized]
    except ValidationError as e:
        print(f"Validation error in trades: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_news(ticker: str) -> List[NewsArticle]:
    """Fetch news with Pydantic validation."""
    url = "https://api.financialdatasets.ai/news/"
    headers = _auth_headers()
    
    r = requests.get(url, params={"ticker": ticker}, headers=headers, timeout=10)
    
    if r.status_code != 200:
        if r.status_code == 401:
            raise ValueError(
                "API error: status 401 (set FINANCIAL_DATASETS_API_KEY for financialdatasets.ai)"
            )
        raise ValueError(f"API error: status {r.status_code}")
    
    data = r.json()
    news = data.get("news", [])
    
    try:
        return [NewsArticle(**item) for item in news]
    except ValidationError as e:
        print(f"Validation error in news: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_company_facts(ticker: str) -> Optional[CompanyFact]:
    """Fetch company facts with Pydantic validation."""
    url = "https://api.financialdatasets.ai/company/facts/"
    headers = _auth_headers()
    
    try:
        r = requests.get(url, params={"ticker": ticker}, headers=headers, timeout=10)
        
        if r.status_code != 200:
            print(f"[INFO] Company facts not available (status {r.status_code})")
            return None
        
        data = r.json()
        
        # The API wraps data in 'company_facts' key
        if 'company_facts' in data:
            facts_data = data['company_facts']
            return CompanyFact(**facts_data) if facts_data else None
        
        return CompanyFact(**data) if data else None
    except ValidationError as e:
        print(f"[INFO] Could not validate company facts: {e}")
        return None
    except Exception as e:
        print(f"[INFO] Could not fetch company facts: {e}")
        return None
