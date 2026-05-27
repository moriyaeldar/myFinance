"""
CSV / Excel transaction importer.

Supported formats
-----------------
Israeli banks (auto-detected by Hebrew column headers):
  - Bank Hapoalim     (תאריך / תיאור / חובה / זכות)
  - Bank Leumi        (תאריך ערך / תיאור / חובה / זכות)
  - Discount Bank     (תאריך / פרטים / חובה / זכות)
  - Mizrahi-Tefahot   (תאריך / תיאור הפעולה / חובה / זכות)
  - Max (Leumi Card)  (תאריך עסקה / שם בית עסק / סכום חיוב)
  - Visa Cal          (תאריך עסקה / שם בית עסק / סכום)
  - Isracard          (תאריך / שם בית עסק / סכום חיוב)

US banks:
  - Chase, Bank of America, Wells Fargo, Capital One, Amex, Mint, Generic
"""
import csv
import hashlib
import io
import uuid
from datetime import datetime, date
from typing import List

import pandas as pd

from analyzer import categorize


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_id(account_id: str, txn_date, desc: str, amount: float, ref: str = "") -> str:
    """Deterministic ID so re-importing the same file doesn't create duplicates."""
    key = f"{account_id}|{txn_date}|{desc}|{amount:.2f}|{ref}"
    return "csv-" + hashlib.sha1(key.encode()).hexdigest()[:20]


def _parse_amount(value: str) -> float:
    if not value:
        return 0.0
    cleaned = str(value).replace("$", "").replace("₪", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_date(value: str) -> date:
    value = str(value).strip().split(".")[0]  # strip microseconds if present
    for fmt in (
        "%d/%m/%Y", "%d/%m/%y",       # Israeli: DD/MM/YYYY
        "%m/%d/%Y", "%m/%d/%y",       # US:      MM/DD/YYYY
        "%Y-%m-%d %H:%M:%S",          # Hapoalim Excel datetime
        "%Y-%m-%d",                   # ISO
        "%d.%m.%Y",                   # DD.MM.YYYY
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {value!r}")


def _norm(headers: List[str]) -> dict:
    """Return {normalised_header: original_index} mapping."""
    return {h.strip().lower(): i for i, h in enumerate(headers)}


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

# Hebrew header keywords for each Israeli bank
_IL_BANK_SIGNATURES = {
    # Credit-card companies — most specific first
    "max_hapoalim":   {"תאריך", "שם בית עסק", "שם כרטיס"},   # Max via Hapoalim portal
    "max":            {"תאריך עסקה", "שם בית עסק", "סכום חיוב"},
    "cal":            {"תאריך עסקה", "שם בית עסק", "סכום"},
    "isracard":       {"תאריך", "שם בית עסק", "סכום חיוב"},
    # Banks — more specific first
    "hapoalim":       {"תאריך", "הפעולה", "חובה", "זכות"},
    "hapoalim_old":   {"תאריך", "תיאור", "חובה", "זכות"},
    "leumi":          {"תאריך ערך", "תיאור", "חובה", "זכות"},
    "mizrahi":        {"תאריך", "תיאור הפעולה", "חובה", "זכות"},
    "discount":       {"תאריך", "פרטים", "חובה", "זכות"},
}


def _detect_format(headers: List[str]) -> str:
    stripped = {h.strip() for h in headers}
    stripped_lower = {h.lower() for h in stripped}

    # Israeli bank check (match by Hebrew keywords)
    for bank, keywords in _IL_BANK_SIGNATURES.items():
        if keywords.issubset(stripped):
            return f"il_{bank}"

    # US bank check (English headers)
    h = stripped_lower
    if "transaction date" in h and "post date" in h and "category" in h:
        return "chase"
    if "date" in h and "description" in h and "amount" in h and "running bal." in h:
        return "bofa"
    if "date" in h and "amount" in h and "* original description" in h:
        return "wellsfargo"
    if "transaction date" in h and "description" in h and "amount" in h and "balance" in h and "card member" not in h:
        return "capitalone"
    if "date" in h and "description" in h and "amount" in h and "original description" in h:
        return "mint"
    if "card member" in h or "reference" in h:
        return "amex"
    return "generic"


# ---------------------------------------------------------------------------
# Excel → rows helper
# ---------------------------------------------------------------------------

def _excel_to_rows(content: bytes, filename: str = "") -> List[List[str]]:
    """
    Read an Excel file and return a list-of-lists (same shape as csv.reader output).
    Skips leading empty/metadata rows so the first meaningful row is the header.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "xlsx"
    engine = "xlrd" if ext == "xls" else "openpyxl"
    df = pd.read_excel(io.BytesIO(content), engine=engine, header=None, dtype=str)
    df = df.fillna("")

    rows = [[str(c).strip() for c in row] for row in df.values.tolist()]
    return _skip_metadata_rows(rows)


def _skip_metadata_rows(rows: List[List[str]]) -> List[List[str]]:
    """
    Skip leading rows that don't look like a header.
    Stops at the first row that contains a known Israeli bank header keyword,
    or the first non-empty row if no keyword is found.
    """
    HEADER_KEYWORDS = {"תאריך", "תאריך ערך", "תאריך עסקה", "תיאור", "פרטים",
                       "חובה", "זכות", "שם בית עסק", "סכום", "date", "description", "amount"}
    for i, row in enumerate(rows):
        cells = {c.strip() for c in row if c.strip()}
        if cells & HEADER_KEYWORDS:
            return rows[i:]
    # Fallback: drop only fully empty leading rows
    while rows and all(not c for c in rows[0]):
        rows.pop(0)
    return rows


# ---------------------------------------------------------------------------
# Israeli bank parsers
# ---------------------------------------------------------------------------

def _parse_il_bank(rows: List[List[str]], fmt: str, account_id: str) -> List[dict]:
    """Parse rows from an Israeli bank / credit-card export."""
    if not rows:
        return []

    headers = rows[0]
    h = {v.strip(): i for i, v in enumerate(headers)}
    transactions = []

    for row in rows[1:]:
        if not row or all(not c.strip() for c in row):
            continue
        try:
            txn = _parse_il_row(row, h, fmt, account_id)
            if txn:
                transactions.append(txn)
        except Exception:
            continue
    return transactions


def _parse_il_row(row, h, fmt, account_id) -> dict | None:
    def col(name):
        idx = h.get(name)
        return row[idx].strip() if idx is not None and idx < len(row) else ""

    if fmt == "il_max_hapoalim":
        # Columns: שם כרטיס | חיוב לתאריך | תאריך | שם בית עסק | סכום חיוב בש''ח | סכום קנייה | אסמכתא
        txn_date = _parse_date(col("תאריך"))
        desc = col("שם בית עסק")
        amount_col = next((k for k in h if k.startswith("סכום חיוב")), None)
        raw_amount = row[h[amount_col]].strip() if amount_col and amount_col in h else ""
        if not raw_amount:
            purchase_col = next((k for k in h if "סכום קנייה" in k), None)
            raw_amount = row[h[purchase_col]].strip() if purchase_col and purchase_col in h else "0"
        amount = _parse_amount(raw_amount)
        ref = col("אסמכתא")  # unique reference per transaction

    elif fmt == "il_max":
        txn_date = _parse_date(col("תאריך עסקה"))
        desc = col("שם בית עסק")
        amount = _parse_amount(col("סכום חיוב"))

    elif fmt == "il_cal":
        txn_date = _parse_date(col("תאריך עסקה"))
        desc = col("שם בית עסק")
        amount = _parse_amount(col("סכום"))

    elif fmt == "il_isracard":
        txn_date = _parse_date(col("תאריך"))
        desc = col("שם בית עסק")
        amount = _parse_amount(col("סכום חיוב"))

    elif fmt == "il_hapoalim":
        txn_date = _parse_date(col("תאריך"))
        action = col("הפעולה")
        details = col("פרטים")
        desc = f"{action} {details}".strip() if details else action
        debit = _parse_amount(col("חובה"))
        credit = _parse_amount(col("זכות"))
        amount = debit if debit else -credit

    elif fmt == "il_hapoalim_old":
        txn_date = _parse_date(col("תאריך"))
        desc = col("תיאור")
        debit = _parse_amount(col("חובה"))
        credit = _parse_amount(col("זכות"))
        amount = debit if debit else -credit

    elif fmt == "il_leumi":
        txn_date = _parse_date(col("תאריך ערך"))
        desc = col("תיאור")
        debit = _parse_amount(col("חובה"))
        credit = _parse_amount(col("זכות"))
        amount = debit if debit else -credit

    elif fmt == "il_discount":
        txn_date = _parse_date(col("תאריך"))
        desc = col("פרטים")
        debit = _parse_amount(col("חובה"))
        credit = _parse_amount(col("זכות"))
        amount = debit if debit else -credit

    elif fmt == "il_mizrahi":
        txn_date = _parse_date(col("תאריך"))
        desc = col("תיאור הפעולה")
        debit = _parse_amount(col("חובה"))
        credit = _parse_amount(col("זכות"))
        amount = debit if debit else -credit

    else:
        return None

    if not desc:
        return None

    group, category = categorize(desc)
    if amount < 0:
        group = "Income"
        category = "Income"

    ref = locals().get("ref", "")
    return {
        "id": _make_id(account_id, txn_date, desc, amount, ref),
        "account_id": account_id,
        "date": txn_date,
        "description": desc,
        "merchant_name": None,
        "amount": amount,
        "category": category,
        "category_group": group,
        "source": "csv",
        "currency": "ILS",
        "pending": False,
    }


# ---------------------------------------------------------------------------
# US bank parsers (unchanged logic, refactored into one function)
# ---------------------------------------------------------------------------

def _parse_us_row(row, h, fmt) -> tuple:
    """Return (date, description, amount) for US bank formats."""
    def get(name, fallback=None):
        idx = h.get(name, h.get(fallback, -1)) if fallback else h.get(name, -1)
        return row[idx].strip() if 0 <= idx < len(row) else ""

    if fmt == "chase":
        return _parse_date(get("transaction date")), get("description"), _parse_amount(get("amount"))

    if fmt == "bofa":
        return _parse_date(get("date")), get("description"), _parse_amount(get("amount"))

    if fmt == "wellsfargo":
        desc = row[4].strip() if len(row) > 4 else get("description")
        return _parse_date(row[0]), desc, _parse_amount(row[1])

    if fmt == "capitalone":
        debit_i = h.get("debit", -1)
        credit_i = h.get("credit", -1)
        if debit_i >= 0 and row[debit_i].strip():
            amt = _parse_amount(row[debit_i])
        elif credit_i >= 0 and row[credit_i].strip():
            amt = -_parse_amount(row[credit_i])
        else:
            amt = _parse_amount(get("amount"))
        return _parse_date(get("transaction date")), get("description"), amt

    if fmt == "amex":
        return _parse_date(get("date")), get("description", "merchant"), _parse_amount(get("amount"))

    if fmt == "mint":
        amt = _parse_amount(get("amount"))
        txn_type_i = h.get("transaction type", -1)
        if txn_type_i >= 0 and "credit" in row[txn_type_i].lower():
            amt = -abs(amt)
        else:
            amt = abs(amt)
        return _parse_date(get("date")), get("description"), amt

    # generic
    date_i = h.get("date", 0)
    desc_i = h.get("description", h.get("memo", 1))
    amt_i = h.get("amount", 2)
    return _parse_date(row[date_i]), row[desc_i].strip(), _parse_amount(row[amt_i])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _decode_csv(content: bytes) -> str:
    """Try common encodings used by Israeli and US banks."""
    for enc in ("utf-8-sig", "cp1255", "windows-1255", "utf-8", "latin-1"):
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("latin-1")


def parse_csv(content: bytes, account_id: str = None, filename: str = "") -> List[dict]:
    """
    Parse a bank CSV or Excel export and return transaction dicts ready for the DB.
    Auto-detects Israeli and US bank formats.
    """
    acct_id = account_id or f"csv-{uuid.uuid4().hex[:8]}"
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    # --- Excel files ---
    if ext in ("xlsx", "xls"):
        rows = _excel_to_rows(content, filename)
        if not rows:
            return []
        fmt = _detect_format(rows[0])
        if fmt.startswith("il_"):
            return _parse_il_bank(rows, fmt, acct_id)
        # US Excel: treat rows directly (no re-decode needed)
        headers = rows[0]
        h = _norm(headers)
        transactions = []
        for row in rows[1:]:
            if not row or all(not c for c in row):
                continue
            try:
                txn_date, desc, amount = _parse_us_row(row, h, fmt)
                if not desc:
                    continue
                group, category = categorize(desc)
                if amount < 0:
                    group, category = "Income", "Income"
                transactions.append({
                    "id": _make_id(acct_id, txn_date, desc, amount),
                    "account_id": acct_id,
                    "date": txn_date,
                    "description": desc,
                    "merchant_name": None,
                    "amount": amount,
                    "category": category,
                    "category_group": group,
                    "source": "csv",
                    "currency": "USD",
                    "pending": False,
                })
            except Exception:
                continue
        return transactions

    # --- CSV files ---
    text = _decode_csv(content)
    rows = list(csv.reader(io.StringIO(text)))
    rows = _skip_metadata_rows(rows)
    if not rows:
        return []

    fmt = _detect_format(rows[0])

    if fmt.startswith("il_"):
        return _parse_il_bank(rows, fmt, acct_id)

    # US bank path
    headers = rows[0]
    h = _norm(headers)
    transactions = []

    for row in rows[1:]:
        if not row or all(not c.strip() for c in row):
            continue
        try:
            txn_date, desc, amount = _parse_us_row(row, h, fmt)
            if not desc:
                continue
            group, category = categorize(desc)
            if amount < 0:
                group = "Income"
                category = "Income"
            transactions.append({
                "id": _make_id(acct_id, txn_date, desc, amount),
                "account_id": acct_id,
                "date": txn_date,
                "description": desc,
                "merchant_name": None,
                "amount": amount,
                "category": category,
                "category_group": group,
                "source": "csv",
                "currency": "USD",
                "pending": False,
            })
        except Exception:
            continue

    return transactions
