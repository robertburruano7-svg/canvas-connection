"""Reads upcoming and missing work from the Canvas LMS REST API."""
from datetime import datetime, timedelta

import httpx


class Canvas:
    def __init__(self, base_url: str, token: str):
        self._http = httpx.Client(
            base_url=f"{base_url}/api/v1/",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )

    def _get_all(self, path: str, params: dict) -> list[dict]:
        items: list[dict] = []
        resp = self._http.get(path, params=params)
        while True:
            resp.raise_for_status()
            items.extend(resp.json())
            nxt = resp.links.get("next", {}).get("url")
            if not nxt:
                return items
            resp = self._http.get(nxt)

    def upcoming(self, start: datetime, days: int) -> list[dict]:
        raw = self._get_all(
            "planner/items",
            {
                "start_date": start.isoformat(),
                "end_date": (start + timedelta(days=days)).isoformat(),
                "per_page": 100,
            },
        )
        out = []
        for item in raw:
            override = item.get("planner_override") or {}
            subs = item.get("submissions") or {}
            if override.get("marked_complete") or subs.get("submitted") or subs.get("graded"):
                continue
            if item.get("plannable_type") == "announcement":
                continue
            p = item.get("plannable") or {}
            out.append({
                "course": item.get("context_name"),
                "type": item.get("plannable_type"),
                "title": p.get("title"),
                "due": p.get("due_at") or p.get("todo_date") or item.get("plannable_date"),
                "points": p.get("points_possible"),
            })
        return sorted(out, key=lambda i: i["due"] or "")

    def missing(self) -> list[dict]:
        raw = self._get_all(
            "users/self/missing_submissions",
            {"include[]": "course", "filter[]": "submittable", "per_page": 100},
        )
        return [
            {
                "course": (a.get("course") or {}).get("name"),
                "title": a.get("name"),
                "due": a.get("due_at"),
                "points": a.get("points_possible"),
            }
            for a in raw
        ]
