"""FastMCP server exposing Mastercard Open Finance US (Finicity) operations.

Run locally over stdio:      python -m openfinance_mcp
Run as a service over HTTP:  python -m openfinance_mcp --transport http --port 9030
"""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config.settings import Settings, load_settings
from .finicity_client import OpenFinanceClient
from .models import ToolResult, wrap
from .spec_defaults import decisions_as_dicts

mcp = FastMCP("openfinance-us")

_client: OpenFinanceClient | None = None
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def get_client() -> OpenFinanceClient:
    """Lazily build the Finicity client from resolved settings."""
    global _client
    if _client is not None:
        return _client
    s = get_settings()
    if not s.configured:
        raise RuntimeError(
            "Open Finance US is not configured. Provide OPEN_FINANCE_PARTNER_ID, "
            "OPEN_FINANCE_PARTNER_SECRET and OPEN_FINANCE_APP_KEY (env, a local .env, "
            "OPENFINANCE_MCP_ENV_FILE, or the sibling vima config/.env)."
        )
    _client = OpenFinanceClient(
        s.partner_id, s.partner_secret, s.app_key, base_url=s.api_base_url
    )
    return _client


# --------------------------------------------------------------------------- #
# Diagnostics (no credentials required)
# --------------------------------------------------------------------------- #
@mcp.tool()
def server_status() -> dict[str, Any]:
    """Report configuration source (secrets masked) and resolved spec decisions."""
    return {
        "credentials": get_settings().masked(),
        "spec_decisions": decisions_as_dicts(),
    }


@mcp.tool()
def create_access_token() -> ToolResult:
    """Force-create a Finicity App-Token; use this to verify credentials work."""
    return wrap(get_client().create_token())


# --------------------------------------------------------------------------- #
# Customers
# --------------------------------------------------------------------------- #
@mcp.tool()
def create_testing_customer(username: str) -> ToolResult:
    """Create a Finicity *testing* customer (sandbox, non-billable)."""
    return wrap(get_client().add_testing_customer(username))


@mcp.tool()
def list_customers(search: str = "", start: int = 1, limit: int = 25) -> ToolResult:
    """List customers, optionally filtered by username search."""
    return wrap(get_client().get_customers(search=search, start=start, limit=limit))


@mcp.tool()
def get_customer(customer_id: str) -> ToolResult:
    """Fetch a single customer by id."""
    return wrap(get_client().get_customer(customer_id))


@mcp.tool()
def delete_customer(customer_id: str) -> ToolResult:
    """Delete a customer and all associated data. Destructive."""
    return wrap(get_client().delete_customer(customer_id))


# --------------------------------------------------------------------------- #
# Connect (account linking)
# --------------------------------------------------------------------------- #
@mcp.tool()
def generate_connect_url(customer_id: str, experience: str = "") -> ToolResult:
    """Generate a hosted Data Connect URL for the customer to link accounts."""
    return wrap(
        get_client().generate_connect_url(customer_id, experience=experience or None)
    )


# --------------------------------------------------------------------------- #
# Accounts
# --------------------------------------------------------------------------- #
@mcp.tool()
def get_customer_accounts(customer_id: str) -> ToolResult:
    """List all linked accounts for a customer."""
    return wrap(get_client().get_customer_accounts(customer_id))


@mcp.tool()
def get_customer_account(customer_id: str, account_id: str) -> ToolResult:
    """Fetch one account for a customer."""
    return wrap(get_client().get_customer_account(customer_id, account_id))


@mcp.tool()
def refresh_customer_accounts(customer_id: str) -> ToolResult:
    """Trigger an aggregation refresh for all of a customer's accounts."""
    return wrap(get_client().refresh_customer_accounts(customer_id))


@mcp.tool()
def get_account_ach_details(customer_id: str, account_id: str) -> ToolResult:
    """Get ACH routing/account number details for an account."""
    return wrap(get_client().get_account_ach_details(customer_id, account_id))


@mcp.tool()
def get_available_balance(customer_id: str, account_id: str) -> ToolResult:
    """Get the real-time available balance for an account."""
    return wrap(get_client().get_available_balance(customer_id, account_id))


# --------------------------------------------------------------------------- #
# Transactions (epoch-second date range)
# --------------------------------------------------------------------------- #
@mcp.tool()
def get_customer_transactions(
    customer_id: str, from_date: int, to_date: int, start: int = 1, limit: int = 1000
) -> ToolResult:
    """Get transactions across all of a customer's accounts. Dates are epoch seconds."""
    return wrap(
        get_client().get_customer_transactions(
            customer_id, from_date, to_date, start=start, limit=limit
        )
    )


@mcp.tool()
def get_account_transactions(
    customer_id: str,
    account_id: str,
    from_date: int,
    to_date: int,
    start: int = 1,
    limit: int = 1000,
) -> ToolResult:
    """Get transactions for a single account. Dates are epoch seconds."""
    return wrap(
        get_client().get_account_transactions(
            customer_id, account_id, from_date, to_date, start=start, limit=limit
        )
    )


@mcp.tool()
def get_recurring_transactions(
    customer_id: str, account_ids: list[str] | None = None
) -> ToolResult:
    """Detect recurring transactions (subscriptions, salary, etc.)."""
    return wrap(get_client().get_recurring_transactions(customer_id, account_ids=account_ids))


@mcp.tool()
def load_historic_transactions(customer_id: str, account_id: str) -> ToolResult:
    """Load up to 24 months of historic transactions for an account."""
    return wrap(get_client().load_historic_transactions(customer_id, account_id))


# --------------------------------------------------------------------------- #
# Institutions
# --------------------------------------------------------------------------- #
@mcp.tool()
def search_institutions(search: str = "", start: int = 1, limit: int = 25) -> ToolResult:
    """Search supported financial institutions."""
    return wrap(get_client().get_institutions(search=search, start=start, limit=limit))


@mcp.tool()
def get_institution(institution_id: str) -> ToolResult:
    """Get details for one institution."""
    return wrap(get_client().get_institution(institution_id))


# --------------------------------------------------------------------------- #
# Consumers + decisioning reports
# --------------------------------------------------------------------------- #
@mcp.tool()
def create_consumer(
    customer_id: str, first_name: str, last_name: str, email: str = "", ssn: str = ""
) -> ToolResult:
    """Create a consumer record (prerequisite for VOA/VOI/VOAI reports)."""
    return wrap(
        get_client().create_consumer(
            customer_id, first_name, last_name, email=email, ssn=ssn
        )
    )


@mcp.tool()
def generate_voa_report(
    customer_id: str, account_ids: list[str] | None = None, from_date: int | None = None
) -> ToolResult:
    """Generate a Verification of Assets (VOA) report."""
    return wrap(
        get_client().generate_voa_report(customer_id, account_ids=account_ids, from_date=from_date)
    )


@mcp.tool()
def generate_voi_report(
    customer_id: str, account_ids: list[str] | None = None
) -> ToolResult:
    """Generate a Verification of Income (VOI) report."""
    return wrap(get_client().generate_voi_report(customer_id, account_ids=account_ids))


@mcp.tool()
def generate_voai_report(
    customer_id: str, account_ids: list[str] | None = None, from_date: int | None = None
) -> ToolResult:
    """Generate a VOA-with-Income (voaHistory) report."""
    return wrap(
        get_client().generate_voai_report(customer_id, account_ids=account_ids, from_date=from_date)
    )


@mcp.tool()
def get_report(report_id: str, purpose_code: str = "3F") -> ToolResult:
    """Fetch a generated decisioning report by id."""
    return wrap(get_client().get_report(report_id, purpose_code=purpose_code))


# --------------------------------------------------------------------------- #
# Payment Success Indicators (PSI)
# --------------------------------------------------------------------------- #
@mcp.tool()
def generate_payment_success_indicators(
    customer_id: str, account_id: str, amount: float
) -> ToolResult:
    """Generate Non-FCRA Payment Success Indicators for a proposed payment."""
    return wrap(
        get_client().generate_payment_success_indicators(customer_id, account_id, amount)
    )


@mcp.tool()
def get_payment_success_indicators(
    customer_id: str, account_id: str, pay_request_id: str
) -> ToolResult:
    """Retrieve a previously generated PSI result by payRequestId."""
    return wrap(
        get_client().get_payment_success_indicators(customer_id, account_id, pay_request_id)
    )


# --------------------------------------------------------------------------- #
# TxPUSH notifications
# --------------------------------------------------------------------------- #
@mcp.tool()
def subscribe_txpush(customer_id: str, account_id: str, callback_url: str) -> ToolResult:
    """Subscribe an account to TxPUSH webhook notifications."""
    return wrap(get_client().subscribe_to_txpush(customer_id, account_id, callback_url))


@mcp.tool()
def disable_txpush(customer_id: str, account_id: str) -> ToolResult:
    """Disable TxPUSH notifications for an account."""
    return wrap(get_client().disable_txpush(customer_id, account_id))


# --------------------------------------------------------------------------- #
# Customers (extended)
# --------------------------------------------------------------------------- #
@mcp.tool()
def create_active_customer(
    username: str, first_name: str = "", last_name: str = ""
) -> ToolResult:
    """Create an *active* (billable) customer for production use."""
    return wrap(get_client().add_customer(username, first_name=first_name, last_name=last_name))


@mcp.tool()
def update_customer(
    customer_id: str, first_name: str = "", last_name: str = "", email: str = ""
) -> ToolResult:
    """Update a customer's profile fields."""
    return wrap(
        get_client().update_customer(
            customer_id,
            first_name=first_name or None,
            last_name=last_name or None,
            email=email or None,
        )
    )


# --------------------------------------------------------------------------- #
# Connect (extended)
# --------------------------------------------------------------------------- #
@mcp.tool()
def generate_lite_connect_url(customer_id: str, institution_id: str) -> ToolResult:
    """Generate a Lite Data Connect URL scoped to one institution."""
    return wrap(get_client().generate_lite_connect_url(customer_id, institution_id))


@mcp.tool()
def generate_fix_connect_url(customer_id: str, institution_login_id: str) -> ToolResult:
    """Generate a Fix Data Connect URL to repair a broken connection."""
    return wrap(get_client().generate_fix_connect_url(customer_id, institution_login_id))


# --------------------------------------------------------------------------- #
# Accounts (extended)
# --------------------------------------------------------------------------- #
@mcp.tool()
def get_account_owner(customer_id: str, account_id: str) -> ToolResult:
    """Get account owner (name/address) information."""
    return wrap(get_client().get_account_owner(customer_id, account_id))


@mcp.tool()
def get_account_owner_details(customer_id: str, account_id: str) -> ToolResult:
    """Get detailed (v3) account owner information."""
    return wrap(get_client().get_account_owner_details(customer_id, account_id))


@mcp.tool()
def get_account_payment_details(customer_id: str, account_id: str) -> ToolResult:
    """Get ACH details incl. RTP/FedNow support (v3)."""
    return wrap(get_client().get_account_payment_details(customer_id, account_id))


@mcp.tool()
def get_loan_payment_details(customer_id: str, account_id: str) -> ToolResult:
    """Get loan payment details for a loan-type account."""
    return wrap(get_client().get_loan_payment_details(customer_id, account_id))


@mcp.tool()
def get_account_statement(customer_id: str, account_id: str, index: int = 1) -> ToolResult:
    """Get an account statement PDF (returned base64-encoded)."""
    return wrap(get_client().get_account_statement(customer_id, account_id, index=index))


@mcp.tool()
def delete_customer_account(customer_id: str, account_id: str) -> ToolResult:
    """Remove access to a single account. Destructive."""
    return wrap(get_client().delete_customer_account(customer_id, account_id))


# --------------------------------------------------------------------------- #
# Institutions (extended)
# --------------------------------------------------------------------------- #
@mcp.tool()
def get_institution_branding(institution_id: str) -> ToolResult:
    """Get an institution's branding assets."""
    return wrap(get_client().get_institution_branding(institution_id))


@mcp.tool()
def get_certified_institutions(search: str = "", start: int = 1, limit: int = 25) -> ToolResult:
    """List certified institutions."""
    return wrap(get_client().get_certified_institutions(search=search, start=start, limit=limit))


@mcp.tool()
def get_institutions_by_routing_number(routing_number: str) -> ToolResult:
    """Look up institutions by ABA routing number."""
    return wrap(get_client().get_institutions_by_routing_number(routing_number))


# --------------------------------------------------------------------------- #
# Consumers (extended)
# --------------------------------------------------------------------------- #
@mcp.tool()
def get_consumer(consumer_id: str) -> ToolResult:
    """Get a consumer record by consumer id."""
    return wrap(get_client().get_consumer(consumer_id))


@mcp.tool()
def get_consumer_for_customer(customer_id: str) -> ToolResult:
    """Get the consumer record associated with a customer."""
    return wrap(get_client().get_consumer_for_customer(customer_id))


# --------------------------------------------------------------------------- #
# Decisioning reports (extended)
# --------------------------------------------------------------------------- #
@mcp.tool()
def generate_cash_flow_personal_report(
    customer_id: str, account_ids: list[str] | None = None
) -> ToolResult:
    """Generate a personal Cash Flow report."""
    return wrap(get_client().generate_cash_flow_personal_report(customer_id, account_ids=account_ids))


@mcp.tool()
def generate_cash_flow_business_report(
    customer_id: str, account_ids: list[str] | None = None
) -> ToolResult:
    """Generate a business Cash Flow report."""
    return wrap(get_client().generate_cash_flow_business_report(customer_id, account_ids=account_ids))


@mcp.tool()
def generate_transactions_report(
    customer_id: str, from_date: int, to_date: int, account_ids: list[str] | None = None
) -> ToolResult:
    """Generate a Transactions report over an epoch-second date range."""
    return wrap(
        get_client().generate_transactions_report(
            customer_id, from_date, to_date, account_ids=account_ids
        )
    )


@mcp.tool()
def generate_balance_analytics_report(
    customer_id: str, user_type: str = "personal", account_ids: list[str] | None = None
) -> ToolResult:
    """Generate a Balance Analytics report."""
    return wrap(
        get_client().generate_balance_analytics_report(
            customer_id, user_type=user_type, account_ids=account_ids
        )
    )


@mcp.tool()
def generate_cashflow_analytics_report(
    customer_id: str, user_type: str = "personal", account_ids: list[str] | None = None
) -> ToolResult:
    """Generate a Cash Flow Analytics report."""
    return wrap(
        get_client().generate_cashflow_analytics_report(
            customer_id, user_type=user_type, account_ids=account_ids
        )
    )


@mcp.tool()
def get_report_by_customer(customer_id: str, report_id: str, purpose_code: str = "3F") -> ToolResult:
    """Fetch a report scoped to a specific customer."""
    return wrap(get_client().get_report_by_customer(customer_id, report_id, purpose_code=purpose_code))


@mcp.tool()
def get_reports_by_customer(customer_id: str) -> ToolResult:
    """List all reports generated for a customer."""
    return wrap(get_client().get_reports_by_customer(customer_id))


# --------------------------------------------------------------------------- #
# FCRA Payment Success Indicators
# --------------------------------------------------------------------------- #
@mcp.tool()
def generate_fcra_payment_success_indicators(
    customer_id: str,
    account_id: str,
    amount: float,
    purpose: str = "1P",
    user_email: str = "user@example.com",
) -> ToolResult:
    """Generate FCRA-permissible Payment Success Indicators."""
    return wrap(
        get_client().generate_fcra_payment_success_indicators(
            customer_id, account_id, amount, purpose=purpose, user_email=user_email
        )
    )


@mcp.tool()
def get_fcra_payment_success_indicators(
    customer_id: str, account_id: str, pay_request_id: str
) -> ToolResult:
    """Retrieve an FCRA PSI result by payRequestId."""
    return wrap(
        get_client().get_fcra_payment_success_indicators(customer_id, account_id, pay_request_id)
    )


# --------------------------------------------------------------------------- #
# Micro-deposit verification
# --------------------------------------------------------------------------- #
@mcp.tool()
def initiate_micro_deposits(
    customer_id: str, receiver: dict, callback_url: str = ""
) -> ToolResult:
    """Initiate micro-deposit account verification."""
    return wrap(
        get_client().initiate_micro_deposits(customer_id, receiver, callback_url=callback_url or None)
    )


@mcp.tool()
def verify_micro_deposits(customer_id: str, account_id: str, amounts: list[float]) -> ToolResult:
    """Verify the two micro-deposit amounts."""
    return wrap(get_client().verify_micro_deposits(customer_id, account_id, amounts))


@mcp.tool()
def get_micro_deposit_details(customer_id: str, account_id: str) -> ToolResult:
    """Get the status/details of a micro-deposit verification."""
    return wrap(get_client().get_micro_deposit_details(customer_id, account_id))


# --------------------------------------------------------------------------- #
# Business services, matching, enrichment, transfers
# --------------------------------------------------------------------------- #
@mcp.tool()
def create_business(customer_id: str, business_name: str, business_type: str = "") -> ToolResult:
    """Create a business record for a customer."""
    return wrap(
        get_client().create_business(customer_id, business_name, business_type=business_type or None)
    )


@mcp.tool()
def get_business_for_customer(customer_id: str) -> ToolResult:
    """Get the business record for a customer."""
    return wrap(get_client().get_business_for_customer(customer_id))


@mcp.tool()
def account_owner_match(
    customer_id: str,
    account_id: str,
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    phone: str = "",
) -> ToolResult:
    """Match provided identity details against account owner records."""
    return wrap(
        get_client().account_owner_match(
            customer_id,
            account_id,
            first_name=first_name,
            last_name=last_name,
            email=email or None,
            phone=phone or None,
        )
    )


@mcp.tool()
def enrich_transactions(transactions: list[dict]) -> ToolResult:
    """Enrich a list of raw transactions with categorization/merchant data."""
    return wrap(get_client().enrich_transactions(transactions))


@mcp.tool()
def get_deposit_switches(customer_id: str) -> ToolResult:
    """List direct-deposit switches for a customer."""
    return wrap(get_client().get_deposit_switches(customer_id))


@mcp.tool()
def get_bill_pay_switches(customer_id: str) -> ToolResult:
    """List bill-pay switches for a customer."""
    return wrap(get_client().get_bill_pay_switches(customer_id))


# --------------------------------------------------------------------------- #
# Sandbox testing utility (headless account linking — no Connect browser flow)
# --------------------------------------------------------------------------- #
@mcp.tool()
def link_testing_accounts(
    customer_id: str,
    institution_id: str = "101732",
    username: str = "demo",
    password: str = "go",
) -> ToolResult:
    """Link FinBank test accounts to a *testing* customer without hosted Connect.

    Sandbox only. Defaults link institution 101732 (FinBank) with demo/go,
    which returns 8 accounts and requires no MFA.
    """
    from .testing_helpers import MfaChallengeError, link_finbank_accounts

    try:
        return wrap(
            link_finbank_accounts(
                get_client(), customer_id, institution_id, username, password
            )
        )
    except MfaChallengeError as e:
        return ToolResult(ok=False, status_code=203, data=None, error=str(e))


@mcp.tool()
def list_finbank_profiles() -> ToolResult:
    """List the verified FinBank sandbox test profiles for headless linking."""
    from .finbank_profiles import profiles_as_dicts

    return ToolResult(ok=True, status_code=200, data={"profiles": profiles_as_dicts()})


@mcp.tool()
def run_happy_path(profile_key: str = "finbank_demo") -> ToolResult:
    """Run a full sandbox happy path end-to-end and return every step.

    Steps: create testing customer -> link FinBank accounts -> list accounts ->
    fetch transactions. Sandbox only; uses headless linking (no browser).
    """
    from .finbank_profiles import profile_by_key
    from .testing_helpers import MfaChallengeError, link_finbank_accounts

    client = get_client()
    steps: list[dict] = []

    def record(name: str, result: ToolResult) -> ToolResult:
        steps.append(
            {
                "step": name,
                "ok": result.ok,
                "status_code": result.status_code,
                "error": result.error,
            }
        )
        return result

    try:
        profile = profile_by_key(profile_key)
    except KeyError as e:
        return ToolResult(ok=False, status_code=400, data=None, error=str(e))

    import time

    created = record(
        "create_testing_customer",
        wrap(client.add_testing_customer(f"happy_{int(time.time())}")),
    )
    if not created.ok:
        return ToolResult(ok=False, status_code=created.status_code,
                          data={"steps": steps}, error="Failed to create customer")
    customer_id = str((created.data or {}).get("id"))

    try:
        linked = record(
            "link_testing_accounts",
            wrap(
                link_finbank_accounts(
                    client, customer_id, profile.institution_id,
                    profile.username, profile.password,
                )
            ),
        )
    except MfaChallengeError as e:
        steps.append({"step": "link_testing_accounts", "ok": False,
                      "status_code": 203, "error": str(e)})
        return ToolResult(ok=False, status_code=203,
                          data={"customer_id": customer_id, "steps": steps}, error=str(e))

    accounts = record("get_customer_accounts", wrap(client.get_customer_accounts(customer_id)))
    account_list = (accounts.data or {}).get("accounts", []) if accounts.data else []

    # Testing accounts have no transactions until a historic load is requested.
    historic_ok = True
    for account in account_list:
        _, hs = client.load_historic_transactions(customer_id, str(account.get("id")))
        historic_ok = historic_ok and hs < 400
    steps.append({"step": "load_historic_transactions", "ok": historic_ok,
                  "status_code": 204 if historic_ok else 502,
                  "error": None if historic_ok else "One or more accounts failed to load history"})

    now = int(time.time())
    txns = record(
        "get_customer_transactions",
        wrap(client.get_customer_transactions(customer_id, now - 730 * 24 * 3600, now)),
    )

    txn_list = (txns.data or {}).get("transactions", []) if txns.data else []
    all_ok = all(s["ok"] for s in steps)
    return ToolResult(
        ok=all_ok,
        status_code=200 if all_ok else 502,
        data={
            "customer_id": customer_id,
            "profile": profile.key,
            "institution": profile.institution_name,
            "account_count": len(account_list),
            "transaction_count": len(txn_list),
            "steps": steps,
        },
        error=None if all_ok else "One or more steps failed",
    )
