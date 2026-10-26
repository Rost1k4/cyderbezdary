"""Допоміжні функції для показу статистики матчу (без запитів і без UI)."""


def format_duration(seconds) -> str:
    if not isinstance(seconds, (int, float)):
        return "н/д"
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def is_radiant(player: dict) -> bool:
    if "isRadiant" in player:
        return bool(player["isRadiant"])
    return player.get("player_slot", 0) < 128


def player_name(p: dict) -> str:
    return p.get("personaname") or p.get("name") or "Анонім"


def val(p: dict, key: str) -> str:
    """Показує значення або 'н/д' — відсутні дані не замінюємо нулями."""
    v = p.get(key)
    return "н/д" if v is None else str(v)
