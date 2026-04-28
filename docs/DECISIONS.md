# Design Decisions

This document captures key architectural and technical design decisions made for the ML Observability Platform, including the rationale and tradeoffs for each decision.

---

## Redis Streams over Kafka

**Problem:**
Need event streaming infrastructure for ML predictions that supports async processing, replay capabilities, and observability without excessive operational overhead.

**Decision:**
Use Redis Streams instead of Apache Kafka for event streaming.

**Rationale:**
Redis Streams provides sufficient event streaming capabilities for a demo/portfolio project with significantly lower operational complexity. It offers consumer groups, message persistence, and replay functionality while maintaining a lightweight footprint. The simpler deployment model (single Redis instance vs. Kafka cluster with Zookeeper) reduces infrastructure management burden and resource consumption.

**Tradeoffs:**
- Less scalable than Kafka for massive throughput (millions of events/second)
- Fewer ecosystem tools and integrations compared to Kafka
- Limited multi-datacenter replication capabilities
- Not ideal for long-term event retention at scale
- Smaller community and fewer enterprise features

**Date:** 2026-04-28

---

## Mean Shift → KS Test Approach

**Problem:**
Need to detect distribution drift in ML predictions efficiently while minimizing false positives and providing statistical confidence in drift detection.

**Decision:**
Implement a two-phase drift detection approach: mean shift detection followed by Kolmogorov-Smirnov (KS) test validation.

**Rationale:**
Mean shift detection provides fast, computationally efficient screening for obvious distribution changes by comparing recent prediction means against baseline. When mean shift is detected, the KS test validates whether the entire distribution has changed significantly, providing statistical rigor. This approach balances speed (mean shift) with accuracy (KS test), reducing false positives while catching genuine drift early.

**Tradeoffs:**
- More complex than single-metric approaches (e.g., only mean or only KS test)
- Requires maintaining baseline period data for comparison
- Two-phase approach adds latency to drift confirmation
- May miss subtle drift patterns that don't affect mean significantly
- Requires tuning two sets of thresholds (mean shift and KS p-value)

**Date:** 2026-04-28

---

## Podman over Docker

**Problem:**
Need container orchestration for local development and deployment with security, compatibility, and operational simplicity.

**Decision:**
Use Podman with podman-compose instead of Docker and Docker Compose.

**Rationale:**
Podman offers rootless container execution, eliminating the need for a privileged daemon and improving security posture. Its daemonless architecture reduces attack surface and resource overhead. Podman maintains Docker CLI compatibility, making migration straightforward, while providing better integration with systemd for production deployments. The rootless model aligns with security best practices and reduces permission-related issues.

**Tradeoffs:**
- Slightly less mature ecosystem compared to Docker
- Some Docker Compose features not fully supported in podman-compose
- Smaller community and fewer third-party tools
- Occasional compatibility issues with Docker-specific workflows
- Less documentation and fewer Stack Overflow answers

**Date:** 2026-04-28

---

## Event-Driven Architecture

**Problem:**
How to process and monitor ML predictions at scale while maintaining loose coupling between services and enabling observability features like replay and audit trails.

**Decision:**
Implement event-driven architecture using Redis Streams as the message backbone, with services consuming prediction events asynchronously.

**Rationale:**
Event-driven architecture naturally decouples services (data generator, inference API, drift detection, metrics collection), enabling independent scaling and deployment. Async processing prevents blocking on slow operations. Event streams provide natural audit trails and replay capabilities essential for ML observability. The pattern supports adding new consumers (e.g., data quality checks, model performance tracking) without modifying producers.

**Tradeoffs:**
- More complex than synchronous REST APIs
- Eventual consistency model requires careful handling
- Debugging distributed event flows is harder than request-response
- Requires stream management (retention, consumer offsets, dead letters)
- Higher operational complexity with multiple async services
- Potential for event ordering issues across partitions

**Date:** 2026-04-28

---

## PostgreSQL for Event Storage

**Problem:**
Need persistent storage for prediction events that supports complex queries, maintains data integrity, and handles semi-structured prediction data flexibly.

**Decision:**
Use PostgreSQL with JSONB columns for storing prediction events and drift detection results.

**Rationale:**
PostgreSQL provides ACID compliance ensuring data integrity for critical prediction records. JSONB support offers schema flexibility for varying prediction payloads while maintaining queryability through GIN indexes. Powerful SQL capabilities enable complex analytics queries for drift analysis and model performance tracking. Proven reliability and operational maturity reduce risk. Strong ecosystem support and tooling availability.

**Tradeoffs:**
- Heavier resource footprint than NoSQL databases for pure document storage
- Requires schema management and migrations
- Vertical scaling limitations compared to distributed NoSQL
- JSONB queries less performant than native document databases for deep nesting
- More complex backup/restore procedures than simpler key-value stores

**Date:** 2026-04-28

---

## Prometheus + Grafana Stack

**Problem:**
Need metrics collection, storage, and visualization for monitoring system health, prediction patterns, and drift detection with industry-standard tooling.

**Decision:**
Use Prometheus for metrics collection and storage, Grafana for dashboard visualization and alerting.

**Rationale:**
Prometheus provides industry-standard metrics collection with powerful PromQL query language, enabling complex aggregations and analysis. Pull-based model simplifies service discovery and reduces coupling. Grafana offers rich visualization capabilities with extensive panel types and dashboard templating. The stack is battle-tested, well-documented, and has strong community support. Native integration between Prometheus and Grafana provides seamless experience.

**Tradeoffs:**
- Pull model requires service discovery configuration and exposed metrics endpoints
- Limited long-term storage without additional components (Thanos, Cortex, VictoriaMetrics)
- Prometheus not designed for high-cardinality metrics (e.g., per-user tracking)
- Grafana alerting less sophisticated than dedicated alerting platforms
- Resource intensive for large-scale deployments
- Requires learning PromQL query language

**Date:** 2026-04-28

---

## Document Maintenance

This document should be updated whenever significant architectural or technical decisions are made. Each entry should include the problem context, decision made, rationale, and honest assessment of tradeoffs.