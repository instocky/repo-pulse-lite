# Инструкция по деплою Repo-Pulse Lite на Ubuntu 22.04

Проект генерирует `report.html` и отдаёт его через Nginx. Само приложение запускается по Cron и обновляет SQLite-базу и HTML-отчёт.

Важно: отчёт не полностью self-contained. В HTML подтягиваются внешние CDN-скрипты `cdn.tailwindcss.com` и `cdn.jsdelivr.net`, поэтому сервер и браузер клиента должны иметь доступ в интернет.

## 1. Подготовка сервера

Предполагается, что вы подключились по SSH под пользователем с `sudo`.

Ubuntu 22.04 обычно поставляется с Python 3.10, а проект требует Python 3.11+.

```bash
sudo apt update
sudo apt install -y software-properties-common git nginx certbot python3-certbot-nginx
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv

python3.11 --version
nginx -v
certbot --version
```

## 2. Развёртывание приложения

Рекомендуемая директория: `/var/www/repo-pulse`.

Если вы работаете под `root`, все файлы проекта, `.env`, `.venv` и cron-задачи дальше тоже будут жить от `root`. Для этого проекта это допустимо, но лучше понимать это заранее.

```bash
sudo mkdir -p /var/www/repo-pulse
sudo chown $USER:$USER /var/www/repo-pulse
cd /var/www/repo-pulse

# Важно: точка в конце клонирует репозиторий прямо в текущую директорию.
git clone <your-repo-url> .

python3.11 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -e .
```

Проверка установленного интерпретатора внутри окружения:

```bash
python --version
```

Ожидается `Python 3.11.x` или выше.

## 3. Конфигурация

Создайте `.env` в корне проекта:

```bash
cp .env.example .env
nano .env
```

Заполните значения:

```env
GITHUB_TOKEN=ghp_your_token_here
PULSE_DB=/var/www/repo-pulse/pulse.db
PULSE_REPORT=/var/www/repo-pulse/report.html
```

Ограничьте доступ к секретам:

```bash
chmod 600 .env
```

## 4. Первый ручной запуск

Перед настройкой Cron и Nginx выполните smoke test:

```bash
cd /var/www/repo-pulse
source .venv/bin/activate
python main.py all
ls -lh pulse.db report.html
```

Ожидается:

- `main.py all` завершается без ошибок.
- Созданы или обновлены `pulse.db` и `report.html`.

## 5. Настройка Nginx

Пример для домена `star.antibumaga.ru`:

```bash
sudo nano /etc/nginx/sites-available/star.antibumaga.ru
```

Вставьте конфиг:

```nginx
server {
    listen 80;
    server_name star.antibumaga.ru;

    root /var/www/repo-pulse;
    index report.html;

    location / {
        try_files /report.html =404;
    }

    location ~ ^/\.(?!well-known).* {
        deny all;
    }

    location ~ \.(db|env)$ {
        deny all;
    }
}
```

Активируйте сайт и проверьте конфигурацию:

```bash
sudo ln -sf /etc/nginx/sites-available/star.antibumaga.ru /etc/nginx/sites-enabled/star.antibumaga.ru
sudo nginx -t
sudo systemctl enable --now nginx
```

Проверка HTTP:

```bash
curl -I http://star.antibumaga.ru
```

## 6. HTTPS через Certbot

После того как DNS уже указывает на сервер и HTTP отвечает корректно:

```bash
sudo certbot --nginx -d star.antibumaga.ru
```

Проверка автопродления сертификата:

```bash
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

## 7. Автоматизация через Cron

Пример: ежедневное обновление в `03:00`.

```bash
crontab -e
```

Добавьте строку:

```cron
0 3 * * * cd /var/www/repo-pulse && /usr/bin/flock -n /tmp/repo-pulse.lock /var/www/repo-pulse/.venv/bin/python main.py all >> /var/www/repo-pulse/cron.log 2>&1
```

Что здесь важно:

- `flock` не даст запустить вторую копию задачи, если предыдущая ещё не завершилась.
- `cron.log` нужно периодически ротировать, иначе он будет расти бесконечно.
- Если вы деплоите под `root`, то и `crontab -e` должен быть выполнен для `root`.

Проверить, что задача записалась:

```bash
crontab -l
```

## 8. Обновление приложения

Обычное обновление без локальных изменений:

```bash
cd /var/www/repo-pulse
git pull
source .venv/bin/activate
pip install -e .
python main.py report
sudo nginx -t
git rev-parse --short HEAD
```

Если `git pull` проходит успешно, `git rev-parse --short HEAD` должен показать новый commit, а `python main.py report` пересоберёт `report.html` уже из актуального кода.

Если `git pull` падает с ошибкой вида:

```text
error: Your local changes to the following files would be overwritten by merge:
        pyproject.toml
Aborting
```

это означает, что на сервере есть незакоммиченные локальные правки, и код не обновился.

Сначала посмотрите, что именно изменено:

```bash
git status
git diff pyproject.toml
```

Если локальная правка не нужна, самый прямой путь такой:

```bash
git restore pyproject.toml
git pull
source .venv/bin/activate
pip install -e .
python main.py report
git rev-parse --short HEAD
```

Важно: если после `git pull` commit не изменился, значит сервер всё ещё работает на старом коде, и новые изменения в `report.py`, `pyproject.toml` или других файлах на прод не попали.

## 9. Типовые проблемы

### `git clone` создал вложенную папку

Если выполнить:

```bash
git clone <your-repo-url>
```

Git создаст подкаталог с именем репозитория. Чтобы сразу развернуть проект в `/var/www/repo-pulse`, используйте команду с точкой в конце:

```bash
git clone <your-repo-url> .
```

### `pip install -e .` падает на `Multiple top-level modules discovered`

Это означает, что на сервер попала старая версия `pyproject.toml`. В актуальной версии проекта уже прописан явный список top-level модулей для `setuptools`.

Проверьте, что в `pyproject.toml` есть блок:

```toml
[tool.setuptools]
py-modules = ["main", "config", "db", "github", "report"]
```

Если блока нет, обновите код из репозитория или временно добавьте его вручную, затем повторите:

```bash
source .venv/bin/activate
pip install -e .
```

## 10. Чек-лист проверки

1. [ ] DNS `A`-запись домена указывает на IP сервера.
2. [ ] На сервере установлен `Python 3.11+`, и `.venv` создан именно на нём.
3. [ ] Репозиторий клонирован в `/var/www/repo-pulse`, а не во вложенный подкаталог.
4. [ ] Файл `.env` заполнен, а права на него ограничены через `chmod 600`.
5. [ ] Ручной запуск `python main.py all` выполнен без ошибок.
6. [ ] Файлы `/var/www/repo-pulse/pulse.db` и `/var/www/repo-pulse/report.html` созданы.
7. [ ] `nginx -t` проходит успешно.
8. [ ] `curl -I http://star.antibumaga.ru` возвращает `200` или редирект на HTTPS.
9. [ ] `https://star.antibumaga.ru` открывается в браузере.
10. [ ] `crontab -l` содержит задачу обновления.
11. [ ] После тестового запуска Cron обновляется `cron.log`.
