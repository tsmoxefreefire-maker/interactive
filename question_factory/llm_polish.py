"""The LLM as a careful EDITOR: it rewrites the WORDS for children, never the answers.

The factory builds correct questions first (offline). Then every piece of text a child reads
(questions, clues, meanings, true/false sentences, explanations…) is sent to the LLM to be rewritten:
simple Arabic, short, friendly — but the same facts. The code checks every rewritten text:
    - same keys back, non-empty, not much longer
    - every concept name in «…» kept, and no new «…» name invented
and checks every question again with the validator. Anything that fails keeps its original text.
"""
import json
import re

import validator

NAME = re.compile(r"«([^»]+)»")

SYSTEM = """You are a children's science editor. You rewrite short Arabic texts for {grade} school students.
Rules (follow ALL of them):
1. Keep exactly the same meaning and the same facts. A true sentence stays true, a false sentence stays false.
2. Never move a meaning from one concept to another. Never add a new fact.
3. Every name written inside «…» must stay exactly as it is, inside «…». Do not add new «…» names.
4. Simple, friendly Arabic (Modern Standard, easy words), short sentences, may use one fitting emoji.
5. Return ONLY one JSON object with exactly the same keys as the input, each value a string. No other text."""

# where a child-facing text lives in each kind of question
def _slots(q):
    t = q["template"]
    yield ("question",), q["question"]
    yield ("how",), q["how"]
    for i, s in enumerate(q.get("solution", [])):
        yield ("solution", i), s
    if t == "meaning":
        for i, o in enumerate(q["options"]):
            yield ("options", i), o
        yield ("answer",), q["answer"]
    if t == "predict":
        for i, o in enumerate(q["options"]):
            yield ("options", i), o
    if t in ("match", "memory"):
        for i, p in enumerate(q["pairs"]):
            yield ("pairs", i, 1), p[1]
    if t == "spell":
        yield ("clue",), q["clue"]
    if t == "true_false":
        for i, s in enumerate(q["statements"]):
            yield ("statements", i, "text"), s["text"]
    if t == "who_am_i":
        for i, c in enumerate(q["clues"]):
            yield ("clues", i), c
    if t == "odd_one_out":
        for k, v in q["intros"].items():
            yield ("intros", k), v
    if t == "unlocks":
        for i, w in enumerate(q["whys"]):
            yield ("whys", i), w
        for i, hs in enumerate(q["hints"]):
            for j, h in enumerate(hs):
                yield ("hints", i, j), h
    if t == "adjust":
        for k in ("low", "high"):
            if q["factor"].get(k):
                yield ("factor", k), q["factor"][k]


def _set(q, path, value):
    obj = q
    for p in path[:-1]:
        obj = obj[p]
    obj[path[-1]] = value


def acceptable(old: str, new) -> bool:
    if not isinstance(new, str) or not new.strip():
        return False
    if len(new) > len(old) * 2 + 40:
        return False
    old_names, new_names = set(NAME.findall(old)), set(NAME.findall(new))
    return old_names <= new_names and new_names <= old_names


def polish_lesson(record: dict, g, llm_generate, grade: str = "primary") -> dict:
    """Rewrite the lesson's texts with the LLM; keep originals wherever a check fails."""
    texts = {}                      # one key per DIFFERENT text, so equal texts stay equal (an answer stays inside its options)
    for c in record["concepts"]:
        for q in c["questions"]:
            for _, text in _slots(q):
                if text not in texts.values():
                    texts[f"t{len(texts) + 1}"] = text
    if not texts:
        return record
    try:
        reply = llm_generate(SYSTEM.replace("{grade}", grade), json.dumps(texts, ensure_ascii=False))
        start, end = reply.find("{"), reply.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("the answer has no JSON object")
        new = json.loads(reply[start:end + 1])
        if not isinstance(new, dict):
            raise ValueError("not a JSON object")
    except Exception as e:                                   # broken answer -> keep everything as it was
        record["warnings"].append(f"llm polish failed, kept the original texts: {e}")
        return record
    rewrite, rejected = {}, 0
    for k, old in texts.items():
        if acceptable(old, new.get(k)):
            rewrite[old] = new[k].strip()
        else:
            rejected += 1
    changed = 0
    for c in record["concepts"]:
        for i, q in enumerate(c["questions"]):
            before = json.loads(json.dumps(q))
            for path, text in list(_slots(q)):
                if text in rewrite:
                    _set(q, path, rewrite[text])
            if validator.check(q, g, record["lesson_id"]):   # the rewritten question must still be valid
                c["questions"][i] = before
                rejected += 1
            elif q != before:
                changed += 1
    record["generator"] = "offline+llm-polish"
    record["llm"] = {"texts": len(texts), "rewritten": len(rewrite), "rejected": rejected, "questions_changed": changed}
    if rejected:
        record["warnings"].append(f"llm polish: {rejected} text(s)/question(s) kept original (failed a check)")
    return record
