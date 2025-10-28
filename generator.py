# generator.py
import os, json
from datetime import date
from utils.fetch_utils import get_country_rate, save_rate_to_csv
from utils.rate_analyzer import get_rate_change
from utils.call_llm import call_llm
from utils.text_utils import humanize
from utils.meta_utils import generate_meta
import markdown
from exporter_wp import publish_to_wordpress

def build_prompt(country_ar, tone, focus, intro, rate, change, min_words, max_words, country_code, style=None):
    today_human = date.today().isoformat()
    dir_map = {"up": "ارتفاع", "down": "انخفاض", "stable": "استقرار"}
    dir_text = dir_map.get(change.get("direction", "stable"), "استقرار")
    caution_eg = (
        "- عند تناول السوق الموازية، استخدم تعبيرات عامة مثل \"وفق تقديرات متعاملين\" أو \"بحسب مراقبين\" دون إدراج أرقام غير مؤكدة.\n"
        "- لا تذكر أبدًا مصادر غير رسمية على أنها رسمية."
        if country_code == "egypt" else ""
    )
    src = rate.get("source") or "مصدر رسمي"
    style_line = f"اكتب التقرير بأسلوب {style}.\n" if style else ""

    return f"""
اكتب تقريرًا اقتصاديًا احترافيًا عن **سعر الدولار اليوم في {country_ar}** بأسلوب صحفي يشبه مقالات "العين الإخبارية" و"اليوم السابع".
{style_line}
🗓️ التاريخ: {today_human}

🔹 البيانات الدقيقة (اعتمد عليها حرفيًا داخل النص):
- السعر الرسمي للشراء: {rate['buy']} {rate['currency']}
- السعر الرسمي للبيع: {rate['sell']} {rate['currency']}
- نسبة التغير مقارنة بالأمس: {change['change']}%
- الاتجاه العام: {dir_text}
- المصدر المعتمد للأسعار: {src}

🔹 التعليمات التحريرية:
1) ابدأ الفقرة الأولى بعبارة قوية وواضحة **تذكر السعر الرسمي مباشرة** وتصف الحالة العامة، مع الإشارة إلى {src}.
2) الفقرة الثانية: **قارن بالأمس** واذكر سببًا منطقيًا للارتفاع/الانخفاض/الاستقرار (مثل قرارات الفائدة، توافر السيولة، تغيرات الطلب الموسمية).
3) الفقرة الثالثة: **السوق الموازية** — تناولها بحذر مهني دون أرقام غير مؤكدة، واذكر أنها تقديرات متعاملين عند الحاجة.
4) الفقرة الرابعة: **السياسة النقدية** — اربط موجزًا بين حركة الدولار وما قد يتابعه البنك المركزي أو تأثير ذلك على الواردات/التضخم.
5) الخاتمة: سطران يحددان ما سيراقبه المتعاملون خلال 48 ساعة (سيولة، أسعار فائدة، تدفقات دولارية، أسعار نفط).

🔹 أسلوب الكتابة:
- لغة عربية اقتصادية دقيقة، جُمل قصيرة، انتقالات بشرية (مثل: في المقابل، من جهة أخرى، في الوقت ذاته).
- تجنّب العبارات العامة المكررة والإنشاء الزائد.
- لا تذكر الذكاء الاصطناعي أو عملية التوليد إطلاقًا.
- الطول المستهدف: بين {min_words} و {max_words} كلمة.

{caution_eg}
"""

def _generate_payload(country_code, config, prompts):
    model = config.get("model", "gpt-5")
    min_w = config.get("content", {}).get("min_words", 140)
    max_w = config.get("content", {}).get("max_words", 220)

    rate = get_country_rate(country_code)
    save_rate_to_csv(rate)
    change = get_rate_change("data/rates_history.csv", rate["country"])

    p = prompts[country_code]
    style = p.get("style")
    prompt = build_prompt(
        country_ar=rate["country"],
        tone=p.get("tone", ""),
        focus=p.get("focus", ""),
        intro=p.get("intro", ""),
        rate=rate,
        change=change,
        min_words=min_w,
        max_words=max_w,
        country_code=country_code,
        style=style
    )

    article_md = call_llm(prompt, model=model, temperature=0.8)
    article_md = humanize(article_md, min_words=min_w, max_words=max_w)
    article_html = markdown.markdown(article_md)

    today = date.today().isoformat()
    title, desc = generate_meta(rate["country"], today, rate["currency"], rate["buy"], rate["sell"], model)
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
    os.makedirs("data/articles", exist_ok=True)
    md_path = f"data/articles/{today}-{country_code}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(article_md)

    return {
        "country_code": country_code,
        "rate": rate,
        "change": change,
        "md_path": md_path,
        "html": article_html,
        "meta": {"title": title, "desc": desc, "slug": f"usd-{country_code}-{today}", "schema": schema}
    }

def generate_one(country_code, preview_only=True):
    with open("config/config.json", encoding="utf-8") as f:
        config = json.load(f)
    with open("config/prompts.json", encoding="utf-8") as f:
        prompts = json.load(f)

    payload = _generate_payload(country_code, config, prompts)
    if not preview_only:
        publish_to_wordpress(payload["html"], country_code, payload["meta"])
    return payload

def _countries_from_env_or_config(config):
    single = os.getenv("SINGLE_COUNTRY", "").strip()
    if single:
        return [single]
    selected = os.getenv("SELECTED_COUNTRIES", "").strip()
    if selected:
        return [c.strip() for c in selected.split(",") if c.strip()]
    return config["countries"]

def main():
    with open("config/config.json", encoding="utf-8") as f:
        config = json.load(f)
    with open("config/prompts.json", encoding="utf-8") as f:
        prompts = json.load(f)

    preview_only = os.getenv("PREVIEW_ONLY", "false").lower() in ("1","true","yes")
    countries = _countries_from_env_or_config(config)

    for cc in countries:
        try:
            payload = _generate_payload(cc, config, prompts)
            if preview_only:
                print(f"👀 Preview generated for {cc}: {payload['md_path']}")
            else:
                publish_to_wordpress(payload["html"], cc, payload["meta"])
        except Exception as e:
            print(f"❌ Failed for {cc}: {e}")

if __name__ == "__main__":
    main()
