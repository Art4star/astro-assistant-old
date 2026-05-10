# Astro Assistant

Астрологічний асистент для щоденних прогнозів і місячних HTML-календарів.

## Швидкий старт

```bash
# 1. Встановити залежності
pip install -r requirements.txt --break-system-packages

# 2. Ввести натальні дані
python3 setup.py

# 3. Прогноз на сьогодні
python3 generate_report.py --type today

# 4. Місячний HTML-звіт
python3 generate_report.py --type month
open output/reports/$(date +%Y-%m)-month.html
```

## Команди через wrapper

```bash
chmod +x scripts/astro
ln -sf ~/Projects/astro-assistant/scripts/astro ~/scripts/astro

astro today        # прогноз + Telegram
astro month        # HTML-календар поточного місяця
astro week         # тиждень
astro best finance # найкращі дні для фінансів
astro setup        # натальні дані
```

## Cron (щоденний брифінг о 8:00)

```
0 8 * * * cd /Users/clawd/Projects/astro-assistant && python3 generate_report.py --type today && python3 send_telegram.py --type today >> /tmp/astro.log 2>&1
```
