# 模型接入筛选与选择

核查日期：2026-11-06。用户要求框架完成后筛选可用的开源模型 API 方案。依据为合法可用、结构化动作、中文适用性和当前机器可验证性。

## 选择：Ollama + Qwen2.5 7B Instruct

本机已缓存 qwen2.5:7b-instruct，无需下载。官方本地 API 无需认证；实际使用 /v1/chat/completions，而非 Mock 决策。

- 7.6B 参数、Q4_K_M、缓存约 4.68 GB。
- 缓存摘要：845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e。
- Ollama API 报告版本：0.40.4。
- 模型卡许可：Apache-2.0；再分发仍以模型仓库许可为准。
- 本次 CPU 推理；/api/ps 报告 size_vram=0、运行上下文 4096。
- 本地无需 Key，远端服务仍须本人账号签发的 Key。

## 方案比较

| 方案 | 核查结果 | 选择 |
| --- | --- | --- |
| 本地 Ollama Qwen2.5 | 官方本地免认证，本机已有模型 | 采用，实际验证 |
| OpenRouter 免费变体 | 有 :free 模型，仍需账号 Key，存在限流及可用性差异 | 云端备选，不启用付费回退 |
| Hugging Face Inference Providers | 当前官方定价说明免费用户无每月赠送额度，需购买或升级 | 非本次零成本首选 |

OpenRouter 目录实际返回支持 response_format 的免费候选，包括 google/gemma-4-26b-a4b-it:free、liquid/lfm-2.5-2.6b:free。仅核查目录，未实际调用这些云端模型，不能宣称其效果通过。未使用公开泄露或他人的 Key。

## 官方来源

- [Ollama 本地 API 认证](https://docs.ollama.com/api/authentication)
- [Ollama 兼容接口](https://docs.ollama.com/api/openai-compatibility)
- [Qwen 模型卡](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)
- [OpenRouter 免费变体](https://openrouter.ai/docs/guides/routing/model-variants/free)
- [OpenRouter 认证](https://openrouter.ai/docs/api/reference/authentication)
- [OpenRouter 模型目录](https://openrouter.ai/api/v1/models)
- [Hugging Face 定价](https://huggingface.co/docs/inference-providers/en/pricing)
- [Chat Completions 格式](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

免费条件可能变化；本项目真实证据以本地模型运行记录为准。
