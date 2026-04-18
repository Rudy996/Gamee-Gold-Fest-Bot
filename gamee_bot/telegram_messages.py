"""Многострочные HTML-сообщения для Telegram (parse_mode=HTML)."""

from __future__ import annotations

import html
from typing import Any


def _esc(s: str) -> str:
    return html.escape(s, quote=False)


def _format_est_usd(v: float) -> str:
    s = f"{v:.12f}".rstrip("0").rstrip(".")
    return s if s else "0"


def _gold_to_est_str(gold: int, gold_micro_divisor: int, est_micro_divisor: int) -> str | None:
    if gold <= 0 or gold_micro_divisor <= 0 or est_micro_divisor <= 0:
        return None
    v = (gold * gold_micro_divisor) / float(est_micro_divisor)
    return _format_est_usd(v)


def format_board_move_message(
    *,
    label: str,
    move_idx: int,
    dice_display: str,
    rewards_line: str,
    energy_before: int,
    energy_after: int,
    gold_before: int,
    gold_after: int,
    tickets_before: int,
    tickets_after: int,
    xp_gained: int,
    time_local: str,
    gold_micro_divisor: int,
    gold_estimate_usd_micro_divisor: int,
) -> str:
    """Уведомление об одном ходе по доске."""
    de = energy_after - energy_before
    dg = gold_after - gold_before
    dt = tickets_after - tickets_before
    de_s = f"+{de}" if de > 0 else str(de)
    dg_s = f"+{dg}" if dg > 0 else str(dg)
    dt_s = f"+{dt}" if dt > 0 else str(dt)

    lines = [
        "🎲 <b>Ход по доске</b>",
        "",
        f"<b>Аккаунт:</b> {_esc(label)}",
        f"<b>Бросок:</b> №{move_idx}",
        f"<b>Выпало на кубике:</b> {_esc(dice_display)}",
        "",
        f"<b>Награда с клетки:</b>",
        _esc(rewards_line),
        "",
        f"<b>Энергия:</b> {energy_before} → {energy_after} <i>({de_s})</i>",
        f"<b>Золото:</b> {gold_before} → {gold_after} <i>({dg_s})</i>",
        f"<b>Билеты:</b> {tickets_before} → {tickets_after} <i>({dt_s})</i>",
    ]
    if xp_gained > 0:
        lines.append(f"<b>XP (сезон):</b> +{xp_gained}")

    est_b = _gold_to_est_str(gold_before, gold_micro_divisor, gold_estimate_usd_micro_divisor)
    est_a = _gold_to_est_str(gold_after, gold_micro_divisor, gold_estimate_usd_micro_divisor)
    if est_b is not None and est_a is not None:
        lines.extend(
            [
                "",
                f"<b>Оценка золота в USD:</b> ${est_b} → ${est_a}",
            ]
        )

    lines.extend(["", f"<i>{_esc(time_local)}</i>"])
    return "\n".join(lines)


def format_daily_claim_message(
    *,
    label: str,
    rewards_line: str,
    streak: int,
    streak_total: int,
) -> str:
    """Уведомление о получении ежедневной награды."""
    st = f"{streak}"
    if streak_total > 0:
        st = f"{streak} из {streak_total}"
    return "\n".join(
        [
            "📅 <b>Ежедневная награда</b>",
            "",
            f"<b>Аккаунт:</b> {_esc(label)}",
            "",
            "<b>Получено:</b>",
            _esc(rewards_line),
            "",
            f"<b>Серия (streak):</b> {st}",
        ]
    )


def format_season_claim_message(
    *,
    label: str,
    rewards_line: str,
) -> str:
    """Уведомление о клейме бесплатных вех сезонного пропуска."""
    return "\n".join(
        [
            "🎁 <b>Сезонный пропуск</b>",
            "",
            f"<b>Аккаунт:</b> {_esc(label)}",
            "",
            "<b>Собрано с вех:</b>",
            _esc(rewards_line),
        ]
    )


def format_summary_message(rows_payload: list[dict[str, Any]], gold_micro_divisor: int, est_micro_divisor: int) -> str:
    """Периодическая сводка по всем аккаунтам."""
    blocks = ["📊 <b>Сводка Gamee</b>", ""]
    for r in rows_payload:
        if not isinstance(r, dict):
            continue
        label = str(r.get("label", ""))
        energy = int(r.get("energy", 0) or 0)
        gold = int(r.get("gold", 0) or 0)
        status = str(r.get("status", "") or "")
        est = _gold_to_est_str(gold, gold_micro_divisor, est_micro_divisor)
        est_part = f"\n   └ оценка ≈ ${est} USD" if est else ""

        blocks.append(f"▫️ <b>{_esc(label)}</b>")
        blocks.append(f"   ⚡ {energy} · 💰 {gold}{est_part}")
        blocks.append(f"   <i>{_esc(status)}</i>")
        blocks.append("")
    return "\n".join(blocks).rstrip()
