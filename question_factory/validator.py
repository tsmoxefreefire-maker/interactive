"""The code checks every generated question before it is saved (the LLM is never trusted blindly)."""
import config
from graph_reader import Graph
from templates import COMMON, SCHEMAS


def check(q: dict, g: Graph, lesson_id: str) -> list:
    """Returns a list of problems; empty means the question is valid."""
    errors = []
    t = q.get("template")
    if t not in config.TEMPLATES:
        return [f"unknown template: {t}"]
    allowed = {**COMMON, **SCHEMAS[t]}
    for key, typ in allowed.items():
        if key not in q:
            errors.append(f"{t}: missing field '{key}'")
        elif not isinstance(q[key], typ):
            errors.append(f"{t}: field '{key}' must be {typ.__name__}")
    extra = set(q) - set(allowed)
    if extra:
        errors.append(f"{t}: unexpected fields {sorted(extra)}")
    if errors:
        return errors
    if q["difficulty"] not in ("easy", "mid", "hard"):
        errors.append(f"{t}: bad difficulty")
    if not q["solution"]:
        errors.append(f"{t}: needs a step-by-step solution")

    unknown = lambda xs: [x for x in xs if x not in g.concepts]
    target = q["target"]
    if target not in g.concepts:
        return errors + [f"{t}: unknown target concept '{target}'"]
    if g.parent.get(target) != lesson_id:
        errors.append(f"{t}: the target concept is not in this lesson")
    if not q["concepts"] or q["concepts"][0] != target:
        errors.append(f"{t}: 'concepts' must start with the target concept")
    if unknown(q["concepts"]):
        errors.append(f"{t}: 'concepts' has unknown ids")

    if t == "meaning":
        if q["answer"] not in q["options"]: errors.append("meaning: the answer is missing from the options")
        if len(set(q["options"])) != len(q["options"]): errors.append("meaning: two options are the same")
        if len(q["options"]) < 3: errors.append("meaning: needs at least 3 options")
    elif t == "sequence":
        if unknown(q["order"]): errors.append("sequence: unknown concepts")
        if target not in q["order"]: errors.append("sequence: the target is not in the chain")
        if not all(g.is_prereq(a, b) for a, b in zip(q["order"], q["order"][1:])):
            errors.append("sequence: the order does not follow prerequisiteOf edges")
    elif t == "unlocks":
        route, junc = q["route"], q["junctions"]
        if unknown(route) or route[0] != target: errors.append("unlocks: the journey must start at the target")
        elif not all(g.is_prereq(a, b) for a, b in zip(route, route[1:])): errors.append("unlocks: the journey does not follow the graph")
        if len(route) < 2: errors.append("unlocks: the journey needs at least one step")
        if len(junc) != len(route) - 1 or len(q["hints"]) != len(junc) or len(q["whys"]) != len(junc): errors.append("unlocks: one crossroads (with hints and a why) per step")
        else:
            for i, opts in enumerate(junc):
                here, nxt = route[i], route[i + 1]
                if unknown(opts) or nxt not in opts: errors.append(f"unlocks: crossroads {i+1} misses the right road"); continue
                if len(set(opts)) != len(opts) or len(opts) < 3: errors.append(f"unlocks: crossroads {i+1} needs 3+ different roads")
                linked = g.descendants(here) | g.ancestors(here)
                if any(o in linked or g.is_prereq(here, o) for o in opts if o != nxt):
                    errors.append(f"unlocks: a wrong road at crossroads {i+1} is actually linked")
    elif t == "prereq":
        if unknown(q["options"]): errors.append(f"{t}: unknown concepts in options")
        if not set(q["correct"]) <= set(q["options"]): errors.append(f"{t}: a correct answer is missing from the options")
        if len(set(q["options"])) != len(q["options"]): errors.append(f"{t}: duplicate options")
        if any(not g.is_prereq(c, target) for c in q["correct"]): errors.append(f"{t}: a 'correct' option is not a real prerequisite")
        related = g.ancestors(target)
        if any(o in related for o in q["options"] if o not in q["correct"]):
            errors.append(f"{t}: a related (direct or indirect) concept is marked wrong")
    elif t == "match":
        ids = [p[0] for p in q["pairs"] if isinstance(p, list) and len(p) == 2]
        if len(ids) != len(q["pairs"]): errors.append("match: every pair must be [concept, meaning]")
        if unknown(ids): errors.append("match: unknown concepts")
        if target not in ids: errors.append("match: the target must be one of the pairs")
        if len(set(ids)) != len(ids) or len({p[1] for p in q["pairs"]}) != len(q["pairs"]): errors.append("match: duplicate concept or meaning")
        if len(q["pairs"]) < 3: errors.append("match: needs at least 3 pairs")
    elif t == "sort":
        if not q["before"] or not q["after"]: errors.append("sort: both baskets need concepts")
        if set(q["before"]) & set(q["after"]): errors.append("sort: a concept is in both baskets")
        if any(x not in g.ancestors(target) for x in q["before"]): errors.append("sort: a 'before' concept does not come before the target")
        if any(x not in g.descendants(target) for x in q["after"]): errors.append("sort: an 'after' concept does not come after the target")
    elif t == "adjust":
        f = q["factor"]
        need = ("label", "unit", "min", "max", "start", "ok_min", "ok_max")
        if any(k not in f for k in need):
            errors.append("adjust: the slider is missing a field")
        else:
            if not (f["min"] <= f["ok_min"] <= f["ok_max"] <= f["max"]): errors.append("adjust: the right range is outside the slider")
            if f["ok_min"] <= f["start"] <= f["ok_max"]: errors.append("adjust: the slider must not start on the answer")
            if g.concepts[target].quantity is None: errors.append("adjust: the graph has no numbers for this concept")
    elif t == "memory":
        ids = [p[0] for p in q["pairs"] if isinstance(p, list) and len(p) == 2]
        if len(ids) != len(q["pairs"]) or unknown(ids): errors.append("memory: bad pairs")
        if target not in ids: errors.append("memory: the target must be one of the pairs")
        if len(set(ids)) != len(ids) or len({p[1] for p in q["pairs"]}) != len(q["pairs"]): errors.append("memory: duplicate cards")
        if len(q["pairs"]) < 3: errors.append("memory: needs at least 3 pairs")
    elif t == "spell":
        if q["word"] != g.concepts[target].text: errors.append("spell: the word must be the concept's name")
        if not q["clue"]: errors.append("spell: needs a clue")
    elif t == "true_false":
        cards = q["statements"]
        if len(cards) < 3: errors.append("true_false: needs at least 3 cards")
        if any(not isinstance(x, dict) or not isinstance(x.get("answer"), bool) or not x.get("text") for x in cards):
            errors.append("true_false: every card needs text and a true/false answer")
        elif all(x["answer"] for x in cards) or not any(x["answer"] for x in cards):
            errors.append("true_false: needs both true and false cards")
    elif t == "fix_chain":
        chain = q["chain"]
        if unknown(chain + [q["wrong"]] + q["options"]): errors.append("fix_chain: unknown concepts")
        if not all(g.is_prereq(a, b) for a, b in zip(chain, chain[1:])): errors.append("fix_chain: the chain does not follow the graph")
        if not (0 <= q["wrong_index"] < len(chain)): errors.append("fix_chain: bad wrong_index")
        else:
            right = chain[q["wrong_index"]]
            if q["wrong"] in chain: errors.append("fix_chain: the wrong link must not belong to the chain")
            if right not in q["options"]: errors.append("fix_chain: the right link is missing from the options")
            if any(o in chain for o in q["options"] if o != right): errors.append("fix_chain: an option is already in the chain")
    elif t == "odd_one_out":
        if unknown(q["family"] + [q["intruder"]]): errors.append("odd_one_out: unknown concepts")
        if target not in q["family"]: errors.append("odd_one_out: the target must be in the family")
        if any(g.parent.get(x) != lesson_id for x in q["family"]): errors.append("odd_one_out: a family member is not from this lesson")
        if g.parent.get(q["intruder"]) == lesson_id: errors.append("odd_one_out: the intruder is from this lesson")
        if any(k not in q["family"] + [q["intruder"]] for k in q["intros"]): errors.append("odd_one_out: an intro for someone not in the game")
    elif t == "predict":
        if not (0 <= q["answer"] < len(q["options"])) or len(q["options"]) < 3: errors.append("predict: needs 3+ options and one answer")
        if unknown(q["affected"] + q["unaffected"]) or not q["affected"]: errors.append("predict: bad concepts")
        after = g.descendants(target)
        if any(x not in after for x in q["affected"]): errors.append("predict: an 'affected' concept does not need the target")
        if any(x in after for x in q["unaffected"]): errors.append("predict: an 'unaffected' concept actually needs the target")
    elif t == "who_am_i":
        if unknown(q["options"]): errors.append("who_am_i: unknown suspects")
        if target not in q["options"]: errors.append("who_am_i: the answer is not among the suspects")
        if len(set(q["options"])) != len(q["options"]) or len(q["options"]) < 3: errors.append("who_am_i: needs 3+ different suspects")
        if len(q["clues"]) < 2: errors.append("who_am_i: needs 2+ clues")
    return errors
