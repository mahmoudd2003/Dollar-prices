# utils/meta_utils.py
# توليد عناوين ووصف Meta واقعية وقصيرة عبر LLM + اختيار أفضل خيار وفق الطول والكلمة المفتاحية.

import json
import re
from typing import Tuple, List
from .call_llm import call_llm

MAX_TITLE = 60
MAX_DESC = 150

def _pick_best(candidates: List[str], max_len: int, keyword: str = "") -> str:
    """
    يختار أفضل مرشح وفق:
    1) عدم تجاوز الطول.
    2) احتواء الكلمة المفتاحية إن وُجدت.
    3) الأقصر أفضل (للـ SERP).
    """
    if not candidates:
        return ""

    def score(s: str) -> tuple:
        over = len(s) > max_len
        kw = 0 if (keyword and keyword in s) else 1  # 0 أفضل (يحتوي الكلمة)
        return (over, kw, len(s))

    ranked = sorted((s.strip() for s in candidates if s.strip()), key=score)
    return ranked[0]

def _fallback_title(country_name: str, iso_date: str) -> str:
    return f"سعر الدولار اليوم في {country_name} – تحديث {iso_date}"

def _fallback_desc(currency_name: str, iso_date: str) -> str:
    return f"آخر تحديث لسعر الدولار مقابل {currency_name} بتاريخ {iso_date}."

def _safe_json_loads(raw: str) -> dict:
    """
    يحاول قراءة JSON حتى لو أعاد النموذج نصًا مع سطور إضافية.
    """
    try:
        return json.loads(raw)
    except Exception:
        # محاولة استخراج كتلة JSON من النص
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}

def generate_meta(country_name: str,
                  iso_date: str,
                  currency_name: str,
                  buy: float,
                  sell: float,
                  model: str) -> Tuple[str, str]:
    """
    يعيد (title, description) وفق أفضل اختيار من 3 اقتراحات من LLM،
    مع بدائل احتياطية إذا فشل التحليل أو تجاوزت الحدود.
    """
    keyword = f"سعر الدولار اليوم في {country_name}"
    meta_prompt = f"""
اقترح 3 عناوين عربية قصيرة (≤{MAX_TITLE} حرفًا) و3 أوصاف Meta (≤{MAX_DESC} حرفًا)
لمقال عن "{keyword}" بتاريخ {iso_date}.
أدرج في أحد العناوين سعر الشراء {buy} وسعر البيع {sell} بطريقة طبيعية دون تهويل.
أعد الإجابة بصيغة JSON بهذا الشكل:
{{"titles": ["...","...","..."], "descriptions": ["...","...","..."]}}
لا تضف أي نص آخر خارج JSON.
"""
    raw = call_llm(meta_prompt, model=model, temperature=0.6)
    data = _safe_json_loads(raw)

    titles = data.get("titles", []) if isinstance(data, dict) else []
    descs  = data.get("descriptions", []) if isinstance(data, dict) else []

    title = _pick_best(titles, MAX_TITLE, keyword=keyword) or _fallback_title(country_name, iso_date)
    desc  = _pick_best(descs,  MAX_DESC)                 or _fallback_desc(currency_name, iso_date)

    # ضمان الحدود النهائية
    title = title[:MAX_TITLE]
    desc  = desc[:MAX_DESC]

    return title, desc
