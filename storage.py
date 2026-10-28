"""Постійне збереження турніру: Supabase у хмарі, SQLite локально.

Для Streamlit Community Cloud задай SUPABASE_URL і SUPABASE_KEY у Secrets.
Без цих параметрів локально використовується SQLite tournament.db.
"""
import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

import tournament as T

DB_PATH = Path(__file__).with_name("tournament.db")
_supabase = None


def _secret(name, default=""):
    value = os.environ.get(name, "")
    if value:
        return value.strip()
    try:
        import streamlit as st
        value = st.secrets.get(name, default)
        return str(value).strip() if value is not None else default
    except Exception:
        return default


def _cloud():
    """Повертає клієнт Supabase, якщо налаштовано; інакше None."""
    global _supabase
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_KEY")
    if not url or not key:
        return None
    if _supabase is None:
        from supabase import create_client
        _supabase = create_client(url, key)
    return _supabase


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # Таблиці в Supabase створюються один раз SQL-скриптом supabase_schema.sql.
    if _cloud():
        return
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
    db = _cloud()
    if db:
        rows = db.table("settings").select("value").eq("key", key).limit(1).execute().data
        return rows[0]["value"] if rows else default
    with closing(_conn()) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def _set_setting(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", (key, str(value)))


def get_teams():
    """Назви команд у порядку додавання (порядок = номер у сітці)."""
    db = _cloud()
    if db:
        return [r["name"] for r in db.table("teams").select("name").order("id").execute().data]
    with closing(_conn()) as conn:
        return [r["name"] for r in conn.execute("SELECT name FROM teams ORDER BY id")]


def is_started():
    return _get_setting("started") == "1"


def get_bo():
    return int(_get_setting("bo", "1"))


def add_team(name):
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
        db = _cloud()
        if db:
            db.table("teams").insert({"name": name}).execute()
        else:
            with closing(_conn()) as conn, conn:
                conn.execute("INSERT INTO teams(name) VALUES (?)", (name,))
    except Exception:
        return "Команда з такою назвою вже є або база даних недоступна."
    return None


def remove_team(name):
    if is_started():
        return "Турнір уже запущено, склад змінювати не можна."
    db = _cloud()
    if db:
        db.table("teams").delete().eq("name", name).execute()
    else:
        with closing(_conn()) as conn, conn:
            conn.execute("DELETE FROM teams WHERE name=?", (name,))
    return None


def start_tournament(bo):
    n = len(get_teams())
    if n not in T.VALID_SIZES:
        return "Потрібно %s команд (зараз %d)." % (T.sizes_text(), n)
    if bo not in T.VALID_BO:
        return "Некоректний формат матчів."
    db = _cloud()
    if db:
        db.table("settings").upsert([{"key": "bo", "value": str(bo)},
                                      {"key": "started", "value": "1"}], on_conflict="key").execute()
    else:
        with closing(_conn()) as conn, conn:
            _set_setting(conn, "bo", bo)
            _set_setting(conn, "started", 1)
    return None


def get_results():
    db = _cloud()
    if db:
        rows = db.table("results").select("match_key,score_a,score_b,winner,dota_match_id").execute().data
    else:
        with closing(_conn()) as conn:
            rows = [dict(r) for r in conn.execute("SELECT * FROM results").fetchall()]
    return {r["match_key"]: {"score_a": r["score_a"], "score_b": r["score_b"],
                              "winner": r["winner"], "dota_match_id": r.get("dota_match_id")}
            for r in rows}


def save_result(match_key, score_a, score_b, winner, dota_match_id=None):
    record = {"match_key": match_key, "score_a": int(score_a), "score_b": int(score_b),
              "winner": winner, "dota_match_id": dota_match_id or None,
              "confirmed_at": datetime.now().isoformat(timespec="seconds")}
    db = _cloud()
    if db:
        db.table("results").upsert(record, on_conflict="match_key").execute()
    else:
        with closing(_conn()) as conn, conn:
            conn.execute("INSERT OR REPLACE INTO results VALUES (?, ?, ?, ?, ?, ?)",
                         (record["match_key"], record["score_a"], record["score_b"], record["winner"],
                          record["dota_match_id"], record["confirmed_at"]))


def set_dota_match_id(match_key, dota_match_id):
    db = _cloud()
    if db:
        db.table("results").update({"dota_match_id": dota_match_id or None}).eq("match_key", match_key).execute()
    else:
        with closing(_conn()) as conn, conn:
            conn.execute("UPDATE results SET dota_match_id=? WHERE match_key=?", (dota_match_id or None, match_key))


def delete_result(match_key):
    db = _cloud()
    if db:
        db.table("results").delete().eq("match_key", match_key).execute()
        db.table("match_stats").delete().eq("match_key", match_key).execute()
    else:
        with closing(_conn()) as conn, conn:
            conn.execute("DELETE FROM results WHERE match_key=?", (match_key,))
            conn.execute("DELETE FROM match_stats WHERE match_key=?", (match_key,))


def get_match_stats():
    db = _cloud()
    if db:
        rows = db.table("match_stats").select("match_key,game_no,data").execute().data
    else:
        with closing(_conn()) as conn:
            rows = [dict(r) for r in conn.execute("SELECT match_key, game_no, data FROM match_stats").fetchall()]
    out = {}
    for r in rows:
        try:
            value = r["data"]
            if isinstance(value, str):
                value = json.loads(value)
            out.setdefault(r["match_key"], {})[int(r["game_no"])] = value
        except (ValueError, TypeError):
            continue
    return out


def save_match_stats(match_key, game_no, data):
    record = {"match_key": match_key, "game_no": int(game_no), "data": data,
              "updated_at": datetime.now().isoformat(timespec="seconds")}
    db = _cloud()
    if db:
        db.table("match_stats").upsert(record, on_conflict="match_key,game_no").execute()
    else:
        with closing(_conn()) as conn, conn:
            conn.execute("INSERT OR REPLACE INTO match_stats VALUES (?, ?, ?, ?)",
                         (match_key, int(game_no), json.dumps(data, ensure_ascii=False), record["updated_at"]))


def delete_match_stats(match_key, game_no):
    db = _cloud()
    if db:
        db.table("match_stats").delete().eq("match_key", match_key).eq("game_no", int(game_no)).execute()
    else:
        with closing(_conn()) as conn, conn:
            conn.execute("DELETE FROM match_stats WHERE match_key=? AND game_no=?", (match_key, int(game_no)))


def reset_all():
    db = _cloud()
    if db:
        # Видаляємо дочірні дані перед командами та налаштуваннями.
        db.table("match_stats").delete().neq("match_key", "__never_matches__").execute()
        db.table("results").delete().neq("match_key", "__never_matches__").execute()
        db.table("teams").delete().neq("name", "__never_team__").execute()
        db.table("settings").delete().neq("key", "__never_setting__").execute()
    else:
        with closing(_conn()) as conn, conn:
            conn.execute("DELETE FROM results")
            conn.execute("DELETE FROM match_stats")
            conn.execute("DELETE FROM teams")
            conn.execute("DELETE FROM settings")
