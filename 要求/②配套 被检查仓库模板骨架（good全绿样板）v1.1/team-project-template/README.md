# 综合项目模板仓库（good 样例）

> 这是《综合项目》的标准仓库起点，已经按附件②《被检查仓库统一约定》摆好目录。
> 复制本仓库后改名即可开始。本项目**不依赖 CI Runner**：测试在本地跑、结果写进 m3 测试报告。

## 怎么用
1. 复制本仓库为你们组的项目仓库，按选题填好 `team-roster.yml` 与 `assessment.yml`。
2. 需求、架构、测试、交付文档分别放入 `docs/m1…m4` 对应目录。
3. 代码放 `src/`，测试放 `tests/`（每条用例注明 `covers: FR-xx`）。
4. AI 交互记到 `process/ai-log.csv`（追加写、勿删改），评审点登记到 `process/review-checkpoints.yml`。
5. 每个里程碑完成后打语义化 tag：`m1-requirements`、`m2-architecture`、`m3-testing`、`m4-release`，终交打 `final`（用 `git tag -a 名称 -m "说明"`）。
6. 公共脚手架在 `common/`（只读克隆、配置读取、报告 JSON 基类），可直接用或改写；核心规则自己写。

## 目录索引
- `team-roster.yml`：学号—姓名—GitLab 账号—角色，贡献核查的基础。
- `assessment.yml`：里程碑截止讲次、评分权重、各子项目阈值（不是 GitLab 的 .gitlab-ci.yml）。
- `common/`：与业务无关的公共底座（repo.py / config.py / report.py）。
- `docs/`：各里程碑交付文档；`src/`：源码；`tests/`：测试用例；`process/`：留痕与评审。

## 运行方式
- 检查系统：`python -m src.<你们的入口>`（具体入口由各组实现）。
- 本地测试（自己的系统）：`python -m pytest tests`，需要覆盖率时 `python -m pytest --cov=src`。
- 依赖：`pip install -r requirements.txt`（仅需 PyYAML；Git 命令依赖系统已安装 git）。
- 不要求、也不依赖学校 GitLab 的 CI Runner；m3 测试报告写清命令与结果，抽审现场复现。

## 安全红线
- 只读令牌、绝不回写学生仓库；凭证不提交到仓库。
- 不按代码行数给分；生成物/脚手架/AI 未接管代码不计入个人贡献。
