"""Render an agreement analysis as Markdown."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _pct(value: Optional[float]) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _num(value: Optional[float], digits: int = 2) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _kappa_label(kappa: Optional[float]) -> str:
    if kappa is None:
        return "无法计算"
    if kappa >= 0.8:
        return "良好"
    if kappa >= 0.6:
        return "可接受"
    if kappa >= 0.4:
        return "偏低"
    return "需重写档位"


def _suggestions(result: Dict[str, Any]) -> List[str]:
    tips: List[str] = []
    overall = result["overall"]
    if overall["exact_rate"] is not None and overall["exact_rate"] < 0.6:
        tips.append(
            "完全一致率低于 60%：标准里存在没有被写清的判断点，先补档位定义，再谈增加标注人力。"
        )
    if overall["adjacent_rate"] is not None and overall["adjacent_rate"] < 0.9:
        tips.append(
            "相邻一致率低于 90%：分歧已经不是措辞问题而是判断尺度问题，需要重写锚点样本。"
        )
    weak = [row for row in result["by_dimension"] if row["kappa"] is not None and row["kappa"] < 0.4]
    if weak:
        names = "、".join(row["label_zh"] for row in weak)
        tips.append(
            f"维度 {names} 的 κ 低于 0.4，档位之间的界线没被标注员共享，建议先单维度复训再重算。"
        )
    if result["disagreements"]:
        top = result["disagreements"][0]
        tips.append(
            f"待仲裁 {len(result['disagreements'])} 处，优先处理极差最大的 {top['item_id']} / {top['dimension']}，"
            "它的分歧会污染同一批数据的其余条目。"
        )
    if result["out_of_scale"]:
        tips.append(f"有 {len(result['out_of_scale'])} 处评分超出量表范围，先修数据再解读指标。")
    if not tips:
        tips.append("本轮数据一致性达标，可以把评分结果直接进入验收，仅保留抽查。")
    return tips


def to_markdown(result: Dict[str, Any], source: str = "", top: int = 10) -> str:
    lines: List[str] = []
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append("# 评测一致性报告")
    lines.append("")
    lines.append(f"- 生成时间：{stamp}")
    if source:
        lines.append(f"- 数据来源：`{source}`")
    lines.append(f"- 评分标准：{result['rubric']['name']} v{result['rubric']['version']}")
    lines.append(
        f"- 规模：{result['n_items']} 个条目 / {result['n_raters']} 位标注员 / {result['n_annotations']} 条评分记录"
    )
    langs = "、".join(f"{k} {v} 条" for k, v in result["by_lang"].items())
    if langs:
        lines.append(f"- 语种分布：{langs}")
    lines.append("")

    overall = result["overall"]
    lines.append("## 一、总体一致性")
    lines.append("")
    lines.append("| 指标 | 值 | 说明 |")
    lines.append("| --- | --- | --- |")
    lines.append(
        f"| 完全一致率 | {_pct(overall['exact_rate'])} | 同一维度上所有标注员给分完全相同 |"
    )
    lines.append(
        f"| 相邻一致率 | {_pct(overall['adjacent_rate'])} | 最高分与最低分之差不超过 1 分 |"
    )
    lines.append(f"| 平均绝对偏差 | {_num(overall['mad'])} | 各分数与中位数之差的平均，单位为分 |")
    lines.append(
        f"| Fleiss κ（单元级汇总） | {_num(overall['kappa'], 3)} | {_kappa_label(overall['kappa'])}；"
        "跨维度汇总，仅作参考 |"
    )
    lines.append(f"| 可比对单元 | {overall['n_cells']} | 至少两位标注员评过的 条目×维度 组合 |")
    lines.append("")

    lines.append("## 二、分维度")
    lines.append("")
    lines.append("| 维度 | 权重 | 可比对 | 完全一致 | 相邻一致 | 平均偏差 | κ | 判读 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in result["by_dimension"]:
        lines.append(
            f"| {row['label_zh']} / {row['label_en']} | {row['weight']:.2f} | {row['n_cells']} | "
            f"{_pct(row['exact_rate'])} | {_pct(row['adjacent_rate'])} | {_num(row['mad'])} | "
            f"{_num(row['kappa'], 3)} | {_kappa_label(row['kappa'])} |"
        )
    lines.append("")
    lines.append(
        "κ 在分数高度集中时会失真：全组都给 4 分、只有一人给 5 分，相邻一致率是 100%，κ 却可能接近 0。"
        "所以 κ 要和相邻一致率一起读，不能单看一个数。"
    )
    lines.append("")

    lines.append("## 三、标注员偏差")
    lines.append("")
    lines.append("| 标注员 | 评过条目 | 评分数 | 加权均分 | 与共识平均偏差 | 最大偏差 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in result["rater_stats"]:
        lines.append(
            f"| {row['rater']} | {row['n_items']} | {row['n_scores']} | "
            f"{_num(row['mean_weighted'])} | {_num(row['mean_dev'])} | {_num(row['max_dev'])} |"
        )
    lines.append("")
    lines.append("偏差以每格中位数为共识，用于发现系统性偏松或偏严的标注员，不代表其判断错误。")
    lines.append("")

    lines.append(f"## 四、待仲裁清单（前 {top} 项）")
    lines.append("")
    if not result["disagreements"]:
        lines.append("无。所有 条目×维度 组合的极差与平均偏差都在阈值内。")
        lines.append("")
    else:
        lines.append("| # | 条目 | 维度 | 分数分布 | 极差 | 偏差 | 触发原因 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for index, row in enumerate(result["disagreements"][:top], 1):
            scores = "、".join(f"{r['rater']}:{r['score']}" for r in row["raters"])
            reason = "极差超阈值" if row["reason"] == "spread" else "平均偏差超阈值"
            lines.append(
                f"| {index} | {row['item_id']} ({row['lang']}) | {row['dimension']} | {scores} | "
                f"{row['spread']} | {_num(row['mad'])} | {reason} |"
            )
        lines.append("")
        lines.append("条目原文：")
        lines.append("")
        seen = set()
        for row in result["disagreements"][:top]:
            if row["item_id"] in seen:
                continue
            seen.add(row["item_id"])
            excerpt = row["excerpt"].replace("|", "\\|")
            lines.append(f"- `{row['item_id']}` {excerpt}")
        lines.append("")

    lines.append("## 五、判读与建议")
    lines.append("")
    for tip in _suggestions(result):
        lines.append(f"- {tip}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "指标只说明「这一批标注能不能用」，不说明「模型好不好」。"
        "标准本身有歧义时，一致性再高也只是稳定地错，判读前请先读一遍 rubric 的档位定义。"
    )
    return "\n".join(lines)
