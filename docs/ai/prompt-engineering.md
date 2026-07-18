---
title: Prompt 工程入门
tags: [ai, prompt, llm]
---

# Prompt 工程入门

> [!NOTE]
> 本文为示例笔记，用于演示字体、公式与代码高亮的渲染效果。

## 核心原则

编写提示词时遵循 **清晰、具体、给示例** 三原则。下面是一个温度参数控制的例子：

```python
def build_prompt(question: str, temperature: float = 0.7) -> str:
    return f"请以严谨的学术口吻回答：{question}（temperature={temperature}）"
```

## 一个公式

注意力机制的计算可写为：

$$
\text{Attention}(Q,K,V) = \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V
$$

行内公式如 $E=mc^2$ 也能正常渲染。

## 小结

| 技巧 | 说明 |
|---|---|
| 少样本 | 提供输入-输出示例 |
| 思维链 | 引导逐步推理 |
| 角色设定 | 指定模型身份 |
