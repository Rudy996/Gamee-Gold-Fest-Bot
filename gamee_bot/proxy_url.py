"""Нормализация строки прокси под httpx и проверка доступа до хоста API Gamee."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urlparse

import httpx

# host:port:user:pass (частый формат у резидентских прокси)
_HOST_PORT_USER_PASS = re.compile(
    r"^([^:]+):(\d{1,5}):([^:]+):(.+)$",
    re.DOTALL,
)
# только host:port (порт — число)
_HOST_PORT_ONLY = re.compile(r"^([^:]+):(\d{1,5})$")


def normalize_gamee_proxy_url(raw: Any) -> str | None:
    """
    Приводит ввод к URL для httpx.

    Поддерживается:
    - http:// https:// socks5:// socks5h:// (как есть, с пробелами обрезка)
    - user:pass@host:port / user:pass@host:port (добавляется http://)
    - host:port
    - host:port:user:password (типичный список прокси — превращается в http://user:pass@host:port)
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    if "://" in s:
        scheme, rest = s.split("://", 1)
        low = scheme.lower().strip()
        if low in ("http", "https", "socks5", "socks5h"):
            r = (rest or "").strip()
            # Легаси в YAML: http://host:port:user:pass (без @) — иначе "порт" = 6879:user:pass
            if r and "@" not in r:
                mfix = _HOST_PORT_USER_PASS.match(r)
                if mfix:
                    host, port_s, user, password = (
                        mfix.group(1),
                        mfix.group(2),
                        mfix.group(3),
                        mfix.group(4),
                    )
                    uq = quote(user, safe="")
                    pq = quote(password, safe="")
                    return f"{low}://{uq}:{pq}@{host}:{port_s}"
            return f"{low}://{rest}" if rest else s
        return s

    m4 = _HOST_PORT_USER_PASS.match(s)
    if m4:
        host, port_s, user, password = m4.group(1), m4.group(2), m4.group(3), m4.group(4)
        u = quote(user, safe="")
        p = quote(password, safe="")
        return f"http://{u}:{p}@{host}:{port_s}"

    if "@" in s and not s.startswith("@"):
        return f"http://{s}"

    m2 = _HOST_PORT_ONLY.match(s)
    if m2:
        return f"http://{m2.group(1)}:{m2.group(2)}"

    return f"http://{s}"


def explain_proxy_formats_short() -> str:
    return (
        "Строка без префикса — HTTP-прокси. Для SOCKS5 в начале обязательно: socks5:// (например socks5://host:1080). "
        "Форматы: host:port · user:pass@host:port · host:port:user:pass · http://… · socks5://…"
    )


def validate_proxy_url_for_httpx(url: str) -> str:
    """Проверяет, что URL разбирается httpx; иначе ValueError с понятным текстом."""
    try:
        httpx.URL(url)
    except httpx.InvalidURL as e:
        raise ValueError(
            f"Неверный формат прокси ({e}). "
            "Проверьте порт (число), логин/пароль и схему — см. подсказку под полем."
        ) from e
    return url


def normalize_and_validate_gamee_proxy(raw: Any) -> str | None:
    n = normalize_gamee_proxy_url(raw)
    if not n:
        return None
    return validate_proxy_url_for_httpx(n)


def probe_gamee_proxy(api_url: str, proxy_url: str, *, timeout: float = 18.0) -> tuple[bool, str]:
    """
    GET на базовый api_url через прокси (как при работе с игрой: httpx + trust_env=False).
    Успех — любой ответ HTTP (включая 403/404), главное установить туннель.
    """
    u = normalize_and_validate_gamee_proxy(proxy_url)
    if not u:
        return False, "Введите непустой адрес прокси."
    base = api_url.rstrip("/") + "/"
    try:
        with httpx.Client(timeout=timeout, trust_env=False, proxy=u) as client:
            r = client.get(base, follow_redirects=True)
        return True, f"Соединение через прокси есть (HTTP {r.status_code})."
    except ValueError as e:
        return False, str(e)
    except httpx.ProxyError as e:
        return False, f"Ошибка прокси: {e}"
    except httpx.ConnectError as e:
        return False, f"Нет соединения через прокси: {e}"
    except httpx.TimeoutException:
        return False, "Таймаут при проверке прокси."
    except OSError as e:
        return False, str(e)
