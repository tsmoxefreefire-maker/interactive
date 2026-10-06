import io
import json
import os
import re
import unittest
import urllib.error

import llm_gateway
import llm_polish
import validator
from graph_reader import Graph
from main import build_lesson

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW = os.path.join(HERE, "plants_book_graph.json")


class FakeResponse(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): return False


class TestGateway(unittest.TestCase):
    def setUp(self):
        self.saved = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "sk-test"

    def tearDown(self):
        if self.saved is None: os.environ.pop("ANTHROPIC_API_KEY", None)
        else: os.environ["ANTHROPIC_API_KEY"] = self.saved

    def test_request_follows_the_claude_api(self):
        r = llm_gateway.build_request("sys", "hi", "sk-test", "claude-sonnet-5-5")
        self.assertEqual(r.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(r.get_header("X-api-key"), "sk-test")
        self.assertEqual(r.get_header("Anthropic-version"), "2023-06-01")
        body = json.loads(r.data)
        self.assertEqual((body["model"], body["system"], body["messages"][0]["content"]), ("claude-sonnet-5-5", "sys", "hi"))

    def test_reads_the_text_back(self):
        fake = lambda req, timeout: FakeResponse(json.dumps({"content": [{"type": "text", "text": "مرحبا"}]}).encode())
        self.assertEqual(llm_gateway.generate("s", "u", opener=fake), "مرحبا")

    def test_missing_key_is_a_clear_error(self):
        os.environ["ANTHROPIC_API_KEY"] = ""
        with self.assertRaises(llm_gateway.LLMError):
            llm_gateway.generate("s", "u", opener=lambda *a, **k: None)

    def test_api_error_is_a_clear_error(self):
        def boom(req, timeout): raise urllib.error.HTTPError(req.full_url, 401, "no", {}, io.BytesIO(b"bad key"))
        with self.assertRaises(llm_gateway.LLMError):
            llm_gateway.generate("s", "u", opener=boom)


class TestPolish(unittest.TestCase):
    """The LLM rewrites the WORDS; the answers and the concepts never change."""
    def setUp(self):
        self.g = Graph.load(NEW)
        self.lesson = {l.id: l for l in self.g.lessons()}["l_parts"]
        self.rec = build_lesson(self.g, self.lesson)

    def editor(self, change):
        def llm(system, user):
            texts = json.loads(user)
            return json.dumps({k: change(k, v) for k, v in texts.items()}, ensure_ascii=False)
        return llm

    def test_kind_rewrite_keeps_everything_valid(self):
        rec = llm_polish.polish_lesson(self.rec, self.g, self.editor(lambda k, v: "✨ " + v))
        self.assertEqual(rec["generator"], "offline+llm-polish")
        self.assertGreater(rec["llm"]["questions_changed"], 10)
        for c in rec["concepts"]:
            for q in c["questions"]:
                self.assertEqual(validator.check(q, self.g, "l_parts"), [])
                if q["template"] == "meaning":
                    self.assertIn(q["answer"], q["options"])          # equal texts stay equal
                    self.assertTrue(q["answer"].startswith("✨"))

    def test_answers_never_change(self):
        before = {(c["concept_id"], i): (q.get("target"), q.get("order"), q.get("correct"), q.get("route"),
                   [s.get("answer") for s in q.get("statements", [])]) for c in self.rec["concepts"] for i, q in enumerate(c["questions"])}
        rec = llm_polish.polish_lesson(self.rec, self.g, self.editor(lambda k, v: v + " 🌱"))
        after = {(c["concept_id"], i): (q.get("target"), q.get("order"), q.get("correct"), q.get("route"),
                  [s.get("answer") for s in q.get("statements", [])]) for c in rec["concepts"] for i, q in enumerate(c["questions"])}
        self.assertEqual(before, after)

    def test_dropping_a_concept_name_is_rejected(self):
        rec = llm_polish.polish_lesson(self.rec, self.g, self.editor(lambda k, v: re.sub(r"«[^»]+»", "هو", v)))
        for c in rec["concepts"]:
            for q in c["questions"]:
                if q["template"] == "true_false":
                    self.assertTrue(all("«" in s["text"] for s in q["statements"]))
        self.assertGreater(rec["llm"]["rejected"], 0)

    def test_inventing_a_new_name_is_rejected(self):
        rec = llm_polish.polish_lesson(self.rec, self.g, self.editor(lambda k, v: v + " «القمر»"))
        self.assertNotIn("«القمر»", json.dumps(rec, ensure_ascii=False))

    def test_broken_reply_keeps_the_original(self):
        original = json.dumps(self.rec["concepts"], ensure_ascii=False)
        rec = llm_polish.polish_lesson(self.rec, self.g, lambda s, u: "sorry, I can't")
        self.assertEqual(json.dumps(rec["concepts"], ensure_ascii=False), original)
        self.assertTrue(any("llm polish failed" in w for w in rec["warnings"]))

    def test_far_too_long_is_rejected(self):
        rec = llm_polish.polish_lesson(self.rec, self.g, self.editor(lambda k, v: v * 30))
        self.assertEqual(rec["llm"]["rewritten"], 0)

    def test_the_editor_is_told_the_rules(self):
        seen = {}
        def llm(system, user):
            seen["system"] = system; return user
        llm_polish.polish_lesson(self.rec, self.g, llm)
        self.assertIn("same facts", seen["system"]); self.assertIn("«…»", seen["system"])


if __name__ == "__main__":
    unittest.main()
