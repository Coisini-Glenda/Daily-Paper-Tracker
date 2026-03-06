"""
analyzer.py  —  AI 分析引擎
修复：401 时立即抛出，不静默吞掉；空列表时跳过 API 调用
"""

import json
import urllib.request
import urllib.error
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PaperAnalyzer:
    def __init__(self, llm_cfg: dict, research_profile: dict):
        self.base_url = llm_cfg["base_url"]
        self.api_key = llm_cfg["api_key"]
        self.model = llm_cfg["model"]
        self.timeout = llm_cfg.get("timeout", 60)
        self.max_tokens = llm_cfg.get("max_tokens", 4000)
        self.profile = research_profile

        # 启动时检查 key 是否为占位符
        if not self.api_key or self.api_key == "YOUR_API_KEY_HERE":
            raise ValueError(
                "\n\n❌ 请先在 config.yaml 中填写真实的 api_key！\n"
                "   找到这一行并替换：\n"
                '   api_key: "YOUR_API_KEY_HERE"\n'
            )

    # ------------------------------------------------------------------

    def filter_and_score(self, papers: List[Dict]) -> List[Dict]:
        if not papers:
            return []
        BATCH = 15
        scored = []
        for i in range(0, len(papers), BATCH):
            batch = papers[i: i + BATCH]
            scored.extend(self._score_batch(batch))
        return scored

    def analyze_top_papers(self, papers: List[Dict]) -> List[Dict]:
        results = []
        for p in papers:
            try:
                analysis = self._deep_analyze(p)
                p.update(analysis)
            except Exception as e:
                logger.warning(f"深度分析失败 [{p['title'][:40]}]: {e}")
                p["zh_summary"] = p.get("abstract", "")[:300]
                p["relevance"] = "分析失败"
                p["insight"] = ""
            results.append(p)
        return results

    def generate_action_plan(self, highlight: List[Dict], reading: List[Dict]) -> str:
        """生成行动建议，若无论文则返回空字符串跳过 API 调用"""
        if not highlight and not reading:
            logger.info("无高分论文，跳过行动计划生成")
            return ""

        titles_h = [f"{i+1}. {p['title']}" for i, p in enumerate(highlight)]
        titles_r = [f"{i+1}. {p['title']}" for i, p in enumerate(reading)]
        profile_str = self._profile_str()

        prompt = f"""你是一名资深科研助手。根据今日论文和研究者背景，生成行动建议。

研究者背景：
{profile_str}

重点关注论文：
{chr(10).join(titles_h) if titles_h else "无"}

深入阅读论文：
{chr(10).join(titles_r) if titles_r else "无"}

请严格按以下 JSON 格式输出，不要有多余文字：
{{
  "must_read": [
    {{
      "title": "论文标题",
      "key_point": "一句话核心贡献",
      "thinking": "结合研究方向的问题"
    }}
  ],
  "deep_read": [
    {{
      "title": "论文标题",
      "key_point": "重点：一句话核心贡献",
      "thinking": "思考：结合研究方向的问题"
    }}
  ],
  "questions": [
    "思考问题1",
    "思考问题2",
    "思考问题3",
    "思考问题4",
    "思考问题5"
  ]
}}
"""
        return self._call_api(prompt)

    # ------------------------------------------------------------------

    def _score_batch(self, papers: List[Dict]) -> List[Dict]:
        profile_str = self._profile_str()
        papers_text = "\n\n".join([
            f"[{i}] 标题: {p['title']}\n摘要: {p['abstract'][:500]}"
            for i, p in enumerate(papers)
        ])

        prompt = f"""你是科研助手，请评估每篇论文与研究方向的相关性（1-5分）。

研究方向：
{profile_str}

请严格按以下标准打分：
5分：高度相关（直接命中核心研究，必读）
4分：相关（涉及相关技术或应用场景，值得参考）
3分：部分相关（底层方法或视角有启发，但应用领域有差异）
2分：边缘相关（仅仅提到了某些通用的关键词，研究重点完全不同）
1分：毫不相关（完全无关的研究领域）


论文列表：
{papers_text}

严格按以下 JSON 格式输出，不要有多余文字：
[
  {{"index": 0, "score": 5, "reason": "一句话理由"}},
  {{"index": 1, "score": 2, "reason": "一句话理由"}}
]
每篇论文必须有对应条目，index 从 0 开始。
"""
        try:
            raw = self._call_api(prompt)
            scores = self._parse_json(raw)
            score_map = {item["index"]: item for item in scores}
            for i, p in enumerate(papers):
                info = score_map.get(i, {})
                p["score"] = int(info.get("score", 1))
                p["score_reason"] = info.get("reason", "")
        except urllib.error.HTTPError as e:
            # 401/403 直接往上抛，不静默
            if e.code in (401, 403):
                raise
            logger.warning(f"批量评分 HTTP 错误 {e.code}: {e}")
            for p in papers:
                p["score"] = 1
                p["score_reason"] = ""
        except Exception as e:
            logger.warning(f"批量评分解析失败: {e}")
            for p in papers:
                p["score"] = 1
                p["score_reason"] = ""
        return papers

    def _deep_analyze(self, paper: Dict) -> Dict:
        profile_str = self._profile_str()
        prompt = f"""请对以下论文进行深度分析。

研究方向：
{profile_str}

论文标题：{paper['title']}
论文摘要：{paper['abstract'][:1000]}

严格按以下 JSON 格式输出，不要有多余文字：
{{
  "zh_summary": "中文摘要（150字以内）",
  "relevance": "与研究方向的关联（50字以内）",
  "insight": "对研究的启示（50字以内）"
}}
"""
        raw = self._call_api(prompt)
        return self._parse_json(raw)

    def _call_api(self, prompt: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "temperature": 0.3,
        }).encode("utf-8")

        req = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            logger.error(f"API 请求失败 {e.code}: {body[:200]}")
            raise

    def _parse_json(self, text: str) -> Any:
        import re
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()
        return json.loads(text)

    def _profile_str(self) -> str:
        # 直接读取配置文件中设定的“完整的科研方向描述”
        return self.profile.get("详细的研究方向")