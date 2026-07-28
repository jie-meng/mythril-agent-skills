# Cross-Functional Requirements (CFR) Estimation Guide

Functional stories tell you **what** to build. CFR tells you **how well** it needs to work.
CFR items are frequently overlooked in user-story-only requirements but can dominate actual
development effort — especially for systems with high reliability, security, or scale demands.

---

## CFR Assessment Framework

For each CFR area, answer three questions:
1. **Does it apply?** — Not every project needs every CFR area.
2. **What's the maturity target?** — Startup MVP vs enterprise production vs regulated industry.
3. **What's the delta from current state?** — If the team already has a mature CI/CD pipeline, the CFR estimate is close to zero. If they have nothing, it's significant.

---

## 1. Infrastructure & DevOps

### Probes
- Is there an existing CI/CD pipeline, or does one need to be built from scratch?
- How many environments (dev, staging, prod, DR)? Are they consistent?
- Infrastructure-as-Code (Terraform, Pulumi, CloudFormation) — exists or needs creation?
- Container orchestration (K8s, ECS, Nomad) or serverless?
- Secrets management — Vault, AWS Secrets Manager, or env vars?
- Networking: VPC design, subnets, NAT gateways, service mesh, API gateway?
- SSL/TLS certificate provisioning and rotation?

### Typical Point Ranges
| Maturity Level | Points | What's Included |
|---|---|---|
| **None → Basic** | 8–20 | CI/CD for one service, single environment, manual secrets, basic Docker |
| **Basic → Standard** | 13–40 | Multi-environment CI/CD, IaC for all resources, automated secrets, container orchestration, monitoring integration |
| **Standard → Enterprise** | 20–60 | Multi-region, auto-scaling, service mesh, GitOps, compliance automation, self-service developer platform |
| **Ongoing (per sprint)** | 2–5 | Pipeline maintenance, dependency updates, cost optimization |

### Common Omissions
- **Environment parity**: Dev != staging != prod → bugs found late. Treat environment setup as CFR, not afterthought.
- **Developer onboarding**: Time-to-first-commit. If >1 day, infrastructure is a bottleneck.
- **Rollback automation**: Can you roll back a deployment with one click? If not, budget for it.
- **Database migrations**: Are they part of the CI/CD pipeline or manual? Automated, tested, rollback-able migrations cost more upfront.

---

## 2. Security

### Probes
- Authentication mechanism? (OAuth2, SAML, JWT, API keys, mTLS)
- Authorization model? (RBAC, ABAC, ReBAC, custom policy engine)
- Data encryption at rest AND in transit — which data? Which algorithms?
- Multi-tenancy: How is tenant data isolated? (DB-per-tenant, schema-per-tenant, row-level, shared)
- Secrets: API keys, DB passwords, third-party tokens — how are they stored and rotated?
- Threat modeling done? Penetration testing budgeted?
- Compliance: SOC2, HIPAA, PCI-DSS, GDPR, ISO 27001?
- Dependency scanning, SAST, DAST in CI/CD?
- Audit logging for all state-changing operations?

### Typical Point Ranges
| Scope | Points | What's Included |
|---|---|---|
| **Simple auth (single role)** | 3–5 | JWT-based login, no roles, no audit |
| **Standard auth + RBAC** | 8–13 | OAuth2 provider integration, role hierarchy, permission checks, token refresh |
| **Enterprise security** | 20–40 | RBAC + ABAC, SSO/SAML, audit trail, secrets rotation, SAST/DAST, pen test, SOC2 prep |
| **Regulated industry** | 40–100 | Full compliance program, HSM, mTLS everywhere, zero-trust architecture, red team exercises |
| **Per-feature security review** | 1–3 | Threat model per feature, security code review |

### Common Omissions
- **Session management**: Token storage, refresh logic, concurrent session handling, forced logout.
- **Rate limiting**: API abuse protection — both at the edge and per-endpoint.
- **CORS/CSP headers**: Often forgotten until the first security scan.
- **Third-party dependency risk**: Do you know the security posture of every npm/pip/gem dependency?
- **Insider threat**: Audit logs for admin actions, separation of duties, approval workflows.

---

## 3. Performance & Scalability

### Probes
- Expected concurrent users? Peak vs average? Growth trajectory?
- Target response time? (p50, p95, p99)
- Target throughput? (requests/second, transactions/second)
- Data volume: how much data, how fast is it growing?
- Read-heavy or write-heavy? Real-time or batch?
- Caching strategy needed? (CDN, application cache, DB query cache)
- Database: indexing strategy, connection pooling, read replicas, sharding?
- Are there known bottlenecks? (legacy system, single DB, monolith)

### Typical Point Ranges
| Scope | Points | What's Included |
|---|---|---|
| **Light (internal tool, <100 users)** | 1–3 | Basic indexing, reasonable defaults |
| **Moderate (B2B SaaS, <10k users)** | 5–13 | Caching layer, connection pooling, query optimization, load testing |
| **High (consumer app, <1M users)** | 13–40 | CDN, read replicas, async processing, horizontal scaling, performance monitoring, chaos testing |
| **Extreme (real-time, >1M users)** | 40–100 | Global CDN, multi-region active-active, sharding, event sourcing, custom infrastructure, dedicated performance team |

### Performance Budgeting
- Page load: <2s for B2B, <1s for consumer
- API response: p95 <200ms for internal, p95 <100ms for external
- Database query: <50ms for OLTP, optimize anything >100ms
- These targets drive architecture choices — don't budget for a cached static page the same as a real-time analytics query.

### Common Omissions
- **Cold start**: First request latency for serverless/lambda architectures.
- **Thundering herd**: Cache stampede under high concurrency.
- **Connection pool exhaustion**: Underestimated concurrent DB connections.
- **N+1 queries**: ORM laziness — hard to estimate without knowing the data model.
- **Long-tail latency**: p99 can be 10x p50; users notice the worst experience.

---

## 4. Monitoring & Observability

### Probes
- Logging: structured (JSON) or unstructured? Centralized (ELK/Loki/Datadog) or per-server?
- Metrics: what to measure? (RED: Rate/Errors/Duration; USE: Utilization/Saturation/Errors)
- Alerting: what thresholds? Who gets paged? Escalation path?
- Distributed tracing needed? (Jaeger, Zipkin, Datadog APM, X-Ray)
- Dashboards: who needs them? (dev, ops, product, executives)
- Synthetic monitoring / health checks / heartbeat endpoints?
- Error tracking (Sentry, Rollbar)?

### Typical Point Ranges
| Scope | Points | What's Included |
|---|---|---|
| **Basic (logs only)** | 2–5 | Structured logging, central log aggregation, basic grep-based debugging |
| **Standard** | 8–13 | Logs + metrics + dashboards + alerting for critical paths, basic APM |
| **Advanced** | 20–40 | Distributed tracing, SLO/SLI monitoring, anomaly detection, synthetic checks, error budgets, on-call runbooks |
| **Per-service monitoring integration** | 1–3 | Add standard metrics/logging to a new service when platform already exists |

### Common Omissions
- **Business metrics**: Not just CPU/memory — also signups, payments, orders, feature adoption. These require instrumentation.
- **Alert fatigue**: Too many alerts → ignored alerts → real incidents missed. Budget time for tuning.
- **Log retention**: Compliance often requires 90+ days. Storage costs scale with volume.
- **On-call readiness**: Monitoring tools alone don't reduce MTTR. Runbooks, escalation paths, and training matter.
- **Frontend monitoring**: JS errors, page load times, user interaction latency. Often overlooked in backend-centric monitoring plans.

---

## 5. SLA / Reliability / Availability

### Probes
- Target availability? (99.9% = 8.76h downtime/year; 99.99% = 52min/year)
- RPO (Recovery Point Objective): How much data can you lose? (0 = synchronous replication)
- RTO (Recovery Time Objective): How fast must you recover? (<1h vs <4h vs <24h)
- Single points of failure identified?
- Disaster recovery plan: active-passive, active-active, pilot light?
- Data backup: frequency, retention, tested restores?
- Graceful degradation: if a dependency fails, does the app crash or degrade?

### Typical Point Ranges
| Target | Points | What's Included |
|---|---|---|
| **Best-effort (dev/startup)** | 2–5 | Backups, basic health checks, manual recovery |
| **99.9% (standard SaaS)** | 8–20 | Automated failover, tested backups, redundant instances, health check + auto-restart |
| **99.99% (enterprise)** | 20–60 | Multi-AZ, multi-region DR, active-active, chaos engineering, zero-downtime deployments, automated rollback |
| **99.999%+ (telco/finance)** | 60–200+ | Full redundancy at every layer, no single point of failure, dedicated SRE team, strict change management |

### Common Omissions
- **Partial failure handling**: Circuit breakers, retries with backoff, bulkheads, timeouts. These pattern implementations add up.
- **Data consistency during failover**: Eventual consistency is easy; strong consistency across regions is hard.
- **DNS propagation delay**: Failover can take minutes due to DNS TTL — is that acceptable?
- **Stateful services**: Stateless web servers scale easily; databases, caches, and message queues don't.

---

## 6. Usability & UX

### Probes
- Are there design mockups / wireframes? What fidelity?
- Accessibility requirements? (WCAG 2.1 AA is standard for government/enterprise)
- Internationalization (i18n)? How many languages? RTL support?
- Responsive design: desktop + tablet + mobile, or specific breakpoints?
- Loading states, empty states, error states designed?
- User onboarding flow (tutorials, tooltips, empty-state CTAs)?
- Design system / component library exists or needs creation?

### Typical Point Ranges
| Scope | Points | What's Included |
|---|---|---|
| **No UX (developer UI)** | 0–3 | Default framework styling, no custom design |
| **Light UX** | 3–8 | Wireframes provided, basic responsive, no i18n, minimal states |
| **Full UX** | 8–20 | Detailed mockups, responsive all breakpoints, loading/empty/error states, basic accessibility |
| **Premium UX** | 20–40 | Design system, full WCAG AA, i18n (3+ languages), motion design, user testing cycles |
| **Per-screen UX polish** | 1–3 | Align implementation to mockups for one screen |

### Common Omissions
- **Empty states**: "No data yet" screens need design, copy, and CTAs. Don't ship a blank page.
- **Error states**: Network errors, validation errors, server errors — each needs distinct UI treatment.
- **Loading states**: Skeleton screens, spinners, progress bars — different patterns for different data types.
- **Edge case content**: Very long names, missing images, RTL text in LTR UI, special characters.
- **Touch targets**: 44px minimum for mobile. Smaller = unusable for a portion of users.

---

## 7. Data Management

### Probes
- Database selection: relational (Postgres/MySQL), document (MongoDB), time-series (InfluxDB/TimescaleDB), graph?
- Schema design: normalized, denormalized, CQRS, event sourcing?
- Data migration strategy: backwards-compatible changes, expand-contract pattern?
- Data retention and archival: how long to keep? When to delete?
- GDPR / data privacy: right to access, right to delete, data export, consent tracking?
- Search functionality: full-text search (Elasticsearch/Typesense)?
- Analytics / reporting: separate read replica or data warehouse?

### Typical Point Ranges
| Scope | Points | What's Included |
|---|---|---|
| **Simple schema (single DB, few tables)** | 1–3 | Basic CRUD tables, indexes, no migration strategy |
| **Moderate schema** | 5–8 | Normalized design, migration tooling, basic archival, full-text search integration |
| **Complex data platform** | 13–40 | Multi-DB architecture, CQRS/event sourcing, data warehouse, GDPR compliance, data lineage |
| **Per-entity data modeling** | 1–3 | New entity type, schema design, migration, API exposure |

### Common Omissions
- **Data migration rollback**: Can you undo a migration safely? Test that.
- **Index impact on writes**: Every index speeds up reads but slows down writes. Balance.
- **Data growth projections**: A table that's fast at 10k rows may crumble at 10M. Plan ahead.
- **Soft delete vs hard delete**: GDPR often requires hard delete, but business logic often wants soft. Both paths need engineering.
- **Backup verification**: A backup that hasn't been restored-tested is not a backup.

---

## 8. Integration & API

### Probes
- Internal integration: between which microservices/modules?
- External integration: third-party APIs, partner systems, legacy monoliths?
- API versioning strategy?
- API documentation: OpenAPI/Swagger, auto-generated or manual?
- Webhook support: outgoing (your system calls theirs) and incoming (they call you)?
- Authentication/authorization between services: mTLS, API keys, OAuth client credentials?
- Rate limiting, throttling, quota management for API consumers?

### Typical Point Ranges
| Scope | Points | What's Included |
|---|---|---|
| **Single internal integration** | 2–5 | REST/gRPC between own services, shared auth context |
| **External API integration** | 5–13 | Third-party API, auth, error handling, retry, rate limit, webhook receiver (or sender) |
| **API platform** | 13–40 | API gateway, developer portal, OpenAPI docs, rate limiting, versioning, SDK generation |
| **Complex integration hub** | 20–60 | Multi-protocol (REST + gRPC + MQ), transformation layer, saga orchestration, dead-letter handling |

### Common Omissions
- **Timeouts and retries**: Network is unreliable. Every integration call needs timeout, retry, and circuit breaker.
- **Idempotency**: Can the same request be safely retried? Payment APIs demand idempotency keys.
- **Contract testing**: Provider changes break consumers silently. Pact/Spring Cloud Contract prevents this.
- **Rate limit handling**: Third-party APIs have rate limits. Your code must respect them (backoff, queuing).
- **IP whitelisting / network access**: Enterprise integrations often require static IPs, VPN tunnels, or VPC peering.

---

## CFR Total: How Much to Add

As a rule of thumb, CFR adds **30–60%** on top of pure functional story points, depending
on system maturity requirements:

| System Type | CFR as % of Functional | Typical CFR Areas |
|---|---|---|
| **Internal tool / PoC** | 10–30% | Basic monitoring, simple auth |
| **B2B SaaS (startup)** | 30–50% | CI/CD, standard auth + RBAC, logging, backups |
| **B2B SaaS (scale-up)** | 50–80% | Full monitoring, performance tuning, multi-tenancy, SLA targets, security review |
| **Enterprise / Regulated** | 80–150% | Compliance, DR, pen testing, advanced security, SRE, audit, i18n, accessibility |

If the estimate has zero CFR items, something is almost certainly being missed. Every
production system needs at minimum: auth, logging, monitoring, and backups.

---

## CFR Anti-Patterns

- **"We'll handle security later"** — Retrofitting auth is 3–5x more expensive than building it in from the start.
- **"Monitoring is just adding a few dashboard widgets"** — Monitoring is instrumentation + aggregation + alerting + runbooks + on-call rotation. The widgets are the last 10%.
- **"The cloud provider handles reliability"** — Cloud providers offer *building blocks*, not reliability. Multi-AZ deployment, failover logic, and DR testing are your responsibility.
- **"We don't need performance work until we have users"** — Architecture decisions made early (DB schema, API design, caching strategy) dictate the performance ceiling. Fixing it later often requires a rewrite.
- **"i18n is just translating strings"** — i18n also means: date/number formatting, RTL layout, pluralization rules, string length variance (German words are ~30% longer than English), culturally appropriate icons and colors.
