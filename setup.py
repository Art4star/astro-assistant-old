#!/usr/bin/env python3
import json
import os
import sys
from datetime import datetime

KNOWN_CITIES = {
    "kyiv": {"lat": 50.45, "lon": 30.52, "tz": "Europe/Kiev"},
    "kiev": {"lat": 50.45, "lon": 30.52, "tz": "Europe/Kiev"},
    "berlin": {"lat": 52.52, "lon": 13.41, "tz": "Europe/Berlin"},
    "munich": {"lat": 48.14, "lon": 11.58, "tz": "Europe/Berlin"},
    "frankfurt": {"lat": 50.11, "lon": 8.68, "tz": "Europe/Berlin"},
    "london": {"lat": 51.51, "lon": -0.13, "tz": "Europe/London"},
    "warsaw": {"lat": 52.23, "lon": 21.01, "tz": "Europe/Warsaw"},
    "new york": {"lat": 40.71, "lon": -74.01, "tz": "America/New_York"},
    "newyork": {"lat": 40.71, "lon": -74.01, "tz": "America/New_York"},
}

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "birth_data.json")


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val if val else default


def main():
    print("=== Астрологічний асистент — налаштування ===\n")

    name = ask("Ваше ім'я", "Artur")

    birth_date_str = ask("Дата народження (ДД.ММ.РРРР)")
    try:
        birth_date = datetime.strptime(birth_date_str, "%d.%m.%Y")
    except (ValueError, TypeError):
        print("Невірний формат дати. Спробуйте ДД.ММ.РРРР")
        sys.exit(1)

    birth_time_str = ask("Час народження (ГГ:ХХ, Enter щоб пропустити)")
    if birth_time_str:
        try:
            datetime.strptime(birth_time_str, "%H:%M")
        except ValueError:
            print("Невірний формат часу. Використовую 12:00")
            birth_time_str = "12:00"
    else:
        birth_time_str = "12:00"

    birth_city = ask("Місто народження", "Kyiv")
    city_key = birth_city.lower().strip()
    city_data = KNOWN_CITIES.get(city_key)

    if city_data:
        lat = city_data["lat"]
        lon = city_data["lon"]
        tz = city_data["tz"]
    else:
        print(f"Місто '{birth_city}' не знайдено у базі.")
        try:
            lat = float(ask("Широта (наприклад 50.45)", "0"))
            lon = float(ask("Довгота (наприклад 30.52)", "0"))
        except ValueError:
            lat, lon = 0.0, 0.0
        tz = ask("Часова зона (наприклад Europe/Kiev)", "Europe/Kiev")

    data = {
        "name": name,
        "birth_date": birth_date.strftime("%Y-%m-%d"),
        "birth_time": birth_time_str,
        "birth_city": birth_city,
        "timezone": tz,
        "latitude": lat,
        "longitude": lon,
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nДані збережено в {DATA_FILE}")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
