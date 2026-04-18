from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gamee_bot.proxy_url import explain_proxy_formats_short
from gamee_bot.ui.proxy_probe_thread import ProxyProbeThread


class EditAccountProxyDialog(QDialog):
    """Редактирование proxy_url для HTTP к API Gamee у выбранного аккаунта."""

    def __init__(self, label: str, current_proxy: str, api_url: str, parent=None) -> None:
        super().__init__(parent)
        self._api_url = api_url
        self._probe_thread: ProxyProbeThread | None = None
        self.setWindowTitle(f"Прокси — {label}")
        self.resize(540, 220)
        root = QVBoxLayout(self)
        root.setSpacing(10)
        hint = QLabel(
            "Только для HTTP JSON-RPC к API игры. Пустое поле — прямое соединение. "
            "Telegram/Telethon не меняются."
        )
        hint.setWordWrap(True)
        hint.setObjectName("hintLabel")
        root.addWidget(hint)
        row_w = QWidget()
        h = QHBoxLayout(row_w)
        h.setContentsMargins(0, 0, 0, 0)
        self._edit = QLineEdit()
        self._edit.setPlaceholderText("host:port:user:pass или user:pass@host:port …")
        self._edit.setText(current_proxy or "")
        h.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        h.addWidget(self._edit, 1)
        self._btn_test = QPushButton("✓")
        self._btn_test.setObjectName("btnProxyProbe")
        self._btn_test.setFixedSize(34, 34)
        self._btn_test.setToolTip("Проверить прокси: GET к базовому URL API (как у бота)")
        self._btn_test.clicked.connect(self._on_test_proxy)
        h.addWidget(self._btn_test)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.addRow("Прокси:", row_w)
        root.addLayout(form)
        self._status = QLabel("")
        self._status.setWordWrap(True)
        self._status.setObjectName("hintLabel")
        root.addWidget(self._status)
        fmt = QLabel(explain_proxy_formats_short())
        fmt.setWordWrap(True)
        fmt.setObjectName("hintLabel")
        root.addWidget(fmt)
        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def proxy_input(self) -> str:
        return self._edit.text().strip()

    def _on_probe_done(self, ok: bool, msg: str) -> None:
        self._btn_test.setEnabled(True)
        self._probe_thread = None
        if ok:
            self._status.setText("✓ " + msg)
            self._status.setStyleSheet("color: #6bcf8e;")
        else:
            self._status.setText("✗ " + msg)
            self._status.setStyleSheet("color: #e8a0a0;")

    def _on_test_proxy(self) -> None:
        raw = self._edit.text().strip()
        if not raw:
            self._status.setStyleSheet("color: #e8a0a0;")
            self._status.setText("Пусто — проверка не нужна (прямой IP).")
            return
        if self._probe_thread is not None and self._probe_thread.isRunning():
            return
        self._btn_test.setEnabled(False)
        self._status.setStyleSheet("")
        self._status.setText("Проверка прокси…")
        th = ProxyProbeThread(self._api_url, raw, self)
        self._probe_thread = th
        th.finished_probe.connect(self._on_probe_done)
        th.start()
