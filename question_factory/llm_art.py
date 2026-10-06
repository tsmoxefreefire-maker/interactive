"""The LLM as an ILLUSTRATOR: a drawing (SVG body) for every concept that the player's library cannot draw.

The player adds the SAME face to every body (eyes that blink and follow, moods), so every subject looks like one family.
Every drawing is checked before it is kept: only simple shapes, no text, no scripts, no links, small size.
Anything that fails → the generic character (the game still works).
"""
import json
import xml.etree.ElementTree as ET

ALLOWED_TAGS = {"g", "path", "circle", "ellipse", "rect", "polygon", "polyline", "line"}
ALLOWED_ATTRS = {"d", "cx", "cy", "r", "rx", "ry", "x", "y", "width", "height", "points", "x1", "y1", "x2", "y2",
                 "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "opacity", "transform"}
FORBIDDEN_IN_VALUES = ("url(", "javascript", "<", "&", "expression", "@import", "data:")
ANIMS = ("bob", "sway", "wobble", "bounce", "wiggle", "leaf", "wind", "drip")
MAX_CHARS, MAX_ELEMENTS = 6000, 40

SYSTEM = """You draw cute, simple characters for a children's learning game, as SVG shapes.
For each concept, draw ONE body that clearly shows the concept, in a 100x100 box (coordinates 0..100).
Style: flat bright colours, outline stroke "#3b2a1a" width 2.6, round joins. Only these elements: path, circle, ellipse, rect, polygon, polyline, line, g.
Do NOT draw a face (the game adds the face). Leave a plain filled area for the face and give its centre and size.
No text, no images, no gradients, no styles, no scripts, no links.
Return ONLY one JSON object: {"<concept id>": {"body": "<svg shapes>", "face": {"x": 50, "y": 55, "s": 0.8}, "anim": "bob"}}.
"anim" is one of: bob, sway, wobble, bounce, wiggle, leaf, wind, drip. "s" is between 0.4 and 1.0."""


def clean_svg(body: str):
    """Return the drawing if it is safe and simple, else None."""
    if not isinstance(body, str) or not body.strip() or len(body) > MAX_CHARS:
        return None
    try:
        root = ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{body}</svg>')
    except ET.ParseError:
        return None
    count = 0
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if el is root:
            continue
        count += 1
        if tag not in ALLOWED_TAGS or (el.text or "").strip():
            return None
        for k, v in el.attrib.items():
            k = k.split("}")[-1]
            if k not in ALLOWED_ATTRS or any(bad in v.lower() for bad in FORBIDDEN_IN_VALUES):
                return None
    if count == 0 or count > MAX_ELEMENTS:
        return None
    return body.strip()


def clean_face(face):
    try:
        x, y, s = float(face["x"]), float(face["y"]), float(face["s"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (15 <= x <= 85 and 15 <= y <= 85 and 0.4 <= s <= 1.0):
        return None
    return {"x": round(x, 1), "y": round(y, 1), "s": round(s, 2)}


def name_key(text: str) -> str:
    """The same concept in two books has two ids but the same name: «الكسور» = «كسور»."""
    t = " ".join((text or "").strip().lower().split())
    return t[2:] if t.startswith("ال") and len(t) > 4 else t


def load_library(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            lib = json.load(f)
        return lib if isinstance(lib, dict) else {}
    except (OSError, ValueError):
        return {}


def save_library(path: str, library: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(library, f, ensure_ascii=False, indent=1)


def _attach(records: list, art: dict) -> None:
    for rec in records:
        rec["art"] = dict(art)
        for cid in art:
            rec["icons"][cid] = "art:" + cid


def use_library(g, records: list, art_icons: set, library: dict) -> dict:
    """No LLM needed: concepts without their own picture get the drawing made earlier for the same NAME (any book)."""
    icons = records[0]["icons"] if records else {}
    art = {}
    for cid, icon in icons.items():
        if icon in art_icons:
            continue
        d = library.get(name_key(g.concepts[cid].text))
        if isinstance(d, dict) and clean_svg(d.get("body")) and clean_face(d.get("face")):
            art[cid] = {"body": d["body"], "face": d["face"], "anim": d.get("anim") if d.get("anim") in ANIMS else "bob"}
    _attach(records, art)
    return art


def draw_missing(g, records: list, art_icons: set, llm_generate, library: dict = None, chunk: int = 8) -> dict:
    """Ask the LLM to draw every concept that still has no picture; keep each drawing in the shared library
    (by name, status «needs_review»), so it is drawn ONCE and reused by every lesson, every book and every later run."""
    library = {} if library is None else library
    icons = records[0]["icons"] if records else {}
    art = use_library(g, records, art_icons, library)
    missing = [cid for cid, icon in icons.items() if icon not in art_icons and cid not in art]
    rejected, failed = 0, 0
    for i in range(0, len(missing), chunk):
        part = missing[i:i + chunk]
        ask = {cid: {"name": g.concepts[cid].text, "meaning": g.concepts[cid].description[:160]} for cid in part}
        try:
            reply = llm_generate(SYSTEM, json.dumps(ask, ensure_ascii=False))
            start, end = reply.find("{"), reply.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("no JSON object")
            drawn = json.loads(reply[start:end + 1])
        except Exception:
            failed += len(part)
            continue
        for cid in part:
            item = drawn.get(cid) if isinstance(drawn, dict) else None
            body = clean_svg(item.get("body")) if isinstance(item, dict) else None
            face = clean_face(item.get("face")) if isinstance(item, dict) else None
            if body and face:
                art[cid] = {"body": body, "face": face, "anim": item.get("anim") if item.get("anim") in ANIMS else "bob"}
                library[name_key(g.concepts[cid].text)] = dict(art[cid], name=g.concepts[cid].text, status="needs_review")
            else:
                rejected += 1
    _attach(records, art)
    for rec in records:
        rec.setdefault("llm", {})["art"] = {"asked": len(missing), "drawn": len(art), "rejected": rejected, "failed": failed}
    return art
