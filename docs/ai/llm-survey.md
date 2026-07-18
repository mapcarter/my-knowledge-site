---
title: 大模型技术综述
tags: [ai, llm, survey]
---

# 大模型技术综述

> [!NOTE]
> 示例占位页，演示导航与链接。补充你自己的综述笔记即可。

## 主流架构

- 解码器-only（GPT 系列）
- 编码器-解码器（T5 系列）
- 混合专家（MoE）

## 训练范式

预训练 → 监督微调 → 人类反馈强化学习（RLHF）。

损失可写为交叉熵：

$$
\mathcal{L} = -\sum_{t} \log p_\theta(x_t \mid x_{<t})
$$
