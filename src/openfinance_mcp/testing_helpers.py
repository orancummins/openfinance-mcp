"""Sandbox-only helpers for headless account linking (FinBank test profiles).

These use Finicity's testing ``addall`` endpoint to link accounts without the
hosted Connect browser flow. They are intended for automated demos and tests
against the sandbox only — never a path for real end-user credentials.

Verified working combinations (Finicity sandbox):
  * institution 101732 (FinBank)             demo / go            -> 8 accounts
  * institution 102105 (FinBank Profiles-A)  profile_02/profile_02 -> 4 accounts
"""
from __future__ import annotations

from typing import Any

from .finicity_client import OpenFinanceClient


class MfaChallengeError(RuntimeError):
    """Raised when the sandbox returns a 203 MFA challenge we can't auto-answer."""


def _build_credentials(client: OpenFinanceClient, institution_id: str,
                       username: str, password: str) -> list[dict[str, Any]]:
    login_form, status = client._make_request(
        "GET", f"/institution/v2/institutions/{institution_id}/loginForm"
    )
    if status >= 400 or not isinstance(login_form, dict):
        raise RuntimeError(f"Could not load login form for {institution_id}: {login_form}")
    creds: list[dict[str, Any]] = []
    for field in login_form.get("loginForms", []):
        name = (field.get("name") or "").lower()
        is_user = "user" in name or "id" in name
        creds.append(
            {
                "id": field.get("id"),
                "name": field.get("name"),
                "value": username if is_user else password,
            }
        )
    if not creds:
        raise RuntimeError(f"Institution {institution_id} exposed no login fields.")
    return creds


def link_finbank_accounts(
    client: OpenFinanceClient,
    customer_id: str,
    institution_id: str = "101732",
    username: str = "demo",
    password: str = "go",
) -> tuple[dict, int]:
    """Link all accounts for a testing customer via the v1 addall endpoint.

    Returns the raw ``(body, status)`` from Finicity. Raises MfaChallengeError
    on a 203 challenge (use a non-MFA profile like demo/go for automation).
    """
    creds = _build_credentials(client, institution_id, username, password)
    body, status = client._make_request(
        "POST",
        f"/aggregation/v1/customers/{customer_id}/institutions/{institution_id}/accounts/addall",
        data={"credentials": creds},
    )
    if status == 203:
        raise MfaChallengeError(
            "Sandbox returned an MFA challenge; use a non-MFA profile "
            "(e.g. institution 101732 with demo/go)."
        )
    return body, status
