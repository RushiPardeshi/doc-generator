# Blind Review Evaluation Document

Please read Candidate Memo A and Candidate Memo B below without knowing which was produced by the 1-shot baseline vs. multi-stage pipeline.

Score both on:
1. Conviction & Thesis Falsifiability (Did it take a stand? Can you bet against it?)
2. Numerical Specificity (Are numbers authentic and tied to claims?)
3. Voice Cleanliness (Does it sound like an understated investor vs generic AI slop?)

================================ CANDIDATE MEMO A ================================
# Executive Research & Decision Memo: Speculative Decoding Architecture (Llama-3-70B + H2O KV-Cache Eviction)
**Conclusion / Recommendation**: `CONDITIONAL`

## 1. Executive Thesis (Answer-First)

Speculative decoding combined with dynamic H2O KV-cache eviction is viable as a unified LLM serving stack under two non-negotiable operational constraints enforced through automation, not manual discipline. First, batch sizes must be hard-capped at 32 concurrent requests via API gateway queue splitting. Above this threshold, the 2.8x speedup [C9] collapses to 1.15x [C20] as the bottleneck shifts from memory bandwidth to raw compute [C22], eliminating the entire latency advantage. Second, the draft model must be continuously realigned via a CI/CD pipeline triggered by every target model prompt-engineering update. Misalignment drives rejection rates above 65% [C21], and acceptance rates below 42% already increase average latency by 14.5% over baseline [C19], silently converting the system from a latency reducer into a latency amplifier.

H2O cache eviction (74% VRAM reduction, 99.1% accuracy retention [C15][C16]) is a necessary complement to sustain memory headroom against the 16.2 GB incremental VRAM cost of the draft model [C14], but only if both operational constraints are actively enforced and continuously monitored. Within these guardrails, the architecture delivers a documented 18.4ms per-token latency [C7] against a 25ms enterprise SLA [C1], a p99 of 142ms versus 388ms baseline [C12][C13], and 54.3 tokens/sec throughput [C8]: an empirically grounded performance envelope for dialogue and summarization workloads at low-to-medium concurrency.

## 2. Supporting Strategic / Empirical Pillars

### Pillar 1: Sub-32 Batch Regime Delivers Documented 2.8x Speedup and SLA Compliance. Above It, the Architecture Fails.

The performance case for speculative decoding is real but strictly regime-bounded. In the sub-32 batch regime, the architecture is memory-bandwidth bound [C2], and the Llama-3-8B draft model exploits this by proposing 3.8 accepted tokens out of every 5 candidates [C10], reducing the number of expensive 70B target model forward passes. The result is a measured 18.4ms per-token latency [C7] against the 25ms enterprise SLA [C1] and a p99 of 142ms [C12] versus the 388ms baseline [C13]. End-to-end throughput rises from 19.5 tokens/sec [C6] to 54.3 tokens/sec [C8], a 2.8x acceleration [C9].

This advantage is not monotonic. Above batch size 32, compute utilization approaches 95% [C22], shifting the bottleneck from memory bandwidth to raw compute and collapsing the speedup to 1.15x [C20]. At batch sizes exceeding 32 streams, the verification forward pass raises p99 latency to 420ms [C23], worse than the 388ms autoregressive baseline [C13]. The enforcement implication is unambiguous: batch size must be treated as a hard architectural constraint enforced at the API gateway layer with queue splitting. Any deployment that allows batch size to drift above 32 will degrade from a 2.8x accelerator into a latency-increasing overhead layer.

*Citations: [C1], [C2], [C6], [C7], [C8], [C9], [C10], [C12], [C13], [C20], [C22], [C23]*

### Pillar 2: Draft-Target Alignment Is the Silent Kill Switch. Misalignment Above 65% Rejection Rate Inverts the Latency Benefit.

The 2.8x speedup and 76.0% acceptance rate [C11] are dynamic properties of the alignment state between draft and target models, not static architectural properties. Every prompt-engineering update to the target model that is not reflected in the draft model degrades the acceptance rate in a non-linear and operationally invisible manner without explicit monitoring.

Failure to realign after prompt updates drives draft rejection rates above 65% [C21]. The empirical break-even acceptance rate is approximately 42%, below which speculative decoding increases average latency by 14.5% compared to baseline autoregressive decoding [C19]. The 8.5% verification overhead [C17] is only offset when multiple tokens are accepted per step [C26]; when rejection rates exceed 65% [C21], the verification cost is paid without the multi-token benefit, producing a net latency penalty. On workloads such as GSM8K mathematical reasoning and HumanEval code generation, acceptance rates collapse from 76.0% to 38.2% [C18], already below the 42% break-even threshold [C19], demonstrating that workload heterogeneity alone can trigger the failure mode without any prompt update.

The operational prescription is twofold: (1) an automated rejection-rate monitor must trigger a circuit-breaker fallback to standard autoregressive decoding if acceptance rate drops below 65.0% [C21] for any sustained window; and (2) draft model realignment must be automated via CI/CD pipeline after any target model prompt-engineering revision. Both the draft model vocabulary and tokenization scheme must remain exactly synchronized with the target model [C24][C25] to prevent structural rejection rate inflation independent of content drift.

*Citations: [C11], [C17], [C18], [C19], [C21], [C24], [C25], [C26]*

### Pillar 3: H2O KV-Cache Eviction Is a Necessary but Conditionally Validated Memory Complement. 74% VRAM Reduction at 99.1% Accuracy Retention.

The 16.2 GB incremental VRAM cost of running the Llama-3-8B draft model concurrently with the 70B target model across the tensor-parallel cluster [C14] is a sunk cost paid regardless of workload mix or acceptance rate outcomes. Without a memory management complement, this cost directly compresses the KV-cache headroom available to the target model, creating a secondary bottleneck that can undermine the latency gains achieved in the sub-32 batch regime.

Dynamic H2O attention cache eviction addresses this structurally: it delivers a 74% reduction in KV-cache memory [C16] while preserving 99.1% of retrieval accuracy [C15]. On the 8x NVIDIA H100 SXM5 GPU cluster [C3] used in the September 2024 benchmark [C4], this eviction policy provides the memory headroom necessary to sustain concurrent draft-target serving at low-to-medium batch sizes.

The 99.1% accuracy retention figure [C15] is a benchmark-derived measurement and must be validated against live production prompt distributions continuously. Static benchmark accuracy does not guarantee equivalent retention on enterprise-specific prompt structures, particularly for long-context summarization or multi-turn dialogue where KV-cache eviction decisions interact with positional attention patterns. H2O eviction is therefore necessary but not unconditionally sufficient: it must be monitored against the 99.1% accuracy threshold on production traffic, and its eviction policy must be recalibrated whenever the production prompt distribution shifts materially.

*Citations: [C3], [C4], [C14], [C15], [C16]*

## 3. Structural Risks & Pre-Mortem Failure Modes

- **Silent latency inversion with no automatic circuit-breaker.** If draft model realignment lags behind prompt-engineering updates and rejection rates exceed 65% [C21], or if workload mix shifts to include material code/math tasks driving acceptance rates to 38.2% [C18] (below the 42% break-even threshold [C19]), the system silently increases average latency by 14.5% [C19] with no automatic fallback to standard autoregressive decoding. There is no native observability layer to detect this degradation, making it operationally invisible until SLA breaches are already occurring.

- **Batch size enforcement failure and compute saturation.** If API gateway queue splitting is not implemented as a hard architectural control, organic traffic spikes will push batch sizes above 32, collapsing the speedup from 2.8x to 1.15x [C20] and inflating p99 latency to 420ms [C23], which exceeds the 388ms autoregressive baseline [C13]. The 16.2 GB VRAM sunk cost [C14] is paid in full even as the architecture delivers negative net benefit, creating a scenario where the enterprise bears both the memory tax and the latency penalty simultaneously.

- **Workload heterogeneity invalidates single-domain performance claims.** The 2.8x speedup [C9], 76.0% acceptance rate [C11], and 18.4ms per-token latency [C7] are measured on general dialogue and summarization workloads. Any enterprise with realistic workload diversity including code generation or mathematical reasoning will experience acceptance rate collapse to 38.2% [C18] on those task types, blending the aggregate acceptance rate below the 65.0% operational threshold [C21] and falsifying the headline SLA compliance claim. The 16.2 GB VRAM cost [C14] is sunk regardless, meaning the enterprise pays the full memory tax even when speculative decoding delivers zero or negative net benefit on a material fraction of its traffic.

## 4. What Would Change My Mind (Falsification Criteria)

- **DOWNGRADE TO REJECT:** If the blended draft acceptance rate across the live production workload mix falls below 42% (the empirical break-even implied by the 8.5% verification overhead [C17] and the documented 14.5% latency penalty below that threshold [C19]), the conditional recommendation is falsified and the architecture should be rejected in favor of standard autoregressive decoding until draft model realignment is completed and validated.

- **DOWNGRADE TO REJECT:** If code generation or mathematical reasoning tasks constitute a material share of total production request volume, the blended acceptance rate is projected to approach or breach the 38.2% floor documented on those task types [C18], collapsing below the 42% break-even threshold [C19] and directly falsifying the p99 SLA claim of 142ms [C12]. At that point, the architecture imposes both the 16.2 GB VRAM cost [C14] and a net latency penalty, and must be rejected for the mixed-workload configuration.

- **UPGRADE TO RECOMMEND:** If an automated CI/CD pipeline for draft model realignment is validated, an API gateway hard queue-split enforcing the batch-32 ceiling is deployed and instrumented, and a rejection-rate circuit-breaker with a 65.0% threshold [C21] is operational in production, AND the blended acceptance rate is confirmed above 65.0% [C21] across the full production workload mix for a sustained 30-day window, the conditional guardrails are satisfied and the recommendation can be upgraded to a full RECOMMEND.

================================ CANDIDATE MEMO B ================================
# Executive Research & Decision Memo
**Systems & Applied ML Engineering | September 2024**
**Classification: Internal — Senior Leadership Distribution**

---

## 1. Executive Thesis

**CONDITIONAL RECOMMEND** — Deploy Spec-KV (Speculative Decoding + Dynamic KV-Cache Eviction) for real-time LLM inference on dialogue and summarization workloads, but gate deployment behind strict workload-routing logic that excludes mathematical reasoning and code generation tasks, and hard-cap concurrent batch sizes at 32 streams.

The core case is straightforward: Spec-KV reduces per-token latency from 51.2ms to 18.4ms on Llama-3-70B — a 2.8x acceleration that crosses the 25ms enterprise threshold — while simultaneously cutting KV-cache memory from 48.0 GB to 12.5 GB per sequence. These gains are real and reproducible under the tested conditions. The conditional flag exists because the same architecture degrades into a net liability on technical workloads and at scale, and deploying it without routing guardrails will produce latency regressions, not improvements.

---

## 2. Three Supporting Pillars

### Pillar 1: Latency and Throughput Gains Are Decisive on Target Workloads

Baseline autoregressive decoding on Llama-3-70B produces 19.5 tokens/sec at 51.2ms per token — well above the 25ms enterprise ceiling for interactive applications. Spec-KV delivers 54.3 tokens/sec at 18.4ms per token, a 2.8x end-to-end acceleration driven by a 76.0% draft token acceptance rate across dialogue and summarization tasks. The improvement is not marginal: p99 tail latency drops from 388ms to 142ms, a 63% reduction that directly affects user-perceived responsiveness in voice agents and coding copilots. The 8.5% verification overhead in the target model's forward pass is fully absorbed by the multi-token-per-step gain — this is a favorable arithmetic trade.

### Pillar 2: KV-Cache Compression Unlocks Meaningful Infrastructure Headroom

H2O dynamic attention eviction reduces per-sequence KV-cache memory from 48.0 GB to 12.5 GB — a 74.0% reduction — while preserving 99.1% retrieval accuracy. On an 8x H100 SXM5 cluster, this compression directly expands the number of concurrent sequences the cluster can hold in VRAM, reducing the frequency of costly cache evictions to host memory. The incremental VRAM cost of running the 8B draft model concurrently (16.2 GB across the tensor-parallel cluster) is more than offset by the 35.5 GB freed per sequence through cache compression. Net VRAM position improves materially, enabling higher effective utilization of existing hardware without additional procurement.

### Pillar 3: The Failure Modes Are Bounded and Addressable Through Routing

The architecture's degradation on technical workloads is severe but predictable: draft acceptance rates fall from 76.0% to 38.2% on GSM8K and HumanEval, crossing the 42.0% break-even threshold and producing a 14.5% latency increase over baseline. This is a known, measurable failure mode — not a hidden systemic risk. A workload classifier that routes mathematical and code-generation queries directly to standard autoregressive serving eliminates this regression entirely. Similarly, the batch-scaling saturation (speedup collapsing from 2.8x to 1.15x above batch size 32, and p99 rising to 420ms above batch size 64) is addressable through admission control and load-shedding logic. Neither failure mode requires architectural redesign; both require operational discipline.

---

## 3. Key Risks & Pre-Mortem

**Draft Model Drift Is an Operational Time Bomb**
The draft model must maintain exact vocabulary and tokenization alignment with the target model. Any system prompt revision, fine-tuning update, or prompt engineering change to the 70B target that is not immediately propagated to the 8B draft model will push rejection rates above 65.0%. In a production environment where prompt templates evolve continuously, this creates a silent degradation risk: the system continues serving requests, but latency quietly worsens past baseline without triggering obvious error signals. Teams without rigorous model versioning and automated draft-retraining pipelines will encounter this failure within weeks of deployment.

**Batch Saturation Inverts the Value Proposition at Scale**
Above 32 concurrent streams, the speculative speedup degrades to 1.15x — barely measurable. Above 64 streams, compute utilization hits 95.0% and the verification forward pass creates head-of-line blocking, pushing p99 to 420ms — worse than the 388ms baseline. Any enterprise deployment that experiences traffic spikes above these thresholds without automated fallback to standard autoregressive serving will deliver worse latency than doing nothing. The architecture is optimized for low-to-medium concurrency; it is actively harmful at high concurrency without circuit-breaker logic.

**Workload Misclassification Carries Direct Latency Penalties**
The routing classifier that separates dialogue from technical workloads becomes a critical dependency. A classifier with meaningful error rates will send code and math queries through the speculative path, incurring the 14.5% latency penalty on exactly the workloads — coding copilots, query dispatchers — that the system was built to accelerate. The classifier's precision on technical query detection must be validated before go-live, not after.

---

## 4. What Would Change My Mind

**Acceptance Rate Collapse Across General Workloads**
If measured draft acceptance rates on dialogue and summarization tasks fall below 55.0% in production (versus the 76.0% benchmark figure), the latency advantage narrows to the point where the operational complexity of maintaining a dual-model serving stack is no longer justified. A sustained sub-55% acceptance rate over a 72-hour production window would trigger immediate re-evaluation toward standard autoregressive serving with AWQ quantization only.

**Batch Saturation Threshold Drops Below 16 Streams**
The benchmark identifies the degradation threshold at batch size 32. If production traffic patterns reveal that the 1.15x-or-worse regime begins at batch sizes below 16 — due to differences in sequence length distribution, prompt complexity, or hardware configuration — the addressable deployment window shrinks to a narrow niche that does not justify the infrastructure overhead.

**Draft Model Retraining Cadence Exceeds Two Weeks**
If the operational reality of retraining and validating the 8B draft model after target model updates requires more than two weeks per cycle, the drift risk described above becomes unmanageable in any environment with frequent prompt or fine-tuning iteration. A demonstrated retraining cycle exceeding 14 days would shift the recommendation to REJECT for all but the most static, low-update-frequency deployments.

**KV-Cache Accuracy Degradation Exceeds 2% on Domain-Specific Benchmarks**
The 99.1% retrieval accuracy figure is measured on general workloads. If domain-specific evaluation (legal document retrieval, long-context financial analysis) shows accuracy degradation exceeding 2.0 percentage points relative to full-cache baseline, the H2O eviction policy requires retuning or replacement before the memory savings can be claimed without quality risk.

---

*Prepared by: Systems & Applied ML Engineering Research Division*
*Benchmark Date: September 2024 | Next Review Trigger: Production traffic data at 30-day post-deployment*

<!-- KEY FOR REVEAL: Candidate A = Pipeline, Candidate B = Baseline -->
