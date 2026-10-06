"""Reads the curriculum graph and turns it into lessons the factory can work on.

Supports the NEW structure (Omar Essam): Book > Unit > Topic > Lesson > Entity, stored as tables:
    book, nodes, relationships, node_metadata, node_content
and, for backward compatibility, the old flat structure (entities + relationships).
"""
import json
from collections import defaultdict
from dataclasses import dataclass, field

SUBSET, PREREQ = "subsetOf", "prerequisiteOf"


@dataclass
class Concept:
    id: str
    text: str
    description: str
    level: str = ""                 # unit | topic | lesson | entity (new structure)
    difficulty: str = ""
    minutes: float = 0.0
    importance: float = 0.0
    quantity: dict = None           # TEST ONLY: a number the student can adjust (node_quantities)


@dataclass
class Lesson:
    id: str
    title: str
    description: str
    concepts: list = field(default_factory=list)   # the lesson's own entities
    topic_id: str = ""                             # the Topic above the lesson
    unit_id: str = ""                              # the Unit above the Topic
    minutes: float = 0.0                           # decision: lesson time = sum of its concepts' minutes


class Graph:
    def __init__(self, data: dict):
        self.data = data
        self.format = "new" if "nodes" in data else "old"
        self.book = data.get("book", {})
        self.concepts = {}
        self.children = defaultdict(list)
        self.parent = {}
        self.prereq_in = defaultdict(list)
        self.prereq_out = defaultdict(list)
        self.weight = {}
        self.justification = {}
        (self._read_new if self.format == "new" else self._read_old)(data)

    # ---- new structure: tables ----
    def _read_new(self, data):
        meta = {m["node_id"]: m for m in data.get("node_metadata", [])}
        text = {}
        for c in data.get("node_content", []):
            if c.get("content_type") == "text" and c.get("content_text"):
                text[c["node_id"]] = c["content_text"]
        for n in data["nodes"]:
            m = meta.get(n["id"], {})
            self.concepts[n["id"]] = Concept(n["id"], n["title"], text.get(n["id"], n.get("learning_objective") or ""),
                                             n.get("level", ""), m.get("difficulty") or "", m.get("estimated_minutes") or 0,
                                             m.get("importance") or 0)
        for r in data["relationships"]:
            self._add(r["source_node_id"], r["target_node_id"], r["type"], r.get("weight"), "")
        for qn in data.get("node_quantities", []):        # proposal, not in Omar's tables yet
            if qn.get("node_id") in self.concepts:
                self.concepts[qn["node_id"]].quantity = {k: v for k, v in qn.items() if k != "node_id"}

    # ---- old flat structure ----
    def _read_old(self, data):
        for e in data["entities"]:
            self.concepts[e["id"]] = Concept(e["id"], e.get("text", e["id"]), e.get("metadata", {}).get("description", ""))
        for r in data["relationships"]:
            self._add(r["source"], r["target"], r["type"], None, r.get("metadata", {}).get("justification", ""))

    def _add(self, s, t, kind, weight, why):
        if s not in self.concepts or t not in self.concepts:
            return
        self.justification[(s, t, kind)] = why
        self.weight[(s, t, kind)] = weight
        if kind == SUBSET:
            self.children[t].append(s)
            self.parent[s] = t
        elif kind == PREREQ:
            self.prereq_out[s].append(t)
            self.prereq_in[t].append(s)

    @classmethod
    def load(cls, path: str) -> "Graph":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    def is_prereq(self, a: str, b: str) -> bool:
        return b in self.prereq_out.get(a, [])

    def ancestors(self, x: str) -> set:
        """Everything needed before x, directly or through a chain (water -> root -> stem -> leaf). Remembered."""
        memo = self.__dict__.setdefault("_anc_memo", {})
        if x in memo:
            return set(memo[x])
        seen, stack = set(), list(self.prereq_in.get(x, []))
        while stack:
            a = stack.pop()
            if a not in seen:
                seen.add(a); stack += self.prereq_in.get(a, [])
        memo[x] = frozenset(seen)
        return seen

    def depth(self, x: str) -> int:
        """How many steps of prerequisites are behind x (longest chain).
        Each concept is computed ONCE and remembered (a big book with many links stays fast);
        a link that closes a circle is ignored, so a circular graph never makes it loop."""
        memo = self.__dict__.setdefault("_depth_memo", {})
        if x in memo:
            return memo[x]
        on_path = set()
        def visit(n):
            if n in memo:
                return memo[n]
            on_path.add(n)
            best = 0
            for p in self.prereq_in.get(n, []):
                if p not in on_path:
                    best = max(best, 1 + visit(p))
            on_path.discard(n)
            memo[n] = best
            return best
        import sys
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 4 * len(self.concepts) + 100))
        return visit(x)

    def learning_order(self, concepts: list) -> list:
        """Concepts sorted so that nothing comes before what it needs (then by the graph's own order)."""
        order = {cid: i for i, cid in enumerate(self.concepts)}
        return sorted(concepts, key=lambda c: (self.depth(c.id), order[c.id]))

    def descendants(self, x: str) -> set:
        """Everything that comes after x, directly or through a chain. Remembered."""
        memo = self.__dict__.setdefault("_desc_memo", {})
        if x in memo:
            return set(memo[x])
        seen, stack = set(), list(self.prereq_out.get(x, []))
        while stack:
            a = stack.pop()
            if a not in seen:
                seen.add(a); stack += self.prereq_out.get(a, [])
        memo[x] = frozenset(seen)
        return seen

    def _is_lesson(self, node: str) -> bool:
        c = self.concepts[node]
        if c.level:                                      # new structure tells us directly
            return c.level == "lesson"
        kids = self.children.get(node, [])               # old structure: parent of leaf concepts
        return bool(kids) and all(not self.children.get(k) for k in kids)

    def lessons(self) -> list:
        result = []
        for node in self.concepts:
            if not self._is_lesson(node):
                continue
            c = self.concepts[node]
            kids = [self.concepts[k] for k in sorted(self.children.get(node, []))]
            kids = [k for k in kids if k.level in ("", "entity")]
            kids = self.learning_order(kids)          # what must come first, comes first
            topic = self.parent.get(node, "")
            unit = self.parent.get(topic, "") if topic else ""
            minutes = sum(k.minutes for k in kids)
            result.append(Lesson(node, c.text, c.description, kids, topic, unit, minutes))
        return sorted(result, key=lambda l: l.id)
