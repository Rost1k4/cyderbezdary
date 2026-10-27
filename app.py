"""Dota 2 Tournament Manager (ФТІ КПІ).

Запускається через main.py (кнопка Run), окремо нічого вводити не треба.
Сторінки: 1) Привітання  2) Турнірна таблиця  3) Ігри та аналіз.
Вносити результати та керувати командами може лише організатор за паролем.
"""
import hmac
import os
from pathlib import Path
import base64

import pandas as pd
import streamlit as st

import ai_review
import opendota
import storage
import tournament as T
from bracket_html import bracket_html
from matchview import format_duration, is_radiant, player_name, val

REFRESH_SECONDS = 10

# Налаштуй під себе
EVENT_NAME = "Турнір з Dota 2"
EVENT_DATE = "Дата уточнюєтьс"
EVENT_PLACE = "ФТІ КПІ ім. Ігоря Сікорського"

st.set_page_config(page_title="Dota 2 · ФТІ КПІ", page_icon="🏆", layout="wide")


def load_secrets():
    """Підхоплює ключі з Secrets (Streamlit Cloud) або .streamlit/secrets.toml (локально)."""
    for secret, env in (("gemini_api_key", "GEMINI_API_KEY"), ("gemini_model", "GEMINI_MODEL"),
                        ("database_url", "DATABASE_URL")):
        if os.environ.get(env):
            continue
        try:
            value = st.secrets.get(secret)
        except Exception:
            value = None
        if value:
            os.environ[env] = str(value).strip()


load_secrets()
try:
    storage.init_db()
except Exception as e:  # пароль до БД у повідомлення не потрапляє: показуємо лише тип помилки
    st.error("Не вдалося підключитися до бази даних (%s). "
             "Перевірте значення database_url у Secrets." % type(e).__name__)
    st.stop()

PAGE_CSS = """<style>
[data-testid='stMainMenu'],[data-testid='stDeployButton'],.stAppDeployButton,[data-testid='stToolbarActions'],#MainMenu,footer{visibility:hidden;}
[data-testid='stDecoration']{display:none;}
[data-testid='stExpandSidebarButton'],[data-testid='stSidebarCollapseButton'],[data-testid='collapsedControl']{visibility:visible !important;}
.hero{background:linear-gradient(135deg,#241E5A 0%,#1C1745 100%);
      border:1px solid #3A3180;border-radius:18px;padding:48px 40px;margin-bottom:24px}
.hero .tag{color:#8B6CFF;font-weight:700;letter-spacing:.12em;font-size:.85rem}
.hero h1{margin:8px 0 12px;font-size:2.8rem;color:#ECE9FF}
.hero p{color:#9A93D1;font-size:1.1rem;max-width:720px;margin:0}
.card{background:#1C1745;border:1px solid #3A3180;border-radius:12px;overflow:hidden;height:100%}
.card .ch{background:#241E5A;padding:8px 16px;font-weight:600;color:#ECE9FF}
.card .cb{padding:14px 16px;color:#9A93D1}
[data-testid="stExpander"]{background:#1C1745;border:1px solid #3A3180;border-radius:10px}
[data-testid="stSidebar"]{border-right:1px solid #3A3180}
</style>"""
st.markdown(PAGE_CSS.replace("\n", ""), unsafe_allow_html=True)


# ------------------------------------------------------------------ допоміжне
def admin_password():
    """Пароль організатора: змінна середовища або .streamlit/secrets.toml."""
    pw = os.environ.get("TOURNAMENT_ADMIN_PASSWORD")
    if pw:
        return pw
    try:
        return st.secrets.get("admin_password")
    except Exception:
        return None


def flash(message, kind="success"):
    st.session_state["flash"] = (kind, message)


def load_state():
    teams = storage.get_teams()
    if not storage.is_started():
        return teams, False, 1, {}, {}
    results = storage.get_results()
    slots = T.resolve(len(teams), teams, results)
    return teams, True, storage.get_bo(), results, slots


@st.cache_data(ttl=600, show_spinner=False)
def cached_match(match_id):
    return opendota.get_match(match_id)


@st.cache_data(ttl=3600, show_spinner=False)
def _cached_heroes():
    return opendota.get_hero_names()


def cached_heroes():
    heroes = _cached_heroes()
    if not heroes:
        _cached_heroes.clear()  # не кешуємо невдалий запит
    return heroes


@st.cache_data(ttl=3600, show_spinner=False)
def cached_ai_short(match_id):
    """Одна AI-оцінка на матч для всіх глядачів (економить запити). Помилки не кешуються."""
    return ai_review.short_review(opendota.get_match(match_id), cached_heroes())


def players_df(players, heroes):
    rows = []
    for p in players:
        rows.append({
            "Гравець": player_name(p),
            "Герой": heroes.get(p.get("hero_id"), "Hero #%s" % p.get("hero_id")),
            "K/D/A": "%s/%s/%s" % (val(p, "kills"), val(p, "deaths"), val(p, "assists")),
            "LH/DN": "%s/%s" % (val(p, "last_hits"), val(p, "denies")),
            "GPM": val(p, "gold_per_min"),
            "XPM": val(p, "xp_per_min"),
            "Шкода героям": val(p, "hero_damage"),
            "Шкода вежам": val(p, "tower_damage"),
        })
    return pd.DataFrame(rows)


def render_match_analysis(mid, scope):
    """Статистика матчу + AI. scope робить ключі кнопок унікальними на сторінці."""
    try:
        with st.spinner("Завантаження..."):
            match = cached_match(mid)
            heroes = cached_heroes()
    except opendota.OpenDotaError as e:
        st.error(str(e))
        request_parse = getattr(opendota, "request_parse", None)
        if request_parse and st.button("Запросити розбір в OpenDota",
                                       key="rq_%s_%d" % (scope, mid)):
            try:
                request_parse(mid)
                st.info("Запит надіслано. Спробуйте ще раз через 1-5 хвилин.")
            except opendota.OpenDotaError as e2:
                st.error(str(e2))
        return
    winner = {True: "Radiant", False: "Dire"}.get(match.get("radiant_win"), "н/д")
    st.write("Переможець: **%s**, тривалість: **%s**, рахунок: %s:%s"
             % (winner, format_duration(match.get("duration")),
                val(match, "radiant_score"), val(match, "dire_score")))
    if not opendota.is_parsed(match):
        st.warning("Матч ще не розібраний повністю: частина даних може бути відсутня.")

    ai_key = "ai_text_%d" % mid
    if st.button("🤖 Коротко від AI", key="ai_%s_%d" % (scope, mid)):
        try:
            with st.spinner("AI аналізує матч..."):
                st.session_state[ai_key] = cached_ai_short(mid)
        except (ai_review.AIError, opendota.OpenDotaError) as e:
            st.session_state.pop(ai_key, None)
            st.error(str(e))
    if ai_key in st.session_state:
        st.info(st.session_state[ai_key])

    players = match["players"]
    st.markdown("**Radiant**")
    st.dataframe(players_df([p for p in players if is_radiant(p)], heroes), hide_index=True)
    st.markdown("**Dire**")
    st.dataframe(players_df([p for p in players if not is_radiant(p)], heroes), hide_index=True)


# --------------------------------------------- публічні блоки (самооновлення)
@st.fragment(run_every=REFRESH_SECONDS)
def bracket_view():
    teams, started, bo, results, slots = load_state()
    if not started:
        st.info("Турнір ще не розпочато. Сітка з'явиться, щойно організатор його запустить.")
        if teams:
            st.write("Зареєстровані команди: " + ", ".join(teams))
        return
    champ = T.champion(slots)
    if champ:
        st.success("🏆 Чемпіон турніру: **%s**" % champ)
    st.caption("Формат матчів: BO%d. Бурштинова рамка: матч готовий до гри. М'ятна: завершено. "
               "Сторінка оновлюється кожні %d с." % (bo, REFRESH_SECONDS))
    st.markdown(bracket_html(len(teams), slots), unsafe_allow_html=True)


@st.fragment(run_every=REFRESH_SECONDS)
def table_view():
    teams, started, bo, results, slots = load_state()
    if not started:
        st.info("Таблиця з'явиться після початку турніру.")
        return
    rec = T.standings(teams, slots)
    table = pd.DataFrame([
        {"Команда": t, "Статус": v["status"], "Перемоги": v["W"], "Поразки": v["L"],
         "Мапи": "%d:%d" % (v["MW"], v["ML"])}
        for t, v in rec.items()
    ]).sort_values(["Перемоги", "Поразки"], ascending=[False, True])
    st.subheader("Лічильник перемог")
    st.dataframe(table, hide_index=True)
    st.subheader("Журнал матчів")
    log = [{"Матч": k, "Команда A": s["a"],
            "Рахунок": "%d:%d" % (s["result"]["score_a"], s["result"]["score_b"]),
            "Команда B": s["b"], "Переможець": s["result"]["winner"],
            "Dota Match ID": s["result"]["dota_match_id"] or ""}
           for k, s in slots.items() if s["result"]]
    if log:
        st.dataframe(pd.DataFrame(log), hide_index=True)
    else:
        st.info("Результатів ще немає.")


# ------------------------------------------------------ блок організатора
def results_admin():
    teams, started, bo, results, slots = load_state()
    if not started:
        st.info("Спочатку запустіть турнір у бічній панелі.")
        return
    size = len(teams)
    champ = T.champion(slots)
    st.subheader("Внести результат")
    ready = [s for s in slots.values() if s["status"] == "ready"]
    if not ready:
        st.info("Турнір завершено." if champ else "Немає матчів, готових до гри.")
    else:
        options = {"%s: %s vs %s" % (s["key"], s["a"], s["b"]): s["key"] for s in ready}
        chosen = st.selectbox("Матч", list(options))
        key = options[chosen]
        s = slots[key]
        need = bo // 2 + 1
        c1, c2 = st.columns(2)
        score_a = c1.number_input("Рахунок: %s" % s["a"], 0, need, 0, key="sa_" + key)
        score_b = c2.number_input("Рахунок: %s" % s["b"], 0, need, 0, key="sb_" + key)
        dota_id = st.text_input("Dota Match ID, не ID лобі (необов'язково, для аналізу)",
                                key="did_" + key)
        confirmed = st.checkbox("Підтверджую, що результат остаточний", key="cf_" + key)
        if st.button("Зберегти результат", type="primary", disabled=not confirmed):
            err = T.validate_result(bo, int(score_a), int(score_b))
            if not err and dota_id.strip() and not dota_id.strip().isdigit():
                err = "Dota Match ID має складатися лише з цифр."
            if err:
                st.error(err)
            else:
                winner = T.winner_from_score(s["a"], s["b"], int(score_a), int(score_b))
                storage.save_result(key, int(score_a), int(score_b), winner,
                                    dota_id.strip() or None)
                flash("Збережено %s: %s %d:%d %s. Переможець: %s."
                      % (key, s["a"], score_a, score_b, s["b"], winner))
                st.rerun()

    editable = [k for k, s in slots.items()
                if s["status"] == "done" and T.can_edit(size, results, k)]
    with st.expander("Скасувати результат (виправлення помилки)"):
        if not editable:
            st.write("Немає результатів, які можна скасувати.")
        else:
            st.caption("Скасувати можна лише матч, від якого ще не залежить жоден збережений "
                       "результат. Для старішого матчу спочатку скасуйте пізніші.")
            undo_key = st.selectbox("Матч", editable)
            undo_ok = st.checkbox("Підтверджую скасування", key="undo_ok")
            if st.button("Скасувати результат", disabled=not undo_ok):
                storage.delete_result(undo_key)
                flash("Результат %s скасовано." % undo_key, "warning")
                st.rerun()


# =============================================================== СТОРІНКИ
def welcome_page():
    st.markdown(
        '<div class="hero"><div class="tag">ФТІ КПІ ІМ. ІГОРЯ СІКОРСЬКОГО</div>'
        '<h1>%s</h1><p>Вітаємо на турнірі з Dota 2! Слідкуйте за сіткою, результатами '
        'та детальним аналізом кожної гри в реальному часі.</p></div>' % EVENT_NAME,
        unsafe_allow_html=True)

    teams, started, bo, results, slots = load_state()
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="card"><div class="ch">📅 Коли</div><div class="cb">%s</div></div>'
                % EVENT_DATE, unsafe_allow_html=True)
    c2.markdown('<div class="card"><div class="ch">📍 Де</div><div class="cb">%s</div></div>'
                % EVENT_PLACE, unsafe_allow_html=True)
    fmt = ("%d команд, BO%d" % (len(teams), bo)) if started else "Реєстрація команд триває"
    c3.markdown('<div class="card"><div class="ch">⚔️ Формат</div><div class="cb">'
                'Double elimination: верхня та нижня сітки, Grand Final.<br>%s</div></div>' % fmt,
                unsafe_allow_html=True)

    st.write("")
    st.info("Учасникам: перед грою ввімкніть у Dota 2 «Журнал матчів доступний усім» "
            "(Налаштування → Спільнота → Параметри), інакше статистика матчу не з'явиться.")
    b1, b2, _ = st.columns([1, 1, 3])
    b1.page_link(PAGE_TABLE, label="Турнірна таблиця", icon="🏆")
    b2.page_link(PAGE_GAMES, label="Ігри та аналіз", icon="📊")


def table_page():
    st.title("🏆 Турнірна таблиця")
    tab_bracket, tab_table = st.tabs(["Сітка", "Таблиця команд"])
    with tab_bracket:
        bracket_view()
    with tab_table:
        table_view()
    if st.session_state.get("is_admin", False):
        st.divider()
        results_admin()


def games_page():
    st.title("📊 Ігри та аналіз")
    teams, started, bo, results, slots = load_state()
    st.subheader("Зіграні матчі")
    if not started:
        st.info("Список ігор з'явиться після початку турніру.")
    else:
        played = [s for s in slots.values() if s["result"]]
        if not played:
            st.info("Результатів ще немає.")
        for s in played:
            r = s["result"]
            title = "%s · %s  %d:%d  %s  →  %s" % (
                s["key"], s["a"], r["score_a"], r["score_b"], s["b"], r["winner"])
            with st.expander(title):
                mid = r["dota_match_id"]
                if not mid:
                    st.caption("Dota Match ID для цього матчу не вказано.")
                    continue
                st.caption("Dota Match ID: %s" % mid)
                if st.toggle("Показати аналіз", key="tg_" + s["key"]):
                    render_match_analysis(int(mid), "log_" + s["key"])

    st.divider()
    st.subheader("Статистика за Match ID")
    with st.form("match_form"):
        match_id = st.text_input("Match ID завершеного матчу (не ID лобі)")
        submitted = st.form_submit_button("Показати статистику", type="primary")
    if submitted:
        if not match_id.strip().isdigit():
            st.session_state.pop("viewed_match", None)
            st.error("Match ID має складатися лише з цифр.")
        else:
            st.session_state["viewed_match"] = int(match_id)
    mid = st.session_state.get("viewed_match")
    if mid is not None:
        render_match_analysis(mid, "free")


# ---------------------------------------------------------------- навігація
PAGE_WELCOME = st.Page(welcome_page, title="Привітання", icon="🏠", url_path="welcome", default=True)
PAGE_TABLE = st.Page(table_page, title="Турнірна таблиця", icon="🏆", url_path="bracket")
PAGE_GAMES = st.Page(games_page, title="Ігри та аналіз", icon="📊", url_path="games")
pg = st.navigation([PAGE_WELCOME, PAGE_TABLE, PAGE_GAMES])

# ---------------------------------------------------------------- бічна панель
is_admin = st.session_state.get("is_admin", False)

with st.sidebar:
    if not is_admin:
        st.header("Організатор")
        password = admin_password()
        if not password:
            st.info("Пароль організатора не задано, тому доступний лише перегляд. "
                    "Задайте admin_password у Secrets (Streamlit Cloud) або в .streamlit/secrets.toml.")
        else:
            with st.form("login"):
                entered = st.text_input("Пароль", type="password")
                if st.form_submit_button("Увійти"):
                    if hmac.compare_digest(entered.encode("utf-8"), password.encode("utf-8")):
                        st.session_state["is_admin"] = True
                        st.rerun()
                    else:
                        st.error("Неправильний пароль.")
    else:
        st.header("Керування турніром")
        if storage.is_persistent():
            st.caption("💾 Сховище: PostgreSQL. Дані зберігаються постійно.")
        else:
            st.info("💾 Дані лежать у локальному файлі tournament.db. На Streamlit Cloud він "
                    "тимчасовий і може зникнути при перезапуску: додайте database_url у Secrets.")
        if st.button("Вийти з режиму організатора"):
            st.session_state["is_admin"] = False
            st.rerun()
        teams = storage.get_teams()
        if not storage.is_started():
            st.caption("Додайте 4 або 8 команд. Порядок додавання = номер у сітці.")
            with st.form("add_team", clear_on_submit=True):
                new_name = st.text_input("Назва команди")
                if st.form_submit_button("Додати команду"):
                    err = storage.add_team(new_name)
                    flash(err or "Команду додано.", "error" if err else "success")
                    st.rerun()
            for i, name in enumerate(teams, 1):
                c1, c2 = st.columns([4, 1])
                c1.write("%d. %s" % (i, name))
                if c2.button("✕", key="rm_" + name, help="Видалити команду"):
                    storage.remove_team(name)
                    st.rerun()
            bo_choice = st.selectbox("Формат матчів", T.VALID_BO, format_func=lambda x: "BO%d" % x)
            if st.button("Запустити турнір", type="primary",
                         disabled=len(teams) not in T.VALID_SIZES):
                err = storage.start_tournament(bo_choice)
                flash(err or "Турнір запущено.", "error" if err else "success")
                st.rerun()
            if len(teams) not in T.VALID_SIZES:
                st.info("Команд: %d. Потрібно 4 або 8." % len(teams))
        else:
            st.write("Команд: **%d**, формат: **BO%d**" % (len(teams), storage.get_bo()))
            with st.expander("Скинути турнір"):
                st.warning("Буде видалено всі команди та результати.")
                sure = st.checkbox("Так, видалити все", key="reset_ok")
                if st.button("Скинути", disabled=not sure):
                    storage.reset_all()
                    flash("Турнір скинуто.")
                    st.rerun()
JAR_URL = "https://send.monobank.ua/jar/usfzttkbh"
QR_PATH = Path(__file__).with_name("qr.png")
if QR_PATH.exists():
    qr_b64 = base64.b64encode(QR_PATH.read_bytes()).decode()
    with st.sidebar:
        st.divider()
        st.markdown(
            '<div style="text-align:center">'
            '<div style="font-weight:700;margin-bottom:8px">Підтримайте розробників 🫶❤️</div>'
            '<a href="%s" target="_blank" rel="noopener noreferrer">'
            '<img src="data:image/png;base64,%s" '
            'style="width:100%%;max-width:220px;cursor:pointer"></a>'
            '<div style="color:#9A93D1;font-size:.8rem;margin-top:6px">'
            'Натисніть на код, щоб відкрити банку</div></div>' % (JAR_URL, qr_b64),
            unsafe_allow_html=True)
        st.link_button("💜 Підтримати", JAR_URL, use_container_width=True)
if "flash" in st.session_state:
    kind, message = st.session_state.pop("flash")
    getattr(st, kind)(message)

pg.run()
