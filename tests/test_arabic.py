"""Arabic (and mixed) question support: language detection, routing, prompts, retrieval, messages."""
import pytest

from src.llm_client import LLMError
from src.query_router import detect_language, normalize_text, route_question
from src.rag_engine import MESSAGES, build_engine
from tests.conftest import FakeLLM


def test_normalize_text_unifies_arabic_variants_and_digits():
    assert normalize_text("أعلى العملاء ١٢٣٤٦") == "اعلي العملاء 12346"
    assert normalize_text("الإجراءات الترويجيّة") == "الاجراءات الترويجيه"
    assert normalize_text("Hello 123") == "Hello 123"


def test_language_detection():
    assert detect_language("أي العملاء لديهم أعلى احتمال؟") == "ar"
    assert detect_language("Which customers have the highest risk?") == "en"
    assert detect_language("ابحث عن منتجات wrapping tape") == "ar"
    assert detect_language("") == "en"


@pytest.mark.parametrize("q,intent", [
    ("لخص مخاطر انقطاع العملاء في آخر لقطة.", "customer"),
    ("أي العملاء لديهم أعلى احتمال للانقطاع؟", "customer"),
    ("كم عميل في كل فئة خطر؟", "customer"),
    ("اشرح فئات المخاطر المستخدمة في هذا المشروع.", "policy"),
    ("ما الإجراءات التي يقترحها دليل الاحتفاظ للعملاء عالي الخطر؟", "policy"),
    ("اشرح قواعد الموافقة على العروض الترويجية.", "policy"),
    ("ما البيانات الناقصة لتقدير قيمة العميل؟", "policy"),
    ("اشرح مؤشرات الأداء الموجودة في القواعد التجارية.", "policy"),
    ("أي العملاء الأعلى خطرا في آخر لقطة، وما الإجراءات التي نفكر فيها؟", "mixed"),
    ("اعرض الأدلة وراء توصيتك.", "evidence"),
    ("ابحث عن منتجات wrapping tape في الكتالوج", "product"),
])
def test_arabic_routing_matches_english_behaviour(q, intent):
    r = route_question(q)
    assert r.intent == intent and r.language == "ar"


def test_arabic_customer_id_digits_top_n_and_category():
    assert route_question("ابحث عن العميل رقم ١٢٣٤٦").customer_ops == [{"op": "lookup", "customer_id": 12346}]
    top = [o for o in route_question("أعلى 5 عملاء عالي الخطر").customer_ops if o["op"] == "top"][0]
    assert top["n"] == 5 and top["category"] == "High"
    assert route_question("أي العملاء الأعلى احتمالا").customer_ops[0]["op"] in ("top", "summary")


def test_arabic_policy_question_gets_english_retrieval_hints():
    r = route_question("اشرح قواعد الموافقة على العروض الترويجية.")
    assert "promotion" in r.retrieval_query and "approval" in r.retrieval_query
    assert route_question("What are the rules?").retrieval_query == "What are the rules?"


def test_arabic_question_uses_real_data_and_asks_for_arabic_reply(config, embedder, fake_llm):
    engine, _ = build_engine(config, embedder=embedder, llm=fake_llm)
    ans = engine.answer("لخص مخاطر انقطاع العملاء في آخر لقطة.")
    assert ans.language == "ar" and ans.used_llm
    assert "<response_language>Arabic" in fake_llm.prompt
    assert "| High | 3 | 50.0 |" in fake_llm.prompt and "Distinct customers: 6" in fake_llm.prompt


def test_english_question_still_asks_for_english(config, embedder, fake_llm):
    engine, _ = build_engine(config, embedder=embedder, llm=fake_llm)
    engine.answer("How many customers are in each risk category?")
    assert "<response_language>English" in fake_llm.prompt


def test_arabic_question_retrieves_english_policy_passages(config, embedder, fake_llm):
    engine, _ = build_engine(config, embedder=embedder, llm=fake_llm)
    ans = engine.answer("اشرح قواعد الموافقة على العروض الترويجية.")
    assert ans.citations and ans.citations[0]["source"] == "promotion_policy.md"


def test_arabic_failure_and_no_evidence_messages(config, embedder):
    engine, _ = build_engine(config, embedder=embedder, llm=FakeLLM(error=LLMError("x", "quota")))
    ans = engine.answer("كم عميل في كل فئة خطر؟")
    assert ans.text == MESSAGES["ar"]["llm_failed"] and ans.tables
    ev = engine.answer("اعرض الأدلة وراء توصيتك.")
    assert ev.text == MESSAGES["ar"]["no_prev"] or ev.text == MESSAGES["ar"]["evidence_intro"]


def test_arabic_evidence_followup_reuses_sources(config, embedder, fake_llm):
    engine, _ = build_engine(config, embedder=embedder, llm=fake_llm)
    first = engine.answer("اشرح قواعد الموافقة على العروض الترويجية.")
    fake_llm.prompt = None
    ev = engine.answer("اعرض الأدلة وراء توصيتك.", last_answer=first)
    assert ev.citations == first.citations and ev.text == MESSAGES["ar"]["evidence_intro"] and fake_llm.prompt is None
