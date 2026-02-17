import requests
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_fixed
from datetime import datetime, timedelta


def default_date_range(days: int = 365):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    return start_date.isoformat(), end_date.isoformat()

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
    params = {
        "ticker": ticker,
        "interval": interval,
        "interval_multiplier": interval_multiplier,
        "start_date": start_date,
        "end_date": end_date
    }
    params = {k: v for k, v in params.items() if v is not None}
    
    r = requests.get(url, params=params, timeout=10)
    
    if r.status_code != 200:
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
    params = {"ticker": ticker, "period": period}
    
    r = requests.get(url, params=params, timeout=10)
    
    if r.status_code != 200:
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
    """Fetch line items - may not be available for all APIs."""
    url = "https://api.financialdatasets.ai/financials/search/line-items"
    
    try:
        r = requests.get(url, params={"ticker": ticker}, timeout=10)
        
        if r.status_code != 200:
            print(f"[INFO] Line items not available (status {r.status_code})")
            return []
        
        data = r.json()
        items = data.get("line_items", [])
        return [LineItem(**item) for item in items]
    except Exception as e:
        print(f"[INFO] Could not fetch line items: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_insider_trades(ticker: str) -> List[InsiderTrade]:
    """Fetch insider trades with Pydantic validation."""
    url = "https://api.financialdatasets.ai/insider-trades"
    
    r = requests.get(url, params={"ticker": ticker}, timeout=10)
    
    if r.status_code != 200:
        raise ValueError(f"API error: status {r.status_code}")
    
    data = r.json()
    trades = data.get("trades", [])
    
    try:
        return [InsiderTrade(**item) for item in trades]
    except ValidationError as e:
        print(f"Validation error in trades: {e}")
        return []

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def get_news(ticker: str) -> List[NewsArticle]:
    """Fetch news with Pydantic validation."""
    url = "https://api.financialdatasets.ai/news/"
    
    r = requests.get(url, params={"ticker": ticker}, timeout=10)
    
    if r.status_code != 200:
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
    
    try:
        r = requests.get(url, params={"ticker": ticker}, timeout=10)
        
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
