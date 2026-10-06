# الأسئلة التفاعلية · Interactive Questions 🌱

**المصنع (Generator)** بيقرأ **أي جراف** (أي مادة)، ولكل درس **ولكل مفهوم** بيولّد **تحديات تفاعلية شبه ألعاب**، بيفحصها، وبيحفظها **JSON** مع الدرس.
**المشغّل (Player / Interpreter)** صفحة HTML + JavaScript بتقرأ الـ JSON وبترسم كل سؤال **لعبة SVG تفاعلية** (كمبيوتر وتلفون).

**▶️ جرّب الألعاب:** [`index.html`](index.html) (٣ كتب: العلوم والرياضيات والتاريخ)

## ابدأ من هون
| | |
|---|---|
| [`PROJECT_OVERVIEW_AR.md`](PROJECT_OVERVIEW_AR.md) ⭐ | **الشرح الكامل بملف واحد**: الفكرة، المصنع والمشغّل، كيف بيشتغل، الديناميك، الرسومات، الفحوصات |
| [`ENGINEER_BRIEF_AR.md`](ENGINEER_BRIEF_AR.md) | للمهندس: الطلب ← وين موجود |
| [`DYNAMIC_AR.md`](DYNAMIC_AR.md) | هل هو ديناميك؟ (آه، ومجرّب) |
| [`HOW_TO_TRY_AR.md`](HOW_TO_TRY_AR.md) | خطوات التشغيل |
| [`question_factory/`](question_factory) | **الكود** + الفحوصات (`tests/`، `tests_browser/`) + `CODE_GUIDE_AR.md` + `CHANGES_AR.md` |
| [`new_structure/`](new_structure) | الجرافين التجريبيين (علوم ورياضيات) |

## التشغيل
```
cd question_factory
python -m unittest discover -s tests -t . -v        # 95 tests OK
python main.py plants_book_graph.json output_new     # العلوم: 3 دروس، 52 تحدي
python main.py math_book_graph.json output_math      # الرياضيات: 4 دروس، 39 تحدي (نفس الكود)
python player/build_player.py plants_book_graph.json output_new math_book_graph.json output_math
```
**أي جراف جديد:** `python main.py جرافك.json output_x` ← بدون تعديل بالكود.
**مع الموديل (اختياري):** حط `ANTHROPIC_API_KEY` **بالـ Terminal بس (مش بملف!)** وزيد `--llm`.

## بأرقام
**١٤** نوع لعبة · **٣ مواد بنفس الكود** · **كتاب ضخم** (٢٤٠ مفهوم) بنص ثانية · **٩٥** فحص كود + فحوصات متصفح
