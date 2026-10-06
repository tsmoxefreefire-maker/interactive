"""Saves each lesson's questions (grouped by concept) next to the lesson, plus one index for the whole book."""
import json
import os
from datetime import date


def save_lesson(out_dir: str, record: dict) -> str:
    folder = os.path.join(out_dir, "lessons", record["lesson_id"])
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "questions.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return path


def save_index(out_dir: str, records: list, source: str) -> str:
    index = {"source_graph": source, "generated_on": date.today().isoformat(),
             "lessons": [{"lesson_id": r["lesson_id"], "title": r["lesson_title"], "unit_id": r.get("unit_id", ""),
                          "topic_id": r.get("topic_id", ""), "lesson_minutes": r.get("lesson_minutes", 0),
                          "questions": r["question_count"],
                          "concepts": {c["concept_id"]: len(c["questions"]) for c in r["concepts"]},
                          "coverage_percent": r["coverage"]["percent"], "status": r["status"],
                          "warnings": r["warnings"]} for r in records]}
    path = os.path.join(out_dir, "index.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    return path
