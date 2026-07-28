# Fibonacci Point Scale — Detailed Reference

A story point is a relative measure combining **effort**, **complexity**, and **uncertainty**.
Points do NOT map to person-days — they describe the *thing being built*, not the *builder*.

---

## Scale Overview

| Points | Label | Effort | Complexity | Uncertainty | Decision Rule |
|---|---|---|---|---|---|
| **1** | Trivial | Minutes to hours | Almost none | Fully known | Can you describe every line of code before writing it? |
| **2** | Small | Hours to a day | Simple logic | Well-understood | One clear implementation path, no branching |
| **3** | Medium | 1–2 days | Moderate | Minor unknowns | Clear goal, slight variations in approach |
| **5** | Typical | 2–5 days | Real feature logic | Some unknowns | Multiple files, data model changes, error handling |
| **8** | Large | 1–2 weeks | Significant | Notable unknowns | Multiple approaches, may need research |
| **13** | Extra-Large | 2–4 weeks | High | Major unknowns | Architecture decisions required |
| **20** | Very Large | 1–2 months | Very high | Substantial unknowns | Should be split; signals an Epic |
| **40** | Massive | Multi-month | Extreme | Most unknowns | Must be decomposed |
| **100** | Epic | Quarter+ | Incalculable | Total ambiguity | Only useful as a placeholder; replace with decomposition |

---

## Domain-Specific Pointing Guide

### Web Application (CRUD-heavy)

| Points | Typical Web Stories |
|---|---|
| **1** | Change a label/color, add a config value, fix a typo, add a static FAQ page |
| **2** | Simple form with basic validation, single API endpoint + list page, search bar with exact match |
| **3** | Filtered list with pagination + sorting, file upload to S3, user profile edit form, basic CSV export |
| **5** | User registration with email verification, role-based CRUD dashboard, form wizard (3+ steps), PDF report generation, OAuth social login integration |
| **8** | Real-time notification system, complex RBAC with custom permissions, advanced search with full-text + facets, multi-step approval workflow, data import with mapping UI |
| **13** | Admin panel from scratch (auth + CRUD + filtering + audit), custom report builder with charting, multi-tenant data isolation layer, real-time collaborative editing |

### Mobile Application (iOS + Android)

| Points | Typical Mobile Stories |
|---|---|
| **1** | Update app icon, change splash screen color, bump SDK version (no breaking changes) |
| **2** | Add a static screen (About, Settings with toggles), simple list with API data, basic deep link |
| **3** | Camera/barcode scanner integration, push notification setup (one platform), form with image picker, local data caching with SQLite/Realm |
| **5** | Full onboarding flow (3+ screens), map with markers and clustering, background upload/download, biometric auth (Face ID + fingerprint) |
| **8** | Offline-first sync engine, chat/messaging screen with real-time updates, video recording + upload, complex animation transitions |
| **13** | Cross-platform AR feature, payment SDK integration (Stripe/Apple Pay / Google Pay), full navigation refactor |

### Backend / API

| Points | Typical Backend Stories |
|---|---|
| **1** | Add a field to an existing API response, update error message text, add a simple health check endpoint |
| **2** | New CRUD endpoint for a simple entity (no relations), add rate limiting to one endpoint, write a DB migration script |
| **3** | API endpoint with nested resource + validation, webhook receiver with signature verification, message queue consumer (single event type), email sending service integration |
| **5** | OAuth2 / JWT auth from scratch, full-text search indexing (Elasticsearch setup + sync), scheduled job with retry + dead-letter queue, data export pipeline (large dataset, async) |
| **8** | Event-driven saga for a multi-step business process, custom API gateway / BFF layer, data pipeline with ETL + transformation, multi-tenant API with tenant context propagation |
| **13** | Real-time sync protocol (WebSocket + conflict resolution), distributed transaction coordinator, custom query engine / GraphQL federation layer |

### IoT / Embedded

| Points | Typical IoT Stories |
|---|---|
| **1** | Change MQTT topic name, update device config parameter, add a log line |
| **2** | Add a new telemetry data point to existing message schema, simple device command (on/off/toggle), device status polling |
| **3** | New sensor data ingestion pipeline (single sensor type), OTA firmware update (single device type, happy path), device shadow / digital twin CRUD |
| **5** | Device provisioning flow with certificate generation, rule engine (basic: if temperature > X, send alert), multi-protocol gateway (MQTT + HTTP bridge), batch OTA with rollback |
| **8** | Full device lifecycle management (register, activate, monitor, decommission), real-time device state synchronization, edge computing rule deployment, multi-vendor protocol adapter |
| **13** | Custom firmware update protocol with delta updates, device fleet management at scale (10k+ devices), digital twin simulation engine, IoT data lake pipeline |

### DevOps / Infrastructure

| Points | Typical DevOps Stories |
|---|---|
| **1** | Add an environment variable to deployment config, update a CI pipeline trigger, add a health check probe |
| **2** | Dockerize a single service, add a Terraform module for S3/RDS, set up a basic Prometheus alert rule, configure ingress rule |
| **3** | CI/CD pipeline for a new microservice (build → test → deploy), infrastructure-as-code for a 3-tier app, centralized logging pipeline (EFK/Loki stack), database backup automation |
| **5** | Kubernetes cluster setup with Helm charts, blue-green / canary deployment pipeline, secrets management with Vault, multi-environment infrastructure (dev/staging/prod) |
| **8** | Service mesh setup (Istio/Linkerd), multi-region deployment with geo-routing, auto-scaling configuration with load testing, disaster recovery automation with runbooks |
| **13** | Full platform engineering (internal developer platform), compliance-as-code (SOC2/HIPAA automation), zero-downtime database migration strategy |

### Data & Analytics

| Points | Typical Data Stories |
|---|---|
| **1** | Add a column to an existing report, tweak a dashboard filter, add a simple aggregate query |
| **2** | New dashboard with 3–5 charts from existing data sources, single-table ETL job, data quality check for one field |
| **3** | Multi-table join report with date range filtering, incremental data sync pipeline, data anomaly detection (threshold-based), scheduled report email distribution |
| **5** | Real-time dashboard with WebSocket data stream, machine learning model serving (pre-trained), multi-source data aggregation pipeline, data lineage tracking |
| **8** | Recommendation engine (collaborative filtering), A/B testing framework backend, custom event tracking pipeline, data warehouse schema design + migration |
| **13** | Real-time fraud detection pipeline, full data platform (ingest → warehouse → BI → ML), GDPR data deletion pipeline across all systems |

---

## Calibration Heuristics

### When to bump up
- The story involves **3+ systems/services** to coordinate
- **No existing pattern** in the codebase to follow
- Requires **new third-party API/SDK** that the team hasn't used before
- Involves **state management** (workflows, state machines, sagas)
- Has **race conditions** or **concurrency** concerns
- Needs **backward compatibility** with existing API/data format
- Crosses **team boundaries** (coordination overhead)

### When to keep it lower
- The team has done **something very similar** before (≤3 months ago)
- A **well-documented library/SDK** handles most of the complexity
- It's a **clone-and-modify** of an existing feature
- The story has **zero third-party dependencies**
- It's a **pure UI** change with no backend/logic changes

### When uncertainty drives the number
- If >50% of the technical approach is unknown → **bump up one level**
- If the third-party API is undocumented or alpha → **bump up two levels**
- If the data model is undefined → **estimate a spike first**, then the story
- If acceptance criteria are vague → **do not estimate**; push for clarification

### The "two values" rule
If you're genuinely stuck between two adjacent Fibonacci values (e.g., 5 vs 8):
1. Ask: "Is the unknown in the *how* (pick lower) or in the *what* (pick higher)?"
2. If still stuck: **always pick the higher value**. Humans systematically under-estimate by 20–40%.

---

## Pointing Anti-Patterns

- **"It's just a form, 1 point"** — Forms involve validation, error states, loading states, accessibility, responsive design, test cases. Rarely a 1.
- **"The library handles it, 2 points"** — Library integration includes: reading docs, handling edge cases, version compatibility, styling overrides, error handling, testing. Bump to 3–5.
- **"Just expose it via API, 3 points"** — API work includes: auth, rate limiting, input validation, error codes, documentation, versioning, monitoring. 5–8 is more realistic.
- **"Migration script, 1 point"** — Data migrations involve: rollback plan, data integrity checks, performance on large datasets, downtime window. 2–5 depending on data volume.
- **Estimating per person**: "Senior dev can do it in 2 days, so 2 points" — Points are not person-days. A 5-point story is 5 points whether a junior or senior does it. The velocity accounts for who's on the team.
