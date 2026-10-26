"""Запити до OpenDota API та базова перевірка відповідей."""
import requests

BASE_URL = "https://api.opendota.com/api"
TIMEOUT = 15  # секунд


class OpenDotaError(Exception):
    """Загальна помилка при роботі з OpenDota."""


class MatchNotFound(OpenDotaError):
    """Матч не знайдено (неправильний ID або ще не з'явився)."""


class RateLimited(OpenDotaError):
    """Перевищено ліміт запитів."""


def _get(path: str):
    url = f"{BASE_URL}{path}"
    try:
        resp = requests.get(url, timeout=TIMEOUT)
    except requests.exceptions.Timeout:
        raise OpenDotaError("API не відповіло вчасно. Спробуйте ще раз.")
    except requests.exceptions.ConnectionError:
        raise OpenDotaError("Немає з'єднання з інтернетом або API недоступне.")
    except requests.exceptions.RequestException as e:
        raise OpenDotaError(f"Помилка запиту: {e}")

    if resp.status_code == 404:
        raise MatchNotFound(
            "Матч не знайдено. Перевірте, що це Match ID (з історії матчів), "
            "а не ID лобі, і що в гравців увімкнено «Журнал матчів доступний усім». "
            "Новий матч може зʼявитися в OpenDota не одразу.")
    if resp.status_code == 429:
        raise RateLimited("Забагато запитів. Зачекайте хвилину і повторіть.")
    if resp.status_code != 200:
        raise OpenDotaError(f"API повернуло код {resp.status_code}.")

    try:
        return resp.json()
    except ValueError:
        raise OpenDotaError("API повернуло некоректну відповідь (не JSON).")


def get_match(match_id: int) -> dict:
    """Повертає сирий JSON матчу з мінімальною перевіркою структури."""
    data = _get(f"/matches/{match_id}")
    if not isinstance(data, dict) or not data.get("players"):
        raise OpenDotaError(
            "Дані матчу неповні (можливо, він ще обробляється). "
            "Спробуйте повторити запит через кілька хвилин."
        )
    return data


def get_hero_names() -> dict:
    """hero_id -> назва героя. Якщо запит не вдався, повертає порожній словник."""
    try:
        heroes = _get("/heroes")
        return {
            int(h["id"]): h.get("localized_name") or h.get("name") or "Unknown"
            for h in heroes if isinstance(h, dict) and "id" in h
        }
    except (OpenDotaError, KeyError, TypeError, ValueError):
        return {}


def get_hero_internal_names() -> dict:
    """internal_name -> hero_id. Потрібно для розбору kill log в AI-оцінці."""
    try:
        result = {}
        for hero in _get("/heroes"):
            if isinstance(hero, dict) and hero.get("id") is not None and hero.get("name"):
                result[str(hero["name"])] = int(hero["id"])
        return result
    except (OpenDotaError, KeyError, TypeError, ValueError):
        return {}


def get_item_names() -> dict:
    """item_id -> назва предмета (ендпоінт /constants/items). При помилці повертає порожній словник."""
    try:
        items = _get("/constants/items")
        return {int(v["id"]): v.get("dname") or k for k, v in items.items()
                if isinstance(v, dict) and "id" in v}
    except (OpenDotaError, KeyError, TypeError, ValueError, AttributeError):
        return {}


def is_parsed(match: dict) -> bool:
    """Чи пройшов матч розбір реплея (parsed_at не порожнє)."""
    return match.get("parsed_at") is not None

def request_parse(match_id: int) -> None:
    """Просить OpenDota підтягнути та розібрати матч."""
    try:
        resp = requests.post(f"{BASE_URL}/request/{match_id}", timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        raise OpenDotaError(f"Помилка запиту: {e}")
    if resp.status_code == 429:
        raise RateLimited("Забагато запитів. Зачекайте хвилину і повторіть.")
    if resp.status_code != 200:
        raise OpenDotaError(f"API повернуло код {resp.status_code}.")
