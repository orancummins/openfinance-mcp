"""Resolved spec decisions + remaining open questions.

The three questions that were previously open have now been confirmed against
the working Finicity client used in production by Vima
(``apis/open_finance/client.py``). They are recorded here as ``confirmed`` and
consumed by the client wrappers so behaviour is centralised and overridable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SpecDecision:
    id: str
    question: str
    answer: str
    status: str  # "confirmed" | "default"
    source: str
    env_override: str | None = None


DECISIONS: list[SpecDecision] = [
    SpecDecision(
        id="psi_path",
        question="PSI endpoint path + body shape (nested transaction?).",
        answer=(
            "POST /payments/customers/{customerId}/accounts/{accountId}/"
            "payment-success-indicators with body "
            '{"transaction": {"settleByDate": "YYYY-MM-DD", "amount": <float>}}'
        ),
        status="confirmed",
        source="Vima apis/open_finance/client.py::generate_payment_success_indicators",
    ),
    SpecDecision(
        id="voai_slug",
        question="VOA-with-income report slug (voaHistory vs voaWithIncome).",
        answer="voaHistory -> POST /decisioning/v2/customers/{id}/voaHistory",
        status="confirmed",
        source="Vima apis/open_finance/client.py::generate_voai_report",
        env_override="OPEN_FINANCE_VOAI_SLUG",
    ),
    SpecDecision(
        id="txpush_body",
        question="TxPUSH subscribe body field names.",
        answer=(
            "POST /aggregation/v1/customers/{customerId}/accounts/{accountId}/"
            'txpush with body {"callbackUrl": <url>} (no "type" field)'
        ),
        status="confirmed",
        source="Vima apis/open_finance/client.py::subscribe_to_txpush",
    ),
    SpecDecision(
        id="psi_settle_days",
        question="Default settle-by horizon when caller omits settleByDate.",
        answer="now + 3 days (overridable)",
        status="default",
        source="Vima client default; verify against your risk policy",
        env_override="OPEN_FINANCE_PSI_SETTLE_DAYS",
    ),
]

# Resolved runtime values (env can override the non-hard-coded ones).
VOAI_SLUG = os.getenv("OPEN_FINANCE_VOAI_SLUG", "voaHistory")
PSI_SETTLE_DAYS = int(os.getenv("OPEN_FINANCE_PSI_SETTLE_DAYS", "3"))


def decisions_as_dicts() -> list[dict]:
    return [d.__dict__ for d in DECISIONS]
