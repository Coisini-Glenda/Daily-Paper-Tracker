"""
fetcher_rss.py  —  RSS 订阅抓取模块，精确过滤昨天日期
"""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone, date
from email.utils import parsedate_to_datetime
from typing import List, Dict
import logging
import re
import base64

logger = logging.getLogger(__name__)

ATOM_NS = "http://www.w3.org/2005/Atom"


def fetch_rss_papers(cfg: dict, target_date: date = None) -> List[Dict]:
    if not cfg.get("enabled", True):
        return []

    if target_date is None:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    feeds = cfg.get("feeds", [])
    all_papers: List[Dict] = []

    for feed_cfg in feeds:
        url = feed_cfg.get("url", "").strip()
        name = feed_cfg.get("name", url)
        if not url:
            logger.warning(f"RSS Feed [{name}] URL 为空，跳过")
            continue
        try:
            # 注意这里：把 feed_cfg 传给了 _parse_feed 函数
            papers = _parse_feed(url, name, target_date, feed_cfg)
            all_papers.extend(papers)
            logger.info(f"RSS [{name}] 抓取 {len(papers)} 篇")
        except Exception as e:
            logger.warning(f"RSS [{name}] 抓取失败: {e}")

    logger.info(f"RSS 共抓取 {len(all_papers)} 篇")
    return all_papers


def _parse_feed(url: str, source_name: str, target_date: date, feed_cfg: dict) -> List[Dict]:
    # 增加 feed_cfg 参数来接收配置
    req = urllib.request.Request(url, headers={"User-Agent": "DailyPaperTracker/1.0"})
    
    # 解析并添加账号密码认证（Basic Auth）
    username = feed_cfg.get("username")
    password = feed_cfg.get("password")
    if username and password:
        auth_str = f"{username}:{password}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        req.add_header("Authorization", f"Basic {b64_auth}")

    with urllib.request.urlopen(req, timeout=20) as resp:
        xml_data = resp.read()

    root = ET.fromstring(xml_data)
    tag = root.tag.lower()

    if "feed" in tag or ATOM_NS in tag:
        return _parse_atom(root, source_name, target_date)
    else:
        return _parse_rss2(root, source_name, target_date)


def _parse_rss2(root: ET.Element, source_name: str, target_date: date) -> List[Dict]:
    papers = []
    channel = root.find("channel")
    if channel is None:
        return papers

    for item in channel.findall("item"):
        title = _get_text(item, "title")
        link = _get_text(item, "link")
        description = _get_text(item, "description")
        pub_date_str = _get_text(item, "pubDate")

        published = _parse_date(pub_date_str)

        # 精确匹配目标日期（允许±1天宽容，因为时区差异）
        if published and abs((published.date() - target_date).days) > 1:
            continue

        papers.append({
            "id": link or title,
            "title": title,
            "abstract": _clean_html(description),
            "authors": [],
            "published": str(target_date),
            "url": link,
            "source": f"RSS·{source_name}",
        })
    return papers


def _parse_atom(root: ET.Element, source_name: str, target_date: date) -> List[Dict]:
    ns = {"a": ATOM_NS}
    papers = []

    for entry in root.findall("a:entry", ns):
        title = _get_ns_text(entry, "a:title", ns)
        link_el = entry.find("a:link", ns)
        link = link_el.get("href", "") if link_el is not None else ""
        summary = _get_ns_text(entry, "a:summary", ns)
        updated_str = _get_ns_text(entry, "a:updated", ns)

        published = _parse_iso(updated_str)
        if published and abs((published.date() - target_date).days) > 1:
            continue

        papers.append({
            "id": link or title,
            "title": title,
            "abstract": _clean_html(summary),
            "authors": [],
            "published": str(target_date),
            "url": link,
            "source": f"RSS·{source_name}",
        })
    return papers


def _get_text(elem, tag):
    child = elem.find(tag)
    return child.text.strip() if child is not None and child.text else ""

def _get_ns_text(elem, tag, ns):
    child = elem.find(tag, ns)
    return child.text.strip() if child is not None and child.text else ""

def _parse_date(s):
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except:
        return None

def _parse_iso(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except:
        return None

def _clean_html(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").strip()