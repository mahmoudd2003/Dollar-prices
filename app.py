# app.py
import streamlit as st
import pandas as pd
import os, json
from datetime import date
from generator import generate_one
from exporter_wp import publish_to_wordpress
from utils.fetch_utils import get_country_rate
from utils.rate_analyzer import get_rate_change

st.set_page_config(page_title="Currency Reporter", layout="centered")
st.title("💵 نظام تقارير سعر الدولار اليوم")
st.caption("معاينة قبل النشر – GPT-5")

CONFIG_PATH = "config/config.json"
with open(CONFIG_PATH, encoding="utf-8") as f:
    config = json.load(f)
all_countries = config["countries"]

# اختيارات
st.sidebar.header("⚙️ الإعدادات")
st.sidebar.write("وضع النشر الافتراضي:", config["wordpress"].get("publish_status", "draft"))
pick = st.multiselect("اختر دولًا للمعاينة:", all_countries, default=all_countries)

# زر توليد للمعاينة فقط
if st.button("👀 توليد للمعاينة (بدون نشر)"):
    st.session_state.previews = {}
    for cc in pick:
        payload = generate_one(cc, preview_only=True)
        st.session_state.previews[cc] = payload
    st.success("تم توليد المقالات للمعاينة.")

# عرض آخر أسعار مختصرة
st.subheader("📊 أحدث الأسعار")
rows = []
for c in pick:
    try:
        rate = get_country_rate(c)
        change = get_rate_change("data/rates_history.csv", rate["country"])
        rows.append({"الدولة": rate["country"], "العملة": rate["currency"], "شراء": rate["buy"], "بيع": rate["sell"], "الاتجاه": change["direction"], "نسبة التغير %": change["change"]})
    except Exception as e:
        rows.append({"الدولة": c, "خطأ": str(e)})
if rows: st.table(pd.DataFrame(rows))

# كروت المعاينة + زر نشر لكل دولة
st.subheader("📰 معاينة المقالات")
previews = st.session_state.get("previews", {})
if not previews:
    st.info("اضغط زر المعاينة أعلاه لتوليد المقالات دون نشر.")
else:
    for cc, p in previews.items():
        with st.expander(f"عرض: {p['meta']['title']}"):
            st.write(f"**Slug:** `{p['meta']['slug']}`")
            st.write(f"**Meta Description:** {p['meta']['desc']}")
            # HTML المقال
            st.markdown(p["html"], unsafe_allow_html=True)
            # زر نشر
            if st.button(f"✅ انشر مقال {cc}", key=f"pub_{cc}"):
                publish_to_wordpress(p["html"], cc, p["meta"])
                st.success(f"نُشر مقال {cc}.")

# سجل النشر
st.subheader("🗂️ سجل النشر")
if os.path.exists("data/logs.txt"):
    with open("data/logs.txt", encoding="utf-8") as f:
        logs = f.read().strip()
    st.text_area("Logs", logs, height=200)
else:
    st.write("لا يوجد سجل بعد.")

st.markdown("---")
st.caption("© 2025 Currency Reporter – Developed by GPT-5")
