# Plans — Internal Product & Business Guidance

> **Classification:** CONFIDENTIAL · INTERNAL USE ONLY  
> **Audience:** ai-lib product, engineering, and business decision-makers  
> **Public repos must NOT link to this directory.**

This folder holds **authoritative internal planning** for the ai-lib product portfolio. It is version-controlled for team alignment and auditability, but **is not marketing or end-user documentation**.

## Canonical documents

| Document | Purpose |
|----------|---------|
| [GOVERNANCE.md](./GOVERNANCE.md) | How these plans are maintained, reviewed, and enforced |
| [PRODUCT_LINE_CHARTER.md](./PRODUCT_LINE_CHARTER.md) | Portfolio layers, SKUs, integration rules, diagrams |
| [IDENTITY_AND_TENANCY.md](./IDENTITY_AND_TENANCY.md) | Unified identity model (tenant → end-user → agent) |

## Quick rules

1. **Charter wins** — If a product README, pitch deck, or issue contradicts the charter, the charter governs until amended.
2. **No silent SKUs** — New monetized surfaces require a charter appendix entry before launch.
3. **End-users are not our customers by default** — We manage **tenants**; tenants manage **their users** (see identity doc).

**Owners (internal):** Portfolio / Infra / Identity / Product — **Alex Wang** (see [GOVERNANCE.md](./GOVERNANCE.md)).

## Amendment process

See [GOVERNANCE.md](./GOVERNANCE.md). Summary: PR to `main` with `plans/` label, Alex Wang review as Portfolio Owner, version bump in charter header.
