# 最小评测集（Eval）

本项目选择 B，只负责需求—测试追溯一致性。正式标准样例验收必须直接使用老师提供的完整仓库目录。

| 评测对象 | 输入特点 | 期望 |
| --- | --- | --- |
| 内置 good 测试夹具 | 表格式 FR/TC，全部为 PASS | 0 issues；FR、关键正常和关键边界覆盖率均为 100% |
| 内置 bad 测试夹具 | 含 FR-05 漏测、FR-02 缺边界、TC-22 孤儿 | `MISSING_TEST(FR-05)`、`CRITICAL_NO_BOUNDARY(FR-02)`、`ORPHAN_TEST(TC-22)` |
| 老师完整标准仓库 `team-99` | 项目符号 FR、标题式 TC；TC 未写实际结果 | 至少报出 R3、R4；其余 TC 严格按 UNKNOWN 处理 |
| 老师完整 m3 bad 仓库 | 格式与标准样例一致；完整仓库目录 | 与标准样例一致，问题码和行号可定位 |
| 项目自身 | 14 条 FR、21 条结构化 TC | 14/14 FR、0 issues、关键正常和边界覆盖率均为 100% |

内置 good、bad 和回归夹具存放在 `tests/__init__.py` 中，通过临时目录生成完整仓库形态，不需要额外的 `examples/` 目录。

## 自动化测试命令

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

## 完整教师仓库验收命令

以下命令均在仓库根目录执行。标准样例目录使用相对路径；若本地目录结构不同，只需替换输入路径，不要把本机绝对路径写入仓库文档。

```powershell
python -m src check `
  "..\要求\⑥标准样例仓库（修正版）v1.2\team-99" `
  --output-dir "$env:TEMP\T13-m3-standard" `
  --team-id G99

python -m src check `
  "..\要求\埋雷样板仓库（bad·m3发学生）\bad-repo-team-99" `
  --output-dir "$env:TEMP\T13-m3-bad" `
  --team-id G99
```

项目自检命令：

```powershell
python -m src check . --output-dir "$env:TEMP\T13-m3-self" --team-id T13
```

## 验收记录

- R3：通过。`FR-05` 无 PASS 用例；`FR-02` 为 critical，只有正常用例、没有边界用例。
- R4：通过。`TC-22` 的 covers 为 `FR-99`，目标需求不存在。
- 标题式格式兼容：通过。`- FR-xx`、`【critical】`、`# TC-<编号> (...)` 均被结构化。
- 实际结果边界：通过。只有明确的 `PASS` 计为通过；样例未写实际结果时保持 UNKNOWN，不推断为 PASS。
- 非结构化输入：通过。系统不猜造需求或覆盖关系，进入人工处理路径。
- 回归：通过。修改、删除、受影响用例和待回归状态均有确定性输出。
- 幂等：通过。同输入重复运行除检查时间外结论一致。

每条问题必须带 `ref/file/line`。good 样例不得出现 HIGH 误报；如果出现误报，应修正契约或规则，而不是放宽全部判定。
