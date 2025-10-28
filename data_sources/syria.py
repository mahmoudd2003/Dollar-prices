# data_sources/syria.py
# جلب سعر الدولار مقابل الليرة السورية (USD→SYP)
# نعتمد على API عام كخيار أول، مع احتياطي ثابت معقول في حال تعذّر الجلب.
# ملاحظة: السوق السورية تعتمد على أسعار موازية متقلبة؛ هنا نعرض معدلًا وسطيًا آمنًا للتحرير.

from __future__ import annotations
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CurrencyReporter/1.0; +https://example.com)"
}

def _from_exchangerate_host() -> float | None:
    """
    مصدر مجاني مستقر:
    https://api.exchangerate.host/latest?base=USD&symbols=SYP
    يعيد معدل USD→SYP (قيمة وسطية عامة).
    """
    url = "https://api.exchangerate.host/latest"
    params = {"base": "USD", "symbols": "SYP"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=12)
    if r.status_code == 200:
        data = r.json()
        rate = data.get("rates", {}).get("SYP")
        if isinstance(rate, (int, float)) and rate > 0:
            return float(rate)
    return None


def get_rate():
    """
    تُعيد قاموسًا موحّدًا:
      {
        "country": "Syria",
        "currency": "ليرة سورية",
        "buy": <float>,
        "sell": <float>
      }
    """
    mid = None

    # 1) API العام
    try:
        mid = _from_exchangerate_host()
    except Exception:
        mid = None

    # 2) قيمة احتياطية إذا فشل الجلب
    if mid is None:
        mid = 15000.0  # تقدير وسطي تقريبي يتغير بمرور الوقت

    # سبريد بسيط لمحاكاة فرق الشراء/البيع
    spread = max(50.0, round(mid * 0.002, 2))  # ~0.2% أو 50 ل.س كحد أدنى
    buy = round(mid, 2)
    sell = round(mid + spread, 2)

    return {
        "country": "Syria",
        "currency": "ليرة سورية",
        "buy": buy,
        "sell": sell
    }
