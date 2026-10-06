"""The closed list of question templates. Every question is about ONE concept (Omar's decision)."""
import config

# Field -> type for each template. The validator rejects anything else (closed schema).
SCHEMAS = {
    "meaning":  {"target": str, "options": list, "answer": str},       # pick the right meaning of the concept
    "sequence": {"target": str, "order": list},                         # put the concept in its place in a prerequisite chain
    "prereq":   {"target": str, "correct": list, "options": list},     # what must be known BEFORE the concept
    "unlocks":  {"target": str, "route": list, "junctions": list, "hints": list, "whys": list},  # a journey: who needs this? then who needs that?
    "match":    {"target": str, "pairs": list},                        # connect the concept and its neighbours to their meanings
    "sort":     {"target": str, "before": list, "after": list},        # sort related concepts into "before it" / "after it"
    "adjust":   {"target": str, "factor": dict},                       # move a slider to the right amount (needs numbers in the graph)
    "memory":   {"target": str, "pairs": list},                        # flip cards and pair each concept with its meaning
    "spell":    {"target": str, "word": str, "clue": str},             # build the concept's name from its letters
    "true_false": {"target": str, "statements": list},                 # swipe each card: true or false
    "fix_chain": {"target": str, "chain": list, "wrong_index": int, "wrong": str, "options": list},  # find and fix the wrong link
    "odd_one_out": {"target": str, "family": list, "intruder": str, "intros": dict},   # which one is not from the family
    "who_am_i": {"target": str, "clues": list, "options": list},       # guess the concept from clues, the earlier the better
    "predict":  {"target": str, "options": list, "answer": int, "affected": list, "unaffected": list},  # what happens if it disappears?
}
COMMON = {"template": str, "difficulty": str, "question": str, "how": str, "solution": list,
          "concepts": list}   # which concepts this question tests; the first one is the concept it belongs to

QUESTION_TEXT = {
    "meaning":  ("شو معنى «{name}»؟", "اسحب الاسم للفقاعة اللي فيها المعنى الصح (أو اكبس عليها)."),
    "sequence": ("ابنِ جسر «{name}»", "ركّب قطع الجسر بالترتيب من الأساس (اسحب أو اكبس)، وبعدين «🚗 يلا!» وخلّي البذرة تقطع."),
    "prereq":   ("شو لازم تعرف قبل «{name}»؟", "اسحب المفاتيح الصح للباب (أو اكبس عليها): كل مفهوم لازم قبله بيفتح قفل."),
    "unlocks":  ("مين بيحتاج «{name}»؟ 🚶 رحلة", "بكل مفترق اختار مين بيحتاج اللي إنت عنده، وامشي لعنده. انتبه من ثعلوب 🦊، والبومة 🦉 بتساعدك (بنجمة)."),
    "match":    ("وصّل «{name}» وجيرانه بمعانيهم", "اسحب خط من كل مفهوم لمعناه (أو اكبس على المفهوم وبعدين على المعنى)."),
    "sort":     ("مصعد «{name}»: مين قبله ومين بعده؟", "حط كل مفهوم بطابق: تحت = قبله، فوق = بعده. لما تخلص اكبس «ثبّت 🔒»."),
    "adjust":   ("اضبط «{name}» صح", "اقرأ المعلومة، حط توقّعك على الشريط، وبعدين «جرّب» وشوف النبتة."),
    "memory":   ("بطاقات الذاكرة: «{name}» وجيرانه", "اقلب بطاقتين: إذا المفهوم ومعناه، بيضلّوا مفتوحين."),
    "spell":    ("ركّب اسم المفهوم", "اقرأ المعنى، واسحب الحروف لمكانها (أو اكبس عليها بالترتيب)."),
    "true_false": ("صح ولا غلط؟ عن «{name}»", "طعمي كل جملة للوحش الصح: «صح» ولا «غلط» (اسحبها لتمّه أو اكبس عليه)."),
    "fix_chain": ("في عربة غلط بقطار «{name}»!", "العربات بالترتيب: كل عربة بتيجي بعد اللي قدامها. لاقي الغلط واكبس عليها، وبعدين حط الصح مكانها."),
    "odd_one_out": ("مين الدخيل؟", "كل واحد بيعرّف عن حاله. واحد بس مش من المجموعة: شدّه لبرا!"),
    "who_am_i": ("مين أنا؟ 🕵️", "اقرأ التلميح واحزر مين أنا!"),
    "predict":  ("شو بيصير لو اختفى «{name}»؟", "توقّع أول، وبعدين شوف شو بيصير للباقين."),
}


def blank(template: str, name: str) -> dict:
    q, how = QUESTION_TEXT[template]
    return {"template": template, "difficulty": config.DIFFICULTY[template], "question": q.format(name=name), "how": how,
            "solution": [], "concepts": []}
