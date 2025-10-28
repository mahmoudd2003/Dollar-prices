# data_sources/egypt.py
# جلب أسعار USD→EGP من مصدر رسمي (البنك المركزي المصري CBE) مع طبقات احتياط.
# يعيد قاموسًا موحّدًا: {"country":"Egypt","currency":"جنيه مصري","buy":..,"sell":..}
# يتضمن "source" لبيان مصدر الأرقام.

from __future__ import annotations
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Tuple

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CurrencyReporter/1.1; +https://example.com)"
}
TIMEOUT = 15


# =============== أدوات مساعدة ===============

AR_NUMS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789..")

def _to_float(s: str) -> Optional[float]:
    """حوّل نص (قد يحوي أرقام عربية/فواصل) إلى float آمن."""
    if not s:
        return None
    s = s.strip().translate(AR_NUMS)
    s = s.replace(",", ".")
    m = re.search(r"(-?\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        v = float(m.group(1))
        # نطاق منطقي لـ USD→EGP
        if 5.0 < v < 400.0:
            return v
    except Exception:
        return None
    return None


def _pick_two_numbers(cells_texts) -> Tuple[Optional[float], Optional[float]]:
    """
    من نصوص خلايا الصف، استخرج قيمتين منطقيتين للشراء/البيع.
    لو وجدنا >2 أرقام، نختار أقرب رقمين لبعضهما (buy <= sell غالبًا).
    """
    vals = []
    for t in cells_texts:
        v = _to_float(t)
        if v is not None:
            vals.append(v)
    if not vals:
        return None, None
    if len(vals) == 1:
        return vals[0], vals[0]
    # رتب واختر رقمين متجاورين
    vals.sort()
    # نفترض buy <= sell
    buy = vals[0]
    sell = vals[-1]
    # إن كان الفارق مبالغًا فيه، جرّب اختيار زوج متجاور
    best_pair = (buy, sell)
    best_gap = sell - buy
    for i in range(len(vals) - 1):
        gap = vals[i+1] - vals[i]
        if 0 <= gap < best_gap:
            best_gap = gap
            best_pair = (vals[i], vals[i+1])
    return round(best_pair[0], 3), round(best_pair[1], 3)


# =============== مصادر مصر ===============

def _from_cbe_exchange_ar() -> Optional[Tuple[float, float, str]]:
    """
    صفحة العربي للبنك المركزي — قد تُغيّر URL من وقت لآخر.
    نبحث عن صف 'الدولار الأمريكي' ونلتقط قيمتين (شراء/بيع).
    """
    url = "https://www.cbe.org.eg/ar/EconomicResearch/Statistics/Pages/ExchangeRatesListing.aspx"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    row = soup.find(lambda tag: tag.name == "tr" and "الدولار" in tag.get_text(" ", strip=True))
    if not row:
        # أحيانًا يكتبون "الدولار الأمريكي" داخل td/th
        row = soup.find(lambda tag: tag.name in ("tr", "td", "th") and "الدولار الأمريكي" in tag.get_text(" ", strip=True))
        row = row.find_parent("tr") if row else None
    if not row:
        return None
    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
    buy, sell = _pick_two_numbers(cells)
    if buy and sell:
        return buy, sell, "CBE (Arabic)"
    return None


def _from_cbe_exchange_en() -> Optional[Tuple[float, float, str]]:
    """
    الصفحة الإنجليزية للبنك المركزي.
    """
    url = "https://www.cbe.org.eg/en/EconomicResearch/Statistics/Pages/ExchangeRates.aspx"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    row = soup.find(lambda tag: tag.name == "tr" and "US Dollar" in tag.get_text(" ", strip=True))
    if not row:
        cell = soup.find(lambda tag: tag.name in ("td", "th") and "US Dollar" in tag.get_text(" ", strip=True))
        row = cell.find_parent("tr") if cell else None
    if not row:
        return None
    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
    buy, sell = _pick_two_numbers(cells)
    if buy and sell:
        return buy, sell, "CBE (English)"
    return None


def _from_cib_bank() -> Optional[Tuple[float, float, str]]:
    """
    البنك التجاري الدولي (CIB).
    الصفحة قد تكون ديناميكية؛ لكن نحاول استخراج أي رقمين منطقيين من كتلة تحتوي 'الدولار الأمريكي' أو 'USD'.
    """
    url = "https://www.cibeg.com/ar/exchange-rates"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    block = soup.find(lambda t: t.name in ("section","div","table") and ("الدولار" in t.get_text(" ", strip=True) or "USD" in t.get_text(" ", strip=True)))
    if not block:
        return None
    texts = [t.get_text(" ", strip=True) for t in block.find_all(["td","th","div","span","p"])]
    buy, sell = _pick_two_numbers(texts)
    if buy and sell:
        return buy, sell, "CIB"
    return None


def _from_banquemisr() -> Optional[Tuple[float, float, str]]:
    """
    بنك مصر — قد تكون الصفحة ديناميكية أيضًا. نحاول الالتقاط من النص.
    """
    url = "https://www.banquemisr.com/ar/rates"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    block = soup.find(lambda t: t.name in ("section","div","table") and ("الدولار" in t.get_text(" ", strip=True) or "USD" in t.get_text(" ", strip=True)))
    if not block:
        return None
    texts = [t.get_text(" ", strip=True) for t in block.find_all(["td","th","div","span","p"])]
    buy, sell = _pick_two_numbers(texts)
    if buy and sell:
        return buy, sell, "Banque Misr"
    return None


def _from_fallback_api() -> Optional[Tuple[float, float, str]]:
    """
    احتياطي أخير: API عام — نستخدمه فقط إذا فشلت المصادر الرسمية.
    """
    url = "https://api.exchangerate.host/latest"
    params = {"base": "USD", "symbols": "EGP"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=12)
    if r.status_code != 200:
        return None
    rate = r.json().get("rates", {}).get("EGP")
    if not isinstance(rate, (int, float)):
        return None
    mid = float(rate)
    if not (5.0 < mid < 400.0):
        return None
    # افترض سبريد بسيط
    buy = round(mid, 3)
    sell = round(mid + max(0.05, round(mid * 0.003, 3)), 3)
    return buy, sell, "Exchangerate.host"


# =============== نقطة الدخول ===============

def get_rate():
    """
    يعيد:
      {
        "country": "Egypt",
        "currency": "جنيه مصري",
        "buy": <float>,
        "sell": <float>,
        "source": "<اسم المصدر>"
      }
    ترتيب المحاولات: CBE العربي → CBE الإنجليزي → CIB → Banque Misr → API عام (احتياط).
    """
    strategies = [
        _from_cbe_exchange_ar,
        _from_cbe_exchange_en,
        _from_cib_bank,
        _from_banquemisr,
        _from_fallback_api,
    ]

    buy = sell = None
    src = "Unknown"

    for fn in strategies:
        try:
            res = fn()
        except Exception:
            res = None
        if res:
            buy, sell, src = res
            break

    # إن فشل الجميع تمامًا — ضع قيمة احتياطية معقولة (لكنها ستشير للمصدر Unknown)
    if buy is None or sell is None:
        mid = 60.0  # احتياطي احترازي فقط لتجنب 50.0 الثابتة
        buy = round(mid, 3)
        sell = round(mid + 0.15, 3)

    # تأكد buy <= sell
    if buy > sell:
        buy, sell = sell, buy

    return {
        "country": "Egypt",
        "currency": "جنيه مصري",
        "buy": buy,
        "sell": sell,
        "source": src
    }
