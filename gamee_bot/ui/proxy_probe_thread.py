from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from gamee_bot.proxy_url import probe_gamee_proxy


class ProxyProbeThread(QThread):
    """Фоновая проверка прокси GET-ом на api_url (как httpx в боте)."""

    finished_probe = Signal(bool, str)

    def __init__(self, api_url: str, proxy_raw: str, parent=None) -> None:
        super().__init__(parent)
        self._api_url = api_url
        self._proxy_raw = proxy_raw

    def run(self) -> None:
        ok, msg = probe_gamee_proxy(self._api_url, self._proxy_raw)
        self.finished_probe.emit(ok, msg)
