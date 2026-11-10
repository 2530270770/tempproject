"""Shared in-memory fixtures for the required m3 test suite."""

from pathlib import Path


GOOD_SRS = """# Good 追溯样例

SRS 版本: v1

| 编号 | 需求描述 | 优先级 | 验收标准 | 版本 |
| --- | --- | --- | --- | --- |
| FR-01 | 解析结构化需求 | 必做 | 字段完整 | v1 |
| FR-02 | 校验关键需求覆盖 | critical | 正常和边界均通过 | v1 |
| FR-03 | 识别孤儿用例 | 必做 | 引用不存在时报错 | v1 |
| FR-04 | 输出双向 RTM | 必做 | 两个方向均可定位 | v1 |
| FR-05 | 比较基线差异 | 必做 | 修改项进入影响清单 | v1 |
| FR-06 | 生成标准 JSON | 必做 | 公共字段齐全 | v1 |
"""

GOOD_TESTS = """# Good 用例集

用例编号: TC-01
covers: FR-01
类型: 正常
步骤: 解析一个需求表格
预期结果: 得到完整需求
实际结果: PASS

用例编号: TC-02
covers: FR-02
类型: 正常
步骤: 检查关键需求
预期结果: 正常用例满足覆盖
实际结果: PASS

用例编号: TC-03
covers: FR-02
类型: 边界
步骤: 检查关键需求边界
预期结果: 边界用例满足覆盖
实际结果: PASS

用例编号: TC-04
covers: FR-03
类型: 正常
步骤: 检查孤儿引用
预期结果: 正确形成反向索引
实际结果: PASS

用例编号: TC-05
covers: FR-04
类型: 正常
步骤: 生成 RTM
预期结果: 双向关系完整
实际结果: PASS

用例编号: TC-06
covers: FR-05
类型: 正常
步骤: 提供基线
预期结果: 输出差异
实际结果: PASS

用例编号: TC-07
covers: FR-06
类型: 正常
步骤: 生成 JSON
预期结果: 字段齐全
实际结果: PASS
"""

BAD_SRS = """# Bad 标准样例

SRS 版本: v1

| 编号 | 需求描述 | 优先级 | 验收标准 | 版本 |
| --- | --- | --- | --- | --- |
| FR-01 | 正常覆盖需求 | 必做 | 有 PASS 用例 | v1 |
| FR-02 | 关键需求仅正常覆盖 | critical | 需要正常和边界 | v1 |
| FR-03 | 有正常用例 | 必做 | 有 PASS 用例 | v1 |
| FR-04 | 有无效等价类用例 | 必做 | 有 PASS 用例 | v1 |
| FR-05 | 故意没有测试 | 必做 | 应报漏测 | v1 |
"""

BAD_TESTS = """# Bad 标准用例集

用例编号: TC-01
covers: FR-01
类型: 正常
步骤: 检查第一条需求
预期结果: 正常
实际结果: PASS

用例编号: TC-02
covers: FR-02
类型: 正常
步骤: 检查关键需求
预期结果: 只有正常用例
实际结果: PASS

用例编号: TC-03
covers: FR-03
类型: 正常
步骤: 检查第三条需求
预期结果: 正常
实际结果: PASS

用例编号: TC-04
covers: FR-04
类型: 无效等价类
步骤: 检查第四条需求
预期结果: 正常
实际结果: PASS

用例编号: TC-22
covers: FR-99
类型: 无效等价类
步骤: 检查不存在的需求
预期结果: 应报孤儿用例
实际结果: PASS
"""

REGRESSION_BASELINE_SRS = """# 基线 SRS

SRS 版本: v1

| 编号 | 需求描述 | 优先级 | 验收标准 | 版本 |
| --- | --- | --- | --- | --- |
| FR-01 | 旧的需求描述 | 必做 | 旧验收标准 | v1 |
| FR-02 | 将被删除的需求 | 必做 | 原验收标准 | v1 |
| FR-03 | 保持稳定的需求 | 必做 | 保持稳定 | v1 |
"""

REGRESSION_CURRENT_SRS = """# 当前 SRS

SRS 版本: v2

| 编号 | 需求描述 | 优先级 | 验收标准 | 版本 |
| --- | --- | --- | --- | --- |
| FR-01 | 修改后的需求描述 | 必做 | 新验收标准 | v2 |
| FR-03 | 保持稳定的需求 | 必做 | 保持稳定 | v2 |
"""

REGRESSION_TESTS = """# 待回归用例集

用例编号: TC-01
covers: FR-01
类型: 正常
验证需求版本: v1
步骤: 旧版本用例
预期结果: 应进入待回归
实际结果: PASS

用例编号: TC-02
covers: FR-02
类型: 正常
验证需求版本: v1
步骤: 删除需求的旧用例
预期结果: 应进入待回归
实际结果: PASS

用例编号: TC-03
covers: FR-03
类型: 正常
验证需求版本: v2
步骤: 稳定需求用例
预期结果: 已完成回归
实际结果: PASS
"""

TEACHER_STANDARD_SRS = """# 自动评阅系统 SRS（G99 组）

## 功能需求
- FR-01 仓库连通性检查：给定仓库链接，只读克隆并报告是否可达。
- FR-02【critical】个人贡献统计：统计每位成员被合并的提交、合并请求、触及模块，标记零贡献、集中提交等异常。
- FR-03 里程碑标签检查：核对语义化标签是否按时、顺序是否合规。
- FR-04 报告导出：导出统一 JSON 与 Markdown 报告。
- FR-05 孤儿用例检测：找出指向不存在需求的测试用例。
- FR-06 AI 日志完整性：校验 ai-log 哈希链与审查记录是否齐全。

## 非功能需求
- NFR-1 约 40 个仓库巡检，单仓库从提交链接到出报告不超过 30 秒。
- NFR-2 同一 commit 重跑结论一致（幂等）。
- NFR-3 对仓库全程只读，无写权限。
"""

TEACHER_STANDARD_TEST_FILES = {
    "TC-01-仓库连通.md": """# TC-01 仓库连通性（happy）
covers: FR-01
前置：链接有效、只读令牌有效。
步骤：提交链接 → 克隆。
预期：报告仓库可达。
""",
    "TC-02-贡献统计.md": """# TC-02 个人贡献统计（happy）
covers: FR-02
前置：4 名成员、提交正常。
步骤：运行贡献统计。
预期：输出每人提交数与被合并贡献。
""",
    "TC-03-标签检查.md": """# TC-03 里程碑标签检查（happy）
covers: FR-03
步骤：读取标签并比对配置。
预期：按时/顺序异常被标记。
""",
    "TC-04-报告导出.md": """# TC-04 报告导出（happy）
covers: FR-04
步骤：运行导出。
预期：生成 JSON 与 Markdown。
""",
    "TC-22-某检查项.md": """# TC-22 某检查项
covers: FR-99
前置：无。
步骤：构造输入并运行。
预期：输出对应结果。
""",
}


def write_repository(
    root: Path,
    *,
    srs: str,
    tests: str | dict[str, str],
    team_id: str = "G99",
) -> Path:
    """Create a complete repository-shaped fixture inside a temporary directory."""
    docs = root / "docs" / "m1-立项与需求"
    tests_dir = root / "tests"
    docs.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    (docs / "SRS.md").write_text(srs, encoding="utf-8")
    if isinstance(tests, str):
        (tests_dir / "TC.md").write_text(tests, encoding="utf-8")
    else:
        for name, content in tests.items():
            (tests_dir / name).write_text(content, encoding="utf-8")
    (root / "team-roster.yml").write_text(
        "course: 高级软件工程\n"
        "team:\n"
        f"  id: {team_id}\n"
        "  project: B\n"
        "  members:\n"
        "    - student_id: \"00000000\"\n"
        "      name: 测试用户\n"
        "      gitlab: fixture-user\n"
        "      role: 组长\n"
        "      modules: 测试夹具\n",
        encoding="utf-8",
    )
    (root / "assessment.yml").write_text(
        "milestones:\n"
        "  m3: {tag: m3-testing, due_lecture: L25}\n"
        "weights:\n"
        "  team: 70\n"
        "  ta_individual: 22\n"
        "  peer: 8\n"
        "traceability_thresholds:\n"
        "  min_cases_per_fr: 1\n"
        "  critical_requires_boundary: true\n"
        "  critical_requires_happy: true\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        "# Temporary complete repository fixture\n",
        encoding="utf-8",
    )
    return root
