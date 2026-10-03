import httpx

MAX_LEN = 4096


class Telegram:
    def __init__(self, token: str):
        self._http = httpx.Client(base_url=f"https://api.telegram.org/bot{token}/", timeout=30)

    def _call(self, method: str, **params):
        resp = self._http.post(method, json=params)
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram {method} failed: {data.get('description')}")
        return data["result"]

    def get_updates(self, offset: int) -> list[dict]:
        return self._call("getUpdates", offset=offset, timeout=0, allowed_updates=["message"])

    def send(self, chat_id: str, text: str) -> None:
        # Split on line boundaries so long summaries stay readable.
        chunk = ""
        for line in text.splitlines(keepends=True):
            if len(chunk) + len(line) > MAX_LEN:
                self._call("sendMessage", chat_id=chat_id, text=chunk)
                chunk = ""
            chunk += line[:MAX_LEN]
        if chunk.strip():
            self._call("sendMessage", chat_id=chat_id, text=chunk)
