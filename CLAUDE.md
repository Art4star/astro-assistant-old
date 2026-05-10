# Астрологічний асистент — інструкції для Claude Code

## Твоя роль
Ти — автономний розробник. Ти реалізуєш повноцінний астрологічний асистент від початку до кінця без підтвердження кожного кроку. Пиши код, тестуй, виправляй помилки, і рухайся далі. Якщо щось не працює — дебаг і фікс одразу.

---

## Контекст проєкту

**Стек:**
- Mac Mini M4, username `clawd`
- OpenClaw (Telegram AI gateway) — вже налаштований
- Claude Code із PRO subscription auth (не API key)
- Python 3.x, shell scripts
- Вивід — HTML файли в браузері

**Де живе проєкт:** `~/Projects/astro-assistant/`

**Telegram доставка:** через OpenClaw з `--session main`

---

## Крок 1 — Структура проєкту

Створи повну структуру директорій:

```
~/Projects/astro-assistant/
├── CLAUDE.md
├── PROMPT.md
├── README.md
├── .env                    # TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN (з openclaw.json)
├── data/
│   ├── birth_data.json     # натальні дані користувача
│   └── history.json        # трекер рішень (порожній масив на старті)
├── engine/
│   ├── __init__.py
│   ├── calculator.py       # розрахунок позицій планет і аспектів
│   ├── interpreter.py      # астро-інтерпретація → структурований текст
│   └── lunar.py            # місячні фази, VOC (Void of Course)
├── output/
│   └── reports/            # HTML звіти (місячні, тижневі, денні)
├── scripts/
│   └── astro               # єдиний shell wrapper для всіх команд
├── templates/
│   └── dashboard.html      # Jinja2 шаблон
├── generate_report.py      # основний скрипт генерації
├── setup.py                # ввід натальних даних
├── send_telegram.py        # відправка в Telegram
└── requirements.txt
```

---

## Крок 2 — Залежності

**requirements.txt:**
```
flatlib==0.2.3
ephem
pytz
jinja2
requests
python-dotenv
```

Встанови: `pip install -r requirements.txt --break-system-packages`

**Важливо:** `flatlib` вимагає Python 3.x. Якщо виникають проблеми з flatlib — використай `kerykeion` як альтернативу (`pip install kerykeion --break-system-packages`). Kerykeion простіший в API і активно підтримується.

---

## Крок 3 — Налаштування `.env`

Прочитай токени з `~/.openclaw/openclaw.json`. Витягни `TELEGRAM_BOT_TOKEN` і `TELEGRAM_CHAT_ID`. Запиши в `.env`:

```bash
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
BIRTH_DATA_FILE=data/birth_data.json
REPORTS_DIR=output/reports
```

---

## Крок 4 — `setup.py` (ввід натальних даних)

Скрипт запитує одноразово:
- Ім'я
- Дату народження (формат: DD.MM.YYYY)
- Час народження (HH:MM, якщо невідомий — пропускає)
- Місто народження (використовує для timezone lookup через `pytz`)

Зберігає в `data/birth_data.json`:
```json
{
  "name": "Artur",
  "birth_date": "1990-05-15",
  "birth_time": "14:30",
  "birth_city": "Kyiv",
  "timezone": "Europe/Kiev",
  "latitude": 50.45,
  "longitude": 30.52
}
```

Для основних міст захардкодь координати (Kyiv, Berlin, Munich, Frankfurt, London, Warsaw, New York). Для інших — використай geopy або захардкодь координати 0,0 з попередженням.

---

## Крок 5 — `engine/calculator.py`

Використовуй `kerykeion` або `flatlib` для розрахунку:

**Що рахувати для заданої дати:**
- Знак і градус Місяця
- Місячна фаза (0-360° від Сонця): New / Waxing Crescent / First Quarter / Waxing Gibbous / Full / Waning Gibbous / Last Quarter / Balsamic
- Чи є Місяць "Void of Course" (VOC) — остання аспект до виходу зі знаку
- Знаки всіх планет: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn
- Ретроградність Mercury, Venus, Mars, Jupiter, Saturn
- Транзити до натальних планет (тільки мажорні аспекти: conjunction 0°, sextile 60°, square 90°, trine 120°, opposition 180°, орб ±3°)

**Функції:**
```python
def get_daily_data(date: datetime, birth_data: dict) -> dict
def get_month_data(year: int, month: int, birth_data: dict) -> list[dict]
def is_mercury_retrograde(date: datetime) -> bool
def get_moon_phase(date: datetime) -> str
def is_void_of_course(date: datetime) -> bool
```

---

## Крок 6 — `engine/interpreter.py`

На вхід — словник з даними дня (з calculator.py). На вихід — структурований результат.

**Система оцінки дня (score від -10 до +10):**

```python
ACTIVITY_RULES = {
    "finance": {
        "favorable": [
            ("moon_phase", ["waxing_gibbous", "full"], +3),
            ("jupiter_aspect", ["trine", "sextile"], +3),
            ("moon_sign", ["taurus", "capricorn", "virgo"], +2),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -4),
            ("saturn_aspect", ["square", "opposition"], -3),
            ("moon_voc", True, -3),
            ("moon_phase", ["balsamic", "new"], -2),
        ]
    },
    "work_technical": {
        "favorable": [
            ("moon_sign", ["virgo", "capricorn", "gemini"], +3),
            ("mercury_aspect", ["trine", "sextile"], +2),
            ("moon_phase", ["waxing_crescent", "first_quarter"], +2),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -3),
            ("moon_voc", True, -2),
            ("moon_sign", ["pisces", "cancer"], -2),
        ]
    },
    "negotiations": {
        "favorable": [
            ("mercury_direct", True, +3),
            ("venus_aspect", ["trine", "sextile"], +2),
            ("moon_sign", ["gemini", "libra", "aquarius"], +2),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -5),
            ("moon_voc", True, -3),
            ("mars_aspect", ["square", "opposition"], -2),
        ]
    },
    "content_publishing": {
        "favorable": [
            ("sun_aspect", ["trine", "sextile"], +2),
            ("mercury_direct", True, +2),
            ("moon_phase", ["waxing_gibbous", "full"], +3),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -3),
            ("moon_phase", ["balsamic"], -3),
            ("saturn_aspect", ["square"], -2),
        ]
    },
    "rest_reflection": {
        "favorable": [
            ("moon_phase", ["balsamic", "last_quarter"], +4),
            ("moon_sign", ["pisces", "cancer", "scorpio"], +2),
            ("saturn_aspect", ["trine"], +1),
        ],
        "unfavorable": [
            ("moon_phase", ["full", "waxing_gibbous"], -2),
            ("mars_aspect", ["conjunction"], -1),
        ]
    },
    "new_beginnings": {
        "favorable": [
            ("moon_phase", ["new", "waxing_crescent"], +4),
            ("jupiter_aspect", ["conjunction", "trine"], +3),
        ],
        "unfavorable": [
            ("mercury_retrograde", True, -3),
            ("moon_phase", ["balsamic", "last_quarter"], -4),
            ("saturn_aspect", ["square", "opposition"], -3),
        ]
    },
    "health_body": {
        "favorable": [
            ("moon_sign", ["virgo", "taurus"], +3),
            ("moon_phase", ["waxing_crescent"], +2),
        ],
        "unfavorable": [
            ("moon_voc", True, -2),
            ("mars_aspect", ["square", "opposition"], -2),
        ]
    }
}
```

**Функції:**
```python
def score_day(daily_data: dict) -> dict:
    # повертає {activity: score, activity: score, ...}

def get_overall_score(scores: dict) -> int:
    # середнє по всіх активностях

def get_day_label(overall_score: int) -> str:
    # > 5: "Відмінний день", 2-5: "Хороший", -1 до 2: "Нейтральний"
    # -4 до -1: "Краще почекати", < -4: "День відпочинку"

def get_warnings(daily_data: dict) -> list[str]:
    # ["⚠️ Меркурій ретроградний до 15.06", "🌑 Місяць без курсу 14:00-18:00"]

def get_recommendations(daily_data: dict, scores: dict) -> dict:
    # {best_for: [...], avoid: [...], tip: str}
```

---

## Крок 7 — `templates/dashboard.html`

**Місячний календар (основний вид):**

Самодостатній HTML файл (всі стилі inline або `<style>` блок, без зовнішніх залежностей крім CDN шрифтів).

**Дизайн:**
- Темна тема: фон `#0d1117`, текст `#e6edf3`
- Акцентний колір: глибокий фіолетовий `#7c3aed` + золотий `#f59e0b`
- Шрифт: `Inter` з Google Fonts або system fonts
- Місяць як emoji: 🌑🌒🌓🌔🌕🌖🌗🌘

**Структура сторінки:**

1. **Header** — ім'я користувача, місяць/рік, кнопки навігації ← →

2. **Легенда** — кольорові квадратики з підписами:
   - 🟢 Зелений (`#166534` bg) — відмінний день (score > 5)
   - 🟡 Жовто-зелений (`#365314` bg) — хороший (2-5)
   - ⬜ Сірий (`#1f2937` bg) — нейтральний (-1 до 2)
   - 🟠 Помаранчевий (`#7c2d12` bg) — краще почекати (-4 до -1)
   - 🔴 Темно-червоний (`#450a0a` bg) — день відпочинку (< -4)

3. **Фільтр** — кнопки-таби: Всі | Фінанси | Робота | Переговори | Контент | Відпочинок | Нові починання | Здоров'я
   При активному фільтрі — перефарбовує клітинки за score конкретної активності (JS)

4. **Сітка календаря** — 7 колонок (Пн-Нд):
   - Номер дня великим шрифтом
   - Емодзі місячної фази
   - Знак місяця (гліф або скорочення)
   - Іконки активних попереджень (☿ для ретро, 🌀 для VOC)
   - Загальна оцінка словом ("Відмінний" / "Відпочинок")

5. **Tooltip при hover** (CSS + JS):
   ```
   📅 Середа, 15 травня
   🌕 Повний місяць у Скорпіоні
   
   ✅ Найкраще для: контент, публікації
   ⚠️ Уникати: фінансові рішення
   
   📊 Оцінки:
   Фінанси: ██░░░ +3
   Робота:  ████░ +6
   ...
   
   💡 Порада дня: Місяць підсилює інтуїцію...
   ```

6. **Бічна панель або секція нижче** — "Глобальні попередження місяця":
   - Ретроградні планети з датами
   - Дати Місяця без курсу (VOC)
   - Повний і Новий місяць

7. **Footer** — дата генерації, "Оновити прогноз" кнопка (відкриває консольну інструкцію)

**JavaScript (вбудований):**
- Перемикання фільтрів активностей
- Tooltip логіка
- Підсвічування поточного дня
- Плавні hover ефекти

---

## Крок 8 — `generate_report.py`

Головний скрипт. Аргументи:

```bash
python generate_report.py --type month --year 2025 --month 6
python generate_report.py --type week
python generate_report.py --type today
python generate_report.py --type best --activity finance --days 30
```

**Логіка:**
1. Завантажує `data/birth_data.json`
2. Рахує дані через `engine/calculator.py`
3. Інтерпретує через `engine/interpreter.py`
4. Рендерить шаблон через Jinja2
5. Зберігає HTML в `output/reports/YYYY-MM-type.html`
6. Виводить шлях до файлу

---

## Крок 9 — `send_telegram.py`

**Функції:**
```python
def send_text(message: str) -> None
def send_html_as_image(html_path: str) -> None  # якщо playwright доступний
def send_summary(daily_data: dict) -> None       # форматований текст для Telegram
```

**Формат щоденного Telegram повідомлення:**
```
🔮 Астро-прогноз на сьогодні — Середа 15.05

🌕 Повний місяць у Скорпіоні

📊 Оцінка дня: Хороший (+4)

✅ Найкраще:
  • Контент та публікації
  • Технічна робота

⚡ Уникати:
  • Фінансові рішення
  • Підписання контрактів

⚠️ Попередження:
  • Місяць без курсу: 16:00–20:00

💡 Порада: Другий половина дня краща для аналізу, не для дій
```

---

## Крок 10 — `scripts/astro` (shell wrapper)

```bash
#!/bin/bash
# Розташування: ~/scripts/astro (або ~/Projects/astro-assistant/scripts/astro)
# chmod +x

PROJ_DIR="$HOME/Projects/astro-assistant"
cd "$PROJ_DIR"

case "$1" in
  month)
    YEAR=${2:-$(date +%Y)}
    MONTH=${3:-$(date +%m)}
    python generate_report.py --type month --year $YEAR --month $MONTH
    ;;
  today)
    python generate_report.py --type today
    python send_telegram.py --type today
    ;;
  week)
    python generate_report.py --type week
    ;;
  best)
    python generate_report.py --type best --activity ${2:-finance} --days ${3:-30}
    ;;
  setup)
    python setup.py
    ;;
  send)
    python send_telegram.py --type ${2:-today}
    ;;
  *)
    echo "Astro Assistant"
    echo ""
    echo "Використання:"
    echo "  astro month [рік] [місяць]   — HTML звіт на місяць"
    echo "  astro today                  — прогноз на сьогодні + Telegram"
    echo "  astro week                   — тижневий звіт"
    echo "  astro best [активність]      — найкращі дні наступні 30 днів"
    echo "  astro setup                  — ввести натальні дані"
    echo "  astro send [тип]             — відправити в Telegram"
    ;;
esac
```

Симлінк: `ln -sf ~/Projects/astro-assistant/scripts/astro ~/scripts/astro`

---

## Крок 11 — Cron для щоденного брифінгу

Додай в crontab (`crontab -e`):
```
0 8 * * * cd /Users/clawd/Projects/astro-assistant && python generate_report.py --type today && python send_telegram.py --type today >> /tmp/astro.log 2>&1
```

---

## Крок 12 — Тестування

Виконай по порядку і перевір що кожне працює:

```bash
# 1. Перевір що flatlib/kerykeion рахує позиції
python -c "from engine.calculator import get_daily_data; from datetime import datetime; print(get_daily_data(datetime.now(), {}))"

# 2. Перевір інтерпретатор
python -c "from engine.interpreter import score_day; print(score_day({}))"

# 3. Згенеруй поточний місяць
python generate_report.py --type month

# 4. Відкрий в браузері (відкрий шлях вручну або через open)
ls output/reports/

# 5. Відправ в Telegram
python send_telegram.py --type today
```

---

## Обробка помилок

- Якщо `flatlib` не встановлюється — переходь на `kerykeion` без питань
- Якщо час народження невідомий — використовуй 12:00 (полудень) як дефолт
- Якщо місто не розпізнане — запитай координати напряму
- VOC розрахунок складний — якщо не виходить з першого разу, спрощена версія: позначати як VOC 2 години перед зміною знаку Місяця
- Якщо Telegram доставка не працює — перевір `--session main` в OpenClaw конфігурації

---

## PROMPT.md (для OpenClaw інтеграції)

```
Ти — астрологічний асистент. У тебе є доступ до скрипта astro на Mac Mini.
Коли користувач запитує астро-прогноз, запускай відповідну команду через bash і повертай результат.
Відповідай українською. Будь конкретним і практичним — не езотеричним.
```

---

## Пріоритет реалізації

1. `setup.py` + `data/birth_data.json` → без даних нічого не працює
2. `engine/calculator.py` → ядро системи
3. `engine/interpreter.py` → базові правила (можна розширювати)
4. `templates/dashboard.html` → HTML шаблон з JS
5. `generate_report.py` → збирає все разом
6. `send_telegram.py` → Telegram доставка
7. `scripts/astro` + cron → автоматизація

**Починай з кроку 1. Не зупиняйся поки весь стек не працює end-to-end.**
