# GameeBot

Клиент для мини-приложения Gamee (Telegram): доска, награды, настройки в одном окне.

## Установка

Нужен **Python 3**. В каталоге с проектом:

```bash
pip install -r requirements.txt
python main.py
```

При первом запуске программа сама создаст `config.yaml` и `accounts.yaml`, если их ещё нет. Дальше — настройки в интерфейсе (Telegram API, аккаунты, при необходимости бот для уведомлений).

Файлы `config.yaml.example` и `accounts.yaml.example` в репозитории — только справочно, как выглядят поля.

**Не выкладывайте в git** `config.yaml`, `accounts.yaml` и каталог `sessions/` — там локальные токены и сессии.
