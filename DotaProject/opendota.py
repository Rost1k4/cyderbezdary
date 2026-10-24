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
        raise MatchNotFound("Матч не знайдено.")
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
        return {h["id"]: h["localized_name"] for h in heroes}
    except (OpenDotaError, KeyError, TypeError):
        return {}


def is_parsed(match: dict) -> bool:
    """Чи пройшов матч розбір реплея (parsed_at не порожнє)."""
    return match.get("parsed_at") is not None