"""Builds the player page from the factory output (all lessons of one or more graphs)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from graph_reader import Graph

def pack(graph_path, out_dir, title):
    g = Graph.load(graph_path)
    idx = json.load(open(os.path.join(out_dir, "index.json"), encoding="utf-8"))
    lessons = [json.load(open(os.path.join(out_dir, "lessons", l["lesson_id"], "questions.json"), encoding="utf-8")) for l in idx["lessons"]]
    lessons = [l for l in lessons if l["question_count"]]
    order = {t: i for i, t in enumerate(n["id"] for n in g.data.get("nodes", []))}
    owner = {x["concept_id"]: l["lesson_id"] for l in lessons for x in l["concepts"]}
    links = {}   # (needs, needed) -> how many prerequisite links point that way
    for l in lessons:
        for c in l["concepts"]:
            for p in g.prereq_in.get(c["concept_id"], []):
                if owner.get(p) and owner[p] != l["lesson_id"]:
                    links[(l["lesson_id"], owner[p])] = links.get((l["lesson_id"], owner[p]), 0) + 1
    for l in lessons:   # a lesson waits for another only if MOST links point that way (never a circle of locks)
        l["requires"] = sorted(b for (a, b), k in links.items() if a == l["lesson_id"] and k > links.get((b, a), 0))
    req = {l["lesson_id"]: l["requires"] for l in lessons}
    depth, on_path = {}, set()
    def d(lid):                       # each lesson once; a requirement that closes a circle is ignored (no endless loop)
        if lid in depth:
            return depth[lid]
        on_path.add(lid)
        best = 0
        for r in req[lid]:
            if r not in on_path and r in req:
                best = max(best, 1 + d(r))
        on_path.discard(lid)
        depth[lid] = best
        return best
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 4 * len(lessons) + 100))
    for l in lessons:
        d(l["lesson_id"])
    for l in lessons:                 # keep only requirements that go "backwards" → no two lessons can ever lock each other
        l["requires"] = [r for r in l["requires"] if depth.get(r, 0) < depth[l["lesson_id"]]]
    lessons.sort(key=lambda l: (depth[l["lesson_id"]], order.get(l.get("topic_id", ""), 0), order.get(l["lesson_id"], 0)))   # the order to learn them
    subject = str(g.book.get("subject", "")).lower()
    kinds = (("math", ("math", "رياضيات")), ("science", ("science", "biology", "علوم", "أحياء")), ("physics", ("physics", "فيزياء")),
             ("chemistry", ("chem", "كيمياء")), ("geography", ("geograph", "جغرافيا")), ("history", ("history", "تاريخ")),
             ("language", ("arabic", "english", "language", "لغة", "عربي")))
    kind = next((k for k, words in kinds if any(w in subject for w in words)), "general")
    return {"title": title, "subject": kind, "names": {k: c.text for k, c in g.concepts.items()}, "lessons": lessons}

if __name__ == "__main__":
    # python player/build_player.py [graph.json output_folder] [graph2.json output_folder2] ...
    root = os.path.dirname(HERE)
    args = sys.argv[1:] or ["plants_book_graph.json", "output_new"]
    if len(args) % 2:
        sys.exit("give pairs: graph.json output_folder")
    graphs = []
    for gp, od in zip(args[::2], args[1::2]):
        g = Graph.load(os.path.join(root, gp))
        graphs.append(pack(os.path.join(root, gp), os.path.join(root, od), g.book.get("title", "الكتاب")))
    data = {"graphs": graphs}
    html = open(os.path.join(HERE, "player_template.html"), encoding="utf-8").read().replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
    out = os.path.join(HERE, "player.html")
    open(out, "w", encoding="utf-8").write(html)
    print("wrote", out, sum(l["question_count"] for g in graphs for l in g["lessons"]), "questions from", len(graphs), "book(s)")
