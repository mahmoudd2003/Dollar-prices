import os, json
from datetime import date
from utils.fetch_utils import get_country_rate, save_rate_to_csv
from utils.rate_analyzer import get_rate_change
from utils.call_llm import call_llm
from utils.text_utils import humanize
from utils.meta_utils import generate_meta
import markdown
from exporter_wp import publish_to_wordpress


# 🧠 دالة إنشاء الـ Prompt
def build_prompt(country_ar, tone, focus, intro, rate, change, min_words, max_words, country_code):
    dir_map = {
        "up": "ارتفع الدولار بصورة طفيفة",
        "down": "تراجع الدولار أمام العملة المحلية",
        "stable": "حافظ الدولار على استقرار نسبي"
    }
    dir_text = dir_map.get(change["direction"], "استقر الدولار")

    # معالجة خاصة لمصر (ذكر السوق الموازية دون أرقام)
    extra_eg = "\n- إن توافرت اليوم بيانات موثوقة حول السوق الموازية فأشر إليها بشكل عام دون إدراج أرقام غير مؤكدة.\n" if country_code == "egypt" else ""

    return f"""
    اكتب تقريرًا اقتصاديًا واقعيًا يشبه أسلوب محررين محلّيين في "{country_ar}".
    المعطيات الدقيقة:
    - تاريخ اليوم: {date.today().isoformat()} (توقيت عمّان)
    - سعر الشراء: {rate['buy']}
    - سعر البيع: {rate['sell']}
    - اتجاه اليوم مقابل الأمس: {dir_text} بنسبة تقريبية {change['change']}%
    - بؤرة التفسير: {focus}
    {extra_eg}

    المطلوب:
    - مقدمة قصيرة غير نمطية تلخص وضع اليوم (سطران كحد أقصى) وتستند إلى "{intro}" كمشهد عام لا كصيغة حرفية.
    - فقرة أرقام واضحة تتضمن مقارنة موجزة مع الأمس.
    - تفسير محلي مرتبط بـ {focus} دون مبالغة أو جزم غير مبرر.
    - جملة رأي منسوبة بشكل عام إلى "متعاملين" أو "مراقبين" بصياغة بشرية.
    - خاتمة عملية تشير لما قد يراقبه السوق خلال 48 ساعة (سيولة/فائدة/نفط/قرارات بنوك).

    ضوابط الأسلوب:
    - لغة عربية صحفية واضحة، جمل قصيرة، انتقالات بشرية (مثل: في المقابل/من جهة أخرى/في الوقت ذاته).
    - تجنب القوالب الجاهزة والتكرار، ولا تذكر الذكاء الاصطناعي أو عملية التوليد.
    - طول مستهدف بين {min_words} و {max_words} كلمة.
    """


# 🚀 الدالة الرئيسية
def main():
    with open("config/config.json", encoding="utf-8") as f:
        config = json.load(f)
    with open("config/prompts.json", encoding="utf-8") as f:
        prompts = json.load(f)

    model = config.get("model", "gpt-5")
    min_w = config.get("content", {}).get("min_words", 140)
    max_w = config.get("content", {}).get("max_words", 220)

    for country_code in config["countries"]:
        print(f"🧭 Generating article for {country_code}…")

        # 1️⃣ جلب السعر وحفظه
        rate = get_country_rate(country_code)
        save_rate_to_csv(rate)

        # 2️⃣ تحليل التغير
        change = get_rate_change("data/rates_history.csv", rate["country"])

        # 3️⃣ إعداد البرومبت
        p = prompts[country_code]
        prompt = build_prompt(
            country_ar=rate["country"],
            tone=p["tone"],
            focus=p["focus"],
            intro=p["intro"],
            rate=rate,
            change=change,
            min_words=min_w,
            max_words=max_w,
            country_code=country_code
        )

        # 4️⃣ توليد المقال عبر GPT-5
        article_md = call_llm(prompt, model=model, temperature=0.8)
        article_md = humanize(article_md, min_words=min_w, max_words=max_w)

        # 5️⃣ حفظ المقال Markdown
        today = date.today().isoformat()
        os.makedirs("data/articles", exist_ok=True)
        md_path = f"data/articles/{today}-{country_code}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(article_md)
        print(f"✅ Saved: {md_path}")

        # 6️⃣ تحويل Markdown إلى HTML
        article_html = markdown.markdown(article_md)

        # 7️⃣ توليد العنوان والوصف
        title, desc = generate_meta(
            rate["country"],
            today,
            rate["currency"],
            rate["buy"],
            rate["sell"],
            model
        )

        # 8️⃣ توليد سكيما JSON-LD
        schema = f"""
<script type="application/ld+json">{{
  "@context": "https://schema.org",
  "@type": "CurrencyExchange",
  "name": "سعر الدولار اليوم في {rate['country']}",
  "currency": "USD",
  "priceCurrency": "{rate['currency']}",
  "exchangeRateSpread": "{rate['buy']} - {rate['sell']}",
  "date": "{today}"
}}</script>
"""

        meta = {
            "title": title,
            "desc": desc,
            "slug": f"usd-{country_code}-{today}",
            "schema": schema
        }

        # 9️⃣ النشر إلى ووردبريس
        publish_to_wordpress(article_html, country_code, meta)


if __name__ == "__main__":
    main()
