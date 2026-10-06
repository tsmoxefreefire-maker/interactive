# مصنع الأسئلة التفاعلية · Interactive Question Factory

**الطلب:** لكل درس بالجراف ← **لكل مفهوم جوا الدرس** ← ولّد أسئلة تفاعلية ← احفظها مع الدرس.

**بيقرأ الستركشر الجديد:** كتاب ← وحدة ← Topic ← درس ← مفهوم (جداول عصام). وبيقرأ القديم كمان.

## التشغيل
```bash
python main.py plants_book_graph.json output_new      # المصنع
python -m unittest discover -s tests -t . -v          # 95 فحص
python player/build_player.py                         # صفحة العرض: player/player.html

# مع الموديل (Claude) يحسّن الصياغة للأطفال، بدون ما يغيّر الأجوبة:
#   حط ANTHROPIC_API_KEY أول (الطريقة بـ HOW_TO_TRY_AR.md)
python main.py plants_book_graph.json output_llm --llm
python player/build_player.py plants_book_graph.json output_llm
```
بايثون عادي بدون مكتبات.

## الناتج
```
output_new/
├── index.json                       ← فهرس: كل درس، كل مفهوم، كم سؤال
└── lessons/<الدرس>/questions.json   ← أسئلة الدرس مقسمة على مفاهيمه
```
**3 دروس · 13 مفهوم · 52 تحدي · 13 نوع تفاعل (كبس وسحب بالإصبع) · شخصية «بذور» 🌱 · جو حسب الدرس · وضع الطالب ووضع المهندس.**

الشرح بالعربي: `CODE_GUIDE_AR.md` · الشرح الكامل للتاسك: `INTERACTIVE_QUESTIONS_SUMMARY_AR.md` · شو تعدّل: `CHANGES_AR.md`
