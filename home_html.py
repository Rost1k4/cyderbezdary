"""HTML та CSS головної сторінки. Не залежить від Streamlit (можна тестувати окремо)."""
import html

import tournament as T

CSS = """<style>
.hero{display:grid;grid-template-columns:1.05fr .95fr;gap:40px;align-items:center;padding:30px 4px 22px;animation:fup .8s ease both}
.pill{display:inline-flex;align-items:center;gap:9px;background:rgba(36,30,90,.7);border:1px solid #3A3180;border-radius:999px;padding:7px 16px;font-size:.8rem;font-weight:600;color:#9A93D1}
.pill i{width:8px;height:8px;border-radius:50%;background:#35D6A0;animation:ping 2s infinite}
@keyframes ping{0%{box-shadow:0 0 0 0 rgba(53,214,160,.7)}70%{box-shadow:0 0 0 10px rgba(53,214,160,0)}100%{box-shadow:0 0 0 0 rgba(53,214,160,0)}}
@keyframes fup{from{opacity:0;transform:translateY(22px)}to{opacity:1;transform:none}}
@keyframes flt{50%{transform:translateY(-12px)}}
.hero h1.hh{font-size:clamp(2.4rem,6vw,4.4rem);font-weight:800;margin:20px 0 16px;padding:0;line-height:1.05}
.hero h1.hh em{font-style:normal;display:block;background:linear-gradient(90deg,#4F8CFF,#C45CFF 55%,#FFD166);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{color:#9A93D1;font-size:1.08rem;max-width:540px;margin:0}
.chips{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}
.chip{background:#1C1745;border:1px solid #3A3180;border-radius:10px;padding:7px 14px;font-size:.8rem;font-weight:700}
.chip.b{border-color:#4F8CFF;color:#4F8CFF}.chip.p{border-color:#C45CFF;color:#C45CFF}.chip.g{border-color:#FFD166;color:#FFD166}
.meta{display:flex;flex-wrap:wrap;gap:18px;margin-top:20px;color:#9A93D1;font-size:.9rem}
.stage{position:relative;height:400px}
.mc{position:absolute;width:262px;background:#1C1745;border:1px solid #3A3180;border-radius:14px;overflow:hidden;box-shadow:0 22px 50px rgba(0,0,0,.45);animation:flt 6s ease-in-out infinite}
.mc .hd{display:flex;justify-content:space-between;font-size:.72rem;padding:5px 12px;background:#241E5A;color:#9A93D1}
.mc .r{display:flex;justify-content:space-between;gap:10px;padding:9px 12px;font-size:.92rem}
.mc .r.w{background:rgba(53,214,160,.18);color:#35D6A0;font-weight:700}.mc .r.l{opacity:.5}.mc .r.d{color:#9A93D1;font-style:italic}
.mc.c1{border-color:#35D6A0;top:0;left:0}
.mc.c2{border-color:#FF9F43;box-shadow:0 0 0 1px #FF9F43,0 22px 50px rgba(255,159,67,.18);top:128px;right:0;animation-delay:-2s}
.mc.c3{border-color:#FFD166;top:262px;left:32px;animation-delay:-4s}.mc.c3 .hd{color:#FFD166}
.cap{position:absolute;bottom:-4px;right:0;font-size:.72rem;color:#9A93D1}
.champ{margin:6px 0 4px;padding:16px 22px;border-radius:16px;border:1px solid #FFD166;background:linear-gradient(90deg,rgba(255,209,102,.2),rgba(255,209,102,.04));font-size:1.15rem;animation:fup .6s ease both}
.champ b{color:#FFD166;font-family:"Unbounded","Arial Black",sans-serif}
.ticker{margin:14px 0 26px;border-block:1px solid #3A3180;background:rgba(28,23,69,.6);overflow:hidden;white-space:nowrap}
.ticker div{display:inline-block;padding:13px 0;animation:run 34s linear infinite;font-family:"Unbounded","Arial Black",sans-serif;font-size:.78rem;letter-spacing:.06em;color:#9A93D1}
.ticker b{color:#ECE9FF;font-weight:500;margin:0 20px}.ticker span{color:#8B6CFF}
@keyframes run{to{transform:translateX(-50%)}}
.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;animation:fup .9s ease both}
.fact{padding:22px 18px 18px;background:#1C1745;border:1px solid #3A3180;border-radius:16px;position:relative;overflow:hidden;transition:transform .2s,border-color .2s}
.fact:hover{transform:translateY(-3px);border-color:#8B6CFF}
.fact::after{content:"";position:absolute;left:0;right:0;top:0;height:3px;background:linear-gradient(90deg,#4F8CFF,#C45CFF,#FFD166)}
.fact b{display:block;font-family:"Unbounded","Arial Black",sans-serif;font-size:clamp(1.3rem,2.4vw,1.9rem);font-weight:700}
.fact span{color:#9A93D1;font-size:.84rem}
.sh{margin:46px 0 6px}.sh .tag{color:#8B6CFF;font-weight:700;letter-spacing:.16em;font-size:.74rem;text-transform:uppercase}
.sh h2{font-size:clamp(1.4rem,3vw,2.1rem);margin:8px 0 8px;padding:0}.sh p{color:#9A93D1;max-width:620px;margin:0}
.grad{background:linear-gradient(90deg,#4F8CFF,#C45CFF 55%,#FFD166);-webkit-background-clip:text;background-clip:text;color:transparent}
.paths{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:20px}
.path{position:relative;background:#1C1745;border:1px solid #3A3180;border-radius:18px;padding:24px 22px;overflow:hidden;transition:transform .2s,border-color .2s}
.path:hover{transform:translateY(-3px);border-color:var(--c)}
.path::before{content:"";position:absolute;inset:0;background:radial-gradient(240px 160px at 0 0,var(--c),transparent 70%);opacity:.16}
.path .n{font-family:"Unbounded","Arial Black",sans-serif;font-size:2.8rem;font-weight:800;color:var(--c);line-height:1;position:relative}
.path h3{font-size:1rem;margin:12px 0 6px;color:var(--c);padding:0;position:relative}.path p{color:#9A93D1;font-size:.92rem;margin:0;position:relative}
.path.wb{--c:#4F8CFF}.path.lb{--c:#C45CFF}.path.gf{--c:#FFD166}
.bento{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:20px}
.tile{background:#1C1745;border:1px solid #3A3180;border-radius:18px;padding:22px;transition:transform .2s,border-color .2s,box-shadow .2s}
.tile:hover{transform:translateY(-3px);border-color:#8B6CFF;box-shadow:0 14px 34px rgba(139,108,255,.18)}
.tile h3{font-family:"Onest",system-ui,sans-serif!important;font-weight:700;font-size:1.02rem;margin:0 0 6px;padding:0}.tile p{color:#9A93D1;font-size:.9rem;margin:0}
.live{display:inline-flex;align-items:center;gap:8px;margin-top:14px;background:rgba(255,159,67,.14);color:#FF9F43;border:1px solid #FF9F43;border-radius:999px;padding:4px 13px;font-weight:700;font-size:.78rem;letter-spacing:.1em}
.live i{width:8px;height:8px;border-radius:50%;background:#FF9F43;animation:ping 1.6s infinite}
.live.off{color:#9A93D1;border-color:#3A3180;background:#241E5A}.live.off i{background:#9A93D1;animation:none}
@media (max-width:900px){.hero{grid-template-columns:1fr}.stage{height:390px;max-width:380px;width:100%;margin:0 auto}
.facts{grid-template-columns:repeat(2,1fr)}.paths{grid-template-columns:1fr}.bento{grid-template-columns:repeat(2,1fr)}}
@media (max-width:560px){.bento{grid-template-columns:1fr}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>"""


def _e(x):
    return html.escape(str(x))


def _mini(cls, key, status, rows):
    body = "".join('<div class="r %s"><span>%s</span>%s</div>'
                   % (c, _e(t), ("<b>%s</b>" % _e(sc)) if sc != "" else "") for c, t, sc in rows)
    return ('<div class="mc %s"><div class="hd"><span>%s</span><span>%s</span></div>%s</div>'
            % (cls, _e(key), _e(status), body))


def stage_html(started, slots):
    """Три картки матчів: реальні, коли турнір іде, інакше приклад."""
    if not started:
        cards = [
            _mini("c1", "W1", "Завершено", [("w", "Команда A", 2), ("l", "Команда B", 1)]),
            _mini("c2", "W2", "Готовий до гри", [("", "Команда C", ""), ("", "Команда D", "")]),
            _mini("c3", "GF", "Очікує", [("d", "Переможець W3", ""), ("d", "Переможець L2", "")]),
        ]
        caption = "Приклад карток матчів"
    else:
        cards = []
        done = [s for s in slots.values() if s["result"]]
        ready = [s for s in slots.values() if s["status"] == "ready"]
        if done:
            s = done[-1]
            r = s["result"]
            rows = [("w" if r["winner"] == s[k] else "l", s[k], r["score_" + k]) for k in ("a", "b")]
            cards.append(_mini("c1", s["key"], "Завершено", rows))
        if ready:
            s = ready[0]
            cards.append(_mini("c2", s["key"], "Готовий до гри", [("", s["a"], ""), ("", s["b"], "")]))
        gf = slots["GF"]
        gf_rows = [("" if gf[k] else "d", gf[k] or gf[k + "_label"], "") for k in ("a", "b")]
        cards.append(_mini("c3", "GF", "Grand Final" if gf["status"] != "done" else "Завершено", gf_rows))
        caption = "Актуальні матчі турніру"
    return '<div class="stage">%s<div class="cap">%s</div></div>' % ("".join(cards), caption)


def facts_html(teams, started, bo, slots):
    n = len(teams)
    if started:
        played = sum(1 for s in slots.values() if s["result"])
        status = "Завершено" if T.champion(slots) else "Триває"
        items = [(n, "команд у турнірі"), ("BO%d" % bo, "формат матчів"),
                 ("%d / %d" % (played, len(slots)), "матчів зіграно"), (status, "статус турніру")]
    else:
        items = [(n or "4–16", "команд зареєстровано" if n else "команд на турнірі"),
                 ("BO1·3·5", "формат матчів"), ("2 життя", "вибуваєш після двох поразок"),
                 ("Реєстрація" if n else "Скоро", "статус турніру")]
    return '<div class="facts">%s</div>' % "".join(
        '<div class="fact"><b>%s</b><span>%s</span></div>' % (_e(v), _e(l)) for v, l in items)


def welcome_html(teams, started, bo, slots, event_date, event_place, stream_url):
    champ = T.champion(slots) if started else None
    banner = ('<div class="champ">🏆 Чемпіон турніру: <b>%s</b></div>' % _e(champ)) if champ else ""
    hero = (
        '<div class="hero"><div>'
        '<span class="pill"><i></i>ФТІ КПІ ім. Ігоря Сікорського</span>'
        '<h1 class="hh">Турнір з <em>Dota&nbsp;2</em></h1>'
        '<p>Вітаємо на турнірі з Dota 2! Слідкуйте за сіткою, результатами та детальним аналізом '
        'кожної гри в реальному часі.</p>'
        '<div class="chips"><span class="chip b">Верхня сітка</span><span class="chip p">Нижня сітка</span>'
        '<span class="chip g">Grand Final</span></div>'
        '<div class="meta"><span>📅 %s</span><span>📍 %s</span></div></div>%s</div>'
        % (_e(event_date), _e(event_place), stage_html(started, slots)))
    words = ["DOUBLE ELIMINATION", "BO1 · BO3 · BO5", "ЖИВА СІТКА", "СТАТИСТИКА МАТЧІВ", "AI-РОЗБІР", "ТРАНСЛЯЦІЯ"]
    run = "<span>◆</span>".join("<b>%s</b>" % w for w in words) + "<span>◆</span>"
    ticker = '<div class="ticker"><div>%s%s</div></div>' % (run, run)
    steps = (
        '<div class="sh"><div class="tag">Як це працює</div>'
        '<h2>Одна поразка <span class="grad">не вирішує все</span></h2>'
        '<p>Double elimination дає кожній команді друге життя: щоб вибути, програти доведеться двічі.</p></div>'
        '<div class="paths">'
        '<div class="path wb"><div class="n">01</div><h3>Верхня сітка</h3><p>Стартують усі. Перемагаєш і прямуєш далі верхньою частиною до фіналу верхньої сітки.</p></div>'
        '<div class="path lb"><div class="n">02</div><h3>Нижня сітка</h3><p>Програв у верхній? Це ще не кінець. Тут можна пробитися до фіналу, але наступна поразка остання.</p></div>'
        '<div class="path gf"><div class="n">03</div><h3>Grand Final</h3><p>Переможці верхньої та нижньої сіток зустрічаються в одному вирішальному матчі.</p></div></div>')
    live = ('<span class="live"><i></i>LIVE</span>' if stream_url
            else '<span class="live off"><i></i>СКОРО</span>')
    bento = (
        '<div class="sh"><div class="tag">Що на тебе чекає</div>'
        '<h2>Дивись і грай з <span class="grad">усіма даними</span></h2></div>'
        '<div class="bento">'
        '<div class="tile"><h3>🏆 Жива сітка</h3><p>Хто з ким грає, хто пройшов далі і хто вибув, оновлюється сама.</p></div>'
        '<div class="tile"><h3>📊 Статистика матчу</h3><p>K/D/A, GPM, шкода: натисни на завершений матч у сітці.</p></div>'
        '<div class="tile"><h3>🤖 AI-розбір</h3><p>Коротко про перебіг гри, переломний момент і MVP.</p></div>'
        '<div class="tile"><h3>📺 Трансляція</h3><p>Найцікавіші матчі в прямому ефірі.</p>%s</div></div>' % live)
    return banner + hero + ticker + facts_html(teams, started, bo, slots) + steps + bento
