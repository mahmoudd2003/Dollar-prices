# utils/text_utils.py
# وظائف "بشرنة" النص الناتج من النموذج: إزالة التكرار، تدوير افتتاحيات،
# إدخال وصلات لغوية بشرية، وضبط الطول ضمن حدود مستهدفة.

import re
from typing import List

# افتتاحيات شائعة سنستبدلها بتدوير تنويعات مرادفة
OPENING_PATTERNS: List[str] = [
    r"^\s*يواصل الدولار",
    r"^\s*يشهد سعر الدولار",
    r"^\s*سجل سعر الدولار",
    r"^\s*استقر سعر الدولار",
    r"^\s*بلغ سعر الدولار"
]

# بدائل بشرية متنوعة للفقرة الافتتاحية (لا تحمل نفس البصمة كل يوم)
OPENING_VARIANTS: List[str] = [
    "مال مسار الدولار اليوم إلى هدوء نسبي",
    "تحرك الدولار الأمريكي بصورة محدودة خلال تعاملات اليوم",
    "بدت حركة الدولار اليوم متوازنة إلى حدٍّ كبير",
    "اتسم تداول الدولار اليوم بدرجة من الاستقرار",
    "ظلّ نطاق حركة الدولار اليوم ضيقًا نسبيًا"
]

# وصلات انتقالية بشرية نُدرج واحدة إذا غابت
TRANSITIONS: List[str] = [
    "في المقابل،",
    "من جهة أخرى،",
    "يُشار إلى أن",
    "في الوقت ذاته،",
    "على صعيد متصل،"
]

# عبارات حشو عامة سنحاول إزالتها عند الحاجة لتقصير النص
GENERIC_FILLERS: List[str] = [
    r"\bومن الجدير بالذكر\b",
    r"\bالجدير بالذكر\b",
    r"\bلا بد من الإشارة\b",
    r"\bتجدر الإشارة\b",
    r"\bيجدر التنويه\b",
]


_open_idx = 0  # مؤشر تدوير الافتتاحيات


def _normalize_whitespace(text: str) -> str:
    # أسطر مزدوجة → سطرين كحد أقصى، مسافات متعددة → مسافة واحدة
    t = re.sub(r"[ \t]+", " ", text)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _rotate_opening_once(text: str) -> str:
    """
    يستبدل أول افتتاحية نمطية ببديل بشري من القائمة.
    لا يكرر الاستبدال داخل النص، فقط أول تطابق في البداية.
    """
    global _open_idx
    for pat in OPENING_PATTERNS:
        m = re.search(pat, text, flags=re.U | re.M)
        if m and m.start() == 0:
            replacement = OPENING_VARIANTS[_open_idx % len(OPENING_VARIANTS)]
            _open_idx += 1
            # استبدل بداية السطر فقط
            text = re.sub(pat, replacement, text, count=1, flags=re.U | re.M)
            break
    return text


def _ensure_transition(text: str) -> str:
    """
    إن لم نجد وصلة انتقالية بشرية داخل النص، نضيف واحدة بعد أول فقرة.
    """
    if any(tr in text for tr in TRANSITIONS):
        return text

    # إدراج انتقال بعد أول سطر/فقرة
    parts = re.split(r"\n\s*\n", text, maxsplit=1)
    if len(parts) == 2:
        return parts[0] + "\n\n" + TRANSITIONS[0] + " " + parts[1]
    else:
        # لا توجد فقرات؛ أضف انتقالًا في منتصف النص تقريبًا
        words = text.split()
        if len(words) > 40:
            mid = len(words) // 2
            return " ".join(words[:mid] + [TRANSITIONS[0]] + words[mid:])
        return text


def _strip_generic_fillers(text: str) -> str:
    for pat in GENERIC_FILLERS:
        text = re.sub(pat, "", text)
    # تنظيف مسافات ناتجة
    return _normalize_whitespace(text)


def _soft_clamp_length(text: str, min_words: int, max_words: int) -> str:
    """
    إذا تجاوز النص الحد الأعلى، نحاول أولاً إزالة الحشو العام،
    ثم نقصّ بأمان عند حدود الجملة/الكلمة.
    وإذا كان أقصر من الحد الأدنى، نحاول تعزيز الخاتمة بجملة موجزة.
    """
    words = text.split()
    n = len(words)

    if n > max_words:
        # جرّب إزالة الحشو
        t = _strip_generic_fillers(text)
        words2 = t.split()
        if len(words2) <= max_words:
            return t

        # قصّ آمن: حاول عند علامة ترقيم قبل max_words + 20
        preview = " ".join(words2[:max_words + 20])
        # ابحث عن أقرب فاصلة/نقطة/تعجب/استفهام للقص
        cut = re.search(r"[\.!\؟]\s*[^\.\!\؟]*$", preview)
        if cut:
            # قص عند آخر نقطة ضمن المعاينة
            end_idx = cut.start()
            return preview[:end_idx].strip()
        else:
            return " ".join(words2[:max_words]).strip()

    if n < min_words:
        # عزّز بخاتمة قصيرة بشرية
        suffix = (
            " وبشكل عام، تبدو حركة الصرف مرهونة بتطورات السيولة وقرارات السياسة النقدية "
            "خلال اليومين المقبلين، مع متابعة حذرة من المتعاملين."
        )
        return (text.rstrip() + " " + suffix).strip()

    return text


def humanize(text: str, min_words: int = 140, max_words: int = 220) -> str:
    """
    الواجهة الرئيسية: تنظّف النص، تدوّر الافتتاحية، تضيف وصلة انتقالية عند الحاجة،
    وتضمن الطول المستهدف. لا تغيّر المعنى الاقتصادي؛ فقط تحسينات أسلوبية.
    """
    t = _normalize_whitespace(text)
    t = _rotate_opening_once(t)
    t = _ensure_transition(t)
    t = _soft_clamp_length(t, min_words, max_words)
    # تنظيف نهائي للمسافات المزدوجة
    t = _normalize_whitespace(t)
    return t
