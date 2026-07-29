from __future__ import annotations

from typing import Any

TIMEFRAME_MAP = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}


class MT5BrokerAdapter:
    """Thin MetaTrader5 wrapper — only imported inside the agent process."""

    def __init__(self) -> None:
        self._mt5 = None
        self.available = False
        try:
            import MetaTrader5 as mt5  # noqa: PLC0415 — Windows agent only

            self._mt5 = mt5
            self.available = True
        except ImportError:
            pass

    @property
    def connected(self) -> bool:
        if not self.available or not self._mt5:
            return False
        info = self._mt5.terminal_info()
        return bool(info and info.connected)

    def connect(self) -> bool:
        if not self.available or not self._mt5:
            return False
        terminal_path = __import__("os").environ.get("MT5_TERMINAL_PATH")
        if terminal_path:
            return bool(self._mt5.initialize(path=terminal_path))
        return bool(self._mt5.initialize())

    def shutdown(self) -> None:
        if self._mt5:
            self._mt5.shutdown()

    def account_info_dict(self) -> dict[str, Any]:
        if not self._mt5:
            return {}
        info = self._mt5.account_info()
        if info is None:
            return {}
        trade_mode = "demo"
        if info.trade_mode is not None:
            # MT5 trade_mode: 0=demo, 2=live (broker-dependent)
            trade_mode = "live" if int(info.trade_mode) == 2 else "demo"
        return {
            "login": info.login,
            "balance": float(info.balance),
            "equity": float(info.equity),
            "server": info.server,
            "trade_mode": trade_mode,
            "currency": info.currency,
        }

    def timeframe_constant(self, tf: str) -> int | None:
        if not self._mt5:
            return None
        mapping = {
            "M1": self._mt5.TIMEFRAME_M1,
            "M5": self._mt5.TIMEFRAME_M5,
            "M15": self._mt5.TIMEFRAME_M15,
            "M30": self._mt5.TIMEFRAME_M30,
            "H1": self._mt5.TIMEFRAME_H1,
            "H4": self._mt5.TIMEFRAME_H4,
            "D1": self._mt5.TIMEFRAME_D1,
        }
        return mapping.get(tf.upper())

    def copy_rates_df(self, symbol: str, timeframe: str, count: int = 400):
        import pandas as pd

        if not self._mt5:
            return pd.DataFrame()
        tf = self.timeframe_constant(timeframe)
        if tf is None:
            return pd.DataFrame()
        rates = self._mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
        frame = pd.DataFrame(rates)
        frame["timestamp"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        frame = frame.set_index("timestamp").sort_index()
        return frame[["open", "high", "low", "close"]]

    def positions_payload(self) -> list[dict[str, Any]]:
        if not self._mt5:
            return []
        positions = self._mt5.positions_get()
        if not positions:
            return []
        rows = []
        for p in positions:
            rows.append(
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "long" if p.type == 0 else "short",
                    "volume": float(p.volume),
                    "price_open": float(p.price_open),
                    "profit": float(p.profit),
                }
            )
        return rows

    def deals_payload(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self._mt5:
            return []
        from datetime import datetime, timedelta, timezone

        date_from = datetime.now(tz=timezone.utc) - timedelta(days=7)
        deals = self._mt5.history_deals_get(date_from, datetime.now(tz=timezone.utc))
        if not deals:
            return []
        rows = []
        for d in sorted(deals, key=lambda x: x.time, reverse=True)[:limit]:
            rows.append(
                {
                    "ticket": d.ticket,
                    "symbol": d.symbol,
                    "volume": float(d.volume),
                    "profit": float(d.profit),
                    "time": int(d.time),
                }
            )
        return rows

    def execute_signal(
        self,
        symbol: str,
        action: str,
        lot: float,
        *,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        open_side: str | None = None,
    ) -> dict[str, Any]:
        if not self._mt5:
            return {"ok": False, "error": "mt5_unavailable"}
        symbol_info = self._mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"ok": False, "error": f"unknown_symbol:{symbol}"}
        if not symbol_info.visible:
            self._mt5.symbol_select(symbol, True)

        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"ok": False, "error": "no_tick"}

        if action in ("exit", "close_all"):
            return self._close_symbol(symbol)

        # Flip: close opposite before opening (matches backtester signal_reverse).
        want = "long" if action == "enter_long" else "short"
        if open_side and open_side != want:
            closed = self._close_symbol(symbol)
            if not closed.get("ok"):
                return closed

        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": self._mt5.ORDER_TYPE_BUY if action == "enter_long" else self._mt5.ORDER_TYPE_SELL,
            "price": tick.ask if action == "enter_long" else tick.bid,
            "deviation": 20,
            "magic": 9001,
            "comment": "tradebot",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_IOC,
        }
        if stop_loss is not None:
            request["sl"] = float(stop_loss)
        if take_profit is not None:
            request["tp"] = float(take_profit)
        result = self._mt5.order_send(request)
        if result is None:
            return {"ok": False, "error": str(self._mt5.last_error())}
        ok = result.retcode == self._mt5.TRADE_RETCODE_DONE
        return {"ok": ok, "retcode": result.retcode, "order": result.order}

    def open_side_for(self, symbol: str) -> str | None:
        if not self._mt5:
            return None
        positions = self._mt5.positions_get(symbol=symbol)
        if not positions:
            return None
        # First position side (netting/hedging simplified for v1)
        return "long" if positions[0].type == 0 else "short"

    def _close_symbol(self, symbol: str) -> dict[str, Any]:
        positions = self._mt5.positions_get(symbol=symbol)
        if not positions:
            return {"ok": True, "closed": 0}
        closed = 0
        errors = []
        for p in positions:
            tick = self._mt5.symbol_info_tick(symbol)
            if tick is None:
                continue
            close_type = self._mt5.ORDER_TYPE_SELL if p.type == 0 else self._mt5.ORDER_TYPE_BUY
            price = tick.bid if p.type == 0 else tick.ask
            request = {
                "action": self._mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": p.volume,
                "type": close_type,
                "position": p.ticket,
                "price": price,
                "deviation": 20,
                "magic": 9001,
                "comment": "tradebot-close",
                "type_time": self._mt5.ORDER_TIME_GTC,
                "type_filling": self._mt5.ORDER_FILLING_IOC,
            }
            result = self._mt5.order_send(request)
            if result and result.retcode == self._mt5.TRADE_RETCODE_DONE:
                closed += 1
            else:
                errors.append(str(self._mt5.last_error()))
        return {"ok": not errors, "closed": closed, "errors": errors}
