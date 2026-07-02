# Plans Governance — ai-lib Product Portfolio

> **Classification:** CONFIDENTIAL · INTERNAL  
> **Status:** Active  
> **Effective:** 2026-07-01  
> **Portfolio Owner:** Alex Wang  
> **Infra Owner (L0/L1/L3):** Alex Wang  
> **Identity Owner:** Alex Wang  
> **Product Owner (all L2 SKUs):** Alex Wang  

## 1. Purpose

These rules ensure documents in **`hiddenpath/ai-lib-plans`** function as **binding internal business guidance**, not informal notes. They apply to all repositories under the ai-lib ecosystem (public `ailib-official/*` product repos and internal `hiddenpath/*` assets) and to partner repos that ship ai-lib–branded products.

**Canonical location:** `hiddenpath/ai-lib-plans` — CONFIDENTIAL plans **must not** live under `ailib-official` (public org). Product repos **must not** mirror the charter locally (see [REPO_ADOPTION.md](./REPO_ADOPTION.md)).

## 2. Authority hierarchy

When documents conflict, resolve in this order:

1. **PRODUCT_LINE_CHARTER.md** — portfolio layers, SKU boundaries, integration mandates  
2. **IDENTITY_AND_TENANCY.md** — tenant / end-user / agent identity rules  
3. **Product-specific internal plans** — only in product repo if **scoped to that SKU**; must not contradict 1–2 and must not redefine layers/SKU catalog  
4. **Public README / marketing** — must not over-promise beyond 1–2  
5. **Issue comments / ad-hoc chat** — non-binding

## 3. Roles

| Role | Responsibility | Assigned |
|------|----------------|----------|
| **Portfolio Owner** | Approves charter amendments; chairs quarterly review | Alex Wang |
| **Product Owner (per L2 SKU)** | Keeps product roadmap aligned with charter; files amendment requests | Alex Wang (all SKUs) |
| **Infra Owner (L0/L1/L3)** | prism-core, Gateway, ai-lib runtimes; publishes integration contracts | Alex Wang |
| **Identity Owner** | Cross-product auth, tenant model, billing identity mapping | Alex Wang |

Amendment approvals in §4 reference the assigned owners above until RACI is expanded.

## 4. Amendment workflow

### 4.1 Minor (clarification, typo, non-normative diagram)

- PR to **`hiddenpath/ai-lib-plans`** `main` with label `plans-minor`  
- One Portfolio Owner or Product Owner approval  
- Patch version bump in charter (`v1.0.1`)

### 4.2 Major (new SKU, layer change, gateway convergence, identity model change)

- PR with label `plans-major`  
- Written rationale: problem, options, decision, impact on existing SKUs  
- Portfolio Owner + Infra Owner approval (Identity Owner if tenancy affected)  
- Minor version bump (`v1.1.0`)  
- **Sunset period** documented if breaking promises to tenants

### 4.3 Emergency (legal, security, production incident)

- Hotfix PR with `plans-emergency`  
- Retrospective amendment within 5 business days

## 5. Enforcement mechanisms

### 5.1 Repository checklist (new L2 product or major feature)

Before GA or paid launch, confirm:

- [ ] Charter appendix row exists (SKU name, layer, inference mode, monetization)  
- [ ] Identity doc: tenant vs end-user boundaries defined  
- [ ] No duplicate L3 data plane without Infra Owner exception  
- [ ] Public README does not contradict charter promises  
- [ ] MCP/control-only products declare `effective_scope` in product UX/docs  

### 5.2 Pull request gate (recommended)

PRs that touch any of the following require checkbox in description linking to charter section:

- New HTTP proxy / gateway / `/api/proxy` route  
- User registration, login, API key issuance  
- Pricing, billing, metering  
- MCP tool descriptions implying Host LLM control  
- New top-level product repo  

Template: use [`.github/pull_request_template.md`](./.github/pull_request_template.md) in **this repo**. Optionally mirror to `hiddenpath/.github` for internal repos — **not** to `ailib-official/.github` (public org).

```markdown
## Portfolio alignment
- [ ] Reviewed ai-lib-plans PRODUCT_LINE_CHARTER.md (section: ___)
- [ ] Identity impact: none / documented in PR
- [ ] New SKU: no / PR to ai-lib-plans included
```

### 5.3 Quarterly portfolio review

Every quarter:

1. Walk all L2 SKUs against charter appendix — mark **active / pivot / sunset / merge**  
2. Reconcile Gateway implementations (Prism hosted vs Eos proxy vs embedded)  
3. Audit public messaging samples (README, Gumroad, plugin manifest)  
4. Update charter version and review log (appendix C in charter)

### 5.4 Confidentiality and org separation

| Org | Purpose | ai-lib-plans |
|-----|---------|--------------|
| **`ailib-official`** | Public OSS, PyPI, plugin market, open README | **Must not** host charter or CONFIDENTIAL plans |
| **`hiddenpath`** | Internal-only repos, NDA material, pre-release strategy | **Canonical home** for ai-lib-plans |

- Do **not** link ai-lib-plans from **public** README, PyPI, or plugin market copy (org members use direct repo access under hiddenpath)
- Do **not** copy charter into product repositories under `ailib-official`
- Do **not** create `ailib-official/ai-lib-plans` — violates org separation policy
- Contractors: NDA + read-only access to hiddenpath/ai-lib-plans on need-to-know basis  

## 6. Relationship to code

Governance is not satisfied by documentation alone. Required **technical anchors** (implement over time):

| Charter rule | Technical enforcement |
|--------------|---------------------|
| Control vs data plane split | `routing_mode` / `effective_scope` in spiderswitch; Gateway Control API in prism |
| Single L3 convergence | Deprecate duplicate proxy paths on a published timeline |
| Tenant vs end-user | Shared `tenant_id` + `subject_id` in Gateway auth middleware |
| No silent SKU | Plugin manifest + `pyproject` version aligned with charter appendix |

## 7. Exceptions

Infra Owner may grant **time-boxed exceptions** (max 90 days) for experiments. Exceptions must be logged in charter Appendix C (Exceptions log) with expiry and owner.

---

*Amend this governance doc using the same §4 process (meta-governance: Major amendment).*
