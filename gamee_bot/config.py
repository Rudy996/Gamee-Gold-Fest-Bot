from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import yaml

from gamee_bot.proxy_url import normalize_gamee_proxy_url

TELETHON_CREDENTIALS_REQUIRED_MSG = (
    "В настройках не указаны api_id и api_hash Telegram. Откройте меню «Настройки», "
    "вкладка «Telegram», вставьте оба значения с сайта https://my.telegram.org → "
    "API development tools и нажмите «Сохранить»."
)


def ensure_config_file(path: Path) -> None:
    """Создаёт config.yaml с шаблоном, если файла ещё нет (первый запуск / клон без конфига)."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    default: dict[str, Any] = {
        "telethon": {"api_id": 0, "api_hash": ""},
        "paths": {"accounts": "accounts.yaml"},
        "ui": {"window_title": "Gamee — кубик доски"},
    }
    path.write_text(
        yaml.safe_dump(default, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def ensure_accounts_file(path: Path) -> None:
    """Создаёт accounts.yaml с пустым списком, если файла ещё нет."""
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("accounts: []\n", encoding="utf-8")


def parse_gamee_ref_input(raw: str | None) -> str | None:
    """
    Реф для Gamee: целая ссылка (t.me/.../start?startapp=…), или только хвост после startapp=.
    Возвращает значение start_param для Mini App либо None.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    low = s.lower()
    key = "startapp="
    if key in low:
        idx = low.index(key)
        val = s[idx + len(key) :].strip()
        val = val.split("&")[0].split("#")[0].strip()
        return val or None
    if "t.me/" in low or low.startswith("http://") or low.startswith("https://"):
        url = s if low.startswith("http") else "https://" + s.lstrip("/")
        qs = parse_qs(urlparse(url).query)
        vals = qs.get("startapp")
        if vals:
            v = unquote(vals[0]).strip()
            return v or None
        return None
    return s


def gamee_proxy_table_summary(raw: Any) -> tuple[str, str]:
    """Тип прокси для ячейки таблицы; в подсказке — узел (хост:порт), без пароля в ячейке."""
    norm = normalize_gamee_proxy_url(raw)
    if not norm:
        return "без прокси", "API Gamee без прокси (к серверу игры идёт ваш IP)."
    u = urlparse(norm)
    scheme = (u.scheme or "http").lower()
    host = u.hostname or "?"
    try:
        port = u.port
    except ValueError:
        return (
            "прокси?",
            "Некорректная строка (часто это http://host:port:user:pass). "
            "Сохраните как host:port:user:pass или user:pass@host:port / socks5://…",
        )
    ps = f":{port}" if port else ""
    if scheme in ("http", "https"):
        kind = "HTTP"
    elif scheme in ("socks5", "socks5h"):
        kind = "SOCKS5"
    else:
        kind = scheme.upper()
    netloc = host + ps
    cell = kind
    if u.username:
        tip = f"{kind}, пользователь «{u.username}», узел {netloc}"
    else:
        tip = f"{kind}, узел {netloc}"
    return cell, tip


@dataclass
class GameeConfig:
    api_url: str
    life_currency_id: int
    gold_currency_id: int
    ticket_currency_id: int
    money_currency_id: int  # MONEY в getAssets, баланс в долларах
    life_micro_divisor: int
    gold_micro_divisor: int
    ticket_micro_divisor: int
    reward_micro_divisor: int
    money_micro_divisor: int  # микро MONEY на 1 цент USD (обычно 10_000)
    # Оценка конвертации Gold Points → USDT в UI prizes.gamee.com: micro / этот делитель.
    gold_estimate_usd_micro_divisor: int
    # telegram.checkTask.code (промокод на prizes.gamee.com); см. HAR.
    check_task_id: int


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    notify_on_move: bool
    notify_on_daily_claim: bool
    notify_on_season_claim: bool
    summary_interval_seconds: int


@dataclass
class TelethonConfig:
    """Пара api_id + api_hash с my.telegram.org для входа по телефону (Telethon)."""

    api_id: int
    api_hash: str
    gamee_start_param: str | None
    # Числовой ref для user.linkTelegramReferral после loginUsingTelegram (как в HAR).
    telegram_referral_ref: int | None


@dataclass
class AppConfig:
    gamee: GameeConfig
    telegram: TelegramConfig
    telethon: TelethonConfig
    accounts_path: Path
    window_title: str


def telethon_credentials_ready(cfg: AppConfig) -> bool:
    """Пара api_id + api_hash с my.telegram.org — нужна для Telethon и запуска бота."""
    return cfg.telethon.api_id > 0 and bool(cfg.telethon.api_hash.strip())


def resolve_account_gamee_start_param(
    cfg: AppConfig,
    account_gamee_ref_raw: str | None,
    *,
    inherit_global_if_empty: bool = False,
) -> str | None:
    """
    Реф (start_param) для аккаунта из accounts.yaml.
    По умолчанию пустое поле в YAML НЕ подменяется глобальным конфигом — смена настроек
    не трогает старые записи. inherit_global_if_empty=True — только для шага «Добавить аккаунт».
    """
    r = (account_gamee_ref_raw or "").strip()
    if r:
        return parse_gamee_ref_input(r)
    if inherit_global_if_empty:
        return cfg.telethon.gamee_start_param
    return None


def resolve_account_telegram_referral_ref(
    cfg: AppConfig,
    account_telegram_referral_ref: int | None,
    *,
    inherit_global_if_empty: bool = False,
) -> int | None:
    """Числовой ref для linkTelegramReferral: только из YAML, если не запрошен fallback как при добавлении аккаунта."""
    if account_telegram_referral_ref is not None:
        return int(account_telegram_referral_ref)
    if inherit_global_if_empty:
        return cfg.telethon.telegram_referral_ref
    return None


def _optional_int_yaml(raw: Any) -> int | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        v = int(s)
    except ValueError:
        return None
    return v if v > 0 else None


def load_config(path: Path) -> AppConfig:
    ensure_config_file(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    base = path.parent.resolve()
    g = raw.get("gamee") or {}
    t = raw.get("telegram") or {}
    th = raw.get("telethon") or {}
    p = raw.get("paths") or {}
    u = raw.get("ui") or {}
    acc = p.get("accounts", "accounts.yaml")
    accounts_path = Path(acc)
    if not accounts_path.is_absolute():
        accounts_path = (base / accounts_path).resolve()
    ensure_accounts_file(accounts_path)
    try:
        telethon_api_id = int(th.get("api_id", 0))
    except (TypeError, ValueError):
        telethon_api_id = 0
    telethon_api_hash = str(th.get("api_hash", "") or "").strip()
    return AppConfig(
        gamee=GameeConfig(
            api_url=str(g.get("api_url", "https://api2.gamee.com/")),
            life_currency_id=int(g.get("life_currency_id", 5)),
            gold_currency_id=int(g.get("gold_currency_id", 65)),
            ticket_currency_id=int(g.get("ticket_currency_id", 1)),
            money_currency_id=int(g.get("money_currency_id", 4)),
            life_micro_divisor=int(g.get("life_micro_divisor", 1_000_000)),
            gold_micro_divisor=int(g.get("gold_micro_divisor", 1_000_000)),
            ticket_micro_divisor=int(g.get("ticket_micro_divisor", 1_000_000)),
            reward_micro_divisor=int(g.get("reward_micro_divisor", 1_000_000)),
            money_micro_divisor=int(g.get("money_micro_divisor", 10_000)),
            gold_estimate_usd_micro_divisor=int(
                g.get("gold_estimate_usd_micro_divisor", 1_000_000_000_000)
            ),
            check_task_id=int(g.get("check_task_id", 2950)),
        ),
        telegram=TelegramConfig(
            bot_token=str(t.get("bot_token", "")),
            chat_id=str(t.get("chat_id", "")),
            notify_on_move=bool(t.get("notify_on_move", True)),
            notify_on_daily_claim=bool(t.get("notify_on_daily_claim", True)),
            notify_on_season_claim=bool(t.get("notify_on_season_claim", True)),
            summary_interval_seconds=int(t.get("summary_interval_seconds", 3600)),
        ),
        telethon=TelethonConfig(
            api_id=telethon_api_id,
            api_hash=telethon_api_hash,
            gamee_start_param=parse_gamee_ref_input(
                th.get("gamee_ref") if "gamee_ref" in th else th.get("mini_app_start_param")
            ),
            telegram_referral_ref=_optional_int_yaml(th.get("telegram_referral_ref")),
        ),
        accounts_path=accounts_path,
        window_title=str(u.get("window_title", "Gamee — кубик доски")),
    )


def read_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def read_full_config_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def save_config_sections(
    path: Path,
    *,
    gamee: dict[str, Any] | None = None,
    telegram: dict[str, Any] | None = None,
    telethon: dict[str, Any] | None = None,
    paths: dict[str, Any] | None = None,
    ui: dict[str, Any] | None = None,
) -> None:
    """Обновляет только перечисленные секции; остальные ключи файла сохраняются."""
    existing = read_full_config_yaml(path)
    if gamee is not None:
        merged = {**(existing.get("gamee") or {}), **gamee}
        for k in (
            "poll_interval_seconds",
            "min_energy_to_play",
            "energy_regen_minutes",
            "play_delay_seconds",
        ):
            merged.pop(k, None)
        existing["gamee"] = merged
    if telegram is not None:
        merged = {**(existing.get("telegram") or {}), **telegram}
        existing["telegram"] = merged
    if telethon is not None:
        merged = {**(existing.get("telethon") or {}), **telethon}
        for k in ("mini_app_bot", "mini_app_short_name", "mini_app_start_param"):
            merged.pop(k, None)
        existing["telethon"] = merged
    if paths is not None:
        merged = {**(existing.get("paths") or {}), **paths}
        existing["paths"] = merged
    if ui is not None:
        merged = {**(existing.get("ui") or {}), **ui}
        existing["ui"] = merged
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(existing, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
