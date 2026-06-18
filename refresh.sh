#!/bin/bash
# Оновлює інтерпретаційний пакет і звіт для поточного місяця.
# Якщо сьогодні >= 25-те — також готує пакет наступного місяця.

set -e
PROJ="$HOME/Projects/astro-assistant"
cd "$PROJ"

YEAR=$(date +%Y)
MONTH=$(date +%-m)
DAY=$(date +%-d)

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── Поточний місяць ──────────────────────────────────────────────────────────
log "Поточний місяць: $YEAR-$(printf '%02d' $MONTH)"

log "  Генерую звіт (Router → ForecastAgent → ... → OutputAgent)..."
/usr/bin/python3 generate_report.py --type month --year "$YEAR" --month "$MONTH"

REPORT_PATH="$PROJ/output/reports/${YEAR}-$(printf '%02d' $MONTH)-report.html"
log "  Готово: $REPORT_PATH"

# ── Інтерпретація через Claude ──────────────────────────────────────────────
INTERP_PATH="$PROJ/data/memory/sessions/${YEAR}-$(printf '%02d' $MONTH)/interpretation.json"
if [ ! -f "$INTERP_PATH" ]; then
    log "  Запускаю інтерпретацію через Claude..."
    /usr/bin/python3 interpret.py --year "$YEAR" --month "$MONTH" || log "  ⚠️ Інтерпретація не вдалася"
else
    log "  Інтерпретація вже існує, пропускаю."
fi

# ── Наступний місяць (якщо >= 25-те) ─────────────────────────────────────────
if [ "$DAY" -ge 25 ]; then
    if [ "$MONTH" -eq 12 ]; then
        NEXT_YEAR=$((YEAR + 1))
        NEXT_MONTH=1
    else
        NEXT_YEAR=$YEAR
        NEXT_MONTH=$((MONTH + 1))
    fi

    NEXT_PKG="$PROJ/output/data/${NEXT_YEAR}-$(printf '%02d' $NEXT_MONTH)-interpret.json"
    if [ ! -f "$NEXT_PKG" ]; then
        log "День >= 25 — готую пакет наступного місяця ($NEXT_YEAR-$(printf '%02d' $NEXT_MONTH))..."
        /usr/bin/python3 generate_report.py --type month --year "$NEXT_YEAR" --month "$NEXT_MONTH"
        log "  Пакет наступного місяця готовий."
    else
        log "Пакет наступного місяця вже існує, пропускаю."
    fi
fi

log "Все готово!"
