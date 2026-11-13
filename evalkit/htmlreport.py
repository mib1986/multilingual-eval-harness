"""Render an agreement analysis as a standalone HTML report.

The page is one file with inline CSS and no external assets: it has to open
from a USB stick, an email attachment or a client's machine that has no
internet. Numbers are formatted here rather than in a template language so the
report keeps working when the JSON changes shape slightly.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any, Dict, List, Optional

from .report import _kappa_label, _pct, _num, _suggestions

ACCEPT_LINE = 0.90  # adjacent-agreement line a batch has to clear before it is usable

CSS = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:#E9E6DE;color:#14181A;
  font-family:"PingFang SC","Microsoft YaHei","Noto Sans SC","Source Han Sans SC",system-ui,sans-serif;
  font-size:15px;line-height:1.65}
.wrap{max-width:1060px;margin:0 auto;padding:44px 40px 72px}
.mono{font-family:ui-monospace,"Cascadia Mono",Consolas,"SF Mono",monospace;
  font-variant-numeric:tabular-nums}
a{color:#1C4B57}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:16px;
  border-bottom:1px solid rgba(20,24,26,.22);padding-bottom:10px}
.brand{font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;font-size:12px;
  letter-spacing:.06em;color:#1C4B57}
.pill{font-size:12px;color:#5A5F60}
h1{font-size:33px;line-height:1.25;font-weight:600;letter-spacing:-.01em;margin:30px 0 12px}
.meta{font-size:12.5px;color:#5A5F60;font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-variant-numeric:tabular-nums;line-height:1.9}
.verdict{margin:30px 0 8px;padding:20px 0 22px;border-top:2px solid #14181A;
  border-bottom:1px solid rgba(20,24,26,.22);display:grid;gap:8px}
.verdict strong{font-size:24px;font-weight:600}
.verdict .why{color:#3C4243;max-width:62ch}
.sec{margin-top:44px;border-top:1px solid rgba(20,24,26,.18);padding-top:16px}
.sec h2{font-size:15px;font-weight:700;margin:0 0 6px}
.sec .note{font-size:12.5px;color:#5A5F60;margin:0 0 20px;max-width:70ch}
.strip{position:relative;height:78px;margin:26px 0 0}
.strip .track{position:absolute;left:0;right:0;top:30px;height:3px;background:rgba(20,24,26,.28)}
.strip .thr{position:absolute;top:14px;bottom:6px;left:90%;border-left:1.5px dashed #B23A2C}
.mk{position:absolute;top:24px;width:1px;height:16px}
.mk i{position:absolute;left:-5px;top:-3px;width:11px;height:11px;border-radius:50%;display:block}
.mk b{position:absolute;top:22px;font-size:11px;font-weight:600;white-space:nowrap;transform:translateX(-50%)}
.mk.exact i{background:#14181A}
.mk.adj i{background:#1C4B57}
.mk.adj b{top:-19px}
.ticks{position:absolute;left:0;right:0;bottom:0;height:16px}
.ticks .ln{position:absolute;top:0;width:1px;height:5px;background:rgba(20,24,26,.3)}
.ticks .ln.red{background:#B23A2C;height:8px}
.ticks .tick{position:absolute;top:8px;font-size:10.5px;color:#7A7F80;
  transform:translateX(-50%)}
.ticks .tick.red{color:#B23A2C;font-weight:600}
.nums{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-top:34px}
.nums div{border-top:1px solid rgba(20,24,26,.25);padding-top:10px;min-width:0}
.nums .k{font-size:11.5px;color:#5A5F60;margin-bottom:4px}
.nums .v{font-size:30px;font-weight:600;line-height:1.2;
  font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;font-variant-numeric:tabular-nums}
.nums .u{font-size:11.5px;color:#5A5F60;margin-top:4px}
table{width:100%;table-layout:fixed;border-collapse:collapse;margin-top:4px}
th,td{text-align:left;padding:9px 8px 9px 0;vertical-align:middle;
  border-bottom:1px solid rgba(20,24,26,.14);font-size:13.5px}
th{font-size:11.5px;color:#5A5F60;font-weight:600;border-bottom:1px solid rgba(20,24,26,.3)}
td.n,th.n{font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-variant-numeric:tabular-nums;text-align:right;padding-right:10px}
.bars{display:grid;gap:3px}
.bar{position:relative;height:5px;background:rgba(20,24,26,.12)}
.bar i{position:absolute;left:0;top:0;bottom:0;display:block}
.bar i.e{background:#14181A}
.bar i.a{background:#1C4B57;opacity:.75}
.badge{display:inline-block;font-size:11.5px;padding:1px 7px;border:1px solid currentColor;
  border-radius:0}
.b-red{color:#B23A2C}
.b-blue{color:#1C4B57}
.b-ink{color:#3C4243}
td.dim{font-weight:600}
.dl{margin:18px 0 0}
.dl div{padding:10px 0;border-bottom:1px solid rgba(20,24,26,.12);display:flex;gap:14px}
.dl div .id{flex:0 0 92px;font-family:ui-monospace,"Cascadia Mono",Consolas,monospace;
  font-size:12px;color:#1C4B57}
.dl div .tx{flex:1 1 auto;min-width:0;font-size:13.5px;color:#2A2F30}
ul.tips{margin:6px 0 0;padding-left:18px}
ul.tips li{margin-bottom:9px;max-width:74ch}
footer{margin-top:46px;border-top:1px solid rgba(20,24,26,.22);padding-top:14px;
  font-size:12px;color:#5A5F60;line-height:1.8}
footer p{max-width:80ch;margin:0 0 6px}
@media (max-width:720px){
  .wrap{padding:28px 20px 48px}
  h1{font-size:25px}
  .nums{grid-template-columns:repeat(2,1fr)}
  .dl div{flex-direction:column;gap:2px}
  table{font-size:12.5px}
}
@media print{
  body{background:#fff}
  .wrap{max-width:none;padding:0}
  .sec,.nums div{break-inside:avoid}
  footer{margin-top:24px}
}
"""

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' fill='%2314181A'/%3E"
    "%3Crect x='6' y='20' width='4' height='6' fill='%23E9E6DE'/%3E"
    "%3Crect x='14' y='14' width='4' height='12' fill='%231C4B57'/%3E"
    "%3Crect x='22' y='8' width='4' height='18' fill='%23B23A2C'/%3E%3C/svg%3E"
)


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _width(rate: Optional[float]) -> str:
    if rate is None:
        return "0%"
    return f"{max(0.0, min(1.0, rate)) * 100:.1f}%"


def _verdict(result: Dict[str, Any]) -> Dict[str, str]:
    """One-sentence call on whether this batch can be used, plus its reason."""
    overall = result["overall"]
    exact = overall["exact_rate"]
    adjacent = overall["adjacent_rate"]
    queue = len(result["disagreements"])
    weak = [
        row for row in result["by_dimension"]
        if row["kappa"] is not None and row["kappa"] < 0.4
    ]

    if adjacent is not None and adjacent >= ACCEPT_LINE:
        if queue == 0 and (exact is None or exact >= 0.6):
            return {
                "tone": "ok",
                "tag": "可用",
                "label": "可用：直接进入验收",
                "why": "相邻一致率已过验收线，且没有需要仲裁的条目。抽检通过即可放行。",
            }
        return {
            "tone": "ok",
            "tag": "可用",
            "label": f"可用：先处理 {queue} 处仲裁",
            "why": "整体尺度已经对齐，剩下的分歧集中在少数条目，仲裁完即可放行。",
        }
    if adjacent is not None and adjacent >= 0.75:
        reason = "相邻一致率低于验收线，说明分歧已经到了判断尺度这一层，不是措辞问题。"
        if weak:
            names = "、".join(row["label_zh"] for row in weak)
            reason += f" 其中 {names} 的 κ 低于 0.4，先补这一维的锚点样本再复训。"
        return {"tone": "warn", "tag": "需复训", "label": "需复训后再用", "why": reason}
    return {
        "tone": "bad",
        "tag": "不可用",
        "label": "不可用：先重写档位",
        "why": "相邻一致率低于 75%，标注员对档位边界的理解没有共享。"
               "此时任何模型分数都没有解释力，先重写 rubric 的低分档描述。",
    }


def _badge(text: str, cls: str) -> str:
    return f'<span class="badge {cls}">{_esc(text)}</span>'


def _verdict_tone_class(tone: str) -> str:
    return {"ok": "b-blue", "warn": "b-ink"}.get(tone, "b-red")


def _scale_strip(result: Dict[str, Any]) -> str:
    overall = result["overall"]
    exact = overall["exact_rate"]
    adjacent = overall["adjacent_rate"]
    parts: List[str] = ['<div class="strip" aria-label="一致性水平刻度">']
    parts.append('<div class="track"></div>')
    parts.append('<div class="thr"></div>')
    if adjacent is not None:
        parts.append(
            f'<div class="mk adj" style="left:{_width(adjacent)}">'
            f'<i></i><b>相邻 {_pct(adjacent)}</b></div>'
        )
    if exact is not None:
        parts.append(
            f'<div class="mk exact" style="left:{_width(exact)}">'
            f'<i></i><b>完全 {_pct(exact)}</b></div>'
        )
    ticks = ['<div class="ticks">']
    for i in range(0, 101, 20):
        ticks.append(f'<div class="ln" style="left:{i}%"></div>')
        ticks.append(f'<div class="tick" style="left:{i}%">{i}</div>')
    ticks.append(f'<div class="ln red" style="left:{ACCEPT_LINE * 100}%"></div>')
    ticks.append(
        f'<div class="tick red" style="left:{ACCEPT_LINE * 100}%">'
        f'{int(ACCEPT_LINE * 100)}</div>'
    )
    ticks.append("</div>")
    parts.append("".join(ticks))
    parts.append("</div>")
    return "".join(parts)


def _verdict_block(result: Dict[str, Any]) -> str:
    verdict = _verdict(result)
    return (
        '<section class="verdict">'
        f'<strong>{_esc(verdict["label"])}</strong>'
        f'<div class="why">{_esc(verdict["why"])}</div>'
        "</section>"
    )


def _numbers(result: Dict[str, Any]) -> str:
    overall = result["overall"]
    cells = [
        ("完全一致率", _pct(overall["exact_rate"]), "所有标注员给出同一个分数"),
        ("相邻一致率", _pct(overall["adjacent_rate"]), "最高与最低之差不超过 1 分"),
        ("Fleiss κ", _num(overall["kappa"], 3), _kappa_label(overall["kappa"])),
        ("可比对单元", f"{overall['n_cells']}", "至少两人评过的 条目×维度"),
    ]
    body = "".join(
        f'<div><div class="k">{_esc(k)}</div><div class="v">{_esc(v)}</div>'
        f'<div class="u">{_esc(u)}</div></div>'
        for k, v, u in cells
    )
    return f'<div class="nums">{body}</div>'


def _dimension_table(result: Dict[str, Any]) -> str:
    rows = []
    for row in result["by_dimension"]:
        exact = row["exact_rate"]
        adjacent = row["adjacent_rate"]
        bars = (
            '<div class="bars">'
            f'<div class="bar"><i class="e" style="width:{_width(exact)}"></i></div>'
            f'<div class="bar"><i class="a" style="width:{_width(adjacent)}"></i></div>'
            "</div>"
        )
        tone = "b-blue" if (row["kappa"] or 0) >= 0.6 else (
            "b-ink" if (row["kappa"] or 0) >= 0.4 else "b-red"
        )
        rows.append(
            "<tr>"
            f'<td class="dim">{_esc(row["label_zh"])}<br>'
            f'<span class="pill">{_esc(row["label_en"])}</span></td>'
            f'<td class="n">{row["weight"] * 100:.0f}%</td>'
            f'<td class="n">{_pct(exact)}</td>'
            f'<td class="n">{_pct(adjacent)}</td>'
            f'<td class="n">{_num(row["mad"])}</td>'
            f'<td class="n">{_num(row["kappa"], 3)}</td>'
            f'<td>{_badge(_kappa_label(row["kappa"]), tone)}</td>'
            "<td>" + bars + "</td>"
            "</tr>"
        )
    return (
        '<table>'
        "<colgroup><col style=\"width:18%\"><col style=\"width:7%\"><col style=\"width:9%\">"
        "<col style=\"width:9%\"><col style=\"width:8%\"><col style=\"width:8%\">"
        "<col style=\"width:13%\"><col style=\"width:28%\"></colgroup>"
        "<thead><tr><th>维度</th><th class=\"n\">权重</th><th class=\"n\">完全</th>"
        "<th class=\"n\">相邻</th><th class=\"n\">偏差</th><th class=\"n\">κ</th>"
        "<th style=\"padding-left:14px\">判读</th><th>完全 / 相邻</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _rater_table(result: Dict[str, Any]) -> str:
    rows = []
    for row in result["rater_stats"]:
        dev = row["mean_dev"]
        width = 0.0 if dev is None else min(dev / 1.0, 1.0) * 100
        rows.append(
            "<tr>"
            f'<td class="dim">{_esc(row["rater"])}</td>'
            f'<td class="n">{row["n_items"]}</td>'
            f'<td class="n">{row["n_scores"]}</td>'
            f'<td class="n">{_num(row["mean_weighted"])}</td>'
            f'<td class="n">{_num(dev)}</td>'
            f'<td class="n">{_num(row["max_dev"])}</td>'
            f'<td style="width:22%"><div class="bar">'
            f'<i class="a" style="width:{width:.1f}%"></i></div></td>'
            "</tr>"
        )
    return (
        '<table>'
        '<colgroup><col style="width:18%"><col style="width:12%"><col style="width:12%">'
        '<col style="width:14%"><col style="width:16%"><col style="width:14%">'
        '<col style="width:14%"></colgroup>'
        '<thead><tr><th>标注员</th><th class="n">评过条目</th><th class="n">评分数</th>'
        '<th class="n">加权均分</th><th class="n">与共识偏差</th><th class="n">最大偏差</th>'
        '<th style="padding-left:14px">偏差幅度</th></tr></thead>'
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _queue_table(result: Dict[str, Any], top: int) -> str:
    queue = result["disagreements"][:top]
    if not queue:
        return '<p class="note">无。所有 条目×维度 组合的极差与平均偏差都在阈值内。</p>'
    rows = []
    dim_labels = {row["id"]: row["label_zh"] for row in result["by_dimension"]}
    for index, row in enumerate(queue, 1):
        scores = "  ".join(f'{r["rater"]}:{r["score"]}' for r in row["raters"])
        reason = "极差超阈值" if row["reason"] == "spread" else "偏差超阈值"
        rows.append(
            "<tr>"
            f'<td class="n">{index}</td>'
            f'<td class="dim">{_esc(row["item_id"])}</td>'
            f'<td class="pill">{_esc(row["lang"] or "—")}</td>'
            f'<td>{_esc(dim_labels.get(row["dimension"], row["dimension"]))}</td>'
            f'<td class="mono" style="font-size:12.5px">{_esc(scores)}</td>'
            f'<td class="n">{row["spread"]}</td>'
            f'<td>{_badge(reason, "b-red")}</td>'
            "</tr>"
        )
    table = (
        '<table>'
        '<colgroup><col style="width:5%"><col style="width:17%"><col style="width:8%">'
        '<col style="width:15%"><col style="width:29%"><col style="width:8%">'
        '<col style="width:18%"></colgroup>'
        '<thead><tr><th class="n">#</th><th>条目</th><th>语种</th><th>维度</th>'
        '<th>分数分布</th><th class="n">极差</th>'
        '<th style="padding-left:14px">触发原因</th></tr></thead>'
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )

    seen: Dict[str, bool] = {}
    entries = []
    for row in queue:
        if row["item_id"] in seen or not row["excerpt"]:
            continue
        seen[row["item_id"]] = True
        entries.append(
            '<div><div class="id">'
            f'{_esc(row["item_id"])}</div><div class="tx">{_esc(row["excerpt"])}</div></div>'
        )
    if not entries:
        return table
    return table + '<div class="dl" style="margin-top:26px">' + "".join(entries) + "</div>"


def _stamp() -> str:
    """Local wall-clock time: whoever opens the page reads it in their own zone."""
    now = datetime.now().astimezone()
    offset = now.strftime("%z")
    zone = f"UTC{offset[:3]}:{offset[3:]}" if len(offset) == 5 else ""
    return f'{now.strftime("%Y-%m-%d %H:%M")}{f" ({zone})" if zone else ""}'


def to_html(result: Dict[str, Any], source: str = "", top: int = 10) -> str:
    """Render the analysis as one self-contained HTML document."""
    stamp = _stamp()
    rubric_name = result["rubric"]["name"] or "rubric"
    langs = " · ".join(f"{k} {v}" for k, v in result["by_lang"].items())

    head_meta = [
        f"标准 {_esc(rubric_name)} v{_esc(result['rubric']['version'])}",
        f"{result['n_items']} 条目 / {result['n_raters']} 位标注员 / {result['n_annotations']} 条评分",
        f"量表 {_esc(result['scale']['min'])}–{_esc(result['scale']['max'])}",
        f"生成 {stamp}",
    ]
    if langs:
        head_meta.append(f"语种 {_esc(langs)}")
    if source:
        head_meta.append(f"数据 {_esc(source)}")

    tips = "".join(f"<li>{_esc(tip)}</li>" for tip in _suggestions(result))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(rubric_name)} · 评测一致性报告</title>
<link rel="icon" href="{FAVICON}">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

<header class="top">
  <div class="brand">evalkit · QC REPORT</div>
  <div class="pill">{_esc(rubric_name)}</div>
</header>

<h1>评测一致性报告</h1>
<div class="meta">{"<br>".join(head_meta)}</div>

{_verdict_block(result)}

<section class="sec">
  <h2>一致性水平</h2>
  <p class="note">完全一致率衡量严格程度，相邻一致率衡量可用程度。相邻率低于 90% 时，
  同一批数据换个人评就会换一份结论。</p>
  {_scale_strip(result)}
  <p class="note" style="margin:10px 0 0">红色虚线为相邻一致率验收线 {int(ACCEPT_LINE * 100)}%；
  深色点为完全一致率，蓝色点为相邻一致率。</p>
  {_numbers(result)}
</section>

<section class="sec">
  <h2>分维度</h2>
  <p class="note">某一维的 κ 明显低于其他维，说明那一维的档位边界没有被共享，
  应先补该维的锚点样本，而不是整体增加标注人力。</p>
  {_dimension_table(result)}
</section>

<section class="sec">
  <h2>标注员偏差</h2>
  <p class="note">偏差以每格中位数为共识。偏松或偏严不代表判断错误，
  但同一位标注员长期偏离，会拉低整批数据的可用性。</p>
  {_rater_table(result)}
</section>

<section class="sec">
  <h2>待仲裁</h2>
  <p class="note">极差达到 {_esc(result['thresholds']['spread'])} 分或平均偏差达到
  {_esc(result['thresholds']['mad'])} 分的组合，不能靠取平均解决，必须回到原文重新判定。</p>
  {_queue_table(result, top)}
</section>

<section class="sec">
  <h2>判读与建议</h2>
  <ul class="tips">{tips}</ul>
</section>

<footer>
  <p>κ 在分数高度集中时会失真：全组都给 4 分、只有一人给 5 分，相邻一致率是 100%，
  κ 却可能接近 0。所以 κ 必须与相邻一致率并读。</p>
  <p>指标只说明「这一批标注能不能用」，不说明「模型好不好」。标准本身有歧义时，
  一致性再高也只是稳定地错。</p>
  <p>本报告含评测条目原文，分发前请确认接收方权限。</p>
</footer>

</div>
</body>
</html>
"""
