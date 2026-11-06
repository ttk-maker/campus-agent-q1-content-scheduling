# 素材审核与发布排期：实时调参与结果画布

用户选择 [Open Design Tweaks](https://open-design.ai/plugins/example-tweaks/) 作为设计参考。本轮借鉴其浮动调参面板、CSS 变量、分段选项与本地偏好记忆，保留现有绿色品牌和四档字号，不复制示例营销内容或图片。

参考来源：[官方公开示例](https://github.com/nexu-io/open-design/tree/main/plugins/_official/examples/tweaks)，manifest 标注 MIT / 0.1.0；访问日期 2026-11-06。该链接是插件介绍页，交互结构进一步参照其公开 example.html。本项目控件与样式为根据业务重新编写，无新增 CDN、第三方运行时或外部字体。

## 实时调参工作台

1. 打开 http://127.0.0.1:8765/ 。桌面左侧查看输入预览和运行结果，右侧填写业务参数；窄屏先输入、后结果。
2. 调整执行步骤上限；素材、原定时间和改时确认边界实时预览。高级请求 JSON 为实际提交来源，批量预览列出全部素材并显示首项原定时间。
3. 拖动滑块或直接输入数值，只更新输入预览。点击原有运行按钮才执行 Agent；修改需求后仍须使用新请求编号。执行过程中快调滑块不可用。
4. 点击右上角“显示设置”，选择松绿 / 湖蓝 / 陶土 / 梅紫、浅色 / 深色、标准 / 大字、舒适 / 紧凑、关闭 / 轻微动效。设置即时生效，按 Esc 或“关闭”返回，焦点回到入口。
5. 显示偏好按项目保存在当前浏览器，刷新后恢复。“恢复默认显示”仅重置外观，不清空输入、请求编号、已保存任务或草稿。禁用存储时显示设置仍可临时生效。
6. 当前输入预览与上次运行结果分开：滑块改变不会重算费用、改动生效时间或刷新脚本检查。题二续跑、题四继续处理沿用原任务参数；新的需求应新建请求。

显示设置仅用于工作台，手册页面维持默认浅色。系统“减少动态效果”优先于轻微动效设置。每项目、每浏览器与每访问地址分别记忆偏好；localhost 与 127.0.0.1 是不同来源。

## 实现边界

HTML 保留原输入 ID 和表单；CSS 桌面布局为结果画布 + 参数侧栏，移动端输入在前。DOM 仍先输入后结果，保证键盘按任务顺序访问。原业务 app.js 完整保留为文件前缀，末尾独立闭包只管理外观、预览、原输入与 range 同步。严格 CSP 和静态文件白名单保持不变，不使用内联脚本或新增服务路由。

所有后端 src/*.py、模型提示、工具、持久化与业务 API 不变。证明文件 [baseline-integrity.json](../examples/tweaks/baseline-integrity.json) 保存本地原始摘要与跨平台 LF 摘要；新增浏览器检查同时验证原业务脚本前缀和后端摘要。LF 摘要只忽略 Git 配置引起的换行差异。

四向精简沿用 frontend-four-pass：精简说明、统一语义色、标准 14/16/20/32px 和大字 16/18/24/36px、统一 8px 圆角。普通卡片无阴影，浮层通过阴影与背景区分。状态保留文字，不靠颜色单独表达。

## 实际验证

- 新增显示和实时输入检查 **37 项通过**：[实际报告](../examples/tweaks/interaction/report.json)。验证主题持久化、重置隔离、坏 JSON / 非法配置 / 禁止存储、焦点/Esc、系统减少动效、八种主题语义对比度、空值/精度、滑块键盘与运行时禁用、调参零 API 写入、显式运行请求及已有结果不被外观改写。
- 原有浏览器业务检查 **19 项通过**：[证据目录](../examples/tweaks/browser/)。演练调用 Mock，不冒充真实模型验证。
- 既有展示检查 **35 项通过**：[报告](../examples/tweaks/presentation/report.json)。覆盖正常、失败/待确认、320/390px、200%文字放大及手册。
- HTTP 测试 **11 项通过**：[输出](../examples/tweaks/http-tests.txt)。
- [修改前截图](../examples/tweaks/before.png)、[新版结果画布](../examples/tweaks/interaction/success-desktop.png)、[深色设置](../examples/tweaks/interaction/settings-dark.png)、[320px 大字页面](../examples/tweaks/interaction/mobile-320.png)。

使用独立 runtime/tweaks-design.db 验证，未向用户 workbench.db 写入测试任务。既有历史例与真实模型记录未覆盖；本轮不重新执行真实模型推理。对比度检查针对实际列出的语义组合，不作为完整无障碍认证。

本地首次色彩检查暴露测试辅助函数只接受六位十六进制，而新增白色写为三位，导致比值 NaN；已统一 token 为六位后全部通过。启动原回归时首次未指定本机 Chrome，Playwright 的独立 Chromium 尚未安装；使用已有 Chrome 后正常执行，不是业务失败。

复现：在独立终端启动 `py -3.10 -m src.web --port 8766 --db runtime/tweaks-review.db`，另一终端设置 `PLAYWRIGHT_CHANNEL=chrome`（本机已有 Chrome）并执行 `node scripts/tweaks-review.cjs`。可通过 WEB_URL / TWEAKS_OUTPUT 覆盖地址与输出。依赖由 `npm ci` 安装；CI 使用已安装的 Chromium。

## 贡献与时间

用户提供参考模板和优化方向；AI 完成参考检查、实现、测试、文档与交付，未把这些记为用户独立编码。三项目共用本轮设计，2026-11-06 23:43（Asia/Shanghai）开始；本地实现验证于 23:56 左右完成，后续提交和 CI 时间在总交付记录中单列。
