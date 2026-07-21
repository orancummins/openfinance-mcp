"""Credential + runtime settings loader.

Resolution order for each ``OPEN_FINANCE_*`` value:

1. The process environment (``os.environ``).
2. A dotenv file pointed to by ``OPENFINANCE_MCP_ENV_FILE``.
3. The sibling Vima repo's ``config/.env`` (auto-discovered), so the MCP can
   run "for real" against the same valid sandbox credentials you already have
   provisioned — without copying secrets into this repo.

No secret values are ever written to disk by this module.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

# Semantic field -> environment variable name (US / Finicity, OAuth2).
_ENV_KEYS = {
    "partner_id": "OPEN_FINANCE_PARTNER_ID",
    "partner_secret": "OPEN_FINANCE_PARTNER_SECRET",
    "app_key": "OPEN_FINANCE_APP_KEY",
    "api_base_url": "OPEN_FINANCE_API_BASE_URL",
}

_PLACEHOLDERS = {
    "",
    "your_partner_id_here",
    "your_partner_secret_here",
    "your_app_key_here",
}

_DEFAULT_BASE_URL = "https://api.finicity.com"


def _candidate_env_files() -> list[Path]:
    """Return dotenv paths to search, nearest/most-explicit first."""
    candidates: list[Path] = []
    explicit = os.environ.get("OPENFINANCE_MCP_ENV_FILE")
    if explicit:
        candidates.append(Path(explicit).expanduser())

    # A local .env in this repo, if present.
    here = Path(__file__).resolve()
    repo_root = here.parents[3]  # .../openfinance-mcp
    candidates.append(repo_root / ".env")

    # The sibling Vima repo's config/.env (default source of valid creds).
    candidates.append(repo_root.parent / "vima" / "config" / ".env")

    return candidates


def _load_env_file_values() -> dict[str, str]:
    for path in _candidate_env_files():
        if path.is_file():
            try:
                values = dotenv_values(str(path))
            except Exception:
                continue
            if any(values.get(k) for k in _ENV_KEYS.values()):
                return {k: (v or "") for k, v in values.items()}
    return {}


@dataclass(frozen=True)
class Settings:
    partner_id: str
    partner_secret: str
    app_key: str
    api_base_url: str
    source: str  # where creds were resolved from (for diagnostics; no secrets)

    @property
    def configured(self) -> bool:
        return (
            self.partner_id not in _PLACEHOLDERS
            and self.partner_secret not in _PLACEHOLDERS
            and self.app_key not in _PLACEHOLDERS
        )

    def masked(self) -> dict[str, str]:
        """Non-secret summary safe to show in the console UI / logs."""
        def tail(v: str) -> str:
            return f"…{v[-4:]}" if len(v) > 4 else ("set" if v else "unset")

        return {
            "partner_id": tail(self.partner_id),
            "partner_secret": "set" if self.partner_secret else "unset",
            "app_key": tail(self.app_key),
            "api_base_url": self.api_base_url or _DEFAULT_BASE_URL,
            "source": self.source,
            "configured": str(self.configured).lower(),
        }


def load_settings() -> Settings:
    file_values = _load_env_file_values()

    def resolve(field: str) -> str:
        env_name = _ENV_KEYS[field]
        return (os.environ.get(env_name) or file_values.get(env_name) or "").strip()

    partner_id = resolve("partner_id")
    source = "environment"
    if not partner_id and file_values:
        source = "vima config/.env (or OPENFINANCE_MCP_ENV_FILE)"

    return Settings(
        partner_id=partner_id,
        partner_secret=resolve("partner_secret"),
        app_key=resolve("app_key"),
        api_base_url=resolve("api_base_url") or _DEFAULT_BASE_URL,
        source=source if partner_id or file_values else "unset",
    )
