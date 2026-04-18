from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)


class EnterCodeDialog(QDialog):
    """Промокод telegram.checkTask.code: taskId и код задаются здесь (по умолчанию taskId из config)."""

    def __init__(self, default_task_id: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ввести код")
        self.setModal(True)
        self.resize(440, 0)

        hint = QLabel(
            "Промокод с prizes.gamee.com. Укажите номер задания (taskId) и код — "
            "они уходят на API для всех аккаунтов. Task ID по умолчанию берётся из "
            "настроек (gamee.check_task_id), его можно сменить только для этого запуска."
        )
        hint.setWordWrap(True)
        hint.setObjectName("mutedHint")

        self._task_id = QSpinBox()
        self._task_id.setRange(1, 999_999_999)
        self._task_id.setValue(max(1, int(default_task_id)))
        self._task_id.setToolTip(
            "Идентификатор задания для telegram.checkTask.code (смотри Network на prizes при вводе кода)."
        )

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("Например G0L6F3S7")
        self._edit.setClearButtonEnabled(True)

        form = QFormLayout()
        form.addRow("Task ID:", self._task_id)
        form.addRow("Код:", self._edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        root = QVBoxLayout(self)
        root.addWidget(hint)
        root.addLayout(form)
        root.addWidget(buttons)

    def task_id(self) -> int:
        return int(self._task_id.value())

    def code(self) -> str:
        return self._edit.text().strip()
