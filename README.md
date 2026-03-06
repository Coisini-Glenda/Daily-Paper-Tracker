## 🔬 科研日报助手 (Daily Paper Tracker)
科研日报助手 是一个基于 Python 和大语言模型 (LLM) 的全自动论文追踪系统。它旨在帮助科研人员从信息过载中解脱，每天自动筛选、分析并生成量身定制的科研简报。

## 🌟 核心功能
多源自动化抓取：支持从 arXiv（按分类）和 RSS 订阅源（如 IEEE TMI、Nature、Medical Image Analysis 等）实时检索最新论文。

精准语义过滤：内置“单句无序匹配”过滤逻辑，确保论文标题或摘要中的关键语境与您的研究方向高度匹配。

AI 智能评分与深度分析：利用 LLM (如 GPT-4o, o3-mini) 对每篇论文进行 1-5 分的相关性打分，并为高分论文生成中文摘要及研究启示。

## 双模式灵活运行：

GUI 配置模式：直观的深色系图形界面，用于修改 API Key、关键词、研究方向及设置定时任务。

静默抓取模式：支持 --task 参数，由系统定时任务调用，在后台静默完成所有工作并生成报告。

自动化行动计划：AI 会根据当日论文给出“必读”、“深入阅读”建议以及启发性的思考问题。

美观的 Markdown 报告：自动生成排版精美的 Markdown 文件，支持通过内置浏览器或系统默认浏览器预览。

## 📂 项目结构
```Plaintext
daily-paper-tracker
├── main.py              # 程序入口：协调 UI 启动与后台任务
├── app.py               # 图形界面：基于 PyQt5 的配置与报告管理
├── analyzer.py          # AI 引擎：处理 LLM 评分、深度分析与行动计划
├── fetcher_arxiv.py     # 抓取模块：处理 arXiv RSS API 数据
├── fetcher_rss.py       # 抓取模块：处理通用期刊 RSS 订阅
├── report_generator.py  # 渲染模块：生成结构化 Markdown 报告
├── config.yaml          # 配置文件：存储 API Key、研究方向与评分规则
├── setup_task.bat       # 自动化工具：一键创建 Windows 定时任务计划
└── daily/               # 报告目录：按日期存放生成的 Markdown 日报
```

## 🚀 快速上手
1. 环境准备
项目支持直接运行 Python 脚本或打包为 EXE 使用。
若直接运行，请安装依赖：

Bash
pip install pyyaml PyQt5 requests markdown2
2. 配置与使用
启动界面：双击 DailyPaperTracker.exe 或运行 python main.py 开启配置界面。

设置研究画像：在“配置”页填入您的关键词（如 Medical LLM）和详细研究方向。

填写 API Key：填入兼容 OpenAI 接口的 API Key 和 Base URL。

保存并测试：点击“保存配置”并尝试“开始生成今日日报”。

3. 实现每日自动追踪
在 UI 界面设置“自动运行时间”（如 09:00）并保存。

右键以管理员身份运行目录下的 setup_task.bat。

系统将每天准时在后台执行抓取任务，您只需通过 UI 界面或 daily/ 文件夹查看新报告即可。

## ⚙️ 配置说明 (config.yaml)
research_profile：定义您的研究兴趣，包括核心关键词和一段详细的科研背景描述，这是 AI 评分的重要依据。

scoring：设置重点关注（Highlight）和深入阅读（Read）的分数阈值。

rss.feeds：可以自由添加任何期刊的 RSS 链接。

## 📝 报告示例
生成的日报包含：

### 📊 数据来源统计：直观展示抓取到的论文数量。

### 🔥 重点关注：AI 评定的 4-5 分论文，含中文摘要及关联分析。

### 📌 今日行动建议：AI 提炼的论文要点及针对性的思考问题。

###💡 研究启示：预留的手动记录区域，方便记录灵感。
