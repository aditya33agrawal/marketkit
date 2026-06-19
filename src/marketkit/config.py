from __future__ import annotations

from pathlib import Path
import os

import platformdirs

# Where cached parquet files live (cross-platform)
CACHE_DIR = Path(platformdirs.user_cache_dir("marketkit"))

# Source priority order (first that succeeds wins)
DEFAULT_SOURCE_ORDER = ["yahoo", "stooq"]

# Cache freshness: daily bars considered stale after this many seconds
CACHE_TTL_SECONDS = 60 * 60 * 12  # 12h

# Trading periods per year, by interval (for annualizing)
PERIODS_PER_YEAR = {"1d": 252, "1wk": 52, "1mo": 12}

# HTTP
REQUEST_TIMEOUT = 15
USER_AGENT = "marketkit/0.1 (+https://github.com/aditya33agrawal/marketkit)"


def alpha_vantage_key() -> str | None:
    """Optional API key read from the environment (never hardcode)."""
    return os.environ.get("ALPHAVANTAGE_API_KEY")


# Global toggles (can be overridden at call time)
OFFLINE = False  # if True, only read cache, never hit network
