"""Hacker News 信息源：官方 Firebase API（免费、无需 key）。

topstories/newest 取近 days 天条目，标题+链接+分数+评论数。
"""
import time
import urllib.request
import json

from .base import Source

API = "https://hacker-news.firebaseio.com/v0"


def _get(path, timeout=15):
    req = urllib.request.Request(API + path, headers={"User-Agent": "signal-vaults/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


class HackerNewsSource(Source):
    name = "hacker-news"

    def __init__(self, limit=60):
        self.limit = limit

    def fetch(self, days=1):
        since = time.time() - days * 86400
        # newest.json 被 firebase 拒(Permission denied), 用 topstories;
        # topstories 只有当前热榜(约500条不分时间), 再逐条按时间过滤
        try:
            ids = _get("/topstories.json")[: self.limit * 2]
        except Exception:
            return self._fetch_algolia(days)
        items = []
        for sid in ids:
            try:
                it = _get("/item/{}.json".format(sid))
            except Exception:
                continue
            if not it or it.get("type") != "story":
                continue
            if it.get("time", 0) < since:
                continue
            items.append(self._fmt(it))
            if len(items) >= self.limit:
                break
        if not items:  # 热榜可能全是当天之前的, 兜底走 Algolia
            return self._fetch_algolia(days)
        return items

    @staticmethod
    def _fmt(it):
        url = it.get("url") or "https://news.ycombinator.com/item?id={}".format(it.get("id"))
        return {
            "title": it.get("title", ""),
            "url": url,
            "summary": "{}分/{}评".format(it.get("score", 0), it.get("descendants", 0)),
            "meta": "hacker-news",
        }

    def _fetch_algolia(self, days):
        """Algolia HN 镜像: 按时间搜, 免 key"""
        import urllib.parse
        since = int(time.time() - days * 86400)
        url = ("https://hn.algolia.com/api/v1/search_by_date?tags=story"
               "&numericFilters=created_at_i>{}".format(since)
               + "&hitsPerPage={}".format(self.limit))
        try:
            data = _get(url)
        except Exception:
            return []
        out = []
        for h in data.get("hits", []):
            link = h.get("url") or "https://news.ycombinator.com/item?id={}".format(h.get("objectID"))
            out.append({
                "title": h.get("title") or h.get("story_title") or "",
                "url": link,
                "summary": "{}分/{}评".format(h.get("points", 0), h.get("num_comments", 0)),
                "meta": "hacker-news",
            })
        return out
