"""Логіка Single Elimination (плей-оф) для 4, 8, 12, 14 або 16 команд. Без UI та бази даних.

Сітка описана даними: кожен матч бере команди зі "слотів":
  ("seed", n)   - команда з номером n
  ("win", key)  - переможець матчу key
Програвший вибуває з турніру. Команда потрапляє в наступний матч ТІЛЬКИ якщо
результат попереднього збережений (підтверджений). Автоматичного просування немає.

Для 12 і 14 команд перші в списку отримують "bye": 4 команди при 12 і
2 команди при 14 одразу потрапляють у другий раунд.

Останній матч сітки - Фінал; його переможець - чемпіон.
Ключі матчів (W1, W2, ...) збережені як раніше, щоб не втратити вже внесені результати.
"""

LAYOUTS = {
    4: {
        "WB": [
            ("Півфінали", [("W1", ("seed", 1), ("seed", 2)),
                           ("W2", ("seed", 3), ("seed", 4))]),
            ("Фінал", [("W3", ("win", "W1"), ("win", "W2"))]),
        ],
    },
    8: {
        "WB": [
            ("Чвертьфінали", [("W1", ("seed", 1), ("seed", 2)),
                              ("W2", ("seed", 3), ("seed", 4)),
                              ("W3", ("seed", 5), ("seed", 6)),
                              ("W4", ("seed", 7), ("seed", 8))]),
            ("Півфінали", [("W5", ("win", "W1"), ("win", "W2")),
                           ("W6", ("win", "W3"), ("win", "W4"))]),
            ("Фінал", [("W7", ("win", "W5"), ("win", "W6"))]),
        ],
    },
    # 12 команд: команди №1-4 мають bye у "Чвертьфінали"
    12: {
        "WB": [
            ("Раунд 1", [("W1", ("seed", 5), ("seed", 6)),
                         ("W2", ("seed", 7), ("seed", 8)),
                         ("W3", ("seed", 9), ("seed", 10)),
                         ("W4", ("seed", 11), ("seed", 12))]),
            ("Чвертьфінали", [("W5", ("seed", 1), ("win", "W1")),
                              ("W6", ("seed", 2), ("win", "W2")),
                              ("W7", ("seed", 3), ("win", "W3")),
                              ("W8", ("seed", 4), ("win", "W4"))]),
            ("Півфінали", [("W9", ("win", "W5"), ("win", "W6")),
                           ("W10", ("win", "W7"), ("win", "W8"))]),
            ("Фінал", [("W11", ("win", "W9"), ("win", "W10"))]),
        ],
    },
    # 14 команд: команди №1-2 мають bye у "Чвертьфінали"
    14: {
        "WB": [
            ("Раунд 1", [("W1", ("seed", 3), ("seed", 4)),
                         ("W2", ("seed", 5), ("seed", 6)),
                         ("W3", ("seed", 7), ("seed", 8)),
                         ("W4", ("seed", 9), ("seed", 10)),
                         ("W5", ("seed", 11), ("seed", 12)),
                         ("W6", ("seed", 13), ("seed", 14))]),
            ("Чвертьфінали", [("W7", ("seed", 1), ("win", "W1")),
                              ("W8", ("win", "W2"), ("win", "W3")),
                              ("W9", ("win", "W4"), ("win", "W5")),
                              ("W10", ("win", "W6"), ("seed", 2))]),
            ("Півфінали", [("W11", ("win", "W7"), ("win", "W8")),
                           ("W12", ("win", "W9"), ("win", "W10"))]),
            ("Фінал", [("W13", ("win", "W11"), ("win", "W12"))]),
        ],
    },
    16: {
        "WB": [
            ("1/8 фіналу", [("W1", ("seed", 1), ("seed", 2)),
                            ("W2", ("seed", 3), ("seed", 4)),
                            ("W3", ("seed", 5), ("seed", 6)),
                            ("W4", ("seed", 7), ("seed", 8)),
                            ("W5", ("seed", 9), ("seed", 10)),
                            ("W6", ("seed", 11), ("seed", 12)),
                            ("W7", ("seed", 13), ("seed", 14)),
                            ("W8", ("seed", 15), ("seed", 16))]),
            ("Чвертьфінали", [("W9", ("win", "W1"), ("win", "W2")),
                              ("W10", ("win", "W3"), ("win", "W4")),
                              ("W11", ("win", "W5"), ("win", "W6")),
                              ("W12", ("win", "W7"), ("win", "W8"))]),
            ("Півфінали", [("W13", ("win", "W9"), ("win", "W10")),
                           ("W14", ("win", "W11"), ("win", "W12"))]),
            ("Фінал", [("W15", ("win", "W13"), ("win", "W14"))]),
        ],
    },
}

SECTIONS = ("WB",)
VALID_SIZES = tuple(sorted(LAYOUTS))
VALID_BO = (1, 3, 5)


def sizes_text():
    """'4, 8, 12, 14 або 16' - для повідомлень користувачу."""
    return ", ".join(str(n) for n in VALID_SIZES[:-1]) + " або " + str(VALID_SIZES[-1])


def flat_matches(size):
    """Усі матчі у порядку залежностей (останній - Фінал)."""
    out = []
    for sec in SECTIONS:
        for _, matches in LAYOUTS[size][sec]:
            out.extend(matches)
    return out


def final_key(size):
    return flat_matches(size)[-1][0]


def section_of(key):
    return "WB"


def slot_label(src):
    kind, ref = src
    if kind == "seed":
        return "Команда №%d" % ref
    return "Переможець %s" % ref


def resolve(size, teams, results):
    """Повертає {key: {a, b, result, status, a_label, b_label, key}}.

    results: {key: {"score_a", "score_b", "winner", ...}} - лише підтверджені.
    status: waiting (немає обох команд) / ready / done.
    Останній елемент словника - Фінал.
    """
    slots = {}

    def team_from(src):
        kind, ref = src
        if kind == "seed":
            return teams[ref - 1] if ref - 1 < len(teams) else None
        r = results.get(ref)
        return r["winner"] if r is not None else None

    for key, a_src, b_src in flat_matches(size):
        a, b = team_from(a_src), team_from(b_src)
        r = results.get(key)
        status = "done" if r else ("ready" if a and b else "waiting")
        slots[key] = {"key": key, "a": a, "b": b, "result": r, "status": status,
                      "a_label": slot_label(a_src), "b_label": slot_label(b_src)}
    return slots


def final_slot(slots):
    """Слот Фіналу (останній матч сітки)."""
    return list(slots.values())[-1]


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
    rec = {t: {"W": 0, "L": 0, "MW": 0, "ML": 0} for t in teams}
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
    champ = champion(slots)
    for t, v in rec.items():
        if champ == t:
            v["status"] = "Чемпіон"
        elif v["L"]:
            v["status"] = "Вибув"
        else:
            v["status"] = "У грі"
    return rec


def champion(slots):
    r = final_slot(slots)["result"]
    return r["winner"] if r else None
