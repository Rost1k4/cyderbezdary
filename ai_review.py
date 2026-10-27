"""AI-оцінка матчу через Google Gemini API: повний розбір (консоль) і мега-короткий (сайт)."""
import time

import requests

import config
import opendota

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = (10, 45)  # секунд: з'єднання, очікування відповіді


class AIError(Exception):
    """Помилка AI-запиту (текст призначений для показу користувачу)."""


class AITimeout(AIError):
    """Gemini не встигла відповісти (пробуємо наступну модель)."""


SYSTEM_PROMPT = """Ти — досвідчений і доброзичливий аналітик Dota 2, тренер. Тобі дають дані одного матчу.
Пиши українською, живо, але по ділу. Спирайся ТІЛЬКИ на надані дані, нічого не вигадуй
і не додумуй мотивів гравців. Блок «ТОЧНІ ПІДРАХУНКИ» найнадійніший: цифри звідти бери як є.
Якщо даних для висновку бракує (матч не розібраний), чесно скажи про це.
Оцінюй ігрові рішення, а не людей: без образ і глузувань, критика має бути конструктивною.
Будівлі goodguys = Radiant, badguys = Dire.

Структура відповіді:
1. Перебіг гри — коротко по фазах (лайнінг, мідгейм, лейт), як змінювалась перевага по золоту.
2. Переломний момент — коли і чому гра зламалась.
3. Де гра пішла не так — конкретні моменти (час), смерті/рішення, які коштували найдорожче.
4. Хто старався найбільше — хто тягнув команду попри обставини.
5. MVP матчу — з обґрунтуванням цифрами.
6. Що купити — для кожного гравця (або ключових) який предмет був би кращим за те, що він купив, і чому.
7. Оцінка гравців — по кожному 1-10 і одне речення.
"""

SHORT_PROMPT = """Ти — доброзичливий аналітик Dota 2 на студентському турнірі. Тобі дають дані одного матчу.
Пиши українською, МЕГА коротко: рівно 4 рядки, разом до 70 слів, без вступів і заголовків.
Спирайся ТІЛЬКИ на надані дані (блок «ТОЧНІ ПІДРАХУНКИ» найнадійніший), нічого не вигадуй
і не додумуй мотивів. Оцінюй ігрові рішення, а не людей: без образ і глузувань.
Radiant = goodguys, Dire = badguys.
Формат (рівно так, кожен пункт з нового рядка):
🏁 <хто виграв і чому, одне речення>
🔄 <переломний момент із часом>
⭐ MVP: <герой [гравець]> — <ключові цифри>
📉 Зона росту: <герой [гравець]> — <що саме можна було зробити краще>
Якщо даних для рядка бракує, пиши "н/д" замість вигадок."""


def _mmss(t) -> str:
    t = int(t)
    sign = "-" if t < 0 else ""
    t = abs(t)
    return f"{sign}{t // 60}:{t % 60:02d}"


def _is_radiant(p: dict) -> bool:
    if "isRadiant" in p:
        return bool(p["isRadiant"])
    return p.get("player_slot", 0) < 128


def _label(p: dict, heroes: dict) -> str:
    hero = heroes.get(p.get("hero_id"), f"Hero#{p.get('hero_id')}")
    name = p.get("personaname") or p.get("name") or "Анонім"
    side = "R" if _is_radiant(p) else "D"
    return f"{hero} [{name}, {side}]"


def _facts(match: dict, players: list, heroes: dict) -> list:
    """Заздалегідь пораховані факти: модель бере їх як є, а не вгадує з сирих рядків."""
    out = []
    adv = match.get("radiant_gold_adv") or []
    if len(adv) >= 2:
        hi = max(range(len(adv)), key=lambda i: adv[i])
        lo = min(range(len(adv)), key=lambda i: adv[i])
        parts = []
        parts.append(f"Radiant максимум +{int(adv[hi])} на {hi}хв" if adv[hi] > 0 else "Radiant по золоту не вів")
        parts.append(f"Dire максимум +{int(-adv[lo])} на {lo}хв" if adv[lo] < 0 else "Dire по золоту не вів")
        out.append("Макс. перевага по золоту: " + "; ".join(parts))
        best = None
        for i in range(5, len(adv)):
            d = adv[i] - adv[i - 5]
            if best is None or abs(d) > abs(best[0]):
                best = (d, i - 5, i)
        if best and abs(best[0]) >= 1000:
            side = "Radiant" if best[0] > 0 else "Dire"
            out.append(f"Найбільший перепад за 5 хв: {best[1]}–{best[2]}хв, на користь {side} "
                       f"(+{abs(int(best[0]))} золота)")

    def top(key, title, reverse=True):
        cand = [p for p in players if isinstance(p.get(key), (int, float))]
        if not cand:
            return
        p = (max if reverse else min)(cand, key=lambda x: x[key])
        out.append(f"{title}: {_label(p, heroes)} — {int(p[key])}")

    top("hero_damage", "Найбільше шкоди героям")
    top("gold_per_min", "Найвищий GPM")
    top("deaths", "Найбільше смертей")
    top("tower_damage", "Найбільше шкоди вежам")
    return out


def build_summary(match: dict, heroes: dict, items: dict, hero_ids: dict, brief: bool = False) -> str:
    players = match["players"]
    labels = {p.get("hero_id"): _label(p, heroes) for p in players}
    by_internal = {k: labels.get(v, k) for k, v in hero_ids.items()}

    lines = []
    win = {True: "Radiant", False: "Dire"}.get(match.get("radiant_win"), "н/д")
    lines.append(f"Переможець: {win}")
    lines.append(f"Тривалість: {_mmss(match.get('duration', 0))}")
    lines.append(f"Рахунок: Radiant {match.get('radiant_score')} : {match.get('dire_score')} Dire")
    lines.append("R = Radiant, D = Dire\n")
    facts = _facts(match, players, heroes)
    if facts:
        lines.append("ТОЧНІ ПІДРАХУНКИ:")
        lines.extend("- " + f for f in facts)
        lines.append("")

    # Перевага по золоту (+ = Radiant веде)
    adv = match.get("radiant_gold_adv")
    if adv:
        pts = [f"{i}хв:{int(v):+d}" for i, v in enumerate(adv) if i % 5 == 0]
        lines.append("Перевага Radiant по золоту: " + ", ".join(pts) + "\n")

    # Гравці
    lines.append("ГРАВЦІ:")
    for p in players:
        item_ids = [p.get(f"item_{i}") for i in range(6)]
        item_names = [items.get(i, f"#{i}") for i in item_ids if i]
        neutral = items.get(p.get("item_neutral"), None) if p.get("item_neutral") else None
        stats = {
            "lvl": p.get("level"), "K/D/A": f"{p.get('kills')}/{p.get('deaths')}/{p.get('assists')}",
            "LH/DN": f"{p.get('last_hits')}/{p.get('denies')}",
            "GPM": p.get("gold_per_min"), "XPM": p.get("xp_per_min"),
            "networth": p.get("net_worth"), "hero_dmg": p.get("hero_damage"),
            "tower_dmg": p.get("tower_damage"), "healing": p.get("hero_healing"),
            "lane_role": p.get("lane_role"), "obs": p.get("obs_placed"),
            "sen": p.get("sen_placed"), "buybacks": p.get("buyback_count"),
            "tf_part": p.get("teamfight_participation"),
        }
        stats = {k: v for k, v in stats.items() if v is not None}
        lines.append(f"- {_label(p, heroes)}: {stats}")
        lines.append(f"  Предмети: {', '.join(item_names) or 'немає'}"
                     + (f"; нейтральний: {neutral}" if neutral else ""))

        plog = p.get("purchase_log") or []
        if plog and not brief:
            bought = [f"{_mmss(x['time'])} {items_name(x['key'])}" for x in plog
                      if not x["key"].startswith(("tango", "clarity", "flask", "ward", "smoke", "dust", "tpscroll"))]
            lines.append("  Покупки: " + ", ".join(bought[:25]))

    # Хронологія вбивств
    kills = []
    for p in players:
        for k in p.get("kills_log") or []:
            victim = by_internal.get(k.get("key"), k.get("key"))
            kills.append((k["time"], _label(p, heroes), victim))
    kills.sort()
    if kills:
        lines.append("\nВБИВСТВА (час, вбивця -> жертва):")
        for t, killer, victim in kills[:(60 if brief else 150)]:
            lines.append(f"{_mmss(t)} {killer} -> {victim}")

    # Цілі: вежі, Рошан тощо
    objs = match.get("objectives") or []
    if objs:
        lines.append("\nЦІЛІ:")
        for o in objs[:(25 if brief else 80)]:
            extra = {k: v for k, v in o.items() if k not in ("time", "type") and v is not None}
            lines.append(f"{_mmss(o.get('time', 0))} {o.get('type')} {extra}")

    return "\n".join(lines)


def items_name(key: str) -> str:
    return key.replace("item_", "")


_CONST_CACHE: dict = {}


def _constants() -> tuple:
    """Предмети та внутрішні імена героїв; невдалі запити не кешуємо."""
    if "items" not in _CONST_CACHE:
        items = opendota.get_item_names()
        if items:
            _CONST_CACHE["items"] = items
        else:
            return {}, opendota.get_hero_internal_names()
    if "hero_ids" not in _CONST_CACHE:
        hero_ids = opendota.get_hero_internal_names()
        if hero_ids:
            _CONST_CACHE["hero_ids"] = hero_ids
        else:
            return _CONST_CACHE["items"], {}
    return _CONST_CACHE["items"], _CONST_CACHE["hero_ids"]


def _error_text(resp) -> str:
    """Короткий опис помилки з тіла відповіді Gemini."""
    try:
        return str(resp.json()["error"]["message"])
    except (ValueError, KeyError, TypeError):
        return ""


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason")
        if reason:
            raise AIError(f"Gemini відхилила запит ({reason}).")
        raise AIError("Gemini не повернула відповіді. Спробуйте ще раз.")
    cand = candidates[0]
    parts = (cand.get("content") or {}).get("parts") or []
    # «роздуми» моделі (thought) користувачу не показуємо
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    if not text:
        if cand.get("finishReason") == "MAX_TOKENS":
            raise AIError("Модель вичерпала ліміт токенів до відповіді. Спробуйте ще раз.")
        raise AIError("Модель повернула порожню відповідь. Спробуйте ще раз.")
    return text


RETRY_CODES = (429, 500, 503, 404)  # після цих відповідей пробуємо наступну модель
ATTEMPTS_PER_MODEL = 3              # 500/503 повторюємо з паузою 2 с, 4 с


def _post(model: str, key: str, body: dict):
    """Один запит до моделі; короткі збої Google (500/503) повторює з наростаючою паузою."""
    resp = None
    for attempt in range(ATTEMPTS_PER_MODEL):
        try:
            resp = requests.post(API_URL.format(model=model), json=body, timeout=TIMEOUT,
                                 headers={"x-goog-api-key": key})
        except requests.exceptions.Timeout:
            raise AITimeout("Gemini не відповіла вчасно. Спробуйте ще раз.")
        except requests.exceptions.ConnectionError:
            raise AIError("Немає з'єднання з інтернетом або Gemini API недоступне.")
        except requests.exceptions.RequestException as e:
            raise AIError(f"Не вдалося звʼязатися з Gemini: {e}")
        if resp.status_code in (500, 503) and attempt < ATTEMPTS_PER_MODEL - 1:
            time.sleep(2 * (attempt + 1))
            continue
        break
    return resp


def _error_for(resp, model: str) -> AIError:
    code = resp.status_code
    details = _error_text(resp)
    if code in (400, 401, 403) and "key" in details.lower():
        return AIError("Gemini не прийняла API-ключ. Перевірте GEMINI_API_KEY.")
    if code == 403:
        return AIError("Доступ до Gemini API заборонено для цього ключа чи регіону.")
    if code == 404:
        return AIError(f"Модель «{model}» не знайдена. Задайте іншу змінною GEMINI_MODEL.")
    if code == 429:
        return AIError("Вичерпано ліміт безкоштовних запитів Gemini. "
                       "Зачекайте хвилину або спробуйте пізніше.")
    if code in (500, 503):
        return AIError("Gemini зараз перевантажена (спробовано кілька моделей). "
                       "Спробуйте за хвилину.")
    return AIError(f"Gemini повернула код {code}. {details}".strip())


# Для короткої відповіді «роздуми» моделі не потрібні. Різні покоління Gemini вимикають їх
# по-різному (бюджет 0 / рівень low), а деякі не вміють зовсім, тому пробуємо по черзі.
THINK_OPTIONS = ({"thinkingBudget": 0}, {"thinkingLevel": "low"}, None)
_THINK_CHOICE: dict = {}  # model -> варіант, який вже спрацював


def _post_adaptive(model: str, key: str, body: dict, fast: bool):
    options = THINK_OPTIONS if fast else (None,)
    if fast and model in _THINK_CHOICE:
        options = (_THINK_CHOICE[model],)
    resp = None
    for i, opt in enumerate(options):
        gen = dict(body["generationConfig"])
        if opt:
            gen["thinkingConfig"] = opt
        resp = _post(model, key, {**body, "generationConfig": gen})
        if resp.status_code == 200:
            if fast:
                _THINK_CHOICE[model] = opt
            return resp
        is_key_error = "key" in _error_text(resp).lower()
        if resp.status_code == 400 and not is_key_error and i < len(options) - 1:
            continue  # модель не прийняла цей варіант: пробуємо наступний
        break
    return resp


def _ask(system: str, user: str, max_tokens: int, temperature: float = 0.3,
         fast: bool = True) -> str:
    key = config.api_key()
    if not key:
        raise AIError(
            "Не задано ключ Gemini. Створіть його на https://aistudio.google.com/apikey "
            "і додайте змінну середовища GEMINI_API_KEY (або файл config_local.py).")
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        # Сучасні моделі «думають» перед відповіддю, і ці токени входять у ліміт,
        # тому max_tokens беремо з запасом; довжину відповіді тримає промпт.
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
    }
    models = [config.model()]
    models += [m for m in config.fallback_models() if m not in models]

    first_error = None
    for model in models:
        try:
            resp = _post_adaptive(model, key, body, fast)
        except AITimeout as e:
            if first_error is None:
                first_error = e
            continue
        if resp.status_code == 200:
            try:
                return _extract_text(resp.json())
            except ValueError:
                raise AIError("Gemini повернула некоректну відповідь.")
        err = _error_for(resp, model)
        if first_error is None:
            first_error = err  # показуємо помилку основної моделі
        if resp.status_code not in RETRY_CODES:
            raise err  # напр. неправильний ключ: інша модель не допоможе
    raise first_error


def _prepare(match: dict, heroes: dict, brief: bool) -> str:
    items, hero_ids = _constants()
    summary = build_summary(match, heroes, items, hero_ids, brief=brief)
    if not opendota.is_parsed(match):
        summary += "\n\nУВАГА: матч не розібраний повністю, подій і покупок може бракувати."
    return summary


def _tidy_short(text: str) -> str:
    """Кожен пункт окремим абзацом: інакше Markdown склеїть рядки в один."""
    text = text.replace("```", "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n\n".join(lines)


def short_review(match: dict, heroes: dict) -> str:
    """Мега-коротка оцінка для сайту. Кидає AIError з готовим текстом."""
    return _tidy_short(_ask(SHORT_PROMPT, _prepare(match, heroes, brief=True), max_tokens=2048))


def review_match(match: dict, heroes: dict) -> None:
    """Повна оцінка для консолі (cli.py)."""
    print("\n" + "=" * 60)
    print("AI-ОЦІНКА МАТЧУ")
    print("=" * 60 + "\n")
    try:
        print(_ask(SYSTEM_PROMPT, _prepare(match, heroes, brief=False), max_tokens=8192, fast=False))
    except AIError as e:
        print(f"Помилка AI-запиту: {e}")
