import json
import os
import shutil
import tempfile
import unittest

import config
import llm_generator
import offline_generator
import validator
from graph_reader import Graph
from main import build_lesson, run_factory

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW = os.path.join(HERE, "plants_book_graph.json")              # new structure (Book > Unit > Topic > Lesson > Entity)
OLD = os.path.join(HERE, "tests", "old_format_graph.json")     # old flat structure, kept for compatibility


def lessons(g):
    return {l.id: l for l in g.lessons()}


class TestReadsNewStructure(unittest.TestCase):
    def setUp(self):
        self.g = Graph.load(NEW)

    def test_detects_new_format(self):
        self.assertEqual((self.g.format, self.g.book["id"]), ("new", "sci_g4"))

    def test_finds_the_three_lessons(self):
        self.assertEqual(sorted(lessons(self.g)), ["l_cycle", "l_needs", "l_parts"])

    def test_lesson_has_its_concepts_topic_and_unit(self):
        parts = lessons(self.g)["l_parts"]
        self.assertEqual(len(parts.concepts), 6)
        self.assertEqual((parts.topic_id, parts.unit_id), ("t_structure", "u_plants"))

    def test_lesson_minutes_are_the_sum_of_its_concepts(self):          # engineer's decision
        self.assertEqual({k: l.minutes for k, l in lessons(self.g).items()}, {"l_parts": 23, "l_needs": 12, "l_cycle": 15})

    def test_meanings_come_from_node_content(self):
        self.assertIn("يمتص", self.g.concepts["root"].description)

    def test_the_plants_book_has_no_invented_numbers(self):
        self.assertTrue(all(c.quantity is None for c in self.g.concepts.values()))

    def test_indirect_links(self):
        self.assertTrue({"water", "soil", "root", "stem"} <= self.g.ancestors("leaf"))
        self.assertTrue({"stem", "leaf"} <= self.g.descendants("root"))


class TestEveryConceptHasQuestions(unittest.TestCase):
    """Omar's decision: every concept has its own questions."""
    def setUp(self):
        self.g = Graph.load(NEW)

    def test_every_concept_has_enough_questions(self):
        for lesson in self.g.lessons():
            rec = build_lesson(self.g, lesson)
            for c in rec["concepts"]:
                self.assertGreaterEqual(len(c["questions"]), config.MIN_QUESTIONS_PER_CONCEPT, c["concept_id"])
            self.assertEqual(rec["coverage"]["percent"], 100)

    def test_questions_belong_to_their_concept(self):
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                for q in c["questions"]:
                    self.assertEqual(q["target"], c["concept_id"])
                    self.assertEqual(q["concepts"][0], c["concept_id"])

    def test_every_concept_has_a_meaning_question(self):          # bubbles or connect-lines
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                self.assertTrue(set(config.MEANING_KINDS) & {q["template"] for q in c["questions"]})

    def test_at_most_max_questions_per_concept(self):
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                self.assertLessEqual(len(c["questions"]), config.MAX_QUESTIONS_PER_CONCEPT)

    def test_each_lesson_mixes_interactions(self):                # variety so the student does not get bored
        for lesson in self.g.lessons():
            kinds = {q["template"] for c in build_lesson(self.g, lesson)["concepts"] for q in c["questions"]}
            self.assertGreaterEqual(len(kinds), 4, lesson.id)

    def test_no_kind_in_more_than_half_of_a_lesson(self):    # the bridge used to be in every concept
        for lesson in self.g.lessons():
            rec = build_lesson(self.g, lesson)
            n = len(rec["concepts"])
            cap = max(1, -(-n // 2))
            counts = {}
            for c in rec["concepts"]:
                for q in c["questions"]:
                    counts[q["template"]] = counts.get(q["template"], 0) + 1
            for kind, k in counts.items():
                if kind != "adjust":
                    self.assertLessEqual(k, cap, f"{lesson.id}: {kind}")

    def test_the_new_activities_are_used(self):
        kinds = {q["template"] for l in self.g.lessons() for c in build_lesson(self.g, l)["concepts"] for q in c["questions"]}
        self.assertTrue({"who_am_i", "fix_chain", "odd_one_out", "true_false", "spell", "memory", "predict"} <= kinds, kinds)

    def test_who_am_i_clues_are_about_the_thing(self):     # note 18: no curriculum talk
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                for q in c["questions"]:
                    if q["template"] == "who_am_i":
                        self.assertGreaterEqual(len(q["clues"]), 2)
                        for clue in q["clues"]:
                            self.assertNotIn("درس", clue); self.assertNotIn("قبلي", clue); self.assertNotIn("بعدي", clue)
                        self.assertNotIn(self.g.concepts[q["target"]].text, " ".join(q["clues"]))

    def test_journey_starts_at_the_concept(self):           # note 24
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                for q in c["questions"]:
                    if q["template"] == "unlocks":
                        self.assertEqual(q["route"][0], c["concept_id"])
                        self.assertEqual(len(q["junctions"]), len(q["route"]) - 1)
                        self.assertEqual(len(q["whys"]), len(q["junctions"]))
                        self.assertIn("مين بيحتاج", q["question"])          # clear for a child (not "a journey from…")

    def test_memory_cards_are_short(self):                  # note 26: readable in time
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                for q in c["questions"]:
                    if q["template"] == "memory":
                        self.assertTrue(all(len(m.split()) <= 14 and "…" not in m for _, m in q["pairs"]))

    def test_everyone_introduces_themselves(self):          # note 20
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                for q in c["questions"]:
                    if q["template"] == "odd_one_out":
                        self.assertEqual(set(q["intros"]), set(q["family"] + [q["intruder"]]))
                        self.assertTrue(all("…" not in t for t in q["intros"].values()))      # complete sentences

    def test_true_false_is_science_not_lesson_order(self):   # «لازم تعرف المي قبل الشمس» is not science
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                for q in c["questions"]:
                    if q["template"] == "true_false":
                        name = self.g.concepts[q["target"]].text
                        for card in q["statements"]:
                            self.assertNotIn("لازم تعرف", card["text"]); self.assertNotIn("بتقدر تتعلم", card["text"])
                            self.assertTrue(card["text"].startswith(f"«{name}»:"))
                        self.assertTrue(any(x["answer"] for x in q["statements"]) and not all(x["answer"] for x in q["statements"]))
                        she = name.split()[0].endswith("ة")
                        for card in q["statements"]:            # the grammar never gives the answer away
                            verb = card["text"].split(":", 1)[1].strip().split()[0]
                            if not card["answer"] and verb[0] in "يت":
                                self.assertEqual(verb[0] == "ت", she, card["text"])

    def test_concepts_come_in_learning_order(self):      # nothing before what it needs
        for lesson in self.g.lessons():
            ids = [c.id for c in lesson.concepts]
            for i, cid in enumerate(ids):
                for p in self.g.ancestors(cid):
                    if p in ids:
                        self.assertLess(ids.index(p), i, (lesson.id, p, cid))

    def test_challenges_go_from_easy_to_hard(self):
        rank = {"easy": 0, "mid": 1, "hard": 2}
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                r = [rank[q["difficulty"]] for q in c["questions"]]
                self.assertEqual(r, sorted(r), c["concept_id"])

    def test_intruder_has_a_named_group_and_a_science_reason(self):     # note 32
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                for q in c["questions"]:
                    if q["template"] == "odd_one_out":
                        self.assertIn(f"«{lesson.title}»", q["question"])
                        self.assertNotIn("درس ثاني", " ".join(q["solution"]))

    def test_journey_has_three_wrong_roads(self):                          # note 33
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                for q in c["questions"]:
                    if q["template"] == "unlocks":
                        self.assertTrue(all(len(j) == 4 for j in q["junctions"]))

    def test_every_concept_has_an_icon(self):              # note 21
        rec = build_lesson(self.g, lessons(self.g)["l_parts"])
        self.assertEqual(rec["icons"]["root"], "🫚")
        self.assertEqual(len(set(rec["icons"][x] for x in ("root", "stem", "leaf", "flower", "fruit", "seed"))), 6)

    def test_lesson_skin(self):
        for lesson in self.g.lessons():
            self.assertEqual(build_lesson(self.g, lesson)["theme"], "garden")

    def test_wrong_options_are_close_ones(self):           # same lesson/topic first: makes the student think
        lesson = lessons(self.g)["l_parts"]
        near = {k.id for k in lesson.concepts} | {"water", "sunlight", "air", "soil"}
        for c in build_lesson(self.g, lesson)["concepts"]:
            for q in c["questions"]:
                if q["template"] == "prereq":
                    wrong = [o for o in q["options"] if o not in q["correct"]]
                    self.assertTrue(all(o in near for o in wrong), (c["concept_id"], wrong))

    def test_no_number_slider_in_a_memorise_understand_subject(self):     # plants = science, no numbers in the book
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                self.assertNotIn("adjust", [q["template"] for q in c["questions"]], c["concept_id"])

    def test_number_slider_only_for_numeric_subjects_with_real_numbers(self):
        import copy
        data = copy.deepcopy(self.g.data)
        data["book"]["subject"] = "Physics"
        data["node_quantities"] = [{"node_id": "water", "label": "x", "unit": "u", "min": 0, "max": 10, "start": 0, "ok_min": 3, "ok_max": 6, "low": "l", "high": "h"}]
        g2 = Graph(data)
        lesson = {l.id: l for l in g2.lessons()}["l_needs"]
        rec = build_lesson(g2, lesson)
        water = [c for c in rec["concepts"] if c["concept_id"] == "water"][0]
        self.assertIn("adjust", [q["template"] for q in water["questions"]])
        data["book"]["subject"] = "Science"                       # same numbers, but a science (memorise/understand) book
        rec2 = build_lesson(Graph(data), {l.id: l for l in Graph(data).lessons()}["l_needs"])
        self.assertNotIn("adjust", [q["template"] for c in rec2["concepts"] for q in c["questions"]])

    def test_predict_is_cause_and_effect_from_the_graph(self):
        found = 0
        for lesson in self.g.lessons():
            for c in build_lesson(self.g, lesson)["concepts"]:
                for q in c["questions"]:
                    if q["template"] == "predict":
                        found += 1
                        after = self.g.descendants(q["target"])
                        self.assertTrue(all(x in after for x in q["affected"]))
                        self.assertTrue(all(x not in after for x in q["unaffected"]))
                        self.assertIn("بيتأثروا", q["options"][q["answer"]])
        self.assertGreater(found, 0)

    def test_missing_questions_give_a_warning(self):
        saved = config.TEMPLATES
        try:
            config.TEMPLATES = ("prereq",)          # only one template: some concepts have nothing before them
            rec = build_lesson(self.g, lessons(self.g)["l_needs"])
        finally:
            config.TEMPLATES = saved
        self.assertLess(rec["coverage"]["percent"], 100)
        self.assertTrue(any(w.startswith("coverage:") for w in rec["warnings"]))


class TestGeneratedQuestions(unittest.TestCase):
    def setUp(self):
        self.g = Graph.load(NEW)

    def all_questions(self):
        for lesson in self.g.lessons():
            per_concept, _ = offline_generator.generate(self.g, lesson)
            for qs in per_concept.values():
                for q in qs:
                    yield lesson, q

    def test_every_question_is_valid(self):
        for lesson, q in self.all_questions():
            self.assertEqual(validator.check(q, self.g, lesson.id), [], f"{lesson.id}/{q['target']}/{q['template']}")

    def test_only_entities_inside_questions(self):
        for lesson, q in self.all_questions():
            used = (q.get("order", []) + q.get("options", []) * (q["template"] not in ("meaning", "predict")) + q["concepts"]
                    + q.get("before", []) + q.get("after", []) + [p[0] for p in q.get("pairs", [])])
            self.assertTrue(all(self.g.concepts[x].level == "entity" for x in used))

    def test_sequence_contains_the_concept_and_follows_edges(self):
        for lesson, q in self.all_questions():
            if q["template"] == "sequence":
                self.assertIn(q["target"], q["order"])
                self.assertTrue(all(self.g.is_prereq(a, b) for a, b in zip(q["order"], q["order"][1:])))

    def test_no_related_concept_is_marked_wrong(self):
        for lesson, q in self.all_questions():
            if q["template"] == "prereq":
                rel = self.g.ancestors(q["target"])
                self.assertTrue(all(o in q["correct"] or o not in rel for o in q["options"]))
            elif q["template"] == "unlocks":
                for here, nxt, opts in zip(q["route"], q["route"][1:], q["junctions"]):
                    rel = self.g.descendants(here) | self.g.ancestors(here)
                    self.assertTrue(all(o == nxt or o not in rel for o in opts))

    def test_meaning_has_one_right_answer(self):
        for lesson, q in self.all_questions():
            if q["template"] == "meaning":
                self.assertEqual(q["options"].count(q["answer"]), 1)

    def test_no_repeated_chain_in_a_lesson(self):        # same bridge twice = boring
        for lesson in self.g.lessons():
            per_concept, _ = offline_generator.generate(self.g, lesson)
            chains = [tuple(q["order"]) for qs in per_concept.values() for q in qs if q["template"] == "sequence"]
            self.assertEqual(len(chains), len(set(chains)), lesson.id)

    def test_same_graph_same_questions(self):
        l = self.g.lessons()[0]
        self.assertEqual(offline_generator.generate(self.g, l), offline_generator.generate(self.g, l))


class TestOldFormatStillWorks(unittest.TestCase):
    def test_old_flat_graph(self):
        g = Graph.load(OLD)
        self.assertEqual(g.format, "old")
        lesson = g.lessons()[0]
        per_concept, _ = offline_generator.generate(g, lesson)
        qs = [q for v in per_concept.values() for q in v]
        self.assertTrue(qs)
        self.assertTrue(all(not validator.check(q, g, lesson.id) for q in qs))


class TestValidatorRejects(unittest.TestCase):
    def setUp(self):
        self.g = Graph.load(NEW)
        self.ok = {"template": "sequence", "difficulty": "mid", "question": "q", "how": "h", "solution": ["s"],
                   "target": "root", "order": ["root", "stem", "leaf"], "concepts": ["root", "stem", "leaf"]}

    def test_valid_passes(self):
        self.assertEqual(validator.check(self.ok, self.g, "l_parts"), [])

    def test_unknown_template(self):
        self.assertTrue(validator.check({**self.ok, "template": "essay"}, self.g, "l_parts"))

    def test_extra_field(self):
        self.assertTrue(validator.check({**self.ok, "score": 10}, self.g, "l_parts"))

    def test_invented_concept(self):
        self.assertTrue(validator.check({**self.ok, "order": ["root", "trunk"]}, self.g, "l_parts"))

    def test_wrong_order(self):
        self.assertTrue(validator.check({**self.ok, "order": ["leaf", "stem", "root"]}, self.g, "l_parts"))

    def test_target_from_another_lesson(self):
        self.assertTrue(validator.check({**self.ok, "target": "water", "concepts": ["water"]}, self.g, "l_parts"))

    def test_concepts_must_start_with_target(self):
        self.assertTrue(validator.check({**self.ok, "concepts": ["stem", "root"]}, self.g, "l_parts"))

    def test_fake_prerequisite(self):
        q = {"template": "prereq", "difficulty": "mid", "question": "q", "how": "h", "solution": ["s"],
             "target": "leaf", "correct": ["flower"], "options": ["flower", "stem", "seed"], "concepts": ["leaf", "flower"]}
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_indirect_prerequisite_marked_wrong(self):
        q = {"template": "prereq", "difficulty": "mid", "question": "q", "how": "h", "solution": ["s"],
             "target": "leaf", "correct": ["stem", "air", "sunlight"], "options": ["stem", "air", "sunlight", "water", "seed"],
             "concepts": ["leaf", "stem"]}
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_fake_journey(self):
        q = {"template": "unlocks", "difficulty": "mid", "question": "q", "how": "h", "solution": ["s"], "target": "root",
             "route": ["root", "seed"], "junctions": [["seed", "air", "flower"]], "hints": [["a", "b", "c"]], "whys": ["w"], "concepts": ["root", "seed"]}
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_journey_with_a_linked_wrong_road(self):
        q = {"template": "unlocks", "difficulty": "mid", "question": "q", "how": "h", "solution": ["s"], "target": "root",
             "route": ["root", "stem"], "junctions": [["stem", "leaf", "seed"]], "hints": [["a", "b", "c"]], "whys": ["w"], "concepts": ["root", "stem"]}
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_meaning_answer_missing(self):
        q = {"template": "meaning", "difficulty": "easy", "question": "q", "how": "h", "solution": ["s"],
             "target": "root", "options": ["a", "b", "c"], "answer": "d", "concepts": ["root"]}
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_missing_solution(self):
        self.assertTrue(validator.check({**self.ok, "solution": []}, self.g, "l_parts"))

    def _base(self, t, **kw):
        return {"template": t, "difficulty": "mid", "question": "q", "how": "h", "solution": ["s"], "target": "root",
                "concepts": ["root"], **kw}

    def test_true_false_needs_both_answers(self):
        cards = [{"text": "a", "answer": True}] * 3
        self.assertTrue(validator.check(self._base("true_false", statements=cards), self.g, "l_parts"))

    def test_fix_chain_wrong_link_inside_chain(self):
        q = self._base("fix_chain", chain=["soil", "root", "stem"], wrong_index=0, wrong="stem", options=["soil", "air", "seed"])
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_odd_one_out_intruder_from_same_lesson(self):
        q = self._base("odd_one_out", family=["root", "stem", "leaf"], intruder="seed", intros={})
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_who_am_i_answer_missing(self):
        q = self._base("who_am_i", clues=["a", "b"], options=["stem", "leaf", "seed"])
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_spell_wrong_word(self):
        self.assertTrue(validator.check(self._base("spell", word="الساق", clue="x"), self.g, "l_parts"))

    def test_memory_without_target(self):
        q = self._base("memory", pairs=[["stem", "a"], ["leaf", "b"], ["seed", "c"]])
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_sort_wrong_basket(self):
        q = {"template": "sort", "difficulty": "mid", "question": "q", "how": "h", "solution": ["s"],
             "target": "root", "before": ["stem"], "after": ["soil"], "concepts": ["root", "stem", "soil"]}
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_match_without_target(self):
        q = {"template": "match", "difficulty": "easy", "question": "q", "how": "h", "solution": ["s"],
             "target": "root", "pairs": [["stem", "a"], ["leaf", "b"], ["seed", "c"]], "concepts": ["root"]}
        self.assertTrue(validator.check(q, self.g, "l_parts"))

    def test_slider_starting_on_the_answer(self):
        f = {"label": "x", "unit": "u", "min": 0, "max": 10, "start": 4, "ok_min": 3, "ok_max": 6}
        q = {"template": "adjust", "difficulty": "hard", "question": "q", "how": "h", "solution": ["s"],
             "target": "water", "factor": f, "concepts": ["water"]}
        self.assertTrue(validator.check(q, self.g, "l_needs"))

    def test_predict_with_a_wrong_effect(self):
        q = {"template": "predict", "difficulty": "mid", "question": "q", "how": "h", "solution": ["s"], "target": "water",
             "options": ["a", "b", "c"], "answer": 0, "affected": ["flower"], "unaffected": ["soil"], "concepts": ["water"]}
        self.assertTrue(validator.check(q, self.g, "l_needs"))

    def test_slider_on_concept_without_numbers(self):
        f = {"label": "x", "unit": "u", "min": 0, "max": 10, "start": 0, "ok_min": 3, "ok_max": 6}
        q = {"template": "adjust", "difficulty": "hard", "question": "q", "how": "h", "solution": ["s"],
             "target": "air", "factor": f, "concepts": ["air"]}
        self.assertTrue(validator.check(q, self.g, "l_needs"))


class TestLLMPath(unittest.TestCase):
    def setUp(self):
        self.g = Graph.load(NEW)
        self.lesson = lessons(self.g)["l_parts"]

    def test_prompt_asks_for_every_concept(self):
        system, user = llm_generator.build_prompt(self.g, self.lesson)
        self.assertIn("EVERY CONCEPT", system)
        self.assertIn('"root"', user)

    def test_good_llm_reply_is_used(self):
        reply = json.dumps({"questions": [{"template": "sequence", "difficulty": "mid", "question": "رتّب طريق الماء",
                                           "how": "اكبس بالترتيب", "solution": ["الجذر أولاً"], "target": "root",
                                           "order": ["root", "stem", "leaf"], "concepts": ["root", "stem", "leaf"]}]})
        rec = build_lesson(self.g, self.lesson, lambda s, u: reply)
        root = [c for c in rec["concepts"] if c["concept_id"] == "root"][0]
        self.assertIn("رتّب طريق الماء", [q["question"] for q in root["questions"]])
        self.assertEqual(rec["generator"], "llm+offline")

    def test_broken_llm_reply_falls_back(self):
        rec = build_lesson(self.g, self.lesson, lambda s, u: "sorry, here are some questions…")
        self.assertEqual(rec["generator"], "offline")
        self.assertTrue(any("llm failed" in w for w in rec["warnings"]))
        self.assertEqual(rec["coverage"]["percent"], 100)

    def test_invalid_llm_question_is_rejected(self):
        reply = json.dumps({"questions": [{"template": "sequence", "difficulty": "mid", "question": "q", "how": "h",
                                           "solution": ["s"], "target": "root", "order": ["leaf", "root"], "concepts": ["root"]}]})
        rec = build_lesson(self.g, self.lesson, lambda s, u: reply)
        self.assertTrue(any("invalid" in w for w in rec["warnings"]))


class TestFactoryRun(unittest.TestCase):
    def test_saves_every_lesson_grouped_by_concept(self):
        out = tempfile.mkdtemp()
        try:
            recs = run_factory(NEW, out)
            self.assertEqual(len(recs), 3)
            index = json.load(open(os.path.join(out, "index.json"), encoding="utf-8"))
            self.assertEqual(len(index["lessons"]), 3)
            for r in recs:
                saved = json.load(open(os.path.join(out, "lessons", r["lesson_id"], "questions.json"), encoding="utf-8"))
                self.assertEqual(saved["status"], "needs_review")
                self.assertEqual(saved["book_id"], "sci_g4")
                self.assertEqual(len(saved["concepts"]), len(r["concepts"]))
        finally:
            shutil.rmtree(out)


if __name__ == "__main__":
    unittest.main()
