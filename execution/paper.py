"""Paper execution. PAPER ONLY — by construction, not by convention.

The broker refuses to instantiate against any base URL other than exactly
``https://paper-api.alpaca.markets``. There is no code path in this repository
that can address a live endpoint: adding one requires a deliberate, reviewed,
versioned change (and a conversation with the owner first).

Fills are SIMULATED (paper fills are idealized; see experiment-design.md §11).
Slippage assumptions from config/costs.yaml are applied by the backtest and
performance accounting, not hidden inside the fill.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from risk.engine import PAPER_URL, PaperModeError, paper_mode_gate


class PaperEndpointRefused(Exception):
    """Raised when anything but the paper endpoint is requested."""


class PaperBroker:
    """Simulated paper broker. No real orders. No real money. Ever."""

    def __init__(self, base_url: str | None = None):
        paper_mode_gate()  # env-level gate first
        url = base_url or os.environ.get("APCA_API_BASE_URL", "")
        if url != PAPER_URL:
            raise PaperEndpointRefused(
                f"refusing non-paper endpoint: {url!r} "
                f"(only {PAPER_URL} is allowed)"
            )
        self.base_url = url

    def submit_order(self, symbol: str, side: str, qty: float,
                     order_type: str = "market",
                     limit_price: float | None = None,
                     reference_price: float | None = None) -> dict:
        """Simulate an immediate fill at the reference price.

        In production this would POST to the paper REST API; here the fill is
        simulated deterministically so the full pipeline (and its ledger) runs
        offline. Slippage is applied downstream in performance accounting.
        """
        if reference_price is None or reference_price <= 0:
            raise ValueError("reference_price must be positive for a fill")
        now = datetime.now(timezone.utc).isoformat()
        return {
            "order_id": f"paper-{uuid.uuid4().hex[:12]}",
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "order_type": order_type,
            "status": "FILLED",
            "fill_price": reference_price,
            "fill_qty": qty,
            "submitted_at": now,
            "filled_at": now,
            "endpoint": self.base_url,  # audit trail: proves paper endpoint
            "simulated": True,
        }
