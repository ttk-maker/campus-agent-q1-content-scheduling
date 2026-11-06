# 前端四向精简记录

2026-11-06，22:25（Asia/Shanghai）开始；使用 [frontend-four-pass Skill](skills/frontend-four-pass/SKILL.md)。用户授权三个项目前端优化，历史冻结标签/备份保留。后端与大模型逻辑不变。

## 题一：素材审核与排期

| 方向 | 实际改动 |
| --- | --- |
| 文案 | 页标题直接命名审核与排期；删去提交区重复说明与空状态流程图。保留仅保存草稿、改时确认、时区和请求编号规则。 |
| 配色 | 沿用深绿品牌；背景、正文、辅助文字、控件边框、主操作、成功、警告、错误统一语义变量。状态仍带文字。 |
| 字号 | 原首页可见文字有 11 种字号，现为14/16/20/32px四档。正文与表单16px、辅助及JSON14px、区块及指标20px、页标题32px。 |
| 装饰 | 普通卡片、输入和按钮统一8px圆角；删除空状态装饰箭头、无状态意义的左色条和重复容器。普通卡片无阴影。 |

结构调整：状态播报移到提交按钮附近，错误不隐藏；请求编号仍可直接操作。日期时间独占一行；草稿表格在窄屏局部横滚且可键盘聚焦。

没有引入新品牌或Radix依赖。保留现有绿色方向，按角色整理颜色。正文对比度检查最低5.28:1；必要控件边界与焦点组合最低3.40:1。此结果针对已测token组合，不宣称完整WCAG认证。

## 验证

- [原有浏览器回归](../examples/ui-refinement/browser/report.json)：19项通过，包含实际业务交互。使用隔离测试库，未改用户业务数据。
- [展示检查](../examples/ui-refinement/presentation/report.json)：35项通过；空、成功、待确认/未完成状态，320/390px窄屏、720px下200%字号放大、键盘跳转及焦点、手册、控制台与HTTP错误。
- [范围核查](../examples/ui-refinement/scope-check.json)：8个受保护文件摘要一致，含全部src/*.py和web/app.js；对照基线 `4b7be35e73a166ab5ec6d154caac30ae7083b6ce`。API参数、事件、确认、续跑、下载、模型Prompt与业务状态均未修改。
- [改动前](../examples/ui-refinement/before/desktop.png) / [改动后](../examples/ui-refinement/after/desktop.png)，[完成态](../examples/ui-refinement/presentation/success-desktop.png)，[窄屏状态](../examples/ui-refinement/presentation/attention-390.png)。

本轮浏览器回归使用Mock/确定性工具，验证展示与交互；没有重新运行真实模型评估，也没有把视觉检查算作模型效果提升。既有真实决策证据仍保留。用户提出四个方向与业务不变约束；代码、Skill及验证由AI辅助完成，不计为用户独立编码。

## 复现

```powershell
py -3.10 -m src.web --port 8766 --db runtime/ui-review.db
# 另一个终端；已安装Node及项目Playwright依赖
node scripts/ui-review.cjs
```

默认使用Chrome；CI通过PLAYWRIGHT_CHANNEL=chromium选择Chromium。WEB_URL可替换服务地址，UI_OUTPUT可替换输出目录。200%检查放大CSS文字变量，不等于对所有浏览器原生缩放/读屏软件做全面认证。

题一首轮浏览器回归仅因手册标题由“一步步”改为“使用手册”触发旧文案断言，改为匹配新标题后19项全过。产品逻辑没有因此修改。

本地HTTP回归也已通过（题一11项，题二12项，题四12项，详见examples/ui-refinement/http-tests.txt）。本轮只改展示，未重复真实模型推理；发布时CI会执行仓库原有完整回归。
