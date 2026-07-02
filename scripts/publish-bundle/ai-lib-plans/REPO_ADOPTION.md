# Repository adoption — how product lines follow ai-lib-plans

> **Classification:** CONFIDENTIAL · INTERNAL  
> **Canonical repo:** `hiddenpath/ai-lib-plans` (**not** `ailib-official`)

## 1. Rule

| Do | Don't |
|----|-------|
| Add `PORTFOLIO.md` pointer at product repo root | Copy `PRODUCT_LINE_CHARTER.md` into product repos |
| Open PRs in **hiddenpath/ai-lib-plans** to change portfolio rules | Edit charter only in spiderswitch / velaclaw / etc. |
| Reference charter section in product PRs when boundary changes | Create per-repo `plans/` for global SKU/layer decisions |
| Use PR template from ai-lib-plans for internal repos | Host CONFIDENTIAL plans under `ailib-official` |
| Keep public product repos under `ailib-official` | Put ai-lib-plans in the public org (even if private) |

## 2. Org separation

| GitHub org | Role |
|------------|------|
| **`ailib-official`** | Public-facing OSS, releases, plugin market, open documentation |
| **`hiddenpath`** | CONFIDENTIAL internal planning, pre-release strategy, NDA material |

**ai-lib-plans belongs exclusively in `hiddenpath`.** A private repo under `ailib-official` still violates governance — that org is treated as public-facing.

## 3. Product repository checklist

For each repo under `ailib-official/*`:

- [ ] Root [`PORTFOLIO.md`](./templates/PORTFOLIO.md) present (pointer only, no charter copy)
- [ ] No `plans/PRODUCT_LINE_CHARTER.md` (or remove if mistakenly added)
- [ ] README does not link to hiddenpath/ai-lib-plans
- [ ] README does not contradict charter (see charter §4.3 promise matrix)
- [ ] New monetized surface has row in charter Appendix A (PR to **hiddenpath/ai-lib-plans**)

## 4. Registered product repos (initial)

| Repo | Org | SKU IDs | Product Owner |
|------|-----|---------|---------------|
| `spiderswitch` | ailib-official | L2-SPIDER, L2-SPIDER-PRO | Alex Wang |
| `prism-core` | ailib-official | L1-PRISM-CORE, L3-PRISM (with hosted) | Alex Wang |
| `velaclaw` | ailib-official | L2-VELACLAW | Alex Wang |
| `vela` | ailib-official | L2-VELA | Alex Wang |
| `aidebate` | ailib-official | L2-AIDEBATE | Alex Wang |
| `ai-lib-python` / `rust` / `go` / `ts` | ailib-official | L0 | Alex Wang |
| Eos (external or `eos-server`) | varies | L2-EOS | Alex Wang |
| **`ai-lib-plans`** | **hiddenpath** | (governance) | Alex Wang |

Update this table via PR to **hiddenpath/ai-lib-plans** when repos are added or retired.

## 5. When to PR which repo

| Change type | Target repo |
|-------------|-------------|
| New SKU, layer rule, gateway convergence, identity model | **hiddenpath/ai-lib-plans** |
| Product-specific roadmap, implementation detail | Product repo (`ailib-official/*`) |
| Charter amendment + product code alignment | **Two PRs**: ai-lib-plans first (or same PR cycle), then product |

## 6. Compliance review

Quarterly (see [GOVERNANCE.md](./GOVERNANCE.md) §5.3), Portfolio Owner verifies each repo in §4 against this checklist.
