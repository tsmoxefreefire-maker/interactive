# كيف تجرّب · خطوة خطوة

## المجلد فيه

```
interactive_questions/
├── HOW_TO_TRY_AR.md                    ← هاد الملف
├── INTERACTIVE_QUESTIONS_SUMMARY_AR.md ← الشرح الكامل للتاسك
├── question_factory/                   ← المصنع (الكود + صفحة العرض)
├── sample/plant_games.html             ← العيّنة (درس النبات بالرسومات)
└── new_structure/                      ← الجراف بالستركشر الجديد + شرحه
```

---

## ١. أسهل تجربة: افتح بالمتصفح (بدون أي تنصيب)

**أ. المصنع:** دبل كليك على
```
question_factory/player/player.html
```
- بتفتح على **👧 وضع الطالب**: «بذور» بترحّب، و**خريطة الدروس** (اللي لسا مش وقته **🔒**، وفي «🔓 افتحه هلأ»).
- فوق في زر **🔒** (اكبسه بيصير **🔓** وبيفتح كل إشي للتجربة قدام الفريق)، وزر **⚙️ وضع المهندس** (الملفات والأدلة)، وزر **🔊 الصوت**.
- اختار درس ← **رحلة الدرس**: كل مفهوم محطة ⭐.
- اختار مفهوم ← العب تحدياته (١٣ نوع): 🤥 مين الصادق · 🌷 وصّل · 🃏 الذاكرة · 🔤 ركّب الاسم · 👉👈 صح ولا غلط · 🌉 الجسر · 🚂 القطار · 🚪 الباب · 🗺️ الطرق · 🛗 المصعد · 👽 الدخيل · 🕵️ مين أنا · 🎚️ اضبط.
- **اسحب بإصبعك أو بالماوس** (أو اكبس إذا أسهل).
- **غلّط بقصد** وشوف: الأنف بيطول 🤥، الحجر بيوقع 💦، الباب بيضحك 🤭، القطة بتطرد 🐱.
- تحت: «ملف الدرس المحفوظ» و«الدليل لمحرك الأدلة».

**ب. العيّنة:** دبل كليك على
```
sample/plant_games.html
```
٦ أسئلة غنية بالرسومات: النبتة بتذبل وبتعيش.

> لازم يكون في إنترنت **بس للخطوط**. بدونه بتشتغل بخط عادي.

---

## ٢. تشغيل المصنع على جهازك (بايثون)

**الخطوة ١:** افتح Terminal (أو PyCharm Terminal) وادخل:
```
cd interactive_questions/question_factory
```
⚠️ إذا فكّيت الضغط وطلع مجلد جوا مجلد، ادخل للي فيه `main.py`.

**الخطوة ٢: الفحوصات**
```
python -m unittest discover -s tests -t . -v
```
✅ لازم تشوف: `Ran 87 tests` و `OK`.

**الخطوة ٣: شغّل المصنع**
```
python main.py plants_book_graph.json output_new
```
✅ لازم تشوف: `3 lessons, 52 questions` وتحتها كل مفهوم وتحدياته.

**الخطوة ٤: شوف اللي انحفظ**
```
output_new/index.json                    ← الفهرس
output_new/lessons/l_parts/questions.json ← أسئلة «أجزاء النبات» مقسمة على مفاهيمها
```

**الخطوة ٥: ابنِ صفحة العرض من جديد**
```
python player/build_player.py
```
وافتح `player/player.html`.

---

## ٣. جرّب على جراف ثاني

حط ملف جراف (بالستركشر الجديد أو القديم) جنب `main.py` وشغّل:
```
python main.py اسم_الملف.json output_test
```
المصنع **بيعرف لحاله** نوع الجراف.

---

## ٤.٥ كتاب الرياضيات (يثبت إنه لأي مادة) 📘
```
python main.py math_book_graph.json output_math
python player/build_player.py plants_book_graph.json output_new math_book_graph.json output_math
```
✅ بتطلع صفحة فيها **الكتابين** (العلوم والرياضيات).

## ٥. مع الموديل (Claude) 🤖 · اختياري

الموديل **بيعيد كتابة الكلام للأطفال** (السؤال، التلميحات، الجمل)، **بدون ما يغيّر الأجوبة**.

**الخطوة ١: مفتاح API**
من **Claude Console** (console.anthropic.com) ← Settings ← API Keys ← اعمل مفتاح.

**الخطوة ٢: حط المفتاح بالـ Terminal** (نفس الشباك اللي بتشغّل فيه):
```
PowerShell:   $env:ANTHROPIC_API_KEY="sk-ant-..."
cmd:          set ANTHROPIC_API_KEY=sk-ant-...
```
(اختياري: موديل أرخص) `$env:ANTHROPIC_MODEL="claude-haiku-4-5-20251001"`

**الخطوة ٣: شغّل المصنع مع الموديل**
```
python main.py plants_book_graph.json output_llm --llm
```
✅ لازم تشوف: `LLM: on` وتحت كل درس `LLM rewrote … texts`.

**الخطوة ٤: اعرضهم**
```
python player/build_player.py plants_book_graph.json output_llm
```
وافتح `player/player.html`.

⚠️ **انتبه:** المفتاح **سرّي**، لا تحطه بملف ولا تبعته لحدا. وكل تشغيلة **بتكلّف** شوي من رصيد الحساب.

## ٤. إذا صار خطأ

| المشكلة | الحل |
|---|---|
| `python` مش معروف | جرّب `py` بدل `python` |
| `No such file` | إنت مش بالمجلد الصح: لازم تكون جنب `main.py` |
| الصفحة بدون ألوان الخط | عادي، الخطوط من الإنترنت |
| `ما في مفتاح` مع `--llm` | ما حطيت `ANTHROPIC_API_KEY` بنفس الشباك (الخطوة ٢) |
| `Claude API error 401` | المفتاح غلط |
| `cannot reach the Claude API` | ما في إنترنت، أو الشبكة مسكّرة |
