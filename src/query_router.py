"""Rule-based intent routing: structured data, document RAG, product catalog, or a mix.

Understands English and Arabic questions. Deliberately simple and testable: regular
expressions and keyword lists only. Arabic text is normalised first (diacritics removed,
alef/ya/ta-marbuta variants unified, Arabic-Indic digits converted), so Arabic patterns
below are written in that normalised form.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

KNOWLEDGE_ALL = ("retention_playbook", "promotion_policy", "business_rules")

# ------------------------------------------------------------------ language helpers
_AR_MARKS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_AR_CHARS = re.compile(r"[\u0600-\u06FF]")
_LATIN = re.compile(r"[A-Za-z]")


def normalize_text(text: str) -> str:
    """Unify Arabic spelling variants and digits; leaves English text unchanged."""
    t = _AR_MARKS.sub("", text).translate(_DIGITS)
    t = re.sub("[أإآٱ]", "ا", t)
    return t.replace("ى", "ي").replace("ة", "ه")


def detect_language(text: str) -> str:
    """'ar' if Arabic script makes up a meaningful share of the letters, else 'en'."""
    ar, la = len(_AR_CHARS.findall(text)), len(_LATIN.findall(text))
    return "ar" if ar >= 3 and ar >= 0.25 * (ar + la) else "en"


# ------------------------------------------------------------------ patterns
_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
_ID_RE = re.compile(
    r"(?:customer|client|account|cust\.?|id|عميل|العميل|زبون|الزبون|حساب)\s*(?:id|number|no\.?|رقم|كود)?\s*[#:]?\s*(\d{3,})", re.I)
_BARE_ID_RE = re.compile(r"(?<![\d.\-])(\d{5,})(?![\d\-])")
_TOPN_RE = re.compile(
    r"\b(?:top|first|highest|worst|bottom|lowest)\s+(\d{1,3})\b|\b(\d{1,3})\s+(?:highest|top|riskiest|most|customers|clients)\b"
    r"|(?:اعلي|اكبر|اخطر|افضل|اول|اقل)\s*(\d{1,3})|(\d{1,3})\s*(?:عملاء|عميل|زبائن)", re.I)
_PRODUCT_ID_RE = re.compile(r"(?:product|منتج)\s*(?:id|code|رقم|كود)?\s*[#:]?\s*([A-Za-z0-9]{4,8})\b", re.I)

_DATA_CUES = re.compile(
    r"which customers|what customers|how many (?:customers|clients)|number of customers|list (?:the )?customers|"
    r"show (?:me )?(?:the )?(?:\w+[- ]){0,3}customers|customers (?:with|at|in|who)|top \d+|highest|lowest|riskiest|"
    r"latest snapshot|snapshot|summar\w+ (?:of )?(?:the )?(?:customer )?(?:lapse|risk)|summar\w+ customer|"
    r"risk (?:distribution|breakdown|summary|counts?)|lapse probabilit|distribution|"
    r"high[- ]risk customers|medium[- ]risk customers|low[- ]risk customers|customers requiring attention|"
    r"needs? attention|need attention", re.I)
_DATA_CUES_AR = re.compile(
    r"اي (?:ال)?(?:عملاء|زبائن)|ايه (?:ال)?عملاء|انهي (?:ال)?عملاء|مين (?:ال)?عملاء|من هم (?:ال)?عملاء|"
    r"كم (?:عميل|زبون|من العملاء)|كام (?:عميل|زبون)|عدد (?:ال)?(?:عملاء|زبائن)|"
    r"اعلي|اكبر|اخطر|اقل (?:ال)?(?:عملاء|خطر|احتمال)|لقطه|"
    r"(?:ملخص|لخص|نظره عامه).*(?:خطر|مخاطر|عملاء|انقطاع|تسرب)|توزيع|"
    r"(?:ال)?عملاء (?:ذوي|ذو|عالي|مرتفع|متوسط|منخفض)|يحتاجون (?:اهتمام|انتباه)|يتطلبون")
_GUIDANCE_CUES = re.compile(
    r"action|recommend|what should|what do we do|retention|playbook|next step|strategy|outreach|"
    r"intervention|engage|re-?engage|promotion|discount|incentive|approval|should we|suggest", re.I)
_GUIDANCE_CUES_AR = re.compile(
    r"اجراء|اجراءات|توصي|توصيه|نوصي|ماذا نفعل|ايه نعمل|استراتيجي|احتفاظ|ابقاء|تواصل|خصم|خصومات|عروض|ترويج|"
    r"حافز|موافقه|اقتراح|اقترح|يقترح|الخطوات التاليه|نفكر")
_EVIDENCE_FOLLOWUP = re.compile(
    r"(show|display|give|see)\b.*\b(evidence|sources?|citations?|references?)|evidence behind|"
    r"what (?:evidence|sources?)|why did you (?:say|recommend)"
    r"|(?:اعرض|اظهر|وريني|ورني|ارني|اعطني|هات).*(?:الادله|دليل|الدليل|المصادر|مصادر|الاستشهاد|المراجع|الاثبات)"
    r"|الدليل وراء|الادله وراء|ما (?:هي )?الادله|ما المصادر|ليه قلت|لماذا اوصيت", re.I)
_PRODUCT_CUES = re.compile(r"\b(products?|catalog|catalogue|items?|sku|stock code)\b|منتج|منتجات|كتالوج|اصناف|سلع", re.I)
_PROMO_CUES = re.compile(
    r"promotion|promo|discount|margin|budget|incentive|rebate|cooldown|approver|approval"
    r"|ترويج|خصم|خصومات|عروض|هامش|ميزانيه|حافز|موافقه|معتمد", re.I)
_KPI_CUES = re.compile(
    r"kpi|metric|formula|definition|define|calculat|revenue|profit|value|threshold|data gap|"
    r"missing|calibrat|schema|column|priority score|focus list|tier|categor|churn|lapse rate|"
    r"retention rate|cancellation|dictionary|snapshot date|evaluat|model performance"
    r"|مؤشر|معادله|تعريف|ايراد|ربح|قيمه|عتبه|حدود|فجوه|ناقصه|مفقوده|معايره|فئه|فئات|تصنيف|الغاء|تقييم|اداء النموذج", re.I)
_PLAYBOOK_CUES = re.compile(
    r"playbook|retention|action|outreach|strategy|flag|escalat|human review|focus list|priority|guardrail|"
    r"reactivation|engage|دليل الاحتفاظ|كتيب|اجراء|اجراءات|استراتيجي|تصعيد|مراجعه بشريه|قائمه التركيز|الاولويه|"
    r"اعاده تنشيط|تواصل|احتفاظ", re.I)
_EXPLAIN_CUES = re.compile(
    r"explain|what is|what are|what does|define|meaning|difference|why"
    r"|اشرح|وضح|ما هو|ما هي|ما معني|تعريف|الفرق|لماذا|يعني", re.I)
_DOC_CUE = re.compile(
    r"playbook|policy|rules?|kpis?|document|guidance|categories used|explain|define"
    r"|دليل|سياسه|قواعد|وثيقه|وثائق|اشرح|وضح|المؤشرات|الفئات المستخدمه", re.I)
_DATA_EXCLUDE = re.compile(
    r"which customers|how many|list|top \d+|highest|lowest|latest snapshot|snapshot|summar"
    r"|اي (?:ال)?عملاء|كم عميل|كام|عدد|قائمه|اعلي|اكبر|اخطر|لقطه|ملخص|لخص", re.I)
_CUSTOMER_WORD = re.compile(r"\bcustomers?\b|عميل|عملاء|زبون|زبائن", re.I)
_RISK_WORD = re.compile(r"\b(risk|lapse|probabilit)|خطر|مخاطر|احتمال|انقطاع|تسرب|توقف", re.I)

# English phrases appended to Arabic questions so retrieval can match the English documents.
_RETRIEVAL_HINTS = [
    (r"ترويج|خصم|خصومات|عروض|حافز|موافقه|ميزانيه|هامش", "promotion policy discount approval rules margin budget"),
    (r"مؤشر|معادله", "KPI definitions formulas metrics"),
    (r"فئه|فئات|تصنيف|عتبه|حدود|مستوي|مستويات", "risk categories tiers thresholds Low Medium High"),
    (r"احتماليه|احتمال", "lapse probability p_lapse"),
    (r"احتفاظ|اجراء|اجراءات|استراتيجي|تواصل", "retention actions playbook recommended actions"),
    (r"قيمه العميل|ايراد|ربح", "customer value revenue profit data gap"),
    (r"ناقصه|مفقوده|فجوه|غير متوفر", "missing data gap"),
    (r"عالي|مرتفع", "high risk customers focus list"),
    (r"الغاء|ملغ", "cancellations repeated cancellation flag"),
    (r"تصعيد|مراجعه بشريه", "human review escalation"),
    (r"لقطه", "snapshot date"),
]


@dataclass
class Route:
    intent: str                                   # "policy" | "customer" | "mixed" | "product" | "evidence"
    needs_customer_data: bool = False
    needs_knowledge: bool = False
    needs_catalog: bool = False
    doc_types: tuple[str, ...] = KNOWLEDGE_ALL
    customer_ops: list[dict] = field(default_factory=list)
    snapshot_date: str | None = None
    reasons: list[str] = field(default_factory=list)
    language: str = "en"
    retrieval_query: str = ""


def _extract_ids(question: str) -> list[int]:
    q = _DATE_RE.sub(" ", question)
    ids = [int(m) for m in _ID_RE.findall(q)]
    ids += [int(m) for m in _BARE_ID_RE.findall(q) if int(m) not in ids]
    return list(dict.fromkeys(ids))


def _category(question: str) -> str | None:
    if re.search(r"\bhighest\b|\blowest\b", question, re.I) and not re.search(r"\bhigh[- ]risk\b|\bhigh\b(?!est)", question, re.I):
        pass_en = None
    else:
        m = re.search(r"\b(low|medium|high)[- ]?(?:risk|lapse)?\b(?!\s*(?:value|margin))", question, re.I)
        pass_en = m.group(1).title() if m else None
    if pass_en:
        return pass_en
    if re.search(r"عالي|مرتفع", question):
        return "High"
    if re.search(r"متوسط", question):
        return "Medium"
    if re.search(r"منخفض|قليل|ضعيف", question) and re.search(r"خطر|مخاطر|عملاء|عميل", question):
        return "Low"
    return None


def _knowledge_types(question: str, mixed: bool) -> tuple[str, ...]:
    types: list[str] = []
    if _PROMO_CUES.search(question):
        types.append("promotion_policy")
    if _KPI_CUES.search(question):
        types.append("business_rules")
    if _PLAYBOOK_CUES.search(question) or mixed:
        types.append("retention_playbook")
    if mixed and "business_rules" not in types:
        types.append("business_rules")  # tier thresholds / calibration caveats
    return tuple(dict.fromkeys(types)) or KNOWLEDGE_ALL


def _build_retrieval_query(question: str, qn: str, lang: str) -> str:
    if lang != "ar":
        return question
    hints = [eng for pat, eng in _RETRIEVAL_HINTS if re.search(pat, qn)]
    return (question + " " + " ".join(hints)).strip()


def route_question(question: str) -> Route:
    route = _route(question)
    route.language = detect_language(question)
    route.retrieval_query = _build_retrieval_query(question, normalize_text(question), route.language)
    return route


def _route(question: str) -> Route:
    q = normalize_text(question.strip())
    ids = _extract_ids(q)
    dates = _DATE_RE.findall(q)
    snapshot = dates[0] if dates else None

    if _EVIDENCE_FOLLOWUP.search(q) and not ids:
        return Route(intent="evidence", reasons=["asks to see the evidence behind the previous answer"])

    data_cue = bool(_DATA_CUES.search(q) or _DATA_CUES_AR.search(q)) or bool(ids) or bool(
        _CUSTOMER_WORD.search(q) and _RISK_WORD.search(q) and not _EXPLAIN_CUES.search(q))
    guidance_cue = bool(_GUIDANCE_CUES.search(q) or _GUIDANCE_CUES_AR.search(q))
    product_cue = bool(_PRODUCT_CUES.search(q)) and not data_cue

    # A pure "explain / playbook / policy" question is documents-only even if it mentions risk.
    if _DOC_CUE.search(q) and not ids and not _DATA_EXCLUDE.search(q):
        data_cue = False

    if product_cue and not guidance_cue:
        return Route(intent="product", needs_catalog=True, reasons=["asks about catalog products"])

    if data_cue:
        mixed = guidance_cue
        ops = _customer_ops(q, ids, snapshot, mixed)
        return Route(
            intent="mixed" if mixed else "customer",
            needs_customer_data=True,
            needs_knowledge=True,  # customer answers always get the tier/threshold caveats from the rules doc
            doc_types=_knowledge_types(q, mixed) if mixed else ("business_rules",),
            customer_ops=ops, snapshot_date=snapshot,
            reasons=["mentions customer/risk data" + (" and asks for guidance" if mixed else "")],
        )

    return Route(intent="policy", needs_knowledge=True, doc_types=_knowledge_types(q, False),
                 needs_catalog=bool(_PRODUCT_CUES.search(q)), reasons=["knowledge question answered from documents"])


def _customer_ops(q: str, ids: list[int], snapshot: str | None, mixed: bool = False) -> list[dict]:
    ops: list[dict] = []
    top_m = _TOPN_RE.search(q)
    top_n = int(next(g for g in top_m.groups() if g)) if top_m else 10
    top_n = max(1, min(top_n, 100))
    cat = _category(q)
    if ids:
        ops += [{"op": "lookup", "customer_id": i} for i in ids[:5]]
    wants_top = re.search(r"highest|riskiest|top|worst|lowest|attention|rank|sort|اعلي|اكبر|اخطر|ترتيب|رتب|اقل|ادني|اهتمام|انتباه|اولويه", q, re.I)
    if (re.search(r"summar|overview|distribution|breakdown|how many|counts?|number of|ملخص|لخص|نظره عامه|توزيع|كم |كام|عدد", q, re.I)
            or (mixed and not ids)
            or not (ids or cat or wants_top)):
        ops.append({"op": "summary"})
    if wants_top or (cat and not ids):
        ops.append({"op": "top", "n": top_n, "category": cat,
                    "ascending": bool(re.search(r"\blowest\b|\bbottom\b|اقل (?:ال)?(?:عملاء|خطر|احتمال)|ادني", q, re.I))})
    if re.search(r"categor|probabilit|difference|explain|فئه|فئات|احتمال|الفرق|اشرح", q, re.I):
        ops.append({"op": "explain_categories"})
    return ops


def extract_product_id(question: str) -> str | None:
    m = _PRODUCT_ID_RE.search(question)
    return m.group(1) if m and any(ch.isdigit() for ch in m.group(1)) else None
