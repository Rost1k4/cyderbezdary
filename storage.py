"""Збереження турніру: SQLite (локально) або PostgreSQL (хмара).

Зберігаємо лише вхідні дані: команди, формат BO і підтверджені результати.
Сітка, лічильники перемог і статуси ЗАВЖДИ рахуються з них заново,
тому розбіжностей між даними не буває.

Яке сховище використовується:
  * задано змінну DATABASE_URL (на Streamlit Cloud її підставляє app.py із Secrets,
    ключ database_url) -> PostgreSQL, дані зберігаються постійно;
  * інакше -> файл tournament.db поруч із кодом (зручно локально; на Streamlit Cloud
    такий файл тимчасовий і може зникнути при перезапуску сервера).
"""
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import tournament as T

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
except ImportError:  # для локального SQLite драйвер не потрібен
    psycopg2 = None

DB_PATH = Path(__file__).with_name("tournament.db")
_INTEGRITY = (sqlite3.IntegrityError,) + ((psycopg2.IntegrityError,) if psycopg2 else ())

POOL_MAX = 8
IDLE_PING_SECONDS = 20  # якщо зʼєднання простоювало довше, перевіряємо його перед використанням


def database_url() -> str:
    return (os.environ.get("DATABASE_URL") or "").strip()


def is_persistent() -> bool:
    """True, якщо дані лежать у зовнішній БД і переживуть перезапуск сервера."""
    return bool(database_url())


# ------------------------------------------------------------------ SQLite
class _SQLite:
    def __init__(self, conn):
        self.conn = conn

    def q(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()] if cur.description else []


@contextmanager
def _sqlite_session():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield _SQLite(conn)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


# -------------------------------------------------------------- PostgreSQL
class _PG:
    def __init__(self, cur):
        self.cur = cur

    def q(self, sql, params=()):
        self.cur.execute(sql.replace("?", "%s"), params)
        return [dict(r) for r in self.cur.fetchall()] if self.cur.description else []


_pool = None
_pool_url = None
_pool_lock = threading.Lock()
_pool_slots = threading.BoundedSemaphore(POOL_MAX)
_last_used = {}  # id(зʼєднання) -> час останнього використання


def _get_pool(url):
    global _pool, _pool_url
    with _pool_lock:
        if _pool is None or _pool_url != url:
            if psycopg2 is None:
                raise RuntimeError("Для PostgreSQL потрібен пакет psycopg2-binary "
                                   "(pip install psycopg2-binary).")
            kwargs = {"connect_timeout": 10, "keepalives": 1, "keepalives_idle": 30,
                      "keepalives_interval": 10, "keepalives_count": 3}
            if "sslmode" not in url:
                kwargs["sslmode"] = "require"
            _pool = psycopg2.pool.ThreadedConnectionPool(1, POOL_MAX, url, **kwargs)
            _pool_url = url
        return _pool


def _checkout(pool):
    """Бере зʼєднання з пулу; «мертве» (хмарна БД закриває простій) відкидає."""
    for _ in range(3):
        conn = pool.getconn()
        idle = time.monotonic() - _last_used.get(id(conn), 0)
        if idle > IDLE_PING_SECONDS:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                conn.rollback()
            except psycopg2.Error:
                _last_used.pop(id(conn), None)
                pool.putconn(conn, close=True)
                continue
        return conn
    raise RuntimeError("Не вдалося підключитися до бази даних.")


@contextmanager
def _pg_session(url):
    pool = _get_pool(url)
    if not _pool_slots.acquire(timeout=20):
        raise RuntimeError("База даних зайнята. Спробуйте ще раз.")
    conn = None
    try:
        conn = _checkout(pool)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield _PG(cur)
            conn.commit()
        except BaseException:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
    finally:
        if conn is not None:
            closed = bool(conn.closed)
            if closed:
                _last_used.pop(id(conn), None)
            else:
                _last_used[id(conn)] = time.monotonic()
            pool.putconn(conn, close=closed)
        _pool_slots.release()


@contextmanager
def _db():
    url = database_url()
    session = _pg_session(url) if url else _sqlite_session()
    with session as db:
        yield db


# ------------------------------------------------------------------- схема
_SQLITE_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS teams (
           id INTEGER PRIMARY KEY AUTOINCREMENT,
           name TEXT NOT NULL UNIQUE COLLATE NOCASE)""",
    """CREATE TABLE IF NOT EXISTS settings (
           key TEXT PRIMARY KEY,
           value TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS results (
           match_key TEXT PRIMARY KEY,
           score_a INTEGER NOT NULL,
           score_b INTEGER NOT NULL,
           winner TEXT NOT NULL,
           dota_match_id TEXT,
           confirmed_at TEXT NOT NULL)""",
]
_PG_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS teams (
           id SERIAL PRIMARY KEY,
           name TEXT NOT NULL)""",
    "CREATE UNIQUE INDEX IF NOT EXISTS teams_name_lower_idx ON teams (LOWER(name))",
    """CREATE TABLE IF NOT EXISTS settings (
           key TEXT PRIMARY KEY,
           value TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS results (
           match_key TEXT PRIMARY KEY,
           score_a INTEGER NOT NULL,
           score_b INTEGER NOT NULL,
           winner TEXT NOT NULL,
           dota_match_id TEXT,
           confirmed_at TEXT NOT NULL)""",
]
_init_lock = threading.Lock()
_pg_ready = False


def init_db():
    """Створює таблиці. Для PostgreSQL робить це один раз за життя процесу."""
    global _pg_ready
    pg = bool(database_url())
    with _init_lock:
        if pg and _pg_ready:
            return
        with _db() as db:
            for stmt in (_PG_SCHEMA if pg else _SQLITE_SCHEMA):
                db.q(stmt)
        if pg:
            _pg_ready = True


# ---------------------------------------------------------------- операції
def _get_setting(key, default=None):
    with _db() as db:
        rows = db.q("SELECT value FROM settings WHERE key=?", (key,))
    return rows[0]["value"] if rows else default


def _set_setting(db, key, value):
    db.q("INSERT INTO settings(key, value) VALUES (?, ?) "
         "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def get_teams():
    """Назви команд у порядку додавання (порядок = номер у сітці)."""
    with _db() as db:
        return [r["name"] for r in db.q("SELECT name FROM teams ORDER BY id")]


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
        with _db() as db:
            db.q("INSERT INTO teams(name) VALUES (?)", (name,))
    except _INTEGRITY:
        return "Команда з такою назвою вже є."
    return None


def remove_team(name):
    if is_started():
        return "Турнір уже запущено, склад змінювати не можна."
    with _db() as db:
        db.q("DELETE FROM teams WHERE name=?", (name,))
    return None


def start_tournament(bo):
    n = len(get_teams())
    if n not in T.VALID_SIZES:
        return "Потрібно рівно 4 або 8 команд (зараз %d)." % n
    if bo not in T.VALID_BO:
        return "Некоректний формат матчів."
    with _db() as db:
        _set_setting(db, "bo", bo)
        _set_setting(db, "started", 1)
    return None


def get_results():
    with _db() as db:
        rows = db.q("SELECT match_key, score_a, score_b, winner, dota_match_id FROM results")
    return {r["match_key"]: {"score_a": r["score_a"], "score_b": r["score_b"],
                             "winner": r["winner"], "dota_match_id": r["dota_match_id"]}
            for r in rows}


def save_result(match_key, score_a, score_b, winner, dota_match_id=None):
    with _db() as db:
        db.q("INSERT INTO results(match_key, score_a, score_b, winner, dota_match_id, confirmed_at) "
             "VALUES (?, ?, ?, ?, ?, ?) "
             "ON CONFLICT(match_key) DO UPDATE SET score_a=excluded.score_a, "
             "score_b=excluded.score_b, winner=excluded.winner, "
             "dota_match_id=excluded.dota_match_id, confirmed_at=excluded.confirmed_at",
             (match_key, score_a, score_b, winner, dota_match_id or None,
              datetime.now().isoformat(timespec="seconds")))


def delete_result(match_key):
    with _db() as db:
        db.q("DELETE FROM results WHERE match_key=?", (match_key,))


def reset_all():
    with _db() as db:
        db.q("DELETE FROM results")
        db.q("DELETE FROM teams")
        db.q("DELETE FROM settings")
