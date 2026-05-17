from datetime import datetime, date
import calendar as cal_module
from typing import List, Dict, Optional

from engine.interpreter import score_day, get_overall_score, ACTIVITY_LABELS

# ── Transit → Human Language ─────────────────────────────────────────────────

_NATAL_AREA: dict[str, str] = {
    "sun": "identity", "ascendant": "identity",
    "moon": "emotions", "mercury": "communication",
    "venus": "money_values", "mars": "action_energy",
    "jupiter": "opportunities", "saturn": "career_structure",
    "pluto": "power_depth", "neptune": "ideals",
    "true_node": "direction", "midheaven": "career",
}

_AREA_LABEL: dict[str, str] = {
    "identity":        "особистості і репутації",
    "emotions":        "емоцій і особистого",
    "communication":   "комунікацій і домовленостей",
    "money_values":    "фінансів і цінностей",
    "action_energy":   "енергії і рішень",
    "opportunities":   "можливостей і зростання",
    "career_structure":"кар'єри і структури",
    "power_depth":     "влади і трансформації",
    "ideals":          "ідеалів і духовного",
    "direction":       "напрямку і місії",
    "career":          "кар'єри і публічності",
    "general":         "поточних справ",
}


def _format_peak(peak_date: str) -> str:
    if not peak_date:
        return ""
    try:
        d = datetime.strptime(peak_date, "%Y-%m-%d")
        months_gen = {
            1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
            5: "травня", 6: "червня", 7: "липня", 8: "серпня",
            9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня",
        }
        return f"пік {d.day} {months_gen.get(d.month, '')}"
    except Exception:
        return ""


def _make_narrative(transit: dict) -> Optional[dict]:
    planet  = transit.get("transit_planet", "").lower()
    aspect  = transit.get("aspect", "").lower()
    natal   = transit.get("natal_planet", "").lower()
    intens  = transit.get("intensity", 0)
    peak    = _format_peak(transit.get("peak_date", ""))
    area    = _NATAL_AREA.get(natal, "general")
    a_lbl   = _AREA_LABEL.get(area, "поточних справ")

    # ── Specific high-signal patterns ──

    if planet == "neptune" and "square" in aspect and natal in ("ascendant", "sun", "moon"):
        return dict(icon="🌫", intensity=intens, peak=peak,
            title="Туман в орієнтирах і самопочутті",
            impact="Наприкінці місяця складніше зрозуміти чого ти насправді хочеш — і як тебе сприймають інші. Межа між своїм і чужим розмита, енергія ніби вислизає.",
            action="Не приймай великих рішень про напрямок до середини червня. Фіксуй думки письмово — але не дій на них одразу.")

    if planet == "neptune" and "square" in aspect and natal in ("jupiter", "saturn", "mercury"):
        return dict(icon="🌫", intensity=intens, peak=peak,
            title="Важко відрізнити реальне від бажаного",
            impact="Чужі обіцянки і нові ідеї звучать переконливо — але деталей або конкретики немає. Ризик взятись за те, що виглядає більшим ніж є.",
            action="Завжди питай конкретні цифри, строки і відповідальних. Якщо відповіді немає — відкладай рішення.")

    if planet == "pluto" and "conjunction" in aspect and natal in ("venus", "moon"):
        return dict(icon="⚡", intensity=intens, peak=peak,
            title="Гострі питання про гроші або партнерства",
            impact="Якщо є незакрите питання про гроші, власність або ділові партнерства — воно почне відчуватись дуже гостро наприкінці місяця.",
            action="Не чекай кризи — ініціюй розмову або перегляд угоди до 25-го, поки ще є вікно дій.")

    if planet == "pluto" and "square" in aspect and natal in ("sun", "ascendant", "saturn"):
        return dict(icon="⚡", intensity=intens, peak=peak,
            title="Тиск на самовизначення і владу",
            impact="Те що не відповідає твоїм справжнім цінностям — буде витіснятись. Зміни не завжди добровільні, але завжди необхідні.",
            action="Не опирайся трансформації — керуй нею. Краще ти ініціюєш зміну, ніж вона нав'яже себе.")

    if planet == "jupiter" and "opposition" in aspect and natal in ("sun", "ascendant", "saturn"):
        return dict(icon="🔭", intensity=intens, peak=peak,
            title="Ризик переоцінити свої можливості",
            impact="Зовнішніх пропозицій і можливостей багато — але є ризик взятись за більше ніж є ресурс. Відчуття 'я можу все' часто не відповідає реальності.",
            action="Фільтруй жорстко: краще одна глибока справа, ніж п'ять поверхневих. Запитай — чи є у мене ресурс на це прямо зараз?")

    if planet == "jupiter" and "conjunction" in aspect:
        return dict(icon="🟢", intensity=intens, peak=peak,
            title=f"Відкриті двері в сфері {a_lbl}",
            impact=f"Юпітер дає природний поштовх в сфері {a_lbl}. Ті хто діє — отримують непропорційно великий результат відносно зусиль.",
            action="Дій. Не після підготовки, не після 'правильного моменту'. Цей і є правильний момент.")

    if planet == "jupiter" and "trine" in aspect:
        return dict(icon="🟢", intensity=intens, peak=peak,
            title=f"Сприятливий вітер для {a_lbl}",
            impact=f"Юпітер відкриває сприятливі умови в сфері {a_lbl}. Менше тертя, більше відгуків на кроки які робиш.",
            action="Саме зараз — виходь, питай, пропонуй. Результат буде кращим ніж зазвичай.")

    if planet == "saturn" and "square" in aspect:
        return dict(icon="🔩", intensity=intens, peak=peak,
            title=f"Перевірка на міцність — {a_lbl}",
            impact=f"Місяць вимагає уповільнення в сфері {a_lbl}. Те, що зроблено неміцно або поспіхом — відчується як тиск або заминка.",
            action="Краще завершити одне добре, ніж три на половину. Зосередься на якості, не на швидкості.")

    if planet == "saturn" and "conjunction" in aspect:
        return dict(icon="🏗", intensity=intens, peak=peak,
            title=f"Перебудова структури — {a_lbl}",
            impact=f"Сатурн вимагає переосмислення і реорганізації в сфері {a_lbl}. Це не зупинка — це будівництво міцнішого фундаменту.",
            action="Знайди що потрібно перебудувати — і роби це системно, не частинами. Краще зараз під тиском, ніж пізніше в кризі.")

    if planet == "saturn" and "opposition" in aspect:
        return dict(icon="🔩", intensity=intens, peak=peak,
            title=f"Зовнішні обмеження в сфері {a_lbl}",
            impact=f"Ззовні приходить тиск або гальмування в сфері {a_lbl}. Ситуація вимагає реалізму і конкретики замість амбіцій.",
            action="Прийми обмеження як дані — і працюй в їх рамках. Спроба зломити стіну головою тут не допоможе.")

    if planet == "uranus" and aspect in ("conjunction", "opposition", "square"):
        return dict(icon="⚡", intensity=intens, peak=peak,
            title="Несподівані зміни або осяяння",
            impact="Уран приносить те, чого не чекаєш. Може бути раптова зміна обставин — або ідея яка давно дозрівала виривається назовні.",
            action="Не намагайся контролювати — адаптуйся швидко. Гнучкість зараз важливіша за план.")

    if planet == "mars" and aspect in ("conjunction", "trine", "sextile"):
        return dict(icon="🔥", intensity=intens, peak=peak,
            title="Прилив енергії і рішучості",
            impact="Є ресурс щоб почати або зрушити те що відкладалось. Марс дає коротке вікно підвищеної дієвості.",
            action="Використай цей момент для конкретного кроку, а не для планування. Зроби те що давно чекає.")

    if intens >= 25:
        aspect_verb = {
            "conjunction": "активує", "opposition": "створює напругу в",
            "square": "кидає виклик", "trine": "підтримує",
            "sextile": "відкриває можливості в",
        }.get(aspect, "впливає на")
        planet_ua = {
            "jupiter": "Юпітер", "saturn": "Сатурн", "pluto": "Плутон",
            "neptune": "Нептун", "uranus": "Уран", "mars": "Марс",
        }.get(planet, planet.title())
        return dict(icon="🔸", intensity=intens, peak=peak,
            title=f"Помітний вплив на сферу {a_lbl}",
            impact=f"{planet_ua} {aspect_verb} сферу {a_lbl}. Варто звернути увагу.",
            action="Реагуй свідомо — не ігноруй і не панікуй.")

    return None


def get_transit_narratives(top_transits: list) -> list:
    """Convert top transit list to sorted human-readable narratives (max 5)."""
    seen: set = set()
    result: list = []
    for t in top_transits:
        key = (t.get("transit_planet"), t.get("aspect"), t.get("natal_planet"))
        if key in seen:
            continue
        seen.add(key)
        n = _make_narrative(t)
        if n:
            result.append(n)
    result.sort(key=lambda x: -x["intensity"])
    return result[:5]


def get_month_theme_from_transits(top_transits: list) -> Optional[dict]:
    """Derive month theme title + subtitle from dominant transit energy."""
    if not top_transits:
        return None
    top = top_transits[0]
    planet = top.get("transit_planet", "").lower()
    aspect = top.get("aspect", "").lower()
    natal  = top.get("natal_planet", "").lower()

    combos = {
        ("neptune", "square"):  ("«Туман і Трансформація»", "розрізняй ілюзії від можливостей — і дій до того як туман згустився"),
        ("pluto",   "conjunction"): ("«Зламай і Відбудуй»", "те що прийшов час змінити — змінюється само. Питання тільки в тому хто ведe процес — ти чи обставини"),
        ("saturn",  "square"):  ("«Уповільнись і Зроби Міцно»", "місяць не для швидкості — для якості. Кожен крок що зроблений добре зараз дає перевагу потім"),
        ("jupiter", "opposition"): ("«Велике Видно Здалеку»", "можливості є — але їх треба оцінювати тверезо, без ейфорії"),
        ("jupiter", "conjunction"): ("«Вікно Відчинено»", "дій — бо такий збіг не щотижня"),
        ("uranus",  "conjunction"): ("«Прорив або Хаос»", "зміни прийдуть — краще самому вести їх ніж реагувати"),
        ("mars",    "conjunction"): ("«Час Діяти»", "є ресурс і є вікно — використовуй"),
    }
    for (p, a), (title, subtitle) in combos.items():
        if planet == p and a in aspect:
            return {"title": title, "subtitle": subtitle}
    return None

MONTH_NAMES_UA = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень",
}
MONTH_NAMES_GEN = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня",
}


def _day_num(daily: dict) -> int:
    return int(daily["date"].split("-")[2])


def _month_num(daily: dict) -> int:
    return int(daily["date"].split("-")[1])


def find_windows(month_data: list, activity: str, min_score: int = 2) -> list:
    """Find date ranges where score for activity >= min_score (max 1-day gap allowed)."""
    month = _month_num(month_data[0])
    scored = []
    for d in month_data:
        scores = score_day(d)
        sc = scores.get(activity, 0)
        scored.append((_day_num(d), sc))

    windows = []
    i = 0
    while i < len(scored):
        day_num, sc = scored[i]
        if sc >= min_score:
            start = day_num
            end = day_num
            max_sc = sc
            j = i + 1
            while j < len(scored):
                next_day, next_sc = scored[j]
                gap = next_day - end
                if next_sc >= min_score:
                    end = next_day
                    max_sc = max(max_sc, next_sc)
                    j += 1
                elif gap <= 2 and j + 1 < len(scored) and scored[j + 1][1] >= min_score:
                    j += 1
                else:
                    break
            if end - start >= 1:
                mn = MONTH_NAMES_GEN[month]
                dates_str = f"{start}–{end} {mn}" if start != end else f"{start} {mn}"
                windows.append({
                    "dates": dates_str,
                    "score": max_sc,
                    "start": start,
                    "end": end,
                    "days": list(range(start, end + 1)),
                })
            i = j
        else:
            i += 1

    windows.sort(key=lambda x: x["score"], reverse=True)
    return windows


def find_avoid_windows(month_data: list, activity: str, max_score: int = -2) -> list:
    """Find date ranges where score for activity <= max_score."""
    month = _month_num(month_data[0])
    scored = []
    for d in month_data:
        scores = score_day(d)
        sc = scores.get(activity, 0)
        scored.append((_day_num(d), sc))

    windows = []
    i = 0
    while i < len(scored):
        day_num, sc = scored[i]
        if sc <= max_score:
            start = day_num
            end = day_num
            min_sc = sc
            j = i + 1
            while j < len(scored):
                next_day, next_sc = scored[j]
                gap = next_day - end
                if next_sc <= max_score:
                    end = next_day
                    min_sc = min(min_sc, next_sc)
                    j += 1
                elif gap <= 2 and j + 1 < len(scored) and scored[j + 1][1] <= max_score:
                    j += 1
                else:
                    break
            if end - start >= 0:
                mn = MONTH_NAMES_GEN[month]
                dates_str = f"{start}–{end} {mn}" if start != end else f"{start} {mn}"
                windows.append({
                    "dates": dates_str,
                    "score": min_sc,
                    "start": start,
                    "end": end,
                })
            i = j
        else:
            i += 1
    return windows


def get_period_overview(month_data: list) -> list:
    """Divide month into meaningful periods based on actual lunar phase transitions."""
    month = _month_num(month_data[0])
    mn = MONTH_NAMES_GEN[month]
    days_count = len(month_data)

    # --- Збираємо ключові події ---
    events = {}  # day_num -> list of event strings

    prev_phase = None
    for d in month_data:
        day = _day_num(d)
        phase = d.get("moon_phase")
        retro = d.get("mercury_retrograde")

        if phase != prev_phase:
            if phase == "new":
                events.setdefault(day, []).append("new_moon")
            elif phase == "full":
                events.setdefault(day, []).append("full_moon")
            elif phase == "first_quarter":
                events.setdefault(day, []).append("first_quarter")
            elif phase == "last_quarter":
                events.setdefault(day, []).append("last_quarter")
            elif phase == "waxing_crescent" and prev_phase == "new":
                events.setdefault(day, []).append("waxing_start")
            elif phase == "waning_gibbous" and prev_phase == "full":
                events.setdefault(day, []).append("waning_start")
            elif phase == "balsamic":
                events.setdefault(day, []).append("balsamic")
        prev_phase = phase

    # Межі відрізків — дні ключових подій
    boundary_days = sorted(set([1] + list(events.keys()) + [days_count]))

    # Мерджимо суміжні межі що стоять менш ніж 3 дні окремо
    merged = [boundary_days[0]]
    for b in boundary_days[1:]:
        if b - merged[-1] >= 3:
            merged.append(b)
    merged.append(days_count + 1)

    # --- Будуємо відрізки ---
    def avg_score(slice_):
        vals = [get_overall_score(score_day(d)) for d in slice_]
        return sum(vals) / len(vals) if vals else 0

    def retro_days_in(slice_):
        return sum(1 for d in slice_ if d.get("mercury_retrograde"))

    def voc_days_in(slice_):
        return sum(1 for d in slice_ if d.get("moon_voc"))

    periods = []
    for i in range(len(merged) - 1):
        start_day = merged[i]
        end_day = merged[i + 1] - 1
        if end_day < start_day:
            continue

        slice_ = [d for d in month_data if start_day <= _day_num(d) <= end_day]
        if not slice_:
            continue

        avg = avg_score(slice_)
        retro = retro_days_in(slice_)
        voc = voc_days_in(slice_)
        period_events = []
        for day in range(start_day, end_day + 1):
            period_events += events.get(day, [])

        dates_str = f"{start_day}–{end_day} {mn}" if start_day != end_day else f"{start_day} {mn}"

        # Визначаємо тему за подіями і score
        parts = []

        if "new_moon" in period_events:
            parts.append("🌑 Новий місяць — час нових намірів і починань")
        elif "full_moon" in period_events:
            parts.append("🌕 Повний місяць — емоційний пік, кульмінація справ")
        elif "first_quarter" in period_events:
            parts.append("🌓 Перша чверть — подолання першого опору")
        elif "last_quarter" in period_events:
            parts.append("🌗 Остання чверть — час підсумків і відпускання")
        elif "balsamic" in period_events:
            parts.append("🌘 Бальзамічна фаза — відпочинок, не починати нового")
        elif "waxing_start" in period_events:
            parts.append("🌒 Місяць росте — сприятливо для дій і просування")
        elif "waning_start" in period_events:
            parts.append("🌖 Місяць спадає — завершення, аналіз, відпочинок")

        if retro > len(slice_) // 2:
            parts.append("☿ Меркурій ретро — перевіряйте деталі, не підписуйте")
        if voc > len(slice_) // 2:
            parts.append("🌀 Багато VOC — плануйте важливе заздалегідь")

        if not parts:
            if avg > 3:
                parts.append("Активна, сприятлива фаза для дій")
            elif avg > 1:
                parts.append("Помірний темп, обирайте моменти")
            elif avg > -1:
                parts.append("Нейтральний фон, без різких кроків")
            else:
                parts.append("Краще уникати великих рішень")

        theme = " · ".join(parts)
        periods.append({"period": dates_str, "theme": theme})

    return periods


def get_month_theme(month_data: list, birth_data: dict) -> dict:
    """Determine main astrological theme of the month based on dominant patterns."""
    all_scores = {act: 0 for act in ACTIVITY_LABELS}
    retro_planets = set()
    voc_days = 0
    full_moon_days = []
    new_moon_days = []
    month = _month_num(month_data[0])
    year = int(month_data[0]["date"].split("-")[0])

    for d in month_data:
        scores = score_day(d)
        for act, sc in scores.items():
            all_scores[act] += sc
        for p in ["mercury", "venus", "mars", "jupiter", "saturn"]:
            if d.get(f"{p}_retrograde"):
                retro_planets.add(p)
        if d.get("moon_voc"):
            voc_days += 1
        if d.get("moon_phase") == "full":
            full_moon_days.append(_day_num(d))
        if d.get("moon_phase") == "new":
            new_moon_days.append(_day_num(d))

    sorted_acts = sorted(all_scores.items(), key=lambda x: x[1], reverse=True)
    top_acts = [a for a, _ in sorted_acts[:3]]
    worst_acts = [a for a, s in sorted_acts if s < 0]

    mn = MONTH_NAMES_UA[month]
    mn_gen = MONTH_NAMES_GEN[month]

    THEMES = {
        ("negotiations", "content_publishing", "work_technical"): {
            "title": "Місяць комунікацій і дій",
            "subtitle": "ясність думки, переконлива мова, видимість результатів",
            "mantra": f"Я говорю — мене чують. Я дію — результат видно.",
        },
        ("finance", "new_beginnings", "work_technical"): {
            "title": "Закладання нового фундаменту",
            "subtitle": "не про хаотичний ривок, а про стабілізацію і ріст",
            "mantra": f"Я не виживаю. Я починаю будувати.",
        },
        ("rest_reflection", "health_body"): {
            "title": "Місяць відновлення і переосмислення",
            "subtitle": "тіло і психіка просять уваги — варто прислухатись",
            "mantra": f"Зупинитись — це теж рух.",
        },
        ("finance", "negotiations"): {
            "title": "Місяць фінансових рішень",
            "subtitle": "гроші, угоди і стратегії виходять на перший план",
            "mantra": f"Чіткість у домовленостях — основа для зростання.",
        },
    }

    title = f"Місяць рівноваги та точності"
    subtitle = "важливо обирати правильні моменти для правильних дій"
    mantra = f"Не все одразу — але кожне вчасно."

    for key_acts, theme_data in THEMES.items():
        if all(a in top_acts for a in key_acts[:2]):
            title = theme_data["title"]
            subtitle = theme_data["subtitle"]
            mantra = theme_data["mantra"]
            break

    core_themes = [ACTIVITY_LABELS[a] for a in top_acts]

    bullets = []
    name = birth_data.get("name", "Ти")
    if "negotiations" in top_acts or "content_publishing" in top_acts:
        bullets.append(f"сприятливий час для переговорів і публічності")
    if "finance" in top_acts:
        bullets.append(f"фінансові рішення мають підтримку планет")
    if "new_beginnings" in top_acts:
        bullets.append(f"нові проєкти і починання можуть злетіти")
    if "rest_reflection" in top_acts:
        bullets.append(f"тіло і психіка просять відновлення")
    if "mercury" in retro_planets:
        bullets.append(f"Меркурій ретроградний — перевіряйте деталі, не поспішайте з підписами")
    if voc_days > 10:
        bullets.append(f"багато Місяць-без-курсу: плануйте важливе заздалегідь")
    if full_moon_days:
        bullets.append(f"Повний місяць {full_moon_days[0]} {mn_gen} — пік емоцій і кульмінація справ")

    if not bullets:
        bullets = ["рівномірний розподіл енергії протягом місяця"]

    return {
        "title": title,
        "subtitle": subtitle,
        "core_themes": core_themes,
        "mantra": mantra,
        "bullets": bullets,
        "retro_planets": list(retro_planets),
        "voc_days": voc_days,
        "full_moon_days": full_moon_days,
        "new_moon_days": new_moon_days,
        "month_name": mn,
        "year": year,
    }


def get_strongest_day(month_data: list) -> dict:
    """Find the single best day of the month."""
    month = _month_num(month_data[0])
    best = None
    best_score = -99
    for d in month_data:
        scores = score_day(d)
        overall = get_overall_score(scores)
        if overall > best_score:
            best_score = overall
            best = (d, scores, overall)

    if not best:
        return {}

    d, scores, overall = best
    day_num = _day_num(d)
    mn = MONTH_NAMES_GEN[month]
    year = int(d["date"].split("-")[0])

    sorted_acts = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_for = [ACTIVITY_LABELS[a] for a, s in sorted_acts[:3] if s > 0]

    from engine.lunar import get_phase_name_ua, get_sign_name_ua
    phase_name = get_phase_name_ua(d["moon_phase"])
    sign_name = get_sign_name_ua(d["moon_sign"])

    return {
        "date": f"{day_num} {mn} {year}",
        "day_num": day_num,
        "score": overall,
        "best_for": best_for,
        "moon": f"{phase_name} у {sign_name}",
        "mercury_direct": not d.get("mercury_retrograde"),
        "moon_voc": d.get("moon_voc"),
    }


def get_danger_zones(month_data: list) -> list:
    """Find multi-day periods that are bad across multiple activities."""
    month = _month_num(month_data[0])
    mn = MONTH_NAMES_GEN[month]

    zones = []
    i = 0
    while i < len(month_data):
        d = month_data[i]
        scores = score_day(d)
        overall = get_overall_score(scores)
        if overall <= -2:
            start = _day_num(d)
            end = start
            reasons = []
            avoids = []

            if d.get("mercury_retrograde"):
                reasons.append("Меркурій ретроградний")
                avoids.append("підписання документів")
            if d.get("moon_voc"):
                reasons.append("Місяць без курсу")
                avoids.append("важливі рішення")
            if scores.get("finance", 0) <= -3:
                avoids.append("фінансові операції")
            if scores.get("negotiations", 0) <= -3:
                avoids.append("переговори і угоди")

            j = i + 1
            while j < len(month_data):
                next_d = month_data[j]
                next_scores = score_day(next_d)
                next_overall = get_overall_score(next_scores)
                if next_overall <= -1:
                    end = _day_num(next_d)
                    j += 1
                else:
                    break

            if end - start >= 1:
                dates_str = f"{start}–{end} {mn}"
                if not reasons:
                    reasons.append("складне планетарне поєднання")
                if not avoids:
                    avoids.append("важливі починання")
                zones.append({
                    "dates": dates_str,
                    "reasons": reasons,
                    "avoid": avoids[:3],
                    "tip": "Використайте цей час для планування і відпочинку",
                })
            i = j
        else:
            i += 1

    return zones[:3]


_GOAL_CAT_ACTIVITY = {
    "documents":     "work_technical",
    "personal":      "new_beginnings",
    "finance":       "finance",
    "negotiations":  "negotiations",
    "career":        "negotiations",
    "learning":      "work_technical",
    "purchase":      "finance",
    "health":        "health_body",
}

_WINDOW_TYPE_UA = {
    "confusion":      ("🌫", "Туман у рішеннях", "Ризик прийняти рішення під тиском ілюзій або чужих очікувань."),
    "overreach_risk": ("🔭", "Ризик переоцінки", "Відчуття 'можу більше ніж є ресурс' — фільтруй пропозиції жорстко."),
    "transformation": ("⚡", "Глибока трансформація", "Незворотні зміни у фінансах або цінностях — краще ти ведеш процес."),
    "restructuring":  ("🔩", "Перебудова структури", "Час переосмислити і зробити міцніше — не поспіхом, а надовго."),
    "energy_boost":   ("🔥", "Прилив енергії", "Вікно підвищеної дієвості — зроби те, що давно чекає."),
    "opportunity":    ("🟢", "Відкрита можливість", "Рухайся — відгук буде кращим ніж зазвичай."),
    "pressure":       ("🔩", "Зовнішній тиск", "Ззовні приходять обмеження — прийми як дані і працюй в рамках."),
    "breakthrough":   ("⚡", "Несподіваний прорив", "Щось що давно дозрівало — може вирватись назовні."),
}


def _get_best_single_days(month_data: list, activity: str, top_n: int = 3) -> list:
    """Return top N single days for activity, preferring no VOC and no Mercury retrograde."""
    scored = []
    for d in month_data:
        sc = score_day(d).get(activity, 0)
        if sc <= 0:
            continue
        clean = not d.get("moon_voc") and not d.get("mercury_retrograde")
        scored.append((_day_num(d), sc, clean))
    scored.sort(key=lambda x: (x[2], x[1]), reverse=True)
    result = []
    for day_num, sc, clean in scored[:top_n]:
        note = "" if clean else "⚠ VOC або ретро"
        result.append({"day": day_num, "score": sc, "note": note})
    return result


def build_goal_sections(month_data: list, goals: list, birth_data: dict) -> list:
    """Build personalized goal cards for active goals."""
    from engine.goal_matcher import (
        find_best_windows_in_month, find_avoid_windows_for_goal,
        get_warnings_for_goal, PRIORITY_EMOJI
    )
    from datetime import datetime

    month = _month_num(month_data[0])
    year = int(month_data[0]["date"].split("-")[0])

    active = sorted(
        [g for g in goals if g.get("status") == "active"],
        key=lambda g: g.get("priority", 9)
    )

    goal_cards = []
    for goal in active:
        favorable = find_best_windows_in_month(goal, month_data)
        avoid = find_avoid_windows_for_goal(goal, month_data)
        windows = sorted(favorable + avoid, key=lambda w: w["start"])
        warnings = get_warnings_for_goal(goal, month_data)
        priority = goal.get("priority", 3)
        emoji = PRIORITY_EMOJI.get(priority, "⚪")

        cat = goal.get("category", "personal")
        activity = _GOAL_CAT_ACTIVITY.get(cat, "new_beginnings")
        best_days = _get_best_single_days(month_data, activity, top_n=3)

        deadline_str = ""
        if goal.get("deadline"):
            try:
                dl = datetime.strptime(goal["deadline"], "%Y-%m-%d")
                if dl.year == year and dl.month == month:
                    deadline_str = f"{dl.day} {MONTH_NAMES_GEN[dl.month]}"
            except Exception:
                pass

        goal_cards.append({
            "id": goal["id"],
            "title": goal["title"],
            "category": cat,
            "priority": priority,
            "priority_emoji": emoji,
            "deadline": deadline_str,
            "notes": goal.get("notes", ""),
            "windows": windows,
            "warnings": warnings,
            "has_windows": len(windows) > 0,
            "best_days": best_days,
        })

    return goal_cards


def get_critical_windows_display(critical_windows: list) -> list:
    """Convert raw critical_windows to display-ready dicts with Ukrainian labels."""
    result = []
    for cw in critical_windows:
        wtype = cw.get("type", "")
        icon, label, desc = _WINDOW_TYPE_UA.get(wtype, ("⚠️", "Важливий транзит", "Зверніть увагу."))
        peak = _format_peak(cw.get("peak_date", ""))
        intensity = cw.get("intensity", 0)
        status = cw.get("status", "")
        status_ua = "наростає" if status == "applying" else ("спадає" if status == "separating" else "")
        result.append({
            "icon": icon,
            "label": label,
            "desc": desc,
            "peak": peak,
            "intensity": intensity,
            "status_ua": status_ua,
            "retro": cw.get("retrograde", False),
        })
    result.sort(key=lambda x: -x["intensity"])
    return result[:5]


def get_weekly_focus(month_data: list, transit_narratives: list) -> Optional[dict]:
    """Return focus for the current calendar week within this month."""
    from datetime import date, timedelta
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    month = _month_num(month_data[0])
    year = int(month_data[0]["date"].split("-")[0])

    week_days = [
        d for d in month_data
        if week_start.day <= _day_num(d) <= week_end.day
        and _month_num(d) == month
    ]
    if not week_days:
        return None

    mn_gen = MONTH_NAMES_GEN[month]
    start_d = _day_num(week_days[0])
    end_d = _day_num(week_days[-1])
    week_str = f"{start_d}–{end_d} {mn_gen}"

    avg_scores: dict = {}
    for act in ACTIVITY_LABELS:
        vals = [score_day(d).get(act, 0) for d in week_days]
        avg_scores[act] = sum(vals) / len(vals) if vals else 0

    top_act = max(avg_scores, key=lambda a: avg_scores[a])
    top_score = avg_scores[top_act]

    WEEKDAY_UA = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
    day_summaries = []
    for d in week_days:
        sc = score_day(d)
        overall = get_overall_score(sc)
        day_num = _day_num(d)
        try:
            wd = date(year, month, day_num).weekday()
            wd_ua = WEEKDAY_UA[wd]
        except Exception:
            wd_ua = ""
        is_today = (date(year, month, day_num) == today)
        day_summaries.append({
            "day": day_num,
            "weekday": wd_ua,
            "score": overall,
            "is_today": is_today,
            "voc": d.get("moon_voc", False),
            "retro": d.get("mercury_retrograde", False),
        })

    voc_days = [ds["day"] for ds in day_summaries if ds["voc"]]
    retro_days = [ds["day"] for ds in day_summaries if ds["retro"]]

    best_day = max(day_summaries, key=lambda ds: ds["score"])
    worst_day = min(day_summaries, key=lambda ds: ds["score"])

    actions = []
    act_label = ACTIVITY_LABELS.get(top_act, top_act)
    if top_score >= 2:
        actions.append(f"Найкращий час для: {act_label} — не відкладай")
    if best_day["score"] >= 3 and not best_day["voc"]:
        actions.append(f"{best_day['weekday']} {best_day['day']} — пікова дієвість, плануй важливе саме тут")
    if worst_day["score"] <= -2:
        actions.append(f"{worst_day['weekday']} {worst_day['day']} — краще уникати великих рішень")
    if voc_days:
        voc_str = ", ".join(str(d) for d in voc_days)
        actions.append(f"VOC (Місяць без курсу) {voc_str} — не починай нового в цей час")
    if retro_days:
        actions.append("Меркурій ретроградний — перевіряй деталі, не підписуй без перечитування")
    if not actions:
        actions.append("Рівна тижня — рухайся за планом без різких кроків")

    top_narratives = transit_narratives[:2] if transit_narratives else []

    return {
        "week_str": week_str,
        "day_summaries": day_summaries,
        "actions": actions[:4],
        "top_narratives": top_narratives,
        "best_day": best_day,
    }


def build_report_sections(month_data: list, birth_data: dict, goals: list = None, forecast_data: dict = None) -> dict:
    """Main function — builds full structure for the report template."""
    month_theme = get_month_theme(month_data, birth_data)
    period_overview = get_period_overview(month_data)
    strongest_day = get_strongest_day(month_data)
    danger_zones = get_danger_zones(month_data)

    SPHERE_ACTIVITIES = {
        "negotiations": {
            "label": "Переговори / Керівництво / Вплив",
            "emoji": "💼",
            "color": "#3b82f6",
            "activity": "negotiations",
        },
        "finance": {
            "label": "Фінанси / Покупки / Рішення",
            "emoji": "💰",
            "color": "#f59e0b",
            "activity": "finance",
        },
        "new_beginnings": {
            "label": "Нові починання",
            "emoji": "🚀",
            "color": "#22c55e",
            "activity": "new_beginnings",
        },
        "health_body": {
            "label": "Здоров'я / Відновлення",
            "emoji": "🧘",
            "color": "#06b6d4",
            "activity": "health_body",
        },
        "housing": {
            "label": "Переїзд / Житло",
            "emoji": "🏡",
            "color": "#a855f7",
            "activity": "new_beginnings",
        },
        "documents": {
            "label": "Документи / Бюрократія",
            "emoji": "🚗",
            "color": "#6b7280",
            "activity": "work_technical",
        },
    }

    sections = {}
    for key, meta in SPHERE_ACTIVITIES.items():
        act = meta["activity"]
        windows = find_windows(month_data, act, min_score=2)
        avoid = find_avoid_windows(month_data, act, max_score=-2)

        window_details = []
        for w in windows[:3]:
            days_in_window = [d for d in month_data if w["start"] <= _day_num(d) <= w["end"]]

            # Найкращий день без VOC і без ретро — для позитивного tip
            best_clean = None
            for d in days_in_window:
                sc = score_day(d).get(act, 0)
                if not d.get("moon_voc") and not d.get("mercury_retrograde"):
                    if best_clean is None or sc > best_clean[1]:
                        best_clean = (d, sc)

            # Підрахунок VOC і ретро днів у вікні
            voc_days = sum(1 for d in days_in_window if d.get("moon_voc"))
            retro_days = sum(1 for d in days_in_window if d.get("mercury_retrograde"))
            total = len(days_in_window)

            tip = ""
            if best_clean:
                tip = "Місяць активний — ідеальний час для дій"
            elif retro_days == total:
                tip = "Весь відрізок — Меркурій ретро, діяти обережно"

            # Попередження — окремо від tip
            warnings = []
            if voc_days > 0:
                warnings.append(f"⚠ {voc_days} VOC-{'день' if voc_days == 1 else 'дні'} у вікні — уникайте початків саме тоді")
            if retro_days > 0 and retro_days < total:
                warnings.append(f"⚠ Меркурій ретро {retro_days}д — перевіряйте деталі")

            sc = w["score"]
            window_details.append({
                "dates": w["dates"],
                "score": sc,
                "emoji": "🔥" if sc >= 6 else ("🟢" if sc >= 3 else "🟡"),
                "level": "hot" if sc >= 6 else ("good" if sc >= 3 else "mild"),
                "reasons": [tip] if tip else [],
                "warnings": warnings,
                "start": w["start"],
                "end": w["end"],
            })

        avoid_details = []
        for a in avoid[:2]:
            avoid_details.append({
                "dates": a["dates"],
                "score": a["score"],
                "emoji": "❌",
                "level": "avoid",
                "reasons": [],
                "warnings": [],
                "start": a["start"],
                "end": a["end"],
            })

        all_windows = sorted(window_details + avoid_details, key=lambda w: w["start"])

        sections[key] = {
            "label": meta["label"],
            "emoji": meta["emoji"],
            "color": meta["color"],
            "windows": all_windows,
            "has_windows": len(all_windows) > 0,
        }

    summary_table = []
    for key, sec in sections.items():
        if sec["windows"]:
            best_dates = ", ".join(w["dates"].split(" ")[0] for w in sec["windows"][:2])
            summary_table.append({
                "sphere": sec["emoji"] + " " + sec["label"].split("/")[0].strip(),
                "best": best_dates,
            })
    avoid_all = get_danger_zones(month_data)
    if avoid_all:
        avoid_dates = ", ".join(z["dates"].split(" ")[0] for z in avoid_all[:2])
        summary_table.append({
            "sphere": "⚠️ Обережність",
            "best": avoid_dates,
        })

    name = birth_data.get("name", "")

    goal_cards = build_goal_sections(month_data, goals or [], birth_data) if goals else []

    # Transit narratives + critical windows from interpretation package
    transit_narratives: list = []
    critical_windows_display: list = []
    if forecast_data:
        top_transits = forecast_data.get("top_transits", [])
        transit_narratives = get_transit_narratives(top_transits)
        transit_theme = get_month_theme_from_transits(top_transits)
        if transit_theme:
            month_theme["title"]    = transit_theme["title"]
            month_theme["subtitle"] = transit_theme["subtitle"]
        raw_cw = forecast_data.get("critical_windows", [])
        critical_windows_display = get_critical_windows_display(raw_cw)

    weekly_focus = get_weekly_focus(month_data, transit_narratives)

    return {
        "month_theme": month_theme,
        "period_overview": period_overview,
        "sections": sections,
        "danger_zones": danger_zones,
        "strongest_day": strongest_day,
        "summary_table": summary_table,
        "name": name,
        "goal_cards": goal_cards,
        "transit_narratives": transit_narratives,
        "critical_windows": critical_windows_display,
        "weekly_focus": weekly_focus,
    }
