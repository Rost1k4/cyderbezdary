"""Dota 2 Tournament Manager (ФТІ КПІ).

Запускається через main.py (кнопка Run), окремо нічого вводити не треба.
Сторінки: 1) Привітання  2) Турнірна таблиця  3) Ігри та аналіз.
Є ще прихована сторінка входу організатора: /admin (її немає в меню).
Вносити результати та керувати командами може лише організатор за паролем.
"""
import hmac
import html
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import streamlit as st

import ai_review
import home_html
import opendota
import storage
import tournament as T
from bracket_html import bracket_html, match_stats_html, players_table_html
from matchview import format_duration, is_radiant, val

REFRESH_SECONDS = 10

# ---- Налаштуй під себе ----
EVENT_NAME = "Турнір з Dota 2"
EVENT_DATE = "Дата уточнюється"
EVENT_PLACE = "ФТІ КПІ ім. Ігоря Сікорського"
STREAM_URL = ""  # встав посилання на стрім, напр. "https://www.twitch.tv/..."

st.set_page_config(page_title="Dota 2 · ФТІ КПІ", page_icon="🏆", layout="wide")
storage.init_db()

PAGE_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Onest:wght@400;500;700&family=Unbounded:wght@500;700;800&display=swap');
[data-testid='stMainMenu'],[data-testid='stDeployButton'],.stAppDeployButton,[data-testid='stToolbarActions'],#MainMenu,footer{visibility:hidden;}
[data-testid='stDecoration']{display:none;}
[data-testid='stExpandSidebarButton'],[data-testid='stSidebarCollapseButton'],[data-testid='collapsedControl']{visibility:visible !important;}
.stApp{background-color:#120F2E;background-image:radial-gradient(640px 420px at 92% -6%,rgba(139,108,255,.30),transparent 70%),radial-gradient(520px 380px at -4% 102%,rgba(79,140,255,.18),transparent 70%),radial-gradient(380px 280px at 60% 55%,rgba(196,92,255,.08),transparent 70%),linear-gradient(rgba(58,49,128,.16) 1px,transparent 1px),linear-gradient(90deg,rgba(58,49,128,.16) 1px,transparent 1px);background-size:auto,auto,auto,56px 56px,56px 56px;background-attachment:fixed}
.stApp,.stApp p,.stApp label,.stApp button,.stApp input,.stApp textarea{font-family:"Onest",system-ui,-apple-system,"Segoe UI",sans-serif}
h1,h2,h3{font-family:"Unbounded","Arial Black",system-ui,sans-serif !important;letter-spacing:-.01em}
.block-container{padding-top:2.2rem;max-width:1280px}
.ph{margin-bottom:10px;animation:fup .6s ease both}
.ph .tag{color:#8B6CFF;font-weight:700;letter-spacing:.16em;font-size:.74rem;text-transform:uppercase}
.ph h1{font-size:clamp(1.7rem,3.6vw,2.4rem);margin:6px 0 4px;padding:0}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#1C1745,#161236);border-right:1px solid #3A3180}
.brand{display:flex;align-items:center;gap:12px;padding:4px 2px 16px;margin-bottom:10px;border-bottom:1px solid #3A3180}
.brand .lg{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;font-size:1.3rem;background:linear-gradient(135deg,#4F8CFF,#C45CFF);box-shadow:0 6px 18px rgba(139,108,255,.4)}
.brand b{display:block;font-family:"Unbounded","Arial Black",sans-serif;font-size:.9rem}
.brand span{color:#9A93D1;font-size:.72rem}
[data-testid="stPageLink-NavLink"]{border-radius:10px;border:1px solid transparent;transition:background .2s,border-color .2s}
[data-testid="stPageLink-NavLink"]:hover{background:rgba(139,108,255,.14);border-color:#3A3180}
[data-testid="stPageLink-NavLink"][aria-current="page"]{background:linear-gradient(90deg,rgba(139,108,255,.32),rgba(139,108,255,.06));border-color:#3A3180}
.stream-btn{display:block;text-align:center;background:linear-gradient(135deg,#8B6CFF,#C45CFF);color:#fff !important;padding:11px 12px;border-radius:12px;font-weight:700;text-decoration:none !important;margin:12px 0;box-shadow:0 8px 22px rgba(139,108,255,.35);transition:transform .2s,box-shadow .2s}
.stream-btn:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(139,108,255,.5)}
.stream-btn.off{background:#241E5A;color:#9A93D1 !important;border:1px solid #3A3180;box-shadow:none}
[data-testid="stBaseButton-secondary"],[data-testid="stBaseButton-secondaryFormSubmit"]{border-radius:10px;border:1px solid #3A3180;background:#1C1745;transition:transform .15s,border-color .15s}
[data-testid="stBaseButton-secondary"]:hover,[data-testid="stBaseButton-secondaryFormSubmit"]:hover{border-color:#8B6CFF;transform:translateY(-1px)}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{border:0;border-radius:10px;background:linear-gradient(135deg,#8B6CFF,#6F4FE8);box-shadow:0 6px 18px rgba(139,108,255,.35);transition:transform .15s,box-shadow .15s}
[data-testid="stBaseButton-primary"]:hover,[data-testid="stBaseButton-primaryFormSubmit"]:hover{transform:translateY(-1px);box-shadow:0 10px 26px rgba(139,108,255,.5)}
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="textarea"]{border-radius:10px !important}
button[role="tab"]{font-weight:600}
button[role="tab"][aria-selected="true"]{color:#8B6CFF}
[data-testid="stDataFrame"]{border:1px solid #3A3180;border-radius:12px;overflow:hidden}
[data-testid="stAlert"]{border-radius:12px;border:1px solid #3A3180}
[data-testid="stExpander"]{background:#1C1745;border:1px solid #3A3180;border-radius:12px}
[data-testid="stMetric"]{background:#1C1745;border:1px solid #3A3180;border-radius:12px;padding:12px 16px}
.pt-wrap{margin:10px 0 18px;overflow-x:auto;border:1px solid #3A3180;border-radius:14px;background:#1C1745}
.pt-title{padding:10px 16px;background:#241E5A;font-family:"Unbounded","Arial Black",sans-serif;font-size:.85rem;border-left:4px solid #8B6CFF}
.pt{width:100%;border-collapse:collapse;font-size:.88rem}
.pt th{padding:9px 14px;text-align:left;color:#9A93D1;font-weight:600;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;border-bottom:1px solid #3A3180;white-space:nowrap}
.pt td{padding:9px 14px;border-bottom:1px solid rgba(58,49,128,.45);white-space:nowrap}
.pt th.n,.pt td.n{text-align:right;font-variant-numeric:tabular-nums}
.pt tr:last-child td{border-bottom:0}.pt tbody tr:hover{background:rgba(139,108,255,.1)}
.pt td.top{color:#35D6A0;font-weight:700}
</style>"""
st.markdown(PAGE_CSS.replace("\n", "") + home_html.CSS.replace("\n", ""), unsafe_allow_html=True)


def page_header(tag, title):
    st.markdown('<div class="ph"><span class="tag">%s</span><h1>%s</h1></div>' % (tag, title),
                unsafe_allow_html=True)


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
    return ai_review.short_review(opendota.get_match(match_id), _cached_heroes())


# ---- статистика для розкритих карток у сітці (кеш в пам'яті сервера) ----
@st.cache_resource
def _stats_store():
    return {}


def _fetch_stats(mid, heroes, store):
    """Готує html статистики і кладе в кеш. Успіх кешується надовго, помилка ненадовго.

    Працює у фоновому потоці, тому жодних викликів st.* тут немає.
    """
    try:
        match = opendota.get_match(int(mid))
        parsed = opendota.is_parsed(match)
        text = match_stats_html(match, heroes, parsed=parsed)
        ttl = 3600 if parsed else 300
    except opendota.OpenDotaError as e:
        text = '<div class="note">%s</div>' % html.escape(str(e))
        ttl = 120
    except Exception:
        text = '<div class="note">Не вдалося завантажити статистику.</div>'
        ttl = 60
    store[mid] = (time.time() + ttl, text)


def load_stats(mids, heroes):
    """{match_id: html} для всіх потрібних матчів; нові запити йдуть паралельно."""
    store = _stats_store()
    now = time.time()
    todo = [m for m in mids if not (m in store and now < store[m][0])]
    if todo:
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda m: _fetch_stats(m, heroes, store), todo))
    return {m: store[m][1] for m in mids if m in store}


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
            with st.spinner("AI аналізує матч (локальна модель, може зайняти до хвилини)..."):
                st.session_state[ai_key] = cached_ai_short(mid)
        except (ai_review.AIError, opendota.OpenDotaError) as e:
            st.session_state.pop(ai_key, None)
            st.error(str(e))
    if ai_key in st.session_state:
        st.info(st.session_state[ai_key])

    players = match["players"]
    for title, flag in (("Radiant", True), ("Dire", False)):
        st.markdown(players_table_html([p for p in players if is_radiant(p) == flag], heroes, title),
                    unsafe_allow_html=True)


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
    st.caption("Формат матчів: BO%d. Бурштинова рамка: матч готовий до гри. М'ятна: завершено, "
               "натисніть на завершений матч, щоб побачити статистику. "
               "Сторінка оновлюється кожні %d с." % (bo, REFRESH_SECONDS))
    mids = {s["result"]["dota_match_id"] for s in slots.values()
            if s["result"] and s["result"]["dota_match_id"]}
    stats = load_stats(mids, cached_heroes()) if mids else {}
    st.markdown(bracket_html(len(teams), slots, stats), unsafe_allow_html=True)


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
    st.dataframe(table, hide_index=True)


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
    teams, started, bo, results, slots = load_state()
    st.markdown(home_html.welcome_html(teams, started, bo, slots, EVENT_DATE, EVENT_PLACE, STREAM_URL),
                unsafe_allow_html=True)
    st.write("")
    st.info("Учасникам: перед грою ввімкніть у Dota 2 «Журнал матчів доступний усім» "
            "(Налаштування → Спільнота → Параметри), інакше статистика матчу не з'явиться.")
    b1, b2, _ = st.columns([1, 1, 3])
    b1.page_link(PAGE_TABLE, label="Турнірна таблиця", icon="🏆")
    b2.page_link(PAGE_GAMES, label="Ігри та аналіз", icon="📊")


def table_page():
    page_header("Live", "🏆 Турнірна таблиця")
    tab_bracket, tab_table = st.tabs(["Сітка", "Таблиця команд"])
    with tab_bracket:
        bracket_view()
    with tab_table:
        table_view()
    if st.session_state.get("is_admin", False):
        st.divider()
        results_admin()


def games_page():
    page_header("Матчі", "📊 Ігри та аналіз")
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


def admin_page():
    """Прихована сторінка входу: адреса /admin, у меню її немає."""
    page_header("Лише для організаторів", "🔐 Вхід організатора")
    if st.session_state.get("is_admin", False):
        st.success("Ви вже в режимі організатора.")
        if st.button("Вийти з режиму організатора"):
            st.session_state["is_admin"] = False
            st.rerun()
        st.page_link(PAGE_WELCOME, label="На головну", icon="🏠")
        return
    password = admin_password()
    if not password:
        st.warning("Пароль організатора не задано. Додайте admin_password у Secrets "
                   "(або змінну TOURNAMENT_ADMIN_PASSWORD).")
        return
    with st.form("login"):
        entered = st.text_input("Пароль", type="password")
        submitted = st.form_submit_button("Увійти", type="primary")
    if submitted:
        if hmac.compare_digest(entered.encode("utf-8"), password.encode("utf-8")):
            st.session_state["is_admin"] = True
            st.switch_page(PAGE_WELCOME)  # після входу повертаємо на головну
        else:
            time.sleep(1)  # уповільнює підбір пароля
            st.error("Неправильний пароль.")


# ---------------------------------------------------------------- навігація
PAGE_WELCOME = st.Page(welcome_page, title="Привітання", icon="🏠", url_path="welcome", default=True)
PAGE_TABLE = st.Page(table_page, title="Турнірна таблиця", icon="🏆", url_path="bracket")
PAGE_GAMES = st.Page(games_page, title="Ігри та аналіз", icon="📊", url_path="games")
PAGE_ADMIN = st.Page(admin_page, title="Вхід організатора", icon="🔐", url_path="admin")
# position="hidden": стандартне меню не показується, свої посилання нижче (без /admin)
pg = st.navigation([PAGE_WELCOME, PAGE_TABLE, PAGE_GAMES, PAGE_ADMIN], position="hidden")

# ---------------------------------------------------------------- бічна панель
is_admin = st.session_state.get("is_admin", False)

with st.sidebar:
    st.markdown('<div class="brand"><div class="lg">🏆</div><div><b>Dota 2 · ФТІ КПІ</b>'
                '<span>Турнірна система</span></div></div>', unsafe_allow_html=True)
    st.page_link(PAGE_WELCOME, label="Привітання", icon="🏠")
    st.page_link(PAGE_TABLE, label="Турнірна таблиця", icon="🏆")
    st.page_link(PAGE_GAMES, label="Ігри та аналіз", icon="📊")

    if STREAM_URL:
        st.markdown('<a class="stream-btn" href="%s" target="_blank" '
                    'rel="noopener noreferrer">📺 Дивитись стрім</a>' % html.escape(STREAM_URL, quote=True),
                    unsafe_allow_html=True)
    else:
        st.markdown('<span class="stream-btn off">📺 Стрім скоро буде</span>',
                    unsafe_allow_html=True)

    if is_admin:
        st.divider()
        st.header("Керування турніром")
        if st.button("Вийти з режиму організатора"):
            st.session_state["is_admin"] = False
            st.rerun()
        teams = storage.get_teams()
        if not storage.is_started():
            st.caption("Додайте %s команд. Порядок додавання = номер у сітці. "
                       "При 12 і 14 командах перші в списку отримують bye "
                       "(одразу у другий раунд верхньої сітки)." % T.sizes_text())
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
                st.info("Команд: %d. Потрібно %s." % (len(teams), T.sizes_text()))
        else:
            st.write("Команд: **%d**, формат: **BO%d**" % (len(teams), storage.get_bo()))
            with st.expander("Скинути турнір"):
                st.warning("Буде видалено всі команди та результати.")
                sure = st.checkbox("Так, видалити все", key="reset_ok")
                if st.button("Скинути", disabled=not sure):
                    storage.reset_all()
                    flash("Турнір скинуто.")
                    st.rerun()

if "flash" in st.session_state:
    kind, message = st.session_state.pop("flash")
    getattr(st, kind)(message)

pg.run()
