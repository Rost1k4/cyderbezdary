"""Dota 2 Tournament Manager (ФТІ КПІ).

Запускається через main.py (кнопка Run), окремо нічого вводити не треба.
Сторінки: 1) Привітання  2) Турнірна таблиця  3) Ігри та аналіз.
Є ще прихована сторінка входу організатора: /cibybybyznik (її немає в меню).
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
import config
import home_html
import opendota
import screenshot_ai
import clipboard_paste
import storage
import tournament as T
from bracket_html import bracket_html, match_stats_html, players_table_html, screenshot_stats_html
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
.stApp{background-color:#120F2E;background-image:radial-gradient(640px 420px at 92% -6%,rgba(139,108,255,.30),transparent 70%),radial-gradient(520px 420px at -4% 102%,rgba(79,140,255,.18),transparent 70%)}
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
.stream-btn{display:block;text-align:center;background:linear-gradient(135deg,#8B6CFF,#C45CFF);color:#fff !important;padding:11px 12px;border-radius:12px;font-weight:700;text-decoration:none !important;transition:transform .2s,box-shadow .2s}
.stream-btn:hover{transform:translateY(-2px);box-shadow:0 12px 30px rgba(139,108,255,.5)}
.stream-btn.off{background:#241E5A;color:#9A93D1 !important;border:1px solid #3A3180;box-shadow:none}
[data-testid="stBaseButton-secondary"],[data-testid="stBaseButton-secondaryFormSubmit"]{border-radius:10px;border:1px solid #3A3180;background:#1C1745;transition:transform .15s,border-color .15s}
[data-testid="stBaseButton-secondary"]:hover,[data-testid="stBaseButton-secondaryFormSubmit"]:hover{border-color:#8B6CFF;transform:translateY(-1px)}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{border:0;border-radius:10px;background:linear-gradient(135deg,#8B6CFF,#6F4FE8);box-shadow:0 6px 18px rgba(139,108,255,.35)}
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


def secret(name, env_name=None):
    """Значення з Secrets або змінної середовища (None, якщо не задано)."""
    value = os.environ.get(env_name or name.upper())
    if value:
        return value
    try:
        return st.secrets.get(name)
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
    for key, games in storage.get_match_stats().items():
        stats["ss:" + key] = screenshot_stats_html(games)
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
    selected_key = None
    ready = [s for s in slots.values() if s["status"] == "ready"]
    if not ready:
        st.info("Турнір завершено." if champ else "Немає матчів, готових до гри.")
    else:
        options = {"%s: %s vs %s" % (s["key"], s["a"], s["b"]): s["key"] for s in ready}
        chosen = st.selectbox("Матч", list(options))
        key = options[chosen]
        selected_key = key
        s = slots[key]
        need = bo // 2 + 1
        c1, c2 = st.columns(2)
        score_a = c1.number_input("Рахунок: %s" % s["a"], 0, need, 0, key="sa_" + key)
        score_b = c2.number_input("Рахунок: %s" % s["b"], 0, need, 0, key="sb_" + key)
        winner_op = st.selectbox("Переміг", [s["a"], s["b"]], index=0, key="winner_" + key)
        dota_id = st.text_input("Dota Match ID",
                                key="did_" + key)
        confirmed = st.checkbox("Підтверджую, що результат остаточний", key="cf_" + key)
        if st.button("Зберегти результат", type="primary", disabled=not confirmed):
            err = T.validate_result(bo, int(score_a), int(score_b))
            if not err and dota_id.strip() and not dota_id.strip().isdigit():
                err = "Dota Match ID має складатися лише з цифр."
            if err:
                st.error(err)
            else:
                winner = winner_op
                storage.save_result(key, int(score_a), int(score_b), winner,
                                    dota_id.strip() or None)
                flash("Збережено %s: %s %d:%d %s. Переможець: %s."
                      % (key, s["a"], score_a, score_b, s["b"], winner))
                st.rerun()

    with st.expander("📷 Додати матч через скріншот", expanded=False):
        st.caption("Встав або завантаж скріншот. AI спробує заповнити всю статистику: переможця, тривалість, рахунок убивств, назви команд, героїв і всі колонки гравців. Перевір дані перед збереженням.")
        ready2 = [s for s in slots.values() if s["status"] == "ready"]
        if not ready2:
            st.info("Немає доступних матчів для додавання через скріншот.")
        else:
            opts = {"%s: %s vs %s" % (s["key"], s["a"], s["b"]): s for s in ready2}
            chosen2 = st.selectbox("Матч для скріншота", list(opts), key="ss_result_match")
            slot = opts[chosen2]
            pasted_images = clipboard_paste.paste_images(key="ss_clipboard_inline") or []
            ss_files = st.file_uploader("Або завантаж фото/скріншот матчу (можна кілька)", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="ss_uploader_inline")
            image_inputs = [(f.getvalue(), f.type or "image/png") for f in (ss_files or [])]
            image_inputs.extend((__import__("base64").b64decode(item["data"]), item.get("mime", "image/png")) for item in pasted_images if item.get("data"))
            ai_ready = screenshot_ai.configured(secret("gemini_api_key", "GEMINI_API_KEY"), secret("ollama_vision_model", "OLLAMA_VISION_MODEL"), secret("openrouter_api_key", "OPENROUTER_API_KEY"))
            if st.button("🔍 Проаналізувати весь скріншот", key="ss_analyze_inline", disabled=not image_inputs or not ai_ready):
                try:
                    with st.spinner("AI зчитує всі доступні поля зі скріншота..."):
                        draft = screenshot_ai.extract(image_inputs,
                            gemini_key=secret("gemini_api_key", "GEMINI_API_KEY"),
                            gemini_model=secret("gemini_model", "GEMINI_MODEL"),
                            ollama_host=secret("ollama_host", "OLLAMA_HOST"),
                            ollama_model=secret("ollama_vision_model", "OLLAMA_VISION_MODEL"),
                            openrouter_key=secret("openrouter_api_key", "OPENROUTER_API_KEY"),
                            openrouter_model=secret("openrouter_model", "OPENROUTER_MODEL") or "google/gemini-2.5-flash")
                    st.session_state["ss_ai_draft_inline"] = draft
                    st.session_state["ss_ai_version_inline"] = st.session_state.get("ss_ai_version_inline", 0) + 1
                    rt = (draft.get("radiant_team") or "").strip().casefold()
                    dt = (draft.get("dire_team") or "").strip().casefold()
                    a_name, b_name = slot["a"].strip().casefold(), slot["b"].strip().casefold()
                    radiant_is_a = bool(rt and rt == a_name)
                    radiant_is_b = bool(rt and rt == b_name)
                    dire_is_a = bool(dt and dt == a_name)
                    dire_is_b = bool(dt and dt == b_name)
                    winner_team = None
                    if draft.get("radiant_win") is True:
                        winner_team = slot["a"] if radiant_is_a else slot["b"] if radiant_is_b else None
                    elif draft.get("radiant_win") is False:
                        winner_team = slot["a"] if dire_is_a else slot["b"] if dire_is_b else None
                    if winner_team:
                        st.session_state["ss_winner_inline"] = winner_team
                    st.success("Розпізнавання завершено. Нижче показані всі дані, які AI зміг зчитати; перевір їх перед збереженням.")
                except screenshot_ai.VisionError as e:
                    st.error(str(e))
            if not ai_ready:
                st.info("Для AI-аналізу додайте OPENROUTER_API_KEY або gemini_api_key у Secrets. Завантаження файлу доступне й без AI.")

            draft = st.session_state.get("ss_ai_draft_inline")
            if draft:
                st.markdown("#### Результат розпізнавання — перевір усі поля")
                version = st.session_state.get("ss_ai_version_inline", 0)
                prefix = f"ss_inline_{slot['key']}_{version}_"
                known_radiant = (draft.get("radiant_team") or "").strip()
                known_dire = (draft.get("dire_team") or "").strip()
                col1, col2, col3, col4 = st.columns(4)
                win_options = ["Не визначено", "Radiant", "Dire"]
                win_index = {True: 1, False: 2}.get(draft.get("radiant_win"), 0)
                parsed_winner = col1.selectbox("Переможець у грі", win_options, index=win_index, key=prefix + "win")
                duration = col2.text_input("Тривалість", value=draft.get("duration") or "", key=prefix + "duration")
                radiant_kills = col3.text_input("Убивства Radiant", value="" if draft.get("radiant_score") is None else str(draft.get("radiant_score")), key=prefix + "rscore")
                dire_kills = col4.text_input("Убивства Dire", value="" if draft.get("dire_score") is None else str(draft.get("dire_score")), key=prefix + "dscore")
                tc1, tc2 = st.columns(2)
                radiant_team = tc1.text_input("Назва команди Radiant", value=known_radiant, key=prefix + "rteam")
                dire_team = tc2.text_input("Назва команди Dire", value=known_dire, key=prefix + "dteam")
                cfg = {"Команда": st.column_config.SelectboxColumn("Команда", options=["Radiant", "Dire"], required=True)}
                cfg.update({label: st.column_config.NumberColumn(label, format="%d", step=1) for label, _ in SS_COLS[3:]})
                edited = st.data_editor(stats_to_df(draft), column_config=cfg, num_rows="dynamic", hide_index=True, key=prefix + "players")
                st.caption("Рахунок серії турніру (наприклад, BO3 2:1) відрізняється від кількості вбивств у конкретній грі, тому його введи окремо.")
                map_default = 0
                if known_radiant.strip().casefold() == slot["b"].strip().casefold():
                    map_default = 1
                radiant_tournament_team = st.selectbox(
                    "Яка команда турніру грала за Radiant?",
                    [slot["a"], slot["b"]], index=map_default, key=prefix + "radiant_mapping")
                dire_tournament_team = slot["b"] if radiant_tournament_team == slot["a"] else slot["a"]
                st.caption("Команда Dire у цьому матчі: %s. Якщо назви команд не видно на скріншоті, обери відповідність вручну." % dire_tournament_team)
                sc1, sc2 = st.columns(2)
                series_a = sc1.number_input("Рахунок серії: %s" % slot["a"], 0, bo, 0, key=prefix + "series_a")
                series_b = sc2.number_input("Рахунок серії: %s" % slot["b"], 0, bo, 0, key=prefix + "series_b")
                ss_match_id = st.text_input("Dota Match ID (необов'язково)", key=prefix + "match_id")
                confirm = st.checkbox("Перевірив розпізнані дані та підтверджую результат", key=prefix + "confirm")
                if st.button("💾 Зберегти результат і всю статистику", type="primary", key=prefix + "save", disabled=not confirm):
                    err = T.validate_result(bo, int(series_a), int(series_b))
                    if not err and ss_match_id.strip() and not ss_match_id.strip().isdigit():
                        err = "Dota Match ID має складатися лише з цифр."
                    if err:
                        st.error(err)
                    else:
                        if parsed_winner == "Radiant":
                            winner = radiant_tournament_team
                        elif parsed_winner == "Dire":
                            winner = dire_tournament_team
                        else:
                            winner = None
                        score_winner = slot["a"] if series_a > series_b else slot["b"] if series_b > series_a else None
                        if winner is None:
                            st.error("AI не визначив переможну сторону за зеленою позначкою. Виправ поле «Переможець у грі» перед збереженням.")
                        elif score_winner != winner:
                            st.error("Переможець за рахунком серії не збігається з переможцем гри. Перевір рахунок серії або відповідність Radiant/Dire.")
                        else:
                            players = df_to_players(edited)
                            if not players:
                                st.error("У таблиці немає розпізнаних гравців. Перевір скріншот або додай гравців вручну.")
                            else:
                                storage.save_result(slot["key"], int(series_a), int(series_b), winner, ss_match_id.strip() or None)
                                storage.save_match_stats(slot["key"], 1, {
                                    "radiant_win": parsed_winner == "Radiant",
                                    "duration": duration.strip() or None,
                                    "radiant_score": _opt_int(radiant_kills),
                                    "dire_score": _opt_int(dire_kills),
                                    "radiant_team": radiant_team.strip() or None,
                                    "dire_team": dire_team.strip() or None,
                                    "players": players,
                                })
                                st.session_state.pop("ss_ai_draft_inline", None)
                                flash("Результат матчу %s і статистику першої гри збережено." % slot["key"])
                                st.rerun()
            else:
                st.caption("Після аналізу тут з'являться назви команд, переможець, тривалість, рахунок убивств і повна таблиця гравців.")

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


# --------------------------------------------- статистика зі скріншота (організатор)
def match_id_admin():
    """Додати або змінити Dota Match ID вже збереженого результату."""
    teams, started, bo, results, slots = load_state()
    played = [s for s in slots.values() if s["result"]] if started else []
    if not played:
        return
    st.subheader("🔢 Dota Match ID матчу")
    options = {"%s: %s vs %s" % (s["key"], s["a"], s["b"]): s["key"] for s in played}
    mk = options[st.selectbox("Матч", list(options), key="mid_match")]
    current = results[mk]["dota_match_id"] or ""
    new = st.text_input("Dota Match ID (не ID лобі). Порожнє поле прибирає ID.", value=current,
                        key="mid_val_%s_%s" % (mk, current))
    if st.button("Зберегти Match ID", key="mid_save_" + mk):
        new = new.strip()
        if new and not new.isdigit():
            st.error("Dota Match ID має складатися лише з цифр.")
        else:
            storage.set_dota_match_id(mk, new or None)
            flash("Match ID матчу %s %s." % (mk, "збережено" if new else "прибрано"))
            st.rerun()


SS_COLS = [("Команда", "team"), ("Гравець", "name"), ("Герой", "hero_name"), ("K", "kills"), ("D", "deaths"),
           ("A", "assists"), ("LH", "last_hits"), ("DN", "denies"), ("GPM", "gold_per_min"),
           ("XPM", "xp_per_min"), ("Шкода героям", "hero_damage"), ("Шкода вежам", "tower_damage")]
SS_NUM = [k for _, k in SS_COLS[3:]]


def stats_to_df(data):
    rows = [{label: ("Radiant" if p.get("team") == "radiant" else "Dire") if key == "team" else p.get(key)
             for label, key in SS_COLS} for p in data.get("players", [])]
    df = pd.DataFrame(rows, columns=[c for c, _ in SS_COLS])
    for label, key in SS_COLS[3:]:
        df[label] = pd.to_numeric(df[label], errors="coerce").astype("Int64")
    return df


def df_to_players(df):
    players = []
    for _, row in df.iterrows():
        name = row["Гравець"] if pd.notna(row["Гравець"]) else None
        hero = row["Герой"] if pd.notna(row["Герой"]) else None
        if not name and not hero:
            continue
        p = {"team": "dire" if row["Команда"] == "Dire" else "radiant",
             "name": str(name).strip() if name else None, "hero_name": str(hero).strip() if hero else None}
        for label, key in SS_COLS[3:]:
            p[key] = None if pd.isna(row[label]) else int(row[label])
        players.append(p)
    return players


def _opt_int(text):
    text = (text or "").strip()
    return int(text) if text.isdigit() else None


def _clean_team_name(value):
    """Фільтрує загальні ярлики Radiant/Dire, які не є реальними назвами команд."""
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"radiant", "dire", "не вказано", "not specified", "", "null", "none"}:
        return ""
    return text


def render_screenshot_stats_form(mk, key_prefix="ss"):
    teams, started, bo, results, slots = load_state()
    slot = slots[mk]
    games_played = max(1, slot["result"]["score_a"] + slot["result"]["score_b"]) if slot.get("result") else 1
    game = st.selectbox("Гра №", list(range(1, games_played + 1)), key=f"{key_prefix}_ss_game_{mk}")
    saved = storage.get_match_stats().get(mk, {}).get(game)
    base = f"{key_prefix}_{mk}_{game}"

    key_g, model_g = secret("gemini_api_key", "GEMINI_API_KEY"), secret("gemini_model", "GEMINI_MODEL")
    openrouter_key = secret("openrouter_api_key", "OPENROUTER_API_KEY")
    openrouter_model = secret("openrouter_model", "OPENROUTER_MODEL") or "google/gemini-2.5-flash"
    host_o, model_o = secret("ollama_host", "OLLAMA_HOST"), secret("ollama_vision_model", "OLLAMA_VISION_MODEL")
    if not screenshot_ai.configured(key_g, model_o, openrouter_key):
        st.info("AI для скріншотів не налаштований (додайте gemini_api_key або openrouter_api_key у Secrets), "
                "але таблицю можна заповнити вручну.")

    st.caption("Можна перетягнути файл або вставити зі скілу: Ctrl+V у поле нижче.")
    pasted = clipboard_paste.paste_images(key=f"{key_prefix}_ss_clip_{base}") or []
    files = st.file_uploader("Або завантаж скріншот(и): PNG, JPG або WEBP (до %d файлів)" % screenshot_ai.MAX_IMAGES,
                            type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                            key=f"{key_prefix}_ssf_{base}")
    image_inputs = [(f.getvalue(), f.type or "image/png") for f in (files or [])]
    image_inputs.extend((__import__("base64").b64decode(item["data"]), item.get("mime", "image/png")) for item in pasted if item.get("data"))
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("🔍 Розпізнати", type="primary", key=f"{key_prefix}_ssgo_{base}",
                 disabled=not image_inputs or not screenshot_ai.configured(key_g, model_o, openrouter_key)):
        try:
            with st.spinner("AI читає таблицю зі скріншота..."):
                draft = screenshot_ai.extract(image_inputs,
                                              gemini_key=key_g, gemini_model=model_g,
                                              ollama_host=host_o, ollama_model=model_o,
                                              openrouter_key=openrouter_key,
                                              openrouter_model=openrouter_model)
            st.session_state["ssd_" + base] = draft
            st.session_state[f"{key_prefix}_ssv_{base}"] = st.session_state.get(f"{key_prefix}_ssv_{base}", 0) + 1
        except screenshot_ai.VisionError as e:
            st.error(str(e))
    if c2.button("✍️ Заповнити вручну", key=f"{key_prefix}_ssm_{base}"):
        st.session_state["ssd_" + base] = screenshot_ai.empty_template()
        st.session_state[f"{key_prefix}_ssv_{base}"] = st.session_state.get(f"{key_prefix}_ssv_{base}", 0) + 1

    draft = st.session_state.get("ssd_" + base)
    data = draft or saved
    if not data:
        st.caption("Вставте скріншот через Ctrl+V у поле вище або завантажте файл, потім натисніть «Розпізнати». Можна також заповнити таблицю вручну.")
        return
    ver = st.session_state.get(f"{key_prefix}_ssv_{base}", 0)
    if draft:
        st.warning("Це чернетка від AI. Обов'язково перевірте цифри, бо AI може помилитися, і лише потім зберігайте.")
    else:
        st.caption("Збережена статистика цієї гри. Можна виправити й зберегти знову.")

    k = f"{key_prefix}_ssw_{base}_{ver}_"
    m1, m2, m3, m4 = st.columns(4)
    win_opts = ["не вказано", "Radiant", "Dire"]
    win_idx = {True: 1, False: 2}.get(data.get("radiant_win"), 0)
    winner = m1.selectbox("Переміг", win_opts, index=win_idx, key=k + "win")
    duration = m2.text_input("Тривалість (хв:сек)", value=data.get("duration") or "", key=k + "dur")
    r_score = m3.text_input("Вбивства Radiant", value="" if data.get("radiant_score") is None
                            else str(data["radiant_score"]), key=k + "rs")
    d_score = m4.text_input("Вбивства Dire", value="" if data.get("dire_score") is None
                            else str(data["dire_score"]), key=k + "ds")

    radiant_default = _clean_team_name(data.get("radiant_team")) or (slot["a"] if slot.get("a") else "")
    dire_default = _clean_team_name(data.get("dire_team")) or (slot["b"] if slot.get("b") else "")
    radiant_team = st.text_input("Radiant: команда", value=radiant_default, key=k + "rt")
    dire_team = st.text_input("Dire: команда", value=dire_default, key=k + "dt")

    cfg = {"Команда": st.column_config.SelectboxColumn("Команда", options=["Radiant", "Dire"], required=True)}
    cfg.update({label: st.column_config.NumberColumn(label, format="%d", step=1) for label, _ in SS_COLS[3:]})
    edited = st.data_editor(stats_to_df(data), column_config=cfg, num_rows="dynamic",
                            hide_index=True, key=k + "ed")

    b1, b2, _ = st.columns([1, 1, 2])
    if b1.button("💾 Зберегти статистику", type="primary", key=f"{key_prefix}_sssave_{base}"):
        players = df_to_players(edited)
        if not players:
            st.error("Таблиця порожня.")
        else:
            storage.save_match_stats(mk, game, {
                "radiant_win": {"Radiant": True, "Dire": False}.get(winner),
                "duration": duration.strip() or None,
                "radiant_score": _opt_int(r_score), "dire_score": _opt_int(d_score),
                "radiant_team": _clean_team_name(radiant_team) or None,
                "dire_team": _clean_team_name(dire_team) or None,
                "players": players})
            st.session_state.pop("ssd_" + base, None)
            flash("Статистику матчу %s (гра %d) збережено." % (mk, game))
            st.rerun()
    if saved and b2.button("🗑 Видалити збережену", key=f"{key_prefix}_ssdel_{base}"):
        storage.delete_match_stats(mk, game)
        st.session_state.pop("ssd_" + base, None)
        flash("Статистику матчу %s (гра %d) видалено." % (mk, game), "warning")
        st.rerun()


def screenshot_admin():
    """Адмінський блок для додавання/редагування статистики зі скріншотів завершених матчів."""
    teams, started, bo, results, slots = load_state()
    st.subheader("📷 Статистика зі скріншота")
    if not started:
        st.info("Спочатку запустіть турнір.")
        return

    played = [key for key, slot in slots.items() if slot.get("result")]
    if not played:
        st.info("Ще немає завершених матчів, для яких можна додати статистику зі скріншота.")
        return

    labels = {
        "%s: %s vs %s" % (key, slots[key]["a"], slots[key]["b"]): key
        for key in played
    }
    chosen_label = st.selectbox(
        "Матч для додавання або редагування статистики",
        list(labels),
        key="screenshot_admin_match",
    )
    render_screenshot_stats_form(labels[chosen_label], key_prefix="admin_ss")


# =============================================================== СТОРІНКИ
def welcome_page():
    teams, started, bo, results, slots = load_state()
    st.markdown(home_html.welcome_html(teams, started, bo, slots, EVENT_DATE, EVENT_PLACE, STREAM_URL),
                unsafe_allow_html=True)
    st.write("")
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
    shots = storage.get_match_stats()
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
                if shots.get(s["key"]):
                    st.markdown(screenshot_stats_html(shots[s["key"]], full=True), unsafe_allow_html=True)
                if not mid:
                    if not shots.get(s["key"]):
                        st.caption("Статистику цього матчу ще не додано.")
                    continue
                st.caption("Dota Match ID: %s" % mid)
                if st.toggle("Показати аналіз", key="tg_" + s["key"]):
                    render_match_analysis(int(mid), "log_" + s["key"])

    if st.session_state.get("is_admin", False):
        st.divider()
        match_id_admin()
        st.divider()
        screenshot_admin()

    st.divider()
    st.subheader("Статистика за Match ID")
    with st.form("match_form"):
        match_id = st.text_input("Match ID завершеного матчу")
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
    """Прихована сторінка входу: адреса /cibybybyznik, у меню її немає."""
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
PAGE_ADMIN = st.Page(admin_page, title="Вхід організатора", icon="🔐", url_path="cibybybyznik")
# position="hidden": стандартне меню не показується, свої посилання нижче (без сторінки входу)
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
