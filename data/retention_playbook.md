# Retention Playbook — Retain & Recommend AI

**Project:** Retain & Recommend AI — Returns-Aware Product Recommendation, Customer Lapse Prediction & RAG-Powered Retention Agent
**Document type:** Knowledge Base file 1 of 3 (business guidance for the retention agent)
**Companion files:** `promotion_policy.md` (discount and promotion rules), `business_rules_kpis.md` (definitions, formulas, thresholds, data rules)
**Version:** 1.1 — risk tiers aligned with the supplied scoring file `customer_lapse_predictions.csv` (three tiers: Low, Medium, High).
**Status:** All thresholds other than the source-file tiers are proposals until validated and approved by the business.

---

## 0. How to Use This Document

### 0.1 Purpose
This playbook tells the AI Agent how to reason about customer retention for a wholesale business: which customers to look at first, what kind of action to consider, when to involve a human, and how to describe results honestly.

### 0.2 Evidence Labels
Every passage in the Knowledge Base uses these labels. The AI Agent must preserve them when quoting or paraphrasing.

| Label | Meaning | Agent behavior |
|---|---|---|
| `Verified Fact` | Established definition or statement confirmed by the business or by its data. | May state as fact. |
| `Proposed Assumption` | Reasonable working value or framework chosen by the author, not confirmed. | State as an assumption; never as a confirmed fact. |
| `Proposed Policy — Requires Business Approval` | A rule suggested for the business to adopt. | Never treat as approved policy. Say it is proposed. |
| `Pending Validation` | Value or claim that must be tested on real data before operational use. | Disclose that it is unvalidated. |
| `Data Gap` | Information that is not available in this Knowledge Base. | Say the information is missing; do not invent it. |
| `Human Review Required` | A decision that a person must make or approve. | Stop and escalate. Do not act autonomously. |

### 0.3 Core Principle: Knowledge Base vs. Structured Data
- **`Verified Fact`** — The Knowledge Base supplies *business guidance, definitions, and policy*. It never supplies customer-specific values.
- **`Verified Fact`** — Customer-specific values (lapse probability, risk tier, value tier, recommended products, cancellation probability, purchase history) must come from actual model outputs or structured data supplied at run time.
- **Guardrail G-1:** If a customer-specific value is not present in the supplied model output or structured data, the AI Agent must state "value not available" and must not estimate, infer, or fabricate it.
- **Guardrail G-2:** Examples in this document use illustrative placeholders. They are not real customers, and example numbers are not benchmarks, results, or targets.

### 0.4 Shared Constants Used Across the Knowledge Base
These values are defined in full in `business_rules_kpis.md` (Section 8 and Section 9). They are repeated here so this file can be retrieved independently.

| Constant | Value | Label |
|---|---|---|
| Prediction horizon (H) | 90 days | `Proposed Assumption`, `Pending Validation` |
| Observation window (W_obs) | 180 days before prediction timestamp | `Proposed Assumption`, `Pending Validation` |
| Risk tiers on lapse probability (p_lapse) | Low < 0.30; Medium 0.30 to < 0.50; High ≥ 0.50 | `Verified Fact` for the ranges observed in the supplied scoring file; business meaning `Pending Validation`; valid as probabilities only if p_lapse is calibrated |
| Value tiers on historical net revenue percentile | V1 ≥ 90th percentile; V2 60th to < 90th; V3 < 60th | `Proposed Assumption`, `Pending Validation` |
| Priority bands | P1 (highest) to P4 (lowest), from the matrix in Section 5 | `Proposed Assumption` |
| Focus List | Top N High-risk customers ranked by Priority Score; N set by the business | `Proposed Assumption`; N is a `Data Gap` |

**Source alignment.** The risk tiers come from the scoring file `customer_lapse_predictions.csv` (5,224 customers, one snapshot dated 2011-09-01). The earlier four-tier draft (with a Critical tier) has been retired. Reason: in that file, 77.0% of customers are already High risk, and a Critical cutoff of 0.80 would have placed 2,055 customers (39.3%) in the top tier, which is far more than any team can review. Urgency inside the High tier is now handled by the Focus List (Section 5.5). Full file profile: `business_rules_kpis.md`, Section 4.4.

---

## 1. Customer Lapse and Churn Concepts

### 1.1 Definitions
- **Lapse** — A customer who was active has stopped purchasing for a defined period. In this project, lapse is defined operationally on a time basis (see 1.2).
- **Churn** — A permanent or long-term end of the customer relationship. **`Verified Fact`** — Churn cannot be observed directly in non-contractual wholesale data, because a customer can simply return later. The project therefore predicts **lapse**, not churn.
- **Non-contractual setting** — **`Proposed Assumption`** — The wholesale customers are not bound by subscriptions, so no formal cancellation event marks the end of the relationship. Confirm with the business.
- **Active customer** — A customer with at least one valid purchase in the observation window ending at the prediction timestamp.
- **Lapsed customer (observed)** — **`Proposed Assumption`** — A customer with zero valid purchases in the 90 days after a prediction timestamp (the label used to train the model) or, for current operations, zero valid purchases in the most recent 90 days.
- **Predicted lapse risk** — The model's estimated probability (p_lapse, between 0 and 1) that an active customer will make zero valid purchases in the next 90 days.

### 1.2 Lapse vs. Churn vs. Cancellation (do not confuse)
| Term | What it describes | Where it is measured |
|---|---|---|
| Lapse | Absence of valid purchases over the horizon | Customer level |
| Churn | Permanent departure | Not directly observable |
| Cancellation | A cancelled order or invoice | Transaction level |
| Return | Goods sent back after delivery | Transaction level, if recorded separately |

- **`Data Gap`** — Whether the source data distinguishes returns from order cancellations is unconfirmed. Until confirmed, the Agent must use the term "cancellation" only for records the data flags as cancellations and must not describe them as customer dissatisfaction.

### 1.3 Why Lapse Matters in Wholesale
- **`Proposed Assumption`** — Wholesale revenue is concentrated in a minority of customers, so losing a few high-value accounts may affect revenue disproportionately. This must be verified with the business's actual revenue concentration (see `business_rules_kpis.md`, Section 12).
- Wholesale purchasing is often irregular or seasonal. A long gap is not always a warning sign; it may be a normal buying cycle. The Agent must compare a customer's current gap against that customer's own typical purchase interval, when available.

### 1.4 Warning Signals (Behavioral Indicators)
Signals the Agent may reference **only if present in the structured data**:
- Increasing days since last purchase (recency) relative to the customer's usual inter-purchase interval.
- Falling purchase frequency versus the previous period.
- Falling order value or net revenue versus the previous period.
- Narrowing product variety.
- Rising cancellation count or cancellation rate.
- Shift from regular to sporadic purchasing.

**Guardrail G-3:** These signals are associations used by the model, not proven causes of lapse. The Agent must not claim that a signal *causes* lapse.

---

## 2. Customer Risk Segmentation

### 2.1 Risk Tiers
**`Verified Fact`** — The scoring file assigns each customer to one of three categories in the column `risk_category`. The observed ranges of `lapse_probability` in the file are: Low up to 0.2977, Medium 0.3001 to 0.4987, High 0.5005 and above. The implied cut points are 0.30 and 0.50. The exact boundary convention (inclusive or exclusive) is a `Data Gap` to confirm with the model owner.

| Risk tier | p_lapse range | Customers in the supplied file (snapshot 2011-09-01) | Plain-language meaning | Typical stance |
|---|---|---|---|---|
| Low | < 0.30 | 657 (12.6%) | Model sees continued purchasing as likely. | Maintain; no intervention needed. |
| Medium | 0.30 to < 0.50 | 548 (10.5%) | Meaningful uncertainty; early signs may be present. | Monitor and light-touch engagement. |
| High | ≥ 0.50 | 4,019 (77.0%) | Lapse is more likely than not, according to the model. | Active, personalized outreach, prioritized by the Focus List. |

- **`Pending Validation`** — The meaning "more likely than not" holds only if p_lapse is calibrated. If calibration is not confirmed, treat the tiers as a ranking aid and say so.
- **`Verified Fact`** — The High tier is very large in the supplied file, so the tier alone cannot decide who to contact first. Use the priority band and Focus List (Section 5).

### 2.2 Interpretation Rules
- A risk tier is a **model-based estimate**, not a fact about the customer's intention.
- A p_lapse of 0.70 means the model assigns a 70% estimated chance under its assumptions, if calibrated. It does **not** mean the customer will lapse, and it is **not** a monetary amount.
- **Guardrail G-4:** The Agent must always report the tier together with its source (model name or version, prediction timestamp). **`Data Gap`** — model name and version are not specified in this Knowledge Base.

### 2.3 Special Flags (Overlay on Risk Tier)
Flags are evaluated from structured data. Definitions and thresholds are in `business_rules_kpis.md`, Section 9.4.

| Flag | Short definition | Label |
|---|---|---|
| Repeated Cancellation Flag (RCF) | ≥ 3 cancellations in W_obs, or value-based cancellation rate ≥ 0.20 with ≥ 3 invoices | `Proposed Assumption`, `Pending Validation` |
| Declining Activity Flag (DAF) | Purchase count or net revenue in last 90 days < 50% of the previous 90 days, with ≥ 2 purchases in the previous 90 days | `Proposed Assumption`, `Pending Validation` |
| Limited History Flag (LHF) | Only 1 valid purchase in W_obs | `Proposed Assumption` |
| Already Lapsed | No valid purchase in the most recent 90 days | `Proposed Assumption` |

Already Lapsed customers are **outside** the primary prediction population (which is active customers). They are handled by reactivation guidance (Section 3.5).

---

## 3. Recommended Actions by Customer Segment

All actions below are **recommendations for human decision-makers**. They are `Proposed Policy — Requires Business Approval`. Any action involving a discount follows `promotion_policy.md`.

### 3.1 Low Risk
- **Goal:** Preserve the relationship efficiently.
- **Recommended actions:** Standard communication; routine account contact; relevant product suggestions based on purchase history.
- **Avoid:** Discounts, special offers, or heavy outreach. See `promotion_policy.md`, Section 6 (avoiding unnecessary discounts).

### 3.2 Medium Risk
- **Goal:** Detect and address early drift.
- **Recommended actions:** Check-in message or call; product recommendations tied to previously purchased categories; confirm that service or availability issues are not present.
- **Escalate if:** Medium risk is combined with RCF, DAF, or V1 value tier. See Section 8.

### 3.3 High Risk
- **Goal:** Re-engage before lapse occurs.
- **Recommended actions:** Personal outreach by an account owner; tailored product recommendations (Section 6); service-recovery conversation if cancellations are present; consider a non-discount incentive first (for example, priority availability, flexible ordering support) before any price-based offer.
- **Promotion:** Eligible for **review** only. See `promotion_policy.md`, Section 8.

### 3.4 High Risk — Focus List (Highest Urgency)
- **Definition:** High-risk customers who rank in the top N by Priority Score (Section 5.5), including all P1 customers. N is set by the business (`Data Gap`).
- **Goal:** Intervene early, with human ownership, where urgency and business importance are greatest.
- **Recommended actions:** **`Human Review Required`** for the action plan; direct contact by a senior account owner; root-cause conversation; tailored recommendation list; any incentive must go through approval.
- **Guardrail G-5:** The Agent may draft a retention strategy but must not send communications or commit to terms.

### 3.5 Already Lapsed (Reactivation)
- **Goal:** Win back a customer with no valid purchase in the last 90 days.
- **Recommended actions:** Reactivation message referencing previously purchased categories; confirm the relationship status with the account owner; avoid assuming the customer is lost permanently.
- **`Data Gap`** — The point at which a lapsed customer is treated as permanently lost (for example, 12 months) is not specified. **`Proposed Assumption`** — Use a business-defined cutoff; confirm before use.
- **Evaluation caution:** Reactivation outcomes must be compared with a control group to avoid crediting normal returning behavior to the campaign (Section 11).

### 3.6 New and Limited-History Customers
- **Goal:** Build a purchasing habit.
- **Guidance:** With few observations, model estimates are less reliable. The Agent must flag low confidence when the Limited History Flag is present, and must not over-interpret p_lapse.

---

## 4. Handling Repeated Cancellations and Declining Activity

### 4.1 Repeated Cancellations
**`Verified Fact`** — Cancellations may reflect many causes: stock-outs, pricing errors, ordering mistakes, delivery problems, customer cash-flow issues, or internal data practices.

**Guardrail G-6:** The Agent must not assume that cancellations indicate dissatisfaction, and must not blame the customer.

Recommended handling when the RCF is present:
1. **Diagnose before acting.** **`Human Review Required`** — An account owner should review the cancelled orders and their reasons. **`Data Gap`** — cancellation reason codes are not confirmed.
2. **Check operational causes.** Availability, lead time, pricing errors, and picking or delivery problems.
3. **Prefer service recovery over discounts.** A discount does not fix an availability or ordering-process problem.
4. **Adjust recommendations.** Down-rank products with a high estimated cancellation risk for that customer (Section 6.3).
5. **Do not reward cancellation behavior.** Do not offer a promotion whose main effect would be to encourage repeated order-and-cancel cycles (see `promotion_policy.md`, Section 5).

### 4.2 Declining Purchase Activity
When the DAF is present:
1. Compare the customer's recent gap with their own historical rhythm; seasonality may explain the decline.
2. Look at which categories declined. A fall in one category may indicate a competitor win or a stock issue.
3. Recommend outreach that asks about needs, not only offers.
4. Escalate when the DAF is combined with a V1 or V2 value tier and High risk.

### 4.3 Both Flags Together (RCF + DAF)
- **`Human Review Required`** — mandatory. Treat as a priority account review, because instability and falling activity together indicate a possible service or relationship problem.

### 4.4 Interaction Summary
| Situation | Suggested primary lever | Promotion stance |
|---|---|---|
| High risk, no flags | Personal outreach + relevant products | Eligible for review |
| High risk + RCF | Service recovery, root-cause review | Requires approval; discount not the first lever |
| High risk + DAF | Needs conversation, category review | Eligible for review |
| Focus List + RCF + DAF | Senior account review | Requires approval |
| Low risk + RCF | Operational review only | Not recommended |

---

## 5. Customer Prioritization

### 5.1 Principle
Prioritization must combine **how likely** a customer is to lapse with **how much the customer matters to the business**. Reviewing only high-risk customers wastes effort on low-value accounts; reviewing only high-value customers ignores urgency.

### 5.2 Value Tiers
**`Proposed Assumption`**, **`Pending Validation`** — based on historical net revenue in W_obs (percentile among active customers).

| Value tier | Rule |
|---|---|
| V1 (High value) | ≥ 90th percentile |
| V2 (Mid value) | 60th to < 90th percentile |
| V3 (Lower value) | < 60th percentile |

**Limitation:** Historical net revenue is neither profit nor future value (see `business_rules_kpis.md`, Section 14). **`Data Gap`** — customer-level margin data is not confirmed.

### 5.3 Priority Matrix
**`Proposed Assumption`**, **`Pending Validation`**

| Risk tier \ Value tier | V1 | V2 | V3 |
|---|---|---|---|
| High | P1 | P2 | P3 |
| Medium | P2 | P3 | P4 |
| Low | P3 | P4 | P4 |

| Priority | Interpretation | Expected handling |
|---|---|---|
| P1 | High urgency, high importance | Immediate human-owned review |
| P2 | Important or urgent | Review within the next planning cycle |
| P3 | Moderate | Light-touch or batched outreach |
| P4 | Low | Monitor; automated standard communication only |

### 5.4 Ordering Within a Band
Within a priority band, the Agent may order customers by the dimensionless Priority Score:

```
Priority Score = p_lapse × V_norm
```
- `p_lapse` — model probability, 0 to 1.
- `V_norm` — percentile rank of the customer's historical net revenue in W_obs, scaled to (0, 1].
- **Unit:** none. **Guardrail G-7:** Priority Score is a ranking aid. It is not a monetary amount, a probability, or an expected loss.

### 5.5 Focus List (Replaces the Former Critical Tier)
**`Proposed Assumption`** — Because the High tier holds most customers in the supplied file, band assignment alone does not limit workload. The Focus List is the practical review queue:

```
Focus List = the N High-risk customers with the highest Priority Score
```
- **N** is the business's review capacity per cycle. **`Data Gap`** — N is not specified. The Agent must not assume a value.
- **Input dependency:** Priority Score needs a value measure (`V_norm`), which is not in the scoring file. Until value data is joined by `customer_id`, the Agent may only order High-risk customers by `p_lapse` and must state that business value was not considered.
- **Ties:** Break ties by higher `V_norm`, then by higher p_lapse, then by `customer_id` for reproducibility.

---

## 6. Product Recommendation Considerations

### 6.1 Purpose in Retention
Relevant recommendations reduce the effort for a customer to place the next order. They are a **retention support tool**, not a guarantee of purchase.

### 6.2 Inputs the Agent May Use
Only from supplied structured data or model output:
- Predicted purchase likelihood (p_buy) per customer and product.
- Predicted cancellation risk (p_cancel) per customer and product, or per product if customer-level is unavailable.
- Product availability and stock status.
- Product business value indicator (revenue or margin proxy, if available).

### 6.3 Returns-Aware (Cancellation-Aware) Ranking
The project uses cancellation risk to avoid recommending items likely to be ordered and then cancelled. The ranking logic is defined in `business_rules_kpis.md`, Section 10:

```
Adjusted Recommendation Score = p_buy × (1 − p_cancel) × Value_norm × Availability_flag
```
- All components are unitless; the result is a ranking score, not a monetary amount.
- **`Pending Validation`** — The multiplicative form is a proposed design.

### 6.4 Recommendation Guardrails
- **Guardrail G-8:** Do not recommend products flagged unavailable, discontinued, or restricted.
- **Guardrail G-9:** Do not recommend a product on the basis of a discount unless the promotion was approved under `promotion_policy.md`.
- **Guardrail G-10:** Explain recommendations using only the signals actually supplied (for example, "previously purchased in this category"). Do not invent reasons.
- **Guardrail G-11:** A recommendation list is a suggestion for a human-reviewed conversation. It is not a commitment of stock or price.

### 6.5 Diversity and Fatigue
**`Proposed Assumption`** — Offering a few relevant products is generally preferable to a long list. The Agent should keep lists short and relevant. The ideal list length is `Data Gap`.

---

## 7. Personalized Retention Strategies

### 7.1 Strategy Building Blocks
| Block | Use when | Needs |
|---|---|---|
| Relationship contact | Any High risk | Account owner assignment (`Data Gap` if absent) |
| Product recommendations | Narrowing variety or declining activity | Recommendation model output |
| Service recovery | RCF present | Cancellation detail |
| Replenishment reminder | Customer has a regular reorder cycle | Purchase interval data |
| Availability priority | Customer affected by stock issues | Stock data |
| Promotion (review) | Only after non-price levers considered | Approval per `promotion_policy.md` |

### 7.2 Personalization Rules
- Base every strategy on supplied customer data. Cite which fields drove it.
- Match tone and offering to the customer's value tier and purchasing history.
- Prefer the **least costly effective action** first: contact before incentive, incentive before discount.
- State uncertainty: any strategy is a hypothesis about what may help.

### 7.3 Required Content of an Agent-Generated Retention Strategy
Each strategy output must contain:
1. Customer identifier (as supplied).
2. Risk tier, p_lapse, prediction timestamp, source (model/version if available).
3. Value tier and priority band.
4. Active flags (RCF, DAF, LHF).
5. Key signals used (from data only).
6. Recommended action(s) and rationale, citing the playbook section.
7. Product suggestions (if available) with scores labeled as scores.
8. Promotion stance per `promotion_policy.md` (Not Recommended, Eligible for Review, or Requires Approval).
9. Human-review status.
10. Limitations and missing data.

---

## 8. Recommended Agent Decision Workflow

### 8.1 Step-by-Step Workflow
1. **Receive input.** Confirm that structured data and model outputs for the customer are present. If not, state which values are missing and stop (Guardrail G-1).
2. **Validate data quality.** Check for missing prediction timestamp, missing p_lapse, or out-of-range values. If invalid, flag a **Data Gap** and escalate.
3. **Identify the segment.** Assign the risk tier, value tier, and flags using the rules in this Knowledge Base.
4. **Determine priority.** Look up the band in Section 5.3.
5. **Retrieve guidance.** Retrieve the relevant segment actions (Section 3) and flag handling (Section 4).
6. **Assess recommendations.** Use model-provided product scores and apply the availability and cancellation guardrails.
7. **Assess promotion stance.** Apply `promotion_policy.md` decision matrix. Default to **Not Recommended** when information is incomplete.
8. **Check human-review triggers.** Apply Section 9.
9. **Generate the output** with the content required in 7.3.
10. **Log for audit** (see `promotion_policy.md`, Section 9, and `business_rules_kpis.md`, Section 16).

### 8.2 Decision Sketch
```
Data complete?  -- no --> state Data Gap, stop
      |
     yes
      v
Assign risk tier, value tier, flags -> priority band
      |
Any human-review trigger? -- yes --> mark Human Review Required
      |
Recommend actions (non-price levers first)
      |
Promotion stance via promotion_policy.md
      |
Generate structured output + audit record
```

### 8.3 Default Behaviors When Information Is Missing
| Missing item | Agent behavior |
|---|---|
| p_lapse | Do not assign a risk tier. Report Data Gap. |
| Value tier inputs | Assign "value unknown"; do not default to V3. Escalate for priority decisions. |
| Cancellation data | Skip RCF assessment and say it was not evaluated. |
| Margin data | Do not claim profitability. |
| Stock data | Do not recommend as available; mark "availability unconfirmed". |

---

## 9. Human Review and Escalation

### 9.1 Mandatory Human Review Triggers
**`Human Review Required`** for any of the following. **`Proposed Policy — Requires Business Approval`** (the list itself).

| ID | Trigger |
|---|---|
| HR-1 | Priority band P1. |
| HR-2 | Customer is on the Focus List (Section 5.5). |
| HR-3 | Customer has both RCF and DAF. |
| HR-4 | Any proposed promotion, discount, credit, or price concession. |
| HR-5 | Missing or invalid model output for a customer that appears to be high-value by other data. |
| HR-6 | Conflicting signals (for example, Low risk tier with a sharp recent drop in activity). |
| HR-7 | Customer-specific sensitive circumstances: disputes, legal, credit issues, complaints (if recorded). |
| HR-8 | Any request that would change customer terms, credit, or contracts. |
| HR-9 | Limited History Flag with a V1 classification (likely data artefact or a new large account). |
| HR-10 | Agent confidence is low because input data failed quality checks. |

### 9.2 What the Agent Must Not Do Autonomously
- Send customer communications.
- Offer or confirm discounts, credits, rebates, or special terms.
- Alter pricing, credit limits, or payment terms.
- Categorize a customer as "lost" or "not worth retaining".
- Make claims about a customer's motives.

### 9.3 Escalation Content
When escalating, the Agent must provide the customer's tier, priority, flags, the trigger ID, key supporting data, and the specific decision needed.

---

## 10. Retention KPI Interpretation and Limitations

KPI definitions and formulas are in `business_rules_kpis.md`, Sections 11 to 13. This section covers interpretation.

### 10.1 How to Read Retention KPIs
| KPI | Reading guidance | Common misreading |
|---|---|---|
| Retention rate | Share of a baseline cohort active in a later period. | Treating it as the effect of the program. |
| Lapse rate | Share of a cohort with no purchase over the horizon. | Treating lapse as permanent loss. |
| Reactivation rate | Share of lapsed customers who purchased again. | Crediting all reactivations to a campaign. |
| Cancellation rate | Share of orders (or value) cancelled. | Assuming cancellations indicate poor customer attitude. |
| Net revenue of retained customers | Revenue from customers who stayed. | Treating it as profit. |

### 10.2 Evaluation Limitations
- **Correlation is not causation.** **`Verified Fact`** — Observed changes after an action do not prove the action caused them.
- **Selection bias.** Customers chosen for outreach are chosen because they are high-risk; comparing them with low-risk customers is misleading.
- **Regression to the mean.** Customers with extreme short-term drops may recover without intervention.
- **Seasonality.** Wholesale cycles can mimic lapse or recovery.
- **Small numbers.** Rates from small groups are unstable; state group sizes.
- **Censoring.** Recent cohorts have not completed the full horizon, so their outcomes are incomplete.
- **No experiment yet.** **`Data Gap`** — No controlled retention experiment is described in this Knowledge Base. Any claimed "uplift" is `Pending Validation` until measured against a holdout group.

### 10.3 Language the Agent Must Use
- Say "associated with" or "the model indicates", not "caused by".
- Say "estimated" for any model output.
- Do not state expected savings or retained revenue as confirmed results.

---

## 11. Practical Examples

**All customers and numbers below are fictional placeholders for illustration. They are not real data, benchmarks, or results.**

### Example 1 — High Risk, High Value, On the Focus List
- **Input (illustrative):** p_lapse = 0.86, High tier; V1; no RCF/DAF; ranks inside the top N.
- **Priority:** P1.
- **Reasoning:** High risk and top-tier value (Section 5.3); high Priority Score places the customer on the Focus List (Section 5.5).
- **Actions:** `Human Review Required` (HR-1, HR-2). Senior account owner contacts the customer to understand needs; Agent prepares a short, availability-checked product list.
- **Promotion stance:** Requires approval (see `promotion_policy.md`). Non-price levers are tried first.
- **Why this is good:** Action matches urgency, avoids automatic discounting, and keeps a human in the loop.

### Example 2 — High Risk, Mid Value, Repeated Cancellations
- **Input (illustrative):** p_lapse = 0.68, High; V2; RCF present.
- **Priority:** P2.
- **Reasoning:** RCF suggests a service or process issue (Section 4.1).
- **Actions:** Account owner reviews the cancelled orders; Agent down-ranks high-cancellation-risk products and recommends products with lower estimated cancellation risk.
- **Promotion stance:** Requires approval; discount is not the first lever.
- **Why this is good:** It addresses a possible root cause rather than trading price for loyalty.

### Example 3 — Medium Risk, Low Value
- **Input (illustrative):** p_lapse = 0.41, Medium; V3.
- **Priority:** P4.
- **Actions:** Standard automated engagement; relevant product suggestions; no personal outreach.
- **Promotion stance:** Not recommended.
- **Why this is good:** It reserves scarce review capacity for higher priorities.

### Example 4 — Low Risk With Sudden Activity Drop (Conflict)
- **Input (illustrative):** p_lapse = 0.22, Low; V1; DAF present.
- **Reasoning:** The model and the observed drop disagree (HR-6).
- **Actions:** `Human Review Required`; check data timing and seasonality; do not dismiss the drop because the tier is Low.
- **Why this is good:** It treats the conflict as a reason for review rather than hiding it.

### Example 5 — Missing Model Output
- **Input:** No p_lapse supplied.
- **Agent response:** "The lapse probability for this customer is not available, so I cannot assign a risk tier or priority. Please supply the model output or check the pipeline."
- **Why this is good:** It never fabricates a score (Guardrail G-1).

### Example 6 — Unacceptable Agent Output (Counterexample)
- **Output:** "This customer will lapse next month and a 15% discount will recover about 4,000 in revenue."
- **Problems:** States a prediction as certainty; invents a discount percentage (proposed rules are unapproved); invents a monetary result; no data source.
- **Correct form:** "The model estimates a lapse probability of [p_lapse] for the next 90 days (source: [model, timestamp]). A promotion, if considered, requires review under the promotion policy. No monetary outcome can be stated without validated evidence."

---

## 12. Open Decisions for the Business

| ID | Decision needed | Status |
|---|---|---|
| OD-1 | Confirm lapse definition, H, and W_obs | `Pending Validation` |
| OD-2 | Confirm risk-tier thresholds and whether p_lapse is calibrated | `Pending Validation` |
| OD-3 | Confirm value-tier cutoffs and whether profit data is available | `Data Gap` |
| OD-4 | Confirm review capacity and ownership model (account owner assignment) | `Data Gap` |
| OD-5 | Confirm whether returns and cancellations are distinguishable | `Data Gap` |
| OD-6 | Approve human-review triggers (HR-1 to HR-10) | `Proposed Policy — Requires Business Approval` |
| OD-7 | Define the cutoff for treating a lapsed customer as lost | `Data Gap` |
| OD-8 | Design a holdout-based evaluation for retention actions | `Pending Validation` |

---

## 13. Questions This Document Can Answer

Use this section to see what to ask the retention agent about this file. Each question is answered from the guidance above. Questions marked **(needs data)** also require customer-specific model output or structured data at run time.

### 13.1 Concepts
- What is the difference between lapse, churn and cancellation?
- Why does this project predict lapse and not churn?
- What warning signs of lapse can the agent look at, and what can it not claim about them?

### 13.2 Risk Segments
- What do Low, Medium and High risk mean, and where do the cut points come from?
- Why is there no Critical tier, and how is urgency handled inside the High tier?
- How should p_lapse be interpreted, and when should it not be trusted as a probability?

### 13.3 Actions and Strategy
- What should we do for a Low, Medium or High risk customer?
- What is the Focus List and who is on it? **(needs data)**
- When should a non-discount action come before a promotion?
- How do I handle a customer who was already lapsed?

### 13.4 Prioritization
- How do risk tier and value tier combine into P1 to P4?
- In what order should I contact High-risk customers when I have limited capacity?
- What is Priority Score and what can it not tell me?

### 13.5 Cancellations and Declining Activity
- What should we do for a customer with repeated cancellations?
- What does the Declining Activity Flag mean and how should I respond?
- What if a customer has both flags?

### 13.6 Recommendations
- Which products should not be recommended to a customer?
- How does cancellation risk affect product recommendations?

### 13.7 Workflow and Escalation
- What steps does the agent follow for a customer?
- When must a human review the decision (HR-1 to HR-10)?
- What must the agent never do on its own?
- What happens if a model output is missing?

### 13.8 KPIs and Limitations
- How do I read retention rate, lapse rate and reactivation rate?
- Why can't we say the retention program caused an improvement?
- Which evaluation limitations should I mention in a report?

### 13.9 Not Answerable From This Document
These need actual data, not the Knowledge Base: a specific customer's p_lapse or tier, the number of customers in a segment today, a customer's product list, expected revenue saved, or the right discount amount (see `promotion_policy.md`). The agent must say the data is unavailable rather than invent it.
