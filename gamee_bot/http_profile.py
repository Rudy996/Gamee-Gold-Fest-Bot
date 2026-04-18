"""Стабильный «браузерный» профиль на аккаунт: TLS (curl_cffi) и HTTP-заголовки согласованы.

Профиль выбирается детерминированно из `label` (один и тот же label → тот же Chrome/язык).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from random import Random

# curl_cffi: только поддерживаемые имена; второе число — major для UA / sec-ch-ua.
_CHROME_DESKTOP: tuple[tuple[str, int], ...] = (
    ("chrome110", 110),
    ("chrome116", 116),
    ("chrome119", 119),
    ("chrome120", 120),
    ("chrome123", 123),
    ("chrome124", 124),
    ("chrome131", 131),
    ("chrome133a", 133),
    ("chrome136", 136),
    ("chrome142", 142),
)

_ACCEPT_LANGUAGE = (
    "ru,en-US;q=0.9,en;q=0.8,uk;q=0.7",
    "ru,en;q=0.9,en-US;q=0.8",
    "ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "ru,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
)

_PRIORITY = (
    "u=1, i",
    "u=1",
    "i",
)


@dataclass(frozen=True, slots=True)
class GameeHttpClientProfile:
    """Один согласованный набор: impersonate (TLS) + заголовки как у этого Chrome на Windows."""

    impersonate: str
    user_agent: str
    sec_ch_ua: str
    sec_ch_ua_mobile: str
    sec_ch_ua_platform: str
    sec_ch_ua_full_version: str
    sec_ch_ua_full_version_list: str
    accept_language: str
    priority: str


def gamee_http_profile_for_label(label: str) -> GameeHttpClientProfile:
    """Уникальный, но постоянный для данного label профиль (псевдослучайный из реалистичного пула)."""
    key = (label or "").strip() or "_default"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    rng = Random(int.from_bytes(digest[:16], "big"))

    imp, major = rng.choice(_CHROME_DESKTOP)
    accept = rng.choice(_ACCEPT_LANGUAGE)
    priority = rng.choice(_PRIORITY)

    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"
    )
    # Как у настоящего Chrome: оба бренда (Chromium — база, Google Chrome — продукт), один major.
    # Порядок как в типичном desktop Chrome / твоём HAR: Not → Chromium → Google Chrome.
    if major >= 120:
        sec_ch_ua = (
            f'"Not(A:Brand";v="8", "Chromium";v="{major}", "Google Chrome";v="{major}"'
        )
        not_full = '"Not(A:Brand";v="8.0.0.0"'
    else:
        sec_ch_ua = (
            f'"Not:A-Brand";v="99", "Chromium";v="{major}", "Google Chrome";v="{major}"'
        )
        not_full = '"Not:A-Brand";v="99.0.0.0"'
    patch_mid = 6000 + (digest[4] % 900)
    patch_low = 80 + (digest[5] % 120)
    full_ver = f"{major}.0.{patch_mid}.{patch_low}"
    full_list = (
        f'"Chromium";v="{full_ver}", "Google Chrome";v="{full_ver}", {not_full}'
    )

    return GameeHttpClientProfile(
        impersonate=imp,
        user_agent=ua,
        sec_ch_ua=sec_ch_ua,
        sec_ch_ua_mobile="?0",
        sec_ch_ua_platform='"Windows"',
        sec_ch_ua_full_version=f'"{full_ver}"',
        sec_ch_ua_full_version_list=full_list,
        accept_language=accept,
        priority=priority,
    )
