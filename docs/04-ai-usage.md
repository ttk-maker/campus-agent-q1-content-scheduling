# AI 辅助使用记录

本项目允许 AI 辅助。Codex 参与：规则梳理、需求分解、方案、原型图、代码、测试和文档；每项实际验证结果见评估文档与 examples/。

用户实际贡献：提供统一规则和题目，决定至少三题、争取四题；授权创建 public 仓库；选择本轮交付可导入 Figma 的图稿；指定优先使用已有模型环境变量。

尚无用户亲自修改代码或运行测试的记录，不将 AI 完成的工作写成用户独立实现。后续用户实际修改与验证继续追加。

原型交付调整：本会话没有 Figma 工具，经用户明确选择，本轮用 SVG 可导入图稿；不宣称已创建 Figma 在线文件。

用户后续要求先完成框架再筛选可用的开源模型 API 方案。助手核查官方接入条件并找到本机已有 Ollama/Qwen，使用本地免 Key 方式运行真实模型。没有让用户提交真实 Key。

助手实际执行：创建并推送 public 仓库、编写与运行自动化测试、生成离线和真实证据、发现并修复真实模型误解 existing 的问题。GitHub Actions 执行远端离线验证。这些属于 AI 辅助完成，不记为用户独立编码。

使用技能：planning-and-task-breakdown、git-workflow-and-versioning、api-and-interface-design、figma-generate-diagram（流程规范，图稿经用户改选 SVG）、OpenAI Docs（兼容接口格式核查）。

第二轮用户要求：按基础→边缘→困难开展冒烟、解决页面 404、联调前后端并提供手册。用户给出具体 404 URL http://localhost:11434/v1。助手复现其为 API 前缀而非网页，新增本地 Web 工作台；编写对抗边界测试，保留首次 9 项失败和 2 项错误，实施修复；执行 HTTP、真实浏览器及本地 Qwen 验证。新增辅助技能为 debugging-and-error-recovery、frontend-ui-engineering、browser-testing-with-devtools。没有将这些操作归因于用户亲自编写或测试。


## 2026-11-06 Tweaks 参考优化

用户提供 Open Design Tweaks 作为方向；AI 查看页面及公开示例，独立实现三工作台的显示控件、实时输入预览和布局，执行浏览器/HTTP验证并记录证据。后端与模型不变，原业务 JavaScript 保留为前缀；本轮不声称重新验证真实模型。参见 [设计与实际验证](11-live-tweaks.md)。
