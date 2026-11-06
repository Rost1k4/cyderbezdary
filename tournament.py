"""Single Elimination з матчем за 3-тє місце. Без UI та бази даних.

Сітка описана даними: кожен матч бере команди зі "слотів":
  ("seed", n)   - команда з номером n
  ("win", key)  - переможець матчу key
  ("lose", key) - команда, що програла матч key
Команда потрапляє в наступний матч лише після підтвердження результату.
Команди, що програли півфінали, грають за 3-тє місце.

Коли кількість команд не є степенем двійки, перші в списку отримують bye:
5 → 3, 6 → 2, 7 → 1, 9 → 7, 12 → 4, 14 → 2 команди пропускають перший раунд.

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
    5: {
        "WB": [
            ("Попередній раунд", [("W1", ("seed", 4), ("seed", 5))]),
            ("Півфінали", [("W2", ("seed", 1), ("win", "W1")),
                           ("W3", ("seed", 2), ("seed", 3))]),
            ("Фінал", [("W4", ("win", "W2"), ("win", "W3"))]),
        ],
    },
    6: {
        "WB": [
            ("Попередній раунд", [("W1", ("seed", 3), ("seed", 4)),
                                  ("W2", ("seed", 5), ("seed", 6))]),
            ("Півфінали", [("W3", ("seed", 1), ("win", "W1")),
                           ("W4", ("win", "W2"), ("seed", 2))]),
            ("Фінал", [("W5", ("win", "W3"), ("win", "W4"))]),
        ],
    },
    7: {
        "WB": [
            ("Попередній раунд", [("W1", ("seed", 2), ("seed", 3)),
                                  ("W2", ("seed", 4), ("seed", 5)),
                                  ("W3", ("seed", 6), ("seed", 7))]),
            ("Півфінали", [("W4", ("seed", 1), ("win", "W1")),
                           ("W5", ("win", "W2"), ("win", "W3"))]),
            ("Фінал", [("W6", ("win", "W4"), ("win", "W5"))]),
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
    9: {
        "WB": [
            ("Попередній раунд", [("W1", ("seed", 8), ("seed", 9))]),
            ("Чвертьфінали", [("W2", ("seed", 1), ("win", "W1")),
                              ("W3", ("seed", 2), ("seed", 3)),
                              ("W4", ("seed", 4), ("seed", 5)),
                              ("W5", ("seed", 6), ("seed", 7))]),
            ("Півфінали", [("W6", ("win", "W2"), ("win", "W3")),
                           ("W7", ("win", "W4"), ("win", "W5"))]),
            ("Фінал", [("W8", ("win", "W6"), ("win", "W7"))]),
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

THIRD_PLACE_KEY = "P3"
for _layout in LAYOUTS.values():
    _, _semi_a, _semi_b = _layout["WB"][-1][1][0]
    _layout["P3"] = [("Бронзовий матч", [
        (THIRD_PLACE_KEY, ("lose", _semi_a[1]), ("lose", _semi_b[1])),
    ])]

SECTIONS = ("WB", "P3")
VALID_SIZES = tuple(sorted(LAYOUTS))
VALID_BO = (1, 3, 5)


def sizes_text():
    """Підтримувані розміри сітки для повідомлень користувачу."""
    return ", ".join(str(n) for n in VALID_SIZES[:-1]) + " або " + str(VALID_SIZES[-1])


def flat_matches(size):
    """Усі матчі у порядку залежностей (останній - Фінал)."""
    out = []
    for sec in SECTIONS:
        for _, matches in LAYOUTS[size][sec]:
            out.extend(matches)
    # Матч за бронзу не змінює стару домовленість: останній слот — Фінал.
    final = final_key(size)
    return [m for m in out if m[0] != final] + [m for m in out if m[0] == final]


def final_key(size):
    return LAYOUTS[size]["WB"][-1][1][0][0]


def section_of(key):
    return "P3" if key == THIRD_PLACE_KEY else "WB"


def match_label(key):
    return "%s · За 3-тє місце" % key if key == THIRD_PLACE_KEY else key


def bye_count(size):
    """Скільки перших команд пропускають початковий раунд."""
    return (1 << (size - 1).bit_length()) - size


def slot_label(src):
    kind, ref = src
    if kind == "seed":
        return "Команда №%d" % ref
    if kind == "lose":
        return "Команда, що програла %s" % ref
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
        previous = slots.get(ref)
        if not previous or not previous["result"]:
            return None
        if kind == "lose":
            return loser(previous)
        return previous["result"]["winner"]

    for key, a_src, b_src in flat_matches(size):
        a, b = team_from(a_src), team_from(b_src)
        r = results.get(key)
        if not a or not b or (r and r.get("winner") not in (a, b)):
            r = None
        status = "done" if r else ("ready" if a and b else "waiting")
        slots[key] = {"key": key, "a": a, "b": b, "result": r, "status": status,
                      "a_label": slot_label(a_src), "b_label": slot_label(b_src)}
    return slots


def final_slot(slots):
    """Слот Фіналу (останній матч сітки)."""
    return list(slots.values())[-1]


def loser(slot):
    """Команда, що програла за підтвердженим winner, а не за кількістю вбивств."""
    if not slot or not slot["result"]:
        return None
    winner = slot["result"]["winner"]
    if winner not in (slot["a"], slot["b"]):
        return None
    return slot["b"] if winner == slot["a"] else slot["a"]


def placements(slots):
    """Визначені місця 1–4; фінал і бронза можуть бути зіграні в будь-якому порядку."""
    places = {}
    if not slots:
        return places
    for slot, first in ((final_slot(slots), 1), (slots.get(THIRD_PLACE_KEY), 3)):
        if slot and slot["result"]:
            places[slot["result"]["winner"]] = first
            places[loser(slot)] = first + 1
    return places


def is_complete(slots):
    return bool(slots) and all(s["status"] == "done" for s in slots.values())


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
        if results.get(k) is not None and any(
                kind in ("win", "lose") and ref == key for kind, ref in (a_src, b_src)):
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
        lost = loser(s)
        rec[r["winner"]]["W"] += 1
        rec[lost]["L"] += 1
        rec[a]["MW"] += r["score_a"]
        rec[a]["ML"] += r["score_b"]
        rec[b]["MW"] += r["score_b"]
        rec[b]["ML"] += r["score_a"]
    places = placements(slots)
    place_status = {1: "Чемпіон", 2: "2-ге місце", 3: "3-тє місце", 4: "4-те місце"}
    bronze = slots.get(THIRD_PLACE_KEY)
    bronze_teams = {bronze["a"], bronze["b"]} if bronze and not bronze["result"] else set()
    for t, v in rec.items():
        v["place"] = places.get(t)
        if v["place"] is not None:
            v["status"] = place_status[v["place"]]
        elif t in bronze_teams:
            v["status"] = "Грає за 3-тє місце"
        elif v["L"]:
            v["status"] = "Вибув"
        else:
            v["status"] = "У грі"
    return rec


def champion(slots):
    if not slots:
        return None
    r = final_slot(slots)["result"]
    return r["winner"] if r else None
