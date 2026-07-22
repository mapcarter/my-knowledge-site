---
title: DCRNN 笔记
tags: [traffic, gnn, dcrnn]
---

# DCRNN 笔记

> [!TIP]
> 扩散卷积循环神经网络（DCRNN）把交通路网建模为有向图。

## 模型结构

- 用图扩散卷积捕捉空间依赖；
- 用编码器-解码器结构捕捉时间依赖。

损失函数常用 MAE：

$$
\mathcal{L} = \frac{1}{N}\sum_{i=1}^{N}\left|\hat{y}_i - y_i\right|
$$

## 代码片段

```python
import torch
import torch.nn as nn

class DCRNNCell(nn.Module):
    def __init__(self, hidden_size: int):
        super().__init__()
        self.hidden_size = hidden_size
        self.linear = nn.Linear(hidden_size * 2, hidden_size)
```

## 结论

在多个公开数据集上，DCRNN 相比传统方法显著降低预测误差。
