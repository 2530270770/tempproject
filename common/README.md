# common/ 公共脚手架

只做与业务无关的通用底座，避免各组重复造轮子，并统一报告格式。

| 文件 | 能力 | 不做什么 |
|---|---|---|
| config.py | 读 assessment.yml / team-roster.yml，按选题取阈值；PyYAML 缺失时使用内置子集解析器 | 不内置阈值，以配置为准 |
| repo.py | 只读克隆、只读 git 命令白名单 | 不 push、不执行被测仓库测试 |
| report.py | Issue / ReportBuilder 报告 JSON 基类 | 不判定问题，issues 由你填 |

## 最小用法
```python
from common import load_assessment, load_roster, threshold_for_project
from common import readonly_clone, ReportBuilder, Issue, Severity

team_id, project, roster = load_roster("team-roster.yml")
cfg = load_assessment("assessment.yml")
th = threshold_for_project(cfg, project)

dest = readonly_clone("https://gitlab.example.com/grp/t07.git", "work/t07",
                      token=READONLY_TOKEN)
report = ReportBuilder(team_id, project, commit="a1b2c3d")
report.set("members", [])  # 你的统计结果
report.add_issue(Issue("ZERO_CONTRIB", Severity.HIGH, "成员 2026004 无被合并提交",
                       {"student_id": "2026004"}))
report.save("report-T07.json")
```

规则提示：阈值（如 min_merged_contributions、bigbang_window_hours）从
`assessment.yml` 读取，不要写死在代码里；规则与问题码由本组实现，至少 8 条。
