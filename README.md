# 题目 1：素材审核与发布排期 Agent

帮助内容团队审核素材并保存排期草稿。**仅草稿，不接真实发布。**

当前阶段：需求与接口设计完成，正在实现与验证。真实模型尚未配置，不能声明满足真实 ReAct 决策验收。

## 评审入口

- [需求与验收](docs/01-requirements.md)
- [架构与决策边界](docs/02-solution.md)
- [评估与证据](docs/03-evaluation.md)
- [AI 使用](docs/04-ai-usage.md)
- [复盘](docs/05-retrospective.md)
- [动作流原型与痛点](docs/06-prototype-and-hardening.md)

技术选择：Python 3.11+ CLI、标准库 HTTP 模型适配、SQLite 原子持久化。无需第三方 Agent 框架、Web 服务或线上部署。

