"""Build the offline modeling course from its two Markdown sources.

Run in an isolated environment with markdown and latex2mathml; no runtime deps
are added to robot-infra. The output uses native MathML and local assets only.
"""
from pathlib import Path
import html
import posixpath
import re

import markdown
from latex2mathml.converter import convert

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets/pipeline-model"
MATH = re.compile(r"(\$\$)(.*?)\$\$|\$([^$\n]+)\$", re.S)

GRAPH = '''<div class="system-map" role="group" aria-label="两条意图链共享执行与记录，反馈闭合人与策略的外环">
<div><strong>遥操意图链</strong><p>人 → WebXR → 传输/latest → 相对映射/侧握锚点 → 异步 IK</p></div>
<div><strong>策略意图链</strong><p>图像与反馈快照 → 模型/动作解码 → ActionChunk 队列</p></div>
<div><strong>共享执行面 ↓</strong><p>目标调度/保持 → 所有权与最终检查 → 驱动内环 → 机器人与物体</p></div>
<div><strong>反馈闭环 ↺</strong><p>机器人 → 状态反馈/相机 → 预览 → 人；状态反馈/相机 → 快照 → 模型</p></div>
<div><strong>记录旁路 → 学习</strong><p>输入 + IK + 网关命令 + 反馈/相机 → 原始多速率记录 → 训练视图/标签/mask</p></div>
</div>'''


def source(path):
    return re.sub(r"\A---\n.*?\n---\n", "", path.read_text(encoding="utf-8"), flags=re.S)


def render(text, base="", prefix=""):
    blocks = {}

    def equation(match):
        display = bool(match.group(1))
        tex = (match.group(2) if display else match.group(3)).strip()
        key = f"MATHPLACEHOLDER{len(blocks)}END"
        value = convert(tex, display="block" if display else "inline")
        blocks[key] = f'<div class="math-display">{value}</div>' if display else value
        return f"\n\n{key}\n\n" if display else key

    text = re.sub(r"```mermaid\n.*?```", GRAPH, text, flags=re.S)
    text = text.replace("<details>", '<details markdown="1">')
    text = MATH.sub(equation, text)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists", "md_in_html"],
                           extension_configs={"toc": {"toc_depth": "2"}})
    body = md.convert(text)
    for key, value in blocks.items():
        body = body.replace(f"<p>{key}</p>", value).replace(key, value)

    def link(match):
        key, url = match.groups()
        if re.match(r"^[a-z]+:|^#", url):
            return match.group(0)
        return f'{key}="{posixpath.normpath(posixpath.join(base, url))}"'

    body = re.sub(r'(href|src)="([^"]+)"', link, body)
    # Scope heading IDs so the tutorial and full report can share one document.
    ids = re.findall(r'<h[1-6] id="([^"]+)"', body)
    toc = md.toc
    for ident in ids:
        body = body.replace(f'id="{ident}"', f'id="{prefix}{ident}"')
        body = body.replace(f'href="#{ident}"', f'href="#{prefix}{ident}"')
        toc = toc.replace(f'href="#{ident}"', f'href="#{prefix}{ident}"')
    body = body.replace("<table>", '<div class="table-scroll"><table>').replace("</table>", "</table></div>")
    return body, toc, len(blocks)


def build():
    tutorial = source(DOCS / "pipeline-learning.md")
    sections = re.split(r"(?=^## )", tutorial, flags=re.M)
    lessons, tail, options, count = [], "", [], 0
    for idx, section in enumerate(sections[1:]):
        title = section.splitlines()[0][3:]
        body, _, n = render(section, prefix=f"lesson{idx}-")
        count += n
        if idx < 8:
            lessons.append(f'<section class="lesson" id="lesson-{idx}" aria-label="{html.escape(title)}">{body}</section>')
            options.append(f'<option value="{idx}">{html.escape(title)}</option>')
        else:
            tail += body
    assert len(lessons) == 8
    report, toc, n = render(source(DOCS / "research/2026-10-22-pipeline-mathematical-model.md"),
                            base="research", prefix="model-")
    count += n
    calculators = (ASSETS / "calculators.html").read_text(encoding="utf-8")
    page = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>遥操与推理 · 数学模型与八课学习</title>
<link rel="stylesheet" href="assets/signal-timing/report.css"><link rel="stylesheet" href="assets/pipeline-model/reader.css"></head>
<body><div class="shell"><aside><div class="brand">ROBOT INFRA / RESEARCH 016</div>
<a href="#course">八课学习路径</a><a href="#experiments">两个设计计算器</a><a href="#model-report">完整建模报告</a>
<a href="pipeline-learning.md">课程 Markdown</a><a href="research/2026-10-22-pipeline-mathematical-model.md">建模 Markdown</a>
<a href="signal-timing-report.html">前篇：采样与真实回放</a><div class="toc">{toc}</div></aside><main>
<header class="hero"><div class="eyebrow">MODEL · TRACE · LEARN</div><h1>每个目标，都有来处。<br>每次执行，都有时刻。</h1>
<p class="lead">沿着一条手柄消息，理解遥操如何留下可信数据；沿着一个动作 chunk，理解模型如何及时、忠实地作用于机器人。</p>
<p class="scope">2026-10-22 · 依据当前源码 · 教学假设与实测分开标注<br>完整覆盖模块接口；未知物理参数仍待辨识。本页不连接设备，不改变配置。</p>
<nav class="jump"><a href="#course">从第一课开始</a><a href="#model-report">直接查数学模型</a></nav></header>
<section id="course"><h2>八课，把数据过程串起来</h2><p>先理解变量，再计算时间，最后决定设计。每课含一个例子和一道可展开答案的练习。</p>
<div class="lesson-controls" hidden><label for="lesson-select">选择课程<select id="lesson-select">{''.join(options)}</select></label>
<div class="lesson-buttons"><button id="previous" type="button">上一课</button><span id="lesson-progress" aria-live="polite"></span><button id="next" type="button">下一课</button></div></div>
<article id="lesson-body">{''.join(lessons)}</article><div class="course-checklist">{tail}</div></section>
{calculators}<article id="model-report">{report}</article>
<footer class="footer">离线原生公式 · 无外部脚本/字体 · Markdown 可在 Obsidian 中编辑。浏览器打印显示全部课程、练习答案与正文；计算器是教学近似，不是硬件性能预测。</footer>
</main></div><script src="assets/pipeline-model/reader.js"></script></body></html>'''
    target = DOCS / "pipeline-model.html"
    target.write_text(page, encoding="utf-8")
    print(f"Built {target} | {count} MathML expressions | {len(page.encode('utf-8'))} bytes")


if __name__ == "__main__":
    build()
