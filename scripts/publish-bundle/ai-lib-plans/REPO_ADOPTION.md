# Repository adoption — how product lines follow ai-lib-plans

> **Classification:** CONFIDENTIAL · INTERNAL  
> **Canonical repo:** `ailib-official/ai-lib-plans`

## 1. Rule

| Do | Don't |
|----|-------|
| Add `PORTFOLIO.md` pointer at product repo root | Copy `PRODUCT_LINE_CHARTER.md` into product repos |
| Open PRs in **ai-lib-plans** to change portfolio rules | Edit charter only in spiderswitch / velaclaw / etc. |
| Reference charter section in product PRs when boundary changes | Create per-repo `plans/` for global SKU/layer decisions |
| Use org `.github` PR template from ai-lib-plans | Duplicate org PR template in every repo (optional override only) |

## 2. Product repository checklist

For each repo under `ailib-official/*`:

- [ ] Root [`PORTFOLIO.md`](./templates/PORTFOLIO.md) present  
- [ ] No `plans/PRODUCT_LINE_CHARTER.md` (or remove if mistakenly added)  
- [ ] README does not contradict charter (see charter §4.3 promise matrix)  
- [ ] New monetized surface has row in charter Appendix A (PR to **ai-lib-plans**)  

## 3. Registered product repos (initial)

| Repo | SKU IDs | Product Owner |
|------|---------|---------------|
| `spiderswitch` | L2-SPIDER, L2-SPIDER-PRO | Alex Wang |
| `prism-core` | L1-PRISM-CORE, L3-PRISM (with hosted) | Alex Wang |
| `velaclaw` | L2-VELACLAW | Alex Wang |
| `vela` | L2-VELA | Alex Wang |
| `aidebate` | L2-AIDEBATE | Alex Wang |
| `ai-lib-python` / `rust` / `go` / `ts` | L0 | Alex Wang |
| Eos (external or `eos-server`) | L2-EOS | Alex Wang |

Update this table via PR to **ai-lib-plans** when repos are added or retired.

## 4. When to PR which repo

| Change type | Target repo |
|-------------|-------------|
| New SKU, layer rule, gateway convergence, identity model | **ai-lib-plans** |
| Product-specific roadmap, implementation detail | Product repo |
| Charter amendment + product code alignment | **Two PRs**: ai-lib-plans first (or same PR cycle), then product |

## 5. Compliance review

Quarterly (see [GOVERNANCE.md](./GOVERNANCE.md) §5.3), Portfolio Owner verifies each repo in §3 against this checklist.
