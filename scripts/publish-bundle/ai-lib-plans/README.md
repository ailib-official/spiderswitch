# ai-lib-plans — Internal Product & Business Guidance

> **Classification:** CONFIDENTIAL · INTERNAL USE ONLY  
> **Audience:** ai-lib product, engineering, and business decision-makers  
> **Canonical repo:** `ailib-official/ai-lib-plans`

This repository holds **authoritative internal planning** for the ai-lib product portfolio. It is version-controlled for team alignment and auditability, but **is not marketing or end-user documentation**.

Product repos (spiderswitch, velaclaw, prism-core, etc.) must **not** copy these documents locally. Each product repo adds only a root [`PORTFOLIO.md`](./templates/PORTFOLIO.md) pointer — see [REPO_ADOPTION.md](./REPO_ADOPTION.md).

## Canonical documents

| Document | Purpose |
|----------|---------|
| [GOVERNANCE.md](./GOVERNANCE.md) | How these plans are maintained, reviewed, and enforced |
| [PRODUCT_LINE_CHARTER.md](./PRODUCT_LINE_CHARTER.md) | Portfolio layers, SKUs, integration rules, diagrams |
| [IDENTITY_AND_TENANCY.md](./IDENTITY_AND_TENANCY.md) | Unified identity model (tenant → end-user → agent) |
| [REPO_ADOPTION.md](./REPO_ADOPTION.md) | How product lines follow this repo |

## Quick rules

1. **Charter wins** — If a product README, pitch deck, or issue contradicts the charter, the charter governs until amended.
2. **No silent SKUs** — New monetized surfaces require a charter appendix entry before launch.
3. **End-users are not our customers by default** — We manage **tenants**; tenants manage **their users** (see identity doc).
4. **No per-product `plans/` for global decisions** — Layer/SKU/gateway/identity changes belong here, not in individual product repos.

**Owners (internal):** Portfolio / Infra / Identity / Product — **Alex Wang** (see [GOVERNANCE.md](./GOVERNANCE.md)).

## Amendment process

See [GOVERNANCE.md](./GOVERNANCE.md). Summary: PR to `main` in **this repo**, Alex Wang review as Portfolio Owner, version bump in charter header.

## Bootstrap (one-time)

If this repo does not exist yet, an org admin creates it and publishes from the spiderswitch staging bundle:

```bash
gh repo create ailib-official/ai-lib-plans --private
git clone git@github.com:ailib-official/spiderswitch.git
cd spiderswitch && bash scripts/publish-ai-lib-plans.sh --from-bundle
```

After publish, **ai-lib-plans** is the sole source of truth; the staging bundle in spiderswitch is only a bootstrap convenience.
