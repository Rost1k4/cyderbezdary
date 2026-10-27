"""Збереження турніру в SQLite (файл tournament.db поруч із кодом).

Зберігаємо лише вхідні дані: команди, формат BO, підтверджені результати та
статистику матчів, розпізнану зі скріншотів. Сітка, лічильники перемог і статуси
ЗАВЖДИ рахуються з них заново, тому розбіжностей між даними не буває.
"""
import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import tournament as T

DB_PATH = Path(__file__).with_name("tournament.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(_conn()) as conn, conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS results (
                match_key TEXT PRIMARY KEY,
                score_a INTEGER NOT NULL,
                score_b INTEGER NOT NULL,
                winner TEXT NOT NULL,
                dota_match_id TEXT,
                confirmed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS match_stats (
                match_key TEXT NOT NULL,
                game_no INTEGER NOT NULL,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (match_key, game_no)
            );
        """)


def _get_setting(key, default=None):
    with closing(_conn()) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _set_setting(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", (key, str(value)))


def get_teams():
    """Назви команд у порядку додавання (порядок = номер у сітці)."""
    with closing(_conn()) as conn:
        return [r["name"] for r in conn.execute("SELECT name FROM teams ORDER BY id")]


def is_started():
    return _get_setting("started") == "1"


def get_bo():
    return int(_get_setting("bo", "1"))


def add_team(name):
    """None, якщо додано, інакше текст помилки."""
    name = " ".join((name or "").split())
    if not name:
        return "Введіть назву команди."
    if len(name) > 40:
        return "Назва задовга (максимум 40 символів)."
    if is_started():
        return "Турнір уже запущено, склад змінювати не можна."
    if len(get_teams()) >= max(T.VALID_SIZES):
        return "Максимум %d команд." % max(T.VALID_SIZES)
    try:
        with closing(_conn()) as conn, conn:
            conn.execute("INSERT INTO teams(name) VALUES (?)", (name,))
    except sqlite3.IntegrityError:
        return "Команда з такою назвою вже є."
    return None


def remove_team(name):
    if is_started():
        return "Турнір уже запущено, склад змінювати не можна."
    with closing(_conn()) as conn, conn:
        conn.execute("DELETE FROM teams WHERE name=?", (name,))
    return None


def start_tournament(bo):
    n = len(get_teams())
    if n not in T.VALID_SIZES:
        return "Потрібно %s команд (зараз %d)." % (T.sizes_text(), n)
    if bo not in T.VALID_BO:
        return "Некоректний формат матчів."
    with closing(_conn()) as conn, conn:
        _set_setting(conn, "bo", bo)
        _set_setting(conn, "started", 1)
    return None


def get_results():
    with closing(_conn()) as conn:
        rows = conn.execute("SELECT * FROM results").fetchall()
    return {r["match_key"]: {"score_a": r["score_a"], "score_b": r["score_b"],
                             "winner": r["winner"], "dota_match_id": r["dota_match_id"]}
            for r in rows}


def save_result(match_key, score_a, score_b, winner, dota_match_id=None):
    with closing(_conn()) as conn, conn:
        conn.execute(
            "INSERT OR REPLACE INTO results VALUES (?, ?, ?, ?, ?, ?)",
            (match_key, score_a, score_b, winner, dota_match_id or None,
             datetime.now().isoformat(timespec="seconds")))


def set_dota_match_id(match_key, dota_match_id):
    """Додає, змінює або (якщо порожньо) прибирає Dota Match ID вже збереженого результату."""
    with closing(_conn()) as conn, conn:
        conn.execute("UPDATE results SET dota_match_id=? WHERE match_key=?",
                     (dota_match_id or None, match_key))


def delete_result(match_key):
    with closing(_conn()) as conn, conn:
        conn.execute("DELETE FROM results WHERE match_key=?", (match_key,))
        conn.execute("DELETE FROM match_stats WHERE match_key=?", (match_key,))


# ---- статистика зі скріншотів: {match_key: {номер_гри: дані}} ----
def get_match_stats():
    with closing(_conn()) as conn:
        rows = conn.execute("SELECT match_key, game_no, data FROM match_stats").fetchall()
    out = {}
    for r in rows:
        try:
            out.setdefault(r["match_key"], {})[r["game_no"]] = json.loads(r["data"])
        except ValueError:
            continue
    return out


def save_match_stats(match_key, game_no, data):
    with closing(_conn()) as conn, conn:
        conn.execute(
            "INSERT OR REPLACE INTO match_stats VALUES (?, ?, ?, ?)",
            (match_key, int(game_no), json.dumps(data, ensure_ascii=False),
             datetime.now().isoformat(timespec="seconds")))


def delete_match_stats(match_key, game_no):
    with closing(_conn()) as conn, conn:
        conn.execute("DELETE FROM match_stats WHERE match_key=? AND game_no=?",
                     (match_key, int(game_no)))


def reset_all():
    with closing(_conn()) as conn, conn:
        conn.execute("DELETE FROM results")
        conn.execute("DELETE FROM match_stats")
        conn.execute("DELETE FROM teams")
        conn.execute("DELETE FROM settings")
