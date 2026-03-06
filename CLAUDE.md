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
├── setup_cron.sh        # 一键配置 cron
├── daily/               # 报告输出目录（自动创建）
└── tracker.log          # 运行日志
```

## 常用命令

```bash
# 安装依赖
pip install pyyaml

# 测试运行（不调用 AI）
python main.py --dry-run

# 生成今日报告
python main.py

# 生成指定日期报告
python main.py --date 2026-03-01

# 配置定时任务（每天 09:00 自动运行）
bash setup_cron.sh

# 查看运行日志
tail -f tracker.log
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
  主方向: "你的研究方向"
  子方向:
    - "子方向1"
    - "子方向2"
  关键词:
    - keyword1
    - keyword2
```

### 添加 arXiv 搜索词
```yaml
arxiv:
  queries:
    - "新关键词"
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

## 常见问题

**Q: API 调用失败？**
检查 `config.yaml` 中的 `base_url`、`api_key`、`model` 是否正确。

**Q: arXiv 没有论文？**
调整 `arxiv.days_back`（默认2天），或检查 `queries` 关键词。

**Q: 报告质量不好？**
在 `research_profile` 中补充更多子方向和关键词，让 AI 判断更准确。

**Q: 修改每天运行时间？**
运行 `crontab -e`，修改时间格式：`分 时 * * *`
例如 `30 8 * * *` = 每天 08:30。
