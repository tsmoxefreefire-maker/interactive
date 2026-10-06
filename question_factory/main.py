"""The factory's single door: for EACH lesson in the graph -> for EACH concept -> generate questions -> validate -> save.

    python main.py <graph.json> <out_dir>
"""
import json
import os
import sys

import config
import llm_generator
import llm_polish
import llm_art
import offline_generator
import storage
import validator
from graph_reader import Graph


def build_lesson(g: Graph, lesson, llm_generate=None) -> dict:
    per_concept, skipped = offline_generator.generate(g, lesson)
    warnings, source = list(skipped), "offline"
    if llm_generate is not None:
        try:
            from_llm = llm_generator.generate(g, lesson, llm_generate)
            good = [q for q in from_llm if not validator.check(q, g, lesson.id)]
            if len(good) < len(from_llm):
                warnings.append(f"llm: {len(from_llm) - len(good)} invalid question(s) rejected")
            if good:
                source = "llm+offline"
                for cid in per_concept:                      # LLM questions first, offline fills the missing templates
                    mine = [q for q in good if q["target"] == cid]
                    have = {q["template"] for q in mine}
                    per_concept[cid] = mine + [q for q in per_concept[cid] if q["template"] not in have]
        except Exception as e:                               # broken reply -> offline only, never crash the batch
            warnings.append(f"llm failed, used offline: {e}")

    concepts_out, missing = [], []
    for c in lesson.concepts:
        valid = []
        for q in per_concept.get(c.id, []):
            problems = validator.check(q, g, lesson.id)
            (valid.append(q) if not problems else warnings.extend(problems))
        if len(valid) < config.MIN_QUESTIONS_PER_CONCEPT:      # coverage check, per concept
            missing.append(c.id)
            warnings.append(f"coverage: concept '{c.id}' has {len(valid)} question(s), needs {config.MIN_QUESTIONS_PER_CONCEPT}")
        rank = {"easy": 0, "mid": 1, "hard": 2}
        valid.sort(key=lambda q: rank.get(q["difficulty"], 1))          # easy -> hard (stable: keeps the variety order)
        concepts_out.append({"concept_id": c.id, "title": c.text, "difficulty": c.difficulty, "minutes": c.minutes,
                             "questions": valid})
    total = sum(len(c["questions"]) for c in concepts_out)
    n = len(concepts_out)
    return {"book_id": g.book.get("id", ""), "unit_id": lesson.unit_id, "topic_id": lesson.topic_id,
            "lesson_id": lesson.id, "lesson_title": lesson.title, "lesson_minutes": lesson.minutes,
            "generator": source, "status": config.DEFAULT_STATUS, "theme": offline_generator.choose_theme(g, lesson),
            "icons": {x: offline_generator.icon_for(g.concepts[x].text, g.concepts[x].description, str(g.book.get("subject", "")))
                      for x in g.concepts if offline_generator.is_entity(g, x)},
            "coverage": {"concepts": n, "ready": n - len(missing), "missing": missing,
                         "percent": round(100 * (n - len(missing)) / n) if n else 100,
                         "min_per_concept": config.MIN_QUESTIONS_PER_CONCEPT},
            "question_count": total, "concepts": concepts_out, "warnings": warnings}


ART_LIBRARY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "art_library.json")   # grows by itself


def run_factory(graph_path: str, out_dir: str, llm_generate=None, polish=None) -> list:
    """polish = the LLM as an editor (recommended): correct questions first, then kinder words."""
    g = Graph.load(graph_path)
    records = []
    for lesson in g.lessons():                                # "access a lesson at a time from the graph"
        record = build_lesson(g, lesson, llm_generate)        # every concept gets its own questions
        if polish is not None:
            record = llm_polish.polish_lesson(record, g, polish)
        records.append(record)
    library = llm_art.load_library(ART_LIBRARY)               # drawings made before for ANY book: reused, never drawn twice
    if polish is not None:                                    # the LLM draws what nobody has drawn yet, and the library grows
        llm_art.draw_missing(g, records, offline_generator.ART_ICONS, polish, library)
        llm_art.save_library(ART_LIBRARY, library)
    else:
        llm_art.use_library(g, records, offline_generator.ART_ICONS, library)
    for record in records:
        storage.save_lesson(out_dir, record)                  # "save given data for the lesson"
    storage.save_index(out_dir, records, graph_path)
    return records


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    use_llm = "--llm" in sys.argv
    graph, out = (args[0], args[1]) if len(args) == 2 else ("plants_book_graph.json", "output")
    polish = None
    if use_llm:
        import os
        import llm_gateway
        if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
            print("⚠️ ما في مفتاح: حط ANTHROPIC_API_KEY أول (الطريقة بملف HOW_TO_TRY_AR.md)، أو شغّل بدون --llm.")
            sys.exit(1)
        polish = llm_gateway.generate
        print("LLM: on (Claude rewrites the words for children; answers stay the same)")
    try:
        recs = run_factory(graph, out, polish=polish)
    except Exception as e:
        print("stopped:", e); sys.exit(1)
    print(f"{len(recs)} lessons, {sum(r['question_count'] for r in recs)} questions -> {out}/")
    for r in recs:
        llm = r.get("llm")
        extra = (f"  · LLM rewrote {llm.get('rewritten', 0)}/{llm.get('texts', 0)} texts" + (f", drew {llm['art']['drawn']}/{llm['art']['asked']} pictures" if llm.get('art') else "")) if llm else ""
        print(f"  {r['lesson_title']}  ({r['coverage']['ready']}/{r['coverage']['concepts']} concepts ready){extra}")
        for w in r["warnings"]:
            if w.startswith("llm"):
                print("     ⚠️", w)
        for c in r["concepts"]:
            print(f"     {c['title']:<16} {len(c['questions'])} questions: {', '.join(q['template'] for q in c['questions'])}")
