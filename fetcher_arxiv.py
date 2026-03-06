"""
fetcher_arxiv.py  —  arXiv 论文抓取模块
使用 arXiv RSS Feed，精确过滤「昨天」日期的论文
"""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone, date
from typing import List, Dict
import time
import logging
import re

logger = logging.getLogger(__name__)

ARXIV_RSS_BASE = "https://rss.arxiv.org/rss/"


def fetch_arxiv_papers(cfg: dict, target_date: date = None) -> List[Dict]:
    """
    抓取指定日期（默认昨天）的 arXiv 论文。
    target_date: 精确匹配的日期，None 则取昨天
    """
    if not cfg.get("enabled", True):
        logger.info("arXiv 抓取已禁用")
        return []

    if target_date is None:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    categories = cfg.get("categories", ["cs.AI", "cs.CL", "cs.LG", "cs.IR", "cs.CV"])
    keywords = cfg.get("queries", [])

    logger.info(f"arXiv 目标日期: {target_date}")

    all_papers: List[Dict] = []
    seen_ids = set()

    for cat in categories:
        logger.info(f"抓取 arXiv 分类: {cat}")
        papers = _fetch_category_rss(cat, target_date)
        for p in papers:
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_papers.append(p)
        time.sleep(1.5)

    # 关键词过滤
    if keywords:
        filtered = _filter_by_keywords(all_papers, keywords)
        logger.info(f"arXiv 关键词过滤: {len(all_papers)} → {len(filtered)} 篇")
        all_papers = filtered

    logger.info(f"arXiv 共抓取 {len(all_papers)} 篇")
    return all_papers


def _fetch_category_rss(category: str, target_date: date) -> List[Dict]:
    url = f"{ARXIV_RSS_BASE}{category}"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "DailyPaperTracker/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            xml_data = resp.read()
    except Exception as e:
        logger.warning(f"arXiv RSS [{category}] 失败: {e}")
        return []

    return _parse_arxiv_rss(xml_data, category, target_date)


def _parse_arxiv_rss(xml_data: bytes, category: str, target_date: date) -> List[Dict]:
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        logger.warning(f"XML 解析失败 [{category}]: {e}")
        return []

    channel = root.find("channel")
    if channel is None:
        return []

    # arXiv RSS 的 pubDate 是该批次的发布时间，不是论文具体日期
    # 论文真实日期在 dc:date 或 description 中，直接取当批次全部即可
    # （arXiv RSS 每天只包含当日新提交，拉到即为最新）
    papers = []
    for item in channel.findall("item"):
        title = _get_text(item, "title").replace("\n", " ").strip()
        link = _get_text(item, "link").strip()
        description = _get_text(item, "description")

        arxiv_id = _extract_arxiv_id(link)
        if not arxiv_id:
            arxiv_id = link

        abstract = _clean_html(description)
        # 新增：利用正则匹配，直接抹除 "Abstract:" 及其之前的所有无用前缀
        abstract = re.sub(r'^.*?Abstract:\s*', '', abstract, flags=re.IGNORECASE | re.DOTALL).strip()
        
        authors = _extract_authors(description)

        papers.append({
            "id": arxiv_id,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "published": str(target_date),   # 标记为目标日期
            "url": link,
            "source": f"arXiv·{category}",
        })

    logger.info(f"  [{category}] 解析到 {len(papers)} 篇")
    return papers


def _filter_by_keywords(papers: List[Dict], keywords: List[str]) -> List[Dict]:
    filtered_papers = []
    for p in papers:
        # 1. 获取标题和摘要，并用句号拼接
        title = p.get("title", "")
        abstract = p.get("abstract", "")
        full_text = f"{title}. {abstract}"
        
        # 2. 按常见的句子结束符（句号、问号、感叹号、分号、换行符）将全文拆分成多个单句
        sentences = re.split(r'[.!?;\n]+', full_text)
        
        matched = False
        for kw in keywords:
            # 将你设定的长关键词拆分成多个单词，比如 ["medical", "llm", "diagnostic", "assessment"]
            parts = kw.strip().lower().split()
            
            # 3. 遍历每一个单句，检查是否【某一句话】同时包含了所有的单词（无序）
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if all(part in sentence_lower for part in parts):
                    matched = True
                    break # 只要找到一句匹配，这篇论文就过关了
            
            if matched:
                break # 只要命中任意一个你的查询规则，就保留论文
                
        if matched:
            filtered_papers.append(p)
            
    return filtered_papers


def _get_text(elem: ET.Element, tag: str) -> str:
    child = elem.find(tag)
    return child.text if child is not None and child.text else ""


def _extract_arxiv_id(url: str) -> str:
    match = re.search(r"arxiv\.org/abs/([^\s?#]+)", url)
    return match.group(1) if match else ""


def _extract_authors(description: str) -> List[str]:
    match = re.search(r"Authors?:\s*([^\n<]+)", description, re.IGNORECASE)
    if match:
        authors_str = _clean_html(match.group(1))
        return [a.strip() for a in authors_str.split(",")][:5]
    return []


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').strip()