"""Tests for the crawler ingestion noise guards (added with the 2026-10 cleanup).

Covered:
    * is_skippable_link() — MediaWiki special/login/return-URL pages are dropped,
      normal article links are kept.
    * is_noise_title() — site chrome titles (nav / login / listing) are dropped.
    * title_exists() — URL-variant duplicates are caught before insert.
    * ROOT_URLS wiring — no mirror host, listing roots are marked skip_root.
"""

from __future__ import annotations

import sqlite3

import pytest

import crawler_subpages as cs


class TestSkippableLink:
    @pytest.mark.parametrize(
        "href",
        [
            # MediaWiki 特殊页 — 原始中文
            "https://www.mywiki.cn/百发百中穿心龙爪手/特殊:所有页面",
            "https://www.mywiki.cn/百发百中穿心龙爪手/index.php?title=Special:AllPages",
            # 同一页的百分号编码形式
            "https://www.mywiki.cn/百发百中穿心龙爪手/index.php/%E7%89%B9%E6%AE%8A:%E6%89%80%E6%9C%89%E9%A1%B5%E9%9D%A2",
            # 登录页带 return URL
            "https://www.mywiki.cn/wiki/index.php?title=%E9%A6%96%E9%A1%B5&returnto=%E9%A6%96%E9%A1%B5",
            "https://www.mywiki.cn/wiki/index.php?title=%E9%A6%96%E9%A1%B5&action=pagesetting",
            # 常规静态资源与锚点
            "https://www.mywiki.cn/a.png",
            "#section",
            "mailto:a@b.c",
        ],
    )
    def test_noise_links_are_skipped(self, href):
        assert cs.is_skippable_link(href) is True

    @pytest.mark.parametrize(
        "href",
        [
            "https://www.mywiki.cn/百发百中穿心龙爪手/2013%E5%B9%B4%E4%BC%AF%E5%85%8B%E5%B8%8C%E5%B0%94%E8%82%A1%E4%B8%9C%E5%A4%A7%E4%BC%9A",
            "https://github.com/ruanyf/weekly/blob/master/docs/issue-410.md",
            "https://ruanyf-weekly.vibecodinghub.org/issue/409",
            "https://example.com/articles/ai-cache",
        ],
    )
    def test_article_links_are_kept(self, href):
        assert cs.is_skippable_link(href) is False


class TestNoiseTitle:
    @pytest.mark.parametrize(
        "title",
        [
            "所有页面 - 个人维基",
            "特殊页面 - lanota",
            "登录 - 个人维基",
            "需要登录 - 个人维基",
            "首页 - 个人维基",
            "个人维基",
            "科技爱好者周刊",
            "Issues · ruanyf/weekly · GitHub",
            "Pull requests · ruanyf/weekly",
            "",
            "   ",
        ],
    )
    def test_site_chrome_titles(self, title):
        assert cs.is_noise_title(title) is True

    @pytest.mark.parametrize(
        "title",
        [
            "科技爱好者周刊（第 409 期）：程序员的职业未来",
            "2013年伯克希尔股东大会 - 个人维基",
            "Git worktree 使用详解",
            "登录鉴权的最佳实践",  # 含「登录」但是正常文章标题
        ],
    )
    def test_article_titles(self, title):
        assert cs.is_noise_title(title) is False


class TestTitleExists:
    def test_detects_existing_title(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE content_summary (id INTEGER PRIMARY KEY, title TEXT NOT NULL)"
        )
        conn.execute("INSERT INTO content_summary (title) VALUES (?)", ("芒格主义 - 个人维基",))
        assert cs.title_exists(conn, "芒格主义 - 个人维基") is True
        assert cs.title_exists(conn, "  芒格主义 - 个人维基  ") is True
        assert cs.title_exists(conn, "另一个标题") is False
        conn.close()


class TestRootConfig:
    def test_no_mirror_root(self):
        hosts = {cs.urlparse(r["url"]).netloc for r in cs.ROOT_URLS}
        assert "ruanyf-weekly.vibecodinghub.org" not in hosts

    def test_listing_roots_are_skipped(self):
        by_url = {r["url"]: r for r in cs.ROOT_URLS}
        assert by_url["https://github.com/ruanyf/weekly/issues"].get("skip_root") is True
        assert by_url["https://github.com/ruanyf/weekly"].get("skip_root") is True
        # 真正的文章根（chuan.us / xiaolai 等）仍然插入
        assert by_url["https://chuan.us/"].get("skip_root") is not True
