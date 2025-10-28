# data_sources/jordan.py
# جلب سعر الدولار مقابل الدينار الأردني (USD→JOD)
# محاولات متعددة: مصدر API عام موثوق → (اختياري) صفحة البنك → قيمة احتياطية.
# نعيد قاموسًا موحّدًا: {"country":"Jordan","currency":"دينار أردني","buy":..,"sell":..}

from __future__ import annotations
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CurrencyReporter/1.0; +https://example.com)"
}

def _from_exchangerate_host() -> float | None:
    """
    مصدر مجاني مستقر:
    https://api.exchangerate.host/latest?base=USD&symbols=JOD
    يعيد معدل USD→JOD (عادة ~0.709)
    """
    url = "https://api.exchangerate.host/latest"
    params = {"base": "USD", "symbols": "JOD"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=12)
    if r.status_code == 200:
        data = r.json()
        rate = data.get("rates", {}).get("JOD")
        if isinstance(rate, (int, float)) and rate > 0:
            return float(rate)
    return None


def _from_cbj_scrape() -> float | None:
    """
    (اختياري) محاولة قراءة سعر الصرف من موقع البنك المركزي الأردني إذا توفّر بشكل مباشر.
    هذه الصفحة/البنية قد تتغير، لذا نستخدمها كمحاولة ثانوية فقط.
    """
    url = "https://www.cbj.gov.jo/Pages/viewpage.aspx?pageID=54"  # صفحة أسعار الصرف (قد تتغير)
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")

    # ابحث عن صف USD داخل جدول العملات (هيكل الصفحة قد يختلف، لذلك نحاول بعدة طرق):
    # 1) أي خلية تحتوي على 'USD' أو 'الدولار الأمريكي'
    candidates = soup.find_all(["td", "th"])
    idx = -1
    for i, c in enumerate(candidates):
        txt = (c.get_text(strip=True) or "").upper()
        if "USD" in txt or "الدولار" in txt:
            idx = i
            break

    if idx == -1:
        return None

    # حاول التقاط الأرقام في الخلايا المجاورة
    # سنبحث قريبًا من الخلية المحددة عن قيمة رقمية تشبه 0.70x
    window = candidates[max(0, idx-3): idx+6]
    def _parse_number(s: str) -> float | None:
        s = s.replace(",", "").replace(" ", "")
        try:
            val = float(s)
            if 0 < val < 5:  # نطاق منطقي لـ USD→JOD
                return val
        except Exception:
            pass
        return None

    for cell in window:
        val = _parse_number(cell.get_text(strip=True))
        if val is not None:
            return val

    return None


def get_rate():
    """
    دالة الواجهة القياسية التي يستدعيها السكربت.
    تُعيد:
      {
        "country": "Jordan",
        "currency": "دينار أردني",
        "buy": <float>,
        "sell": <float>
      }
    """
    # 1) جرّب مصدر API العام
    mid = None
    try:
        mid = _from_exchangerate_host()
    except Exception:
        mid = None

    # 2) إن فشل، حاول سكراب البنك المركزي (قد لا ينجح دائمًا)
    if mid is None:
        try:
            mid = _from_cbj_scrape()
        except Exception:
            mid = None

    # 3) إن فشل الجميع، استخدم قيمة احتياطية معقولة
    if mid is None:
        mid = 0.709  # متوسط معروف تقريبًا

    # نحسب سعر شراء/بيع بفارق بسيط لمحاكاة السبريد الرسمي/السوقي
    spread = 0.003  # فرق تقريبي
    buy = round(mid, 6)
    sell = round(mid + spread, 6)

    return {
        "country": "Jordan",
        "currency": "دينار أردني",
        "buy": buy,
        "sell": sell
    }
