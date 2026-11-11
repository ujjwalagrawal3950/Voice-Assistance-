"""Tests for Indian currency, metric, and acronym speech normalization."""

from app.agent.service import AgentService


def test_normalize_indian_currency_phrases():
    raw = "Last month sales were ₹2,00,000, this month ₹1,35,000, and ASP stayed ₹500."
    out = AgentService._normalize_for_speech(raw)
    assert "2 lakh rupees" in out
    assert "1 lakh 35 thousand rupees" in out
    assert "500 rupees" in out


def test_normalize_crores_thousands_and_decimals():
    assert "40 thousand rupees" in AgentService._normalize_for_speech("Potential recovery ~₹40,000")
    assert "about 40 thousand rupees" in AgentService._normalize_for_speech("~₹40,000")
    assert "1 crore 25 lakh rupees" in AgentService._normalize_for_speech("₹1,25,00,000")
    assert "1.35 lakh rupees" in AgentService._normalize_for_speech("₹1.35L")


def test_normalize_arrows_percentages_and_acronyms():
    raw = "Orders fell 400 → 270 (-32.5%), OOS SKUs 5 → 18, ASP ₹500, SLA breaches rose."
    out = AgentService._normalize_for_speech(raw)
    assert "400 to 270" in out
    assert "minus 32.5 percent" in out
    assert "out of stock products 5 to 18" in out
    assert "average selling price 500 rupees" in out
    assert "pickup timeline breaches" in out


def test_make_spoken_text_only_for_voice_channel():
    svc = AgentService()
    msg = "**Headline:** Sales dropped ₹2,00,000 → ₹1,35,000 (-32.5%).\n- 18 SKUs are OOS."
    assert svc._make_spoken_text(msg, "chat") is None
    spoken = svc._make_spoken_text(msg, "voice")
    assert spoken is not None
    assert "2 lakh rupees to 1 lakh 35 thousand rupees" in spoken
    assert "18 products are out of stock" in spoken
    assert "*" not in spoken

