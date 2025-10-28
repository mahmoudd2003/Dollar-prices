# data_sources/egypt.py
# جلب أسعار USD→EGP من مصدر رسمي (CBE) مع طبقات احتياط (CIB, Banque Misr, API).
# يعيد قاموسًا: {"country":"Egypt","currency":"جنيه مصري","buy":..,"sell":..,"source":"..."}.

from __future__ import annotations
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional, Tuple

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CurrencyReporter/1.1; +https://example.com)"
}
TIMEOUT = 15

# ---------- أدوات ----------
AR_NUMS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789..")

def _to_float(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.strip().translate(AR_NUMS).replace(",", ".")
    m = re.search(r"(-?\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        v = float(m.group(1))
        if 5.0 < v < 400.0:
            return v
    except Exception:
        return None
    return None

def _pick_two_numbers(cells_texts) -> Tuple[Optional[float], Optional[float]]:
    vals = []
    for t in cells_texts:
        v = _to_float(t)
        if v is not None:
            vals.append(v)
    if not vals:
        return None, None
    if len(vals) == 1:
        return round(vals[0], 3), round(vals[0], 3)
    vals.sort()
    # اختر أقرب زوج منطقي buy<=sell
    buy, sell = vals[0], vals[-1]
    gap = sell - buy
    best = (buy, sell, gap)
    for i in range(len(vals) - 1):
        g = vals[i+1] - vals[i]
        if 0 <= g < best[2]:
            best = (vals[i], vals[i+1], g)
    return round(best[0], 3), round(best[1], 3)

# ---------- مصادر ----------
def _from_cbe_exchange_ar() -> Optional[Tuple[float, float, str]]:
    url = "https://www.cbe.org.eg/ar/EconomicResearch/Statistics/Pages/ExchangeRatesListing.aspx"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    row = soup.find(lambda t: t.name == "tr" and "الدولار" in t.get_text(" ", strip=True))
    if not row:
        cell = soup.find(lambda t: t.name in ("td","th") and "الدولار الأمريكي" in t.get_text(" ", strip=True))
        row = cell.find_parent("tr") if cell else None
    if not row:
        return None
    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td","th","span","div"])]
    buy, sell = _pick_two_numbers(cells)
    if buy and sell:
        return buy, sell, "CBE (Arabic)"
    return None

def _from_cbe_exchange_en() -> Optional[Tuple[float, float, str]]:
    url = "https://www.cbe.org.eg/en/EconomicResearch/Statistics/Pages/ExchangeRates.aspx"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, "lxml")
    row = soup.find(lambda t: t.name == "tr" and "US Dollar" in t.get_text(" ", strip=True))
    if not row:
        cell = soup.find(lambda t: t.name in ("td","th") and "US Dollar" in t.get_text(" ", strip=True))
        row = cell.find_parent("tr") if cell else None
    if not row:
        return None
    cells = [c.get_text(" ", strip=True) for c in row.find_all(["td","th","span","div"])]
    buy, sell = _pick_two_numbers(cells)
    if buy and sell:
        return buy, sell, "CBE (English)"
    return None

def _from_cib_bank() -> Optional[Tuple[float, float, str]]:
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
    buy = round(mid, 3)
    sell = round(mid + max(0.05, round(mid * 0.003, 3)), 3)
    return buy, sell, "Exchangerate.host"

# ---------- الواجهة ----------
def get_rate():
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
    if buy is None or sell is None:
        mid = 60.0
        buy = round(mid, 3)
        sell = round(mid + 0.15, 3)
    if buy > sell:
        buy, sell = sell, buy
    return {
        "country": "Egypt",
        "currency": "جنيه مصري",
        "buy": buy,
        "sell": sell,
        "source": src
    }
