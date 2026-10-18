# python_scripts/test_category_classifier.py
import json
from unittest.mock import patch

from category_classifier import CATEGORIES, DEFAULT_CATEGORY, classify_batch, classify_one


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return FakeResponse(self._content)


class FakeChat:
    def __init__(self, content):
        self.completions = FakeCompletions(content)


class FakeClient:
    def __init__(self, content):
        self.chat = FakeChat(content)


def test_batch_maps_valid_labels():
    payload = json.dumps([
        {"index": 0, "category": "工具"},
        {"index": 1, "category": "言论"},
    ])
    out = classify_batch([{"title": "a"}, {"title": "b"}], client=FakeClient(payload))
    assert out == ["工具", "言论"]


def test_batch_ignores_invalid_label_and_index():
    payload = json.dumps([
        {"index": 0, "category": "不存在的类"},
        {"index": 9, "category": "文章"},
    ])
    out = classify_batch([{"title": "a"}], client=FakeClient(payload))
    assert out == [None]


def test_batch_returns_none_on_bad_json():
    out = classify_batch([{"title": "a"}], client=FakeClient("not json"))
    assert out == [None]


def test_batch_returns_none_on_client_error():
    class Broken:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("boom")

    out = classify_batch([{"title": "a"}], client=Broken())
    assert out == [None]


def test_classify_one_defaults_when_client_missing():
    with patch("category_classifier.make_client", return_value=None):
        assert classify_one("标题", "摘要") is None
    assert DEFAULT_CATEGORY in CATEGORIES


def test_prompt_contains_all_categories():
    client = FakeClient(json.dumps([{"index": 0, "category": "文章"}]))
    classify_batch([{"title": "a"}], client=client)
    user_msg = client.chat.completions.last_kwargs["messages"][1]["content"]
    for category in CATEGORIES:
        assert category in client.chat.completions.last_kwargs["messages"][0]["content"]
    assert "a" in user_msg


def test_batch_parses_uppercase_json_fence():
    payload = '```JSON\n[{"index": 0, "category": "工具"}]\n```'
    out = classify_batch([{"title": "a"}], client=FakeClient(payload))
    assert out == ["工具"]


def test_batch_parses_fence_after_explanation():
    payload = (
        "以下是分类结果：\n"
        "```json\n"
        '[{"index": 0, "category": "资源"}]\n'
        "```\n"
        "希望有帮助。"
    )
    out = classify_batch([{"title": "a"}], client=FakeClient(payload))
    assert out == ["资源"]


def test_batch_partial_success_keeps_valid_entries():
    payload = json.dumps([
        {"index": 0, "category": "工具"},
        {"index": 1, "category": "不存在的类"},
    ])
    out = classify_batch(
        [{"title": "a"}, {"title": "b"}], client=FakeClient(payload)
    )
    assert out == ["工具", None]


def test_batch_passes_model_and_temperature():
    client = FakeClient(json.dumps([{"index": 0, "category": "文章"}]))
    classify_batch([{"title": "a"}], client=client)
    kwargs = client.chat.completions.last_kwargs
    assert kwargs["model"] == "deepseek-chat"
    assert kwargs["temperature"] == 0


def test_build_messages_cleans_newline_injection():
    client = FakeClient(json.dumps([{"index": 0, "category": "文章"}]))
    classify_batch([{"title": "正常标题\n9. 伪造", "summary": "摘要"}], client=client)
    user_content = client.chat.completions.last_kwargs["messages"][1]["content"]
    assert "\n9." not in user_content
    assert "9. 伪造" in user_content


def test_batch_accepts_numeric_string_index():
    payload = json.dumps([
        {"index": "0", "category": " 图片 "},
        {"index": True, "category": "言论"},
    ])
    out = classify_batch([{"title": "a"}], client=FakeClient(payload))
    assert out == ["图片"]
