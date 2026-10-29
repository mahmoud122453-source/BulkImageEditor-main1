# دليل التشغيل — BulkImageEditor

هذا الدليل يصف التشغيل الذي تم التحقق منه على هذا الجهاز. الأوامر نُفذت من جذر المشروع:

`D:\project_lv3\BulkImageEditor-main`

## البيئة التي تم فحصها

| البند | القيمة الفعلية |
| --- | --- |
| نظام التشغيل | Windows 10 (10.0.19045) |
| Python | 3.12.0 |
| pip | 26.1 |
| Pillow | 12.2.0 |
| PyQt5 | 5.15.11 (Qt 5.15.2) |
| Matplotlib | 3.8.2 |
| Tkinter | مثبت، والبرنامج لا يستخدمه |

لا يوجد ملف `requirements.txt`. عند بدء الفحص لم تكن هناك بيئة افتراضية داخل المشروع، والمكتبات المذكورة كانت مثبتة في Python العام. قسم البيئة الافتراضية أدناه يعيد إنشاء بيئة محلية ويُثبت هذه المكتبات فقط.

## ما يحتاجه كل مدخل

- سطر الأوامر `main.py`: Pillow فقط.
- نافذة البرنامج: Pillow وPyQt5 وMatplotlib.
- Matplotlib لا يرسم صورًا هنا. النافذة تستخدمه لقراءة خطوط النظام من النوع `ttf`.

## التثبيت

من جذر المشروع. أُنشئت `.venv` على هذا الجهاز، ثم نُفّذ التثبيت. المحاولة الأولى انقطعت بـ `ReadTimeoutError` أثناء تنزيل PyQt5. نجحت الإعادة مع مهلة أطول:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --default-timeout 120 pillow PyQt5 matplotlib
```

النسخ التي ثبتت داخل `.venv`: Pillow 12.3.0، وPyQt5 5.15.11، وMatplotlib 3.11.2. Matplotlib يجلب حزمًا إضافية مثل `numpy`، والبرنامج لا يستوردها مباشرة.

فحوصات المعالجة الأولى نُفذت بمفسر النظام قبل إنشاء البيئة، وكانت لديه Pillow 12.2.0 وMatplotlib 3.8.2. إعادة التحقق النهائية استخدمت مفسر `.venv`.

التفعيل الاختياري في PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

إذا منع PowerShell التفعيل، استدعِ المفسر مباشرة:

```powershell
.\.venv\Scripts\python.exe main.py --help
```

مجلد `.venv` مذكور أصلًا في `.gitignore`.

## هيكل المجلدات

```text
BulkImageEditor-main/
  main.py                          مدخل سطر الأوامر
  README.md
  LICENSE                          GPL-3.0، حقوق NullPointerExcy سنة 2024
  src/
    resizer.py                     تصغير الصور مع حفظ النسبة
    watermark.py                   علامة مائية نصية أو صورية
    ui/bulk_image_editor_ui.py     نافذة PyQt5
  images/input|output|watermark/   مجلدات فارغة فيها .gitkeep فقط
  resources/git/                   لقطات الواجهة وأمثلة README
  test_data/                       صور الاختبار التي أُنشئت لهذا الفحص
```

لا تشغّل المعالجة على Desktop أو Downloads أو Documents. استخدم `test_data` أو مجلدات تنشئها أنت داخل المشروع.

كتلة `if __name__ == "__main__"` في `src/resizer.py` و`src/watermark.py` تستخدم المسار النسبي `../images/input`. عند التشغيل من جذر المشروع يصبح هذا المسار خارج المشروع، وقد يلمس مجلدًا غير مقصود. لا تستخدم هذين الملفين كأمر تشغيل.

## أمر سطر الأوامر

المساعدة:

```powershell
python main.py --help
```

تم تشغيله بنجاح. البرنامج يطلب `--input_path` و`--output_path`. بدون هذين الخيارين يخرج برمز `2` ولا يفتح نافذة.

مثال مُتحقق: تصغير مجلد اختبار إلى حد أقصى 400×400:

```powershell
python main.py --input_path test_data\input_cli --output_path test_data\output\cli_resize --resize --max_width 400 --max_height 400
```

النتيجة التي قيست: `large.jpg` أصبح 400×300، و`small.jpg` بقي 120×90، و`photo.png` نُسخ بعد المعالجة. رمز الخروج `0`.

علامة مائية نصية:

```powershell
python main.py --input_path test_data\input_cli --output_path test_data\output\cli_wm --add_watermark --watermark_text CLI --position center --alpha 1 --text_color #ffffff
```

في PowerShell ضع اللون بين علامتي اقتباس حتى لا يُفسر `#`:

```powershell
python main.py --input_path test_data\input_cli --output_path test_data\output\cli_wm --add_watermark --watermark_text CLI --position center --alpha 1 --text_color "#ffffff"
```

تصغير ثم علامة مائية صورية على ناتج التصغير:

```powershell
python main.py --input_path test_data\input_cli --output_path test_data\output\cli_both --resize --max_width 500 --max_height 500 --add_watermark --watermark_image test_data\watermark\logo.png --position top-left --alpha 1
```

تمت العملية: الصورة الكبيرة أصبحت 500×375، وبكسل الشعار في أعلى اليسار كان أحمر.

`--font_size` و`--font_family` غير موجودين في `main.py`. تمريرهما ينهي البرنامج برمز `2`:

```text
unrecognized arguments: --font_size 40
```

سطر الأوامر يثبت حجم الخط عند 30 وملف الخط عند `arial.ttf`.

إذا لم تُمرر `--resize` ولا `--add_watermark` يخرج البرنامج برمز `0` دون كتابة صور.

## أمر النافذة

من جذر المشروع:

```powershell
python -m src.ui.bulk_image_editor_ui
```

تم التحقق: العملية تبقى تعمل، وعنوان النافذة `Bulk Image Editor`.

هذا الأمر يفشل ولا تظهر نافذة:

```powershell
python .\src\ui\bulk_image_editor_ui.py
```

الخطأ الفعلي:

```text
ModuleNotFoundError: No module named 'src'
```

النافذة لا تحتوي معاينة ولا شريط تقدم. الرسائل تُطبع في الطرفية التي شغّلت الأمر. أغلق النافذة من زر الإغلاق لإنهاء العملية.

النافذة لا تجمع التصغير والعلامة المائية في ضغطة واحدة. تحديد أحدهما يلغي الآخر. إلغاء التحديد يفعّل الخيار الآخر.

## مكان الناتج

الملف الناتج يحمل اسم الملف الأصلي نفسه داخل مجلد الإخراج. لا توجد لاحقة جديدة. تشغيل العملية مرة ثانية يستبدل الملف الموجود.

التصغير يحافظ على نمط الصورة. ملف PNG الشفاف يبقى `RGBA`.

العلامة المائية تحوّل الناتج إلى `RGB` قبل الحفظ، حتى لو كان المصدر PNG شفافًا. الشفافية الأصلية تُحذف، وتبقى قيم الأحمر والأخضر والأزرق التي كانت تحتها.

## إجراء الاختبار

صور الاختبار مولَّدة داخل `test_data` وليست صورًا شخصية. لإعادة الفحوصات:

```powershell
python test_data\run_processing_tests.py
```

الملخص يُكتب إلى `test_data\results.json`. المجلدات المهمة:

- `test_data\input`: JPG صغير وكبير، PNG، PNG شفاف، صورة عريضة، صورة طويلة، صورة مربعة.
- `test_data\watermark\logo.png`: شعار أحمر 100×100.
- `test_data\output\...`: ناتج كل حالة.

## أخطاء شائعة

| ما يحدث | السبب الذي ظهر عند التشغيل |
| --- | --- |
| `the following arguments are required: --input_path, --output_path` | تشغيل `main.py` بدون المسارين. رمز الخروج 2. |
| `ModuleNotFoundError: No module named 'src'` | تشغيل ملف الواجهة مباشرة بدل `python -m`. |
| `FileNotFoundError` ومجلد الإخراج فارغ وقد أُنشئ | مجلد الإدخال غير موجود. التصغير ينشئ الإخراج أولًا ثم يفشل عند قراءة الإدخال. |
| `NotADirectoryError` | تمرير ملف صورة واحد إلى `--input_path`. الكود يقرأ مجلدًا. |
| `invalid choice` لـ `--position` | القيمة خارج: `top-left` و`top-right` و`bottom-left` و`bottom-right` و`center`. |
| `invalid int value` | `--max_width` أو `--max_height` ليس عددًا صحيحًا. |
| `UnidentifiedImageError` وتتوقف الدفعة | ملف بامتداد صورة ومحتواه تالف. الملفات التي نُسخت قبله تبقى، والملفات التالية لا تُعالج. |
| `ValueError: Invalid hex color format` | لون النص ليس `#RRGGBB`. لا يُحفظ شيء من هذه الدفعة. |
| `ValueError: height and width must be > 0` | علامة مائية صورية على صورة عرضها أقل من 10 بكسل. العرض المحسوب يصبح 0. |
| `ZeroDivisionError` أو `scale must be > 0` | حد التصغير `0` أو قيمة سالبة. الواجهة تمنع ذلك بمدى 100–5000، والدالة نفسها لا تمنعه. |
| `FileNotFoundError` لملف الشعار | `--watermark_image` يشير إلى ملف غير موجود. تتوقف الدفعة ولا يُحفظ ناتج. |
| الخط غير موجود | `ImageFont.truetype` يفشل، ثم يُستخدم `ImageFont.load_default()`. المعالجة تكمل. |
| لا تظهر صور | لم يُمرر `--resize` ولا `--add_watermark`، أو الامتداد ليس `png` أو `jpg` أو `jpeg`. |

## ما لا يدعمه المشروع

- امتدادات `bmp` و`gif` و`webp` تُتخطى بصمت.
- لا يوجد تكبير. الصورة الأصغر من الحد تُحفظ بحجمها.
- لا يوجد خيار عرض فقط أو ارتفاع فقط. القيمة دائمًا صندوق `(أقصى عرض، أقصى ارتفاع)`.
- لا يوجد قص إلى عرض وارتفاع محددين مع تشويه النسبة.
- سطر الأوامر لا يغيّر حجم الخط ولا عائلة الخط.
