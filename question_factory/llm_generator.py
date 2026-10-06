"""The LLM path: builds the instruction, calls the team's LLM gateway, parses and validates the answer.

The LLM only fills data inside the closed templates. If its answer is broken or invalid,
the factory falls back to the offline generator for that template.
"""
import json

import config
from graph_reader import Graph, Lesson
from templates import SCHEMAS

SYSTEM = """You write interactive, game-like questions for a school tutoring platform.
EVERY CONCEPT of the lesson gets its own questions (at least {min_per_concept} per concept).
You ONLY fill data for the allowed templates. Return ONLY a JSON object: {"questions": [...]}. No other text.
Rules:
1. Use ONLY concept ids that appear in the lesson context. Never invent ids.
2. Allowed templates and fields: {schemas}
3. Every question needs: template, difficulty (easy|mid|hard), question, how, solution (list of short steps),
   target (the ONE concept the question belongs to) and concepts (ids it tests, starting with target).
4. "sequence" order and "prereq" answers MUST follow the prerequisiteOf edges given in the context.
5. Write question, how and solution in Arabic for {grade} students. Keep each line short.
6. Every question must make the student DO something (match, sort, order, choose)."""


def lesson_context(g: Graph, lesson: Lesson) -> dict:
    own = [c.id for c in lesson.concepts] + [lesson.id]
    near = set(own)
    for c in own:
        near |= set(g.prereq_in.get(c, [])) | set(g.prereq_out.get(c, []))
    return {
        "lesson": {"id": lesson.id, "title": lesson.title, "description": lesson.description},
        "concepts": [{"id": c.id, "text": c.text, "description": c.description} for c in lesson.concepts],
        "nearby_concepts": [{"id": x, "text": g.concepts[x].text} for x in sorted(near - set(own))],
        "prerequisiteOf": [[a, b] for a in sorted(near) for b in g.prereq_out.get(a, []) if b in near],
    }


def build_prompt(g: Graph, lesson: Lesson, grade: str = "primary") -> tuple:
    schemas = {t: {k: v.__name__ for k, v in s.items()} for t, s in SCHEMAS.items()}
    system = (SYSTEM.replace("{schemas}", json.dumps(schemas)).replace("{grade}", grade)
              .replace("{min_per_concept}", str(config.MIN_QUESTIONS_PER_CONCEPT)))
    user = "Lesson context:\n" + json.dumps(lesson_context(g, lesson), ensure_ascii=False, indent=1)
    return system, user


def parse(reply: str) -> list:
    """The reply must be one JSON object with a 'questions' list. Anything else is rejected."""
    data = json.loads(reply)
    if not isinstance(data, dict) or not isinstance(data.get("questions"), list):
        raise ValueError("reply must be {\"questions\": [...]}")
    return data["questions"]


def generate(g: Graph, lesson: Lesson, llm_generate) -> list:
    """llm_generate(system, user) -> str is the team's LLM gateway (Architecture: llm.generate port)."""
    system, user = build_prompt(g, lesson)
    return parse(llm_generate(system, user))
