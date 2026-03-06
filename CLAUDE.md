# CLAUDE.md — 科研日报项目技能文件

## 项目概述
本项目是一个**每日科研论文自动追踪系统**，每天自动：
1. 从 arXiv 抓取最新论文
2. 从 RSS 订阅抓取期刊论文
3. 使用 AI 分析相关性并评分
4. 生成结构化 Markdown 科研日报

## 项目结构
```
daily-paper-tracker/
├── config.yaml          # ⭐ 核心配置（API、研究方向、关键词）
├── main.py              # 主入口
├── fetcher_arxiv.py     # arXiv 抓取（官方 API，无需 key）
├── fetcher_rss.py       # RSS 订阅抓取
├── analyzer.py          # AI 分析引擎（OpenAI 兼容接口）
├── report_generator.py  # Markdown 报告生成
├── daily/               # 报告输出目录（自动创建）
└── tracker.log          # 运行日志
```

## 配置说明（config.yaml）

### 必须修改的字段
```yaml
llm:
  api_key: "YOUR_API_KEY_HERE"   # 替换为真实 API Key
  model: "gpt-4o"                 # 替换为你使用的模型
```

### 自定义研究方向
```yaml
research_profile:
  关键词:
  - 关键词1
  - 关键词2

  详细的研究方向: 关于你研究方向的详细描述，用于筛选论文的相关性.
```

### 添加 RSS 订阅源
```yaml
rss:
  feeds:
    - name: "期刊名称"
      url: "https://your-rss-feed-url"
```

## 输出格式
报告保存在 `daily/YYYY-MM-DD.md`，包含：
- 📊 数据来源统计
- 🔥 重点关注（≥4星，最多5篇）
- 📖 深入阅读（3-4星，最多5篇）
- 📌 今日行动建议（必读/深入阅读/思考问题）
- 💡 研究启示

