# فحوصات المتصفح (Playwright)

بتفتح **صفحة الألعاب** بمتصفح حقيقي وبتلعب فيها **زي الطالب** (كبس، سحب، سحب بالإصبع على تلفون).

## مرة وحدة: التنصيب
```
pip install playwright
python -m playwright install chromium
```

## قبل الفحص: ابنِ الصفحة (العلوم أول)
```
cd question_factory
python main.py plants_book_graph.json output_new
python main.py math_book_graph.json output_math
python player/build_player.py plants_book_graph.json output_new math_book_graph.json output_math
```

## الفحوصات
| الأمر | بيفحص |
|---|---|
| `python tests_browser/test_games.py` | كل التحديات بتنحل + فحوصات الملاحظات (٥ دقايق تقريباً) |
| `python tests_browser/test_games.py "" solve` | **بس** حل كل التحديات |
| `python tests_browser/test_order.py` | الترتيب والأقفال والانتقال التلقائي |
| `python tests_browser/test_touch.py` | السحب **بالإصبع** على شاشة تلفون |
| `python tests_browser/test_physics.py` | الفيزياء (السيارة، الإشي الممسوك…) |
| `python tests_browser/test_leave.py` | تبلش كل لعبة وتغلط وتتركها بالنص ← بلا أخطاء |

✅ كل سطر بيطلع **✅** أو **❌**، وبالآخر `JS errors: none`.
الصور بتنحفظ بمجلد `tests_browser/shots/`.
