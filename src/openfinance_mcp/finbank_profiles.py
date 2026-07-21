"""FinBank sandbox scenario matrix.

Verified live against the Finicity sandbox. Each profile links headlessly via
``link_finbank_accounts`` (the v1 addall endpoint) with no MFA, so they can be
used in automated tests and the console happy-path runner.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FinBankProfile:
    key: str
    institution_id: str
    institution_name: str
    username: str
    password: str
    expected_min_accounts: int
    notes: str


PROFILES: list[FinBankProfile] = [
    FinBankProfile(
        key="finbank_demo",
        institution_id="101732",
        institution_name="FinBank",
        username="demo",
        password="go",
        expected_min_accounts=8,
        notes="Classic no-MFA profile; checking, savings, loans, cards, investments.",
    ),
    FinBankProfile(
        key="finbank_profiles_a",
        institution_id="102105",
        institution_name="FinBank Profiles - A",
        username="profile_02",
        password="profile_02",
        expected_min_accounts=4,
        notes="Profiles bank; includes a 401K/investment account.",
    ),
]

DEFAULT_PROFILE = PROFILES[0]


def profile_by_key(key: str) -> FinBankProfile:
    for p in PROFILES:
        if p.key == key:
            return p
    raise KeyError(f"Unknown FinBank profile: {key!r}")


def profiles_as_dicts() -> list[dict]:
    return [p.__dict__ for p in PROFILES]
