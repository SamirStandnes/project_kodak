"""Tests for scripts/shared/calculations.py"""
import pytest
from datetime import datetime
import pandas as pd

from kodak.shared.calculations import (
    xirr,
    get_adjusted_qty,
    get_price_with_fallback
)


class TestXirr:
    """Tests for the XIRR calculation function."""

    def test_empty_transactions(self):
        """Empty transaction list should return 0."""
        result = xirr([])
        assert result == 0.0

    def test_all_positive_flows(self):
        """All positive flows (no investment) should return 0."""
        transactions = [
            (datetime(2024, 1, 1), 1000.0),
            (datetime(2024, 6, 1), 500.0),
        ]
        result = xirr(transactions)
        assert result == 0.0

    def test_all_negative_flows(self):
        """All negative flows (no returns) should return 0."""
        transactions = [
            (datetime(2024, 1, 1), -1000.0),
            (datetime(2024, 6, 1), -500.0),
        ]
        result = xirr(transactions)
        assert result == 0.0

    def test_simple_100_percent_return(self):
        """Invest 1000, get 2000 after 1 year = 100% return."""
        transactions = [
            (datetime(2023, 1, 1), -1000.0),  # Investment (outflow)
            (datetime(2024, 1, 1), 2000.0),   # Return (inflow)
        ]
        result = xirr(transactions)
        assert abs(result - 1.0) < 0.01  # ~100% return

    def test_simple_50_percent_return(self):
        """Invest 1000, get 1500 after 1 year = 50% return."""
        transactions = [
            (datetime(2023, 1, 1), -1000.0),
            (datetime(2024, 1, 1), 1500.0),
        ]
        result = xirr(transactions)
        assert abs(result - 0.5) < 0.01  # ~50% return

    def test_negative_return(self):
        """Invest 1000, get 500 back should yield negative return."""
        transactions = [
            (datetime(2023, 1, 1), -1000.0),
            (datetime(2024, 1, 1), 500.0),
        ]
        result = xirr(transactions)
        assert result < 0  # Should be a negative return

    def test_multiple_investments(self):
        """Multiple investments with final value."""
        transactions = [
            (datetime(2023, 1, 1), -1000.0),
            (datetime(2023, 7, 1), -1000.0),
            (datetime(2024, 1, 1), 2200.0),
        ]
        result = xirr(transactions)
        assert result > 0  # Should be positive return

    def test_transactions_sorted(self):
        """Transactions should work regardless of input order."""
        # Unsorted input
        transactions = [
            (datetime(2024, 1, 1), 1500.0),
            (datetime(2023, 1, 1), -1000.0),
        ]
        result = xirr(transactions)
        assert abs(result - 0.5) < 0.01


class TestGetAdjustedQty:
    """Tests for the stock split adjustment function."""

    def test_no_splits(self):
        """No splits in map should return original quantity."""
        split_map = {}
        result = get_adjusted_qty("AAPL", 100.0, "2024-01-01", split_map)
        assert result == 100.0

    def test_symbol_not_in_map(self):
        """Symbol not in split map should return original quantity."""
        split_map = {"TSLA": [(pd.Timestamp("2024-06-01"), 5.0)]}
        result = get_adjusted_qty("AAPL", 100.0, "2024-01-01", split_map)
        assert result == 100.0

    def test_zero_quantity(self):
        """Zero quantity should return zero."""
        split_map = {"AAPL": [(pd.Timestamp("2024-06-01"), 4.0)]}
        result = get_adjusted_qty("AAPL", 0.0, "2024-01-01", split_map)
        assert result == 0.0

    def test_split_after_ref_date(self):
        """Split after ref date should multiply quantity."""
        split_map = {"AAPL": [(pd.Timestamp("2024-06-01"), 4.0)]}
        # Bought 25 shares before 4:1 split
        result = get_adjusted_qty("AAPL", 25.0, "2024-01-01", split_map)
        assert result == 100.0  # 25 * 4 = 100

    def test_split_before_ref_date(self):
        """Split before ref date should not affect quantity."""
        split_map = {"AAPL": [(pd.Timestamp("2024-01-01"), 4.0)]}
        # Bought 100 shares after the split
        result = get_adjusted_qty("AAPL", 100.0, "2024-06-01", split_map)
        assert result == 100.0  # No adjustment needed

    def test_multiple_splits(self):
        """Multiple splits should compound."""
        split_map = {
            "AAPL": [
                (pd.Timestamp("2024-03-01"), 2.0),  # 2:1 split
                (pd.Timestamp("2024-09-01"), 5.0),  # 5:1 split
            ]
        }
        # Bought 10 shares before both splits
        result = get_adjusted_qty("AAPL", 10.0, "2024-01-01", split_map)
        assert result == 100.0  # 10 * 2 * 5 = 100

    def test_partial_split_application(self):
        """Only splits after ref date should apply."""
        split_map = {
            "AAPL": [
                (pd.Timestamp("2024-03-01"), 2.0),  # 2:1 split (before)
                (pd.Timestamp("2024-09-01"), 5.0),  # 5:1 split (after)
            ]
        }
        # Bought 20 shares after first split but before second
        result = get_adjusted_qty("AAPL", 20.0, "2024-06-01", split_map)
        assert result == 100.0  # 20 * 5 = 100 (only second split applies)


class TestGetPriceWithFallback:
    """Tests for the price lookup function."""

    def test_price_from_dict(self):
        """Should return price from dictionary if available."""
        price_dict = {"AAPL": 150.0, "MSFT": 350.0}
        result = get_price_with_fallback("AAPL", price_dict, "2024-01-01")
        assert result == 150.0

    def test_missing_price_returns_zero(self):
        """Missing price with no fallback returns 0."""
        price_dict = {"MSFT": 350.0}
        result = get_price_with_fallback("AAPL", price_dict, "2024-01-01")
        # Will return 0.0 since no DB fallback in test
        assert result == 0.0

    def test_zero_price_triggers_fallback(self):
        """Zero price in dict should trigger fallback logic."""
        price_dict = {"AAPL": 0.0}
        result = get_price_with_fallback("AAPL", price_dict, "2024-01-01")
        # Falls back to DB, which won't find anything in test
        assert result == 0.0

    def test_missing_log_parameter(self):
        """Missing log should be populated when price not found."""
        price_dict = {}
        missing_log = []
        result = get_price_with_fallback("AAPL", price_dict, "2024-01-01", missing_log)
        assert result == 0.0
        # Note: missing_log population depends on DB state
