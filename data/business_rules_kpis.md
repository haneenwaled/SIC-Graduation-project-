# Business Rules and KPIs — Retain & Recommend AI

**Project:** Retain & Recommend AI — Returns-Aware Product Recommendation, Customer Lapse Prediction & RAG-Powered Retention Agent
**Document type:** Knowledge Base file 3 of 3 (business and analytics reference)
**Companion files:** `retention_playbook.md` (retention actions), `promotion_policy.md` (promotion rules)
**Version:** 1.1 — risk tiers and data dictionary aligned with the supplied scoring file `customer_lapse_predictions.csv`

---

## 1. Purpose, Reading Rules, and Evidence Labels

### 1.1 Purpose
This document is the reference for definitions, data rules, formulas, thresholds, evaluation methods, and traceability used by the project. The AI Agent uses it to explain what a metric means, how it is calculated, what it can and cannot show, and which data it needs.

### 1.2 Evidence Labels
| Label | Meaning |
|---|---|
| `Verified Fact` | Established definition or confirmed statement. |
| `Proposed Assumption` | Working choice by the author; not confirmed. |
| `Proposed Policy — Requires Business Approval` | Suggested rule; not approved. |
| `Pending Validation` | Must be tested on real data before operational use. |
| `Data Gap` | Information not available in the Knowledge Base. |
| `Human Review Required` | A person must decide or approve. |

### 1.3 Ground Rules
- **Rule R-1:** This document defines *how* to compute and interpret things. It contains **no** actual customer data, model results, or performance figures. **`Verified Fact`** — none were supplied.
- **Rule R-2:** The dataset schema is not confirmed. Field names in Section 4 are a **template** (`Data Gap` until mapped to the real source).
- **Rule R-3:** Model scores (probabilities, ranking scores, priority scores) are **never** monetary amounts.
- **Rule R-4:** Customer-specific values used by the AI Agent must come from model outputs or structured data, never from this document.
- **Rule R-5:** All numeric thresholds in this document are `Proposed Assumption` and `Pending Validation` unless marked otherwise.

---

## 2. Business Terminology

| Term | Definition |
|---|---|
| Wholesale customer | A business that buys products in bulk for resale or business use. **`Proposed Assumption`** — customers are identified by a customer identifier. |
| Customer ID | Unique identifier of a customer. **`Data Gap`** — handling of transactions without a customer ID is unconfirmed (Section 5). |
| Invoice / Order | A record of a purchase transaction containing one or more line items. |
| Line item | One product row within an invoice, with quantity and unit price. |
| Valid purchase | A line or invoice that counts as a completed sale after applying data quality rules (Section 5). |
| Cancellation | A transaction that reverses or voids an order. |
| Return | Goods sent back after delivery. **`Data Gap`** — may or may not be separated from cancellations in the source. |
| Gross revenue | Sales value before subtracting cancellations or returns. |
| Net revenue | Gross revenue minus the value of cancellations and returns. |
| Profit | Revenue minus costs. **`Data Gap`** — cost data not confirmed. |
| Customer value | A measure of a customer's importance. In this project, a **historical** value (net revenue) used for tiering, not a forecast of future profit. |
| Lapse | A customer's absence of valid purchases over the prediction horizon (Section 8). |
| Churn | Permanent end of relationship; not directly observable here. |
| Retention | A customer remaining active over a period. |
| Prediction timestamp (T) | The date and time at which the model's inputs are frozen and a prediction is made. |
| Observation window (W_obs) | The period before T from which features are computed. |
| Prediction horizon (H) | The period after T over which the outcome is observed. |
| Risk tier | Category (Low, Medium, High) derived from p_lapse; supplied as `risk_category` in the scoring file. |
| Value tier | Category (V1, V2, V3) derived from historical net revenue percentile. |
| Priority band | P1 to P4, from risk tier and value tier. |
| Focus List | The top N High-risk customers ranked by Priority Score. N is set by the business (`Data Gap`). |
| Snapshot date | The date of the scoring run in the file; treated as the prediction timestamp T (`Proposed Assumption`). |
| p_lapse | Model-estimated probability of lapse in H, range 0 to 1. |
| p_buy | Model-estimated purchase likelihood for a customer-product pair. |
| p_cancel | Model-estimated cancellation likelihood for a customer-product pair (or product-level). |
| Score | A model or ranking output with no inherent currency unit. |

---

## 3. Core Business Concepts

### 3.1 Customer
- Unit of analysis for lapse prediction and retention.
- **Active customer:** at least one valid purchase in W_obs ending at T.
- **Already Lapsed customer:** no valid purchase in the most recent 90 days as of T. `Proposed Assumption`.
- **Limited History:** exactly one valid purchase in W_obs.

### 3.2 Transaction
A transaction is an invoice with a timestamp, a customer, and one or more line items. A purchase transaction increases sales; a cancellation or return transaction reduces net sales.

### 3.3 Product
An item with an identifier and (ideally) a description, category, price, cost, and stock status. **`Data Gap`** — product category hierarchy, cost, and stock fields are unconfirmed.

### 3.4 Purchase
A valid completed sale after exclusion of cancellations, returns, test records, and other non-sales (Section 5).

### 3.5 Return vs. Cancellation
| Concept | Timing | Effect |
|---|---|---|
| Cancellation | Order is voided, often before or around fulfillment | Reduces net revenue; may lower fulfilment |
| Return | Goods come back after delivery | Reduces net revenue; may incur handling costs |

**`Data Gap`** — If the source does not distinguish them, treat both as "Cancellation/Return Events" and label results accordingly. The Agent must not state a cause for either.

### 3.6 Cancellation Risk
The estimated likelihood that an order line for a customer-product pair is later cancelled or returned. It is used to down-rank recommendations (Section 10). It is a model output, not a fact about customer intent.

---

## 4. Data Dictionary Template

**`Data Gap`** — The real schema is not provided. The table below is a **generic transactional template** to be mapped to the actual source. Do not assume these names exist. Fields marked "Required" are needed for the core use cases.

### 4.1 Transaction-Level Fields
| Template field | Type | Definition | Unit | Required | Notes |
|---|---|---|---|---|---|
| `invoice_id` | string | Unique transaction identifier | — | Yes | Cancellation indicator convention `Data Gap` |
| `line_id` | string | Line item identifier | — | Optional | |
| `customer_id` | string | Customer identifier | — | Yes | Missing values handled per Section 5 |
| `product_id` | string | Product identifier | — | Yes | |
| `invoice_timestamp` | datetime | Date/time of transaction | UTC or local, `Data Gap` | Yes | Timezone to be confirmed |
| `quantity` | integer | Units on the line | units | Yes | Negative values may indicate cancellations/returns, `Data Gap` |
| `unit_price` | decimal | Price per unit | currency, `Data Gap` | Yes | |
| `currency` | string | Currency code | — | If multiple | Currency conversion rules `Data Gap` |
| `is_cancellation` | boolean | Cancellation/return indicator | — | Yes | Derived or supplied |
| `country` | string | Customer or ship-to country | — | Optional | |
| `discount_amount` | decimal | Discount applied | currency | Optional | Needed for promotion analysis |
| `unit_cost` | decimal | Product cost per unit | currency | Optional | Needed for profit/margin |
| `stock_status` | string | Availability flag | — | Optional | Needed for availability rule |

### 4.2 Derived Fields
| Derived field | Formula | Unit |
|---|---|---|
| `line_value` | `quantity × unit_price` | currency |
| `invoice_value` | sum of `line_value` over lines in an invoice | currency |
| `recency_days` | `T − last valid purchase timestamp` | days |
| `frequency_W` | count of distinct valid purchase invoices in W | count |
| `monetary_W` | sum of net revenue in W | currency |

### 4.3 Model Output Fields (Template)
| Field | Definition | Range/Unit |
|---|---|---|
| `p_lapse` | Estimated probability of lapse in H | 0 to 1 |
| `p_buy` | Estimated purchase likelihood (customer-product) | 0 to 1 |
| `p_cancel` | Estimated cancellation likelihood | 0 to 1 |
| `risk_tier` | Tier from p_lapse (source column `risk_category`) | Low/Medium/High |
| `value_tier` | Tier from historical net revenue | V1/V2/V3 |
| `priority_band` | From matrix | P1 to P4 |
| `prediction_timestamp` | T | datetime |
| `model_version` | Model identifier | `Data Gap` |

### 4.4 Verified Source File: `customer_lapse_predictions.csv`
**`Verified Fact`** — The following was profiled directly from the supplied file.

| File column | Type | Meaning | Maps to template field | Observed |
|---|---|---|---|---|
| `customer_id` | integer | Customer identifier | `customer_id` | 5,224 unique values, none missing |
| `snapshot_date` | date (text) | Date of the scoring run | `prediction_timestamp` (`Proposed Assumption`: snapshot date equals T) | One value only: 2011-09-01 |
| `lapse_probability` | decimal | Model-estimated probability of lapse | `p_lapse` | Min about 0.00000002, max 0.9996, mean 0.664, median 0.743 |
| `risk_category` | text | Risk tier | `risk_tier` | Low 657 (12.6%), Medium 548 (10.5%), High 4,019 (77.0%) |

**Integrity checks (Verified Fact):** 5,224 rows; 5,224 unique customers; no missing values; no duplicate customer and date pairs; every `risk_category` matches the observed ranges (Low up to 0.2977, Medium 0.3001 to 0.4987, High 0.5005 and above).

**Not present in the file (`Data Gap`):** `model_version`, prediction horizon, observation window, actual outcome label, net revenue or value tier, cancellation fields, `p_buy`, `p_cancel`, product and stock fields, and any ranking field.

**Consequences for the AI Agent:**
- **SF-1:** Always report the snapshot date (2011-09-01) with any customer-specific statement, and do not describe the data as current.
- **SF-2:** Priority band, flags, Focus List and recommendations cannot be produced until the missing fields are supplied and joined by `customer_id`. Otherwise state the Data Gap.
- **SF-3:** Model performance cannot be evaluated from this file. It has one snapshot and no outcome column (see Section 15).
- **SF-4:** Calibration is unverified (`Pending Validation`). A mean predicted lapse probability of 0.664 would imply that about two thirds of scored customers lapse if the model were calibrated. Whether that matches reality is unknown.
- **SF-5:** Whether the file contains only Active customers (Section 7) is a `Data Gap`.
- **SF-6:** If `risk_category` does not match the ranges above for any row, flag it (`HR-10`) and do not use that row.

---

## 5. Data Quality Rules

`Proposed Policy — Requires Business Approval` unless stated. Each rule should be confirmed against the real data.

| ID | Rule | Rationale |
|---|---|---|
| DQ-1 | Exclude records without `customer_id` from customer-level modeling; report their share. | Cannot attribute to a customer. |
| DQ-2 | Identify cancellation/return records using the confirmed convention; do not count them as purchases. | Avoid overstating sales. |
| DQ-3 | Exclude non-product lines (for example postage, fees, manual adjustments, samples, test entries) once identified. `Data Gap` — list of such codes unknown. | Not genuine product demand. |
| DQ-4 | Review zero or negative unit prices; exclude or treat per business rule. | Errors or adjustments. |
| DQ-5 | Handle duplicates: remove exact duplicate rows after confirming they are not legitimate repeats. | Avoid double counting. |
| DQ-6 | Check date validity: no future dates, consistent timezone. | Time logic integrity. |
| DQ-7 | Review extreme quantities/values (outliers) before capping; document any treatment. | Avoid distortion; may be real wholesale bulk. |
| DQ-8 | Reconcile cancellations to original orders where possible; record unmatched cancellations. | Cancellation accuracy. |
| DQ-9 | Standardize currency if multiple currencies exist. `Data Gap`. | Comparable values. |
| DQ-10 | Do not impute customer-level values silently; record missingness. | Transparency. |

### 5.1 Preprocessing Rules
1. Build a cleaned transaction table with a `valid_purchase` flag and an `is_cancellation` flag.
2. Aggregate per customer within W_obs relative to T, using only records with timestamp ≤ T (Section 15.3).
3. Retain a data-quality log: counts of records removed per rule.
4. Keep raw data unchanged; apply cleaning in a reproducible step.

### 5.2 Data Quality Reporting
The Agent should mention material data-quality limitations when they affect a result (for example, large share of missing customer IDs).

---

## 6. Calculation Conventions

- **Time:** Days are calendar days. A "period" is the stated window ending at T unless stated.
- **Notation:** `T` prediction timestamp; `W_obs` observation window length; `H` prediction horizon; `C` set of customers in scope.
- **Currency:** All monetary values are in the source currency unless converted. `Data Gap` — currency is unconfirmed.
- **Denominators:** Every KPI definition names its denominator. If a denominator is zero, the KPI is **undefined**, not zero.
- **Small groups:** Report group size alongside any rate.
- **Missing data:** Report "not available" rather than imputing.

---

## 7. Data Scope for Customer Population

- **Prediction population (primary):** Active customers at T (≥ 1 valid purchase in W_obs). `Proposed Assumption`.
- **Out of scope for lapse prediction:** Already Lapsed customers (handled by reactivation guidance) and customers without customer ID.
- **Limitation:** Customers acquired shortly before T have little history; flag with the Limited History Flag.

---

## 8. Customer Lapse Prediction Definitions

### 8.1 Time Structure
```
        |<---------- W_obs ---------->|T|<---------- H ---------->|
   features computed here (≤ T)          label observed here (> T)
```

| Element | Definition | Proposed value | Label |
|---|---|---|---|
| Prediction timestamp (T) | Date when features are frozen and a prediction is made | Set per run | `Verified Fact` that it must be explicit |
| Observation window (W_obs) | Days before T used for features | 180 days | `Proposed Assumption`, `Pending Validation` |
| Prediction horizon (H) | Days after T over which lapse is observed | 90 days | `Proposed Assumption`, `Pending Validation` |

### 8.2 Label Definition
```
lapse_label(c, T) = 1  if customer c is Active at T and has 0 valid purchases in (T, T + H]
lapse_label(c, T) = 0  if customer c is Active at T and has ≥ 1 valid purchase in (T, T + H]
```
- Only Active customers at T are labeled.
- A customer's final label is observable only after T + H has passed. Cohorts where T + H is in the future are **censored** and must not be used for training or evaluation.
- Cancelled purchases do not count as valid purchases.

### 8.3 Model Output
`p_lapse(c, T)` is the estimated probability that `lapse_label(c, T) = 1`.

### 8.4 Calibration Requirement
**`Pending Validation`** — Reading risk tiers (Section 9) as real probabilities assumes `p_lapse` is calibrated, meaning that among customers with p_lapse near 0.7, about 70% actually lapse. In the supplied file the probabilities range from about 0.00000002 to 0.9996, which can indicate an over-confident model. If calibration is not confirmed, use the tiers and `p_lapse` as a ranking aid and use the percentile rank (Section 9.1) for urgency, and state this.

### 8.5 Choice of H and W_obs
**`Proposed Assumption`** — The values 90 and 180 days are starting points. They should be validated against customers' typical inter-purchase intervals: if many customers normally buy less often than every 90 days, H is too short and produces false lapse signals. **`Data Gap`** — the real distribution of inter-purchase intervals is unknown.

### 8.6 Already Lapsed Customers
A customer with no valid purchase in the most recent 90 days as of T. `Proposed Assumption`. Not scored by the lapse model; handled under reactivation.

---

## 9. Risk Segmentation

### 9.1 Risk Tier Thresholds
**`Verified Fact`** — These cut points are the ones observed in the scoring file `customer_lapse_predictions.csv`. The boundary convention is a `Data Gap` to confirm with the model owner. This Knowledge Base adopts lower bound inclusive, upper bound exclusive (`Proposed Assumption`).

| Tier | Rule on p_lapse | Customers in the supplied file | Share |
|---|---|---|---|
| Low | p_lapse < 0.30 | 657 | 12.6% |
| Medium | 0.30 ≤ p_lapse < 0.50 | 548 | 10.5% |
| High | p_lapse ≥ 0.50 | 4,019 | 77.0% |

**Why there is no Critical tier.** An earlier draft proposed four tiers with cut points at 0.60 and 0.80. Applied to the supplied file, that scheme would place 2,055 customers (39.3%) in a Critical tier, which exceeds realistic review capacity. The draft was retired. Urgency within the High tier is handled by the Focus List and by the percentile rank below.

**Urgency Percentile** (descriptive, no calibration needed):
```
Urgency Percentile(c) = percent rank of p_lapse(c) among all scored customers in the same snapshot
```
- Unit: percentile, 0 to 100. Higher means a higher p_lapse relative to other customers in that snapshot.
- Limitation: It is relative to one snapshot and says nothing about the absolute chance of lapse.

**Focus List** (`Proposed Assumption`):
```
Focus List = the N High-risk customers with the highest Priority Score
```
- N is set by the business (`Data Gap`). Priority Score is defined in Section 9.3.
- If value data is not available, order High-risk customers by p_lapse and state that value was not considered.

### 9.2 Value Tier Definition
```
V_norm(c) = percentile rank of monetary_W(c) among active customers, scaled to (0, 1]
```
| Tier | Rule |
|---|---|
| V1 | V_norm ≥ 0.90 |
| V2 | 0.60 ≤ V_norm < 0.90 |
| V3 | V_norm < 0.60 |

- `monetary_W(c)` = net revenue (valid purchases minus cancellations/returns) for customer c in W_obs. Unit: currency.
- **Limitation:** Historical value is not profit or future value (Section 14). Ties and small populations affect percentiles.
- **Alternative:** If margin data is available, a margin-based value measure may be used; this is a change requiring business approval.

### 9.3 Priority Matrix
`Proposed Assumption`, `Pending Validation`.

| Risk \ Value | V1 | V2 | V3 |
|---|---|---|---|
| High | P1 | P2 | P3 |
| Medium | P2 | P3 | P4 |
| Low | P3 | P4 | P4 |

**Priority Score** (ordering aid within a band):
```
Priority Score = p_lapse × V_norm
```
Unit: dimensionless, range (0, 1]. Not a probability, not a monetary amount, not an expected loss.

### 9.4 Flags
`Proposed Assumption`, `Pending Validation`.

| Flag | Definition | Variables |
|---|---|---|
| Repeated Cancellation Flag (RCF) | `cancel_count_W ≥ 3` **or** (`cancel_value_rate_W ≥ 0.20` **and** `invoice_count_W ≥ 3`) | See Section 13 |
| Declining Activity Flag (DAF) | `purchases_last90 / purchases_prev90 < 0.5` **or** `netrev_last90 / netrev_prev90 < 0.5`, provided `purchases_prev90 ≥ 2` | Last 90 days vs. the preceding 90 days before T |
| Limited History Flag (LHF) | `invoice_count_W = 1` | |
| Already Lapsed | No valid purchase in 90 days before T | |

- **Limitation:** With W_obs = 180 days, "last 90" and "previous 90" use the full window. Seasonality and irregular purchasing can trigger DAF without real decline.

### 9.5 Required Reporting
When the Agent reports a tier, it must include the prediction timestamp, the model version (or Data Gap), and whether thresholds are calibrated or percentile-based.

---

## 10. Recommendation Ranking Logic

### 10.1 Components
| Component | Definition | Range | Source |
|---|---|---|---|
| `p_buy(c, i)` | Estimated purchase likelihood of product i by customer c in the recommendation horizon | 0 to 1 | Recommender model |
| `p_cancel(c, i)` | Estimated likelihood that a purchase of i by c is cancelled or returned | 0 to 1 | Cancellation model (customer-product or product-level) |
| `Value_norm(i)` | Business value indicator of product i, normalized | 0 to 1 | Margin or revenue proxy; `Data Gap` |
| `Availability_flag(i)` | 1 if available, 0 if unavailable/restricted/unconfirmed | {0, 1} | Stock data; `Data Gap` |

### 10.2 Adjusted Recommendation Score
`Proposed Assumption`, `Pending Validation`.
```
Adjusted Recommendation Score(c, i) = p_buy(c, i) × (1 − p_cancel(c, i)) × Value_norm(i) × Availability_flag(i)
```
- **Unit:** dimensionless score in [0, 1]. Used only to rank products for a given customer.
- **Interpretation:** Higher means "relatively better candidate" given likelihood of purchase, likelihood of the sale surviving cancellation, and value.
- **Not** a probability of sale, expected revenue, or profit. The product of the terms assumes independence, which is a simplification.
- **Fallbacks:**
  - If `Value_norm` is unavailable: set to 1 for all products and state that value was not considered.
  - If `p_cancel` is unavailable: omit the term and state the recommendation is not cancellation-aware.
  - If `Availability_flag` is unavailable: mark "availability unconfirmed" and do not present as confirmed.

### 10.3 Ranking Rules
1. Exclude products with `Availability_flag = 0`.
2. Rank remaining products by Adjusted Recommendation Score, descending.
3. Break ties by `p_buy`, then by lower `p_cancel`.
4. Optionally exclude products the customer already buys on every order, unless replenishment is the goal. `Proposed Assumption`.
5. Keep the list short; list length is a `Data Gap`.

### 10.4 Limitations
- Recommendation scores depend on model quality (`Pending Validation`).
- Offline ranking metrics do not prove that recommendations change purchasing.
- The cancellation term corrects for expected cancellations; it does not explain them.

---

## 11. Core Revenue, Order, and Frequency KPIs

All formulas apply to a defined period and customer set. "Valid" means after the rules in Section 5.

| KPI | Formula | Variables and unit | Denominator | Limitations |
|---|---|---|---|---|
| Gross Revenue | `Σ (quantity × unit_price)` over valid purchase lines | quantity: units; unit_price: currency/unit; result: currency | — | Ignores cancellations/returns |
| Cancellation/Return Value | `Σ |quantity × unit_price|` over cancellation/return lines | currency | — | Matching to original orders may be incomplete |
| Net Revenue | `Gross Revenue − Cancellation/Return Value` | currency | — | Not profit |
| Order Count | count of distinct valid purchase invoices | count | — | Depends on invoice definition |
| Average Order Value (AOV) | `Gross Revenue / Order Count` | currency per order | Order Count | Skewed by large orders; use median alongside |
| Net AOV | `Net Revenue / Order Count` | currency per order | Order Count | Mixes periods if cancellations occur later |
| Purchase Frequency | `Order Count / number of active customers in the period` | orders per customer per period | Active customers | Period length must be stated |
| Customer-Level Frequency | `frequency_W(c)` = distinct valid invoices in W | count | — | Limited by W |
| Recency | `T − timestamp of last valid purchase` | days | — | Compare to customer's own typical interval |
| Mean Inter-Purchase Interval | mean days between consecutive valid purchases of a customer | days | n − 1 intervals | Undefined with < 2 purchases; unstable with few purchases |
| Items per Order | `Σ quantity / Order Count` | units per order | Order Count | Unit definitions vary by product |
| Product Variety | distinct `product_id` purchased in period | count | — | Depends on product ID granularity |

**Cautions:**
- Quantities and values are only comparable if currency and unit-of-measure are consistent (`Data Gap`).
- Averages in wholesale data are strongly affected by a few large customers; report distributions where possible.

---

## 12. Customer Value and Concentration

### 12.1 Historical Customer Value
```
monetary_W(c) = Net Revenue of customer c in W_obs
```
Unit: currency. **`Verified Fact`** — this is a historical measure; it does not predict future spend or profit.

### 12.2 Revenue Concentration
```
Top-k% Revenue Share = (Σ monetary_W for the top k% customers) / (Σ monetary_W for all active customers)
```
- Unit: ratio (0 to 1). Denominator: total net revenue of active customers in W_obs.
- Use to understand dependence on top customers. **`Data Gap`** — actual concentration is unknown; any claim about it requires computed data.

### 12.3 Customer Value Approaches (Reference)
| Approach | Definition | Data needed | Status |
|---|---|---|---|
| Historical net revenue | Section 12.1 | Transactions | Used for value tiers |
| Historical margin | Net revenue minus product cost | Cost data | `Data Gap` |
| Predicted future value (e.g., CLV) | Model-estimated future value | Long history, model | Not defined in this Knowledge Base; `Pending Validation` |

### 12.4 Limitations
Value tiers based on a 180-day window can misrepresent customers with long buying cycles or seasonal buying.

---

## 13. Cancellation and Retention KPIs

### 13.1 Cancellation KPIs
| KPI | Formula | Unit / Denominator | Limitations |
|---|---|---|---|
| Order Cancellation Rate | `cancelled invoices / (valid purchase invoices + cancelled invoices)` | ratio; all invoices considered | Depends on matching rules |
| Value Cancellation Rate | `Cancellation/Return Value / Gross Revenue` | ratio; gross revenue | Timing mismatch if cancellations are later than sales |
| Customer Cancellation Count | `cancel_count_W(c)` | count | Small counts are unstable |
| Customer Value Cancellation Rate | `cancel_value_rate_W(c) = Cancellation/Return Value(c) / Gross Revenue(c)` | ratio; customer gross revenue in W | Undefined if gross revenue is zero |
| Product Cancellation Rate | `cancelled units of product i / units ordered of product i` | ratio; units ordered | Product with few orders is unreliable |

**Interpretation:** Cancellation rates describe transactions; they do not by themselves explain why cancellations occur.

### 13.2 Retention and Lapse KPIs
| KPI | Formula | Unit / Denominator | Limitations |
|---|---|---|---|
| Retention Rate | `customers Active at T who purchase in (T, T+H] / customers Active at T` | ratio; active customers at T | Complement of lapse rate; cohort-dependent |
| Lapse Rate | `1 − Retention Rate` = `lapse_label = 1 / Active at T` | ratio; active customers at T | Lapse is not churn |
| Reactivation Rate | `Already Lapsed customers at T who purchase in (T, T+H] / Already Lapsed customers at T` | ratio; lapsed customers at T | Includes natural return behavior |
| Retained Net Revenue | `Σ net revenue in (T, T+H] from customers Active at T` | currency | Not profit; not attributable to a program |
| Revenue Retention Ratio | `Net revenue in (T, T+H] from customers Active at T / net revenue in W_obs from the same customers` | ratio; same-customer baseline | Windows have different lengths unless normalized; state it |
| Program Uplift (when an experiment exists) | `Retention rate (treated) − Retention rate (holdout)` | percentage points | Requires randomized or well-controlled holdout; `Pending Validation` |

### 13.3 Cautions
- Do not attribute changes in retention to the Agent or any campaign without a holdout comparison.
- Reactivation and retention should be reported with group sizes and the period used.
- Report outcomes only after T + H has fully elapsed (censoring).

---

## 14. Revenue vs. Profit vs. Customer Value vs. Model Scores

### 14.1 Distinctions
| Concept | What it is | Unit | Source | Can it be used as a monetary amount? |
|---|---|---|---|---|
| Revenue (gross/net) | Sales value recorded | currency | Transactions | Yes, as historical revenue |
| Profit | Revenue minus costs | currency | Requires cost data (`Data Gap`) | Only if cost data supplied |
| Customer value (historical) | Net revenue by customer in a window | currency | Transactions | Historical revenue only; not profit or forecast |
| Customer value (predicted, e.g., CLV) | Model-estimated future value | currency or score | Not defined here | Only if model defined, validated, and labeled |
| p_lapse, p_buy, p_cancel | Probabilities | 0 to 1 | Models | **No** |
| Priority Score, Adjusted Recommendation Score | Ranking scores | dimensionless | Formulas above | **No** |
| Risk tier, value tier, priority band | Categories | — | Rules | **No** |

### 14.2 Rules for the AI Agent
- **Rule M-1:** Never express a probability or score in currency terms.
- **Rule M-2:** Never multiply a probability by revenue and present the product as "money at risk" or "expected loss". `Verified Fact` — such a figure depends on calibration, causal assumptions, and horizon matching that have not been validated here.
- **Rule M-3:** Do not state profit without cost data and a shown calculation.
- **Rule M-4:** When asked about financial impact, explain what data would be required and say that no validated estimate exists (`Data Gap`).
- **Rule M-5:** Use "estimated" and "model-based" for any model output.

---

## 15. Model Evaluation, Temporal Validation, and Limitations

**`Verified Fact`** — No model performance results are provided in this Knowledge Base. All metrics below are definitions and interpretation guidance. Any performance claim requires actual evaluation outputs (`Pending Validation`).

### 15.1 Lapse Model (Binary Classification) Metrics
| Metric | Definition | How to interpret | Limitations |
|---|---|---|---|
| ROC-AUC | Probability a random lapsing customer is scored higher than a random non-lapsing one | 0.5 = no better than chance; higher is better ranking | Can look good with imbalanced classes; ignores calibration |
| PR-AUC | Area under the precision–recall curve | Compare to the lapse base rate | Sensitive to class prevalence |
| Precision | `TP / (TP + FP)` | Among flagged customers, share that truly lapsed | Depends on threshold |
| Recall | `TP / (TP + FN)` | Share of lapsing customers that were flagged | Depends on threshold |
| F1 | Harmonic mean of precision and recall | Balance of the two | Ignores true negatives; threshold-dependent |
| Brier Score | Mean of `(p_lapse − label)²` | Lower is better; measures probability accuracy | Needs comparison to a baseline |
| Calibration (e.g., reliability curve, ECE) | Agreement between predicted probability and observed frequency | Needed for tier thresholds to be meaningful | Needs enough data per bin |
| Lift / Gain at top k% | Lapse rate in top k% divided by overall lapse rate | Value of ranking for prioritization | Depends on k and base rate |
| Precision@N (top N) | Share of the N highest-scored customers who lapse | Matches the review-capacity use case | N is a business decision (`Data Gap`) |

TP = true positives, FP = false positives, FN = false negatives. A positive is a customer who lapses.

**Baselines (recommended):** `Proposed Assumption` — compare against simple rules (for example, recency-based) and against the base lapse rate, so improvement is meaningful.

### 15.2 Recommendation and Cancellation Model Metrics
| Metric | Definition | Interpretation | Limitations |
|---|---|---|---|
| Precision@K | Share of the top K recommended products actually purchased in the evaluation period | Accuracy of top picks | Depends on K; ignores rank order |
| Recall@K | Share of purchased products captured in top K | Coverage | Depends on K |
| Hit Rate@K | Share of customers with at least one purchased product in top K | Simple success rate | Coarse |
| MAP@K | Mean average precision at K | Rank-sensitive accuracy | Harder to interpret |
| NDCG@K | Rank-weighted gain | Rewards putting correct items higher | Gain definitions vary |
| Coverage / Diversity | Share of catalog recommended, variety across lists | Guards against narrow lists | Does not measure relevance |
| Cancellation model: ROC-AUC, PR-AUC, Brier | As in 15.1, with cancellation as the positive class | Measures cancellation risk estimates | Rare events make PR-AUC essential |
| Net-Outcome Hit Rate | Hit rate counting only purchases that were **not** cancelled | Returns-aware measure of recommendation success | Cancellation timing and matching |

### 15.3 Temporal Validation Rules
`Proposed Policy — Requires Business Approval`
1. **Split by time, never at random.** Train on earlier prediction timestamps and validate/test on later ones.
2. **Use multiple prediction timestamps** (rolling-origin / backtesting) to check stability across seasons. Number of folds `Data Gap`.
3. **Gap between training and testing:** Ensure the label period of training samples ends before the test T. Otherwise the future leaks into training.
4. **Censoring:** Exclude samples whose T + H lies beyond the last available data date.
5. **Customer overlap:** The same customers appear at multiple timestamps; consider customer-grouped evaluation to measure generalization to new customers, in addition to time-based splits.
6. **Preprocessing fit on training data only:** For example, percentiles, scalers, and encodings.
7. **Hyperparameter selection on validation periods only;** the final test period is used once.

### 15.4 Data Leakage Prevention
| Leakage type | Example | Prevention |
|---|---|---|
| Future data in features | Counting purchases after T | Compute features with timestamp ≤ T only |
| Label overlap | Using H-period behavior in features | Strict window separation |
| Post-event fields | Fields created after outcome (for example, account status set after lapse) | Review each field's creation time (`Data Gap`) |
| Cancellation timing | A cancellation after T that reverses a purchase before T | Use information as known at T; define rules for late cancellations |
| Global statistics | Percentiles computed on all data including future | Compute within training data/prior to T |
| Identifier leakage | IDs that encode time or customer age | Review features |
| Duplicate customers across splits | Same customer in train and test at close times | Group or time-gap splits |

### 15.5 Evaluation Limitations
- **No causal claims:** Predictive accuracy does not show that interventions work.
- **Base rate sensitivity:** Metrics depend on the lapse rate, which varies by period.
- **Seasonality and shocks:** A single period may not represent future periods.
- **Calibration drift:** Probabilities may degrade over time; monitor.
- **Selection effects:** Offline evaluation on historical data cannot reveal effects of recommendations that were never shown.
- **Business-value gap:** Good metrics do not guarantee business benefit; measure outcomes with a holdout (`Pending Validation`).
- **Small groups:** High-value segments are small, so metrics for them are noisy.
- **Fairness and consistency:** Check performance across customer segments. `Proposed Assumption`.

### 15.6 Monitoring (Proposed)
`Proposed Assumption` — Track data quality, score distributions, calibration, and tier shares over time, and trigger review when they shift materially. Thresholds `Data Gap`.

---

## 16. Traceability: Business Rules, Input Data, Model Outputs, Recommendations

### 16.1 Principle
Every AI-generated recommendation must be traceable to (a) the rule or guidance used, (b) the data inputs, and (c) the model output. This enables audits, debugging, and trust.

### 16.2 Rule Identifier Convention
| Prefix | Source |
|---|---|
| `G-` | Retention playbook guardrails |
| `HR-` | Human-review triggers (retention playbook) |
| `E-`, `X-`, `U-`, `A-`, `PG-` | Promotion policy (eligibility, exclusion, unnecessary discount avoidance, approval, guardrails) |
| `DQ-` | Data quality rules (this file) |
| `R-`, `M-` | Reading rules and monetary rules (this file) |

### 16.3 Traceability Matrix
| Business rule | Input data required | Model output used | AI-generated output influenced |
|---|---|---|---|
| Risk tiering (Section 9.1) | `customer_id`, transactions up to T | `p_lapse`, `prediction_timestamp`, `model_version` | Risk tier in the strategy |
| Value tiering (Section 9.2) | Net revenue in W_obs | None (rule-based) | Value tier, priority band |
| Priority matrix (Section 9.3) | Risk tier, value tier | `p_lapse` | Priority band, ordering |
| RCF (Section 9.4) | Cancellation count/value in W_obs | None (rule-based) | Flag, escalation, promotion stance |
| DAF (Section 9.4) | Purchases and revenue by period | None (rule-based) | Flag, outreach guidance |
| Recommendation ranking (Section 10) | Product list, stock, value indicators | `p_buy`, `p_cancel` | Product suggestions |
| Promotion matrix (`promotion_policy.md`, Section 8) | Risk tier, value tier, flags, margin, stock, budget | `p_lapse` | Promotion stance |
| Human-review triggers (`retention_playbook.md`, Section 9) | All of the above | All | Escalation status |

### 16.4 Required Audit Record for Each Agent Output
| Field | Description |
|---|---|
| Output ID and timestamp | Unique identifier and creation time |
| Customer ID | As supplied |
| Prediction timestamp T | From model output |
| Model version(s) | Lapse, recommendation, cancellation (`Data Gap` if absent) |
| Input data snapshot reference | Identifier of the data extract used |
| Parameters in force | H, W_obs, thresholds, version of this Knowledge Base |
| Rule IDs applied | From the convention in 16.2 |
| Retrieved Knowledge Base passages | File and section |
| Missing data and Data Gaps | Listed explicitly |
| Human-review status and reviewer decision | Outcome and reason |

### 16.5 Traceability Rules
- **T-1:** Every customer-specific statement in an Agent output must cite its data source (model output or structured data field).
- **T-2:** Every business guidance statement must cite the Knowledge Base section.
- **T-3:** Statements without a source must be marked as assumptions or omitted.
- **T-4:** If the Knowledge Base and the data disagree (for example, thresholds differ), report the conflict and apply human review (`HR-6` / `HR-10`).

---

## 17. Data Availability Requirements by KPI

`Data Gap` — Availability in the real source is not confirmed. "Required" means the KPI cannot be computed without it.

| KPI / Output | Required data | Optional data | Cannot be computed if missing |
|---|---|---|---|
| Gross/Net Revenue | `quantity`, `unit_price`, cancellation indicator, timestamp | `currency` | Cancellation indicator (Net) |
| Order Count, AOV, Frequency | `invoice_id`, `customer_id`, timestamp | — | `customer_id` (customer-level) |
| Recency, Inter-Purchase Interval | `customer_id`, timestamp | — | Timestamps |
| Customer Value (historical) | Net revenue by customer | — | `customer_id` |
| Customer Margin / Profit | `unit_cost` | Handling and shipping costs | `unit_cost` |
| Cancellation KPIs | Cancellation indicator, order linkage | Reason codes | Cancellation indicator |
| Return vs. Cancellation split | Separate return indicator | Reason codes | Distinct flags |
| Lapse label and p_lapse | Transactions across ≥ W_obs + H history, multiple T | — | Sufficient history |
| Retention / Lapse / Reactivation Rate | Transactions after T through T + H | — | Completed horizon |
| Risk, value, priority tiers | `p_lapse`, net revenue | — | `p_lapse` (risk), revenue (value) |
| RCF / DAF / LHF | Cancellation and purchase history by period | — | Period history |
| Recommendation score | `p_buy`, `p_cancel`, `Value_norm`, `Availability_flag` | Category hierarchy | `p_buy` |
| Promotion margin check | `unit_price`, `unit_cost`, discount | Handling costs | `unit_cost` |
| Promotion budget check | Budget and spend tracking | — | Budget data |
| Program Uplift | Holdout or randomized group and outcomes | — | Experimental design |

**Rule DA-1:** When a required input is missing, the KPI is reported as "not computable: [missing input]".

---

## 18. Open Decisions for the Business

| ID | Decision needed | Status |
|---|---|---|
| BR-1 | Map the template data dictionary to the actual schema | `Data Gap` |
| BR-2 | Confirm timezone, currency, and units of measure | `Data Gap` |
| BR-3 | Confirm cancellation and return conventions, and whether they can be separated | `Data Gap` |
| BR-4 | Confirm treatment of records without customer ID and non-product lines | `Data Gap` |
| BR-5 | Validate H and W_obs against purchase cycles | `Pending Validation` |
| BR-6 | Validate calibration and risk-tier thresholds | `Pending Validation` |
| BR-7 | Validate value-tier cutoffs, and decide whether margin data replaces revenue | `Pending Validation` / `Data Gap` |
| BR-8 | Validate RCF and DAF thresholds | `Pending Validation` |
| BR-9 | Approve the recommendation score formula or alternatives | `Pending Validation` |
| BR-10 | Provide product cost, stock status, and category data | `Data Gap` |
| BR-11 | Define temporal validation scheme (folds, test period) | `Proposed Policy — Requires Business Approval` |
| BR-12 | Define the monitoring approach and alert thresholds | `Data Gap` |
| BR-13 | Define an experiment (holdout) to measure retention uplift | `Pending Validation` |
| BR-14 | Set review capacity (top-N) for prioritization | `Data Gap` |

---

## 19. Questions This Document Can Answer

Use this section to see what to ask the retention agent about definitions, data and metrics. Questions marked **(needs data)** also require the actual files or model outputs at run time.

### 19.1 Definitions and Terminology
- What is the difference between revenue, net revenue, profit and customer value?
- What is the difference between a return and a cancellation, and what is unknown in our data?
- What do prediction timestamp, observation window and prediction horizon mean?

### 19.2 The Supplied Scoring File
- What columns does `customer_lapse_predictions.csv` contain and what do they mean?
- How many customers are in each risk tier? (5,224 customers: 657 Low, 548 Medium, 4,019 High; one snapshot dated 2011-09-01)
- What is missing from the file, and what can't we do because of it?
- Is the file good enough to evaluate model performance? (No: one snapshot and no outcome column.)

### 19.3 Data Dictionary and Data Quality
- Which fields are needed for each KPI?
- How should cancellations, missing customer IDs, duplicates and outliers be handled?
- What is the template schema, and which parts are still unconfirmed?

### 19.4 KPI Formulas
- How are gross revenue, net revenue, AOV and purchase frequency calculated, with which denominator?
- How are retention rate, lapse rate, reactivation rate and cancellation rate defined?
- What does the Repeated Cancellation Flag mean and how is it computed?

### 19.5 Segmentation and Ranking
- How is a customer assigned to Low, Medium or High risk?
- How are value tiers and priority bands (P1 to P4) assigned?
- How is the Focus List built, and what is Priority Score?
- How is a product recommendation scored, and how does cancellation risk enter it?

### 19.6 Model Evaluation
- What do ROC-AUC, PR-AUC, precision, recall, Brier score and calibration tell me?
- How should I split data in time, and how do I prevent data leakage?
- What are the limits of the evaluation, and why can't we claim the program caused improvements?

### 19.7 Traceability
- Which rule, data field and model output produced a given recommendation?
- What must be stored in the audit record for each agent output?

### 19.8 Not Answerable From This Document
The document does not hold actual revenue figures, model performance results, profit or margin values, or approved business thresholds. The agent must report these as `Data Gap` or `Pending Validation` and must not invent them.
