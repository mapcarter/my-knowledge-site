---
title: STM32 DMA 笔记
tags: [embedded, stm32, dma]
---

# STM32 DMA 笔记

> [!WARNING]
> 配置 DMA 前务必确认外设时钟已开启，否则传输不会启动。

## 基本用法

直接存储器访问（DMA）可在无 CPU 干预下搬运数据：

```c
// 启动 UART 接收的 DMA 传输
HAL_UART_Receive_DMA(&huart1, rx_buf, BUF_LEN);
```

## 要点

1. 设置源地址、目标地址、数据长度；
2. 配置传输方向（外设↔内存）；
3. 开启传输完成中断。

公式为吞吐量估算：$T = \frac{L}{B \cdot f}$。
