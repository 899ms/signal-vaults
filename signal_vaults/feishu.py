"""飞书推送通道: 群机器人 Webhook（最简路径, 无需建应用/审批）。

配置 (本地 .env, 不入库):
    FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxxx

获取方式: 飞书群 → 设置 → 群机器人 → 添加自定义机器人 → 复制 Webhook 地址。
支持签名校验版机器人: 再填 FEISHU_WEBHOOK_SECRET。

富文本限制: webhok 文本消息 150KB; 用 markdown 语法 + at 全体可选。
"""
import base64
import hashlib
import hmac
import os
import time
import urllib.request
import json

from . import config

NL = "\n"


def feishu_ready():
    return bool(os.environ.get("FEISHU_WEBHOOK_URL"))


def _sign(secret, timestamp):
    string_to_sign = "{}\n{}".format(timestamp, secret)
    digest = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _post(payload):
    url = os.environ["FEISHU_WEBHOOK_URL"]
    secret = os.environ.get("FEISHU_WEBHOOK_SECRET")
    if secret:
        ts = str(int(time.time()))
        payload["timestamp"] = ts
        payload["sign"] = _sign(secret, ts)
    proxy = config.PUSH_PROXY or ""
    handler = urllib.request.ProxyHandler(
        {"https": proxy, "http": proxy} if proxy else {})
    opener = urllib.request.build_opener(handler)
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=30) as r:
        return json.loads(r.read())


def push_feishu(digest, txt_path=None):
    """把 digest 推到飞书群。返回 HTTP/业务状态码描述。"""
    if not feishu_ready():
        print("  (未配置 FEISHU_WEBHOOK_URL, 跳过飞书推送)")
        return 0
    m = digest["meta"]
    lines = ["**Signal Vaults 知识日报** ({})".format(
        m.get("chat", "")), ""]
    for i, k in enumerate(digest["hot"][:8], 1):
        lines.append("{}. **{}**".format(i, k.get("topic", "")))
        lines.append("   {}".format(k.get("detail", "")))
    res = digest.get("resources") or []
    if res:
        lines += ["", "**资源/链接**"]
        for r in res[:8]:
            if isinstance(r, dict) and r.get("url"):
                lines.append("- [{}]({})".format(
                    (r.get("title") or r["url"])[:60], r["url"]))
            elif isinstance(r, dict):
                lines.append("- {}".format(r.get("title", "")))
    if txt_path and os.path.exists(txt_path):
        lines += ["", "完整日报: work/{}".format(os.path.basename(txt_path))]

    resp = _post({"msg_type": "text", "content": {"text": NL.join(lines)}})
    code = resp.get("code", resp.get("StatusCode", -1))
    ok = code == 0
    print("  -> 飞书推送 {}".format("OK" if ok else "失败 code={}".format(code)))
    return 200 if ok else code
