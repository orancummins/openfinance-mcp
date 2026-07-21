"""
Mastercard Open Finance API Client
Handles authentication and API calls to the Open Banking APIs
"""
import base64
import time
from typing import Any

import requests


class OpenFinanceClient:
    """Client for Mastercard Open Finance (US Open Banking) APIs"""

    def __init__(self, partner_id: str, partner_secret: str, app_key: str,
                 base_url: str = "https://api.finicity.com"):
        self.partner_id = partner_id
        self.partner_secret = partner_secret
        self.app_key = app_key
        self.base_url = base_url
        self._token: str | None = None
        self._token_timestamp: float = 0
        self._last_request: dict | None = None
        self._last_response: dict | None = None

    @property
    def last_request(self) -> dict | None:
        """Get the last API request details"""
        return self._last_request

    @property
    def last_response(self) -> dict | None:
        """Get the last API response details"""
        return self._last_response

    def _get_token(self) -> str:
        """Get or refresh the access token"""
        # Token valid for 2 hours, refresh after 90 minutes
        if self._token and (time.time() - self._token_timestamp) < 5400:
            return self._token

        url = f"{self.base_url}/aggregation/v2/partners/authentication"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Finicity-App-Key": self.app_key,
            "User-Agent": "MastercardOpenBankingDemo/1.0"
        }
        payload = {
            "partnerId": self.partner_id,
            "partnerSecret": self.partner_secret
        }

        # Store request details (mask secret)
        self._last_request = {
            "method": "POST",
            "url": url,
            "headers": {**headers},
            "body": {**payload, "partnerSecret": "********"}
        }

        response = requests.post(url, headers=headers, json=payload)
        self._last_response = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.json() if response.ok else response.text
        }

        if response.ok:
            self._token = response.json().get("token")
            self._token_timestamp = time.time()
            return self._token
        else:
            raise Exception(f"Failed to get token: {response.text}")

    def _make_request(self, method: str, endpoint: str,
                      data: dict | None = None,
                      params: dict | None = None) -> tuple[dict, int]:
        """Make an authenticated API request"""
        token = self._get_token()
        url = f"{self.base_url}{endpoint}"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Finicity-App-Key": self.app_key,
            "Finicity-App-Token": token,
            "User-Agent": "MastercardOpenBankingDemo/1.0"
        }

        # Store request details
        self._last_request = {
            "method": method,
            "url": url,
            "headers": {**headers, "Finicity-App-Token": token[:10] + "..."},
            "body": data,
            "params": params
        }

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            params=params
        )

        try:
            response_body = response.json()
        except Exception:
            response_body = response.text

        # Store response details
        self._last_response = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_body
        }

        return response_body, response.status_code

    # ==================== Authentication ====================

    def create_token(self) -> tuple[dict, int]:
        """Create a new access token"""
        self._token = None  # Force refresh
        self._get_token()
        return {"token": self._token[:10] + "...", "message": "Token created successfully"}, 200

    # ==================== Customers ====================

    def add_testing_customer(self, username: str) -> tuple[dict, int]:
        """Create a testing customer"""
        return self._make_request(
            "POST",
            "/aggregation/v2/customers/testing",
            data={"username": username}
        )

    def add_customer(self, username: str, first_name: str = "", last_name: str = "") -> tuple[dict, int]:
        """Create an active (billable) customer"""
        data = {"username": username}
        if first_name:
            data["firstName"] = first_name
        if last_name:
            data["lastName"] = last_name
        return self._make_request("POST", "/aggregation/v2/customers/active", data=data)

    def get_customers(self, search: str = "", start: int = 1, limit: int = 25) -> tuple[dict, int]:
        """Get all customers"""
        params = {"start": start, "limit": limit}
        if search:
            params["search"] = search
        return self._make_request("GET", "/aggregation/v1/customers", params=params)

    def get_customer(self, customer_id: str) -> tuple[dict, int]:
        """Get a customer by ID"""
        return self._make_request("GET", f"/aggregation/v1/customers/{customer_id}")

    def update_customer(self, customer_id: str, first_name: str = None,
                        last_name: str = None, email: str = None) -> tuple[dict, int]:
        """Update a customer's profile (PUT /aggregation/v1/customers/{id})"""
        data: dict[str, Any] = {}
        if first_name:
            data["firstName"] = first_name
        if last_name:
            data["lastName"] = last_name
        if email:
            data["email"] = email
        if not data:
            data["firstName"] = "Test"
        return self._make_request("PUT", f"/aggregation/v1/customers/{customer_id}", data=data)

    def delete_customer(self, customer_id: str) -> tuple[dict, int]:
        """Delete a customer"""
        return self._make_request("DELETE", f"/aggregation/v1/customers/{customer_id}")

    # ==================== Data Connect ====================

    def generate_connect_url(self, customer_id: str, partner_id: str = None,
                             experience: str = None) -> tuple[dict, int]:
        """Generate a Data Connect URL for account linking"""
        data = {
            "partnerId": partner_id or self.partner_id,
            "customerId": customer_id
        }
        if experience:
            data["experience"] = experience
        return self._make_request("POST", "/connect/v2/generate", data=data)

    def generate_lite_connect_url(self, customer_id: str, institution_id: str) -> tuple[dict, int]:
        """Generate a Lite Data Connect URL"""
        data = {
            "partnerId": self.partner_id,
            "customerId": customer_id,
            "institutionId": institution_id
        }
        return self._make_request("POST", "/connect/v2/generate/lite", data=data)

    def generate_fix_connect_url(self, customer_id: str, institution_login_id: str) -> tuple[dict, int]:
        """Generate a Fix Data Connect URL for reconnection"""
        data = {
            "partnerId": self.partner_id,
            "customerId": customer_id,
            "institutionLoginId": institution_login_id
        }
        return self._make_request("POST", "/connect/v2/generate/fix", data=data)

    # ==================== Accounts ====================

    def get_customer_accounts(self, customer_id: str) -> tuple[dict, int]:
        """Get all accounts for a customer"""
        return self._make_request("GET", f"/aggregation/v1/customers/{customer_id}/accounts")

    def get_customer_account(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Get a specific account"""
        return self._make_request("GET", f"/aggregation/v2/customers/{customer_id}/accounts/{account_id}")

    def refresh_customer_accounts(self, customer_id: str) -> tuple[dict, int]:
        """Refresh all accounts for a customer"""
        return self._make_request("POST", f"/aggregation/v1/customers/{customer_id}/accounts", data={})

    def get_account_owner(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Get account owner information"""
        return self._make_request(
            "GET",
            f"/aggregation/v1/customers/{customer_id}/accounts/{account_id}/owner"
        )

    def get_account_owner_details(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Get detailed account owner information"""
        return self._make_request(
            "GET",
            f"/aggregation/v3/customers/{customer_id}/accounts/{account_id}/owner"
        )

    def delete_customer_account(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Delete access to a customer account"""
        return self._make_request(
            "DELETE",
            f"/aggregation/v1/customers/{customer_id}/accounts/{account_id}"
        )

    # ==================== Transactions ====================

    def get_customer_transactions(self, customer_id: str, from_date: int, to_date: int,
                                  start: int = 1, limit: int = 1000,
                                  include_pending: bool = True) -> tuple[dict, int]:
        """Get all transactions for a customer"""
        params = {
            "fromDate": from_date,
            "toDate": to_date,
            "start": start,
            "limit": limit,
            "includePending": str(include_pending).lower()
        }
        return self._make_request(
            "GET",
            f"/aggregation/v3/customers/{customer_id}/transactions",
            params=params
        )

    def get_account_transactions(self, customer_id: str, account_id: str,
                                 from_date: int, to_date: int,
                                 start: int = 1, limit: int = 1000) -> tuple[dict, int]:
        """Get transactions for a specific account"""
        params = {
            "fromDate": from_date,
            "toDate": to_date,
            "start": start,
            "limit": limit
        }
        return self._make_request(
            "GET",
            f"/aggregation/v4/customers/{customer_id}/accounts/{account_id}/transactions",
            params=params
        )

    def get_recurring_transactions(self, customer_id: str, account_ids: list = None) -> tuple[dict, int]:
        """Get recurring transactions for a customer"""
        data = {}
        if account_ids:
            data["accountIds"] = account_ids
        return self._make_request(
            "POST",
            f"/aggregation/customers/{customer_id}/recurring-transactions",
            data=data
        )

    def load_historic_transactions(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Load historic transactions for an account (up to 24 months)"""
        return self._make_request(
            "POST",
            f"/aggregation/v1/customers/{customer_id}/accounts/{account_id}/transactions/historic",
            data={}
        )

    # ==================== Institutions ====================

    def get_institutions(self, search: str = "", start: int = 1, limit: int = 25) -> tuple[dict, int]:
        """Search for financial institutions"""
        params = {"start": start, "limit": limit}
        if search:
            params["search"] = search
        return self._make_request("GET", "/institution/v2/institutions", params=params)

    def get_institution(self, institution_id: str) -> tuple[dict, int]:
        """Get institution details"""
        return self._make_request("GET", f"/institution/v2/institutions/{institution_id}")

    def get_institution_branding(self, institution_id: str) -> tuple[dict, int]:
        """Get institution branding assets"""
        return self._make_request("GET", f"/institution/v2/institutions/{institution_id}/branding")

    def get_certified_institutions(self, search: str = "", start: int = 1,
                                   limit: int = 25) -> tuple[dict, int]:
        """Get certified institutions"""
        params = {"start": start, "limit": limit}
        if search:
            params["search"] = search
        return self._make_request("GET", "/institution/v2/certifiedInstitutions", params=params)

    def get_institutions_by_routing_number(self, routing_number: str) -> tuple[dict, int]:
        """Get institutions by routing number"""
        return self._make_request(
            "GET",
            f"/institution/v1/institutions/routingNumber/{routing_number}"
        )

    # ==================== Consumers ====================

    def create_consumer(self, customer_id: str, first_name: str, last_name: str,
                        email: str = "", phone: str = "", ssn: str = "",
                        address: str = "123 Main St", city: str = "Salt Lake City",
                        state: str = "UT", zip_code: str = "84101") -> tuple[dict, int]:
        """Create a consumer for report generation"""
        data: dict = {
            "firstName": first_name,
            "lastName": last_name,
            "address": address,
            "city": city,
            "state": state,
            "zip": zip_code,
        }
        # API requires: either ssn or birthday; either phone or email
        if ssn:
            data["ssn"] = ssn
        else:
            data["birthday"] = {"year": 1990, "month": 1, "dayOfMonth": 15}
        if phone:
            data["phone"] = phone
        if email:
            data["email"] = email
        if not phone and not email:
            data["email"] = "consumer@example.com"
        return self._make_request(
            "POST",
            f"/decisioning/v1/customers/{customer_id}/consumer",
            data=data
        )

    def get_consumer(self, consumer_id: str) -> tuple[dict, int]:
        """Get consumer details"""
        return self._make_request("GET", f"/decisioning/v1/consumers/{consumer_id}")

    def get_consumer_for_customer(self, customer_id: str) -> tuple[dict, int]:
        """Get consumer for a customer"""
        return self._make_request("GET", f"/decisioning/v1/customers/{customer_id}/consumer")

    # ==================== Reports ====================

    def generate_voa_report(self, customer_id: str, account_ids: list = None,
                            from_date: int = None) -> tuple[dict, int]:
        """Generate Verification of Assets report"""
        data = {}
        if account_ids:
            data["accountIds"] = account_ids
        if from_date:
            data["fromDate"] = from_date
        return self._make_request(
            "POST",
            f"/decisioning/v2/customers/{customer_id}/voa",
            data=data
        )

    def generate_voi_report(self, customer_id: str, account_ids: list = None) -> tuple[dict, int]:
        """Generate Verification of Income report"""
        data = {}
        if account_ids:
            data["accountIds"] = account_ids
        return self._make_request(
            "POST",
            f"/decisioning/v2/customers/{customer_id}/voi",
            data=data
        )

    def generate_voai_report(self, customer_id: str, account_ids: list = None,
                             from_date: int = None) -> tuple[dict, int]:
        """Generate VOA with Income report"""
        data = {}
        if account_ids:
            data["accountIds"] = account_ids
        if from_date:
            data["fromDate"] = from_date
        return self._make_request(
            "POST",
            f"/decisioning/v2/customers/{customer_id}/voaHistory",
            data=data
        )

    def generate_cash_flow_personal_report(self, customer_id: str,
                                           account_ids: list = None) -> tuple[dict, int]:
        """Generate Cash Flow Report (Personal)"""
        data = {}
        if account_ids:
            data["accountIds"] = account_ids
        return self._make_request(
            "POST",
            f"/decisioning/v2/customers/{customer_id}/cashFlowPersonal",
            data=data
        )

    def generate_cash_flow_business_report(self, customer_id: str,
                                           account_ids: list = None) -> tuple[dict, int]:
        """Generate Cash Flow Report (Business)"""
        data = {}
        if account_ids:
            data["accountIds"] = account_ids
        return self._make_request(
            "POST",
            f"/decisioning/v2/customers/{customer_id}/cashFlowBusiness",
            data=data
        )

    def generate_transactions_report(self, customer_id: str, from_date: int, to_date: int,
                                     account_ids: list = None) -> tuple[dict, int]:
        """Generate Transactions Report"""
        data = {
            "fromDate": from_date,
            "toDate": to_date
        }
        if account_ids:
            data["accountIds"] = account_ids
        return self._make_request(
            "POST",
            f"/decisioning/v2/customers/{customer_id}/transactions",
            data=data
        )

    def generate_balance_analytics_report(self, customer_id: str,
                                          user_type: str = "personal",
                                          account_ids: list = None) -> tuple[dict, int]:
        """Generate Balance Analytics Report"""
        data = {
            "analyticsReportData": {
                "forCraPurpose": False
            }
        }
        if account_ids:
            data["accountIds"] = " ".join(account_ids)  # API expects whitespace-separated string
        return self._make_request(
            "POST",
            f"/decisioning/v2/customers/{customer_id}/reports/balance-analytics/userTypes/{user_type}",
            data=data
        )

    def generate_cashflow_analytics_report(self, customer_id: str,
                                           user_type: str = "personal",
                                           account_ids: list = None) -> tuple[dict, int]:
        """Generate Cash Flow Analytics Report"""
        data = {
            "analyticsReportData": {
                "forCraPurpose": False
            }
        }
        if account_ids:
            data["accountIds"] = " ".join(account_ids)  # API expects whitespace-separated string
        return self._make_request(
            "POST",
            f"/decisioning/v2/customers/{customer_id}/reports/cashflow-analytics/userTypes/{user_type}",
            data=data
        )

    def get_report(self, report_id: str, purpose_code: str = "3F") -> tuple[dict, int]:
        """Get a report by ID"""
        return self._make_request(
            "POST",
            f"/decisioning/v3/reports/{report_id}",
            data={"purpose": purpose_code},
            params={"purpose": purpose_code},
        )

    def get_report_by_customer(self, customer_id: str, report_id: str, purpose_code: str = "3F") -> tuple[dict, int]:
        """Get a report by customer and report ID"""
        return self._make_request(
            "GET",
            f"/decisioning/v3/customers/{customer_id}/reports/{report_id}",
            params={"purpose": purpose_code},
        )

    def get_reports_by_customer(self, customer_id: str) -> tuple[dict, int]:
        """Get all reports for a customer"""
        return self._make_request("GET", f"/decisioning/v1/customers/{customer_id}/reports")

    # ==================== Payment Success Indicators ====================

    def generate_payment_success_indicators(self, customer_id: str, account_id: str,
                                            amount: float) -> tuple[dict, int]:
        """Generate Non-FCRA Payment Success Indicators"""
        from datetime import datetime, timedelta
        settle_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        data = {
            "transaction": {
                "settleByDate": settle_date,
                "amount": amount
            }
        }
        return self._make_request(
            "POST",
            f"/payments/customers/{customer_id}/accounts/{account_id}/payment-success-indicators",
            data=data
        )

    def get_payment_success_indicators(self, customer_id: str, account_id: str,
                                       pay_request_id: str) -> tuple[dict, int]:
        """Get Payment Success Indicators result"""
        return self._make_request(
            "GET",
            f"/payments/customers/{customer_id}/accounts/{account_id}/payment-success-indicators/{pay_request_id}"
        )

    def generate_fcra_payment_success_indicators(self, customer_id: str, account_id: str,
                                                  amount: float, purpose: str = "1P",
                                                  user_email: str = "user@example.com") -> tuple[dict, int]:
        """Generate FCRA Payment Success Indicators"""
        from datetime import datetime, timedelta
        settle_date = (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d')
        data = {
            "transaction": {
                "settleByDate": settle_date,
                "amount": amount
            },
            "user": {
                "email": user_email
            }
        }
        return self._make_request(
            "POST",
            f"/payments/customers/{customer_id}/accounts/{account_id}/fcra-payment-success-indicators",
            params={"purpose": purpose},
            data=data
        )

    def get_fcra_payment_success_indicators(self, customer_id: str, account_id: str,
                                             pay_request_id: str) -> tuple[dict, int]:
        """Get FCRA Payment Success Indicators result"""
        return self._make_request(
            "GET",
            f"/payments/customers/{customer_id}/accounts/{account_id}/fcra-payment-success-indicators/{pay_request_id}"
        )

    # ==================== ACH Details ====================

    def get_account_ach_details(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Get ACH routing and account details"""
        return self._make_request(
            "GET",
            f"/aggregation/v1/customers/{customer_id}/accounts/{account_id}/details"
        )

    def get_account_payment_details(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Get ACH details with RTP/FedNow support info"""
        return self._make_request(
            "GET",
            f"/aggregation/v3/customers/{customer_id}/accounts/{account_id}/details"
        )

    # ==================== Account Balance ====================

    def get_available_balance(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Get real-time available balance"""
        return self._make_request(
            "GET",
            f"/aggregation/v1/customers/{customer_id}/accounts/{account_id}/availableBalance/live"
        )

    # ==================== Micro Deposits ====================

    def initiate_micro_deposits(self, customer_id: str, receiver: dict,
                                callback_url: str = None) -> tuple[dict, int]:
        """Initiate micro deposit verification"""
        data = {"receiver": receiver}
        if callback_url:
            data["callbackUrl"] = callback_url
        return self._make_request(
            "POST",
            f"/microentry/v1/customers/{customer_id}",
            data=data
        )

    def verify_micro_deposits(self, customer_id: str, account_id: str,
                              amounts: list) -> tuple[dict, int]:
        """Verify micro deposit amounts"""
        data = {"amounts": amounts}
        return self._make_request(
            "POST",
            f"/microentry/v1/customers/{customer_id}/accounts/{account_id}/amounts",
            data=data
        )

    def get_micro_deposit_details(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Get micro deposit details"""
        return self._make_request(
            "GET",
            f"/microentry/v1/customers/{customer_id}/accounts/{account_id}"
        )

    # ==================== Account Statements ====================

    def get_account_statement(self, customer_id: str, account_id: str,
                              index: int = 1) -> tuple[dict, int]:
        """Get account statement PDF, returned as base64 in the data dict"""
        token = self._get_token()
        url = f"{self.base_url}/aggregation/v1/customers/{customer_id}/accounts/{account_id}/statement"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/octet-stream",
            "Finicity-App-Key": self.app_key,
            "Finicity-App-Token": token,
            "User-Agent": "MastercardOpenBankingDemo/1.0"
        }
        req_params = {"index": index}
        self._last_request = {
            "method": "GET",
            "url": url,
            "headers": {**headers, "Finicity-App-Token": token[:10] + "..."},
            "body": None,
            "params": req_params,
        }
        response = requests.get(url, headers=headers, params=req_params)
        content_type = response.headers.get("Content-Type", "")
        if response.status_code < 400 and response.content and "pdf" in content_type:
            b64 = base64.b64encode(response.content).decode("ascii")
            body: dict[str, Any] = {"pdf_base64": b64, "size_bytes": len(response.content)}
            self._last_response = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": {"message": f"PDF received ({len(response.content):,} bytes) — use viewer below"},
            }
        else:
            try:
                body = response.json()
            except Exception:
                body = {"error": response.text}
            self._last_response = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": body,
            }
        return body, response.status_code

    def get_loan_payment_details(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Get loan payment details for a loan-type account"""
        return self._make_request(
            "GET",
            f"/aggregation/v2/customers/{customer_id}/accounts/{account_id}/loanDetails"
        )

    # ==================== Business Services ====================

    def create_business(self, customer_id: str, business_name: str,
                        personally_liable: bool = True,
                        address_line1: str = "123 Main St",
                        city: str = "Salt Lake City", state: str = "UT",
                        country: str = "US", postal_code: str = "84101",
                        phone_country_code: str = "1", phone_no: str = "2025550100",
                        email: str = None, business_type: str = None) -> tuple[dict, int]:
        """Create a business record for a customer"""
        data: dict[str, Any] = {
            "name": business_name,
            "personallyLiable": personally_liable,
            "address": {
                "addressLine1": address_line1,
                "city": city,
                "state": state,
                "country": country,
                "postalCode": postal_code,
            },
            "phoneNumber": {
                "countryCode": phone_country_code,
                "phoneNo": phone_no,
            },
        }
        if email:
            data["email"] = email
        if business_type:
            data["type"] = business_type
        return self._make_request(
            "POST",
            f"/business-services/customers/{customer_id}/businesses",
            data=data
        )

    def get_business_for_customer(self, customer_id: str) -> tuple[dict, int]:
        """Get business details for a customer"""
        return self._make_request(
            "GET",
            f"/business-services/customers/{customer_id}/businesses"
        )

    # ==================== Account Owner Matching ====================

    def account_owner_match(self, customer_id: str, account_id: str,
                            first_name: str = "", last_name: str = "",
                            address: dict = None,
                            email: str = None, phone: str = None) -> tuple[dict, int]:
        """Match account owner information"""
        data: dict[str, Any] = {
            "name": {"firstName": first_name, "lastName": last_name}
        }
        if address:
            data["address"] = address
        if email:
            data["email"] = email
        if phone:
            data["phone"] = phone
        return self._make_request(
            "POST",
            f"/account-owner-verification-matchings/customers/{customer_id}/accounts/{account_id}",
            data=data
        )

    # ==================== TxPush ====================

    def subscribe_to_txpush(self, customer_id: str, account_id: str,
                            callback_url: str) -> tuple[dict, int]:
        """Subscribe to TxPush notifications"""
        data = {"callbackUrl": callback_url}
        return self._make_request(
            "POST",
            f"/aggregation/v1/customers/{customer_id}/accounts/{account_id}/txpush",
            data=data
        )

    def disable_txpush(self, customer_id: str, account_id: str) -> tuple[dict, int]:
        """Disable TxPush notifications"""
        return self._make_request(
            "DELETE",
            f"/aggregation/v1/customers/{customer_id}/accounts/{account_id}/txpush"
        )

    # ==================== Data Enrichment ====================

    def enrich_transactions(self, transactions: list) -> tuple[dict, int]:
        """Enrich transactions with categorization"""
        data = {"transactions": transactions}
        return self._make_request("POST", "/data-enrichment/transactions", data=data)

    # ==================== Transfer Services ====================

    def get_deposit_switches(self, customer_id: str) -> tuple[dict, int]:
        """Get deposit switches for a customer"""
        return self._make_request(
            "GET",
            f"/transfer/customers/{customer_id}/deposit-switches"
        )

    def get_bill_pay_switches(self, customer_id: str) -> tuple[dict, int]:
        """Get bill pay switches for a customer"""
        return self._make_request(
            "GET",
            f"/transfer/customers/{customer_id}/bill-pay-switches"
        )


# Demo data for testing without credentials
DEMO_CUSTOMERS = [
    {"id": "6012118342", "username": "demo_customer_1", "createdDate": 1607450357, "type": "testing"},
    {"id": "6012118343", "username": "demo_customer_2", "createdDate": 1607450400, "type": "testing"}
]

DEMO_ACCOUNTS = [
    {
        "id": "6020488416",
        "number": "111111",
        "name": "Checking",
        "balance": 9357.24,
        "type": "checking",
        "status": "active",
        "currency": "USD",
        "institutionId": "102105",
        "institutionName": "FinBank"
    },
    {
        "id": "6020488414",
        "number": "22222203",
        "name": "Savings",
        "balance": 22327.30,
        "type": "savings",
        "status": "active",
        "currency": "USD",
        "institutionId": "102105",
        "institutionName": "FinBank"
    },
    {
        "id": "6020488412",
        "number": "101010",
        "name": "Personal Investments",
        "balance": 100000.00,
        "type": "investment",
        "status": "active",
        "currency": "USD",
        "institutionId": "102105",
        "institutionName": "FinBank"
    },
    {
        "id": "6020488411",
        "number": "121212",
        "name": "My 401k",
        "balance": 265000.00,
        "type": "investmentTaxDeferred",
        "status": "active",
        "currency": "USD",
        "institutionId": "102105",
        "institutionName": "FinBank"
    }
]

DEMO_TRANSACTIONS = [
    {"id": 1, "amount": -45.99, "description": "AMAZON.COM", "category": "Shopping", "date": "2026-02-15", "type": "debit"},
    {"id": 2, "amount": 2500.00, "description": "PAYROLL DEPOSIT", "category": "Paycheck", "date": "2026-02-14", "type": "credit"},
    {"id": 3, "amount": -89.50, "description": "WHOLE FOODS MARKET", "category": "Groceries", "date": "2026-02-13", "type": "debit"},
    {"id": 4, "amount": -150.00, "description": "ELECTRIC BILL", "category": "Utilities", "date": "2026-02-12", "type": "debit"},
    {"id": 5, "amount": -12.99, "description": "NETFLIX", "category": "Entertainment", "date": "2026-02-11", "type": "debit"},
    {"id": 6, "amount": -65.00, "description": "GAS STATION", "category": "Transportation", "date": "2026-02-10", "type": "debit"},
    {"id": 7, "amount": -234.50, "description": "TARGET", "category": "Shopping", "date": "2026-02-09", "type": "debit"},
    {"id": 8, "amount": 500.00, "description": "TRANSFER FROM SAVINGS", "category": "Transfer", "date": "2026-02-08", "type": "credit"},
    {"id": 9, "amount": -42.00, "description": "UBER EATS", "category": "Food & Dining", "date": "2026-02-07", "type": "debit"},
    {"id": 10, "amount": -1200.00, "description": "RENT PAYMENT", "category": "Housing", "date": "2026-02-01", "type": "debit"}
]

DEMO_INSTITUTIONS = [
    {"id": "102105", "name": "FinBank Profiles - A", "urlHomeApp": "https://finbank.com", "oauthEnabled": True},
    {"id": "102224", "name": "Chase", "urlHomeApp": "https://chase.com", "oauthEnabled": True},
    {"id": "102233", "name": "Bank of America", "urlHomeApp": "https://bankofamerica.com", "oauthEnabled": True},
    {"id": "102235", "name": "Wells Fargo", "urlHomeApp": "https://wellsfargo.com", "oauthEnabled": True},
    {"id": "102247", "name": "Citibank", "urlHomeApp": "https://citi.com", "oauthEnabled": True}
]
