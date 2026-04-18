from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt

from datetime import datetime

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from gamee_bot.config import read_full_config_yaml, save_config_sections
from gamee_bot.notify import TelegramNotifier
from gamee_bot.telegram_messages import (
    format_board_move_message,
    format_daily_claim_message,
    format_season_claim_message,
    format_summary_message,
)


class SettingsDialog(QDialog):
    """Настройки без правки YAML вручную."""

    def __init__(self, config_path: Path, parent=None) -> None:
        super().__init__(parent)
        self._config_path = config_path.resolve()
        self.setWindowTitle("Настройки")
        self.resize(580, 540)

        self._raw = read_full_config_yaml(self._config_path)

        tabs = QTabWidget()
        tabs.addTab(self._tab_general(), "Общие")
        tabs.addTab(self._tab_notify(), "Уведомления")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(tabs)
        root.addWidget(buttons)

    def _small_hint(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setObjectName("hintLabel")
        return lab

    def _settings_card(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box.setObjectName("settingsCard")
        return box

    def _tab_general(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setSpacing(0)
        lay.setContentsMargins(4, 8, 4, 8)

        lead = QLabel("Подключение")
        lead.setObjectName("settingsLead")
        sub = QLabel("API Telegram (обязательно) и рефка Gamee, если нужна.")
        sub.setObjectName("settingsMicro")
        sub.setWordWrap(True)
        lay.addWidget(lead)
        lay.addWidget(sub)

        api_box = self._settings_card("Telegram API")
        api_l = QVBoxLayout(api_box)
        api_l.setSpacing(10)
        hint_api = QLabel(
            '<span style="line-height:1.5">Один раз на всё приложение. Создайте приложение на '
            '<a href="https://my.telegram.org/auth" style="color:#8ab4f8">my.telegram.org</a> → '
            "<b>API development tools</b> и скопируйте два значения ниже.</span>"
        )
        hint_api.setOpenExternalLinks(True)
        hint_api.setWordWrap(True)
        hint_api.setObjectName("hintLabel")
        api_l.addWidget(hint_api)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(14)
        self._th_api_id = QLineEdit()
        self._th_api_id.setPlaceholderText("Число, например 12345678")
        self._th_api_hash = QLineEdit()
        self._th_api_hash.setPlaceholderText("Строка из пару десятков символов")
        form.addRow("App api_id:", self._th_api_id)
        form.addRow("App api_hash:", self._th_api_hash)
        api_l.addLayout(form)
        lay.addWidget(api_box)

        ref_box = self._settings_card("Рефка Gamee")
        ref_l = QVBoxLayout(ref_box)
        ref_l.setSpacing(10)
        ref_l.addWidget(
            self._small_hint(
                "Реф с "
                '<a href="https://t.me/gamee/start">t.me/gamee/start</a> '
                "— целиком ссылку или пусто."
            )
        )
        self._th_gamee_ref = QLineEdit()
        self._th_gamee_ref.setPlaceholderText("Ссылка с рефом или пусто")
        ref_l.addWidget(self._th_gamee_ref)
        ref_l.addWidget(
            self._small_hint(
                "<b>User ID в Telegram</b> — только цифры. Необязательно."
            )
        )
        self._th_telegram_referral_ref = QLineEdit()
        self._th_telegram_referral_ref.setPlaceholderText("Только цифры или пусто")
        ref_l.addWidget(self._th_telegram_referral_ref)
        lay.addWidget(ref_box)

        lay.addStretch()

        th = self._raw.get("telethon") or {}
        api_id_raw = th.get("api_id", 0)
        api_hash_raw = str(th.get("api_hash", "") or "")
        self._th_api_id.setText(str(int(api_id_raw)) if api_id_raw else "")
        self._th_api_hash.setText(api_hash_raw)
        ref = th.get("gamee_ref")
        if ref is None:
            ref = th.get("mini_app_start_param")
        self._th_gamee_ref.setText(str(ref).strip() if ref else "")
        tr = th.get("telegram_referral_ref")
        self._th_telegram_referral_ref.setText(
            str(int(tr)) if tr is not None and str(tr).strip() else ""
        )
        return w

    def _tab_notify(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(
            QLabel(
                "Какие события дублировать в Telegram. Токен и Chat ID можно не указывать — "
                "тогда уведомления не отправляются."
            )
        )
        tg = self._raw.get("telegram") or {}
        form = QFormLayout()
        self._tg_token = QLineEdit()
        self._tg_token.setPlaceholderText("От @BotFather")
        self._tg_chat = QLineEdit()
        self._tg_chat.setPlaceholderText("Ваш chat_id")
        self._tg_token.setText(str(tg.get("bot_token", "")))
        self._tg_chat.setText(str(tg.get("chat_id", "")))
        self._tg_notify_move = QCheckBox("О каждом ходе по доске")
        self._tg_notify_move.setChecked(bool(tg.get("notify_on_move", True)))
        self._tg_notify_daily = QCheckBox("О получении ежедневной награды")
        self._tg_notify_daily.setChecked(bool(tg.get("notify_on_daily_claim", True)))
        self._tg_notify_season = QCheckBox("О клейме сезонного пропуска")
        self._tg_notify_season.setChecked(bool(tg.get("notify_on_season_claim", True)))
        checks_col = QVBoxLayout()
        checks_col.addWidget(self._tg_notify_move)
        checks_col.addWidget(self._tg_notify_daily)
        checks_col.addWidget(self._tg_notify_season)
        checks_wrap = QWidget()
        checks_wrap.setLayout(checks_col)
        self._tg_summary = QSpinBox()
        self._tg_summary.setRange(0, 86400)
        self._tg_summary.setSuffix(" сек (0 = выкл.)")
        self._tg_summary.setValue(max(0, int(tg.get("summary_interval_seconds", 3600))))
        form.addRow("Токен бота:", self._tg_token)
        form.addRow("Chat ID:", self._tg_chat)
        form.addRow("События:", checks_wrap)
        form.addRow("Сводка раз в (0 = выкл.):", self._tg_summary)
        lay.addLayout(form)

        test_box = QGroupBox("Проверка уведомлений")
        test_l = QVBoxLayout(test_box)
        test_l.addWidget(
            self._small_hint(
                "Отправка в Telegram сейчас, без сохранения настроек. "
                "Нужны заполненные токен и Chat ID выше."
            )
        )
        test_form = QFormLayout()
        self._tg_test_format = QComboBox()
        self._tg_test_format.addItem("Ход по доске", "move")
        self._tg_test_format.addItem("Ежедневная награда", "daily")
        self._tg_test_format.addItem("Сезонный пропуск", "season")
        self._tg_test_format.addItem("Периодическая сводка", "summary")
        test_form.addRow("Формат:", self._tg_test_format)
        self._tg_test_btn = QPushButton("Отправить тестовое сообщение")
        self._tg_test_btn.clicked.connect(self._on_send_test_telegram)
        test_form.addRow("", self._tg_test_btn)
        test_l.addLayout(test_form)
        lay.addWidget(test_box)

        lay.addStretch()
        return w

    def _on_send_test_telegram(self) -> None:
        token = self._tg_token.text().strip()
        chat = self._tg_chat.text().strip()
        if not token or not chat:
            QMessageBox.warning(
                self,
                "Тест уведомления",
                "Укажите токен бота и Chat ID в полях выше.",
            )
            return
        g = self._raw.get("gamee") or {}
        gm = int(g.get("gold_micro_divisor", 1_000_000))
        ed = int(g.get("gold_estimate_usd_micro_divisor", 1_000_000_000_000))
        ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        kind = self._tg_test_format.currentData()
        notifier = TelegramNotifier(token, chat)
        try:
            if kind == "move":
                text = format_board_move_message(
                    label="demo",
                    move_idx=1,
                    dice_display="4",
                    rewards_line="⭐ 10, 💰 50, 🎟️ 2",
                    energy_before=8,
                    energy_after=7,
                    gold_before=14000,
                    gold_after=14050,
                    tickets_before=450,
                    tickets_after=452,
                    xp_gained=15,
                    time_local=ts,
                    gold_micro_divisor=gm,
                    gold_estimate_usd_micro_divisor=ed,
                )
            elif kind == "daily":
                text = format_daily_claim_message(
                    label="demo",
                    rewards_line="⚡ 25, 💰 100",
                    streak=3,
                    streak_total=14,
                )
            elif kind == "season":
                text = format_season_claim_message(
                    label="demo",
                    rewards_line="💰 500, ⭐ 20",
                )
            else:
                text = format_summary_message(
                    [
                        {
                            "label": "demo",
                            "energy": 8,
                            "gold": 14000,
                            "status": "ожидание (тест)",
                        },
                        {
                            "label": "demo-2",
                            "energy": 5,
                            "gold": 9000,
                            "status": "типичная строка",
                        },
                    ],
                    gm,
                    ed,
                )
            ok = notifier.send(text, silent=False)
        finally:
            notifier.close()
        if ok:
            QMessageBox.information(
                self,
                "Тест уведомления",
                "Сообщение отправлено. Проверь чат с ботом.",
            )
        else:
            QMessageBox.warning(
                self,
                "Тест уведомления",
                "Не удалось отправить. Проверь токен, Chat ID и что написал боту /start.",
            )

    def _on_save(self) -> None:
        aid = self._th_api_id.text().strip()
        ah = self._th_api_hash.text().strip()
        if not aid or not ah:
            QMessageBox.warning(
                self,
                "Ключи Telegram",
                "Укажите api_id и api_hash с my.telegram.org — без них программа не работает.",
            )
            return
        try:
            api_id_int = int(aid)
            if api_id_int <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "api_id", "api_id должно быть положительным числом.")
            return
        ref = self._th_gamee_ref.text().strip()
        tr_line = self._th_telegram_referral_ref.text().strip()
        telegram_referral_ref = None
        if tr_line:
            try:
                telegram_referral_ref = int(tr_line)
                if telegram_referral_ref <= 0:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(
                    self,
                    "User ID в Telegram",
                    "Нужно целое число или пустое поле.",
                )
                return
        th = {
            "api_id": api_id_int,
            "api_hash": ah,
            "gamee_ref": ref if ref else None,
            "telegram_referral_ref": telegram_referral_ref,
        }

        summary_sec = self._tg_summary.value()
        telegram = {
            "bot_token": self._tg_token.text().strip(),
            "chat_id": self._tg_chat.text().strip(),
            "notify_on_move": self._tg_notify_move.isChecked(),
            "notify_on_daily_claim": self._tg_notify_daily.isChecked(),
            "notify_on_season_claim": self._tg_notify_season.isChecked(),
            "summary_interval_seconds": int(summary_sec),
        }

        try:
            save_config_sections(
                self._config_path,
                telegram=telegram,
                telethon=th,
            )
        except OSError as e:
            QMessageBox.critical(self, "Сохранение", str(e))
            return

        self.accept()
