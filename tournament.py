"""Логіка Double Elimination для 4, 8, 12, 14 або 16 команд. Без UI та бази даних.

Сітка описана даними: кожен матч бере команди зі "слотів":
  ("seed", n)   - команда з номером n
  ("win", key)  - переможець матчу key
  ("lose", key) - той, хто програв у матчі key
Команда потрапляє в наступний матч ТІЛЬКИ якщо результат попереднього
збережений (підтверджений). Автоматичного просування немає.

Для 12 і 14 команд перші в списку отримують "bye": 4 команди при 12 і
2 команди при 14 одразу потрапляють у другий раунд верхньої сітки.

Формат: один Grand Final (без "скидання" сітки).
"""

LAYOUTS = {
    4: {
        "WB": [
            ("Раунд 1", [("W1", ("seed", 1), ("seed", 2)),
                         ("W2", ("seed", 3), ("seed", 4))]),
            ("Фінал WB", [("W3", ("win", "W1"), ("win", "W2"))]),
        ],
        "LB": [
            ("Раунд 1", [("L1", ("lose", "W1"), ("lose", "W2"))]),
            ("Фінал LB", [("L2", ("win", "L1"), ("lose", "W3"))]),
        ],
        "GF": [("Grand Final", [("GF", ("win", "W3"), ("win", "L2"))])],
    },
    8: {
        "WB": [
            ("Раунд 1", [("W1", ("seed", 1), ("seed", 2)),
                         ("W2", ("seed", 3), ("seed", 4)),
                         ("W3", ("seed", 5), ("seed", 6)),
                         ("W4", ("seed", 7), ("seed", 8))]),
            ("Півфінали WB", [("W5", ("win", "W1"), ("win", "W2")),
                              ("W6", ("win", "W3"), ("win", "W4"))]),
            ("Фінал WB", [("W7", ("win", "W5"), ("win", "W6"))]),
        ],
        "LB": [
            ("Раунд 1", [("L1", ("lose", "W1"), ("lose", "W2")),
                         ("L2", ("lose", "W3"), ("lose", "W4"))]),
            ("Раунд 2", [("L3", ("win", "L1"), ("lose", "W6")),
                         ("L4", ("win", "L2"), ("lose", "W5"))]),
            ("Раунд 3", [("L5", ("win", "L3"), ("win", "L4"))]),
            ("Фінал LB", [("L6", ("win", "L5"), ("lose", "W7"))]),
        ],
        "GF": [("Grand Final", [("GF", ("win", "W7"), ("win", "L6"))])],
    },
    # 12 команд: команди №1-4 мають bye у "Чвертьфінали WB"
    12: {
        "WB": [
            ("Раунд 1", [("W1", ("seed", 5), ("seed", 6)),
                         ("W2", ("seed", 7), ("seed", 8)),
                         ("W3", ("seed", 9), ("seed", 10)),
                         ("W4", ("seed", 11), ("seed", 12))]),
            ("Чвертьфінали WB", [("W5", ("seed", 1), ("win", "W1")),
                                 ("W6", ("seed", 2), ("win", "W2")),
                                 ("W7", ("seed", 3), ("win", "W3")),
                                 ("W8", ("seed", 4), ("win", "W4"))]),
            ("Півфінали WB", [("W9", ("win", "W5"), ("win", "W6")),
                              ("W10", ("win", "W7"), ("win", "W8"))]),
            ("Фінал WB", [("W11", ("win", "W9"), ("win", "W10"))]),
        ],
        "LB": [
            ("Раунд 1", [("L1", ("lose", "W1"), ("lose", "W7")),
                         ("L2", ("lose", "W2"), ("lose", "W8")),
                         ("L3", ("lose", "W3"), ("lose", "W5")),
                         ("L4", ("lose", "W4"), ("lose", "W6"))]),
            ("Раунд 2", [("L5", ("win", "L1"), ("win", "L2")),
                         ("L6", ("win", "L3"), ("win", "L4"))]),
            ("Раунд 3", [("L7", ("win", "L5"), ("lose", "W10")),
                         ("L8", ("win", "L6"), ("lose", "W9"))]),
            ("Раунд 4", [("L9", ("win", "L7"), ("win", "L8"))]),
            ("Фінал LB", [("L10", ("win", "L9"), ("lose", "W11"))]),
        ],
        "GF": [("Grand Final", [("GF", ("win", "W11"), ("win", "L10"))])],
    },
    # 14 команд: команди №1-2 мають bye у "Чвертьфінали WB"
    14: {
        "WB": [
            ("Раунд 1", [("W1", ("seed", 3), ("seed", 4)),
                         ("W2", ("seed", 5), ("seed", 6)),
                         ("W3", ("seed", 7), ("seed", 8)),
                         ("W4", ("seed", 9), ("seed", 10)),
                         ("W5", ("seed", 11), ("seed", 12)),
                         ("W6", ("seed", 13), ("seed", 14))]),
            ("Чвертьфінали WB", [("W7", ("seed", 1), ("win", "W1")),
                                 ("W8", ("win", "W2"), ("win", "W3")),
                                 ("W9", ("win", "W4"), ("win", "W5")),
                                 ("W10", ("win", "W6"), ("seed", 2))]),
            ("Півфінали WB", [("W11", ("win", "W7"), ("win", "W8")),
                              ("W12", ("win", "W9"), ("win", "W10"))]),
            ("Фінал WB", [("W13", ("win", "W11"), ("win", "W12"))]),
        ],
        "LB": [
            ("Раунд 1", [("L1", ("lose", "W1"), ("lose", "W2")),
                         ("L2", ("lose", "W5"), ("lose", "W6"))]),
            ("Раунд 2", [("L3", ("win", "L1"), ("lose", "W10")),
                         ("L4", ("lose", "W3"), ("lose", "W9")),
                         ("L5", ("lose", "W4"), ("lose", "W8")),
                         ("L6", ("win", "L2"), ("lose", "W7"))]),
            ("Раунд 3", [("L7", ("win", "L3"), ("win", "L4")),
                         ("L8", ("win", "L5"), ("win", "L6"))]),
            ("Раунд 4", [("L9", ("win", "L7"), ("lose", "W12")),
                         ("L10", ("win", "L8"), ("lose", "W11"))]),
            ("Раунд 5", [("L11", ("win", "L9"), ("win", "L10"))]),
            ("Фінал LB", [("L12", ("win", "L11"), ("lose", "W13"))]),
        ],
        "GF": [("Grand Final", [("GF", ("win", "W13"), ("win", "L12"))])],
    },
    16: {
        "WB": [
            ("Раунд 1", [("W1", ("seed", 1), ("seed", 2)),
                         ("W2", ("seed", 3), ("seed", 4)),
                         ("W3", ("seed", 5), ("seed", 6)),
                         ("W4", ("seed", 7), ("seed", 8)),
                         ("W5", ("seed", 9), ("seed", 10)),
                         ("W6", ("seed", 11), ("seed", 12)),
                         ("W7", ("seed", 13), ("seed", 14)),
                         ("W8", ("seed", 15), ("seed", 16))]),
            ("Чвертьфінали WB", [("W9", ("win", "W1"), ("win", "W2")),
                                 ("W10", ("win", "W3"), ("win", "W4")),
                                 ("W11", ("win", "W5"), ("win", "W6")),
                                 ("W12", ("win", "W7"), ("win", "W8"))]),
            ("Півфінали WB", [("W13", ("win", "W9"), ("win", "W10")),
                              ("W14", ("win", "W11"), ("win", "W12"))]),
            ("Фінал WB", [("W15", ("win", "W13"), ("win", "W14"))]),
        ],
        "LB": [
            ("Раунд 1", [("L1", ("lose", "W1"), ("lose", "W2")),
                         ("L2", ("lose", "W3"), ("lose", "W4")),
                         ("L3", ("lose", "W5"), ("lose", "W6")),
                         ("L4", ("lose", "W7"), ("lose", "W8"))]),
            ("Раунд 2", [("L5", ("win", "L1"), ("lose", "W12")),
                         ("L6", ("win", "L2"), ("lose", "W11")),
                         ("L7", ("win", "L3"), ("lose", "W10")),
                         ("L8", ("win", "L4"), ("lose", "W9"))]),
            ("Раунд 3", [("L9", ("win", "L5"), ("win", "L6")),
                         ("L10", ("win", "L7"), ("win", "L8"))]),
            ("Раунд 4", [("L11", ("win", "L9"), ("lose", "W14")),
                         ("L12", ("win", "L10"), ("lose", "W13"))]),
            ("Раунд 5", [("L13", ("win", "L11"), ("win", "L12"))]),
            ("Фінал LB", [("L14", ("win", "L13"), ("lose", "W15"))]),
        ],
        "GF": [("Grand Final", [("GF", ("win", "W15"), ("win", "L14"))])],
    },
}

SECTIONS = ("WB", "LB", "GF")
VALID_SIZES = tuple(sorted(LAYOUTS))
VALID_BO = (1, 3, 5)


def sizes_text():
    """'4, 8, 12, 14 або 16' - для повідомлень користувачу."""
    return ", ".join(str(n) for n in VALID_SIZES[:-1]) + " або " + str(VALID_SIZES[-1])


def flat_matches(size):
    """Усі матчі у порядку залежностей: WB, потім LB, потім GF."""
    out = []
    for sec in SECTIONS:
        for _, matches in LAYOUTS[size][sec]:
            out.extend(matches)
    return out


def section_of(key):
    return {"W": "WB", "L": "LB", "G": "GF"}[key[0]]


def slot_label(src):
    kind, ref = src
    if kind == "seed":
        return "Команда №%d" % ref
    if kind == "win":
        return "Переможець %s" % ref
    return "Програвший %s" % ref


def resolve(size, teams, results):
    """Повертає {key: {a, b, result, status, a_label, b_label, key}}.

    results: {key: {"score_a", "score_b", "winner", ...}} - лише підтверджені.
    status: waiting (немає обох команд) / ready / done.
    """
    slots = {}

    def team_from(src):
        kind, ref = src
        if kind == "seed":
            return teams[ref - 1] if ref - 1 < len(teams) else None
        r = results.get(ref)
        if r is None:
            return None
        s = slots[ref]
        if kind == "win":
            return r["winner"]
        return s["b"] if r["winner"] == s["a"] else s["a"]

    for key, a_src, b_src in flat_matches(size):
        a, b = team_from(a_src), team_from(b_src)
        r = results.get(key)
        status = "done" if r else ("ready" if a and b else "waiting")
        slots[key] = {"key": key, "a": a, "b": b, "result": r, "status": status,
                      "a_label": slot_label(a_src), "b_label": slot_label(b_src)}
    return slots


def validate_result(bo, score_a, score_b):
    """None, якщо рахунок допустимий для формату BO, інакше текст помилки."""
    need = bo // 2 + 1
    if score_a < 0 or score_b < 0:
        return "Рахунок не може бути від'ємним."
    if max(score_a, score_b) != need:
        return "У форматі BO%d переможець має мати рівно %d перемог(и)." % (bo, need)
    if min(score_a, score_b) >= need:
        return "Обидві команди не можуть мати по %d перемог(и)." % need
    return None


def winner_from_score(team_a, team_b, score_a, score_b):
    return team_a if score_a > score_b else team_b


def can_edit(size, results, key):
    """Результат можна скасувати, лише якщо від нього ще не залежить жоден підтверджений матч."""
    for k, a_src, b_src in flat_matches(size):
        if results.get(k) is not None and key in (a_src[1], b_src[1]):
            return False
    return True


def standings(teams, slots):
    """Статистика та статус кожної команди (рахується з результатів, не зберігається)."""
    rec = {t: {"W": 0, "L": 0, "MW": 0, "ML": 0, "lost_in": []} for t in teams}
    for s in slots.values():
        r = s["result"]
        if not r or s["a"] not in rec or s["b"] not in rec:
            continue
        a, b = s["a"], s["b"]
        loser = b if r["winner"] == a else a
        rec[r["winner"]]["W"] += 1
        rec[loser]["L"] += 1
        rec[a]["MW"] += r["score_a"]
        rec[a]["ML"] += r["score_b"]
        rec[b]["MW"] += r["score_b"]
        rec[b]["ML"] += r["score_a"]
        rec[loser]["lost_in"].append(section_of(s["key"]))
    gf = slots["GF"]["result"]
    for t, v in rec.items():
        if gf and gf["winner"] == t:
            v["status"] = "Чемпіон"
        elif "LB" in v["lost_in"] or "GF" in v["lost_in"]:
            v["status"] = "Вибув"
        elif "WB" in v["lost_in"]:
            v["status"] = "Нижня сітка"
        else:
            v["status"] = "Верхня сітка"
    return rec


def champion(slots):
    gf = slots["GF"]["result"]
    return gf["winner"] if gf else None
