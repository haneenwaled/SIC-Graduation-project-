# Promotion Policy — Retain & Recommend AI

**Project:** Retain & Recommend AI — Returns-Aware Product Recommendation, Customer Lapse Prediction & RAG-Powered Retention Agent
**Document type:** Knowledge Base file 2 of 3 (promotion and discount decision policy)
**Companion files:** `retention_playbook.md` (retention actions), `business_rules_kpis.md` (definitions, formulas, thresholds)
**Version:** 1.1 — risk tiers aligned with the supplied scoring file `customer_lapse_predictions.csv` (Low, Medium, High)

---

## 0. Critical Notice and Reading Rules

### 0.1 No Approved Company Policy Is Included
**`Verified Fact`** — This document does **not** contain a company's approved discount limits, margin requirements, budgets, or eligibility rules. None were provided to the author.

**`Proposed Policy — Requires Business Approval`** — Every rule below that sets a limit, condition, or decision outcome is a proposal. The AI Agent must **never treat a proposed rule as approved business policy**, must not present proposed rules to customers or staff as binding, and must disclose their proposed status when citing them.

### 0.2 Placeholders
Where a number would normally appear, this document uses a named placeholder. Placeholders have no value until the business sets them. The Agent must not guess a value.

| Placeholder | Meaning | Status |
|---|---|---|
| `D_MAX_[tier]` | Maximum discount percentage permitted for a category of promotion | `Data Gap` — not set |
| `M_MIN` | Minimum acceptable margin after discount | `Data Gap` — not set |
| `B_PERIOD` | Promotion budget for a defined period | `Data Gap` — not set |
| `B_CUSTOMER` | Maximum promotion spend per customer per period | `Data Gap` — not set |
| `N_COOLDOWN` | Minimum days between promotions to the same customer | `Data Gap` — not set |
| `APPROVER_ROLE_[n]` | Role entitled to approve at a given level | `Data Gap` — not set |

### 0.3 Evidence Labels
`Verified Fact`, `Proposed Assumption`, `Proposed Policy — Requires Business Approval`, `Pending Validation`, `Data Gap`, `Human Review Required`. Definitions are in `retention_playbook.md`, Section 0.2.

### 0.4 Customer-Specific Inputs
- **Guardrail PG-1:** Customer risk tier, value tier, flags, and product scores used in promotion decisions must come from actual model outputs or structured data. If missing, the decision outcome is **Not Recommended** until the data is supplied.
- **Guardrail PG-2:** The Agent must never state or imply that a model score or priority score is a monetary amount, a profit figure, or a guaranteed return from a promotion.

### 0.5 Shared Terms (Consistent With Other Files)
- **Risk tiers:** Low (p_lapse < 0.30), Medium (0.30 to < 0.50), High (≥ 0.50). `Verified Fact` for the ranges observed in `customer_lapse_predictions.csv`; business meaning `Pending Validation`. The earlier Critical tier has been retired.
- **Focus List:** The top N High-risk customers by Priority Score (`retention_playbook.md`, Section 5.5). N is a `Data Gap`.
- **Value tiers:** V1 (≥ 90th percentile of historical net revenue), V2 (60th to < 90th), V3 (< 60th). `Proposed Assumption`, `Pending Validation`.
- **Flags:** Repeated Cancellation Flag (RCF), Declining Activity Flag (DAF), Limited History Flag (LHF).
- **Priority bands:** P1 to P4 (see `retention_playbook.md`, Section 5.3).

---

## 1. Purpose and Principles

### 1.1 Purpose
The promotion policy ensures that incentives are used deliberately for retention, protect profitability, and remain auditable.

### 1.2 Principles
`Proposed Policy — Requires Business Approval`
1. **Last resort, not first lever.** Use non-price retention actions first (service recovery, outreach, availability support).
2. **Need-based.** A promotion should respond to a documented retention need (risk, decline, or a specific barrier), not to routine behavior.
3. **Smallest effective incentive.** Use the lowest-cost incentive that plausibly addresses the need.
4. **Profit-protective.** Do not recommend a promotion whose profitability cannot be assessed.
5. **Human-approved.** The Agent recommends; people decide.
6. **Auditable.** Every recommendation is logged with its inputs and rule references.
7. **Fair and consistent.** Similar customers in similar situations receive consistent treatment.

---

## 2. Promotion Types Covered

| Type | Description |
|---|---|
| Percentage discount | Reduction on price of selected products or an order |
| Volume or tier incentive | Better price for purchase volume |
| Free shipping or service benefit | Non-price commercial benefit |
| Credit or rebate | Value returned after purchase |
| Bundle offer | Combination of products at a package price |
| Early-access or priority-availability benefit | Non-price benefit; no margin cost |

**`Data Gap`** — Which of these types the business actually offers is not specified.

**`Proposed Assumption`** — Non-price benefits (early access, priority availability, service attention) are lower risk to profitability and should be considered before price-based promotions.

---

## 3. Eligibility and Exclusion Criteria

### 3.1 Eligibility Criteria (All Must Be True)
`Proposed Policy — Requires Business Approval`

| ID | Criterion |
|---|---|
| E-1 | Customer-specific model outputs are present and valid (p_lapse, risk tier, prediction timestamp). |
| E-2 | Customer risk tier is **High**, or the Declining Activity Flag is present with Medium risk and V1/V2 value. |
| E-3 | A documented retention need exists (for example, declining activity or a specific barrier). |
| E-4 | Non-price retention actions have been considered and recorded. |
| E-5 | The customer is not excluded under Section 3.2. |
| E-6 | The product or order is available and not excluded under Section 5. |
| E-7 | Profitability can be assessed (margin data available), or the promotion is marked for Approval with a Data Gap. |
| E-8 | No cooldown violation (`N_COOLDOWN`) and no per-customer budget breach (`B_CUSTOMER`). |

### 3.2 Exclusion Criteria (Any One Excludes)
`Proposed Policy — Requires Business Approval`

| ID | Exclusion | Rationale |
|---|---|---|
| X-1 | Low risk tier with no flags. | Discount unlikely to change behavior; wastes margin. |
| X-2 | Missing or invalid model output. | Cannot justify the need. |
| X-3 | Customer in dispute, credit hold, or collections. | `Human Review Required`; commercial issues first. |
| X-4 | Repeated Cancellation Flag where cancellations are unexplained. | Do not reward unexplained order-and-cancel cycles; review first. |
| X-5 | Product unavailable, discontinued, restricted, or under stock constraint. | Cannot be fulfilled. |
| X-6 | Customer already received a promotion within `N_COOLDOWN`. | Avoids training customers to wait for discounts. |
| X-7 | Promotion would push projected margin below `M_MIN`. | Profitability safeguard. |
| X-8 | Budget `B_PERIOD` or `B_CUSTOMER` exhausted. | Budget safeguard. |
| X-9 | Customer is Already Lapsed and no reactivation approach has been approved. | Needs a distinct reactivation decision (Section 4.3). |
| X-10 | Legal or contractual pricing restriction applies. | `Data Gap`; confirm with business. |

---

## 4. Customer-Specific Considerations

### 4.1 By Risk Tier
| Tier | Promotion stance (default) |
|---|---|
| Low | Not recommended |
| Medium | Not recommended unless DAF with V1/V2; otherwise non-price actions |
| High (not on the Focus List) | Eligible for review |
| High (on the Focus List) | Requires approval |

### 4.2 By Flags
- **RCF present:** The promotion is not the first lever. Require review of cancellation causes. If unexplained, exclusion X-4 applies.
- **DAF present:** A targeted offer on categories that declined may be considered, after a needs conversation.
- **LHF present:** Model reliability is reduced; promotion requires approval and a Data Gap note.

### 4.3 Already Lapsed Customers
**`Proposed Policy — Requires Business Approval`** — Reactivation offers are treated as a separate decision. They require approval regardless of value tier, because the customer is outside the standard prediction population and because outcomes are hard to separate from natural return behavior.

### 4.4 Value Tier Considerations
- V1 customers: higher potential justification, but also higher exposure if margin is eroded. Require approval when the customer is on the Focus List.
- V3 customers: Default to non-price, low-cost actions. A promotion needs a documented reason.
- **Guardrail PG-3:** Value tier is derived from historical net revenue. It does not equal profit. If customer margin is unknown, say so.

### 4.5 Fairness and Consistency
**`Proposed Policy — Requires Business Approval`**
- Decisions must rest on business factors (risk, value, margin, availability), not on protected or irrelevant personal characteristics.
- Record the rule path for each recommendation so similar cases can be checked for consistency.

---

## 5. Product Availability and Cancellation Considerations

### 5.1 Availability Rules
- **PG-4:** Never recommend a promotion on a product marked unavailable, discontinued, or restricted.
- **PG-5:** If stock status is unknown, mark "availability unconfirmed" and require approval; do not assume availability.
- **PG-6:** Avoid promoting products with constrained stock that would be oversold, because stock-outs lead to cancellations.

### 5.2 Cancellation-Aware Rules
`Proposed Policy — Requires Business Approval`
- **PG-7:** Do not offer promotions on products with high estimated cancellation risk for that customer or segment, unless a human confirms the cause has been addressed. **`Data Gap`** — what counts as "high" cancellation risk is not defined; use model-supplied values and the thresholds approved by the business.
- **PG-8:** A promotion must not make it cheaper to place and then cancel an order. Check whether the offer conditions apply only to fulfilled (non-cancelled) orders.
- **PG-9:** Promotion effectiveness must be measured on **net** (post-cancellation) results, not gross orders.

---

## 6. Rules for Avoiding Unnecessary or Excessive Discounts

`Proposed Policy — Requires Business Approval`

| ID | Rule | Reason |
|---|---|---|
| U-1 | Do not discount customers who show strong, regular purchasing (Low risk). | Margin giveaway. |
| U-2 | Try non-price actions first and record the attempt. | Cheaper and avoids price dependence. |
| U-3 | Use the smallest incentive that addresses the documented need, never above `D_MAX_[tier]`. | Limits margin erosion. |
| U-4 | Limit promotions to relevant products or categories rather than blanket order discounts. | Targeting reduces cost. |
| U-5 | Enforce cooldown `N_COOLDOWN` between promotions per customer. | Prevents discount habituation. |
| U-6 | Enforce per-customer and period budgets. | Cost control. |
| U-7 | Do not stack promotions unless explicitly approved. | Prevents compounding discounts. |
| U-8 | Time-limit all promotions. | Avoids permanent price reductions. |
| U-9 | Do not use promotions to compensate for service failures that have not been investigated. | Treat the cause. |
| U-10 | Do not present a discount as guaranteed to retain the customer. | No causal evidence yet (`Pending Validation`). |

---

## 7. Discount Limits, Budgets, Margins, and Profitability Safeguards

### 7.1 Limits and Budgets
**`Data Gap`** — Actual limits, budgets, and margin requirements are not provided. The framework below is structural only.

| Control | Definition | Value |
|---|---|---|
| Discount cap by tier | Maximum percentage for each promotion category | `D_MAX_[tier]` — not set |
| Minimum margin | Lowest acceptable margin after discount | `M_MIN` — not set |
| Period budget | Total promotion spend allowed | `B_PERIOD` — not set |
| Customer budget | Spend allowed per customer per period | `B_CUSTOMER` — not set |
| Cooldown | Days between promotions per customer | `N_COOLDOWN` — not set |

### 7.2 Margin Safeguard Formula (Structural)
```
Post-Promotion Margin Rate = (Net Price after Discount − Unit Cost) / Net Price after Discount
```
- `Net Price after Discount` — currency per unit, after the discount.
- `Unit Cost` — currency per unit of product cost. **`Data Gap`** — product cost data is not confirmed.
- **Unit:** ratio (0 to 1) or percentage. Denominator: net price after discount.
- **Rule:** If `Post-Promotion Margin Rate < M_MIN`, the recommendation is **Not Recommended**.
- **Limitation:** The formula ignores shipping, handling, payment, and returns costs unless they are included in unit cost.

### 7.3 Profitability Assessment Cautions
- Revenue, profit, customer value, and model scores are different things (see `business_rules_kpis.md`, Section 14).
- **PG-10:** The Agent must not claim that a promotion is profitable unless cost and margin data are supplied and the calculation is shown.
- **PG-11:** Historical net revenue of a customer does not justify a discount by itself.
- **PG-12:** Expected gains from a retained customer are `Pending Validation` until measured in a controlled evaluation.

### 7.4 Budget Tracking
**`Proposed Policy — Requires Business Approval`** — Each approved promotion must be recorded against its budget; the Agent must check whether remaining budget information is available. If not available, mark `Data Gap` and require approval.

---

## 8. Promotion Decision Matrix

### 8.1 Outcomes
| Outcome | Meaning |
|---|---|
| **Not Recommended** | The Agent should not propose a promotion. Suggest non-price actions. |
| **Eligible for Review** | A promotion may be proposed for human review within standard limits. A reviewer confirms before anything is offered. |
| **Requires Approval** | A promotion may be drafted only with explicit approval by an authorized approver before any communication. |

All outcomes are `Proposed Policy — Requires Business Approval`.

### 8.2 Primary Matrix (No Exclusion Triggered, Data Complete)
| Risk tier | V1 | V2 | V3 |
|---|---|---|---|
| Low | Not Recommended | Not Recommended | Not Recommended |
| Medium | Not Recommended (Eligible for Review if DAF) | Not Recommended (Eligible for Review if DAF) | Not Recommended |
| High | Eligible for Review | Eligible for Review | Not Recommended (Eligible for Review only with documented reason) |

The Focus List override in Section 8.3 is applied after this matrix.

### 8.3 Override Rules (Applied After the Matrix)
| Condition | Result |
|---|---|
| Any exclusion X-1 to X-10 applies | **Not Recommended** (X-3, X-9, X-10 may route to Requires Approval or Human Review) |
| Missing model output or risk tier | **Not Recommended** |
| Margin data missing | At most **Requires Approval**, with Data Gap noted |
| Stock status unknown | **Requires Approval** |
| RCF present with explained cancellations | Raise one level (Eligible for Review → Requires Approval) |
| RCF present with unexplained cancellations | **Not Recommended** until reviewed |
| Any promotion above `D_MAX_[tier]`, outside budget, or stacked | **Requires Approval** |
| Already Lapsed (reactivation) | **Requires Approval** |
| Limited History Flag | Raise one level |
| Conflicting signals (HR-6) | **Requires Approval** |
| Customer is on the Focus List | **Requires Approval** |
| Risk tier from the scoring file conflicts with `lapse_probability` ranges (HR-10) | **Not Recommended** until the data is checked |

### 8.4 Reading Rule
When two rules conflict, the **more restrictive** outcome applies (order: Not Recommended > Requires Approval > Eligible for Review).

---

## 9. Conditions Requiring Human Approval

`Human Review Required` — Approval is mandatory in any of these cases. `Proposed Policy — Requires Business Approval`.

| ID | Condition |
|---|---|
| A-1 | Any promotion for a customer on the Focus List (`retention_playbook.md`, Section 5.5). |
| A-2 | Any promotion for a P1-band customer. |
| A-3 | Discount above `D_MAX_[tier]` or any exception to a rule. |
| A-4 | Margin data missing or `Post-Promotion Margin Rate` unverified. |
| A-5 | Stock status unknown or constrained. |
| A-6 | Customer has the RCF. |
| A-7 | Customer has the LHF. |
| A-8 | Reactivation of an Already Lapsed customer. |
| A-9 | Credits, rebates, payment-term changes, or contract-level concessions. |
| A-10 | Promotions stacked with another offer. |
| A-11 | Remaining budget unknown or insufficient. |
| A-12 | Conflicting signals or low data quality. |
| A-13 | Any customer-facing communication that mentions price. |

---

## 10. Approval Workflow and Auditability

### 10.1 Workflow
1. **Agent drafts** a promotion recommendation with the required fields (10.2).
2. **Eligibility check** against Sections 3 to 7.
3. **Decision matrix** outcome assigned (Section 8).
4. **Routing:** Not Recommended → record and suggest alternatives; Eligible for Review → reviewer; Requires Approval → approver at `APPROVER_ROLE_[n]` (`Data Gap`).
5. **Human decision** recorded: approved, modified, rejected, with reason.
6. **Execution** occurs outside the Agent, by authorized staff.
7. **Post-hoc review** compares outcomes with expectations, using net results and, where possible, a holdout group.

### 10.2 Required Fields in Every Promotion Recommendation
| Field | Description |
|---|---|
| Recommendation ID | Unique identifier |
| Timestamp | Time of the recommendation |
| Customer ID | As supplied |
| Model version and prediction timestamp | `Data Gap` if not supplied |
| p_lapse, risk tier, value tier, priority band | From model/structured data |
| Flags | RCF, DAF, LHF, Already Lapsed |
| Products and scores | Labeled as scores |
| Matrix outcome and rule path | E-, X-, U-, A- IDs applied |
| Margin check result | Or Data Gap |
| Budget check result | Or Data Gap |
| Non-price actions considered | Recorded |
| Human reviewer and decision | Name/role, date, reason |
| Knowledge Base version | Document names and versions retrieved |
| Limitations | Missing data and assumptions |

### 10.3 Auditability Rules
- **PG-13:** Store the exact inputs and rule IDs used for each recommendation so the decision can be reproduced.
- **PG-14:** Preserve human overrides and reasons.
- **PG-15:** The Agent must not alter or delete audit records.
- **PG-16:** Policy changes must be versioned; each recommendation references the version in force.
- **`Data Gap`** — Retention period for audit records is not specified.

---

## 11. Examples

**All customers and values below are fictional. Placeholders such as `D_MAX_[tier]` have no assigned values. Examples show decision logic, not recommended discount levels.**

### 11.1 Acceptable Recommendations

**Example A — High risk, V2, DAF, data complete**
- **Input:** High risk tier, V2, DAF present, no RCF; stock available; margin data supplied; within budget; no cooldown breach.
- **Outcome:** Eligible for Review.
- **Recommendation:** "Consider a time-limited incentive on the declining category, within `D_MAX_[tier]` once the business sets it. Non-price actions considered: needs conversation and availability priority. Margin check: passed (calculation attached). Requires reviewer confirmation."
- **Why acceptable:** Documented need, targeted, safeguards checked, no invented percentage, human review.

**Example B — High risk, V1, on the Focus List**
- **Outcome:** Requires Approval.
- **Recommendation:** "Draft proposal for approver: senior outreach first; if an incentive is proposed, it is subject to `APPROVER_ROLE_[n]` approval, margin verification, and a budget check."
- **Why acceptable:** Escalation, non-price first, no commitment.

**Example C — Low risk customer**
- **Outcome:** Not Recommended.
- **Recommendation:** "No promotion advised. Maintain routine engagement."
- **Why acceptable:** Avoids unnecessary discounting.

**Example D — High risk, RCF with explained cancellations (supplier stock-out)**
- **Outcome:** Requires Approval (raised one level).
- **Recommendation:** "Cause identified as stock-out, now resolved. Suggest service-recovery contact; any incentive requires approval."
- **Why acceptable:** Addresses root cause and escalates.

### 11.2 Unacceptable Recommendations

| Unacceptable output | Problems | Correct approach |
|---|---|---|
| "Offer this customer 20% off; it will win them back." | Invented percentage; implied guaranteed result; no approval. | State outcome (Requires Approval), reference placeholders, avoid promising results. |
| "Customer is high value, so give a discount." | Value tier alone does not justify a discount; ignores risk and margin. | Apply the full matrix and checks. |
| "Offer a discount on product X" (stock unknown) | Violates PG-5. | Mark availability unconfirmed; require approval. |
| "Offer a discount to a Low risk customer to keep them happy." | Violates X-1 and U-1. | Not Recommended. |
| "This promotion will generate 5,000 in extra profit." | Invented monetary result; revenue/profit/score confusion. | Do not state monetary outcomes without validated evidence and shown calculation. |
| "Send the customer the offer now." | The Agent must not send communications. | Hand to authorized staff after approval. |
| "Company policy allows up to 15% discount." | Treats a proposed/unspecified rule as approved policy. | State that limits are `Data Gap` / proposed. |
| Offering a discount to a customer with unexplained repeated cancellations | Violates X-4. | Review cancellations first. |

---

## 12. Open Decisions for the Business

| ID | Decision needed | Status |
|---|---|---|
| PD-1 | Set `D_MAX_[tier]` per promotion category | `Data Gap` |
| PD-2 | Set `M_MIN` and confirm product cost and margin data availability | `Data Gap` |
| PD-3 | Set `B_PERIOD` and `B_CUSTOMER` | `Data Gap` |
| PD-4 | Set `N_COOLDOWN` | `Data Gap` |
| PD-5 | Name approver roles and levels (`APPROVER_ROLE_[n]`) | `Data Gap` |
| PD-6 | Approve or revise eligibility (E-), exclusion (X-), avoidance (U-), and approval (A-) rules | `Proposed Policy — Requires Business Approval` |
| PD-7 | Confirm which promotion types are offered | `Data Gap` |
| PD-8 | Define audit-record retention | `Data Gap` |
| PD-9 | Define reactivation promotion rules | `Proposed Policy — Requires Business Approval` |
| PD-10 | Plan a holdout-based test of promotion effectiveness | `Pending Validation` |

---

## 13. Questions This Document Can Answer

Use this section to see what to ask the retention agent about promotions. Questions marked **(needs data)** also require customer-specific model output or structured data at run time.

### 13.1 Eligibility and Exclusion
- Is a customer eligible for a promotion? **(needs data)**
- Which customers must be excluded from promotions, and why?
- Why is a Low-risk customer not recommended for a discount?

### 13.2 Decision Outcomes
- What do "Not Recommended", "Eligible for Review" and "Requires Approval" mean?
- What is the outcome for a High-risk customer with a given value tier? **(needs data)**
- How do override rules change the matrix result, and which rule wins when two conflict?

### 13.3 Approval and Audit
- When is human approval mandatory (A-1 to A-13)?
- What steps does an approval follow?
- What must be logged for every promotion recommendation?

### 13.4 Limits, Margins and Budgets
- What discount limit applies? The document does not set one. It says this is a `Data Gap` and lists the placeholders the business must fill.
- How is post-promotion margin checked, and what data is needed?
- How are cooldown periods and budgets enforced?

### 13.5 Cancellations and Availability
- Why is a product on a promotion not recommended when its stock is unknown?
- How do repeated cancellations affect promotion eligibility?
- How do we stop a promotion from encouraging order-and-cancel behavior?

### 13.6 Examples
- Show an acceptable promotion recommendation and an unacceptable one.
- Why is "give a 20% discount to win them back" not an acceptable output?

### 13.7 Not Answerable From This Document
The document cannot state approved discount percentages, margins, budgets, approver names or expected profit from a promotion. These are `Data Gap` items. The agent must say so and must not present proposed rules as company policy.
