"""Розпізнавання таблиці результатів матчу зі скріншота (Gemini або Ollama з vision-моделлю).

Без Streamlit: ключі й налаштування передає app.py. Результат: словник
{radiant_win, duration, radiant_score, dire_score, players: [...]}, який
адміністратор перевіряє й виправляє перед збереженням.
"""
import base64
import json
import re

import requests

import config

TIMEOUT = 350
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "google/gemini-2.5-flash"
OPENROUTER_FALLBACK_MODELS = ("google/gemma-4-31b-it:free",)
MAX_IMAGES = 4
MAX_BYTES = 8_000_000
ALLOWED_MIME = ("image/png", "image/jpeg", "image/webp")

NUM_KEYS = ("kills", "deaths", "assists", "last_hits", "denies",
            "gold_per_min", "xp_per_min", "hero_damage", "tower_damage")


class VisionError(Exception):
    """Помилка розпізнавання (текст призначений для показу користувачу)."""


PROMPT = """You read Dota 2 end-of-match screenshots (scoreboard / results screen).
The images may show different tabs of the SAME match: merge them into ONE record per player
(match rows by hero and nickname). Return ONLY valid JSON, no comments, exactly in this shape:
{
  "radiant_win": true | false | null,
  "duration": "MM:SS" | null,
  "radiant_score": integer | null,
  "dire_score": integer | null,
  "radiant_team": string | null,
  "dire_team": string | null,
  "players": [
   {"team": "radiant" | "dire", "name": string | null, "hero_name": string | null,
    "kills": integer | null, "deaths": integer | null, "assists": integer | null,
    "last_hits": integer | null, "denies": integer | null,
    "gold_per_min": integer | null, "xp_per_min": integer | null,
    "hero_damage": integer | null, "tower_damage": integer | null}
  ]
}
Rules:
- Radiant is the top group of 5 players (green side), Dire is the bottom group (red side).
- Determine the winner from the GREEN victory marker/highlight/badge on the result screen. The side with the green winner indicator wins, even if the other side has a larger number or score. Do NOT decide by comparing kills, score, K/D/A, or the largest number. If the green marker is not clearly visible, set radiant_win to null.
- If actual team/clan names are visible, return them as radiant_team and dire_team exactly as displayed; do not mistake player names or hero names for team names. If not visible, use null.
- name = the player nickname exactly as written. hero_name = the hero name as shown (any language), else null.
- last_hits and denies come from "LH/DN" style columns. Convert values like "12.3k" to 12300.
- Use null for anything you cannot read. NEVER guess or invent numbers.
- At most 10 players."""


# ------------------------------------------------------------ нормалізація
def _int(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip().lower().replace("\u00a0", "").replace(" ", "")
    if not s:
        return None
    mult = 1
    if s.endswith("k"):
        mult, s = 1000, s[:-1]
    if re.fullmatch(r"\d{1,3}(,\d{3})+", s):
        s = s.replace(",", "")
    s = s.replace(",", ".")
    try:
        return int(round(float(s) * mult))
    except ValueError:
        return None


def _win(v):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower() if v is not None else ""
    if s in ("true", "radiant", "radiant win", "radiant victory"):
        return True
    if s in ("false", "dire", "dire win", "dire victory"):
        return False
    return None


def _duration(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return "%d:%02d" % (int(v) // 60, int(v) % 60)
    s = str(v).strip() if v is not None else ""
    return s if re.fullmatch(r"\d{1,3}:\d{2}(:\d{2})?", s) else None


def _text(v):
    s = str(v).strip() if v is not None else ""
    return s or None


def normalize(d):
    """Приводить відповідь моделі до чистої структури; зайве відкидає."""
    if not isinstance(d, dict):
        raise VisionError("AI повернув дані в несподіваному форматі. Спробуйте ще раз.")
    players = []
    for p in (d.get("players") or [])[:10]:
        if not isinstance(p, dict):
            continue
        t = str(p.get("team") or "").strip().lower()
        row = {"team": "radiant" if t.startswith("rad") else "dire" if t.startswith("dir") else None,
               "name": _text(p.get("name")), "hero_name": _text(p.get("hero_name"))}
        for k in NUM_KEYS:
            row[k] = _int(p.get(k))
        players.append(row)
    for i, row in enumerate(players):  # якщо команду не визначено: перші 5 Radiant, решта Dire
        if row["team"] is None:
            row["team"] = "radiant" if i < 5 else "dire"
    return {"radiant_win": _win(d.get("radiant_win")), "duration": _duration(d.get("duration")),
            "radiant_score": _int(d.get("radiant_score")), "dire_score": _int(d.get("dire_score")),
            "radiant_team": _text(d.get("radiant_team")), "dire_team": _text(d.get("dire_team")),
            "players": players}


def parse(raw):
    """Текст відповіді моделі -> нормалізований словник."""
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise VisionError("AI не повернув таблицю. Спробуйте чіткіший скріншот.")
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        raise VisionError("AI повернув пошкоджені дані. Спробуйте ще раз.")
    out = normalize(data)
    if not out["players"]:
        raise VisionError("На скріншоті не знайдено гравців. Потрібен екран підсумків матчу.")
    return out


def empty_template():
    """Порожня таблиця для ручного заповнення: 5 Radiant + 5 Dire."""
    row = {k: None for k in NUM_KEYS}
    return {"radiant_win": None, "duration": None, "radiant_score": None, "dire_score": None,
            "radiant_team": None, "dire_team": None, "players": [dict(row, team=t, name=None, hero_name=None)
                        for t in ("radiant",) * 5 + ("dire",) * 5]}


# ------------------------------------------------------------ провайдери

def _openrouter(images, key, model, fallbacks=()):
    models = [model] + list(fallbacks)
    last_error = None
    for current_model in models:
        content = [{"type": "text", "text": PROMPT}]
        for data, mime in images:
            data_url = f"data:{mime};base64,{base64.b64encode(data).decode()}"
            content.append({"type": "image_url", "image_url": {"url": data_url}})

        payload = {
            "model": current_model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0,
        }
        try:
            resp = requests.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
                timeout=TIMEOUT,
            )
        except requests.exceptions.Timeout:
            last_error = VisionError("OpenRouter не відповів вчасно. Спробуйте ще раз.")
            continue
        except requests.exceptions.RequestException as e:
            last_error = VisionError(f"Не вдалося звʼязатися з OpenRouter: {e}")
            continue

        if resp.status_code == 200:
            try:
                return resp.json()["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError, ValueError):
                raise VisionError("OpenRouter не повернув коректну відповідь.")

        try:
            detail = resp.json().get("error", {}).get("message", "")
        except ValueError:
            detail = ""

        if resp.status_code in (401, 403):
            raise VisionError("OpenRouter відхилив ключ. Перевірте OPENROUTER_API_KEY.")

        if resp.status_code == 429 or "rate limit" in detail.lower() or "insufficient_quota" in detail.lower():
            last_error = VisionError("Перевищено ліміт OpenRouter. Пробую резервну модель.")
            continue

        if resp.status_code == 404 or "no provider serves" in detail.lower():
            last_error = VisionError(f"Модель {current_model} більше недоступна на OpenRouter. Пробую резервну.")
            continue

        raise VisionError(f"OpenRouter повернув код {resp.status_code}: {detail or resp.text}")

    if last_error is not None:
        raise last_error
    raise VisionError("OpenRouter не відповів коректно. Спробуйте ще раз.")


def _gemini(images, key, model):
    parts = [{"text": PROMPT}] + [
        {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}}
        for data, mime in images]
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    try:
        resp = requests.post(GEMINI_URL.format(model=model),
                             headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                             json=body, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        raise VisionError("Gemini не відповів вчасно. Спробуйте ще раз.")
    except requests.exceptions.RequestException as e:
        raise VisionError("Не вдалося звʼязатися з Gemini: %s" % e)
    if resp.status_code in (401, 403):
        raise VisionError("Gemini відхилив ключ. Перевірте gemini_api_key у Secrets.")
    if resp.status_code == 404:
        raise VisionError("Модель «%s» не знайдена. Вкажіть актуальну назву в Secrets: gemini_model." % model)
    if resp.status_code == 429:
        raise VisionError("Перевищено ліміт запитів Gemini. Зачекайте хвилину і повторіть.")
    if resp.status_code != 200:
        raise VisionError("Gemini повернув код %d." % resp.status_code)
    try:
        cand = resp.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in cand)
    except (ValueError, KeyError, IndexError, TypeError):
        raise VisionError("Gemini не повернув відповідь (можливо, зображення відхилено). Спробуйте інший скріншот.")


def _ollama(images, host, model):
    body = {"model": model, "stream": False, "format": "json",
            "messages": [{"role": "user", "content": PROMPT,
                          "images": [base64.b64encode(d).decode() for d, _ in images]}],
            "options": {"temperature": 0, "num_ctx": 8192}}
    try:
        resp = requests.post("%s/api/chat" % host.rstrip("/"), json=body, timeout=300)
    except requests.exceptions.ConnectionError:
        raise VisionError("Ollama не запущена. Запустіть застосунок Ollama.")
    except requests.exceptions.RequestException as e:
        raise VisionError("Не вдалося звʼязатися з Ollama: %s" % e)
    if resp.status_code == 404:
        raise VisionError("Модель не встановлена. Виконайте: ollama pull %s" % model)
    if resp.status_code != 200:
        raise VisionError("Ollama повернула код %d." % resp.status_code)
    try:
        return resp.json()["message"]["content"]
    except (ValueError, KeyError, TypeError):
        raise VisionError("Ollama повернула некоректну відповідь.")


def configured(gemini_key=None, ollama_model=None, openrouter_key=None):
    return bool(gemini_key or ollama_model or openrouter_key)


def extract(images, gemini_key=None, gemini_model=None, ollama_host=None, ollama_model=None,
            openrouter_key=None, openrouter_model=None):
    """images: [(bytes, mime)]. Gemini, якщо є ключ, інакше OpenRouter/ Ollama, якщо задано vision-модель."""
    if not images:
        raise VisionError("Додайте хоча б один скріншот.")
    if len(images) > MAX_IMAGES:
        raise VisionError("Забагато файлів: максимум %d." % MAX_IMAGES)
    for data, mime in images:
        if mime not in ALLOWED_MIME:
            raise VisionError("Підтримуються лише PNG, JPG та WEBP.")
        if len(data) > MAX_BYTES:
            raise VisionError("Файл завеликий (максимум 8 МБ).")

    # Підтримуємо як секрети сайту, так і змінні середовища.
    if openrouter_key:
        raw = _openrouter(images, openrouter_key,
                          openrouter_model or DEFAULT_OPENROUTER_MODEL,
                          fallbacks=OPENROUTER_FALLBACK_MODELS)
    elif gemini_key:
        raw = _gemini(images, gemini_key, gemini_model or DEFAULT_GEMINI_MODEL)
    elif ollama_model:
        raw = _ollama(images, ollama_host or "http://localhost:11434", ollama_model)
    else:
        raise VisionError("AI для скріншотів не налаштований: додайте OPENROUTER_API_KEY або gemini_api_key у Secrets.")
    return parse(raw)

