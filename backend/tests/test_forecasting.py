"""Unit tests for demand forecasting service."""

from datetime import date, timedelta

import pytest

from app.services.forecasting import (
    moving_average_forecast,
    seasonal_naive_forecast,
    backtest_forecast,
    get_forecast,
    calculate_replenishment_recommendation,
)


def _add_rows(session, seller_id: str, sku_id: str, start_date: date, days: int, base_units: int = 10):
    from app.models import DailyPerformance

    rows = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        # Deterministic pattern: weekday vs weekend variation
        units = base_units + (2 if d.weekday() >= 5 else 0)
        rows.append(DailyPerformance(
            seller_id=seller_id,
            sku_id=sku_id,
            perf_date=d,
            units_sold=units,
            gross_sales=units * 50000,
            discounts=0,
            net_sales=units * 50000,
            views=units * 10,
            clicks=units * 2,
            orders=units,
            cancellations=0,
            returns=0,
            dispatched_units=units,
            stockout_indicator=False,
            data_quality="observed",
            source="test",
        ))
    session.add_all(rows)
    session.commit()


class TestMovingAverageForecast:
    def test_returns_forecast(self, db_session):
        from app.models import Seller, Product

        seller = Seller(id="s1", display_name="Test", marketplace="mock")
        db_session.add(seller)
        db_session.add(Product(
            id="sku-1", seller_id="s1", sku_code="T-1", title="Test",
            category="Cat", selling_price=50000, unit_cost=40000, current_stock=50,
            supplier_lead_time_days=3, minimum_order_quantity=1, active=True,
        ))
        db_session.commit()

        start = date.today() - timedelta(days=29)
        _add_rows(db_session, "s1", "sku-1", start, days=30, base_units=10)

        result = moving_average_forecast(db_session, "s1", "sku-1", horizon_days=7, lookback_days=30)
        assert result["model"] == "moving_average"
        assert len(result["forecast"]) == 7
        assert result["forecast"][0]["forecast_units"] >= 10.0
        assert result["data_status"] == "estimated"
        assert "data_quality_caveats" in result
        assert result["festival_uplift_type"] == "scenario-only"

    def test_no_history(self, db_session):
        from app.models import Seller

        seller = Seller(id="s1", display_name="Test", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        result = moving_average_forecast(db_session, "s1", "sku-missing", horizon_days=7)
        assert "error" in result


class TestSeasonalNaiveForecast:
    def test_returns_forecast(self, db_session):
        from app.models import Seller, Product

        seller = Seller(id="s1", display_name="Test", marketplace="mock")
        db_session.add(seller)
        db_session.add(Product(
            id="sku-1", seller_id="s1", sku_code="T-1", title="Test",
            category="Cat", selling_price=50000, unit_cost=40000, current_stock=50,
            supplier_lead_time_days=3, minimum_order_quantity=1, active=True,
        ))
        db_session.commit()

        start = date.today() - timedelta(days=83)
        _add_rows(db_session, "s1", "sku-1", start, days=84, base_units=10)

        result = seasonal_naive_forecast(db_session, "s1", "sku-1", horizon_days=7, lookback_days=84)
        assert result["model"] == "seasonal_naive"
        assert len(result["forecast"]) == 7
        assert "weekday_averages" in result
        assert result["data_status"] == "estimated"

    def test_insufficient_history(self, db_session):
        from app.models import Seller

        seller = Seller(id="s1", display_name="Test", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        result = seasonal_naive_forecast(db_session, "s1", "sku-1", horizon_days=7)
        assert "error" in result
        assert "Insufficient history" in result["error"]


class TestBacktest:
    def test_returns_metrics(self, db_session):
        from app.models import Seller, Product

        seller = Seller(id="s1", display_name="Test", marketplace="mock")
        db_session.add(seller)
        db_session.add(Product(
            id="sku-1", seller_id="s1", sku_code="T-1", title="Test",
            category="Cat", selling_price=50000, unit_cost=40000, current_stock=50,
            supplier_lead_time_days=3, minimum_order_quantity=1, active=True,
        ))
        db_session.commit()

        start = date.today() - timedelta(days=179)
        _add_rows(db_session, "s1", "sku-1", start, days=180, base_units=10)

        result = backtest_forecast(db_session, "s1", "sku-1", method="moving_average")
        assert result["method"] == "moving_average"
        assert result["mae"] is not None
        assert result["wape"] is not None
        assert result["train_days"] > 0
        assert result["test_days"] > 0

    def test_insufficient_history(self, db_session):
        from app.models import Seller

        seller = Seller(id="s1", display_name="Test", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        result = backtest_forecast(db_session, "s1", "sku-1")
        assert "error" in result


class TestReplenishment:
    def test_returns_recommendation(self, db_session):
        from app.models import Seller, Product

        seller = Seller(
            id="s1", display_name="Test", marketplace="mock",
            available_replenishment_budget=10000000,  # ₹1,00,000
            storage_capacity=10000,
        )
        db_session.add(seller)
        db_session.add(Product(
            id="sku-1", seller_id="s1", sku_code="T-1", title="Test",
            category="Cat", selling_price=50000, unit_cost=40000,
            current_stock=10, incoming_stock=0,
            supplier_lead_time_days=3, minimum_order_quantity=1,
            minimum_margin=0.10, active=True,
        ))
        db_session.commit()

        start = date.today() - timedelta(days=29)
        _add_rows(db_session, "s1", "sku-1", start, days=30, base_units=10)

        result = calculate_replenishment_recommendation(db_session, "s1", "sku-1")
        assert "error" not in result
        assert result["sku_id"] == "sku-1"
        assert result["recommended_reorder_quantity"] >= 0
        assert result["can_order"] is True
        assert result["within_budget"] is True
        assert result["margin_ok"] is True
        assert result["data_status"] == "estimated"

    def test_over_budget_blocks_order(self, db_session):
        from app.models import Seller, Product

        seller = Seller(
            id="s1", display_name="Test", marketplace="mock",
            available_replenishment_budget=1000,  # Very small budget
            storage_capacity=10000,
        )
        db_session.add(seller)
        db_session.add(Product(
            id="sku-1", seller_id="s1", sku_code="T-1", title="Test",
            category="Cat", selling_price=50000, unit_cost=40000,
            current_stock=0, incoming_stock=0,
            supplier_lead_time_days=3, minimum_order_quantity=1,
            minimum_margin=0.10, active=True,
        ))
        db_session.commit()

        start = date.today() - timedelta(days=29)
        _add_rows(db_session, "s1", "sku-1", start, days=30, base_units=50)

        result = calculate_replenishment_recommendation(db_session, "s1", "sku-1")
        assert result["can_order"] is False
        assert result["within_budget"] is False
