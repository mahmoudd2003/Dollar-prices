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
st.caption("إصدار تجريبي - يعتمد على GPT-5")

# تحميل الإعدادات
CONFIG_PATH = "config/config.json"
if not os.path.exists(CONFIG_PATH):
    st.error("⚠️ لم يتم العثور على config/config.json")
    st.stop()

with open(CONFIG_PATH, encoding="utf-8") as f:
    config = json.load(f)

countries = config["countries"]
st.sidebar.header("⚙️ الإعدادات")
selected = st.sidebar.multiselect(
    "اختر الدول لتوليد التقرير:",
    countries,
    default=countries
)

st.sidebar.write("وضع النشر:", config["wordpress"].get("publish_status", "draft"))

# 🪄 زر التوليد
if st.button("🚀 توليد المقالات الآن"):
    st.info("جاري تنفيذ العملية، قد يستغرق ذلك بضع دقائق...")
    os.environ["SELECTED_COUNTRIES"] = ",".join(selected)
    generate_articles()
    st.success("✅ تم توليد المقالات بنجاح!")

# 🔹 عرض الأسعار الحالية
st.subheader("📊 أحدث الأسعار")
data = []
for c in selected:
    try:
        rate = get_country_rate(c)
        change = get_rate_change("data/rates_history.csv", rate["country"])
        data.append({
            "الدولة": rate["country"],
            "عملة": rate["currency"],
            "شراء": rate["buy"],
            "بيع": rate["sell"],
            "الاتجاه": change["direction"],
            "نسبة التغير %": change["change"]
        })
    except Exception as e:
        data.append({"الدولة": c, "خطأ": str(e)})

if data:
    st.table(pd.DataFrame(data))

# 🔹 عرض سجل النشر
st.subheader("🗂️ سجل النشر")
if os.path.exists("data/logs.txt"):
    with open("data/logs.txt", encoding="utf-8") as f:
        logs = f.read().strip()
    st.text_area("Logs", logs, height=200)
else:
    st.write("لا يوجد سجل بعد.")

st.markdown("---")
st.caption("© 2025 Currency Reporter – Developed by GPT-5")
