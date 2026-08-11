"""Export FX OHLCV bars from yfinance into hs-data/bars/."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

SYMBOL_MAP = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "XAUUSD": "GC=F",
}

TF_MAP = {
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}

# Yahoo intraday history is limited (~730 days for H1).
TF_MAX_DAYS = {
    "H1": 700,
    "H4": 700,
    "D1": 3650,
}


def _default_range(timeframe: str, end: str) -> str:
    end_dt = datetime.fromisoformat(end)
    days = TF_MAX_DAYS.get(timeframe, 700)
    start_dt = end_dt - timedelta(days=days)
    return start_dt.strftime("%Y-%m-%d")


def _flatten_columns(df) -> None:
    if hasattr(df.columns, "levels"):
        df.columns = [str(c[0]).lower() if isinstance(c, tuple) else str(c).lower() for c in df.columns]
    else:
        df.columns = [str(c).lower() for c in df.columns]


def _write_bars(path: Path, rows: list[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        for r in rows:
            w.writerow([r["time"], r["open"], r["high"], r["low"], r["close"], r["volume"]])
    return len(rows)


def download_symbol_tf(symbol: str, timeframe: str, start: str, end: str) -> list[dict]:
    import yfinance as yf

    ticker = SYMBOL_MAP[symbol]
    interval = TF_MAP[timeframe]
    effective_start = start
    if timeframe in TF_MAX_DAYS:
        auto_start = _default_range(timeframe, end)
        if start < auto_start:
            effective_start = auto_start
    df = yf.download(
        ticker,
        start=effective_start,
        end=end,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )
    if df.empty:
        raise RuntimeError(f"No data for {symbol} {timeframe} ({ticker})")

    _flatten_columns(df)

    rows: list[dict] = []
    for ts, row in df.iterrows():
        t = ts.to_pydatetime()
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        else:
            t = t.astimezone(timezone.utc)
        vol = row.get("volume", 0)
        if vol != vol:  # NaN
            vol = 0
        rows.append(
            {
                "time": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "open": round(float(row["open"]), 5),
                "high": round(float(row["high"]), 5),
                "low": round(float(row["low"]), 5),
                "close": round(float(row["close"]), 5),
                "volume": int(vol),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Export FX bars via yfinance")
    p.add_argument("--out-dir", type=Path, default=Path("bars"))
    p.add_argument("--symbols", default="EURUSD,GBPUSD,USDJPY,XAUUSD")
    p.add_argument("--timeframes", default="H1,H4,D1")
    p.add_argument("--start", default="2018-01-01", help="Clamped for intraday per Yahoo limits")
    p.add_argument("--end", default=None, help="Default: today UTC")
    args = p.parse_args(argv)
    end = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    tfs = [t.strip().upper() for t in args.timeframes.split(",") if t.strip()]
    total = 0
    for sym in symbols:
        if sym not in SYMBOL_MAP:
            print(f"Skip unknown symbol {sym}")
            continue
        for tf in tfs:
            if tf not in TF_MAP:
                continue
            try:
                rows = download_symbol_tf(sym, tf, args.start, end)
            except RuntimeError as exc:
                print(f"WARN: {exc}")
                continue
            n = _write_bars(args.out_dir / f"{sym}_{tf}.csv", rows)
            print(f"Wrote {n} bars → {args.out_dir / f'{sym}_{tf}.csv'}")
            total += n
    print(f"Done ({total} bars total)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
