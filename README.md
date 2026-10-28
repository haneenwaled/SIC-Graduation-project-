# Retain & Recommend AI

**Returns-aware product recommendation, customer lapse prediction and a RAG-powered retention assistant.**

A Streamlit application for a business manager. It combines (1) a Gemini-powered chat assistant that answers from your policy documents and product catalog with visible evidence, and (2) deterministic Pandas queries and a dashboard over the customer lapse predictions.

---

## 1. Purpose and architecture

```
 question ──► query_router ──┬─► customer_data (Pandas)  ─► exact counts / rankings / lookups ─┐
                             ├─► retriever (FAISS + local embeddings) ─► policy / playbook /   ├─► prompt_builder ─► Gemini ─► answer + evidence
                             │                                           KPI / catalog passages ┘
                             └─► "show evidence" follow-up ─► previous sources (no LLM call)
```

* **Numbers are never computed by the LLM.** Counts, percentages, rankings and lookups come from Pandas; Gemini only explains them.
* **Documents are retrieved, not memorised.** The three Markdown files and the product catalog are chunked, embedded locally and stored in FAISS.
* **Evidence is shown for every answer**: the data tables used and the exact passages (file + section) sent to the model.

## 2. What each module does

| File | Role |
|---|---|
| `app.py` | Streamlit UI: assistant chat, demonstration panel, dashboard, sidebar status |
| `src/config.py` | All settings (env vars / `.env`), file names, risk-tier constants |
| `src/document_loader.py` | Loads/validates Markdown + JSONL; reports the exact missing filename |
| `src/chunking.py` | Heading-aware chunks with `source`, `doc_type`, `section`, `chunk_id` metadata; one chunk per product |
| `src/embeddings.py` | Local Sentence-Transformers embedder (+ labelled offline fallback) |
| `src/vector_store.py` | FAISS index, on-disk cache, content-hash fingerprint to detect stale indexes |
| `src/retriever.py` | Semantic search with metadata filters; policy vs. catalog retrieval kept separate |
| `src/customer_data.py` | CSV validation + deterministic queries (latest snapshot, counts, sort, lookup) |
| `src/query_router.py` | Rule-based intent routing: policy / customer / mixed / product / evidence |
| `src/prompt_builder.py` | Grounded system prompt, evidence blocks, injection-safe delimiters, citations |
| `src/llm_client.py` | Gemini wrapper with friendly, secret-free error messages |
| `src/rag_engine.py` | Orchestrates everything; builds/loads the index |
| `tests/` | Automated tests (no live API needed) |
| `scripts/smoke_test_gemini.py` | Optional manual live API check |

## 3. Prerequisites

* Windows 10/11, **Python 3.11 or 3.12** (recommended; check with `python --version`)
* VS Code (optional but recommended) with the Python extension
* A Gemini API key from <https://aistudio.google.com/apikey>
* Internet on first run: the multilingual embedding model (~470 MB) is downloaded once from Hugging Face, and Gemini is called over the internet.

## 4. Open the project in VS Code

1. Unzip `retain-recommend-rag.zip`.
2. In VS Code: **File → Open Folder…** and choose the `retain-recommend-rag` folder.
3. Open a terminal: **Terminal → New Terminal** (PowerShell).

## 5. Create and activate a virtual environment (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the script ("running scripts is disabled"), run this once for the current window and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 6. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

(The first install is large because `sentence-transformers` pulls in PyTorch.)

## 7. Configure the Gemini API key

```powershell
Copy-Item .env.example .env
notepad .env
```

Replace `your_gemini_api_key_here` with your key and save. **The key goes only in `.env`** (never in code; `.env` is git-ignored). Optional settings (model, chunk size, top-k…) are documented inside `.env.example`.

If you already ran an older version, delete the `.cache` folder (or just restart: the index rebuilds automatically because the embedding model changed).

> **Model names change.** The default `GEMINI_MODEL=gemini-3.5-flash` was taken from Google's published model list, but it could not be verified against the live API while this project was built. Run `python scripts/smoke_test_gemini.py` to see which models your key can use, and change `GEMINI_MODEL` if needed.

## 8. Run the application

```powershell
streamlit run app.py
```

The browser opens at <http://localhost:8501>. The first start embeds ~4,350 chunks and caches the index in `.cache/index/`; later starts load it instantly. The index is **rebuilt automatically** if any source document, chunk setting or embedding model changes.

Without an API key the app still starts: the dashboard, data tables and retrieved evidence work, and the chat shows setup instructions instead of a written answer.

## 9. Run the tests

```powershell
python -m pytest -q
```

No API key or internet is needed (a fake LLM and a deterministic embedder are used with tiny temporary fixtures). Optional live check:

```powershell
python scripts/smoke_test_gemini.py
$env:RUN_LIVE_TESTS = "1"; python -m pytest tests/test_live_gemini.py -v
```

## 10. Try the assistant

Use the sidebar buttons or the **Demonstration panel**; they run the real pipeline. Good tests:

| Question | What should happen |
|---|---|
| Summarize customer lapse risk in the latest snapshot. | Pandas counts (Low 657 / Medium 548 / High 4,019, snapshot 2011-09-01) + a short explanation |
| Which customers have the highest lapse probabilities? | Sorted table from the CSV |
| What retention actions does the playbook suggest for high-risk customers? | Passages from `retention_playbook.md` with section names |
| Explain the promotion approval rules. | Passages from `promotion_policy.md`, noting rules are *proposed*, not approved |
| Which customers have the highest lapse risk…, and what retention actions should we consider? | Mixed: data tables **and** playbook/KPI passages |
| Look up customer 12346 | Record from the CSV only (no invented history) |
| Find products matching wrapping tape in the catalog. | Catalog entries |
| Show the evidence behind your recommendation. | Re-displays the sources of the previous answer |

Open **📎 Evidence and sources** under any answer to see exactly what the model was given.

## 10b. Arabic and English

You can ask in **English or Arabic**; the assistant answers in the language of your question (Arabic answers are shown right-to-left). The sidebar has an **Arabic examples** section.

How it works: the router normalises Arabic spelling and digits (`١٢٣٤٦` = `12346`) and recognises Arabic keywords; Arabic questions get English search hints so they match the English documents; the embedding model is multilingual (`paraphrase-multilingual-MiniLM-L12-v2`); and the prompt tells Gemini which language to reply in. Customer IDs, file names, evidence labels (e.g. `Data Gap`) and citation labels stay in their original form.

Limits: the documents and product names are English, so searching the catalog works best when you type the product words in English (e.g. `ابحث عن منتجات wrapping tape`). Routing is keyword-based, so very unusual Arabic phrasings may be sent to the documents instead of the customer data; rephrase with words like عملاء / أعلى / خطر / لقطة. Dialect (Egyptian/Gulf) wording is only partly covered. The interface labels (sidebar, buttons) remain in English.

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| "Gemini API key not configured" | Create `.env` from `.env.example` and set `GEMINI_API_KEY`; restart Streamlit |
| "configured Gemini model is unavailable" | Run `python scripts/smoke_test_gemini.py`; set `GEMINI_MODEL` to a listed model |
| Quota / rate limit message | Wait and retry, or check your Google AI Studio plan |
| Sidebar says "Embedding model not loaded… fallback" | No internet / blocked Hugging Face on first run. Connect, delete the `.cache` folder, restart. The fallback is keyword-based and noticeably weaker |
| "Missing required input file(s): …" | Put the named file(s) in `data/` with the exact original filename |
| Stale or odd retrieval after editing a document | Restart the app; the index rebuilds when file contents change. You can also delete `.cache/` |
| `Activate.ps1` cannot be loaded | Use the `Set-ExecutionPolicy -Scope Process …` command in section 5 |
| `ModuleNotFoundError` | Activate `.venv`, then `python -m pip install -r requirements.txt` |
| Port already in use | `streamlit run app.py --server.port 8502` |

## 12. What the system can and cannot conclude

**Can:** report counts and percentages of distinct customers per risk category for a snapshot; list/sort customers by estimated lapse probability; look up a customer's risk record; explain playbook actions, promotion rules, KPI definitions, thresholds and data gaps from the documents; search product catalog statistics (price, quantity, revenue per product).

**Cannot (not in the supplied files):** customer names, purchase history, revenue, profit, cancellations, product preferences, customer lifetime value, value tiers, priority bands, flags, or the Focus List (these need data joined by `customer_id`). It cannot evaluate model accuracy (one snapshot, no outcomes), cannot say a discount or action *will* retain a customer, and cannot recommend a specific product for a specific customer. The documents state that their thresholds and rules are **proposals requiring business approval**; the assistant is instructed to say so. All data is from one snapshot (**2011-09-01**) and must not be presented as current.

**Privacy:** your files stay on your computer. When an answer is generated, your question, the computed data results and the retrieved passages are sent to the Gemini API.

**Note on rounding:** the High tier is 4,019 of 5,224 customers = 76.9% (the documents round this to 77.0%); the app shows its own computed value.
