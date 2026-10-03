"""Bot state (personal tasks, Telegram offset, last summary date).

The repo is public, so the file is encrypted with a Fernet key held in the
STATE_KEY secret before it is committed.
"""
import json
import os
from dataclasses import asdict, dataclass, field

from cryptography.fernet import Fernet


@dataclass
class Task:
    text: str
    due: str | None = None  # YYYY-MM-DD, optional


@dataclass
class State:
    tasks: list[Task] = field(default_factory=list)
    telegram_offset: int = 0
    last_summary_date: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "State":
        data = json.loads(raw)
        return cls(
            tasks=[Task(**t) for t in data.get("tasks", [])],
            telegram_offset=data.get("telegram_offset", 0),
            last_summary_date=data.get("last_summary_date"),
        )


def load(path: str, key: str) -> State:
    if not os.path.exists(path):
        return State()
    with open(path, "rb") as f:
        token = f.read()
    return State.from_json(Fernet(key).decrypt(token).decode())


def save(state: State, path: str, key: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(Fernet(key).encrypt(state.to_json().encode()))
