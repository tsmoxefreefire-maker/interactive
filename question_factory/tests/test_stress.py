"""A big, messy book: many lessons, missing meanings, circular links, unknown names.
The factory must keep going to the end, never crash, and give every concept a picture that means something."""
import json
import os
import random
import tempfile
import time
import unittest

import offline_generator
from graph_reader import Graph
from main import build_lesson, run_factory

NAMES = ["الجمع", "الطرح", "الكسور", "الزوايا", "المعادلات", "النسبة المئوية", "الاحتمالات", "المساحة", "المحيط", "الأنماط",
         "الخلية", "القلب", "الصوت", "الحرارة", "الصخور", "المطر", "الكواكب", "القمر", "النجوم", "المغناطيس", "الذرة",
         "الإعراب", "الفعل", "الاسم", "الحضارة الفرعونية", "الخرائط", "الجبال", "شيء غريب جداً", "مفهوم بلا اسم معروف", "Photosynthesis"]


def messy_book(lessons=30, per=8, seed=7):
    rng = random.Random(seed)
    nodes = [{"id": "b", "title": "كتاب ضخم", "level": "book"}, {"id": "u", "title": "وحدة", "level": "unit"}, {"id": "t", "title": "موضوع", "level": "topic"}]
    rels = [{"source_node_id": "u", "target_node_id": "b", "type": "subsetOf"}, {"source_node_id": "t", "target_node_id": "u", "type": "subsetOf"}]
    content, ids = [], []
    for li in range(lessons):
        lid = f"l{li}"
        nodes.append({"id": lid, "title": f"الدرس {li + 1}", "level": "lesson"})
        rels.append({"source_node_id": lid, "target_node_id": "t", "type": "subsetOf"})
        for k in range(per):
            cid = f"c{li}_{k}"
            ids.append(cid)
            nodes.append({"id": cid, "title": f"{rng.choice(NAMES)} {li}-{k}", "level": "entity"})
            rels.append({"source_node_id": cid, "target_node_id": lid, "type": "subsetOf"})
            if rng.random() > 0.2:                                   # some concepts have NO meaning
                content.append({"node_id": cid, "content_type": "text", "content_text": rng.choice(
                    ["جزء من كلّ؛ يُكتب بسطاً فوق مقام", "ضمّ عددين معاً؛ ينتج عنه المجموع", "شكل له ثلاثة أضلاع", "", "كلمة تدل على حدث وزمن"])})
    for _ in range(len(ids) * 2):                                    # random links, including circles
        a, b = rng.sample(ids, 2)
        rels.append({"source_node_id": a, "target_node_id": b, "type": "prerequisiteOf", "weight": 0.5})
    rels.append({"source_node_id": ids[0], "target_node_id": ids[1], "type": "prerequisiteOf"})
    rels.append({"source_node_id": ids[1], "target_node_id": ids[0], "type": "prerequisiteOf"})   # a circle on purpose
    return {"book": {"id": "b", "title": "كتاب ضخم", "subject": "Mathematics"}, "nodes": nodes, "relationships": rels, "node_content": content}


class TestBigMessyBook(unittest.TestCase):
    def test_keeps_going_to_the_end(self):
        data = messy_book()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "big.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            t0 = time.time()
            recs = run_factory(path, os.path.join(tmp, "out"))
            took = time.time() - t0
            self.assertEqual(len(recs), 30)                           # every lesson, none skipped
            self.assertTrue(os.path.exists(os.path.join(tmp, "out", "index.json")))
            self.assertLess(took, 60)
            total = sum(r["question_count"] for r in recs)
            self.assertGreater(total, 30 * 8)                         # questions for (almost) every concept

    def test_lessons_never_lock_each_other_in_a_circle(self):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "player"))
        import build_player
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "big.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(messy_book(), f, ensure_ascii=False)
            run_factory(path, os.path.join(tmp, "out"))
            lessons = build_player.pack(path, os.path.join(tmp, "out"), "big")["lessons"]
        order = {l["lesson_id"]: i for i, l in enumerate(lessons)}
        self.assertFalse(lessons[0]["requires"])                                  # the first lesson is always open
        self.assertTrue(all(order[r] < order[l["lesson_id"]] for l in lessons for r in l["requires"]))

    def test_every_concept_gets_a_picture_that_means_something(self):
        g = Graph(messy_book(lessons=6))
        rec = build_lesson(g, g.lessons()[0])
        for cid, icon in rec["icons"].items():
            self.assertTrue(icon in offline_generator.ART_ICONS or icon.startswith("subj:🧮:"), (cid, icon))
            self.assertNotEqual(icon, "🔹")


if __name__ == "__main__":
    unittest.main()
