from dataclasses import dataclass
from enum import Enum
from typing import Any


class SignalAction(str, Enum):
    ENTER_LONG = "enter_long"
    ENTER_SHORT = "enter_short"
    EXIT = "exit"
    CLOSE_ALL = "close_all"


@dataclass(frozen=True)
class Signal:
    action: SignalAction
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.action, str):
            object.__setattr__(self, "action", SignalAction(self.action))
