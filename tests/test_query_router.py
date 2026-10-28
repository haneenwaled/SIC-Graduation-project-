import pytest

from src.query_router import extract_product_id, route_question


@pytest.mark.parametrize("q", [
    "Explain the promotion approval rules.",
    "What retention actions does the playbook suggest for high-risk customers?",
    "Explain the KPIs documented in the business rules.",
    "Explain the risk categories used in this project.",
    "What data is missing before we can estimate customer value?",
])
def test_policy_questions_use_rag_only(q):
    r = route_question(q)
    assert r.intent == "policy" and r.needs_knowledge and not r.needs_customer_data


@pytest.mark.parametrize("q", [
    "Summarize customer lapse risk in the latest snapshot.",
    "Which customers have the highest lapse probabilities?",
    "How many customers are in each risk category?",
])
def test_customer_questions_invoke_structured_data(q):
    r = route_question(q)
    assert r.intent == "customer" and r.needs_customer_data and r.customer_ops


def test_mixed_question_uses_both():
    r = route_question("Which customers have the highest lapse risk in the latest snapshot, and what retention actions should we consider?")
    assert r.intent == "mixed" and r.needs_customer_data and r.needs_knowledge
    assert "retention_playbook" in r.doc_types
    ops = [o["op"] for o in r.customer_ops]
    assert "summary" in ops and "top" in ops


def test_customer_id_lookup_and_top_n_and_snapshot():
    r = route_question("Show customer 12346 risk")
    assert r.customer_ops == [{"op": "lookup", "customer_id": 12346}]
    r = route_question("List the top 5 high risk customers on 2011-09-01")
    top = [o for o in r.customer_ops if o["op"] == "top"][0]
    assert top["n"] == 5 and top["category"] == "High" and r.snapshot_date == "2011-09-01"


def test_highest_is_not_mistaken_for_high_category():
    top = [o for o in route_question("Which customers have the highest lapse probabilities?").customer_ops if o["op"] == "top"][0]
    assert top["category"] is None


def test_evidence_followup_route():
    assert route_question("Show the evidence behind your recommendation.").intent == "evidence"


def test_product_question_routes_to_catalog():
    r = route_question("Find products matching wrapping tape in the catalog.")
    assert r.intent == "product" and r.needs_catalog and not r.needs_customer_data


def test_promotion_question_selects_promotion_policy_documents():
    assert "promotion_policy" in route_question("Is a discount allowed for a low-risk customer?").doc_types


def test_extract_product_id():
    assert extract_product_id("details for product 10123C please") == "10123C"
    assert extract_product_id("find products about tape") is None
