# evalkit

多语言评测的一致性检查器：把一批 rubric 评分判成「能用」还是「不能用」，并指出具体卡在哪里。

A small, dependency-free harness for rubric-based evaluation. It answers one question — **is this batch of annotations usable, and if not, which cells are pulling it down** — and it answers it before the data goes anywhere near a model comparison.

---

## 它解决什么问题

评测数据最常见的失败不是「标错了」，而是**没人知道标得准不准**：

- 同一批回答，三个标注员给分差异过大，平均一下看起来有分，其实是把噪声当结论；
- 团队里有人系统性偏松、有人偏严，但没人说得清是谁、偏了多少；
- 一批数据里只有少数几条真的需要讨论，其余都在共识区，却每次开会从头炒一遍。

这个工具干三件事：算一致性、定位偏差来源、把该仲裁的条目单独排成一列。它不评价模型好坏，只评价「这批评分能不能作为证据」。

## 快速开始

无第三方依赖，Python 3.8+：

```bash
python cli.py report --rubric rubric.json --annotations data/sample_annotations.jsonl --out examples/report.md
```

输出：

```
report written to examples/report.md
items=10 raters=3 exact=62.5% adjacent=92.5% kappa=0.530
arbitration queue: 3
```

完整报告见 [`examples/report.md`](examples/report.md)。校验 rubric 是否可用：

```bash
python cli.py validate --rubric rubric.json
```

## 报告包含什么

| 部分 | 回答的问题 |
| --- | --- |
| 总体一致性 | 这批数据整体达到可用线了吗 |
| 分维度 | 是哪个维度在拖后腿，还是全都松 |
| 标注员偏差 | 谁偏松、谁偏严，偏了多少，是否需要单独复训 |
| 待仲裁清单 | 哪几条不要再投票，直接进仲裁，按严重度排好 |
| 判读与建议 | 基于本次数字给出的下一步动作，不是通用建议 |

## 指标定义与局限

| 指标 | 定义 | 什么时候别信它 |
| --- | --- | --- |
| 完全一致率 | 同一 条目×维度 上所有标注员给分完全相同 | 量表档位多时天然偏低，别拿它当唯一标准 |
| 相邻一致率 | 最高分与最低分之差 ≤ 1 | 只说明「差得不多」，不说明差得对 |
| 平均绝对偏差 | 各分数与中位数之差的均值 | 中位数本身可能是共识错误 |
| Fleiss κ | 扣除随机一致后的真实一致性 | **分数高度集中时严重失真**：全组 4 分、一人 5 分，相邻一致 100%，κ 可能接近 0 |

κ 一律与相邻一致率并读；报告里也写了这句，防止有人只看 κ 一个数就下结论。安全边界这类「几乎全给满分」的维度，κ 天然不可靠，看完全一致率更合适。

## 数据结构

`rubric.json` —— 评分标准，维度权重必须合计为 1.0：

```json
{
  "scale": { "min": 1, "max": 5 },
  "thresholds": { "spread": 2, "mad": 0.75 },
  "dimensions": [
    { "id": "factuality", "label_zh": "事实性", "weight": 0.35,
      "levels": { "5": "全部陈述正确", "1": "主要错误或编造" } }
  ]
}
```

`annotations.jsonl` —— 一行一条评分记录，同一条目由多行组成：

```json
{"item_id": "zh-01", "lang": "zh", "excerpt": "定期存款提前支取，利息怎么算？",
 "rater": "r1", "scores": {"factuality": 5, "faithfulness": 5, "language": 4, "safety": 5}}
```

缺评不需要占位：某位标注员没评某个维度，直接不在 `scores` 里放这个键即可，指标会自动跳过该单元。

## 调阈值

```bash
python cli.py report --rubric rubric.json --annotations data/sample_annotations.jsonl \
  --spread 3 --mad 1.0 --top 20
```

`--spread`：极差达到多少分就进仲裁队列。`--mad`：平均偏差达到多少进队列。`--top`：清单最多列几条。两个条件是「或」的关系——任意一个触发就进队列，因为一个偏松一个偏严的组合，平均偏差可能被抵消，极差却不会。

## 设计取舍

- **不做准确率**：评测数据通常没有标准答案，只有多个判断。用「与某位专家的一致率」冒充准确率，是把循环论证包装成指标。
- **不做两两对比矩阵**：N 位标注员两两比较是 N×N 张表，没人读。单元级指标加一份按严重度排序的清单更有用。
- **κ 不单独作为门槛**：见上表。分布偏斜时它会给出误导性的低值。
- **阈值写进 rubric**：同一个工具在不同项目里该有不同的松紧标准，所以阈值属于标准的一部分，不属于工具的默认值。

## 局限

- 只处理评分，不处理文本质量本身。标准写错了，一致性再高也只是稳定地错。
- 条目数少于 20 时，κ 的估计不稳定，建议先只看完全一致率与偏差。
- 仲裁队列按极差排序，不判断谁对。仲裁仍然需要人。
- 目前输出 Markdown，没有 HTML 报告与趋势追踪。

## 结构

```
evalkit/
  agreement.py   一致性指标（含推广到不等标注员数的 Fleiss κ）
  analyze.py     汇总计算与仲裁队列
  report.py      Markdown 报告渲染
  rubric.py      标准加载与结构校验
rubric.json      示例标准：四维、权重 0.35/0.30/0.20/0.15
data/            10 条三语示例（中文 4、英文 3、馬来文 3）× 3 位标注员
examples/        由示例数据生成的报告
tests/           20 项单元测试，含手算校验的 κ 用例
```

```bash
python -m unittest discover -s tests -v
```

## 关于示例数据

`data/` 里的条目与评分全部为合成数据，用于演示指标行为，**不含任何客户材料、真实题面或受保密协议约束的内容**。换成自己的数据时，按上面的 schema 改写即可，代码不需要动。

## License

MIT，见 [LICENSE](LICENSE)。
