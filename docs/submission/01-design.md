# 题目1 · 素材审核与发布排期 Agent：设计说明

交付日期：2026-11-07（Asia/Shanghai）。提交题号：1。仓库：https://github.com/ttk-maker/campus-agent-q1-content-scheduling。固定交付标签：`q1-submission-20261107`。配套文档：https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/docs/submission/02-delivery-and-acceptance.md 。

本文件供评审理解业务、动态决策、工程边界与实际证据。最终提交 SHA 由固定标签解析：`git rev-parse q1-submission-20261107^{commit}`；本地独立交付副本首页附最终完整 SHA。文档不把自身所属 commit 的 SHA 写入自身正文，以避免自引用改变 commit。

## 1. 用户、需求与范围

帮助内容团队审核待处理素材，在保留硬性发布时间要求的前提下形成无冲突、可确认的排期草稿。

- 输入：素材 ID、元数据、发布时间要求、已有排期与审核规则；全部示例使用合成资料。
- 输出：每项素材的审核状态、风险原因、原定/建议/生效时间、待确认项、草稿 ID 和保存状态；始终明确未发布。
- 成功标准：覆盖题目全部必须验收点，至少两条不同工具观察后的真实模型决策路径；硬约束由程序复验，工具实际失败不得虚报成功。
- 范围：CLI 与本机 HTTP/Web 工作台均可运行。业务工具使用合成资料、本地函数和SQLite；真实模型使用Ollama `qwen2.5:7b-instruct`。Mock只验证流程，不证明真实决策能力。

## 2. 动作流与模型职责

读取素材 → 检查规则 → 必要时补查 → 查询时段 → 模型按工具观察选择原时段、替代时段或停止 → 工具保存草稿 → 模型结束。

动作接口：`read_asset(include_supplement)`、`check_rules()`、`query_slots()`、`save_draft(suggested_at)`、`finish(outcome)`。

每轮模型输出一个动作、参数及简短决策依据；执行器校验后执行工具，将实际观察回传模型，再产生下一动作或结束。Trace保存步骤、工具参数、返回结果和后续动作，不收集模型内部思维过程。预设状态骨架限定合法动作，模型负责范围内的具体选择；最终状态以工具证据为准。

正常路径在规则通过、原时段可用后保存原时间；冲突路径观察到18:00占用后建议19:00，工具保存待确认草稿，原硬性时间不生效变更；写入失败时返回真实失败。模型可选择补查、替代时段或终态，工具独立核验授权与事实。

默认单请求24步，批量素材共享预算；模型 HTTP 单次45秒；达到动作上限返回 `budget_exhausted`，未处理素材也明确标记。

## 3. 架构与可靠性

CLI/Web → Agent循环与模型适配器 → 确定性工具与守卫 → SQLite；工具观察返回模型，输出状态由实际持久结果构造。无需多Agent或生产Runtime。

草稿以 `(request_id, asset_id)` 唯一，需求摘要防止同键不同输入；SQLite `BEGIN IMMEDIATE` 事务内复验风险、占用并保存。确认绑定请求、素材版本与建议时间，旧确认失效；待确认草稿不占位，ready 草稿才占位。可信用户确认是独立入口，不向模型开放。

Python 3.10+标准库承担CLI、HTTP、模型请求与测试，SQLite承担本地事务和持久化。未使用第三方Agent框架。选择原生实现是为了使状态、授权、失败与重试边界容易检查；代价是需要自行维护协议与持久化逻辑。Node.js/Playwright仅用于浏览器自动化，不是应用启动依赖。

Web只监听本机，包含同源/Host/会话令牌与请求大小守卫；这是本机演示边界，不是生产账号认证。完整执行Trace应及时导出；网页内存任务记录有限，业务结果仍持久化。

## 4. 原型与前端

[可导入Figma的动作流与痛点SVG](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/docs/prototypes/agent-flow.svg)。图稿已交付，本项目没有Figma在线文件。前端为桌面结果画布+参数侧栏，窄屏先输入后结果；显示设置即时变更主题色、明暗、字号、密度和动效，偏好按项目保存在本地浏览器。业务参数只更新预览，显式点击运行才调用Agent，已有结果不会随预览改写。设计参考Open Design Tweaks，代码按本项目业务独立实现。

[实时调参设计与验证](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/docs/11-live-tweaks.md)；[网页使用手册](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/docs/08-user-manual.md)。

## 5. 验收点与证据

| 验收点 | 实际证据 | 核对重点 |
|---|---|---|
| 正常排期 | [输入、输出与运行记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/real/normal) | completed / ready，原时段保持，未发布 |
| 信息缺失 | [输入、输出与运行记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/real/missing) | needs_information，零草稿；不能把该例称为已完成补查 |
| 规则风险 | [输入、输出与运行记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/real/risk) | blocked，零草稿，列出风险 |
| 时段冲突 | [输入、输出与运行记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/real/conflict) | 18:00→建议19:00，needs_confirmation，effective_at为空 |
| 重复提交 | [输入、输出与运行记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/real/duplicate) | 两次同 draft_id，保存份数为1，第二次 existing |
| 保存失败 | [输入、输出与运行记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/real/save-failure) | failed，零草稿，不虚报成功 |
| 更换占用后重提 | [输入、输出与运行记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/real/changed-occupancy) | 同请求与数据库观察新占用快照，再次调整 |
| 独立确认与复验 | [输入、输出与运行记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/real/confirmation) | 确认后重跑，原草稿升级ready；仍未发布 |

至少两条真实模型循环的直接入口：

- [正常动作记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/examples/real/normal/trace-1.jsonl)
- [冲突调整动作记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/examples/real/conflict/trace-1.jsonl)
- [保存失败动作记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/examples/real/save-failure/trace-1.jsonl)

证据同时保存输入、实际输出、Trace；目录中的JSON/JSONL是实际运行记录，截图只是补充。缺输入的入口守卫和Mock不计作真实模型决策证明。

## 6. 测试、失败与改进

本次交付从Git源码归档解压到独立目录，重跑全量Python测试 **69项**、离线CLI与历史证据校验；结果见 [交付前检查](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/examples/submission/preflight.json)。历史前端回归：业务19项、展示35项、实时调参37项通过；最终文档提交还将执行GitHub CI。CI只运行工程/Mock验证，不声称在runner上运行真实Qwen。

初轮真实模型曾误解 existing 导致失败终态；增加“操作完成”和“待确认”的区分。后续强化过期确认、已保存草稿失效、写入竞争、运行中刷新恢复；真实“全部时段占满”首轮未正确结束，补充工具容量语义后复测通过。失败日志保留。

原始失败：[examples/real-initial-failure/](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/real-initial-failure)、[examples/robustness/real-before-capacity-fix/](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107/examples/robustness/real-before-capacity-fix)。最新综合证据入口：[验收结果](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/examples/robustness/real/report.json)。历史目录里保留false报告是审计事实，不应删除，也不能仅选旧报告推断最新复测结果。

本次是交付封装，未修改后端、模型或前端运行逻辑，未再次调用模型生成整套真实结果；真实决策记录来自先前实际执行，本次程序重新核对留存证据。

## 7. 已知限制与下一步

只查询原时段及其后三个整小时间隔，易于复现但不覆盖复杂日期窗口；合成必填/授权/禁词规则不能替代生产审核。每次调用方提供完整排期快照，生产仍需可信来源与版本控制。未提供取消草稿接口、账户认证、真实发布或公网服务。

样本为小规模合成场景，不代表生产成功率。模型可能返回非法动作、反复尝试、超时或达到步数上限，系统须诚实报告未完成。下一步优先扩展真实资料和模型重复评估，再根据业务接入生产服务、身份权限与可观测性。

## 8. AI辅助、个人贡献和用时

用户实际贡献：提供题目、规则、验收要求，决定项目优先级、额外边缘测试和前端方向，提供参考模板。AI承担需求梳理、原型、代码、测试、实际模型试验、失败分析、文档与GitHub操作。没有把AI生成内容记为候选人独立编码，也没有虚构用户已手工验收的记录。详见 [AI使用记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/docs/04-ai-usage.md) 与 [复盘](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/docs/05-retrospective.md)。

首轮2026-11-06 14:04–14:53，约49分钟；网页与稳健性追加15:24–15:57，约33分钟，含CPU推理、测试与等待。 三项目共同前端精简2026-11-06 22:25–22:41约16分钟；共同Tweaks改造23:43至11-07 00:01约18分钟。实际累计已超过官方建议3小时，应按实际报告；这些是开发会话跨度，包含AI、推理与CI等待，不等于候选人个人独立工作时长。此次封装自2026-11-07 15:28开始，结束与耗时附最终交付副本。
