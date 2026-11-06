# 第一轮真实模型失败记录（部分运行，非最终验收）

模型：Ollama qwen2.5:7b-instruct；代码基线：699962d34437869799ef7ea5446209288efc82c5。

真实批次执行至补查场景时中止，以修复已经发现的模型决策失败；该目录不构成完整场景集，没有完整 manifest。

观察：conflict 场景模型先误选被占用的原始时间，被 available_candidate_required 拒绝后重新查询并恢复。duplicate 第二次运行虽成功获得 existing，却再次调用保存并试图使用不支持的 pending 终态，最后结束为 failed。实际数据库仍只有一份 pending_confirmation 草稿，没有越权发布或伪报保存成功。

修复：候选时间使用用户原时区呈现以减少换算歧义；明确 existing 与 saved 都代表草稿操作成功；工具观察增加 save_succeeded、operation_complete 和 user_confirmation_required，区分操作完成与业务确认。仍由模型选择下一步，授权与持久化守卫不放宽。最终重跑证据放 examples/real/。
