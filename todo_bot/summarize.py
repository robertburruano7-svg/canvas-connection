"""Turns the raw to-do data into a short Telegram message using Claude.

Two backends, picked by which secret is set:
  CLAUDE_CODE_OAUTH_TOKEN  runs the Claude Code CLI on your Claude Pro/Max
                           subscription, so there's no per-message charge.
  ANTHROPIC_API_KEY        calls the Anthropic API directly (pay per use).
"""
import json
import os
import subprocess
import tempfile

import anthropic

INSTRUCTIONS = """You write a student's daily to-do briefing, delivered as a Telegram message.

You'll get JSON with today's date, Canvas assignments due soon, Canvas work that's already
missing, and the student's personal task list. Write the message:

- Open with one line saying how heavy today and the next couple of days look.
- Then a "Today" section, a "Next few days" section, and an "Overdue" section only if
  something is missing or past due. Omit empty sections.
- Under each, one line per item: course or "Personal", the title, and the due time in
  plain words ("tonight 11:59pm", "Thu"). Put the most urgent or highest-point items first.
- End with one concrete suggestion for what to start first and why.

Plain text only, no Markdown (Telegram shows asterisks literally). A few emoji as section
markers are fine. Keep it under 1,500 characters. Never invent items that aren't in the data."""


def _prompt(payload: dict) -> str:
    return f"{INSTRUCTIONS}\n\n<data>\n{json.dumps(payload, indent=1)}\n</data>"


def _via_api(api_key: str, model: str, payload: dict) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    response = client.beta.messages.create(
        model=model or "claude-opus-5-5",
        max_tokens=4000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": _prompt(payload)}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined the request")
    return "".join(b.text for b in response.content if b.type == "text").strip()


def _via_subscription(oauth_token: str, model: str, payload: dict) -> str:
    cmd = ["npx", "-y", "@anthropic-ai/claude-code", "-p", "--output-format", "text", "--tools", ""]
    if model:
        cmd += ["--model", model]
    # Run outside the repo so the CLI has nothing to read but the prompt.
    with tempfile.TemporaryDirectory() as cwd:
        result = subprocess.run(
            cmd,
            input=_prompt(payload),
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=300,
            env={**os.environ, "CLAUDE_CODE_OAUTH_TOKEN": oauth_token},
        )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exited {result.returncode}: {result.stderr[-500:]}")
    return result.stdout.strip()


def summarize(cfg, payload: dict) -> str:
    if cfg.claude_oauth_token:
        return _via_subscription(cfg.claude_oauth_token, cfg.claude_model, payload)
    if cfg.anthropic_api_key:
        return _via_api(cfg.anthropic_api_key, cfg.claude_model, payload)
    raise RuntimeError("Set CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY")


def plain_summary(payload: dict) -> str:
    """Used when Claude is unavailable, so the daily message still arrives."""
    lines = [f"📋 To-do for {payload['today']} (Claude unavailable, raw list)"]
    for label, key in (("Overdue", "canvas_missing"), ("Canvas", "canvas_upcoming")):
        if payload[key]:
            lines.append(f"\n{label}:")
            lines += [f"- {i['course']}: {i['title']} (due {i['due']})" for i in payload[key]]
    if payload["personal_tasks"]:
        lines.append("\nPersonal:")
        lines += [f"- {t['text']}" + (f" (due {t['due']})" if t.get("due") else "") for t in payload["personal_tasks"]]
    if len(lines) == 1:
        lines.append("Nothing due. Enjoy the day.")
    return "\n".join(lines)
