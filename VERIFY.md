# 项目验收单・multilingual-eval-harness

一份能发给老板、招聘方、项目组看的自验清单。别人问你「这东西真能跑吗」，你不解释，直接照下面三步跑给他看。

***

## 一、这是什么

一个**多语言评测的一致性检查器**：给一批 rubric 评分，回答「这批评分能不能当证据用」，不能的话指出具体卡在哪一条、哪一位标注员、哪一个维度。

不评价模型好坏，只评价「评分本身可不可信」。这是评测工作里最常被跳过、也最容易出事的一步：三个标注员给分差得离谱，平均一下看起来有分，其实是把噪声当结论。

* 仓库：`mib1986/multilingual-eval-harness`（public）

* 技术：纯 Python 标准库，零第三方依赖，Python 3.8+

* 规模：5 个模块 + CLI + 示例标准 + 三语示例数据 + 24 项单元测试

## 二、三步自验（约 30 秒）

在仓库目录里打开 PowerShell，依次执行：

```
py cli.py validate --rubric rubric.json
py cli.py report --rubric rubric.json --annotations data/sample_annotations.jsonl --out examples/report.md --html-out examples/qc-report.html
py -m unittest discover -s tests -q
```

**预期输出（逐字对照）**

第一条，校验评分标准：

```
ok: multilingual-answer-quality v1.0.0, 4 dimensions
  - factuality (事实性) weight=0.35
  - faithfulness (忠实度) weight=0.3
  - language (语言质量) weight=0.2
  - safety (安全边界) weight=0.15
```

第二条，出两份报告：

```
report written to examples/report.md
html report written to examples/qc-report.html
items=10 raters=3 exact=62.5% adjacent=92.5% kappa=0.530
arbitration queue: 3
```

第三条，跑测试：

```
Ran 24 tests in 0.0xx s

OK
```

然后双击 `examples/qc-report.html`，浏览器里应该看到：顶部一句话结论「可用：先处理 3 处仲裁」，一条 0–100 的刻度尺（黑点 62.5%、蓝点 92.5%、红色虚线 90），四个大数字，四张表。

**任何一步对不上，就是有问题，别当它已经能走。** 如果 `py` 报「不是内部或外部命令」，说明 Python 启动器没进 PATH；本机已确认 `py` 可用，`python` 反而被商店别名占用，所以命令里一律写 `py`。

## 三、三个数字怎么读（被追问时必须能答）

| 数字 | 含义 | 一句话解释 |
| --- | --- | --- |
| 完全一致率 62.5% | 40 个「条目 × 维度」里，25 个所有标注员给分完全相同 | 严格标准，档位多时天然偏低 |
| 相邻一致率 92.5% | 最高分与最低分之差 ≤ 1 分的比例 | **可用性标准**，90% 是验收线 |
| Fleiss κ 0.530 | 扣掉「瞎猜也会一致」的那部分之后的真实一致性 | 中等一致；分数高度集中时会失真，必须与相邻一致率并读 |

待仲裁 3 条：`zh-03` 的事实性（极差 3）、`zh-03` 的忠实度（极差 2）、`ms-03` 的事实性（极差 2）。这三条不投票、直接进仲裁，是工具替你省下的会议时间。

## 四、上线状态（截至 2026-11-14）

| 项目 | 状态 |
| --- | --- |
| 远端文件 | 13 个，与本地**逐文件按 git blob SHA-1 校验一致** |
| 测试 | 24 项全部通过（本机 Python 3.14.10 实跑） |
| 本人机器复跑 | **2026-11-14 由 Chan Chee Aun 在本机 Windows PowerShell 5.1 实跑通过**：validate 输出四维权重、report 输出 `exact=62.5% adjacent=92.5% kappa=0.530` 与 `queue: 3`、`Ran 24 tests ... OK`，与预期输出逐字一致 |
| HTML 报告 | 单文件、无脚本、无外链，可离线打开或打印成 PDF |
| 未推送 | `examples/qc-report.html`（本地生成，仓库里不放；跑上面第二条命令即可得到） |

`cli.py`、`tests/test_evalkit.py`、`README.md`、`evalkit/htmlreport.py` 四个文件的 blob SHA 已与 GitHub 返回值逐一核对，不是「显示成功」就算成功。

## 五、以后怎么改、怎么更新

改代码：只动 `evalkit/` 下的模块，`cli.py` 只管参数。改完必须跑第三条命令，测试不过不许推。

换数据：按 `data/sample_annotations.jsonl` 的格式写自己的标注记录（一行一条评分，同一条目多行），代码不用改。

换标准：改 `rubric.json`，维度权重必须合计 1.0；仲裁阈值 `spread` / `mad` 也写在这里，因为不同项目的松紧标准不同。

更新线上：把改过的文件推到 GitHub，推之前先给一份文件清单确认。推完按第二节重跑一次，本地与远端输出一致才算完成。

## 六、边界（主动说，比被人问出来强）

* 只处理评分，不处理文本质量本身。标准写错了，一致性再高也只是稳定地错。

* 条目少于 20 时 κ 估计不稳，此时只看完全一致率与偏差。

* 仲裁队列按极差排序，不判断谁对；仲裁仍然需要人。

* 没有趋势追踪，两次运行之间的一致性变化要自己对比两份报告。

* 示例数据全部合成，不含任何客户材料、真实题面或受保密协议约束的内容。
