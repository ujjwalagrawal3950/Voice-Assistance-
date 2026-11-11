"""Domain guardrails, edge-case input validation, and output safety checks for Virtual KAM."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal, Optional

MAX_MESSAGE_CHARS = 3500

OFF_TOPIC_REFUSAL = (
    "I can't help with that. I am your Snapdeal Virtual KAM, so I can only "
    "assist with your store's sales, inventory, pricing, cancellations, and business planning."
)

INJECTION_REFUSAL = (
    "I can't help with overriding instructions or sharing internal system details. "
    "I am your Snapdeal Virtual KAM and can only assist with your store's sales, "
    "inventory, pricing, cancellations, and business planning."
)

NOISE_PROMPT = (
    "I didn't catch a clear business question. Please ask about your store's "
    "sales, inventory, pricing, cancellations, or business planning."
)

TOO_LONG_REPLY = (
    "Your message is too long to process reliably. Please ask a concise question "
    "about your store's sales, inventory, pricing, cancellations, or business planning."
)

GREETING_REPLY = (
    "Namaste! I'm your Snapdeal Virtual KAM. What would you like to review today—"
    "your recent sales performance, out-of-stock products, cancellations, or a restocking plan?"
)

FAREWELL_REPLY = (
    "You're welcome! Let me know whenever you'd like a quick summary of our discussion "
    "or want to review your pending recommendations."
)

CAPABILITY_REPLY = (
    "I'm your Snapdeal Virtual KAM. I can diagnose sales drops, quantify stockout losses, "
    "analyze cancellations and margins, simulate restocking budgets and delays, check "
    "upcoming festivals, and prepare recommendations for your approval. I can't help with "
    "non-business topics like coding or general trivia—what store topic should we look at?"
)

EMPTY_FALLBACK_REPLY = (
    "I couldn't generate a clear response for that. Please rephrase your question about "
    "your store's sales, inventory, pricing, cancellations, or business planning."
)

ScopeCategory = Literal[
    "empty_or_noise",
    "too_long",
    "prompt_injection",
    "off_topic",
    "mixed_off_topic",
    "greeting",
    "farewell",
    "capability",
    "needs_scope_check",
    "in_scope",
]


@dataclass(frozen=True)
class QueryScopeResult:
    """Structured outcome of pre-LLM edge-case and scope classification."""

    category: ScopeCategory
    reason: str = ""
    direct_reply: Optional[str] = None
    has_business_signal: bool = False
    is_followup: bool = False


_PURE_GREETING_PATTERN = re.compile(
    r"^(?:hi+|hello+|hey+|hlo+|namaste|namaskar|hola|good\s+(?:morning|afternoon|evening|day))"
    r"(?:[\s,!.\-?]+(?:there|kam|assistant|sir|ma'?am|madam|ji|team|ai|bot))*[\s,!.\-?]*$",
    re.IGNORECASE,
)

_PURE_FAREWELL_PATTERN = re.compile(
    r"^(?:thanks?(?:\s+you)?|thank\s+you(?:\s+(?:very\s+much|so\s+much))?|ty|thx|"
    r"bye+|goodbye|good\s+bye|see\s+you|take\s+care|stop)"
    r"(?:[\s,!.\-?]+(?:kam|assistant|sir|ji|bye|thanks))?[\s,!.\-?]*$",
    re.IGNORECASE,
)

_SOFT_ACK_NO_HISTORY_PATTERN = re.compile(
    r"^(?:ok(?:ay)?|got\s+it|alright|cool|great|nice|done)[\s,!.\-?]*$",
    re.IGNORECASE,
)

_CAPABILITY_PATTERN = re.compile(
    r"^(?:who\s+are\s+you|what\s+are\s+you|what\s+can\s+you\s+do|how\s+can\s+you\s+help(?:\s+me)?|"
    r"what\s+do\s+you\s+do|help\s+me\s+understand\s+your\s+(?:features|capabilities)|your\s+role)[\s?!.]*$",
    re.IGNORECASE,
)

_NOISE_TRANSCRIPT_PATTERN = re.compile(
    r"^(?:\[.*\]|\(.*\)|uh+|um+|umm+|hmm+|hm+|erm+|ah+|oh+|err+|testing|test\s*123|mic\s*check)$",
    re.IGNORECASE,
)

_PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+(?:all\s+|any\s+|your\s+|the\s+)?(?:previous|prior|above|system)?\s*instructions?\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+(?:all\s+|your\s+|the\s+)?(?:rules?|instructions?|prompts?|guidelines?)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:reveal|show|print|dump|repeat|output|leak|display)\s+(?:me\s+)?(?:your\s+|the\s+)?"
        r"(?:system\s+prompt|developer\s+instructions?|hidden\s+(?:rules?|prompt)|api\s*keys?|secrets?|credentials?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|switch\s+role\s+to|roleplay\s+as)\s+"
        r"(?!a\s+(?:snapdeal|virtual|key\s+account|kam|business|commerce|seller))\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:jailbreak|dan\s+mode|do\s+anything\s+now|developer\s+mode|bypass\s+(?:rules?|guardrails?|safety))\b", re.IGNORECASE),
)

_BUSINESS_WORD_PATTERN = re.compile(
    r"\b(?:"
    r"sales?|revenue|gmv|orders?|units?|asp|average\s+selling\s+price|price|pricing|"
    r"margin|margins|profit|profits|profitability|loss|losses|roi|budget|budgets|cost|costs|"
    r"invest|investment|spend|spending|allocate|allocation|delay|delayed|"
    r"stock|stocks|stockout|stockouts|out\s+of\s+stock|oos|restock|restocking|replenish|replenishment|reorder|reordering|"
    r"inventory|warehouse|supplier|suppliers|vendor|vendors|lead\s+time|moq|sku|skus|catalog|catalogue|"
    r"product|products|item|items|category|categories|listing|listings|visibility|conversion|"
    r"traffic|views|clicks|impressions|cancel|cancels|cancelled|canceled|cancellation|cancellations|"
    r"rto|return|returns|refund|refunds|sla|pickup|dispatch|delivery|"
    r"festival|festivals|festive|diwali|holi|eid|christmas|navratri|rakhi|pongal|onam|wedding|payday|"
    r"season|seasonal|seasonality|trend|trends|forecast|forecasting|predict|demand|"
    r"recommendation|recommendations|recommend|approve|approved|reject|rejected|action|actions|"
    r"alert|alerts|proactive|dashboard|kpi|kpis|metric|metrics|summary|summarize|summarise|wrap\s+up|"
    r"what\s+if|what-if|scenario|scenarios|simulate|simulation|growth|grow|decline|declining|slump|"
    r"drop|dropped|dropping|fall|falling|boost|improve|store|shop|seller|marketplace|snapdeal|"
    r"competitor|competitors|rival|discount|discounts|promo|promotion|promotions|campaign|campaigns|ads|"
    r"bundle|bundling|slow\s+moving|dead\s+stock|customer|customers|buyer|buyers|purchase\s+order|credit|"
    r"business|planning|strategy|diagnostic|diagnose|root\s+cause|outcome|outcomes|"
    r"dukan|dukaan|bikri|maal|saman|samaan|munafa|nuksan|nuksaan|fayda|ghata|paisa|paise|"
    r"rupay|rupaye|rupee|rupees|kharch|kharcha|lagana|tyohar|tyohaar|shaadi|grahak|vyapar|dhandha|kamai|"
    r"basmati|rice|kurti|shoes?|headphones?|airdopes|lipstick|trimmer|grooming|beard|water|tea|chips|dal|shampoo|soap"
    r")\b",
    re.IGNORECASE,
)

_BUSINESS_SYMBOL_PATTERN = re.compile(
    r"(?:₹|\b(?:rs\.?|inr)\s*\d+|\bsku-\d+|\bSD-[A-Z]+-\d+|\b\d+(?:\.\d+)?\s*(?:lakh|lac|crore)\b)",
    re.IGNORECASE,
)

# Standalone analytical question patterns (must express an actual business question, not just "for my sales")
_GENUINE_BUSINESS_ASK_PATTERN = re.compile(
    r"\b(?:"
    r"why\s+(?:are|is|did)\s+(?:my\s+)?(?:sales|revenue|orders?|cancellations?|returns?|conversion|stock)|"
    r"(?:why\s+)?(?:my\s+)?(?:sales|revenue|orders?)\s+(?:are|is|went|have)?\s*(?:down|drop|dropped|dropping|declining|falling|low)|"
    r"sales\s+(?:down|drop|dropped|slump|decline|trend|performance)|"
    r"revenue\s+(?:down|drop|change|decomposition)|"
    r"out\s+of\s+stock|stockout|inventory\s+health|stock\s+cover|low\s+stock|dead\s+stock|"
    r"which\s+(?:sku|skus|product|products|category|categories|item|items)|"
    r"check\s+(?:my\s+)?(?:stock|margin|lead\s+time|sales|orders?|cancellations?|budget|sku)|"
    r"how\s+(?:many|much)\s+.*(?:sold|stock|units|orders|margin|cost|lost|revenue)|"
    r"(?:restock|replenish|reorder)\s+plan|what\s+should\s+i\s+(?:restock|reorder|do|prioritize)|"
    r"what[\s-]+if|if\s+i\s+(?:spend|invest|delay|allocate)|"
    r"cancellation\s+(?:rate|breakdown|spike|reason)|return\s+rate|"
    r"festival\s+calendar|diwali|wedding\s+season|payday|"
    r"proactive\s+alerts?|recommendations?|outcome\s+track\s+record|"
    r"summarize|summarise|summary\s+of\s+(?:my\s+)?(?:call|store|sales|month)"
    r")\b",
    re.IGNORECASE,
)

_OFF_TOPIC_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "coding",
        re.compile(
            r"(?:"
            r"\b(?:linked\s+list|doubly\s+linked|binary\s+tree|binary\s+search|hash\s*map|hash\s*table|"
            r"depth\s+first|breadth\s+first|dijkstra|dynamic\s+programming|leetcode|hackerrank|codeforces|"
            r"big[- ]o|time\s+complexity|space\s+complexity|recursion|fibonacci|palindrome|factorial|"
            r"two\s+sum|bubble\s+sort|merge\s*sort|quick\s*sort|heap\s*sort|topological\s+sort|"
            r"sql\s+query|syntax\s+error|compile\s+error|null\s+pointer|segfault)\b|"
            r"\b(?:write|give|show|generate|create|build|solve|implement|debug|fix|refactor)\s+"
            r"(?:a\s+|an\s+|me\s+|the\s+)?"
            r"(?:python|java|javascript|typescript|c\+\+|c#|golang|rust|ruby|php|sql|html|css|bash|shell|regex)?\s*"
            r"(?:code|program|script|function|method|class|query|snippet|algorithm)\b|"
            r"\b(?:in|using)\s+(?:python|java|javascript|typescript|c\+\+|c#|golang|rust|sql|react|node\.?js|angular|vue)\b|"
            r"\breverse\s+(?:a\s+|an\s+|the\s+)?(?:linked\s+list|array|string|integer|number|binary\s+tree|stack|queue|nodes?)\b|"
            r"\bdef\s+[a-z_]\w*\s*\(|public\s+static\s+void|#include\s*<|console\.log\(|SELECT\s+\*?\s+FROM\b"
            r")",
            re.IGNORECASE,
        ),
    ),
    (
        "creative_writing",
        re.compile(
            r"\b(?:write|compose|tell|sing|crack)\s+(?:(?:me|us)\s+)?(?:a\s+|an\s+|some\s+)?(?:"
            r"poem|poetry|story|novel|song|lyrics|rap|essay|haiku|joke|jokes|riddle|shayari|fanfiction|fun\s+fact"
            r")\b|\broast\s+me\b",
            re.IGNORECASE,
        ),
    ),
    (
        "academics_trivia",
        re.compile(
            r"(?:\b(?:"
            r"capital\s+of\s+[a-z]+|who\s+invented|who\s+discovered|"
            r"who\s+(?:is|was)\s+the\s+(?:first|current|last|ceo|founder|owner|president|prime\s+minister|king|queen|captain|coach)|"
            r"who\s+won\s+(?:the\s+)?(?:(?:last|first|recent|latest|previous|\d{4})\s+)?(?:nobel|oscar|grammy|election|world\s+cup|ipl|match|tournament)|"
            r"meaning\s+of\s+life|solve\s+(?:this\s+|the\s+)?(?:equation|integral|derivative|triangle)|"
            r"calculate\s+(?:the\s+)?(?:area|volume|circumference|derivative|integral|factorial|fibonacci|square\s+root|hypotenuse)|"
            r"quadratic\s+equation|trigonometry|calculus|photosynthesis|periodic\s+table|solar\s+system|"
            r"black\s+hole|quantum\s+(?:mechanics|physics|computing|entanglement)|world\s+war\s+(?:1|2|i|ii)|"
            r"tallest\s+mountain|largest\s+ocean|"
            r"translate\s+.*\s+(?:to|into)\s+(?:french|spanish|german|japanese|korean|italian|latin|arabic|russian)"
            r")\b|^\s*(?:what\s+is\s+|solve\s+|calculate\s+)?\d+\s*[\+\-\*/\^]\s*\d+(?:\s*[\+\-\*/\^]\s*\d+)*\s*[=?]*\s*$)",
            re.IGNORECASE,
        ),
    ),
    (
        "lifestyle_personal",
        re.compile(
            r"\b(?:"
            r"recipe\s+(?:for|of)|[a-z]+\s+recipe\b|how\s+to\s+(?:cook|bake|brew|prepare)\s+(?:biryani|pasta|cake|pizza|curry|maggi|noodles|omelette|[a-z]+)|"
            r"symptoms?\s+of|medicine\s+(?:for|should\s+i)|what\s+(?:medicine|tablet|pill)\b|medical\s+advice|"
            r"diagnose\s+my\s+(?:pain|fever|headache|cough)|(?:i\s+have\s+|suffering\s+from\s+)(?:a\s+)?(?:fever|headache|cold|cough|stomach\s*ache)\b|"
            r"workout\s+routine|gym\s+split|horoscope|zodiac\s+sign|tarot\s+reading|astrology|"
            r"relationship\s+advice|dating\s+tips|divorce\s+lawyer"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "investing_gambling",
        re.compile(
            r"\b(?:"
            r"bitcoin|cryptocurrency|crypto|ethereum|dogecoin|nft|stock\s+market|share\s+market|"
            r"nifty\s*50|sensex|mutual\s+funds?|stocks\s+to\s+buy|option\s+trading|forex\s+trading|"
            r"dream11|fantasy\s+cricket|betting\s+odds|lottery\s+numbers"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "sports_weather_travel",
        re.compile(
            r"\b(?:"
            r"cricket\s+match\s+score|live\s+score|ipl\s+points\s+table|football\s+match|fifa\s+world\s+cup|"
            r"movie\s+review|best\s+movies\s+on|netflix\s+recommendation|celebrity\s+gossip|"
            r"weather\s+(?:today|in|forecast)|temperature\s+(?:today|outside|forecast)|rain\s+forecast|"
            r"flight\s+ticket|hotel\s+booking"
            r")\b",
            re.IGNORECASE,
        ),
    ),
)

_FOLLOWUP_HINT_PATTERN = re.compile(
    r"\b(?:what\s+about|how\s+about|which\s+one|that\s+one|the\s+(?:first|second|third)\s+one|"
    r"this\s+one|those|them|it|more\s+details|explain\s+that|why\s+did\s+that|compare|versus|vs|"
    r"last\s+week|this\s+week|previous\s+month|instead|go\s+ahead|yes|no|ok|okay|alright|proceed)\b",
    re.IGNORECASE,
)

# Catches code syntax even if the LLM slips (without flagging Markdown tables or SKUs)
_CODE_LEAK_PATTERN = re.compile(
    r"(?:```(?:python|py|javascript|js|typescript|ts|java|cpp|c\+\+|c|sql|bash|sh)\b"
    r"|^\s*def\s+[a-z_]\w*\s*\([^)]*\)\s*:"
    r"|^\s*public\s+(?:class|static)\s+"
    r"|#include\s*<[^>]+>"
    r"|curr\.next\s*="
    r"|node\.next\b"
    r"|\bfunction\s+[a-z_]\w*\s*\([^)]*\)\s*\{)",
    re.IGNORECASE | re.MULTILINE,
)


def _contains_business_signal(msg_lower: str) -> bool:
    """Return True if the message contains clear store, e-commerce, Hinglish business, or planning tokens."""
    if _BUSINESS_WORD_PATTERN.search(msg_lower):
        return True
    if _BUSINESS_SYMBOL_PATTERN.search(msg_lower):
        return True
    return False


def _detect_off_topic_reason(msg_lower: str) -> Optional[str]:
    """Match explicit non-business topic rules deterministically."""
    for reason, pattern in _OFF_TOPIC_RULES:
        if pattern.search(msg_lower):
            return reason
    return None


def _is_gibberish_or_empty_noise(stripped: str) -> bool:
    """Detect blank inputs, punctuation soup, Whisper noise tags, or keyboard mash."""
    if not stripped:
        return True
    if _NOISE_TRANSCRIPT_PATTERN.match(stripped):
        return True
    if not re.search(r"[A-Za-z0-9\u0900-\u097F]", stripped):
        return True
    # Pure punctuation/symbols with fewer than 2 alphanumeric characters (unless greeting already matched)
    alnum_chars = re.findall(r"[A-Za-z0-9\u0900-\u097F]", stripped)
    if len(alnum_chars) < 2:
        return True
    # Single consonant-heavy or keyboard-row mash (e.g., "asdfghjklqwr", "qwertyuiop")
    tokens = re.findall(r"[A-Za-z]+", stripped)
    if len(tokens) == 1 and len(tokens[0]) >= 6:
        word = tokens[0].lower()
        if not _contains_business_signal(word) and (
            not re.search(r"[aeiouy]", word)
            or bool(re.search(r"[bcdfghjklmnpqrstvwxz]{6,}", word))
            or any(seq in word for seq in ("qwerty", "asdfg", "zxcvb"))
        ):
            return True
    return False


def classify_query_scope(
    message: str,
    history: Optional[list[dict[str, str]]] = None,
) -> QueryScopeResult:
    """Classify seller message before tool/LLM orchestration to enforce scope and handle edge cases."""
    raw = message or ""
    stripped = raw.strip()

    if len(stripped) > MAX_MESSAGE_CHARS:
        return QueryScopeResult(category="too_long", reason="exceeds_max_chars", direct_reply=TOO_LONG_REPLY)

    if _is_gibberish_or_empty_noise(stripped):
        return QueryScopeResult(category="empty_or_noise", reason="noise_or_empty", direct_reply=NOISE_PROMPT)

    msg_lower = stripped.lower()

    for inj_pat in _PROMPT_INJECTION_PATTERNS:
        if inj_pat.search(msg_lower):
            return QueryScopeResult(category="prompt_injection", reason="injection", direct_reply=INJECTION_REFUSAL)

    off_topic_reason = _detect_off_topic_reason(msg_lower)
    has_business = _contains_business_signal(msg_lower)

    if off_topic_reason:
        # Refuse cleanly unless there is an independent, explicit store analytics/planning question too.
        if has_business and _GENUINE_BUSINESS_ASK_PATTERN.search(msg_lower):
            return QueryScopeResult(
                category="mixed_off_topic",
                reason=off_topic_reason,
                has_business_signal=True,
            )
        return QueryScopeResult(
            category="off_topic",
            reason=off_topic_reason,
            direct_reply=OFF_TOPIC_REFUSAL,
            has_business_signal=False,
        )

    if _PURE_GREETING_PATTERN.match(stripped):
        return QueryScopeResult(category="greeting", reason="greeting", direct_reply=GREETING_REPLY)

    if _PURE_FAREWELL_PATTERN.match(stripped):
        return QueryScopeResult(category="farewell", reason="farewell", direct_reply=FAREWELL_REPLY)

    if not history and _SOFT_ACK_NO_HISTORY_PATTERN.match(stripped):
        return QueryScopeResult(category="farewell", reason="ack_no_history", direct_reply=FAREWELL_REPLY)

    if _CAPABILITY_PATTERN.match(stripped):
        return QueryScopeResult(category="capability", reason="capability", direct_reply=CAPABILITY_REPLY)

    if has_business:
        return QueryScopeResult(category="in_scope", has_business_signal=True)

    has_history = bool(history)
    is_followup = has_history and bool(_FOLLOWUP_HINT_PATTERN.search(msg_lower)) and len(stripped.split()) <= 16
    if is_followup:
        return QueryScopeResult(category="in_scope", has_business_signal=False, is_followup=True)

    return QueryScopeResult(
        category="needs_scope_check",
        reason="ambiguous_or_unclassified",
        has_business_signal=False,
        is_followup=False,
    )


def build_scope_system_directive(scope: QueryScopeResult) -> str:
    """Return high-priority system instructions matching the classified query scope."""
    base_boundary = (
        "STRICT DOMAIN BOUNDARY (NON-NEGOTIABLE — OVERRIDES ALL FORMATTING RULES):\n"
        "- You are strictly a Snapdeal Virtual Key Account Manager (KAM). You ONLY assist with e-commerce "
        "store analytics, sales, inventory, SKUs, pricing, margins, cancellations, returns, promotions/visibility, "
        "budgets, supplier lead times, and business planning.\n"
        "- NEVER answer general trivia, homework/math puzzles, recipes, medical/legal/personal advice, creative "
        "writing (poems/stories/jokes/songs), or programming/coding/DSA questions (Python, JS, SQL, linked lists, etc.).\n"
        "- NEVER write programming code blocks or create clever metaphors connecting off-topic prompts to sales.\n"
        f"- For any non-business request, reply DIRECTLY with: \"{OFF_TOPIC_REFUSAL}\""
    )

    if scope.category == "mixed_off_topic":
        return (
            f"{base_boundary}\n"
            f"- MIXED REQUEST DETECTED (blocked topic: {scope.reason}): First state in ONE plain sentence that "
            "you can't help with the non-business/coding request, DO NOT write any code or analogies to coding, "
            "and then answer ONLY the legitimate store business question."
        )

    if scope.category == "needs_scope_check":
        return (
            f"{base_boundary}\n"
            "- SCOPE CHECK REQUIRED: First judge whether the user's message is genuinely about an e-commerce store, "
            "product catalog, selling, or business planning (including indirect or Hinglish phrasings).\n"
            "- If it IS NOT business/planning related (for example trivia, science, sports, translation, personal "
            "topics, random facts), STOP and output ONLY the exact refusal sentence above with zero KPIs, zero "
            "numbered 1-5 report sections, and zero metaphors.\n"
            "- If it IS a genuine store/product/planning question, call the relevant tool (`search_catalog_skus`, "
            "`get_dashboard_kpis`, etc.) and answer accurately using real observed data."
        )

    return base_boundary


def contains_disallowed_code_or_bypass(text: str) -> bool:
    """Detect leaked programming code syntax in an assistant reply."""
    if not text:
        return False
    return bool(_CODE_LEAK_PATTERN.search(text))


def sanitize_assistant_reply(reply: str, scope: QueryScopeResult) -> tuple[str, bool]:
    """Ensure post-LLM text is non-empty and free of leaked programming code blocks."""
    cleaned = (reply or "").strip()
    if not cleaned:
        return EMPTY_FALLBACK_REPLY, True

    if contains_disallowed_code_or_bypass(cleaned):
        if scope.category in ("off_topic", "prompt_injection", "needs_scope_check"):
            return OFF_TOPIC_REFUSAL, True
        # Mixed turn: strip fenced code blocks and return a clean business-only fallback if nothing coherent remains.
        stripped_code = re.sub(r"```[\s\S]*?```", "", cleaned).strip()
        if not stripped_code or contains_disallowed_code_or_bypass(stripped_code):
            return OFF_TOPIC_REFUSAL, True
        return stripped_code, True

    return cleaned, False
