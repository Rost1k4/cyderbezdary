"""Малює турнірну сітку як HTML. Не залежить від Streamlit."""
import html

import tournament as T

CSS = """<style>
.br-wrap{overflow-x:auto;padding:4px 2px 14px}
.br-row{display:flex;gap:26px;align-items:stretch;min-width:max-content}
.br-col{display:flex;flex-direction:column;min-width:215px}
.br-col h5{margin:0 0 6px;font-size:.85rem;font-weight:600;color:#9A93D1}
.br-ms{display:flex;flex-direction:column;justify-content:space-around;gap:14px;flex:1}
.m{border:1px solid #3A3180;border-radius:8px;overflow:hidden;background:#1C1745;color:#ECE9FF}
.m.ready{border-color:#FF9F43;box-shadow:0 0 0 1px #FF9F43}
.m.done{border-color:#35D6A0}
.m .hd{display:flex;justify-content:space-between;font-size:.72rem;padding:3px 8px;background:#241E5A;color:#9A93D1}
.m .t{display:flex;justify-content:space-between;gap:10px;padding:6px 8px;font-size:.9rem}
.m .t.tbd{color:#9A93D1;font-style:italic}
.m .t.w{background:rgba(53,214,160,.18);color:#35D6A0;font-weight:700}
.m .t.l{opacity:.5}
.sec{border-left:5px solid;padding-left:10px;margin:22px 0 8px}
.sec h3{margin:0;padding:0}
.sec.WB{border-color:#4F8CFF}.sec.WB h3{color:#4F8CFF}
.sec.LB{border-color:#C45CFF}.sec.LB h3{color:#C45CFF}
.sec.GF{border-color:#FFD166}.sec.GF h3{color:#FFD166}
</style>"""

STATUS_TEXT = {"waiting": "Очікує", "ready": "Готовий до гри", "done": "Завершено"}
SECTION_TITLES = {"WB": "Верхня сітка (Winners Bracket)",
                  "LB": "Нижня сітка (Losers Bracket)",
                  "GF": "Grand Final"}


def match_card(slot):
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
    return ('<div class="m %s"><div class="hd"><span>%s</span><span>%s</span></div>%s</div>'
            % (slot["status"], slot["key"], STATUS_TEXT[slot["status"]], "".join(rows)))


def section_html(section, size, slots):
    cols = []
    for round_name, matches in T.LAYOUTS[size][section]:
        cards = "".join(match_card(slots[key]) for key, _, _ in matches)
        cols.append('<div class="br-col"><h5>%s</h5><div class="br-ms">%s</div></div>'
                    % (html.escape(round_name), cards))
    return ('<div class="sec %s"><h3>%s</h3></div>'
            '<div class="br-wrap"><div class="br-row">%s</div></div>'
            % (section, SECTION_TITLES[section], "".join(cols)))


def bracket_html(size, slots):
    """Один рядок без переносів, щоб Markdown не ламав розмітку."""
    return CSS.replace("\n", "") + "".join(section_html(s, size, slots) for s in T.SECTIONS)
