"""
report_generator.py  —  Markdown 报告生成器
输出格式完全对齐"科研日报"截图效果
"""

import json
from datetime import datetime
from typing import List, Dict, Any


def generate_report(
    date_str: str,
    arxiv_papers: List[Dict],
    rss_papers: List[Dict],
    highlight: List[Dict],
    reading: List[Dict],
    action_plan_raw: str,
) -> str:
    """
    生成完整的 Markdown 科研日报。
    """
    today = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]

    # 解析行动计划
    action = _safe_parse(action_plan_raw)

    lines = []

    # ── 标题 ──────────────────────────────────────────────
    lines += [
        "# 📅 科研日报",
        "",
        f"> 生成时间：{date_str}  "
        f"数据来源：RSS订阅 + arXiv  "
        f"说明：今日（{date_str}，{weekday}）",
        "",
    ]

    # ── 数据来源统计 ───────────────────────────────────────
    lines += [
        "## 📊 数据来源统计",
        "",
        "| 来源 | 论文数量 |",
        "|------|----------|",
        f"| RSS订阅 | {len(rss_papers)} 篇 |",
        f"| arXiv | {len(arxiv_papers)} 篇 |",
        "",
    ]

    # ── 重点关注 ───────────────────────────────────────────
    stars = "⭐" * 5
    lines += [
        f"## 🔥 重点关注 （{stars}）",
        "",
    ]
    if highlight:
        for p in highlight:
            score_stars = "⭐" * p.get("score", 5)
            lines += [
                    f"### {p['title']}",
                    "",
                    f"- **English Abstract**: {p.get('abstract', '无')}",
                    f"- **中文摘要**: {p.get('zh_summary', '无')}",
                    f"- **与你研究的关联**: {p.get('relevance', p.get('score_reason', ''))}",
                    f"- **链接**: {p.get('url', '')}",
                    f"- **来源**: {p.get('source', 'arXiv')} | {p.get('published', '')} | {score_stars}",
                    "",
                ]
    else:
        lines += ["暂无高度相关论文。", ""]

    # ── 深入阅读 ───────────────────────────────────────────
    lines += [
        "## 📖 深入阅读",
        "",
    ]
    if reading:
        for p in reading:
            score_stars = "⭐" * p.get("score", 3)
            lines += [
                    f"### {p['title']}",
                    "",
                    f"- **English Abstract**: {p.get('abstract', '无')}",
                    f"- **中文摘要**: {p.get('zh_summary', '无')}",
                    f"- **与你研究的关联**: {p.get('relevance', p.get('score_reason', ''))}",
                    f"- **链接**: {p.get('url', '')}",
                    f"- **来源**: {p.get('source', 'arXiv')} | {p.get('published', '')} | {score_stars}",
                    "",
                ]
    else:
        lines += ["暂无推荐论文。", ""]

    # ── 今日行动建议 ──────────────────────────────────────
    lines += [
        "## 📌 今日行动建议",
        "",
    ]

    if action:
        # 必读论文
        must_read = action.get("must_read", [])
        if must_read:
            lines += ["### 必读论文", ""]
            for i, item in enumerate(must_read, 1):
                lines += [
                    f"{i}. **{item.get('title', '')}**",
                    f"   - 重点：{item.get('key_point', '')}",
                    f"   - 思考：{item.get('thinking', '')}",
                    "",
                ]

        # 深入阅读
        deep_read = action.get("deep_read", [])
        if deep_read:
            lines += ["### 深入阅读", ""]
            for i, item in enumerate(deep_read, 1):
                lines += [
                    f"{i}. **{item.get('title', '')}**",
                    f"   - 重点：{item.get('key_point', '')}",
                    f"   - 思考：{item.get('thinking', '')}",
                    "",
                ]

        # 思考问题
        questions = action.get("questions", [])
        if questions:
            lines += ["### 思考问题", ""]
            for i, q in enumerate(questions, 1):
                lines += [f"{i}. {q}"]
            lines += [""]

    # ── 研究启示 ──────────────────────────────────────────
    lines += [
        "## 💡 研究启示",
        "",
        "> （请在此处手动记录今日阅读后的思考、实验灵感或交叉想法...）",
        "",
    ]

    # ── 页脚 ──────────────────────────────────────────────
    lines += [
        "---",
        "",
        f"*本日报由科研助手自动生成 | 保存路径：daily/{date_str}.md*",
    ]

    return "\n".join(lines)


def _safe_parse(raw: str) -> Dict[str, Any]:
    """容错解析 JSON"""
    if not raw:
        return {}
    try:
        import re
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("```").strip()
        return json.loads(cleaned)
    except Exception:
        return {}
