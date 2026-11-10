# 架构与构件图

## 1. 系统边界

- 系统内：读取目标仓库、解析结构化 FR/TC、建立双向 RTM、执行一致性规则、比较基线、驱动变更回归、输出 JSON/Markdown 报告。
- 边界外系统：校内 GitLab 提供仓库与历史，统一身份认证提供已核验角色。AI 服务是可选初筛能力，当前版本不接入，也不参与追溯结论定稿。
- 明确不做：不执行被检查仓库构建/测试；不评价用例设计质量；不向目标仓库写入；不做 A 的贡献统计或 C 的 AI 合规审计；不对自然语言自动给出确定追溯结论。

## 2. 构件图

```mermaid
flowchart LR
    U[教师/助教/学生] -->|已认证角色与组号| CLI[CLI 编排]
    G[(目标仓库或 GitLab)] -->|只读 SRS/TC/Git 历史| CLI
    CFG[(assessment.yml)] -->|阈值配置| CLI
    CLI --> AUTH[权限策略]
    CLI --> TASK[检查任务状态机]
    TASK --> P[Markdown 解析器]
    P --> MODEL[结构化 FR/TC 模型]
    BASE[(基线 SRS)] --> MODEL
    MODEL --> ENGINE[追溯规则引擎]
    ENGINE --> ENTRY[需求/用例状态机]
    ENGINE --> REG[变更回归状态机]
    ENGINE --> REPORT[JSON + RTM + 差异清单]
    REPORT --> REVIEW{人工确认}
    REVIEW -->|确认| ARCHIVE[归档报告]
    REVIEW -->|打回并重新检查| TASK
```

系统对目标仓库始终只读，不执行其代码，也不向其写入任何内容。正常检查路径是输入解析、规则分析、生成报告和人工确认；人工打回报告时可以重新进入检查流程，但不会修改目标仓库。报告只写入独立输出目录。
