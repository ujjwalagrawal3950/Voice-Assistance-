"""Unit tests for deterministic KPI calculations."""

from datetime import date, timedelta

import pytest

from app.services.kpi import (
    calculate_gross_sales,
    calculate_net_sales,
    calculate_orders,
    calculate_units_sold,
    calculate_average_selling_price,
    calculate_cancellation_rate,
    calculate_return_rate,
    calculate_conversion_rate,
    calculate_stockout_sku_count,
    calculate_inventory_value,
    calculate_stock_cover_days,
    period_over_period_change,
)


def _make_row(
    session,
    seller_id: str,
    sku_id: str,
    perf_date: date,
    units_sold: int = 10,
    gross_sales: int = 50000,
    discounts: int = 5000,
    net_sales: int = 45000,
    views: int = 100,
    clicks: int = 20,
    orders: int = 8,
    conversion_rate: float = 0.08,
    cancellations: int = 1,
    returns: int = 0,
    dispatched_units: int = 7,
    stockout_indicator: bool = False,
    data_quality: str = "observed",
):
    from app.models import DailyPerformance

    row = DailyPerformance(
        seller_id=seller_id,
        sku_id=sku_id,
        perf_date=perf_date,
        units_sold=units_sold,
        gross_sales=gross_sales,
        discounts=discounts,
        net_sales=net_sales,
        views=views,
        clicks=clicks,
        orders=orders,
        conversion_rate=conversion_rate,
        cancellations=cancellations,
        returns=returns,
        dispatched_units=dispatched_units,
        stockout_indicator=stockout_indicator,
        data_quality=data_quality,
        source="test",
    )
    session.add(row)
    session.commit()
    return row


class TestGrossSales:
    def test_gross_sales_sum(self, db_session):
        from app.models import Seller

        seller = Seller(
            id="seller-1", display_name="Test Seller", marketplace="mock-marketplace"
        )
        db_session.add(seller)
        db_session.commit()

        today = date.today()
        _make_row(db_session, "seller-1", "sku-1", today, gross_sales=10000)
        _make_row(db_session, "seller-1", "sku-2", today, gross_sales=20000)

        result = calculate_gross_sales(db_session, "seller-1", today, days=30)
        assert result["value"] == 30000
        assert result["currency"] == "INR"
        assert result["data_status"] == "calculated"
        assert "formula" in result
        assert "period_start" in result
        assert "period_end" in result

    def test_gross_sales_empty_period(self, db_session):
        from app.models import Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        result = calculate_gross_sales(db_session, "seller-1", date.today(), days=30)
        assert result["value"] == 0


class TestNetSales:
    def test_net_sales_formula(self, db_session):
        from app.models import Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        today = date.today()
        # net_sales = gross_sales - discounts
        _make_row(db_session, "seller-1", "sku-1", today, gross_sales=10000, discounts=2000, net_sales=8000)

        result = calculate_net_sales(db_session, "seller-1", today, days=30)
        assert result["value"] == 8000


class TestASP:
    def test_asp_calculation(self, db_session):
        from app.models import Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        today = date.today()
        # net_sales = 10000, orders = 4 -> ASP = 2500
        _make_row(
            db_session, "seller-1", "sku-1", today, net_sales=10000, orders=4
        )

        result = calculate_average_selling_price(db_session, "seller-1", today, days=30)
        assert result["value"] == 2500  # paise

    def test_asp_none_when_no_orders(self, db_session):
        from app.models import Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        result = calculate_average_selling_price(db_session, "seller-1", date.today(), days=30)
        assert result["value"] is None


class TestCancellationRate:
    def test_cancellation_rate(self, db_session):
        from app.models import Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        today = date.today()
        # 2 cancellations out of 10 orders = 0.2
        _make_row(db_session, "seller-1", "sku-1", today, orders=10, cancellations=2)

        result = calculate_cancellation_rate(db_session, "seller-1", today, days=30)
        assert result["value"] == 0.2


class TestReturnRate:
    def test_return_rate(self, db_session):
        from app.models import Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        today = date.today()
        _make_row(db_session, "seller-1", "sku-1", today, orders=10, returns=1)

        result = calculate_return_rate(db_session, "seller-1", today, days=30)
        assert result["value"] == 0.1


class TestConversionRate:
    def test_conversion_rate(self, db_session):
        from app.models import Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        today = date.today()
        # 5 orders / 100 views = 0.05
        _make_row(db_session, "seller-1", "sku-1", today, orders=5, views=100)

        result = calculate_conversion_rate(db_session, "seller-1", today, days=30)
        assert result["value"] == 0.05

    def test_conversion_none_when_no_views(self, db_session):
        from app.models import Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        result = calculate_conversion_rate(db_session, "seller-1", date.today(), days=30)
        assert result["value"] is None


class TestStockoutCount:
    def test_stockout_sku_count(self, db_session):
        from app.models import Product

        seller = Seller = None
        from app.models import Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        # 2 active products with 0 stock, 1 with stock
        db_session.add_all(
            [
                Product(
                    id="sku-1", seller_id="seller-1", sku_code="A-1", title="A",
                    category="Cat", selling_price=1000, unit_cost=800, current_stock=0, active=True,
                ),
                Product(
                    id="sku-2", seller_id="seller-1", sku_code="A-2", title="B",
                    category="Cat", selling_price=1000, unit_cost=800, current_stock=0, active=True,
                ),
                Product(
                    id="sku-3", seller_id="seller-1", sku_code="A-3", title="C",
                    category="Cat", selling_price=1000, unit_cost=800, current_stock=50, active=True,
                ),
            ]
        )
        db_session.commit()

        result = calculate_stockout_sku_count(db_session, "seller-1")
        assert result["value"] == 2


class TestPeriodOverPeriod:
    def test_pop_change(self):
        assert period_over_period_change(135000, 200000) == -32.5

    def test_pop_zero_previous(self):
        assert period_over_period_change(100, 0) is None

    def test_pop_none_previous(self):
        assert period_over_period_change(100, None) is None


class TestStockCover:
    def test_stock_cover_days(self, db_session):
        from app.models import Product, Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        today = date.today()
        db_session.add(
            Product(
                id="sku-1", seller_id="seller-1", sku_code="A-1", title="A",
                category="Cat", selling_price=1000, unit_cost=800,
                current_stock=100, active=True,
            )
        )
        db_session.commit()

        # 30 days, 300 units sold total -> 10/day -> 100/10 = 10 days cover
        for i in range(30):
            d = today - timedelta(days=i)
            _make_row(db_session, "seller-1", "sku-1", d, units_sold=10)

        result = calculate_stock_cover_days(db_session, "seller-1", "sku-1", today, days=30)
        assert result["value"] == 10.0


class TestInventoryValue:
    def test_inventory_value(self, db_session):
        from app.models import Product, Seller

        seller = Seller(id="seller-1", display_name="Test Seller", marketplace="mock")
        db_session.add(seller)
        db_session.commit()

        db_session.add_all(
            [
                Product(
                    id="sku-1", seller_id="seller-1", sku_code="A-1", title="A",
                    category="Cat", selling_price=1000, unit_cost=800, current_stock=10, active=True,
                ),
                Product(
                    id="sku-2", seller_id="seller-1", sku_code="A-2", title="B",
                    category="Cat", selling_price=2000, unit_cost=1500, current_stock=5, active=True,
                ),
            ]
        )
        db_session.commit()

        result = calculate_inventory_value(db_session, "seller-1")
        # cost: 800*10 + 1500*5 = 8000 + 7500 = 15500
        # selling: 1000*10 + 2000*5 = 10000 + 10000 = 20000
        assert result["value_at_cost"] == 15500
        assert result["value_at_selling"] == 20000
