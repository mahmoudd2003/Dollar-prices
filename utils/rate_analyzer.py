# utils/rate_analyzer.py
# يحلل تغير سعر اليوم مقابل أمس لكل دولة بالاعتماد على data/rates_history.csv

from __future__ import annotations
import pandas as pd
from typing import Dict

# حدود حساسية الاتجاه (بالنسبة المئوية)
UP_THRESHOLD = 0.2     # ↑ إذا زاد عن +0.2%
DOWN_THRESHOLD = -0.2  # ↓ إذا أقل من -0.2%

def _direction_from_percent(pct: float) -> str:
    if pct > UP_THRESHOLD:
        return "up"
    if pct < DOWN_THRESHOLD:
        return "down"
    return "stable"

def get_rate_change(csv_path: str, country_label: str) -> Dict[str, float | str]:
    """
    يحسب نسبة تغير "سعر الشراء" لعملات دولة محددة بين أحدث يوم واليوم السابق.
    المتوقّع أن يحتوي csv على الأعمدة: [date, country, buy, sell]

    Returns:
      {
        "change": 0.0,           # نسبة التغير %
        "direction": "stable",   # up | down | stable
        "today_buy": float|None,
        "yesterday_buy": float|None
      }
    """
    try:
        df = pd.read_csv(csv_path, dtype={"country": str})
    except FileNotFoundError:
        return {"change": 0.0, "direction": "stable", "today_buy": None, "yesterday_buy": None}

    if df.empty or "country" not in df.columns:
        return {"change": 0.0, "direction": "stable", "today_buy": None, "yesterday_buy": None}

    # فلترة الدولة
    d = df[df["country"] == country_label].copy()
    if d.empty:
        return {"change": 0.0, "direction": "stable", "today_buy": None, "yesterday_buy": None}

    # تحويل التاريخ وترتيب تنازليًا
    # نتسامح مع صيغ مختلفة للتاريخ
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"]).sort_values("date", ascending=False)

    # إزالة التكرارات لنفس اليوم (نحتفظ بأحدث إدخال)
    d = d.drop_duplicates(subset=["date"], keep="first")

    if len(d) < 2:
        # لا يوجد أمس للمقارنة
        today_buy = float(d.iloc[0]["buy"]) if "buy" in d.columns else None
        return {"change": 0.0, "direction": "stable", "today_buy": today_buy, "yesterday_buy": None}

    today_row = d.iloc[0]
    yest_row  = d.iloc[1]

    try:
        today_buy = float(today_row["buy"])
        yest_buy  = float(yest_row["buy"])
    except Exception:
        return {"change": 0.0, "direction": "stable", "today_buy": None, "yesterday_buy": None}

    if yest_buy == 0:
        pct = 0.0
    else:
        pct = ((today_buy - yest_buy) / yest_buy) * 100.0

    pct_rounded = round(pct, 2)
    return {
        "change": pct_rounded,
        "direction": _direction_from_percent(pct_rounded),
        "today_buy": today_buy,
        "yesterday_buy": yest_buy
    }
