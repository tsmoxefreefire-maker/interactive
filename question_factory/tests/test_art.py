import json
import os
import unittest

import llm_art
import offline_generator
from graph_reader import Graph
from main import build_lesson

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATH = os.path.join(HERE, "math_book_graph.json")
GOOD = '<path d="M10 10 L90 10 L90 90 Z" fill="#7CC6F2" stroke="#3b2a1a" stroke-width="2.6"/><circle cx="50" cy="50" r="20" fill="#FFD25A"/>'


class TestSafeDrawings(unittest.TestCase):
    """A drawing from the LLM is kept only if it is simple and safe."""
    def test_simple_shapes_are_kept(self):
        self.assertEqual(llm_art.clean_svg(GOOD), GOOD)

    def test_scripts_links_text_styles_are_refused(self):
        for bad in ['<script>alert(1)</script>', '<circle cx="5" cy="5" r="5" onload="x()"/>', '<a href="http://x"><circle r="5"/></a>',
                    '<text x="1" y="1">hi</text>', '<rect width="5" height="5" style="fill:red"/>', '<image href="data:x"/>',
                    '<rect width="5" height="5" fill="url(#g)"/>', '<foreignObject/>', 'not svg <<', '']:
            self.assertIsNone(llm_art.clean_svg(bad), bad)

    def test_too_big_is_refused(self):
        self.assertIsNone(llm_art.clean_svg('<circle cx="5" cy="5" r="5"/>' * 60))

    def test_face_must_be_inside_and_sized(self):
        self.assertEqual(llm_art.clean_face({"x": 50, "y": 60, "s": 0.8}), {"x": 50.0, "y": 60.0, "s": 0.8})
        self.assertIsNone(llm_art.clean_face({"x": 99, "y": 60, "s": 0.8}))
        self.assertIsNone(llm_art.clean_face({"x": 50, "y": 60, "s": 3}))


class TestAnySubject(unittest.TestCase):
    """The same factory works for a maths book: questions, pictures from the subject library, numbers only where the book has them."""
    def setUp(self):
        self.g = Graph.load(MATH)
        self.recs = [build_lesson(self.g, l) for l in self.g.lessons()]

    def test_maths_book_without_any_code_change(self):
        self.assertEqual(len(self.recs), 4)
        self.assertTrue(all(r["coverage"]["percent"] == 100 for r in self.recs))

    def test_every_maths_concept_has_a_maths_picture(self):
        icons = self.recs[0]["icons"]
        self.assertTrue(all(icon in offline_generator.ART_ICONS for icon in icons.values()), icons)
        self.assertEqual(icons["fraction"], "🍕"); self.assertEqual(icons["addition"], "➕")

    def test_number_slider_appears_in_maths(self):
        kinds = {q["template"] for r in self.recs for c in r["concepts"] for q in c["questions"]}
        self.assertIn("adjust", kinds)

    def test_llm_draws_what_the_library_cannot(self):
        g = Graph.load(MATH)
        recs = [build_lesson(g, l) for l in g.lessons()]
        recs[0]["icons"]["numbers"] = "🔹"                      # pretend the library cannot draw «الأعداد»
        for r in recs[1:]:
            r["icons"]["numbers"] = "🔹"
        asked = {}
        def illustrator(system, user):
            asked.update(json.loads(user))
            return json.dumps({cid: {"body": GOOD, "face": {"x": 50, "y": 55, "s": 0.8}, "anim": "bob"} for cid in json.loads(user)})
        library = {}
        art = llm_art.draw_missing(g, recs, offline_generator.ART_ICONS, illustrator, library)
        self.assertEqual(list(asked), ["numbers"])
        self.assertIn("أعداد", library)                                    # kept by NAME, for any book
        self.assertIn("numbers", art)
        self.assertTrue(all(r["icons"]["numbers"] == "art:numbers" and "numbers" in r["art"] for r in recs))

    def test_a_bad_drawing_falls_back_to_the_generic_character(self):
        g = Graph.load(MATH)
        recs = [build_lesson(g, l) for l in g.lessons()]
        for r in recs:
            r["icons"]["numbers"] = "🔹"
        art = llm_art.draw_missing(g, recs, offline_generator.ART_ICONS,
                                   lambda s, u: json.dumps({"numbers": {"body": "<script>x</script>", "face": {"x": 50, "y": 50, "s": .8}}}))
        self.assertEqual(art, {})
        self.assertEqual(recs[0]["icons"]["numbers"], "🔹")
        self.assertEqual(recs[0]["llm"]["art"]["rejected"], 1)


class TestGrowingLibrary(unittest.TestCase):
    """A concept drawn once is never drawn again — not in another lesson, another book or another run, even without the LLM."""
    def recs_with_unknown(self):
        g = Graph.load(MATH)
        recs = [build_lesson(g, l) for l in g.lessons()]
        for r in recs:
            r["icons"]["numbers"] = "subj:🧮:أعداد"
        return g, recs

    def test_second_run_reuses_the_drawing(self):
        library, calls = {}, []
        def illustrator(system, user):
            calls.append(list(json.loads(user)))
            return json.dumps({cid: {"body": GOOD, "face": {"x": 50, "y": 55, "s": .8}} for cid in json.loads(user)})
        g, recs = self.recs_with_unknown(); llm_art.draw_missing(g, recs, offline_generator.ART_ICONS, illustrator, library)
        g, recs = self.recs_with_unknown(); llm_art.draw_missing(g, recs, offline_generator.ART_ICONS, illustrator, library)
        self.assertEqual(len(calls), 1)                                     # asked once only
        self.assertEqual(recs[0]["icons"]["numbers"], "art:numbers")

    def test_library_works_without_the_llm(self):
        library = {"أعداد": {"body": GOOD, "face": {"x": 50, "y": 55, "s": .8}, "anim": "bob"}}
        g, recs = self.recs_with_unknown()
        llm_art.use_library(g, recs, offline_generator.ART_ICONS, library)
        self.assertEqual(recs[0]["icons"]["numbers"], "art:numbers")

    def test_a_bad_library_entry_is_ignored(self):
        g, recs = self.recs_with_unknown()
        llm_art.use_library(g, recs, offline_generator.ART_ICONS, {"أعداد": {"body": "<script/>", "face": {"x": 50, "y": 50, "s": .8}}})
        self.assertEqual(recs[0]["icons"]["numbers"], "subj:🧮:أعداد")


class TestEveryConceptHasAMeaningfulPicture(unittest.TestCase):
    def test_unknown_concept_gets_its_subjects_character_with_its_name(self):
        self.assertTrue(offline_generator.icon_for("الاحتمالات", "", "Mathematics").startswith(("subj:🧮:", "🎲")))
        self.assertEqual(offline_generator.icon_for("الإعراب", "", "Arabic"), "subj:📖:إعراب")

    def test_meaning_helps_when_the_name_does_not(self):
        self.assertEqual(offline_generator.icon_for("الناتج", "ما ينتج عن عملية الجمع", "Mathematics"), "➕")


if __name__ == "__main__":
    unittest.main()
