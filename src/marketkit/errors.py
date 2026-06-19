class MarketkitError(Exception):
    """Base for all marketkit errors."""


class SourceError(MarketkitError):
    """A data source failed in a non-recoverable way (bad response, parse error)."""


class RateLimited(SourceError):
    """A source refused due to rate limiting (HTTP 429) or auth throttling (401)."""


class DataUnavailable(MarketkitError):
    """No source could provide data for this request."""


class InvalidRequest(MarketkitError):
    """The caller passed bad arguments (bad ticker, bad date range, bad interval)."""
