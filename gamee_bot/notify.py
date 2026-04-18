from __future__ import annotations

from typing import Any

import httpx

_TELEGRAM_TEXT_MAX = 4000
_MESSAGE_FOOTER = ("")


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._token = (bot_token or "").strip()
        self._chat_id = (chat_id or "").strip()
        self._client = httpx.Client(timeout=30.0)

    def enabled(self) -> bool:
        return bool(self._token and self._chat_id)

    def send(self, text: str, silent: bool = False) -> bool:
        if not self.enabled():
            return False
        room = _TELEGRAM_TEXT_MAX - len(_MESSAGE_FOOTER)
        body = text if len(text) <= room else text[: max(0, room - 1)] + "…"
        out = body + _MESSAGE_FOOTER
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload: dict[str, Any] = {
            "chat_id": self._chat_id,
            "text": out[:_TELEGRAM_TEXT_MAX],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if silent:
            payload["disable_notification"] = True
        try:
            r = self._client.post(url, json=payload)
            return r.is_success
        except OSError:
            return False

    def close(self) -> None:
        self._client.close()
