# canvas-connection

A Telegram bot that messages you a Claude-written summary of your to-do list every morning at 7:00 AM Eastern. It pulls upcoming and missing assignments from Canvas LMS and merges them with a personal task list you manage by texting the bot.

It costs nothing to run. GitHub Actions runs it every 15 minutes (free and unlimited on public repos), Telegram bots are free, and Claude runs on your existing Claude Pro or Max subscription through a Claude Code token.

## How it works

There's no server. A scheduled GitHub Actions workflow (`.github/workflows/bot.yml`) runs `python -m todo_bot.main` every 15 minutes. Each run reads any messages you've sent the bot since the last run, replies, and on the first run after 7:00 AM sends the daily summary. Your personal tasks live in `data/state.enc`, encrypted with a key only you hold, because this repo is public. The bot never prints task text or Canvas data to the Actions log for the same reason.

The tradeoff for being free: replies to commands take up to 15 minutes (GitHub's scheduler sometimes runs late), not instantly.

## Setup (about 15 minutes)

All values below go in the repo under **Settings → Secrets and variables → Actions → New repository secret**.

1. **Telegram bot.** In Telegram, message [@BotFather](https://t.me/BotFather), send `/newbot`, and follow the prompts. Save the token it gives you as `TELEGRAM_BOT_TOKEN`.

2. **Encryption key.** Run this anywhere with Python and save the output as `STATE_KEY`:
   ```
   pip install cryptography && python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   Keep a copy somewhere safe. Lose it and the bot can't read your saved tasks.

3. **Claude (free on your subscription).** On a computer with [Claude Code](https://code.claude.com) installed, run `claude setup-token`, sign in with your Pro/Max account, and save the token as `CLAUDE_CODE_OAUTH_TOKEN`. Usage counts against your plan's normal limits; one summary a day is a tiny fraction.

   If you'd rather use the pay-per-use API, set `ANTHROPIC_API_KEY` instead. A daily summary costs roughly half a cent to two cents.

4. **Canvas.** In Canvas, go to **Account → Settings → Approved Integrations → + New Access Token**. Save the token as `CANVAS_TOKEN`, and your school's Canvas address (for example `https://canvas.myschool.edu`, no trailing slash) as `CANVAS_BASE_URL`. Some schools disable student tokens; if so, the bot still works with just your personal list.

5. **Merge to `main`.** GitHub only runs scheduled workflows from the default branch.

6. **Find your chat id.** Send your bot any message, then go to **Actions → todo-bot → Run workflow**. The bot replies with your chat id. Save it as `TELEGRAM_CHAT_ID`. From now on it only answers you.

Run the workflow once more manually and send `/today` to test.

## Using it

```
/add Email professor about extension by 2026-10-08
/list
/done 2
/today       get the summary right now
```

Any message that isn't a command is added as a task.

## Settings

Optional repository **variables** (Settings → Secrets and variables → Actions → Variables):

| Variable | Default | |
|---|---|---|
| `SUMMARY_TIME` | `07:00` | 24-hour local time |
| `TIMEZONE` | `America/New_York` | any IANA zone name |
| `CLAUDE_MODEL` | plan default (subscription) / `claude-opus-5-5` (API) | |

## Notes

GitHub pauses scheduled workflows in repos with no activity for 60 days. The bot commits its state file daily, which normally counts as activity; if the schedule ever stops, re-enable it from the Actions tab.

If Claude is unreachable, you still get the morning message as a plain list.
