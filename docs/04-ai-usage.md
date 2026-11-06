# AI 辅助使用记录

本项目允许 AI 辅助。Codex 参与：规则梳理、需求分解、方案、原型图、代码、测试和文档；每项实际验证结果见评估文档与 examples/。

用户实际贡献：提供统一规则和题目，决定至少三题、争取四题；授权创建 public 仓库；选择本轮交付可导入 Figma 的图稿；指定优先使用已有模型环境变量。

尚无用户亲自修改代码或运行测试的记录，不将 AI 完成的工作写成用户独立实现。后续用户实际修改与验证继续追加。

原型交付调整：本会话没有 Figma 工具，经用户明确选择，本轮用 SVG 可导入图稿；不宣称已创建 Figma 在线文件。

用户后续要求先完成框架再筛选可用的开源模型 API 方案。助手核查官方接入条件并找到本机已有 Ollama/Qwen，使用本地免 Key 方式运行真实模型。没有让用户提交真实 Key。

助手实际执行：创建并推送 public 仓库、编写与运行自动化测试、生成离线和真实证据、发现并修复真实模型误解 existing 的问题。GitHub Actions 执行远端离线验证。这些属于 AI 辅助完成，不记为用户独立编码。

使用技能：planning-and-task-breakdown、git-workflow-and-versioning、api-and-interface-design、figma-generate-diagram（流程规范，图稿经用户改选 SVG）、OpenAI Docs（兼容接口格式核查）。
