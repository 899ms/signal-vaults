"""信息源抽象层。

每个信息源实现 fetch(days) -> list[Item]：
    Item = {"title": str, "url": str, "summary": str, "meta": str}

signal-vaults 用同一套 LLM 提炼/渲染/推送管线处理所有来源：
    wechat 群聊 / 公众号（内置）+ hn / reddit（sources/）
"""
import datetime


def _day_cutoff(days):
    return time.time() - days * 86400 if (time := __import__("time")) else 0


class Source:
    """信息源基类。子类实现 fetch(days)。"""
    name = "base"

    def fetch(self, days=1):
        raise NotImplementedError


def fmt_items(items, source_label=""):
    """把 Item 列表格式化为 LLM 提炼用的纯文本（与微信分片同格式）。"""
    lines = []
    for it in items:
        lines.append("[{src}] {title} | {url} | {summary}".format(
            src=source_label or it.get("meta", ""),
            title=it.get("title", ""),
            url=it.get("url", ""),
            summary=(it.get("summary") or "")[:200]))
    return "\n".join(lines)
