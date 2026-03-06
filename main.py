#!/usr/bin/env python3
"""
main.py  —  科研日报助手（打包修复版）
修复了打包 EXE 后无法读取同级目录下 config.yaml 的问题。
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from PyQt5.QtWidgets import QApplication

# 导入原有模块
from fetcher_arxiv import fetch_arxiv_papers, _filter_by_keywords
from fetcher_rss import fetch_rss_papers
from analyzer import PaperAnalyzer
from report_generator import generate_report
from app import MainWindow 

# ── 路径修正逻辑 ──────────────────────────────────────────────────────────────
def get_base_path():
    """获取程序运行时的基础目录（兼容脚本和打包后的 EXE）"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 EXE，返回 EXE 所在的文件夹路径
        return os.path.dirname(sys.executable)
    # 如果是直接运行 Python 脚本，返回脚本所在的文件夹路径
    return os.path.dirname(os.path.abspath(__file__))

# 设置全局基础路径
BASE_DIR = get_base_path()
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
LOG_PATH = os.path.join(BASE_DIR, "tracker.log")

# 修正工作目录，确保后续生成报告和读取文件都在 EXE 同级目录下进行
os.chdir(BASE_DIR)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")

def load_config(path: str) -> dict:
    config_path = Path(path)
    if not config_path.exists():
        logger.warning(f"未找到配置文件: {path}")
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_fetch_task(args, cfg):
    """ 执行后台静默抓取任务 """
    core_keywords = cfg.get("research_profile", {}).get("关键词", [])
    if "arxiv" in cfg:
        cfg["arxiv"]["queries"] = core_keywords
    if "rss" in cfg:
        cfg["rss"]["queries"] = core_keywords

    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    target_date = yesterday.date()
    target_date_str = str(target_date)

    logger.info(f"=== 开始自动抓取任务 [{target_date_str}] ===")
    
    # 抓取逻辑
    arxiv_papers = fetch_arxiv_papers(cfg.get("arxiv", {}), target_date)
    rss_papers = fetch_rss_papers(cfg.get("rss", {}), target_date)
    all_papers = arxiv_papers + rss_papers
    
    if core_keywords:
        all_papers = _filter_by_keywords(all_papers, core_keywords)

    if not all_papers:
        logger.warning("未发现相关论文，任务结束。")
        return

    # AI 分析与报告生成
    analyzer = PaperAnalyzer(llm_cfg=cfg["llm"], research_profile=cfg.get("research_profile", {}))
    scored_papers = analyzer.filter_and_score(all_papers)
    scored_papers.sort(key=lambda x: x.get("score", 0), reverse=True)

    sc = cfg.get("scoring", {})
    highlight = [p for p in scored_papers if p.get("score", 0) >= sc.get("highlight_threshold", 4)][:sc.get("max_highlight", 5)]
    reading   = [p for p in scored_papers if sc.get("read_threshold", 3) <= p.get("score", 0) < sc.get("highlight_threshold", 4)][:sc.get("max_read", 5)]

    highlight = analyzer.analyze_top_papers(highlight)
    reading   = analyzer.analyze_top_papers(reading)
    action_plan_raw = analyzer.generate_action_plan(highlight, reading)

    report_md = generate_report(target_date_str, arxiv_papers, rss_papers, highlight, reading, action_plan_raw)

    # 确保输出目录相对于 BASE_DIR
    output_dir_name = cfg.get("output", {}).get("dir", "./daily")
    output_dir = Path(BASE_DIR) / output_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{target_date_str}.md").write_text(report_md, encoding="utf-8")
    
    logger.info(f"✅ 日报已自动生成。")

def main():
    parser = argparse.ArgumentParser(description="科研日报助手")
    parser.add_argument("--task", action="store_true", help="后台静默抓取模式")
    args = parser.parse_args()

    # 重新加载配置（确保是最新路径）
    cfg = load_config(CONFIG_PATH)

    if args.task:
        # 后台自动抓取
        if not cfg:
            logger.error(f"配置文件缺失，请确保在以下路径存在 config.yaml:\n{CONFIG_PATH}")
            return
        run_fetch_task(args, cfg)
    else:
        # 启动 UI 界面
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        # 创建实例
        win = MainWindow()
        
        # 强制修正 UI 实例中的配置文件路径，防止其指向临时文件夹
        win.cfg_path = CONFIG_PATH
        win.cfg = cfg
        # 触发 UI 重新加载数据
        win.cfg_tab.cfg = win.cfg
        win.cfg_tab.cfg_path = win.cfg_path
        win.cfg_tab._load() 
        
        win.show()
        sys.exit(app.exec())

if __name__ == "__main__":
    main()