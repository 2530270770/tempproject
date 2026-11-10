# 需求—测试追溯一致性检查器

| 项目信息 | 内容 |
| --- | --- |
| 组号 | T13 |
| 选题 | B 题：需求—测试追溯一致性 |
| 项目名称 | 需求—测试追溯一致性检查器 |
| 课程 | 高级软件工程（2026 秋） |

本项目面向符合统一约定的仓库，只读解析 `SRS.md` 中的功能需求（FR）和 `tests/` 中的测试用例（TC），依据 `covers: FR-xx` 建立双向需求—测试追溯矩阵（RTM），识别漏测、孤儿用例、重复或非法引用、关键需求缺正常/边界用例、全 FAIL 假覆盖，以及需求变更后的待回归项。

检查结果输出为 JSON 与 Markdown，每条问题保留编号、文件、行号或 commit 等可核对证据。系统不执行被检查仓库的构建或测试，不向目标仓库写入内容，也不对非结构化自然语言自动给出确定结论。

## 团队成员与分工

| 姓名 | 学号 | 角色 | 主要职责 |
| --- | --- | --- | --- |
| 陈俊鹏 | SA26225048 | 组长 | 需求基线与系统边界、Markdown 解析、基线差异、CLI 集成、README 与最终发布 |
| 陈磊 | SA26225049 | 组员 | 规则引擎、三个核心状态机、JSON/Markdown 报告、测试与质量、AI 留痕 |

两人均参与交叉评审和集成验证。陈磊复核系统边界、架构论证、解析器和 CLI；陈俊鹏复核规则边界、状态机、报告质量和测试结论。

## 当前进度

### M1：需求基线

- 已提交 `NABC.md`、`SRS.md`、`RTM.md` 和《需求审查分析报告》。
- 已明确 14 条 FR、5 条 NFR、角色权限矩阵和 B 题硬规则。
- 已按课程约定创建 tag `m1-requirements`。

### M2：架构与最小内核

M2 已在 `feature/m2-kernel` 集成分支完成最小内核，并通过 good/bad 样例验证：

- 已补充系统边界、一张构件图、ADR-001 和《架构决策论证报告》。
- 已实现 Markdown 模型、SRS/TC 解析器、双向 RTM、规则引擎和 CLI 编排。
- 已落地检查任务、需求/用例条目和变更回归三个核心状态机。
- 已实现 JSON/Markdown 报告、证据定位、角色权限和只读 GitLab 入口。
- M2 内容完成交叉评审并通过合并请求合入 `main` 后，创建 annotated tag `m2-architecture`。

### M3：测试与质量

- 已补齐 21 条结构化 TC 和 43 个自动化测试；
- 已增加内置 good、bad、regression 测试夹具，并完成两份教师完整标准样例的验收；
- 已兼容项目符号式 FR、`【critical】` 和标题式 TC；
- 项目自检为 14/14 FR 覆盖、关键正常/边界覆盖率 100%、0 issues；
- 教师标准样例和 m3 bad 样例均可检出 R3、R4 对应问题；
- 测试报告记录通过率、覆盖率和性能测量命令。

`m3-testing` 应在 m3 全部 MR 合入 `main`、人工评审通过后创建。

## 运行环境

- Python 3.10 或更高版本。
- 本地目录检查不需要网络。
- 远端 GitLab 仓库检查需要系统已安装 Git，并通过环境变量提供只读令牌。
- `PyYAML` 为可选依赖；未安装时使用仓库内的 YAML 子集解析器。

安装可选依赖：

```powershell
python -m pip install -r requirements.txt
```

## 检查命令

可按以下方式检查符合统一约定的仓库：

```powershell
python -m src check <目标仓库路径> `
  --output-dir <独立报告目录> `
  --team-id T13
```

若目标仓库位于 Git 历史中，可指定基线提交：

```powershell
python -m src check <目标仓库路径> `
  --baseline-ref <基线提交> `
  --output-dir <独立报告目录> `
  --team-id T13
```

远端仓库只读检查：

```powershell
$env:GITLAB_READ_TOKEN = "<只读令牌>"

python -m src check `
  --repo-url https://git.ustc.edu.cn/<命名空间>/<仓库>.git `
  --ref main `
  --output-dir <独立报告目录> `
  --team-id T13
```

令牌只从环境变量读取，不得写入代码、报告或 Git。

## m3 验收目标

给定包含结构化 FR/TC 的样例输入，系统应输出 FR—TC 双向 RTM，并至少识别：

- 存在 FR、但没有任何 `PASS` 用例覆盖的漏测项。
- `covers` 指向不存在 FR 的孤儿用例。
- 关键 FR 缺少正常或边界 `PASS` 用例。

规则只把 `实际结果: PASS` 计为覆盖；FAIL、UNKNOWN 或无法解析的结果不得静默提升覆盖率。

当前集成分支的验证结果：

- good 样例：6/6 FR 覆盖，0 个问题。
- bad 样例：正确报出 `FR-05` 漏测、`FR-02` 关键边界用例缺口和 `TC-22` 孤儿用例。
- 教师标准样例和 m3 bad 样例：均正确报出 `MISSING_TEST(FR-05)`、`CRITICAL_NO_BOUNDARY(FR-02)` 和 `ORPHAN_TEST(TC-22)`。样例 TC 未写实际结果，因此严格按 UNKNOWN 处理，并报告其余真实覆盖缺口。
- 项目自身：14/14 FR、21 条 TC、0 个问题。

## 报告约定

JSON 报告使用统一公共字段，包括：

```text
team_id
project
commit
checked_at
read_only
requirements
tests
coverage
regression
issues
```

Markdown 报告展示双向 RTM、覆盖率、问题码、证据位置和变更回归清单。同一输入重复检查时，除 `checked_at` 外应产生相同结论和相同问题顺序。

## M2 与 m3 文档

```text
docs/m2-架构与设计/
├── architecture.md              # 系统边界、构件图与运行边界
├── ADR.md                       # 架构决策记录
├── design.md                    # 模块、三个状态机与关键算法
└── 架构决策论证报告.md          # 甲乙丙方案比较、风险、选型与 ADR

docs/m3-测试/
├── 测试报告.md                  # 命令、通过率、覆盖率与标准样例结果
└── Eval集.md                    # 最小评测集与问题码断言
```

## 目录结构

```text
T13/
├── README.md
├── assessment.yml
├── team-roster.yml
├── requirements.txt
├── common/
│   ├── config.py                # 花名册和评阅配置读取
│   ├── repo.py                  # 只读 Git 命令封装
│   └── report.py                # 统一报告 JSON 基类
├── docs/
│   ├── m1-立项与需求/
│   ├── m2-架构与设计/
│   └── m3-测试/
├── process/
│   ├── ai-log.csv               # AI 交互日志
│   ├── ai-log-hash-chain.csv    # 日志哈希链
│   └── review-checkpoints.yml   # 里程碑人工评审点
├── scripts/
│   └── ai_log_tool.py           # 追加日志并校验哈希链
├── tests/
│   ├── TC-01.md ~ TC-21.md      # 每个文件一条结构化追溯用例
│   ├── __init__.py              # 内置测试夹具
│   ├── coverage_report.py       # m3 覆盖率测量
│   └── test_*.py                # 43 个自动化测试
└── src/
    ├── __main__.py
    └── traceability/
        ├── __init__.py
        ├── cli.py
        ├── engine.py
        ├── models.py
        ├── parser.py
        ├── permissions.py
        ├── reporting.py
        └── state_machines.py
```

`src/traceability/` 包含 M2 最小内核和 M3 标准样例兼容修正。只有明确的 `实际结果: PASS` 计入覆盖；缺失、`NOT PASS`、`FAIL（期望 PASS）` 等文本均不得被推断为 PASS。

## AI 与过程留痕

AI 仅用于辅助生成初稿、解释材料和整理结构。需求基线、架构选型、规则边界和最终结论由组员人工审查并接管。

每次使用 AI 后通过 `scripts/ai_log_tool.py` 追加日志并更新哈希链：

```powershell
python scripts\ai_log_tool.py verify
```

每个里程碑至少登记一次人工评审。本仓库不修改或删除历史日志，人工动作、审查人和决策人必须真实可核验。

## 安全与范围

- 只读访问被检查仓库，不执行其中的代码或测试。
- 不向目标仓库写入、修复或提交内容。
- 不保存 GitLab 令牌。
- 不评价用例设计质量，不替代人工评审。
- 不做子项目 A 的贡献统计，也不做子项目 C 的完整 AI 合规审计。
- M3 文档中的测试数量、覆盖率和性能数据均来自 2026-11-10 的实际复跑。
