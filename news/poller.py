"""News REST poller (Alpaca news API). Market-hours polling cadence.

Free-tier path is REST polling (e.g. every 60s during market hours), budgeted
against 200 req/min. ``received_at`` (ingestion time) is the honest T0 —
labeled as receipt latency, never wire latency.

No network calls happen at import time. ``poll_once`` requires credentials;
tests use fixtures instead.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

NEWS_URL = "https://data.alpaca.markets/v1beta1/news"


class MissingCredentialsError(Exception):
    """No API keys available; polling is impossible."""


class NewsPoller:
    def __init__(self, symbols: list[str], poll_interval_s: int = 60,
                 limit: int = 50):
        self.symbols = list(symbols)
        self.poll_interval_s = poll_interval_s
        self.limit = limit
        self._page_token: str | None = None

    def _auth_headers(self) -> dict:
        key = os.environ.get("APCA_API_KEY_ID")
        secret = os.environ.get("APCA_API_SECRET_KEY")
        if not key or not secret:
            raise MissingCredentialsError(
                "APCA_API_KEY_ID / APCA_API_SECRET_KEY not set; "
                "see .env.example (never commit real keys)"
            )
        return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}

    def poll_once(self) -> list[dict]:
        """One REST poll. Returns raw article dicts (stored byte-identical first)."""
        params = {
            "symbols": ",".join(self.symbols),
            "sort": "desc",
            "limit": str(self.limit),
        }
        if self._page_token:
            params["page_token"] = self._page_token
        url = NEWS_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=self._auth_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.load(resp)
        self._page_token = body.get("next_page_token")
        return body.get("news", [])

    @staticmethod
    def receipt_timestamp() -> str:
        return datetime.now(timezone.utc).isoformat()
