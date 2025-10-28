# data_sources/iraq.py
# جلب سعر الدولار مقابل الدينار العراقي (USD→IQD)
# نعتمد أساسًا على API عام مستقر، مع محاولة سكراب خفيفة من موقع البنك المركزي العراقي كخطة احتياطية.

from __future__ import annotations
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CurrencyReporter/1.0; +https://example.com)"
}

def _from_exchangerate_host() -> float | None:
    """
    مصدر مجاني مستقر:
    https://api.exchangerate.host/latest?base=USD&symbols=IQD
    يعيد معدل USD→IQD (قيمة وسطية عامة).
    """
    url = "https://api.exchangerate.host/latest"
    params = {"base": "USD", "symbols": "IQD"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=12)
    if r.status_code == 200:
        data = r.json()
        rate = data.get("rates", {}).get("IQD")
        if isinstance(rate, (int, float)) and rate > 0:
            return float(rate)
    return None


def _from_cbi_scrape() -> float | None:
    """
    محاولة احتياطية: قراءة تلميح عن السعر من موقع البنك المركزي العراقي (قد تتغير البنية).
    https://cbi.iq
    سنلتقط أول رقم منطقي ضمن نطاق الدينار العراقي (900–2000).
    """
    url = "https://cbi.iq"
    r = requests.get(url, headers=HEADERS, timeout=12)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    # التقط أي رقم ضمن نطاق منطقي (قد يظهر مثل 1310.000 أو 1310)
    import re
    candidates = re.findall(r"\b(\d{3,4}(?:\.\d{1,3})?)\b", text)
    # انتقِ أول قيمة تقع ضمن نطاق IQD الشائع
    for c in candidates:
        try:
            v = float(c)
            if 900.0 <= v <= 2000.0:
                return v
        except Exception:
            pass
    return None


def get_rate():
    """
    واجهة موحّدة تعيد:
      {
        "country": "Iraq",
        "currency": "دينار عراقي",
        "buy": <float>,
        "sell": <float>
      }

    ملاحظة تحريرية:
    - السوق العراقية تشهد فجوة بين الرسمي والموازي. هنا نعرض معدلًا وسطيًا
      (من API أو من تلميحات CBI) دون الخوض في أرقام موازية غير موثوقة.
    """
    mid = None

    # 1) API العام
    try:
        mid = _from_exchangerate_host()
    except Exception:
        mid = None

    # 2) احتياطي: سكراب خفيف من CBI
    if mid is None:
        try:
            mid = _from_cbi_scrape()
        except Exception:
            mid = None

    # 3) قيمة احتياطية معقولة إذا فشل الكل
    if mid is None:
        mid = 1310.0  # قريب من السعر الرسمي الشائع مؤخرًا

    # سبريد بسيط لمحاكاة فرق الشراء/البيع
    spread = max(1.0, round(mid * 0.002, 3))  # ~0.2% أو 1 دينار كحد أدنى
    buy = round(mid, 3)
    sell = round(mid + spread, 3)

    return {
        "country": "Iraq",
        "currency": "دينار عراقي",
        "buy": buy,
        "sell": sell
    }
