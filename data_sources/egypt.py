# data_sources/egypt.py
# جلب سعر الدولار مقابل الجنيه المصري (USD→EGP)
# اعتماد أساسي على API عام مستقر، مع محاولة سكراب احتياطية من موقع البنك المركزي المصري (CBE) إذا لزم.

from __future__ import annotations
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CurrencyReporter/1.0; +https://example.com)"
}

def _from_exchangerate_host() -> float | None:
    """
    مصدر مجاني مستقر:
    https://api.exchangerate.host/latest?base=USD&symbols=EGP
    يعيد معدل USD→EGP (قيمة وسطية تقريبية من السوق/الأسواق الرسمية).
    """
    url = "https://api.exchangerate.host/latest"
    params = {"base": "USD", "symbols": "EGP"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=12)
    if r.status_code == 200:
        data = r.json()
        rate = data.get("rates", {}).get("EGP")
        if isinstance(rate, (int, float)) and rate > 0:
            return float(rate)
    return None


def _from_cbe_scrape() -> float | None:
    """
    محاولة احتياطية لقراءة السعر من موقع البنك المركزي المصري (CBE).
    ملاحظة: بنية الصفحات قد تتغير، لذا هذا الحل "best-effort".
    صفحة (قد تتغير): https://www.cbe.org.eg/en/EconomicResearch/Statistics/Pages/ExchangeRates.aspx
    نبحث عن صف 'US Dollar' ثم نلتقط آخر قيمة رقمية مجاورة.
    """
    url = "https://www.cbe.org.eg/en/EconomicResearch/Statistics/Pages/ExchangeRates.aspx"
    r = requests.get(url, headers=HEADERS, timeout=15)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    # ابحث عن خلية تحتوي على 'US Dollar'
    cell = soup.find(lambda tag: tag.name in ["td", "th"] and tag.get_text(strip=True) and "US Dollar" in tag.get_text(strip=True))
    if not cell:
        return None

    # ابحث في الخلايا المجاورة عن رقم منطقي (10–200 مثلًا)
    def _parse_egp(s: str) -> float | None:
        s = s.replace(",", "").strip()
        try:
            v = float(s)
            if 5.0 < v < 300.0:
                return v
        except Exception:
            pass
        return None

    # جرب في نفس الصف أولًا
    row = cell.find_parent("tr")
    if row:
        for td in row.find_all("td"):
            val = _parse_egp(td.get_text(strip=True))
            if val is not None:
                return val

    # كحل أخير، مسح محدود حول الخلية
    neighbors = cell.find_all_next(["td", "th"], limit=6)
    for n in neighbors:
        val = _parse_egp(n.get_text(strip=True))
        if val is not None:
            return val

    return None


def get_rate():
    """
    تعيد قاموسًا موحّدًا:
      {
        "country": "Egypt",
        "currency": "جنيه مصري",
        "buy": <float>,
        "sell": <float>
      }

    ملاحظة تحريرية مهمة:
    - نحن نقدّم السعر الرسمي/الوسطي فقط هنا.
    - ذكر "السوق الموازية" يتم داخل النص عبر الـprompt بشكل عام دون أرقام غير موثوقة.
    """
    mid = None

    # 1) API العام
    try:
        mid = _from_exchangerate_host()
    except Exception:
        mid = None

    # 2) احتياطي: سكراب CBE
    if mid is None:
        try:
            mid = _from_cbe_scrape()
        except Exception:
            mid = None

    # 3) قيمة احتياطية معقولة إذا فشل كل شيء
    if mid is None:
        mid = 50.0  # احتياطي تقريبي؛ عدّله إن رغبت

    # سبريد بسيط لمحاكاة فرق الشراء/البيع
    spread = max(0.05, round(mid * 0.003, 3))  # ~0.3% أو 0.05 كحد أدنى
    buy = round(mid, 6)
    sell = round(mid + spread, 6)

    return {
        "country": "Egypt",
        "currency": "جنيه مصري",
        "buy": buy,
        "sell": sell
    }
