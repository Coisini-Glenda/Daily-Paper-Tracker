#!/usr/bin/env python3
"""
app.py  —  科研日报助手 GUI
依赖：pip install PyQt5 markdown2 pyyaml
运行：python app.py
"""

import sys
import os
import json
import re
import tempfile
import webbrowser
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QTabWidget,
    QProgressBar, QFrame, QGroupBox, QGridLayout,
    QComboBox, QTextBrowser, QMessageBox, QFileDialog, QSpinBox, QTimeEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl, QTime
from PyQt5.QtGui import QDesktopServices, QTextCursor

# ── 全局样式 ──────────────────────────────────────────────────────────────────
STYLE = """
QMainWindow, QWidget {
    background-color: #0f1117;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
    font-size: 14px;
}
QTabWidget::pane {
    border: 1px solid #2d3748;
    border-radius: 8px;
    background-color: #1a1d2e;
}
QTabBar::tab {
    background-color: #1a1d2e;
    color: #718096;
    padding: 10px 28px;
    border: none;
    font-size: 13px;
    font-weight: 500;
}
QTabBar::tab:selected {
    color: #7c6af7;
    border-bottom: 2px solid #7c6af7;
}
QTabBar::tab:hover:!selected { color: #a0aec0; }

QPushButton {
    background-color: #7c6af7;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 22px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover    { background-color: #6b5ce7; }
QPushButton:pressed  { background-color: #5a4bd1; }
QPushButton:disabled { background-color: #2d3748; color: #4a5568; }
QPushButton#secondary {
    background-color: #252840;
    color: #a0aec0;
    border: 1px solid #2d3748;
}
QPushButton#secondary:hover { background-color: #2d3748; }

QLineEdit, QTextEdit, QSpinBox, QTimeEdit {
    background-color: #1e2130;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 9px 12px;
    color: #e2e8f0;
    selection-background-color: #7c6af7;
}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QTimeEdit:focus { border: 1px solid #7c6af7; }
QSpinBox::up-button, QTimeEdit::up-button, QSpinBox::down-button, QTimeEdit::down-button {
    background: #2d3748; border-radius: 2px; width: 16px;
}

QComboBox {
    background-color: #1e2130;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e2e8f0;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #1e2130;
    border: 1px solid #2d3748;
    selection-background-color: #7c6af7;
    color: #e2e8f0;
}

QProgressBar {
    background-color: #1e2130;
    border: none;
    border-radius: 5px;
    height: 10px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7c6af7, stop:1 #38bdf8);
    border-radius: 5px;
}

QGroupBox {
    border: 1px solid #2d3748;
    border-radius: 10px;
    margin-top: 16px;
    padding: 14px 12px 10px 12px;
    font-weight: 600;
    color: #a0aec0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
    color: #7c6af7;
}

QTextEdit#logArea {
    background-color: #0d1117;
    border: 1px solid #1e2130;
    border-radius: 8px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 12px;
    color: #8b949e;
    padding: 8px;
}

QTextBrowser#reportView {
    background-color: #0f1117;
    border: none;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
    font-size: 15px;
    padding: 32px 48px;
    line-height: 1.8;
}
"""

# ── Markdown → HTML 渲染 ──────────────────────────────────────────────────────
def md_to_html(md_content: str) -> str:
    lines = md_content.split("\n")
    html_lines = []
    in_table, in_code, in_ul, in_ol = False, False, False, False

    def close_lists():
        nonlocal in_ul, in_ol
        r = []
        if in_ul: r.append("</ul>"); in_ul = False
        if in_ol: r.append("</ol>"); in_ol = False
        return r

    def inline(text):
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
        text = re.sub(r'\[(.+?)\]\((https?://[^\)]+)\)', r'<a href="\2">\1</a>', text)
        text = re.sub(r'(?<!["\(])(https?://\S+)', r'<a href="\1">\1</a>', text)
        return text

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            if in_code:
                html_lines.append("</pre></code>")
                in_code = False
            else:
                html_lines.extend(close_lists())
                html_lines.append('<code><pre style="background:#1e2130;border:1px solid #2d3748;border-radius:8px;padding:14px;overflow-x:auto;color:#e2e8f0;font-family:Consolas,monospace;font-size:13px;">')
                in_code = True
            i += 1; continue

        if in_code:
            html_lines.append(line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            i += 1; continue

        if line.startswith("######"):
            html_lines.extend(close_lists()); html_lines.append(f'<h6 style="color:#a0aec0;margin:0.8em 0 0.3em;">{inline(line[6:].strip())}</h6>')
        elif line.startswith("#####"):
            html_lines.extend(close_lists()); html_lines.append(f'<h5 style="color:#a0aec0;margin:0.8em 0 0.3em;">{inline(line[5:].strip())}</h5>')
        elif line.startswith("####"):
            html_lines.extend(close_lists()); html_lines.append(f'<h4 style="color:#e2e8f0;margin:0.9em 0 0.3em;">{inline(line[4:].strip())}</h4>')
        elif line.startswith("###"):
            html_lines.extend(close_lists()); html_lines.append(f'<h3 style="color:#e2e8f0;font-size:1.1em;margin:1em 0 0.3em;padding-bottom:4px;border-bottom:1px solid #2d3748;">{inline(line[3:].strip())}</h3>')
        elif line.startswith("##"):
            html_lines.extend(close_lists()); html_lines.append(f'<h2 style="color:#38bdf8;font-size:1.4em;margin:1.2em 0 0.4em;padding-bottom:6px;border-bottom:2px solid #1e2130;">{inline(line[2:].strip())}</h2>')
        elif line.startswith("#"):
            html_lines.extend(close_lists()); html_lines.append(f'<h1 style="color:#7c6af7;font-size:1.9em;margin:0.8em 0 0.5em;padding-bottom:8px;border-bottom:2px solid #2d3748;">{inline(line[1:].strip())}</h1>')
        elif re.match(r'^---+$', line.strip()):
            html_lines.extend(close_lists()); html_lines.append('<hr style="border:none;border-top:1px solid #2d3748;margin:1.5em 0;">')
        elif line.startswith(">"):
            html_lines.extend(close_lists()); html_lines.append(f'<blockquote style="border-left:3px solid #7c6af7;padding:8px 16px;margin:12px 0;background:#1a1d2e;border-radius:0 8px 8px 0;color:#a0aec0;">{inline(line[1:].strip())}</blockquote>')
        elif "|" in line and line.strip().startswith("|"):
            if not in_table:
                html_lines.extend(close_lists()); html_lines.append('<table style="border-collapse:collapse;width:100%;margin:12px 0;">'); in_table = True
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                html_lines.append("<thead><tr>" + "".join(f'<th style="background:#1e2130;color:#7c6af7;padding:10px 14px;text-align:left;border:1px solid #2d3748;">{inline(c)}</th>' for c in cells) + "</tr></thead><tbody>")
            elif re.match(r'^[\|\s\-:]+$', line): pass
            else:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                html_lines.append("<tr>" + "".join(f'<td style="padding:9px 14px;border:1px solid #2d3748;color:#cbd5e0;">{inline(c)}</td>' for c in cells) + "</tr>")
        else:
            if in_table: html_lines.append("</tbody></table>"); in_table = False
            ul_match = re.match(r'^(\s*)[-*+]\s+(.+)', line)
            if ul_match:
                if not in_ul: html_lines.append('<ul style="padding-left:1.5em;margin:0.5em 0;">'); in_ul = True
                html_lines.append(f'<li style="margin:0.3em 0;color:#cbd5e0;">{inline(ul_match.group(2))}</li>')
            elif re.match(r'^\d+\.\s+', line):
                txt = re.sub(r'^\d+\.\s+', '', line)
                if not in_ol: html_lines.append('<ol style="padding-left:1.5em;margin:0.5em 0;">'); in_ol = True
                html_lines.append(f'<li style="margin:0.3em 0;color:#cbd5e0;">{inline(txt)}</li>')
            elif line.strip() == "":
                html_lines.extend(close_lists()); html_lines.append("<br>")
            else:
                html_lines.extend(close_lists()); html_lines.append(f'<p style="margin:0.4em 0;color:#cbd5e0;">{inline(line)}</p>')
        i += 1

    html_lines.extend(close_lists())
    if in_table: html_lines.append("</tbody></table>")
    body = "\n".join(html_lines)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
* {{ box-sizing: border-box; }}
body {{ background:#0f1117; color:#e2e8f0; font-family:'Segoe UI',sans-serif; font-size:15px; line-height:1.8; padding:32px 56px; max-width:960px; margin:0 auto; }}
a {{ color:#7c6af7; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
code {{ background:#1e2130; color:#f6c90e; padding:2px 6px; border-radius:4px; font-family:Consolas,monospace; font-size:0.9em; }}
strong {{ color:#e2e8f0; }} em {{ color:#a0aec0; }}
</style></head><body>{body}</body></html>"""

# ── Worker Thread ─────────────────────────────────────────────────────────────
class PaperWorker(QThread):
    sig_progress = pyqtSignal(int, str)
    sig_log      = pyqtSignal(str, str)
    sig_finished = pyqtSignal(str, str)
    sig_failed   = pyqtSignal(str)

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg

    def run(self):
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from fetcher_arxiv import fetch_arxiv_papers
            from fetcher_rss import fetch_rss_papers
            from analyzer import PaperAnalyzer
            from report_generator import generate_report

            cfg = self.cfg
            target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()
            date_str = str(target_date)

            self.sig_progress.emit(5, "抓取 arXiv 论文")
            self.sig_log.emit("开始抓取 arXiv 论文...", "info")
            arxiv_papers = fetch_arxiv_papers(cfg.get("arxiv", {}), target_date)
            self.sig_log.emit(f"✅ arXiv 完成：{len(arxiv_papers)} 篇", "success")

            self.sig_progress.emit(20, "抓取 RSS 订阅")
            self.sig_log.emit("开始抓取 RSS 订阅...", "info")
            rss_papers = fetch_rss_papers(cfg.get("rss", {}), target_date)
            self.sig_log.emit(f"✅ RSS 完成：{len(rss_papers)} 篇", "success")

            all_papers = arxiv_papers + rss_papers
            self.sig_log.emit(f"📚 初始共抓取 {len(all_papers)} 篇（arXiv: {len(arxiv_papers)}, RSS: {len(rss_papers)}）", "info")

            # ── 新增：对所有来源(arXiv+RSS)执行统一的【单句无序匹配】过滤 ──
            from fetcher_arxiv import _filter_by_keywords
            core_keywords = cfg.get("research_profile", {}).get("关键词", [])
            if core_keywords:
                self.sig_log.emit("🔍 正在执行严格的单句关键词匹配过滤...", "info")
                all_papers = _filter_by_keywords(all_papers, core_keywords)
                self.sig_log.emit(f"🎯 过滤后最终剩余: {len(all_papers)} 篇", "success")
            # ────────────────────────────────────────────────────────────

            if not all_papers:
                self.sig_log.emit("今日没有符合关键词的论文。", "warn")
                self.sig_failed.emit("未抓取到符合要求的论文（已被关键词全部过滤），请明天再试或修改关键词。")
                return

            self.sig_progress.emit(40, "AI 批量评分")
            self.sig_log.emit(f"🤖 AI 批量评分中（仅对过滤后的 {len(all_papers)} 篇）...", "info")


            self.sig_log.emit(f"AI 批量评分中（共 {len(all_papers)} 篇）...", "info")
            analyzer = PaperAnalyzer(
                llm_cfg=cfg["llm"],
                research_profile=cfg.get("research_profile", {}),
            )
            scored = analyzer.filter_and_score(all_papers)
            scored.sort(key=lambda x: x.get("score", 0), reverse=True)

            sc = cfg.get("scoring", {})
            ht = sc.get("highlight_threshold", 4)
            rt = sc.get("read_threshold", 2)
            highlight = [p for p in scored if p.get("score", 0) >= ht][:sc.get("max_highlight", 5)]
            reading   = [p for p in scored if rt <= p.get("score", 0) < ht][:sc.get("max_read", 5)]
            self.sig_log.emit(f"✅ 评分完成：重点关注 {len(highlight)} 篇，深入阅读 {len(reading)} 篇", "success")

            self.sig_progress.emit(65, "深度分析高分论文")
            self.sig_log.emit("深度分析高分论文...", "info")
            highlight = analyzer.analyze_top_papers(highlight)
            reading   = analyzer.analyze_top_papers(reading)
            self.sig_log.emit("✅ 深度分析完成", "success")

            self.sig_progress.emit(85, "生成行动建议")
            self.sig_log.emit("生成今日行动建议...", "info")
            action_plan_raw = analyzer.generate_action_plan(highlight, reading)
            self.sig_log.emit("✅ 行动建议完成", "success")

            self.sig_progress.emit(95, "生成 Markdown 报告")
            self.sig_log.emit("生成 Markdown 日报...", "info")
            report_md = generate_report(
                date_str=date_str,
                arxiv_papers=arxiv_papers,
                rss_papers=rss_papers,
                highlight=highlight,
                reading=reading,
                action_plan_raw=action_plan_raw,
            )

            output_dir = Path(cfg.get("output", {}).get("dir", "./daily"))
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{date_str}.md"
            output_path.write_text(report_md, encoding="utf-8")

            self.sig_progress.emit(100, "完成 ✅")
            self.sig_log.emit(f"🎉 报告已保存：{output_path}", "success")
            self.sig_finished.emit(str(output_path), report_md)

        except Exception as e:
            import traceback
            self.sig_failed.emit(f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}")

# ── Config Tab ────────────────────────────────────────────────────────────────
class ConfigTab(QWidget):
    def __init__(self, cfg: dict, cfg_path: str):
        super().__init__()
        self.cfg = cfg
        self.cfg_path = cfg_path
        self._build()
        self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(14)

        # 顶层网络布局 (2列)
        grid = QGridLayout()
        grid.setSpacing(16)

        # [左上] API
        api_g = QGroupBox("🔑  API 设置")
        gl = QGridLayout(api_g)
        gl.addWidget(QLabel("Base URL"), 0, 0)
        self.url_input = QLineEdit()
        gl.addWidget(self.url_input, 0, 1)
        gl.addWidget(QLabel("API Key"), 1, 0)
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        gl.addWidget(self.key_input, 1, 1)
        gl.addWidget(QLabel("Model"), 2, 0)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems(["o3-mini", "gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"])
        gl.addWidget(self.model_combo, 2, 1)
        grid.addWidget(api_g, 0, 0)

        # [右上] 研究方向
        rg = QGroupBox("🔬  研究方向")
        rgl = QGridLayout(rg)
        rgl.addWidget(QLabel("关键词（用“；”分割开）"), 0, 0)
        self.keywords = QLineEdit()
        rgl.addWidget(self.keywords, 0, 1)
        rgl.addWidget(QLabel("详细描述"), 1, 0, Qt.AlignmentFlag.AlignTop)
        self.research_detail = QTextEdit()
        self.research_detail.setFixedHeight(85)
        rgl.addWidget(self.research_detail, 1, 1)
        grid.addWidget(rg, 0, 1)

        # [左下] 评分配置
        sg = QGroupBox("📊  评分与显示规则 (1-5分)")
        sgl = QGridLayout(sg)
        
        sgl.addWidget(QLabel("⭐ 重点关注最低分:"), 0, 0)
        self.ht_spin = QSpinBox(); self.ht_spin.setRange(1, 5)
        sgl.addWidget(self.ht_spin, 0, 1)
        
        sgl.addWidget(QLabel("📚 深入阅读最低分:"), 1, 0)
        self.rt_spin = QSpinBox(); self.rt_spin.setRange(1, 5)
        sgl.addWidget(self.rt_spin, 1, 1)
        
        sgl.addWidget(QLabel("重点关注最大篇数:"), 0, 2)
        self.mh_spin = QSpinBox(); self.mh_spin.setRange(1, 20)
        sgl.addWidget(self.mh_spin, 0, 3)
        
        sgl.addWidget(QLabel("深入阅读最大篇数:"), 1, 2)
        self.mr_spin = QSpinBox(); self.mr_spin.setRange(1, 20)
        sgl.addWidget(self.mr_spin, 1, 3)
        grid.addWidget(sg, 1, 0)

        # [右下] 系统自动化设置
        sysg = QGroupBox("⚙️  系统与自动化设置")
        sysgl = QGridLayout(sysg)
        sysgl.addWidget(QLabel("📁 报告保存位置:"), 0, 0)
        
        out_row = QHBoxLayout()
        self.out_input = QLineEdit()
        out_row.addWidget(self.out_input)
        self.out_btn = QPushButton("浏览")
        self.out_btn.setObjectName("secondary")
        self.out_btn.setFixedHeight(34)
        self.out_btn.clicked.connect(self._browse_dir)
        out_row.addWidget(self.out_btn)
        sysgl.addLayout(out_row, 0, 1)

        sysgl.addWidget(QLabel("⏰ 自动运行时间:"), 1, 0)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        sysgl.addWidget(self.time_edit, 1, 1)
        
        grid.addWidget(sysg, 1, 1)
        root.addLayout(grid)

        root.addStretch()

        # 按钮行
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("💾  保存配置")
        self.save_btn.setObjectName("secondary")
        self.save_btn.setFixedHeight(40)
        self.save_btn.clicked.connect(self.save_config)
        btn_row.addWidget(self.save_btn)
        btn_row.addStretch()

        self.run_btn = QPushButton("▶   开始生成今日日报")
        self.run_btn.setFixedHeight(44)
        self.run_btn.setMinimumWidth(200)
        btn_row.addWidget(self.run_btn)
        root.addLayout(btn_row)

    def _browse_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择报告保存位置", self.out_input.text())
        if dir_path:
            self.out_input.setText(dir_path)

    def _load(self):
        llm = self.cfg.get("llm", {})
        self.url_input.setText(llm.get("base_url", ""))
        self.key_input.setText("" if llm.get("api_key", "") == "YOUR_API_KEY_HERE" else llm.get("api_key", ""))
        self.model_combo.setCurrentText(llm.get("model", "o3-mini"))

        rp = self.cfg.get("research_profile", {})
        self.keywords.setText("；".join(rp.get("关键词", [])))
        self.research_detail.setPlainText(rp.get("详细的研究方向", ""))

        sc = self.cfg.get("scoring", {})
        self.ht_spin.setValue(sc.get("highlight_threshold", 4))
        self.rt_spin.setValue(sc.get("read_threshold", 2))
        self.mh_spin.setValue(sc.get("max_highlight", 5))
        self.mr_spin.setValue(sc.get("max_read", 5))

        self.out_input.setText(self.cfg.get("output", {}).get("dir", "./daily"))
        
        t_str = self.cfg.get("system", {}).get("schedule_time", "09:00")
        self.time_edit.setTime(QTime.fromString(t_str, "HH:mm"))

    def get_cfg(self) -> dict:
        cfg = json.loads(json.dumps(self.cfg))
        cfg.setdefault("llm", {})
        cfg["llm"]["base_url"] = self.url_input.text().strip()
        cfg["llm"]["api_key"]  = self.key_input.text().strip()
        cfg["llm"]["model"]    = self.model_combo.currentText().strip()
        
        kws = [k.strip() for k in re.split(r'[；;，,]', self.keywords.text()) if k.strip()]
        cfg["research_profile"] = {
            "关键词": kws,
            "详细的研究方向": self.research_detail.toPlainText().strip(),
        }

        cfg.setdefault("scoring", {})
        cfg["scoring"]["highlight_threshold"] = self.ht_spin.value()
        cfg["scoring"]["read_threshold"] = self.rt_spin.value()
        cfg["scoring"]["max_highlight"] = self.mh_spin.value()
        cfg["scoring"]["max_read"] = self.mr_spin.value()

        cfg.setdefault("output", {})
        cfg["output"]["dir"] = self.out_input.text().strip()
        
        cfg.setdefault("system", {})
        cfg["system"]["schedule_time"] = self.time_edit.time().toString("HH:mm")
        
        return cfg

    def save_config(self):
        cfg = self.get_cfg()
        with open(self.cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, sort_keys=False)
        self.cfg = cfg

        # 尝试自动修改 Windows 计划任务时间
        time_str = cfg["system"]["schedule_time"]
        msg = f"配置已保存到\n{self.cfg_path}"
        
        try:
            # 尝试更改已经存在的 DailyPaperTracker 任务
            cmd = f'schtasks /Change /TN "DailyPaperTracker" /ST {time_str}'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                msg += f"\n\n✅ Windows 定时任务已自动同步为每天 {time_str} 运行。"
            else:
                msg += f"\n\n⚠️ 定时任务时间未同步。\n如果你还没配置过定时运行，请去根目录右键管理员运行一次 setup_task.bat"
        except Exception:
            pass

        QMessageBox.information(self, "✅ 保存成功", msg)

# ── Run Tab ───────────────────────────────────────────────────────────────────
STEPS = ["抓取 arXiv", "抓取 RSS", "AI 评分", "深度分析", "生成报告"]
STEP_MAP = {
    "抓取 arXiv 论文": 0, "抓取 RSS 订阅": 1,
    "AI 批量评分": 2, "深度分析高分论文": 3,
    "生成 Markdown 报告": 4, "完成 ✅": 4,
}

class RunTab(QWidget):
    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(14)

        steps_row = QHBoxLayout()
        steps_row.setSpacing(0)
        self._step_widgets = []
        for i, name in enumerate(STEPS):
            col = QVBoxLayout()
            col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle = QLabel(str(i + 1))
            circle.setFixedSize(34, 34)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            circle.setStyleSheet("background:#2d3748;color:#4a5568;border-radius:17px;font-weight:bold;font-size:13px;")
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color:#4a5568;font-size:11px;margin-top:5px;")
            col.addWidget(circle, 0, Qt.AlignmentFlag.AlignCenter)
            col.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
            self._step_widgets.append((circle, lbl))
            w = QWidget(); w.setLayout(col)
            steps_row.addWidget(w)
            if i < len(STEPS) - 1:
                ln = QFrame(); ln.setFrameShape(QFrame.Shape.HLine)
                ln.setStyleSheet("color:#2d3748;"); ln.setFixedHeight(2)
                steps_row.addWidget(ln)
        root.addLayout(steps_row)

        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setTextVisible(False)
        self.pbar.setFixedHeight(10)
        root.addWidget(self.pbar)

        self.plabel = QLabel("等待开始...")
        self.plabel.setStyleSheet("color:#718096;font-size:12px;")
        root.addWidget(self.plabel)

        log_title = QLabel("运行日志")
        log_title.setStyleSheet("color:#a0aec0;font-weight:600;font-size:13px;")
        root.addWidget(log_title)

        self.log_area = QTextEdit()
        self.log_area.setObjectName("logArea")
        self.log_area.setReadOnly(True)
        root.addWidget(self.log_area)

    def reset(self):
        self.pbar.setValue(0)
        self.plabel.setText("等待开始...")
        self.log_area.clear()
        for c, l in self._step_widgets:
            c.setStyleSheet("background:#2d3748;color:#4a5568;border-radius:17px;font-weight:bold;font-size:13px;")
            l.setStyleSheet("color:#4a5568;font-size:11px;margin-top:5px;")

    def update_progress(self, pct: int, step: str):
        self.pbar.setValue(pct)
        self.plabel.setText(f"{step}  {pct}%")
        active = STEP_MAP.get(step, -1)
        for i, (c, l) in enumerate(self._step_widgets):
            if i < active:
                c.setStyleSheet("background:#38a169;color:white;border-radius:17px;font-weight:bold;font-size:13px;")
                l.setStyleSheet("color:#38a169;font-size:11px;margin-top:5px;")
            elif i == active:
                c.setStyleSheet("background:#7c6af7;color:white;border-radius:17px;font-weight:bold;font-size:13px;")
                l.setStyleSheet("color:#7c6af7;font-size:11px;margin-top:5px;")

    def append_log(self, msg: str, level: str = "info"):
        colors = {"info":"#8b949e","warn":"#e3a03a","error":"#f85149","success":"#3fb950"}
        color = colors.get(level, "#8b949e")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f'<span style="color:#4a5568">[{ts}]</span> <span style="color:{color}">{msg}</span>')
        self.log_area.moveCursor(QTextCursor.End)

# ── Report Tab ────────────────────────────────────────────────────────────────
class ReportTab(QWidget):
    def __init__(self, output_dir: str):
        super().__init__()
        self.output_dir = output_dir
        self._current_md = ""
        self._build()
        self.refresh_list()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tb = QWidget()
        tb.setFixedHeight(52)
        tb.setStyleSheet("background:#13151f;border-bottom:1px solid #2d3748;")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(16, 0, 16, 0)
        tbl.setSpacing(10)

        tbl.addWidget(QLabel("📄  历史报告："))
        self.combo = QComboBox()
        self.combo.setFixedWidth(200)
        self.combo.currentIndexChanged.connect(self._load_selected)
        tbl.addWidget(self.combo)
        tbl.addStretch()

        self.open_btn = QPushButton("📂  打开文件夹")
        self.open_btn.setObjectName("secondary")
        self.open_btn.setFixedHeight(34)
        self.open_btn.clicked.connect(self._open_folder)
        tbl.addWidget(self.open_btn)

        self.browser_btn = QPushButton("🌐  浏览器打开")
        self.browser_btn.setObjectName("secondary")
        self.browser_btn.setFixedHeight(34)
        self.browser_btn.clicked.connect(self._open_in_browser)
        tbl.addWidget(self.browser_btn)

        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setObjectName("secondary")
        self.refresh_btn.setFixedSize(34, 34)
        self.refresh_btn.clicked.connect(self.refresh_list)
        tbl.addWidget(self.refresh_btn)

        root.addWidget(tb)

        self.browser = QTextBrowser()
        self.browser.setObjectName("reportView")
        self.browser.setOpenExternalLinks(True)
        self.browser.setOpenLinks(True)
        root.addWidget(self.browser)

        self._show_placeholder()

    def _show_placeholder(self):
        self.browser.setHtml("""
        <div style="display:flex;align-items:center;justify-content:center;
            height:400px;flex-direction:column;background:#0f1117;">
            <div style="font-size:48px;margin-bottom:16px;">📄</div>
            <div style="color:#718096;font-size:16px;font-family:sans-serif;">运行完成后，报告将在此处渲染显示</div>
        </div>""")

    def update_dir(self, new_dir: str):
        self.output_dir = new_dir
        self.refresh_list()

    def refresh_list(self):
        self.combo.blockSignals(True)
        self.combo.clear()
        p = Path(self.output_dir)
        if p.exists():
            for f in sorted(p.glob("*.md"), reverse=True):
                self.combo.addItem(f.name, str(f))
        self.combo.blockSignals(False)
        if self.combo.count() > 0:
            self._load_selected(0)
        else:
            self._show_placeholder()

    def load_md(self, md_content: str):
        self._current_md = md_content
        self.browser.setHtml(md_to_html(md_content))
        self.refresh_list()

    def _load_selected(self, idx: int):
        path = self.combo.itemData(idx)
        if path and Path(path).exists():
            content = Path(path).read_text(encoding="utf-8")
            self._current_md = content
            self.browser.setHtml(md_to_html(content))

    def _open_folder(self):
        p = Path(self.output_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))

    def _open_in_browser(self):
        if not self._current_md: return
        escaped = json.dumps(self._current_md)
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="[https://cdn.jsdelivr.net/npm/marked/marked.min.js](https://cdn.jsdelivr.net/npm/marked/marked.min.js)"></script>
<script>MathJax={{tex:{{inlineMath:[['$','$'],['\\\\(','\\\\)']],displayMath:[['$$','$$'],['\\\\[','\\\\]']]}}}};
</script><script src="[https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js](https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js)"></script>
<style>
body{{background:#0f1117;color:#e2e8f0;font-family:'Segoe UI',sans-serif;font-size:15px;line-height:1.8;padding:32px 56px;max-width:960px;margin:0 auto;}}
h1{{color:#7c6af7;border-bottom:2px solid #2d3748;padding-bottom:8px;}}
h2{{color:#38bdf8;border-bottom:1px solid #2d3748;padding-bottom:4px;}}
h3{{color:#e2e8f0;}} a{{color:#7c6af7;}}
table{{border-collapse:collapse;width:100%;}}
th{{background:#1e2130;color:#7c6af7;padding:10px;border:1px solid #2d3748;}}
td{{padding:9px;border:1px solid #2d3748;}}
code{{background:#1e2130;color:#f6c90e;padding:2px 6px;border-radius:4px;}}
blockquote{{border-left:3px solid #7c6af7;padding:8px 16px;background:#1a1d2e;}}
</style></head><body><div id="c"></div>
<script>document.getElementById('c').innerHTML=marked.parse({escaped});
if(window.MathJax)MathJax.typesetPromise();</script></body></html>"""
        tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
        tmp.write(html); tmp.close()
        webbrowser.open(f"file://{tmp.name}")

# ── Main Window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔬  科研日报助手")
        self.resize(1100, 800)
        self.setMinimumSize(950, 680)
        self.cfg_path = str(Path(__file__).parent / "config.yaml")
        self.cfg = self._load_cfg()
        self._build()
        self.setStyleSheet(STYLE)

    def _load_cfg(self) -> dict:
        try:
            with open(self.cfg_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        vl = QVBoxLayout(central)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(58)
        header.setStyleSheet("background:#13151f;border-bottom:1px solid #2d3748;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(22, 0, 22, 0)
        t = QLabel("🔬  科研日报助手")
        t.setStyleSheet("color:#e2e8f0;font-size:18px;font-weight:700;")
        hl.addWidget(t)
        hl.addStretch()
        sub = QLabel("Daily Paper Tracker  ·  powered by arXiv + AI")
        sub.setStyleSheet("color:#4a5568;font-size:12px;")
        hl.addWidget(sub)
        vl.addWidget(header)

        self.tabs = QTabWidget()
        output_dir = self.cfg.get("output", {}).get("dir", "./daily")

        self.cfg_tab    = ConfigTab(self.cfg, self.cfg_path)
        self.run_tab    = RunTab()
        self.report_tab = ReportTab(output_dir)

        self.tabs.addTab(self.cfg_tab,    "⚙️   配置")
        self.tabs.addTab(self.run_tab,    "▶   运行")
        self.tabs.addTab(self.report_tab, "📄   报告")

        self.cfg_tab.run_btn.clicked.connect(self._start)
        self.cfg_tab.out_input.textChanged.connect(self.report_tab.update_dir)
        vl.addWidget(self.tabs)

    def _start(self):
        cfg = self.cfg_tab.get_cfg()
        if not cfg.get("llm", {}).get("api_key") or cfg["llm"]["api_key"] == "YOUR_API_KEY_HERE":
            QMessageBox.warning(self, "配置不完整", "请先在 API 设置中填写真实的 API Key！")
            return

        self.tabs.setCurrentIndex(1)
        self.run_tab.reset()
        self.cfg_tab.run_btn.setEnabled(False)

        self.worker = PaperWorker(cfg)
        self.worker.sig_progress.connect(self.run_tab.update_progress)
        self.worker.sig_log.connect(self.run_tab.append_log)
        self.worker.sig_finished.connect(self._done)
        self.worker.sig_failed.connect(self._fail)
        self.worker.start()

    def _done(self, path: str, md: str):
        self.cfg_tab.run_btn.setEnabled(True)
        self.run_tab.append_log(f"🎉 报告已保存：{path}", "success")
        self.report_tab.load_md(md)
        self.tabs.setCurrentIndex(2)

    def _fail(self, err: str):
        self.cfg_tab.run_btn.setEnabled(True)
        self.run_tab.append_log(f"❌ 失败：{err.split(chr(10))[0]}", "error")
        QMessageBox.critical(self, "运行失败", err[:400])

if __name__ == "__main__":
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())