# app.py
import streamlit as st
import pandas as pd
import os
import json
from datetime import date

from generator import main as generate_articles
from utils.fetch_utils import get_country_rate
from utils.rate_analyzer import get_rate_change

st.set_page_config(page_title="Currency Reporter", layout="centered")
st.title("💵 نظام تقارير سعر الدولار اليوم")
st.caption("إصدار تجريبي – يعتمد على GPT-5")

# تحميل الإعدادات
CONFIG_PATH = "config/config.json"
if not os.path.exists(CONFIG_PATH):
    st.error("⚠️ لم يتم العثور على config/config.json")
    st.stop()

with open(CONFIG_PATH, encoding="utf-8") as f:
    config = json.load(f)

all_countries = config["countries"]

st.sidebar.header("⚙️ الإعدادات")
st.sidebar.write("وضع النشر:", config["wordpress"].get("publish_status", "draft"))

# اختيار متعدد
multi_selected = st.multiselect(
    "اختر دولًا لتوليد التقارير (متعدد):",
    all_countries,
    default=all_countries
)

# اختيار دولة واحدة
single_selected = st.selectbox(
    "أو اختر دولة واحدة فقط:",
    ["— لا شيء —"] + all_countries,
    index=0
)

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 توليد المقالات للدول المختارة (متعدد)"):
        if not multi_selected:
            st.warning("اختر دولة واحدة على الأقل.")
        else:
            st.info("جاري التنفيذ…")
            os.environ["SINGLE_COUNTRY"] = ""  # تأكيد الإلغاء
            os.environ["SELECTED_COUNTRIES"] = ",".join(multi_selected)
            generate_articles()
            st.success("✅ تم التوليد للدول المختارة.")

with col2:
    if st.button("⚡ توليد مقال لدولة واحدة"):
        if single_selected == "— لا شيء —":
            st.warning("اختر دولة واحدة من القائمة.")
        else:
            st.info(f"يتم الآن توليد مقال لـ {single_selected} …")
            os.environ["SELECTED_COUNTRIES"] = ""  # تأكيد الإلغاء
            os.environ["SINGLE_COUNTRY"] = single_selected
            generate_articles()
            st.success(f"✅ تم توليد مقال لدولة: {single_selected}")

st.markdown("---")
st.subheader("📊 أحدث الأسعار (حسب اختيارك أعلاه)")
show_list = [single_selected] if single_selected != "— لا شيء —" else (multi_selected or all_countries)

rows = []
for c in show_list:
    try:
        rate = get_country_rate(c)
        change = get_rate_change("data/rates_history.csv", rate["country"])
        rows.append({
            "الدولة": rate["country"],
            "العملة": rate["currency"],
            "شراء": rate["buy"],
            "بيع": rate["sell"],
            "الاتجاه": change["direction"],
            "نسبة التغير %": change["change"]
        })
    except Exception as e:
        rows.append({"الدولة": c, "خطأ": str(e)})

if rows:
    st.table(pd.DataFrame(rows))

st.subheader("🗂️ سجل النشر")
if os.path.exists("data/logs.txt"):
    with open("data/logs.txt", encoding="utf-8") as f:
        logs = f.read().strip()
    st.text_area("Logs", logs, height=200)
else:
    st.write("لا يوجد سجل بعد.")

st.markdown("---")
st.caption("© 2025 Currency Reporter – Developed by GPT-5")
