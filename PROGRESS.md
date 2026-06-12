# Progress

## 2026-06-12

### 问题排查
- TL;DR 仅显示 "Harness"，Key Takeaways 为空或碎片

### 根因分析

1. **`_strip_non_latin_tail` 破坏中文内容**（`providers/base.py`）
   - 该函数设计用于去除英文中追加的 CJK 拒绝/注入文本
   - 但 `digest_language=zh` 时，整个返回内容都是中文，函数找到最早 CJK 块后直接截断到只剩 "Harness"
   - 修复：只在文本末尾 30% 范围内的 CJK 块才截断

2. **max_tokens 硬编码不可配置**
   - 之前 `openai_provider.py` `_chat` 默认 4096，不可调
   - 现已做成 config.yaml 可配：`llm.openai_max_tokens` / `llm.ollama_num_predict`

### 改动
- `config.py`: `LlmConfig` 新增 `openai_max_tokens` (default 4096) 和 `ollama_num_predict` (default 4096)
- `providers/base.py`: `_strip_non_latin_tail` 只处理末尾 30% 的 CJK 块
- `providers/openai_provider.py`: 接受 `max_tokens` 参数并使用
- `providers/ollama_provider.py`: 接受 `num_predict` 参数并使用
- `providers/factory.py`: 从 config 传入参数
