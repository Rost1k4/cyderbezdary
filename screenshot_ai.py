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

TIMEOUT = 120
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"  # змінюється в Secrets: gemini_model
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
- "radiant_win" comes from the Radiant/Dire victory banner; null if not visible.
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
            "players": [dict(row, team=t, name=None, hero_name=None)
                        for t in ("radiant",) * 5 + ("dire",) * 5]}


# ------------------------------------------------------------ провайдери
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


def configured(gemini_key=None, ollama_model=None):
    return bool((gemini_key or config.api_key()) or ollama_model)


def extract(images, gemini_key=None, gemini_model=None, ollama_host=None, ollama_model=None):
    """images: [(bytes, mime)]. Gemini, якщо є ключ, інакше Ollama, якщо задано vision-модель."""
    if not images:
        raise VisionError("Додайте хоча б один скріншот.")
    if len(images) > MAX_IMAGES:
        raise VisionError("Забагато файлів: максимум %d." % MAX_IMAGES)
    for data, mime in images:
        if mime not in ALLOWED_MIME:
            raise VisionError("Підтримуються лише PNG, JPG та WEBP.")
        if len(data) > MAX_BYTES:
            raise VisionError("Файл завеликий (максимум 8 МБ).")

    gemini_key = gemini_key or config.api_key()
    gemini_model = gemini_model or config.model() or DEFAULT_GEMINI_MODEL

    if gemini_key:
        raw = _gemini(images, gemini_key, gemini_model)
    elif ollama_model:
        raw = _ollama(images, ollama_host or "http://localhost:11434", ollama_model)
    else:
        raise VisionError("AI для скріншотів не налаштований: додайте GEMINI_API_KEY або gemini_api_key у Secrets.")
    return parse(raw)

