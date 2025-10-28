import requests
from requests.auth import HTTPBasicAuth
import json, os
from datetime import date

def publish_to_wordpress(article_html, country_code, meta, config_path="config/config.json"):
    """
    ينشر المقال على ووردبريس باستخدام REST API.
    يعتمد على:
      - config/config.json: يحتوي عنوان الـ API، المستخدم، كلمة مرور التطبيق، التصنيفات، وضع النشر.
      - meta: dict يحتوي title/desc/slug/schema
    يضيف schema JSON-LD أسفل المحتوى ويُرسل الوصف كـ excerpt (متوافق غالباً مع Yoast/RankMath كبديل آمن).
    """
    # تحميل الإعدادات
    with open(config_path, encoding="utf-8") as f:
        conf = json.load(f)

    wp_url = conf["wordpress"]["url"]                     # مثال: https://example.com/wp-json/wp/v2/posts
    user = conf["wordpress"]["user"]                      # مستخدم ووردبريس (يفضل صلاحية Editor)
    app_password = conf["wordpress"]["app_password"]      # Application Password من لوحة ووردبريس
    categories = conf["wordpress"]["categories"]          # {"jordan": 12, ...}
    status = conf["wordpress"].get("publish_status", "publish")  # "draft" أثناء الاختبار

    # تحضير الحمولة
    payload = {
        "title": meta["title"],
        "content": article_html + meta.get("schema", ""),
        "status": status,
        "slug": meta["slug"],
        "categories": [categories.get(country_code, 0)],
        "excerpt": meta.get("desc", "")
    }

    # إرسال الطلب
    try:
        resp = requests.post(
            wp_url,
            auth=HTTPBasicAuth(user, app_password),
            json=payload,
            timeout=30
        )
    except requests.RequestException as e:
        print(f"❌ WP request error: {e}")
        _log_publish(country_code, "failed_request")
        return

    # التحقق من النتيجة
    if resp.status_code == 201:
        try:
            post_id = resp.json().get("id")
        except Exception:
            post_id = "unknown"
        print(f"✅ Published: Post ID {post_id}")
        _log_publish(country_code, post_id)
    else:
        print(f"❌ WP publish failed [{resp.status_code}]: {resp.text}")
        _log_publish(country_code, f"failed_{resp.status_code}")


def _log_publish(country_code, result):
    """
    يسجل عمليات النشر والنتائج في data/logs.txt
    """
    os.makedirs("data", exist_ok=True)
    line = f"{date.today().isoformat()} | {country_code} | {result}\n"
    with open("data/logs.txt", "a", encoding="utf-8") as f:
        f.write(line)
