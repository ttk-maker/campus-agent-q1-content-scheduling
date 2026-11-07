# 题目1 · 素材审核与发布排期 Agent：提交与考官验收指南

交付日期：2026-11-07（Asia/Shanghai）。本文件包含提交入口、版本、访问/密钥说明、复制运行命令、逐项验收及故障定位。

## 1. 提交信息

| 项目 | 信息 |
|---|---|
| 提交题号 | 1 |
| 题目名称 | 素材审核与发布排期 Agent |
| GitHub仓库 | https://github.com/ttk-maker/campus-agent-q1-content-scheduling |
| 可见性 | Public，匿名可读，无需评审账号授权 |
| 固定交付标签 | `q1-submission-20261107` |
| 固定源码地址 | https://github.com/ttk-maker/campus-agent-q1-content-scheduling/tree/q1-submission-20261107 |
| 源码下载 | https://github.com/ttk-maker/campus-agent-q1-content-scheduling/archive/refs/tags/q1-submission-20261107.zip |
| 最终commit SHA | 以 `git rev-parse q1-submission-20261107^{commit}` 解析；独立交付副本首页列出完整SHA |
| 设计说明 | https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/docs/submission/01-design.md |
| CI | https://github.com/ttk-maker/campus-agent-q1-content-scheduling/actions；核对最终SHA对应成功运行，独立交付副本首页附精确链接 |
| 本机Web | `http://127.0.0.1:8765/`，须先在评审电脑启动 |
| 使用手册 | `http://127.0.0.1:8765/manual.html` 或 [仓库手册](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/docs/08-user-manual.md) |

GitHub交付的是源码和证据，未提供公网托管应用。`localhost` / `127.0.0.1` 都指访问者自己的电脑，不会连接候选人的电脑。固定标签用于避免main后续变化影响评审；提交表应填写独立交付副本首页的完整SHA。

## 2. 访问权限、密钥与配置

| 场景 | 是否需要密钥 | 配置与说明 |
|---|---|---|
| 阅读/克隆公开仓库 | 不需要 | 无GitHub PAT、访问口令或解压密码 |
| 运行Mock及Python测试 | 不需要 | 无模型服务、无环境变量要求 |
| 本机真实Ollama模型 | 不需要 | `MODEL_BASE_URL=http://localhost:11434/v1`；`MODEL_NAME=qwen2.5:7b-instruct` |
| 访问本机工作台 | 不需要登录密码 | 默认仅本机；会话/CSRF令牌由页面自动获取，不是需分发的评审密钥 |
| 改用远端模型（可选） | 需要评审自己合法持有的Key | 通过环境变量`MODEL_API_KEY`注入；项目不提供共享商业Key，未验证任意供应商兼容性 |

**本交付包没有需另行领取的秘密密钥，也没有模型权重。** 真实模式需自行安装Ollama并下载模型。[环境变量模板](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/.env.example)只说明变量，应用不会自动读取`.env`；复制模板不等于完成配置。远端模型不要把Key写入仓库或提交文档。

题一远端需OpenAI兼容Chat Completions JSON对象输出；题二/题四需JSON Schema结构化输出。地址以`/v1`为基础，不附`/chat/completions`。工作台的本地默认值不意味着CLI可以省略真实模型变量。

## 3. 从零启动（Windows PowerShell）

安装Git及完整Python 3.10+。应用和Python测试只使用标准库，`requirements.txt`无第三方运行依赖；无需先装Node。以下命令从仓库根执行：

```powershell
git clone https://github.com/ttk-maker/campus-agent-q1-content-scheduling.git
cd campus-agent-q1-content-scheduling
git checkout q1-submission-20261107
git rev-parse HEAD
py -3.10 --version
py -3.10 -m unittest discover -s tests -v
py -3.10 -m src.web --port 8765 --db runtime/acceptance-web.db
```

保持服务终端开启，在浏览器访问 `http://127.0.0.1:8765/`。Linux/macOS把`py -3.10`替换为`python3`；安装Git/Python/可选Ollama依赖系统环境，本项目不捆绑这些程序。ZIP解压也可运行，ZIP没有`.git`时以交付包清单和完整SHA校验版本。

优先选择“离线演练”检查工程链路。默认演练可能是冲突或超长情形，未完成/待确认是设计内状态，不能只看按钮是否显示成功。

## 4. 最短CLI复现

```powershell
py -3.10 -m src.cli run --mode mock --request data/requests/conflict.json --db runtime/acceptance-cli.db --output runtime/acceptance-output.json --trace runtime/acceptance-trace.jsonl
```

预期：原定北京时间18:00占用，建议19:00；状态待确认，生效时间为空，草稿已保存且未发布。 输出为`runtime/acceptance-output.json`，每步记录为`runtime/acceptance-trace.jsonl`。使用新数据库进行全新演练；测试重复执行时必须保留数据库、原输入与request_id，不重新生成请求。

CLI退出码2表示失败或动作预算耗尽；待确认、资料不足、风险阻断等状态还需读取JSON。日期是合成演练固定值，历史排期证据不是实时业务日历；用于新业务时应同时调整请求和占用快照。

确认验收优先在网页点击明确的“确认改为…并重新审核”，确认后再次检查风险和占用；仅保存草稿，绝不能解释为已发布。

## 5. 真实模型复现

安装Ollama，启动其服务（桌面应用已运行则无需重复执行`ollama serve`）。首次模型下载需要网络与磁盘空间；7B模型CPU推理可能持续数分钟，硬件不足时会明确失败/超时，不会自动伪装成Mock。

```powershell
ollama pull qwen2.5:7b-instruct
ollama list
$env:MODEL_BASE_URL = 'http://localhost:11434/v1'
$env:MODEL_NAME = 'qwen2.5:7b-instruct'
py -3.10 -m src.cli run --mode real --request data/requests/conflict.json --db runtime/acceptance-real.db --output runtime/real-output.json --trace runtime/real-trace.jsonl
```

题二/题四先执行第4节make_request创建输入。网页选“真实模型”后运行；若改了环境变量，应从同一个已配置终端启动/重启Web服务。`http://localhost:11434/v1`只是模型API前缀，浏览器直接打开404不表示工作台损坏；工作台端口是8765。可用`ollama list`确认模型已安装。

真实模型输出不保证逐步复现历史Trace，验收应检查是否根据实际观察调整、是否保留硬约束以及结果真实一致。参考目标秒数或替代费用不是允许模型伪造的固定答案。无法运行真实模型时，可审核仓库既有真实记录，同时运行Mock验证工程链路；必须注明没有本次实时模型验证。

## 6. 考官逐项验收清单

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

建议操作顺序：正常场景 → 缺信息 → 工具失败 → 核心冲突/超限 → 重复执行 → 调整素材/占用/预算/秒数后重新运行。不同业务输入应生成新ID；故意测试重复必须保留原ID和原输入。结果、保存状态、账本/事实检查与Trace应相互一致。

真实动态决策直接入口：

- [正常动作记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/examples/real/normal/trace-1.jsonl)
- [冲突调整动作记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/examples/real/conflict/trace-1.jsonl)
- [保存失败动作记录](https://github.com/ttk-maker/campus-agent-q1-content-scheduling/blob/q1-submission-20261107/examples/real/save-failure/trace-1.jsonl)

每题已包含至少三组实际输入、输出和运行记录，覆盖正常、资料不足及工具失败；本表进一步覆盖全部必验。普通步骤失败不应被涂改成成功；达到上限必须明确未完成。

## 7. 自动验证与材料索引

```powershell
py -3.10 -m unittest discover -s tests -v
py -3.10 scripts/verify_examples.py --mode mock
py -3.10 scripts/verify_examples.py --mode real
```

证据校验器会读取留存结果并更新验收汇总文件，不重新调用模型；若需保持提交工作树完全不变，在另一个克隆/ZIP目录运行。全量Python预期69项通过。浏览器回归与显示测试的命令见README；需要Node.js22+和Playwright，非启动必需。最终CI覆盖Python3.10/3.12、原浏览器回归、展示与实时控件检查。

| 交付要求 | 仓库材料 |
|---|---|
| 环境/安装/运行/评审入口 | README.md |
| 项目代码与模型/工具 | src/ |
| 可执行测试 | tests/、scripts/ |
| 实际输入/输出/Trace | examples/ |
| 合成资料及规则 | data/ |
| 需求/方案/评估/AI使用/复盘 | docs/01-requirements.md 至 docs/05-retrospective.md |
| 本题两份交付文档 | docs/submission/01-design.md、02-delivery-and-acceptance.md |
| 依赖与变量 | requirements.txt、package.json/package-lock.json、.env.example |
| 干净归档检查与日志 | examples/submission/preflight.json、python-tests.txt、CLI及证据校验日志 |

旧失败证据保留，最新成功复测通过设计说明的验收映射定位。不要用截图替代代码或Trace，也不要把Mock报告当真实模型效果。压缩包只包含Git跟踪内容，不包含开发机数据库、虚拟环境、node_modules、真实.env或模型权重。

## 8. 常见问题与提交前确认

- 页面404：使用工作台根地址`http://127.0.0.1:8765/`，不要使用模型`/v1`前缀作为网页。
- 端口占用：启动时改为`--port 8781`，浏览器使用对应新端口。
- 模型不可用：确认Ollama服务、模型名称、变量所在终端；失败时保留错误，不声称真实决策通过。
- 修改输入后同ID被拒绝：生成新ID；同请求恢复/重复验收则保持原输入和数据库。
- 前端滑块改变但结果没变：输入预览不触发运行，需点击业务按钮；外观设置也不改写已执行结果。
- 评审异地打不开localhost：这是评审自己的电脑；先clone并启动，不需要候选人电脑的访问密钥。

提交表填写：题号1、公开GitHub URL和**最终完整commit SHA**。用户要求交付题1/2/4；官方最低范围是四选一，不应把“三题”表述为官方强制要求。公有仓库无需单独配置评审账号读权限。

本轮只整理交付、文档与检查证据；运行逻辑保持既有已验证版本。实际开发与AI辅助范围、未完成项见配套设计说明，不虚构个人独立实现或实时模型验证。
