"""`marketkit` console entry point. Stdlib argparse only -- no extra dependency.

    marketkit get RELIANCE.NS --period 5y --out reliance.csv
    marketkit summary RELIANCE.NS
    marketkit plot RELIANCE.NS --indicators sma:50,rsi --save chart.png
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from marketkit.errors import MarketkitError
from marketkit.fetch import get
from marketkit.summary import summary


def _cmd_get(args: argparse.Namespace) -> None:
    df = get(args.ticker, period=args.period, interval=args.interval)
    if args.out:
        df.to_csv(args.out)
        print(f"wrote {len(df)} rows to {args.out}")
    else:
        print(df.to_string())


def _cmd_summary(args: argparse.Namespace) -> None:
    print(summary(args.ticker, period=args.period).to_string())


def _cmd_plot(args: argparse.Namespace) -> None:
    from marketkit.plot import plot

    df = get(args.ticker, period=args.period)
    indicators = args.indicators.split(",") if args.indicators else None
    ax = plot(df, indicators=indicators)
    if args.save:
        ax.figure.savefig(args.save)
        print(f"saved chart to {args.save}")
    else:
        import matplotlib.pyplot as plt

        plt.show()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marketkit", description="marketkit command-line interface")
    sub = parser.add_subparsers(dest="command", required=True)

    get_p = sub.add_parser("get", help="fetch OHLCV data")
    get_p.add_argument("ticker")
    get_p.add_argument("--period", default="1y")
    get_p.add_argument("--interval", default="1d")
    get_p.add_argument("--out", default=None, help="write to this CSV path instead of stdout")
    get_p.set_defaults(func=_cmd_get)

    summary_p = sub.add_parser("summary", help="one-line risk/return report")
    summary_p.add_argument("ticker")
    summary_p.add_argument("--period", default="1y")
    summary_p.set_defaults(func=_cmd_summary)

    plot_p = sub.add_parser("plot", help="render a price chart (needs marketkit[plot])")
    plot_p.add_argument("ticker")
    plot_p.add_argument("--period", default="1y")
    plot_p.add_argument("--indicators", default=None, help="comma-separated, e.g. sma:50,rsi")
    plot_p.add_argument("--save", default=None, help="save to this image path instead of showing")
    plot_p.set_defaults(func=_cmd_plot)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except MarketkitError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
