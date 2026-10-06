"""Every number the factory uses, in one place (proposals unless marked)."""

# Omar's decision: EVERY CONCEPT has its own questions.
# A concept needs at least this many questions, otherwise the factory warns (coverage check)
MIN_QUESTIONS_PER_CONCEPT = 2

# "What does it mean?": how many wrong meanings next to the right one
MEANING_DISTRACTORS = 3

# Sequence around the concept: shortest / longest chain worth asking about
SEQUENCE_MIN_LENGTH = 2
SEQUENCE_MAX_LENGTH = 5

# "What comes before / after?": how many wrong options next to the right ones
PREREQ_DISTRACTORS = 3

# Short meanings keep the cards readable
DESCRIPTION_MAX_WORDS = 16

# Same seed -> same questions (needed for tests and review)
SEED = 7

# Most questions one concept gets (the factory picks a varied mix so the student does not get bored)
MAX_QUESTIONS_PER_CONCEPT = 4

# Match: the concept + this many neighbours, each with its meaning
MATCH_NEIGHBOURS = 2

# Sort before/after: most concepts in each basket
SORT_MAX_PER_SIDE = 3

# The only templates the factory may produce (closed list), all built around ONE concept.
TEMPLATES = ("meaning", "match", "memory", "spell", "true_false",            # what the concept MEANS (memorise)
             "sequence", "fix_chain", "prereq", "unlocks", "sort",           # how it LINKS to others (understand)
             "odd_one_out", "who_am_i", "predict",                             # meaning + links, cause and effect
             "adjust")                                                         # numbers (slider) — numeric subjects only
DIFFICULTY = {"meaning": "easy", "match": "easy", "memory": "easy", "spell": "easy", "true_false": "easy",
              "sequence": "mid", "fix_chain": "mid", "prereq": "mid", "unlocks": "mid", "sort": "mid",
              "odd_one_out": "mid", "who_am_i": "mid", "predict": "mid", "adjust": "hard"}

# Variety (so the student does not get bored): the first question of a concept is a "meaning" one,
# chosen in turn from this list; the rest come from the "links" list, rotating from concept to concept.
MEANING_KINDS = ("meaning", "match", "true_false", "spell", "memory")
LINK_KINDS = ("predict", "who_am_i", "sort", "fix_chain", "prereq", "odd_one_out", "unlocks", "sequence")

# The slider game ("adjust", like the magnet example) only makes sense where the BOOK gives numbers:
# numeric subjects (maths, physics, chemistry) AND real quantities in the graph. Memorise/understand subjects never get it.
NUMERIC_SUBJECTS = ("mathematics", "math", "physics", "chemistry", "رياضيات", "فيزياء", "كيمياء")
# The same kind may appear in at most this share of a lesson's concepts (the bridge was in every concept)
MAX_KIND_SHARE = 0.5

# true/false: how many statement cards
TRUE_FALSE_CARDS = 4
# who am I: how many clues and how many suspects
WHO_CLUES = 3
WHO_SUSPECTS = 4
# journey (unlocks): longest trip and wrong roads at each crossroads
JOURNEY_MAX_STEPS = 3
JOURNEY_WRONG_ROADS = 3      # 3 wrong + 1 right: the fox always stands on a wrong one, so 3 choices stay
# memory: concept + this many neighbours (pairs of cards)
MEMORY_NEIGHBOURS = 2

# Each lesson gets a "skin" that fits it (same game, different look). Closed list.
THEMES = ("garden", "default")
THEME_KEYWORDS = {"garden": ("نبات", "نباتات", "plant", "plants", "زهرة", "بذرة")}

# Every generated lesson waits for a teacher before students see it (Brilliant: human review)
DEFAULT_STATUS = "needs_review"
