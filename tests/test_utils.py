"""Tests for scripts/shared/utils.py"""
import pytest
from kodak.shared.utils import clean_num, generate_txn_hash, load_config


class TestCleanNum:
    """Tests for the clean_num function."""

    def test_float_passthrough(self):
        """Float values should pass through unchanged."""
        assert clean_num(123.45) == 123.45
        assert clean_num(0.0) == 0.0
        assert clean_num(-50.5) == -50.5

    def test_int_to_float(self):
        """Integer values should be converted to float."""
        assert clean_num(100) == 100.0
        assert clean_num(0) == 0.0
        assert clean_num(-25) == -25.0

    def test_string_parsing(self):
        """String numbers should be parsed correctly."""
        assert clean_num("123.45") == 123.45
        assert clean_num("1 000") == 1000.0  # Space as thousand separator
        assert clean_num("1,5") == 1.5  # Comma as decimal (European)

    def test_empty_values(self):
        """Empty/None values should return 0.0."""
        assert clean_num(None) == 0.0
        assert clean_num("") == 0.0

    def test_invalid_string(self):
        """Invalid strings should return 0.0."""
        assert clean_num("abc") == 0.0
        assert clean_num("N/A") == 0.0


class TestGenerateTxnHash:
    """Tests for transaction hash generation."""

    def test_consistent_hash(self):
        """Same inputs should produce same hash."""
        hash1 = generate_txn_hash("2024-01-15", "ACC001", "BUY", "AAPL", 1000.00)
        hash2 = generate_txn_hash("2024-01-15", "ACC001", "BUY", "AAPL", 1000.00)
        assert hash1 == hash2

    def test_different_inputs_different_hash(self):
        """Different inputs should produce different hashes."""
        hash1 = generate_txn_hash("2024-01-15", "ACC001", "BUY", "AAPL", 1000.00)
        hash2 = generate_txn_hash("2024-01-16", "ACC001", "BUY", "AAPL", 1000.00)
        assert hash1 != hash2

    def test_amount_precision(self):
        """Amount differences below 2 decimal places should hash the same."""
        hash1 = generate_txn_hash("2024-01-15", "ACC001", "BUY", "AAPL", 1000.001)
        hash2 = generate_txn_hash("2024-01-15", "ACC001", "BUY", "AAPL", 1000.004)
        assert hash1 == hash2  # Both round to 1000.00

    def test_date_with_time(self):
        """Date with timestamp should use only the date part."""
        hash1 = generate_txn_hash("2024-01-15 10:30:00", "ACC001", "BUY", "AAPL", 1000.00)
        hash2 = generate_txn_hash("2024-01-15 14:45:00", "ACC001", "BUY", "AAPL", 1000.00)
        assert hash1 == hash2


class TestLoadConfig:
    """Tests for configuration loading."""

    def test_returns_dict(self):
        """Config should always return a dictionary."""
        config = load_config()
        assert isinstance(config, dict)

    def test_has_base_currency(self):
        """Config should have a base_currency key."""
        config = load_config()
        assert 'base_currency' in config
        assert len(config['base_currency']) == 3  # Currency code is 3 letters

    def test_has_defaults(self):
        """Config should have default values."""
        config = load_config()
        assert 'data_dir' in config
        assert 'reference_dir' in config
