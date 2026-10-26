"""Консольна версія: введення Match ID, показ статистики та повна AI-оцінка."""
import json
import sys
from pathlib import Path


import opendota


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


def print_team(title: str, players: list, heroes: dict):
    print(f"\n=== {title} ===")
    print(f"{'Гравець':<20}{'Герой':<20}{'K/D/A':<10}{'LH/DN':<10}{'GPM':<6}{'XPM':<6}{'Шкода':<8}{'Вежі':<6}")
    for p in players:
        hero = heroes.get(p.get("hero_id"), f"Hero #{p.get('hero_id')}")
        kda = f"{val(p,'kills')}/{val(p,'deaths')}/{val(p,'assists')}"
        lhdn = f"{val(p,'last_hits')}/{val(p,'denies')}"
        print(f"{player_name(p)[:19]:<20}{hero[:19]:<20}{kda:<10}{lhdn:<10}"
              f"{val(p,'gold_per_min'):<6}{val(p,'xp_per_min'):<6}"
              f"{val(p,'hero_damage'):<8}{val(p,'tower_damage'):<6}")


def show_match(match: dict, heroes: dict):
    players = match["players"]
    radiant = [p for p in players if is_radiant(p)]
    dire = [p for p in players if not is_radiant(p)]

    winner = "Radiant" if match.get("radiant_win") else "Dire"
    if match.get("radiant_win") is None:
        winner = "н/д"

    print(f"\nMatch ID: {match.get('match_id')}")
    print(f"Переможець: {winner}")
    print(f"Тривалість: {format_duration(match.get('duration'))}")
    print(f"Рахунок: Radiant {val(match,'radiant_score')} : {val(match,'dire_score')} Dire")
    if not opendota.is_parsed(match):
        print("⚠ Матч ще не розібраний повністю: частина даних може бути відсутня.")
    if len(players) != 10:
        print(f"⚠ Очікувалось 10 гравців, отримано {len(players)}.")

    print_team("RADIANT", radiant, heroes)
    print_team("DIRE", dire, heroes)


def main():
    import ai_review
    save_raw = "--raw" in sys.argv

    raw_id = input("Введіть Match ID: ").strip()
    if not raw_id.isdigit():
        print("Match ID має складатися лише з цифр.")
        return

    print("Завантаження даних...")
    try:
        match = opendota.get_match(int(raw_id))
    except opendota.OpenDotaError as e:
        print(f"Помилка: {e}")
        return

    if save_raw:
        Path("reports").mkdir(exist_ok=True)
        path = Path("reports") / f"raw_{raw_id}.json"
        path.write_text(json.dumps(match, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Сирі дані збережено: {path}")

    heroes = opendota.get_hero_names()
    show_match(match, heroes)
    ai_review.review_match(match, heroes)


if __name__ == "__main__":
    main()