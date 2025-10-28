# utils/call_llm.py
# دالة اتصال آمنة بـ OpenAI مع إعادة المحاولة + خيار fallback

import os
import time
import random
from typing import Optional
from openai import OpenAI

_client: Optional[OpenAI] = None


def _client_singleton() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY غير مضبوط في متغيرات البيئة.")
        _client = OpenAI(api_key=api_key)
    return _client


def call_llm(prompt: str, model: str = "gpt-5",
             temperature: float = 0.8,
             max_retries: int = 3,
             fallback_model: Optional[str] = "gpt-4o-mini") -> str:
    """
    يستدعي نموذج OpenAI لإنتاج نص.
    - model: النموذج الأساسي (نوصي gpt-5)
    - fallback_model: نموذج احتياطي في حال فشل الأساس (يمكن تعطيله بوضع None)
    - max_retries: عدد محاولات إعادة الطلب مع backoff أُسّي
    """
    client = _client_singleton()

    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.responses.create(
                model=model,
                input=prompt,
                temperature=temperature,
            )
            return resp.output_text
        except Exception as e:
            last_err = e
            sleep_for = (2 ** attempt) + random.uniform(0, 0.6)
            time.sleep(sleep_for)

    # فشل النموذج الأساسي بعد المحاولات -> جرّب fallback إذا موجود
    if fallback_model:
        try:
            resp = client.responses.create(
                model=fallback_model,
                input=prompt,
                temperature=min(temperature, 0.7),  # خفّض قليلاً لثبات أعلى
            )
            return resp.output_text
        except Exception as e2:
            last_err = e2

    raise RuntimeError(f"LLM call failed. Last error: {last_err}")
