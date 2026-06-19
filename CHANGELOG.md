# Changelog

## 0.1.3

- Also ignore missing type stubs for `requests` under mypy strict mode
  (CI's Python 3.9 job didn't have requests' bundled types resolved the
  same way the dev environment did). No behavior change.

## 0.1.2

- Fix `mypy --strict` failures (missing annotations, untyped pandas
  imports, unsupported `python_version`) that broke CI for the `v0.1.1`
  tag before it could publish. No behavior change.

## 0.1.1

- First functional release. The `0.1.0` tag/PyPI upload shipped only empty
  module stubs; this release implements the actual package per
  `docs/tech-plan.md`: clean-data contract, Yahoo/Stooq sources with
  fallback, Parquet cache, fetch orchestration, returns/risk/indicator
  analytics, and `summary()`.

## 0.1.0

- Initial (non-functional) scaffold.
