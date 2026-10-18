"""七分类分类器：用 DeepSeek 给内容打上唯一分类。

独立模块，不依赖 web_content_system（那个包顶层会拉起 selenium）。
"""

from __future__ import annotations

import json
import os

CATEGORIES = ["科技动态", "文章", "工具", "资源", "图片", "文摘", "言论"]
DEFAULT_CATEGORY = "文章"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com"

SYSTEM_PROMPT = (
    "你是内容分类器。把每个条目归入且仅归入以下七类之一："
    + "、".join(CATEGORIES)
    + '。只输出 JSON 数组，元素为 {"index": 输入序号, "category": 分类}，'
    "不要输出任何其他文字。"
)


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass


def make_client():
    """返回 OpenAI 兼容客户端；缺少 key 或 SDK 时返回 None。"""
    _load_env()
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
    )


def build_messages(items):
    lines = []
    for index, item in enumerate(items):
        lines.append(
            f"{index}. 标题：{item.get('title', '')}\n"
            f"摘要：{str(item.get('summary', ''))[:200]}"
        )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(lines)},
    ]


def classify_batch(items, client=None, model=DEFAULT_MODEL):
    """把一批条目分类；返回与输入等长的列表，无法判断的位置为 None。"""
    result = [None] * len(items)
    if not items:
        return result
    client = client or make_client()
    if client is None:
        return result
    try:
        response = client.chat.completions.create(
            model=model,
            messages=build_messages(items),
            temperature=0,
            max_tokens=512,
        )
        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()
        payload = json.loads(raw)
        for entry in payload:
            index = entry.get("index")
            category = entry.get("category")
            if (
                isinstance(index, int)
                and 0 <= index < len(items)
                and category in CATEGORIES
            ):
                result[index] = category
    except Exception:
        return [None] * len(items)
    return result


def classify_one(title, summary="", client=None, model=DEFAULT_MODEL):
    """单条分类；失败返回 None（调用方决定兜底）。"""
    items = [{"title": title, "summary": summary}]
    return classify_batch(items, client=client, model=model)[0]
