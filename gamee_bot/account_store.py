from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from gamee_bot.config import normalize_gamee_proxy_url, read_yaml_mapping


def safe_account_filename(label: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", label.strip(), flags=re.UNICODE)
    s = s.strip(" _") or "account"
    return s[:64]


@dataclass
class AccountRecord:
    label: str
    init_data: str
    install_uuid: str
    telethon_session: str | None = None
    # Сырой ввод как в настройках (ссылка или хвост startapp=). Пусто → общий реф из config.
    gamee_ref: str | None = None
    # user.linkTelegramReferral → params.ref; пусто → telethon.telegram_referral_ref из config.
    telegram_referral_ref: int | None = None
    # True = уже был зарегистрирован в Gamee до этого логина; рефы из YAML не применяются.
    gamee_preexisting: bool = False
    proxy_url: str | None = None  # только HTTP к API Gamee (api2.gamee.com); пусто — без прокси

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"label": self.label, "install_uuid": self.install_uuid}
        if self.telethon_session:
            d["telethon_session"] = self.telethon_session
        else:
            d["init_data"] = self.init_data
        if self.gamee_ref and str(self.gamee_ref).strip():
            d["gamee_ref"] = str(self.gamee_ref).strip()
        if self.telegram_referral_ref is not None:
            d["telegram_referral_ref"] = int(self.telegram_referral_ref)
        if self.gamee_preexisting:
            d["gamee_preexisting"] = True
        pu = normalize_gamee_proxy_url(self.proxy_url)
        if pu:
            d["proxy_url"] = pu
        return d

    @staticmethod
    def from_dict(d: dict[str, Any], index: int, accounts_yaml_dir: Path) -> AccountRecord:
        label = str(d.get("label") or f"account_{index + 1}").strip()
        init = str(d.get("init_data", "")).strip()
        ts_raw = d.get("telethon_session")
        ts = str(ts_raw).strip() if ts_raw is not None else ""
        if not init and not ts:
            raise ValueError(f"Аккаунт «{label}»: укажите init_data или telethon_session")
        if init and ts:
            raise ValueError(
                f"Аккаунт «{label}»: только одно из полей — init_data или telethon_session"
            )
        gamee_preexisting = bool(d.get("gamee_preexisting"))
        gr_raw = d.get("gamee_ref")
        gamee_ref = str(gr_raw).strip() if gr_raw is not None and str(gr_raw).strip() else None
        tr_raw = d.get("telegram_referral_ref")
        telegram_referral_ref: int | None = None
        if tr_raw is not None and str(tr_raw).strip():
            try:
                telegram_referral_ref = int(str(tr_raw).strip())
                if telegram_referral_ref <= 0:
                    telegram_referral_ref = None
            except ValueError as e:
                raise ValueError(
                    f"Аккаунт «{label}»: telegram_referral_ref должно быть целым числом"
                ) from e
        if gamee_preexisting:
            gamee_ref = None
            telegram_referral_ref = None
        pr_raw = d.get("proxy_url")
        proxy_url = normalize_gamee_proxy_url(pr_raw) if pr_raw is not None else None
        iu = d.get("install_uuid")
        if iu is None or str(iu).strip() == "":
            if init:
                install = str(uuid.uuid5(uuid.NAMESPACE_URL, init))
            else:
                sp = Path(ts)
                if not sp.is_absolute():
                    sp = (accounts_yaml_dir / sp).resolve()
                install = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{label}|{sp}"))
        else:
            install = str(iu).strip()
        return AccountRecord(
            label=label,
            init_data=init,
            install_uuid=install,
            telethon_session=ts if ts else None,
            gamee_ref=gamee_ref,
            telegram_referral_ref=telegram_referral_ref,
            gamee_preexisting=gamee_preexisting,
            proxy_url=proxy_url,
        )


def load_accounts(path: Path) -> list[AccountRecord]:
    data = read_yaml_mapping(path)
    items = data.get("accounts")
    if not items:
        return []
    if not isinstance(items, list):
        raise ValueError("accounts.yaml: поле accounts должно быть списком")
    base = path.parent.resolve()
    out: list[AccountRecord] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        out.append(AccountRecord.from_dict(item, i, base))
    return out


def save_accounts_template(path: Path, accounts: list[AccountRecord]) -> None:
    payload = {"accounts": [a.to_dict() for a in accounts]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _delete_telethon_session_files(session_path: Path) -> None:
    """Удаляет .session и типичные хвосты SQLite (-wal, -shm, -journal), если есть."""
    candidates = [
        session_path,
        Path(str(session_path) + "-journal"),
        Path(str(session_path) + "-wal"),
        Path(str(session_path) + "-shm"),
    ]
    for p in candidates:
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass


def remove_account_by_label(path: Path, label: str) -> tuple[bool, Path | None]:
    """
    Удаляет аккаунт из accounts.yaml.
    Если у записи был telethon_session — удаляет файл сессии на диске (перелогин с нуля).
    Возвращает (успех, путь к .session что удаляли или None).
    """
    want = label.strip()
    if not want:
        return False, None
    data = read_yaml_mapping(path)
    items = data.get("accounts")
    if not isinstance(items, list):
        return False, None
    base = path.parent.resolve()
    session_file: Path | None = None
    new_items: list[Any] = []
    found = False
    for x in items:
        if isinstance(x, dict) and str(x.get("label", "")).strip() == want:
            found = True
            ts = x.get("telethon_session")
            if ts and str(ts).strip():
                p = Path(str(ts).strip())
                if not p.is_absolute():
                    p = (base / p).resolve()
                else:
                    p = p.resolve()
                session_file = p
            continue
        new_items.append(x)
    if not found:
        return False, None
    data["accounts"] = new_items
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    if session_file is not None:
        _delete_telethon_session_files(session_file)
    return True, session_file


def set_account_gamee_registration_state(
    path: Path,
    label: str,
    *,
    brand_new_user: bool,
) -> None:
    """
    После loginUsingTelegram: brand_new_user=True — новая регистрация в Gamee; иначе аккаунт уже был,
    рефы в YAML удаляем и ставим gamee_preexisting (рефы больше не применяются).
    """
    want = label.strip()
    if not want:
        return
    data = read_yaml_mapping(path)
    items = data.get("accounts")
    if not isinstance(items, list):
        return
    changed = False
    for x in items:
        if not isinstance(x, dict) or str(x.get("label", "")).strip() != want:
            continue
        if brand_new_user:
            if "gamee_preexisting" in x:
                del x["gamee_preexisting"]
                changed = True
        else:
            x["gamee_preexisting"] = True
            x.pop("gamee_ref", None)
            x.pop("telegram_referral_ref", None)
            changed = True
        break
    if not changed:
        return
    data["accounts"] = items
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def set_account_proxy_url(path: Path, label: str, raw: str | None) -> bool:
    """Записывает proxy_url для аккаунта (нормализованный URL или снятие прокси при пустом вводе)."""
    want_label = label.strip()
    if not want_label:
        return False
    want = normalize_gamee_proxy_url(raw) if raw and str(raw).strip() else None
    data = read_yaml_mapping(path)
    items = data.get("accounts")
    if not isinstance(items, list):
        return False
    changed = False
    for x in items:
        if not isinstance(x, dict):
            continue
        if str(x.get("label", "")).strip() != want_label:
            continue
        changed = True
        if want:
            x["proxy_url"] = want
        else:
            x.pop("proxy_url", None)
        break
    if not changed:
        return False
    data["accounts"] = items
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return True


def append_account(path: Path, record: AccountRecord) -> None:
    data = read_yaml_mapping(path)
    items = data.get("accounts")
    if items is None:
        items = []
    if not isinstance(items, list):
        raise ValueError("accounts.yaml: поле accounts должно быть списком")
    items.append(record.to_dict())
    data["accounts"] = items
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
