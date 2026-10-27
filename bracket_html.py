"""Малює турнірну сітку як HTML. Не залежить від Streamlit.

Завершений матч - це <details>: клік по картці розкриває її (вона плавно
розширюється) і показує статистику. Статистику готує app.py і передає
словником stats {dota_match_id: html}, тому тут немає жодних запитів до мережі.
"""
import html

import tournament as T

CSS = """<style>
.br-wrap{overflow-x:auto;padding:4px 2px 14px}
.br-row{display:flex;gap:26px;align-items:stretch;min-width:max-content}
.br-col{display:flex;flex-direction:column;min-width:215px;transition:min-width .35s ease}
.br-col:has(details.m[open]){min-width:640px}
.br-col h5{margin:0 0 6px;font-size:.85rem;font-weight:600;color:#9A93D1}
.br-ms{display:flex;flex-direction:column;justify-content:space-around;gap:14px;flex:1}
.m{border:1px solid #3A3180;border-radius:12px;overflow:hidden;background:#1C1745;color:#ECE9FF;transition:transform .2s,box-shadow .2s,border-color .2s}.m:hover{transform:translateY(-2px)}
.m.ready{border-color:#FF9F43;box-shadow:0 0 0 1px #FF9F43;animation:br-pulse 2.4s ease-in-out infinite}@keyframes br-pulse{50%{box-shadow:0 0 0 1px #FF9F43,0 0 20px rgba(255,159,67,.45)}}
.m.done{border-color:#35D6A0}
.m .hd{display:flex;justify-content:space-between;font-size:.72rem;padding:3px 8px;background:#241E5A;color:#9A93D1}
.m .t{display:flex;justify-content:space-between;gap:10px;padding:6px 8px;font-size:.9rem}
.m .t.tbd{color:#9A93D1;font-style:italic}
.m .t.w{background:rgba(53,214,160,.18);color:#35D6A0;font-weight:700}
.m .t.l{opacity:.5}
details.m>summary{list-style:none;cursor:pointer;display:block}
details.m>summary::-webkit-details-marker{display:none}
details.m>summary:hover .hd{background:#2D2570;color:#ECE9FF}
details.m[open]{border-color:#8B6CFF;box-shadow:0 10px 32px rgba(0,0,0,.5)}
details.m[open]>summary .hd{background:#8B6CFF;color:#fff}
.m .stats{padding:10px 12px 12px;border-top:1px solid #3A3180;animation:br-open .3s ease}
@keyframes br-open{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:none}}
.stats .sum{color:#9A93D1;font-size:.8rem;margin-bottom:6px}
.stats .sum b{color:#ECE9FF}
.stats .sum a{color:#8B6CFF}
.stats .side{font-weight:700;font-size:.85rem;margin:8px 0 2px;color:#ECE9FF}
.stats table{width:100%;border-collapse:collapse;font-size:.78rem}
.stats th{color:#9A93D1;text-align:left;font-weight:600;padding:2px 6px;border-bottom:1px solid #3A3180}
.stats td{padding:3px 6px;border-bottom:1px solid rgba(58,49,128,.5)}
.stats .note{color:#9A93D1;font-size:.78rem;font-style:italic;margin-top:8px}
@media (prefers-reduced-motion:reduce){.br-col{transition:none}.m .stats{animation:none}.m.ready{animation:none}.m{transition:none}}
.sec{border-left:5px solid;padding:8px 16px;margin:26px 0 10px;border-radius:0 12px 12px 0;background:linear-gradient(90deg,rgba(255,255,255,.06),transparent)}
.sec h3{margin:0;padding:0;font-family:"Unbounded","Arial Black",system-ui,sans-serif;font-size:1.02rem;letter-spacing:.02em}
.sec.WB{border-color:#4F8CFF}.sec.WB h3{color:#4F8CFF}
.sec.LB{border-color:#C45CFF}.sec.LB h3{color:#C45CFF}
.sec.GF{border-color:#FFD166}.sec.GF h3{color:#FFD166}
</style>"""

STATUS_TEXT = {"waiting": "Очікує", "ready": "Готовий до гри", "done": "Завершено ▾"}
SECTION_TITLES = {"WB": "Верхня сітка (Winners Bracket)",
                  "LB": "Нижня сітка (Losers Bracket)",
                  "GF": "Grand Final"}


# ------------------------------------------------------ статистика матчу
def _v(p, key):
    value = p.get(key)
    return "н/д" if value is None else html.escape(str(value))


def _is_radiant(p):
    if "isRadiant" in p:
        return bool(p["isRadiant"])
    return p.get("player_slot", 0) < 128


def _duration(seconds):
    if not isinstance(seconds, (int, float)):
        return "н/д"
    return "%d:%02d" % (int(seconds) // 60, int(seconds) % 60)


def match_stats_html(match, heroes, parsed=True):
    """Компактна статистика матчу OpenDota для розкритої картки (один рядок, без \\n)."""
    players = match.get("players") or []
    winner = {True: "Radiant", False: "Dire"}.get(match.get("radiant_win"), "н/д")
    mid = html.escape(str(match.get("match_id", "")))
    parts = ['<div class="sum">Переможець: <b>%s</b> · тривалість %s · вбивства %s:%s · '
             '<a href="https://www.opendota.com/matches/%s" target="_blank" '
             'rel="noopener noreferrer">OpenDota</a></div>'
             % (winner, _duration(match.get("duration")),
                _v(match, "radiant_score"), _v(match, "dire_score"), mid)]
    for title, flag in (("Radiant", True), ("Dire", False)):
        rows = []
        for p in players:
            if _is_radiant(p) != flag:
                continue
            name = html.escape(p.get("personaname") or p.get("name") or "Анонім")
            hero = html.escape(heroes.get(p.get("hero_id"), "Hero #%s" % p.get("hero_id")))
            rows.append("<tr><td>%s</td><td>%s</td><td>%s/%s/%s</td><td>%s</td><td>%s</td></tr>"
                        % (name, hero, _v(p, "kills"), _v(p, "deaths"), _v(p, "assists"),
                           _v(p, "gold_per_min"), _v(p, "hero_damage")))
        parts.append('<div class="side">%s</div><table><tr><th>Гравець</th><th>Герой</th>'
                     '<th>K/D/A</th><th>GPM</th><th>Шкода</th></tr>%s</table>'
                     % (title, "".join(rows)))
    if not parsed:
        parts.append('<div class="note">Матч ще не розібраний повністю: частина даних може бути відсутня.</div>')
    parts.append('<div class="note">Усі гравці, предмети та AI-оцінка: сторінка «Ігри та аналіз».</div>')
    return "".join(parts)


# ------------------------------------------------------------- сітка
def match_card(slot, stats=None):
    result = slot["result"]
    rows = []
    for side in ("a", "b"):
        name = slot[side]
        if name is None:
            css, text, score = "t tbd", slot[side + "_label"], ""
        else:
            css, text, score = "t", name, ""
            if result:
                score = result["score_" + side]
                css += " w" if result["winner"] == name else " l"
        rows.append('<div class="%s"><span>%s</span><b>%s</b></div>'
                    % (css, html.escape(text), score))
    head = ('<div class="hd"><span>%s</span><span>%s</span></div>'
            % (slot["key"], STATUS_TEXT[slot["status"]]))
    body = head + "".join(rows)
    if slot["status"] != "done":
        return '<div class="m %s">%s</div>' % (slot["status"], body)

    mid = result.get("dota_match_id")
    if not mid:
        detail = '<div class="note">Dota Match ID не вказано, статистики немає.</div>'
    elif stats and mid in stats:
        detail = stats[mid]
    else:
        detail = '<div class="note">Статистика недоступна.</div>'
    return ('<details class="m done"><summary>%s</summary><div class="stats">%s</div></details>'
            % (body, detail))


def section_html(section, size, slots, stats=None):
    cols = []
    for round_name, matches in T.LAYOUTS[size][section]:
        cards = "".join(match_card(slots[key], stats) for key, _, _ in matches)
        cols.append('<div class="br-col"><h5>%s</h5><div class="br-ms">%s</div></div>'
                    % (html.escape(round_name), cards))
    return ('<div class="sec %s"><h3>%s</h3></div>'
            '<div class="br-wrap"><div class="br-row">%s</div></div>'
            % (section, SECTION_TITLES[section], "".join(cols)))


def bracket_html(size, slots, stats=None):
    """Один рядок без переносів, щоб Markdown не ламав розмітку.

    stats: {dota_match_id (рядок): готовий html зі статистикою} або None.
    """
    return CSS.replace("\n", "") + "".join(
        section_html(s, size, slots, stats) for s in T.SECTIONS)
