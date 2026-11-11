"""Tests for hybrid mode: Google Gemini API backend LLM + local voice/TTS."""

from types import SimpleNamespace

import pytest

from app.agent.service import AgentService
from app.api.health import _check_google_llm, health
from app.config import settings
from app.main import _validate_config


def _run_coro(coro):
    """Step a synchronous mocked coroutine without Windows sandbox event-loop hangs."""
    try:
        coro.send(None)
    except StopIteration as done:
        return done.value
    raise AssertionError("Coroutine yielded unexpectedly")


def test_validate_config_does_not_require_ollama(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "secret_key", "local-dev-secret-key")
    monkeypatch.setattr(settings, "database_url", "sqlite:///./virtual_kam.db")
    monkeypatch.setattr(settings, "google_model", "gemini-3-flash-preview")
    monkeypatch.setattr(settings, "google_base_url", "https://generativelanguage.googleapis.com/v1beta")
    _validate_config()


def test_agent_requires_google_api_key():
    svc = AgentService(google_api_key="", google_model="gemini-3-flash-preview")
    with pytest.raises(RuntimeError, match="GOOGLE_API_KEY"):
        _run_coro(svc._call_google([{"role": "user", "content": "hi"}]))


def test_agent_calls_google_gemini_generate_content_with_404_fallback(monkeypatch):
    calls = []

    class DummyResp:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            calls.append((url, headers, json))
            if "gemini-2.5-flash" in url:
                return DummyResp(404, {"error": {"message": "retired model"}})
            return DummyResp(
                200,
                {"candidates": [{"content": {"parts": [{"text": "Observed revenue is ₹2,00,000."}]}}]},
            )

    monkeypatch.setattr("app.agent.service.httpx.AsyncClient", DummyClient)
    svc = AgentService(
        google_api_key="AIza-test-key",
        google_model="gemini-2.5-flash",
        google_base_url="https://generativelanguage.googleapis.com/v1beta/",
    )
    reply = _run_coro(
        svc._call_google([
            {"role": "system", "content": "Be a concise KAM."},
            {"role": "assistant", "content": "Namaste!"},
            {"role": "user", "content": "How are sales?"},
        ])
    )
    assert "₹2,00,000" in reply
    assert len(calls) == 2
    assert calls[0][0].endswith("/models/gemini-2.5-flash:generateContent")
    assert calls[1][0].endswith("/models/gemini-3-flash-preview:generateContent")
    assert calls[1][1]["x-goog-api-key"] == "AIza-test-key"
    assert calls[1][2]["system_instruction"] == {"parts": [{"text": "Be a concise KAM."}]}
    assert calls[1][2]["contents"] == [
        {"role": "model", "parts": [{"text": "Namaste!"}]},
        {"role": "user", "parts": [{"text": "How are sales?"}]},
    ]


def test_agent_executes_gemini_function_call_loop_preserving_thought_signature(monkeypatch):
    calls = []
    executed = []

    class DummyResp:
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, headers=None, json=None):
            calls.append(json)
            if len(calls) == 1:
                return DummyResp(
                    200,
                    {
                        "candidates": [
                            {
                                "content": {
                                    "role": "model",
                                    "parts": [
                                        {
                                            "functionCall": {
                                                "name": "search_catalog_skus",
                                                "args": {"query": "Beard"},
                                                "id": "call_123",
                                            },
                                            "thoughtSignature": "sig_abc_999",
                                        }
                                    ],
                                }
                            }
                        ]
                    },
                )
            return DummyResp(
                200,
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "Ayurvedic Beard Grooming Kit is out of stock (0 units)."}
                                ]
                            }
                        }
                    ]
                },
            )

    monkeypatch.setattr("app.agent.service.httpx.AsyncClient", DummyClient)
    svc = AgentService(google_api_key="AIza-test-key", google_model="gemini-3-flash-preview")

    async def fake_exec(tool_name, args):
        executed.append((tool_name, args))
        return {"matched_count": 1, "products": [{"sku_id": "sku-002", "current_stock": 0}]}

    monkeypatch.setattr(svc, "_execute_tool", fake_exec)
    extra_tools = {}
    reply = _run_coro(
        svc._call_google(
            [{"role": "user", "content": "How is Beard kit doing?"}],
            seller_id="demo-seller-001",
            channel="chat",
            extra_tool_results=extra_tools,
        )
    )
    assert "Ayurvedic Beard Grooming Kit" in reply
    assert executed == [("search_catalog_skus", {"query": "Beard", "seller_id": "demo-seller-001"})]
    assert "search_catalog_skus" in extra_tools
    second_contents = calls[1]["contents"]
    assert second_contents[1]["parts"][0]["thoughtSignature"] == "sig_abc_999"
    assert second_contents[2]["parts"][0]["functionResponse"]["id"] == "call_123"


def test_search_catalog_skus_matches_by_title(db_session, monkeypatch):
    from app.models import Product, Seller
    from app.agent.tools import search_catalog_skus

    seller = Seller(id="cat-seller-1", display_name="Cat Store", marketplace="Snapdeal", timezone="Asia/Kolkata")
    db_session.add(seller)
    db_session.add(
        Product(
            id="cat-sku-1",
            seller_id="cat-seller-1",
            sku_code="SD-TST-01",
            title="Basmati Rice 5kg",
            category="Grocery",
            selling_price=50000,
            unit_cost=35000,
            current_stock=0,
            supplier_lead_time_days=10,
        )
    )
    db_session.commit()

    monkeypatch.setattr("app.agent.tools._get_db", lambda: db_session)
    # Prevent _get_db cleanup from closing fixture session early
    monkeypatch.setattr(db_session, "close", lambda: None)
    res = search_catalog_skus("cat-seller-1", query="Basmati")
    assert res["matched_count"] == 1
    assert res["products"][0]["sku_id"] == "cat-sku-1"
    assert res["products"][0]["status"] == "out_of_stock"


def test_health_reports_google_dependency(db_session, monkeypatch):
    monkeypatch.setattr(settings, "google_api_key", "")
    resp = SimpleNamespace(status_code=200)
    payload = health(response=resp, db=db_session)
    assert set(payload["dependencies"].keys()) == {"database", "google"}
    assert payload["dependencies"]["database"]["status"] == "ok"
    assert payload["dependencies"]["google"]["status"] == "warning"
    assert _check_google_llm()["status"] == "warning"

