# utils/fetch_utils.py
# جلب مصدر الدولة + حفظ السجل مع إجبار reload لتطبيق التعديلات فورًا.

import importlib
import os
from datetime import date
from typing import Dict, Any, Optional
import pandas as pd

DATA_DIR = "data"
HISTORY_CSV = os.path.join(DATA_DIR, "rates_history.csv")

def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "articles"), exist_ok=True)

def _round_num(x: Optional[float], ndigits: int = 6) -> Optional[float]:
    try:
        return round(float(x), ndigits)
    except Exception:
        return None

def get_country_rate(country_code: str) -> Dict[str, Any]:
    try:
        module = importlib.import_module(f"data_sources.{country_code}")
        module = importlib.reload(module)  # 🔁 مهم جدًا
    except ModuleNotFoundError as e:
        raise RuntimeError(f"لا يوجد مصدر بيانات للدولة: {country_code} ({e})")
    if not hasattr(module, "get_rate"):
        raise RuntimeError(f"ملف المصدر {country_code} لا يحتوي الدالة get_rate().")

    data = module.get_rate()
    if not isinstance(data, dict):
        raise RuntimeError(f"الدالة get_rate() في {country_code} يجب أن تعيد dict.")

    data.setdefault("country", country_code)
    data.setdefault("currency", "")
    data["buy"] = _round_num(data.get("buy"))
    data["sell"] = _round_num(data.get("sell"))
    if data["buy"] is None or data["sell"] is None:
        raise RuntimeError(f"قيم الأسعار غير صالحة للدولة {country_code}: {data}")
    return data

def save_rate_to_csv(data: Dict[str, Any], csv_path: str = HISTORY_CSV) -> None:
    _ensure_dirs()
    row = {"date": date.today().isoformat(), "country": data.get("country", ""), "buy": data.get("buy"), "sell": data.get("sell")}
    if not os.path.exists(csv_path):
        pd.DataFrame([row], columns=["date", "country", "buy", "sell"]).to_csv(csv_path, index=False)
        return
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        df = pd.DataFrame(columns=["date", "country", "buy", "sell"])
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(csv_path, index=False)
