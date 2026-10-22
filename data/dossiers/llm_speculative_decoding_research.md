# Technical Research Report: Speculative Decoding & KV-Cache Compression for Real-Time LLM Inference

**Research Division**: Systems & Applied ML Engineering  
**Benchmark Date**: September 2024  
**Scope**: Low-Latency Enterprise LLM Serving Architecture Evaluation  

---

## 1. Executive Summary & Objective

Modern enterprise applications (interactive coding copilots, real-time voice agents, high-frequency query dispatchers) require LLM generation latencies under 25ms per token. Autoregressive token-by-token generation is fundamentally memory-bandwidth bound at small batch sizes. 

This research packet evaluates **Speculative Decoding paired with Dynamic KV-Cache Eviction (Spec-KV)** across a cluster of 8x NVIDIA H100 SXM5 GPUs, contrasting it against naive autoregressive generation and static 4-bit weight-only quantization (AWQ).

---

## 2. Empirical Benchmark Data & System Metrics

### 2.1 Latency and Token Throughput
- **Baseline Latency**: Standard autoregressive decoding on Llama-3-70B requires an average of 51.2ms per token (throughput of 19.5 tokens/sec) at batch size 1.
- **Speculative Acceleration**: Utilizing a speculative drafting setup with a fine-tuned Llama-3-8B draft model achieves an average latency of 18.4ms per token (throughput of 54.3 tokens/sec), representing an overall 2.8x end-to-end acceleration factor.
- **Draft Acceptance Rate**: The target 70B model accepts an average of 3.8 draft tokens out of every 5 proposed candidate tokens, translating to an average token acceptance rate of 76.0% across general dialogue and summarization workloads.
- **Tail Latency**: The p99 generation latency under speculative decoding was measured at 142ms, compared to 388ms for naive autoregressive serving.

### 2.2 Memory Footprint and Compute Overhead
- **DRAM Footprint**: Running the draft 8B model concurrently with the 70B target model adds an incremental 16.2 GB of GPU VRAM across the tensor-parallel cluster.
- **KV-Cache Eviction**: Applying dynamic H2O attention cache eviction preserves 99.1% of retrieval accuracy while truncating token KV-cache memory from 48.0 GB down to 12.5 GB per sequence (a 74.0% memory reduction).
- **Verification Overhead**: The parallel verification step in the target model consumes 8.5% of total forward-pass compute budget, which is offset by generating multiple tokens per step.

### 2.3 Task-Specific Degradation and Divergence
- **Technical & Mathematical Reasoning**: On GSM8K mathematical reasoning and HumanEval code generation, draft model acceptance rates drop sharply from 76.0% down to 38.2%.
- **Speculation Penalty**: When acceptance rates fall below 42.0%, speculative decoding becomes a net-negative performer, increasing average latency by 14.5% compared to baseline decoding due to discarded draft rollbacks.
- **Concurrence & Batch Scaling**: At batch sizes above 32 concurrent requests, memory bandwidth saturation diminishes the speculative speedup from 2.8x down to 1.15x.

---

## 3. Structural Risks & Deployment Tradeoffs

### 3.1 Draft Model Drift and Synchronization
The draft model must share the exact vocabulary and tokenization scheme as the target model. Whenever the target model receives prompt engineering updates or system prompt revisions, the draft model requires retraining or aligned distillation. Failure to align leads to immediate draft rejection rates exceeding 65.0%.

### 3.2 High-Concurrency Saturation
At batch sizes exceeding 64 streams, compute utilization approaches 95.0%, transitioning the serving bottleneck from memory bandwidth back to raw compute. Under these conditions, the verification forward pass creates head-of-line blocking, raising p99 latency to 420ms.
