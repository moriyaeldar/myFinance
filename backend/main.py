"""
myFinance – FastAPI backend
"""
import os
import uuid
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

load_dotenv()

from database import (
    init_db, get_db, Transaction, Account, CategorySettings
)
from models import (
    TransactionOut, AccountOut, CategorySettingsOut, CategorySettingsUpdate,
    CategorySummary, MonthlyTrend, DashboardStats, AnalysisResponse,
    PlaidLinkTokenResponse, PlaidExchangeRequest, AIAdviceResponse,
)
from analyzer import compute_dashboard, compute_category_summaries, compute_monthly_trends
from csv_importer import parse_csv
from demo_data import generate_demo_transactions, DEMO_ACCOUNTS
import ai_advisor

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="myFinance API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings_map(db: Session) -> dict:
    """Return {category_group: {status, monthly_budget}} dict."""
    settings = db.query(CategorySettings).all()
    return {
        s.category_group: {"status": s.status, "monthly_budget": s.monthly_budget}
        for s in settings
    }


def _upsert_account(db: Session, data: dict):
    existing = db.query(Account).filter_by(id=data["id"]).first()
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
    else:
        db.add(Account(**data))


def _upsert_transaction(db: Session, data: dict):
    existing = db.query(Transaction).filter_by(id=data["id"]).first()
    if not existing:
        db.add(Transaction(**data))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

@app.post("/api/demo/load", tags=["Demo"])
def load_demo_data(db: Session = Depends(get_db)):
    """Load 6 months of realistic demo transactions."""
    # Wipe existing demo data
    db.query(Transaction).filter_by(source="demo").delete()
    db.query(Account).filter_by(source="demo").delete()

    for acct in DEMO_ACCOUNTS:
        _upsert_account(db, acct)

    for txn in generate_demo_transactions(months=6):
        _upsert_transaction(db, txn)

    db.commit()
    count = db.query(Transaction).filter_by(source="demo").count()
    return {"message": f"Loaded {count} demo transactions across 2 accounts."}


@app.delete("/api/demo/clear", tags=["Demo"])
def clear_demo_data(db: Session = Depends(get_db)):
    db.query(Transaction).filter_by(source="demo").delete()
    db.query(Account).filter_by(source="demo").delete()
    db.commit()
    return {"message": "Demo data cleared."}


# ---------------------------------------------------------------------------
# Plaid
# ---------------------------------------------------------------------------

@app.get("/api/plaid/link-token", response_model=PlaidLinkTokenResponse, tags=["Plaid"])
def get_link_token():
    if not os.getenv("PLAID_CLIENT_ID"):
        raise HTTPException(status_code=400, detail="Plaid credentials not configured. Use demo mode or CSV import.")
    try:
        from plaid_service import create_link_token
        token = create_link_token()
        return {"link_token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plaid/exchange", tags=["Plaid"])
def exchange_token(body: PlaidExchangeRequest, db: Session = Depends(get_db)):
    if not os.getenv("PLAID_CLIENT_ID"):
        raise HTTPException(status_code=400, detail="Plaid credentials not configured.")
    try:
        from plaid_service import exchange_public_token, fetch_accounts, fetch_transactions
        access_token = exchange_public_token(body.public_token)

        accounts = fetch_accounts(access_token)
        for acct in accounts:
            if body.institution_name:
                acct["institution"] = body.institution_name
            _upsert_account(db, acct)

        transactions = fetch_transactions(access_token)
        for txn in transactions:
            _upsert_transaction(db, txn)

        db.commit()
        return {
            "accounts_added": len(accounts),
            "transactions_added": len(transactions),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------

@app.post("/api/import/csv", tags=["Import"])
async def import_csv(
    file: UploadFile = File(...),
    account_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    content = await file.read()
    account_id = f"csv-{uuid.uuid4().hex[:8]}"

    transactions = parse_csv(content, account_id, filename=file.filename or "")
    if not transactions:
        raise HTTPException(status_code=400, detail="No valid transactions found in file.")

    # Create a synthetic account for the CSV
    currency = transactions[0].get("currency", "USD") if transactions else "USD"
    acct = Account(
        id=account_id,
        name=account_name or file.filename or "Imported Account",
        type="depository",
        subtype="checking",
        institution="CSV Import",
        balance=0.0,
        currency=currency,
        source="csv",
        active=True,
    )
    db.merge(acct)

    added = 0
    for txn in transactions:
        txn["account_id"] = account_id
        existing = db.query(Transaction).filter_by(id=txn["id"]).first()
        if not existing:
            db.add(Transaction(**txn))
            added += 1

    db.commit()
    return {"transactions_added": added, "account_id": account_id}


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

@app.get("/api/accounts", response_model=List[AccountOut], tags=["Accounts"])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).filter_by(active=True).all()


@app.delete("/api/accounts/{account_id}", tags=["Accounts"])
def delete_account(account_id: str, db: Session = Depends(get_db)):
    acct = db.query(Account).filter_by(id=account_id).first()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found.")
    db.query(Transaction).filter_by(account_id=account_id).delete()
    db.delete(acct)
    db.commit()
    return {"message": "Account and transactions removed."}


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

@app.get("/api/transactions", response_model=List[TransactionOut], tags=["Transactions"])
def list_transactions(
    account_id: Optional[str] = None,
    category_group: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(200, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(Transaction)
    if account_id:
        q = q.filter(Transaction.account_id == account_id)
    if category_group:
        q = q.filter(Transaction.category_group == category_group)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    return q.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()


@app.patch("/api/transactions/{txn_id}/category", tags=["Transactions"])
def recategorize(txn_id: str, category_group: str, category: str, db: Session = Depends(get_db)):
    txn = db.query(Transaction).filter_by(id=txn_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found.")
    txn.category_group = category_group
    txn.category = category
    db.commit()
    return {"message": "Category updated."}


# ---------------------------------------------------------------------------
# Category Settings
# ---------------------------------------------------------------------------

@app.get("/api/categories/settings", response_model=List[CategorySettingsOut], tags=["Categories"])
def get_category_settings(db: Session = Depends(get_db)):
    return db.query(CategorySettings).all()


@app.patch("/api/categories/{category_group}/settings", response_model=CategorySettingsOut, tags=["Categories"])
def update_category_settings(
    category_group: str,
    body: CategorySettingsUpdate,
    db: Session = Depends(get_db),
):
    setting = db.query(CategorySettings).filter_by(category_group=category_group).first()
    if not setting:
        setting = CategorySettings(category_group=category_group)
        db.add(setting)

    if body.status is not None:
        if body.status not in ("essential", "optional", "cut"):
            raise HTTPException(status_code=400, detail="status must be 'essential', 'optional', or 'cut'")
        setting.status = body.status
    if body.monthly_budget is not None:
        setting.monthly_budget = body.monthly_budget
    if body.notes is not None:
        setting.notes = body.notes

    db.commit()
    db.refresh(setting)
    return setting


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

@app.get("/api/analysis", tags=["Analysis"])
def get_analysis(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).all()
    accounts = db.query(Account).filter_by(active=True).all()
    smap = _settings_map(db)
    status_map = {k: v["status"] for k, v in smap.items()}

    dashboard_raw = compute_dashboard(transactions, status_map)
    categories = compute_category_summaries(transactions, smap)
    trends = compute_monthly_trends(transactions)

    return {
        "dashboard": {
            **dashboard_raw,
            "accounts_connected": len(accounts),
            "transactions_count": len(transactions),
        },
        "categories": categories,
        "monthly_trends": trends,
        "accounts": [
            {
                "id": a.id, "name": a.name, "type": a.type,
                "subtype": a.subtype, "institution": a.institution,
                "balance": a.balance, "currency": a.currency, "source": a.source, "active": a.active,
            }
            for a in accounts
        ],
    }


@app.get("/api/analysis/advice", tags=["Analysis"])
def get_ai_advice(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).all()
    smap = _settings_map(db)
    status_map = {k: v["status"] for k, v in smap.items()}

    dashboard_raw = compute_dashboard(transactions, status_map)
    categories = compute_category_summaries(transactions, smap)
    trends = compute_monthly_trends(transactions)

    cut_categories = [g for g, s in status_map.items() if s == "cut"]

    try:
        advice = ai_advisor.get_ai_recommendations(
            categories=categories,
            monthly_trends=trends,
            stats=dashboard_raw,
            cut_categories=cut_categories,
        )
    except Exception as e:
        advice = ai_advisor._rule_based_fallback(categories, dashboard_raw)

    return advice


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
