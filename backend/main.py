"""
myFinance – FastAPI backend
"""
import os
import uuid
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

def _billing_month(d: date) -> tuple:
    """Return (year, month) of the billing period a date falls into (10th–9th cycle)."""
    if d.day >= 10:
        return (d.year, d.month)
    if d.month == 1:
        return (d.year - 1, 12)
    return (d.year, d.month - 1)


def _billing_period_dates(year: int, month: int):
    """Return (start_date, end_date) for a billing month."""
    start = date(year, month, 10)
    if month == 12:
        end = date(year + 1, 1, 9)
    else:
        end = date(year, month + 1, 9)
    return start, end


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
# Plaid
# ---------------------------------------------------------------------------

@app.get("/api/plaid/link-token", response_model=PlaidLinkTokenResponse, tags=["Plaid"])
def get_link_token():
    if not os.getenv("PLAID_CLIENT_ID"):
        raise HTTPException(status_code=400, detail="Plaid credentials not configured. Use CSV import.")
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

    try:
        transactions = parse_csv(content, account_id, filename=file.filename or "")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Parse error: {e}")

    if not transactions:
        raise HTTPException(status_code=400, detail="No valid transactions found. Check that the file is a supported bank export format.")

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

    # Build a set of existing (date, amount, description) to catch cross-account duplicates
    existing_keys = {
        (str(r.date), round(r.amount, 2), r.description)
        for r in db.query(Transaction.date, Transaction.amount, Transaction.description).all()
    }

    added = 0
    for txn in transactions:
        txn["account_id"] = account_id
        content_key = (str(txn["date"]), round(float(txn["amount"]), 2), txn.get("description", ""))
        if content_key in existing_keys:
            continue
        existing = db.query(Transaction).filter_by(id=txn["id"]).first()
        if not existing:
            db.add(Transaction(**txn))
            existing_keys.add(content_key)
            added += 1

    db.commit()
    return {"transactions_added": added, "account_id": account_id}


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@app.post("/api/admin/deduplicate", tags=["Admin"])
def deduplicate_transactions(db: Session = Depends(get_db)):
    """Remove cross-account duplicate transactions (same date+amount+description), keeping oldest."""
    all_txns = db.query(Transaction).order_by(Transaction.created_at).all()
    seen: dict = {}
    to_delete = []
    for txn in all_txns:
        key = (str(txn.date), round(txn.amount, 2), txn.description)
        if key in seen:
            to_delete.append(txn.id)
        else:
            seen[key] = txn.id
    for txn_id in to_delete:
        db.query(Transaction).filter_by(id=txn_id).delete()
    db.commit()
    return {"duplicates_removed": len(to_delete)}


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

@app.get("/api/billing-months", tags=["Analysis"])
def get_billing_months(db: Session = Depends(get_db)):
    """Return all billing periods (10th–9th) that have transactions, newest first."""
    rows = db.query(Transaction.date).all()
    seen: set = set()
    for (d,) in rows:
        seen.add(_billing_month(d))
    result = []
    for (year, month) in sorted(seen, reverse=True):
        start, end = _billing_period_dates(year, month)
        result.append({
            "label": f"{year}-{month:02d}",
            "year": year,
            "month": month,
            "start": str(start),
            "end": str(end),
        })
    return result


@app.get("/api/analysis", tags=["Analysis"])
def get_analysis(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Transaction)
    if start_date:
        q = q.filter(Transaction.date >= start_date)
    if end_date:
        q = q.filter(Transaction.date <= end_date)
    transactions = q.all()
    all_transactions = db.query(Transaction).all()
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
            "transactions_count": len(all_transactions),
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


# ---------------------------------------------------------------------------
# Serve React frontend (production build)
# ---------------------------------------------------------------------------

_DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../frontend/dist")

if os.path.exists(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse(os.path.join(_DIST, "index.html"))
