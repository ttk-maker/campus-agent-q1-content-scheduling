# 评估

本页记录首轮完整验收。2026-11-06 后续新增 Web 工作台和困难边界修复；最新 69 项分层测试、浏览器和真实模型边界验证见 [本轮稳健性报告](09-robustness-and-web.md)。examples/real/ 保留首轮证据，不将其误写为本轮完整重测。

环境：Windows / Python 3.10.11；真实模型 Ollama qwen2.5:7b-instruct，温度 0。本地采用 CPU 推理，无需 API Key。

自动化测试：37 项通过，见 [原始输出](../examples/unit-tests.txt) 和 [命令及环境](../examples/unit-tests.json)。离线 11 组场景、14 次 Agent 运行、61 条检查通过，见 [验收报告](../examples/mock/acceptance.json) 和 [清单](../examples/mock/manifest.json)。真实模型最终批次：11 组场景、14 次运行、61 条检查通过，见 [真实验收报告](../examples/real/acceptance.json) 与 [清单](../examples/real/manifest.json)。

## 六类验收与证据

| 验收点 | 预期结果 | 离线实际结果 | 真实模型最终证据路径 |
| --- | --- | --- | --- |
| 正常排期 | 保留原定时间，ready 草稿，未发布 | completed / ready | [normal](../examples/real/normal/output-1.json) |
| 信息缺失 | 明确缺失字段，补查或请求资料 | needs_information，零草稿 | [missing](../examples/real/missing/output-1.json) |
| 规则风险 | 报告风险并阻断 | blocked，零草稿 | [risk](../examples/real/risk/output-1.json) |
| 时段冲突 | 原定 18:00，建议 19:00 待确认 | needs_confirmation / effective_at=null | [conflict](../examples/real/conflict/output-1.json) |
| 重复提交 | 同一 draft_id，只一份草稿 | 第二次 existing，draft_count=1 | [duplicate](../examples/real/duplicate/output-2.json) |
| 保存失败 | 明确失败，不伪报成功 | failed，零草稿 | [save-failure](../examples/real/save-failure/output-1.json) |

每个目录含 input.json、fixture.json、output-N.json、trace-N.jsonl、storage-summary.json。离线对应目录在 examples/mock/。全部业务资料为合成数据；真实与 Mock 模式分开记录。

## 真实动态决策路径

- [正常 Trace](../examples/real/normal/trace-1.jsonl)：规则通过且时段空闲，模型选择保存原时间。
- [缺资料 Trace](../examples/real/missing/trace-1.jsonl)：观察到授权信息缺失，模型选择补查或请求补充。
- [冲突 Trace](../examples/real/conflict/trace-1.jsonl)：观察原时段占用，模型选择替代时段，工具返回待确认草稿。
- [保存失败 Trace](../examples/real/save-failure/trace-1.jsonl)：写入失败后模型选择失败终态。

Trace 仅记录外部动作、参数、观察与简要理由，不含模型内部思维过程。Mock 不作为真实模型决策证据。

## 审核要点与痛点强化

- 更换占用：[changed-occupancy](../examples/mock/changed-occupancy/output-2.json)，同一数据库和请求先产生待确认草稿；占用改为 19:00 后重提，原定 18:00 可用，按原要求更新同一份草稿。
- 确认升级：[confirmation](../examples/mock/confirmation/output-2.json) 和 [独立用户确认](../examples/mock/confirmation/user-confirmation.json)，同一草稿变为 ready。
- 预算：[budget](../examples/mock/budget/output-1.json)，两步后返回 budget_exhausted，不产生草稿。
- tests/test_scheduling.py 覆盖并发同请求、并发抢时段、确认后被占用、旧确认失效、素材版本变化、同键不同需求、恶意素材、非法发布/确认、保存失败后的虚假完成声明。
- tests/test_model_adapter.py 检查观察回传、网络错误脱敏、本地免密与远端认证约束。

## 失败与修复（保留事实）

1. 默认 Python 3.14 缺少 unittest.suite 和 stringprep，切换完整 Python 3.10.11；README 给出命令。
2. SQLite 事务上下文不会自动关闭连接，Windows 生成器曾因文件锁清理失败。存储层及生成器确保关闭连接后重新生成成功。
3. [第一轮真实模型失败](../examples/real-initial-failure/README.md)：模型因时区换算先误选已占用时段，工具拦截后恢复；重复运行时误解 existing，最终返回 failed，数据库仍只有一份待确认草稿。保留 [原始失败 Trace](../examples/real-initial-failure/duplicate/trace-2.jsonl)。修复为候选使用用户时区，明确 saved/existing 都表示草稿操作成功，增加操作完成和待确认的独立字段；没有放宽写入或确认约束。

## 限制

- 单轮、小规模合成场景不能证明真实生产成功率；尚无多轮统计稳定性或延迟分位数评估。
- 合成规则只检查必填、授权和禁用词；不覆盖完整内容安全审核。
- 只查询原定时间及之后三个整小时间隔；不支持复杂节假日、优先级和多日期时间窗。
- CLI 操作者可信；生产系统需身份认证。确认后必须重跑以重新审核与查占用。
- CLI 每次以事务同步调用方提供的完整占用快照，再执行 Agent；更换占用后的重复提交使用同一数据库。生产环境仍需增加占用版本与认证来源。
- 待确认不占位，ready 草稿占位；改变 ready 意图需新请求。尚未提供取消草稿接口。
- CPU 调用可能超过 45 秒；非法 JSON 或网络错误明确失败。未验证云端供应商实际效果。
- Prompt 优先建议先补查，但最终真实 missing 案例没有遵循这一偏好：模型试图查时段，被审核守卫拒绝后直接请求补充。该终态满足缺资料安全边界，但不应描述成已经补查；补查能力由 supplement 案例单独展示，后续需评估补查遵循率。
- 未提供真实发布、公网托管或 Figma 在线文件；当前已新增本机 Web 工作台，SVG 原型仍可导入。


## 最终真实模型运行汇总

| 场景 | 运行次数 | 最后一次实际终态 |
| --- | --- | --- |
| normal | 1 | completed |
| missing | 1 | needs_information |
| risk | 1 | blocked |
| conflict | 1 | needs_confirmation |
| duplicate | 2 | needs_confirmation |
| save-failure | 1 | failed |
| supplement | 1 | completed |
| confirmation | 2 | completed |
| batch | 1 | completed, needs_confirmation, needs_information |
| budget | 1 | budget_exhausted |
| changed-occupancy | 2 | completed |

共 87 个模型/工具步骤，含 9 次被执行器拒绝的动作；最终终态验收通过不意味着每一步都无误。拒绝与恢复过程原样保留在 Trace，没有删除失败步骤。没有对不同随机种子或模型版本进行统计测试。
