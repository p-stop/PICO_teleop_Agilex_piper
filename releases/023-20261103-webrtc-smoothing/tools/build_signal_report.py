"""Build an offline report with native MathML; no network/browser dependencies."""
from pathlib import Path
import posixpath
import re
import markdown
from latex2mathml.converter import convert

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets/signal-timing"


def build():
    source = (DOCS / "research/2026-10-20-signal-timing-and-learning.md").read_text(encoding="utf-8")
    source = re.sub(r"\A---\n.*?\n---\n", "", source, flags=re.S)
    # The Markdown retains an editable Mermaid graph. The standalone report uses
    # a native overview plus its full explanatory table, with no Mermaid CDN.
    source = re.sub(r"```mermaid\n.*?```", '<div class="flow" aria-label="信号处理链">'
                    '<span>手柄 / XRFrame</span><b>→</b><span>网络 / 映射</span><b>→</b>'
                    '<span>异步 IK</span><b>→</b><span>目标 / 网关</span><b>→</b>'
                    '<span>驱动 / 实际运动</span><b>→</b><span>反馈 / 多速率记录</span>'
                    '</div>', source, flags=re.S)
    math_blocks = {}
    def math_replace(match):
        display = bool(match.group(1))
        tex = match.group(2) if display else match.group(3)
        key = f"MATHPLACEHOLDER{len(math_blocks)}END"
        converted = convert(tex.strip(), display="block" if display else "inline")
        math_blocks[key] = '<div class="math-display">' + converted + '</div>' if display else converted
        return "\n\n" + key + "\n\n" if display else key
    source = re.sub(r"(\$\$)(.*?)\$\$|\$([^$\n]+)\$", math_replace, source, flags=re.S)
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"], extension_configs={"toc": {"toc_depth": "2"}})
    body = md.convert(source)
    for key, value in math_blocks.items():
        body = body.replace("<p>" + key + "</p>", value).replace(key, value)
    body = body.replace("[!abstract]", "<strong>阅读提要</strong>")
    def link(match):
        key, url = match.group(1), match.group(2)
        if re.match(r"^[a-z]+:|^#", url):
            return match.group(0)
        return f'{key}="{posixpath.normpath(posixpath.join("research", url))}"'
    body = re.sub(r'(href|src)="([^"]+)"', link, body)
    body = body.replace("<table>", '<div class="table-scroll"><table>').replace("</table>", "</table></div>")
    experiments = (ASSETS / "experiments.html").read_text(encoding="utf-8")
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>从手柄到策略 · 信号与时间研究</title><link rel="stylesheet" href="assets/signal-timing/report.css"></head>
<body><div class="shell"><aside><div class="brand">ROBOT INFRA / RESEARCH 015</div>
<a href="#experiments">交互实验 A–D</a><a href="#report">完整研究报告</a>
<a href="research/2026-10-20-signal-timing-and-learning.md">Obsidian / Markdown 源文</a>
<div class="toc">{md.toc}</div></aside><main>
<header class="hero"><div class="eyebrow">SIGNALS · SAMPLING · EXECUTION</div>
<h1>从手柄到策略<br>每一帧，发生在什么时候？</h1>
<p class="lead">把连续运动、离散数据和模型动作连接起来。用四个实验理解：采到了什么、丢掉了什么，以及回放究竟能恢复什么。</p>
<p class="scope">2026-10-20 · 原始论文 × 当前源码 × 已录真机证据<br>前三个实验是教学模型；第四个来自真实三秒回放。本页不连接机器人。</p>
<nav class="jump" aria-label="实验导航"><a href="#experiment-a">A 采样与混叠</a><a href="#experiment-b">B 控制与记录</a><a href="#experiment-c">C Chunk 时间预算</a><a href="#experiment-d">D 真实回放</a></nav></header>
{experiments}<article id="report">{body}</article>
<footer class="footer">离线阅读 · 本地资源 · 无遥测 · 原始日志未修改。使用浏览器打印可保存正文 PDF；交互图保留在网页中。</footer>
</main></div><script src="assets/signal-timing/evidence.js"></script><script src="assets/signal-timing/report.js"></script></body></html>"""
    target = DOCS / "signal-timing-report.html"
    target.write_text(page, encoding="utf-8")
    print(f"Built {target} | {len(math_blocks)} MathML expressions | {len(page.encode('utf-8'))} bytes")


if __name__ == "__main__":
    build()
