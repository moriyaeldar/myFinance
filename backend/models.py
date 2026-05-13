from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class TransactionOut(BaseModel):
    id: str
    account_id: str
    date: date
    description: str
    merchant_name: Optional[str]
    amount: float
    category: str
    category_group: str
    source: str
    currency: str
    pending: bool

    class Config:
        from_attributes = True


class AccountOut(BaseModel):
    id: str
    name: str
    type: str
    subtype: Optional[str]
    institution: Optional[str]
    balance: float
    currency: str
    source: str
    active: bool

    class Config:
        from_attributes = True


class CategorySettingsOut(BaseModel):
    id: int
    category_group: str
    status: str
    monthly_budget: Optional[float]
    notes: Optional[str]

    class Config:
        from_attributes = True


class CategorySettingsUpdate(BaseModel):
    status: Optional[str] = None        # "essential" | "optional" | "cut"
    monthly_budget: Optional[float] = None
    notes: Optional[str] = None


class CategorySummary(BaseModel):
    category_group: str
    total: float
    transaction_count: int
    percentage_of_total: float
    monthly_avg: float
    status: str
    monthly_budget: Optional[float]
    top_merchants: List[str]


class MonthlyTrend(BaseModel):
    month: str          # "2025-01"
    income: float
    expenses: float
    net: float
    by_group: dict


class DashboardStats(BaseModel):
    total_expenses_mtd: float
    total_income_mtd: float
    net_mtd: float
    total_expenses_30d: float
    savings_potential: float        # sum of "cut" categories
    top_category: str
    accounts_connected: int
    transactions_count: int


class PlaidLinkTokenResponse(BaseModel):
    link_token: str


class PlaidExchangeRequest(BaseModel):
    public_token: str
    institution_name: Optional[str] = None


class AnalysisResponse(BaseModel):
    dashboard: DashboardStats
    categories: List[CategorySummary]
    monthly_trends: List[MonthlyTrend]
    accounts: List[AccountOut]


class AIRecommendation(BaseModel):
    title: str
    description: str
    estimated_monthly_savings: float
    priority: str          # "high" | "medium" | "low"
    category: str
    action: str            # short actionable step


class AIAdviceResponse(BaseModel):
    recommendations: List[AIRecommendation]
    summary: str
    savings_potential_monthly: float
    savings_potential_annual: float
    health_score: int      # 0-100
    health_label: str
