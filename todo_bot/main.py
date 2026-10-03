"""One pass of the bot. GitHub Actions runs this every 15 minutes.

Each run answers any Telegram commands sent since the last run, and sends the
daily summary once the configured time has passed. Nothing personal is printed,
because Actions logs on a public repo are world-readable.
"""
import re
import sys
from datetime import datetime

from . import state as state_mod
from .canvas import Canvas
from .config import Config
from .state import Task
from .summarize import plain_summary, summarize
from .telegram import Telegram

HELP = """Commands:
/add <task>  add a personal task (end with "by YYYY-MM-DD" to set a due date)
/list  show your personal tasks
/done <number>  remove a task
/today  send the Claude summary now
/help  this message

Any plain message is added as a task too.
Replies arrive on the next check, within about 15 minutes."""

DUE_RE = re.compile(r"\s+by\s+(\d{4}-\d{2}-\d{2})\s*$", re.IGNORECASE)


def build_payload(cfg: Config, st: state_mod.State, now: datetime) -> dict:
    payload = {
        "today": now.strftime("%A %Y-%m-%d"),
        "now": now.strftime("%H:%M %Z"),
        "canvas_upcoming": [],
        "canvas_missing": [],
        "personal_tasks": [{"text": t.text, "due": t.due} for t in st.tasks],
    }
    if cfg.canvas_base_url and cfg.canvas_token:
        canvas = Canvas(cfg.canvas_base_url, cfg.canvas_token)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        payload["canvas_upcoming"] = canvas.upcoming(start, cfg.days_ahead)
        payload["canvas_missing"] = canvas.missing()
    return payload


def send_summary(cfg: Config, tg: Telegram, st: state_mod.State, now: datetime) -> None:
    payload = build_payload(cfg, st, now)
    try:
        text = summarize(cfg, payload)
    except Exception as exc:  # still deliver something if Claude fails
        print(f"Claude summary failed ({type(exc).__name__}); sending plain list", file=sys.stderr)
        text = plain_summary(payload)
    tg.send(cfg.telegram_chat_id, text)


def handle(text: str, st: state_mod.State) -> tuple[str | None, bool]:
    """Returns (reply, wants_summary_now)."""
    cmd, _, arg = text.strip().partition(" ")
    cmd = cmd.split("@")[0].lower()
    arg = arg.strip()

    if cmd in ("/start", "/help"):
        return HELP, False
    if cmd == "/today":
        return None, True
    if cmd == "/list":
        if not st.tasks:
            return "No personal tasks.", False
        return "\n".join(
            f"{n}. {t.text}" + (f" (due {t.due})" if t.due else "") for n, t in enumerate(st.tasks, 1)
        ), False
    if cmd == "/done":
        if not arg.isdigit() or not 1 <= int(arg) <= len(st.tasks):
            return "Usage: /done <number from /list>", False
        removed = st.tasks.pop(int(arg) - 1)
        return f"✅ Done: {removed.text}", False
    if cmd.startswith("/") and cmd != "/add":
        return f"Unknown command.\n\n{HELP}", False

    body = arg if cmd == "/add" else text.strip()
    if not body:
        return "Usage: /add <task>", False
    due = None
    if m := DUE_RE.search(body):
        due, body = m.group(1), body[: m.start()]
    st.tasks.append(Task(text=body, due=due))
    return f"Added #{len(st.tasks)}: {body}" + (f" (due {due})" if due else ""), False


def run() -> int:
    cfg = Config.from_env()
    if not cfg.telegram_token or not cfg.state_key:
        print("TELEGRAM_BOT_TOKEN and STATE_KEY are required", file=sys.stderr)
        return 1

    tg = Telegram(cfg.telegram_token)
    st = state_mod.load(cfg.state_path, cfg.state_key)
    before = st.to_json()
    now = datetime.now(cfg.timezone)

    summary_now = False
    updates = tg.get_updates(st.telegram_offset)
    for upd in updates:
        st.telegram_offset = upd["update_id"] + 1
        msg = upd.get("message") or {}
        chat_id = str((msg.get("chat") or {}).get("id", ""))
        text = msg.get("text")
        if not chat_id or not text:
            continue
        if not cfg.telegram_chat_id:
            # Setup mode: tell the user their chat id so they can save it as a secret.
            tg.send(chat_id, f"Your chat id is {chat_id}. Save it as the TELEGRAM_CHAT_ID secret.")
            continue
        if chat_id != cfg.telegram_chat_id:
            continue  # ignore strangers
        reply, wants = handle(text, st)
        summary_now |= wants
        if reply:
            tg.send(chat_id, reply)
    print(f"processed {len(updates)} update(s)")

    if cfg.telegram_chat_id:
        due_time = now.replace(hour=cfg.summary_hour, minute=cfg.summary_minute, second=0, microsecond=0)
        today = now.date().isoformat()
        if summary_now or (now >= due_time and st.last_summary_date != today):
            send_summary(cfg, tg, st, now)
            if now >= due_time:
                st.last_summary_date = today
            print("summary sent")

    if st.to_json() != before:
        state_mod.save(st, cfg.state_path, cfg.state_key)
        print("state changed")
    return 0


if __name__ == "__main__":
    sys.exit(run())
