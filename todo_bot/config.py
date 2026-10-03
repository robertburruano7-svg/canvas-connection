import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default


@dataclass(frozen=True)
class Config:
    telegram_token: str
    telegram_chat_id: str
    canvas_base_url: str
    canvas_token: str
    state_key: str
    state_path: str
    timezone: ZoneInfo
    summary_hour: int
    summary_minute: int
    days_ahead: int
    anthropic_api_key: str
    claude_oauth_token: str
    claude_model: str

    @classmethod
    def from_env(cls) -> "Config":
        hour, minute = _env("SUMMARY_TIME", "07:00").split(":")
        return cls(
            telegram_token=_env("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_env("TELEGRAM_CHAT_ID"),
            canvas_base_url=_env("CANVAS_BASE_URL").rstrip("/"),
            canvas_token=_env("CANVAS_TOKEN"),
            state_key=_env("STATE_KEY"),
            state_path=_env("STATE_PATH", "data/state.enc"),
            timezone=ZoneInfo(_env("TIMEZONE", "America/New_York")),
            summary_hour=int(hour),
            summary_minute=int(minute),
            days_ahead=int(_env("DAYS_AHEAD", "7")),
            anthropic_api_key=_env("ANTHROPIC_API_KEY"),
            claude_oauth_token=_env("CLAUDE_CODE_OAUTH_TOKEN"),
            claude_model=_env("CLAUDE_MODEL"),
        )
