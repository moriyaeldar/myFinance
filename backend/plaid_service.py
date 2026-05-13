"""
Plaid integration – creates link tokens, exchanges public tokens,
and pulls transactions + account balances.
"""
import os
import uuid
from datetime import date, timedelta
from typing import List, Optional

from plaid.api import plaid_api
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
from plaid import Configuration, ApiClient, Environment

from analyzer import categorize


def _get_client():
    env_map = {
        "sandbox": Environment.Sandbox,
        "development": Environment.Development,
        "production": Environment.Production,
    }
    plaid_env = os.getenv("PLAID_ENV", "sandbox")
    configuration = Configuration(
        host=env_map.get(plaid_env, Environment.Sandbox),
        api_key={
            "clientId": os.getenv("PLAID_CLIENT_ID", ""),
            "secret": os.getenv("PLAID_SECRET", ""),
        },
    )
    api_client = ApiClient(configuration)
    return plaid_api.PlaidApi(api_client)


def create_link_token(user_id: str = "user-1") -> str:
    client = _get_client()
    request = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id=user_id),
        client_name="myFinance",
        products=[Products("transactions")],
        country_codes=[CountryCode("US")],
        language="en",
    )
    response = client.link_token_create(request)
    return response["link_token"]


def exchange_public_token(public_token: str) -> str:
    client = _get_client()
    request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = client.item_public_token_exchange(request)
    return response["access_token"]


def fetch_accounts(access_token: str) -> List[dict]:
    client = _get_client()
    request = AccountsGetRequest(access_token=access_token)
    response = client.accounts_get(request)
    accounts = []
    for acct in response["accounts"]:
        accounts.append({
            "id": acct["account_id"],
            "name": acct["name"],
            "type": str(acct["type"]),
            "subtype": str(acct.get("subtype", "")),
            "balance": float(acct["balances"].get("current", 0) or 0),
            "currency": acct["balances"].get("iso_currency_code", "USD") or "USD",
            "plaid_access_token": access_token,
            "source": "plaid",
        })
    return accounts


def fetch_transactions(access_token: str, days: int = 365) -> List[dict]:
    client = _get_client()
    start_date = date.today() - timedelta(days=days)
    end_date = date.today()

    all_transactions = []
    offset = 0

    while True:
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(count=500, offset=offset),
        )
        response = client.transactions_get(request)
        txns = response["transactions"]
        if not txns:
            break

        for t in txns:
            amount = float(t["amount"])  # Plaid: positive = debit from user
            merchant = t.get("merchant_name") or ""
            desc = t.get("name", "")
            group, category = categorize(desc, merchant)

            # Income: Plaid uses negative amounts for deposits
            if amount < 0:
                group = "Income"
                category = "Income"

            all_transactions.append({
                "id": t["transaction_id"],
                "account_id": t["account_id"],
                "date": t["date"],
                "description": desc,
                "merchant_name": merchant or None,
                "amount": amount,
                "category": category,
                "category_group": group,
                "source": "plaid",
                "currency": t.get("iso_currency_code", "USD") or "USD",
                "pending": bool(t.get("pending", False)),
            })

        offset += len(txns)
        if offset >= response["total_transactions"]:
            break

    return all_transactions
